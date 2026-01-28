"""Dialog fuer das Model-Management."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
from typing import Callable

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.core.config import Config


@dataclass(frozen=True)
class ModelInfo:
    """Beschreibung eines unterstuetzten Modells."""

    name: str
    model_type: str
    repo_id: str


class DownloadThread(QThread):
    """Fuehrt den Model-Download in einem separaten Thread aus."""

    progress_changed = pyqtSignal(int)
    status_changed = pyqtSignal(str)
    finished_with_result = pyqtSignal(bool, str)

    def __init__(self, repo_id: str, target_dir: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.repo_id = repo_id
        self.target_dir = target_dir

    def run(self) -> None:
        """Startet den Snapshot-Download und meldet Fortschritt."""
        try:
            from huggingface_hub import snapshot_download
            from tqdm.auto import tqdm

            self.status_changed.emit("Download gestartet")
            self.progress_changed.emit(0)
            self.target_dir.mkdir(parents=True, exist_ok=True)

            def emit_progress(value: int) -> None:
                self.progress_changed.emit(value)

            class SignalTqdm(tqdm):
                """TQDM-Adapter fuer Fortschrittsmeldungen in der GUI."""

                def update(self, n: int = 1) -> None:  # type: ignore[override]
                    super().update(n)
                    if self.total:
                        percent = int(self.n / self.total * 100)
                        emit_progress(percent)

            snapshot_download(
                repo_id=self.repo_id,
                local_dir=str(self.target_dir),
                local_dir_use_symlinks=False,
                resume_download=True,
                tqdm_class=SignalTqdm,
            )
            self.progress_changed.emit(100)
            self.status_changed.emit("Download abgeschlossen")
            self.finished_with_result.emit(True, "")
        except Exception as exc:  # noqa: BLE001 - Fehler sollen in der GUI angezeigt werden.
            self.status_changed.emit(f"Fehler: {exc}")
            self.finished_with_result.emit(False, str(exc))


class ModelManagerDialog(QDialog):
    """Verwaltet Download und Loeschung der KI-Modelle."""

    def __init__(self, config: Config, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.config = config
        self.models_path = self.config.get_model_path()
        self.models_path.mkdir(parents=True, exist_ok=True)

        self.supported_models = self._build_supported_models(config)
        self.active_threads: dict[int, DownloadThread] = {}
        self.progress_widgets: dict[int, QProgressBar] = {}
        self.action_buttons: dict[int, QPushButton] = {}

        self.setWindowTitle("Model-Manager")
        self.resize(800, 400)

        main_layout = QVBoxLayout(self)
        self.table = QTableWidget(self)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Modell Name", "Typ", "Status", "Aktion"])
        self.table.setRowCount(len(self.supported_models))
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        main_layout.addWidget(self.table)
        self._populate_table()

    @staticmethod
    def _build_supported_models(config: Config) -> list[ModelInfo]:
        """Definiert die Liste der unterstuetzten Modelle."""
        models = config.get("models", {})
        ocr_repo = models.get("ocr", {}).get("repo", "deepseek-ai/DeepSeek-OCR-2")
        llm_repo = models.get("llm", {}).get("repo", "Qwen/Qwen2.5-7B-Instruct")
        return [
            ModelInfo(name="DeepSeek-OCR-2", model_type="OCR", repo_id=ocr_repo),
            ModelInfo(name="Qwen2.5-7B-Instruct", model_type="LLM", repo_id=llm_repo),
            ModelInfo(
                name="all-MiniLM-L6-v2",
                model_type="Embedding",
                repo_id="sentence-transformers/all-MiniLM-L6-v2",
            ),
        ]

    @staticmethod
    def _model_folder(repo_id: str) -> str:
        """Erzeugt einen stabilen Ordnernamen fuer lokale Downloads."""
        return repo_id.replace("/", "__")

    def _populate_table(self) -> None:
        """Fuellt die Tabelle mit Modellinformationen."""
        for row, info in enumerate(self.supported_models):
            name_item = QTableWidgetItem(info.name)
            type_item = QTableWidgetItem(info.model_type)
            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, type_item)
            self._refresh_row(row)

        self.table.resizeColumnsToContents()

    def _refresh_row(self, row: int) -> None:
        """Aktualisiert Status und Aktion fuer eine Zeile."""
        model_info = self.supported_models[row]
        installed = self._is_model_installed(model_info.repo_id)
        status_text = "Installiert" if installed else "Fehlt"
        status_item = QTableWidgetItem(status_text)
        status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(row, 2, status_item)
        self._set_action_widget(row, installed)

    def _set_action_widget(self, row: int, installed: bool) -> None:
        """Erzeugt das Aktionsfeld mit Button und Fortschrittsbalken."""
        container = QWidget(self)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        action_button = QPushButton("Loeschen" if installed else "Download", container)
        progress_bar = QProgressBar(container)
        progress_bar.setRange(0, 100)
        progress_bar.setValue(0)
        progress_bar.setVisible(False)

        if installed:
            action_button.clicked.connect(lambda: self._delete_model(row))
        else:
            action_button.clicked.connect(lambda: self._start_download(row))

        layout.addWidget(action_button)
        layout.addWidget(progress_bar)

        self.action_buttons[row] = action_button
        self.progress_widgets[row] = progress_bar
        self.table.setCellWidget(row, 3, container)

    def _model_dir(self, repo_id: str) -> Path:
        """Berechnet den lokalen Modellpfad."""
        return self.models_path / self._model_folder(repo_id)

    def _is_model_installed(self, repo_id: str) -> bool:
        """Prueft, ob ein Modell lokal installiert ist."""
        model_dir = self._model_dir(repo_id)
        return model_dir.exists() and any(model_dir.iterdir())

    def _start_download(self, row: int) -> None:
        """Startet einen Download-Thread fuer das gewaehlte Modell."""
        model_info = self.supported_models[row]
        target_dir = self._model_dir(model_info.repo_id)
        progress_bar = self.progress_widgets[row]
        action_button = self.action_buttons[row]

        progress_bar.setVisible(True)
        progress_bar.setValue(0)
        action_button.setEnabled(False)

        thread = DownloadThread(model_info.repo_id, target_dir, self)
        thread.progress_changed.connect(progress_bar.setValue)
        thread.status_changed.connect(lambda text: self._update_status_text(row, text))
        thread.finished_with_result.connect(
            lambda success, message: self._handle_download_finished(row, success, message)
        )
        thread.finished.connect(lambda: self._cleanup_thread(row))
        self.active_threads[row] = thread
        thread.start()

    def _update_status_text(self, row: int, text: str) -> None:
        """Aktualisiert die Status-Spalte mit Laufzeitinfos."""
        status_item = self.table.item(row, 2)
        if status_item is not None:
            status_item.setText(text)

    def _handle_download_finished(self, row: int, success: bool, message: str) -> None:
        """Reagiert auf das Ende eines Downloads."""
        progress_bar = self.progress_widgets.get(row)
        action_button = self.action_buttons.get(row)
        if progress_bar:
            progress_bar.setVisible(False)
        if action_button:
            action_button.setEnabled(True)

        if not success:
            QMessageBox.warning(self, "Download fehlgeschlagen", message or "Unbekannter Fehler")
        self._refresh_row(row)

    def _cleanup_thread(self, row: int) -> None:
        """Entfernt den Thread aus der internen Verwaltung."""
        self.active_threads.pop(row, None)

    def _delete_model(self, row: int) -> None:
        """Loescht das Modellverzeichnis, um Speicher freizugeben."""
        model_info = self.supported_models[row]
        model_dir = self._model_dir(model_info.repo_id)
        if not model_dir.exists():
            self._refresh_row(row)
            return

        try:
            shutil.rmtree(model_dir)
        except OSError as exc:
            QMessageBox.warning(self, "Loeschen fehlgeschlagen", str(exc))
            return

        self._refresh_row(row)

    def any_model_missing(self) -> bool:
        """Prueft, ob mindestens ein Modell fehlt."""
        return any(not self._is_model_installed(info.repo_id) for info in self.supported_models)

    def ensure_models(self, on_missing: Callable[[], None]) -> None:
        """Fuehrt eine Callback-Aktion aus, wenn Modelle fehlen."""
        if self.any_model_missing():
            on_missing()
