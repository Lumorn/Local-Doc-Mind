"""Hauptfenster fuer das Local-Doc-Mind-Dashboard."""

from __future__ import annotations

from pathlib import Path

from PIL import Image
from PyQt6 import QtWidgets
from PyQt6.QtCore import QDir, QModelIndex, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import (
    QAction,
    QColor,
    QDesktopServices,
    QPalette,
    QStandardItem,
    QStandardItemModel,
)
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMainWindow,
    QSplitter,
    QTextEdit,
    QToolBar,
    QTreeView,
    QWidget,
)

from src.gui.widgets.scan_view import ScanView


def apply_dark_theme(app: QApplication) -> None:
    """Aktiviert den Fusion-Style und eine dunkle Farbpalette."""
    app.setStyle("Fusion")

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(30, 30, 30))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(220, 220, 220))
    palette.setColor(QPalette.ColorRole.Base, QColor(20, 20, 20))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(30, 30, 30))
    palette.setColor(QPalette.ColorRole.Text, QColor(220, 220, 220))
    palette.setColor(QPalette.ColorRole.Button, QColor(45, 45, 45))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(220, 220, 220))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(57, 255, 20))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(10, 10, 10))
    app.setPalette(palette)


class MainWindow(QMainWindow):
    """Dashboard mit Dateibaum, Scan-Ansicht und Log-Konsole."""

    start_watchdog_requested = pyqtSignal()
    stop_watchdog_requested = pyqtSignal()

    def __init__(self, config: dict, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # Konfiguration sichern und Ausgangspfad bestimmen.
        self.config = config
        paths = config.get("paths", {})
        self.output_path = str(Path(paths.get("output", "./output")).resolve())

        self.setWindowTitle("Local-Doc-Mind")
        self.resize(1280, 720)

        self.tree_view = QTreeView(self)
        self.file_model = self._create_file_model()
        self.tree_view.setModel(self.file_model)
        self._apply_tree_root()
        self.tree_view.setHeaderHidden(False)

        self.scan_view = ScanView(self)

        self.log_view = QTextEdit(self)
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet(
            "background-color: #0b0f0b; color: #39ff14; font-family: Consolas, monospace;"
        )

        right_splitter = QSplitter(Qt.Orientation.Vertical, self)
        right_splitter.addWidget(self.scan_view)
        right_splitter.addWidget(self.log_view)
        right_splitter.setStretchFactor(0, 3)
        right_splitter.setStretchFactor(1, 1)

        main_splitter = QSplitter(Qt.Orientation.Horizontal, self)
        main_splitter.addWidget(self.tree_view)
        main_splitter.addWidget(right_splitter)
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 3)
        self.setCentralWidget(main_splitter)

        self._build_toolbar()
        _ = Image

    def _build_toolbar(self) -> None:
        """Erzeugt die Haupt-Toolbar mit Aktionen."""
        toolbar = QToolBar("Aktionen", self)
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        start_action = QAction("Start Watchdog", self)
        start_action.triggered.connect(self.start_watchdog_requested.emit)
        toolbar.addAction(start_action)

        stop_action = QAction("Stop Watchdog", self)
        stop_action.triggered.connect(self.stop_watchdog_requested.emit)
        toolbar.addAction(stop_action)

        open_action = QAction("Open Config", self)
        open_action.triggered.connect(self._open_config)
        toolbar.addAction(open_action)

    def attach_worker(self, worker) -> None:
        """Verbindet Worker-Signale mit den UI-Komponenten."""
        worker.new_log.connect(self.append_log)
        worker.update_image.connect(self.scan_view.show_image)
        worker.update_overlay.connect(self.scan_view.draw_boxes)
        worker.file_processed.connect(self._refresh_tree)

    def append_log(self, message: str) -> None:
        """Fuegt dem Log-Fenster eine neue Zeile hinzu."""
        self.log_view.append(message)

    def _refresh_tree(self, _path: str | None = None) -> None:
        """Aktualisiert den Dateibaum fuer neue Inhalte."""
        self.file_model = self._create_file_model()
        self.tree_view.setModel(self.file_model)
        self._apply_tree_root()

    def _open_config(self) -> None:
        """Oeffnet die Konfiguration oder laesst eine Datei auswaehlen."""
        config_path = Path(self.config.get("config_path", ""))
        if config_path.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(config_path)))
            return

        selected, _ = QFileDialog.getOpenFileName(
            self,
            "Konfiguration auswaehlen",
            str(Path.cwd()),
            "YAML-Dateien (*.yaml *.yml)",
        )
        if selected:
            QDesktopServices.openUrl(QUrl.fromLocalFile(selected))

    def _create_file_model(self):
        """Erzeugt ein Dateimodell mit kompatibler Fallback-Logik."""
        model_class = getattr(QtWidgets, "QFileSystemModel", None)
        if model_class is None:
            model_class = getattr(QtWidgets, "QDirModel", None)

        if model_class is None:
            return self._build_fallback_model()

        model = model_class(self)
        if hasattr(model, "setFilter"):
            model.setFilter(QDir.Filter.AllDirs | QDir.Filter.Files | QDir.Filter.NoDotAndDotDot)
        if hasattr(model, "setRootPath"):
            model.setRootPath(self.output_path)
        return model

    def _apply_tree_root(self) -> None:
        """Setzt den Root-Knoten fuer den Dateibaum."""
        if not hasattr(self.file_model, "index"):
            return

        if isinstance(self.file_model, QStandardItemModel):
            # Beim Fallback-Modell muss ein Index ueber Zeilen/Spalten gesetzt werden.
            root_index = self.file_model.index(0, 0) if self.file_model.rowCount() else QModelIndex()
        else:
            root_index = self.file_model.index(self.output_path)

        if root_index.isValid():
            self.tree_view.setRootIndex(root_index)

    def _build_fallback_model(self) -> QStandardItemModel:
        """Baut ein einfaches Modell, falls kein Qt-Dateimodell verfuegbar ist."""
        model = QStandardItemModel(self)
        model.setHorizontalHeaderLabels(["Dateien"])
        root_item = QStandardItem(Path(self.output_path).name or self.output_path)
        root_item.setEditable(False)
        model.appendRow(root_item)
        self._populate_tree(root_item, Path(self.output_path))
        return model

    def _populate_tree(self, parent_item: QStandardItem, directory: Path) -> None:
        """Fuegt rekursiv Unterordner und Dateien zum Fallback-Modell hinzu."""
        if not directory.exists():
            return
        for entry in sorted(directory.iterdir(), key=lambda item: (item.is_file(), item.name.lower())):
            item = QStandardItem(entry.name)
            item.setEditable(False)
            parent_item.appendRow(item)
            if entry.is_dir():
                self._populate_tree(item, entry)
