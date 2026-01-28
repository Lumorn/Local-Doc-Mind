"""Dialog fuer die Bearbeitung der Einstellungen."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QWidget,
)

from src.core.config import Config


class SettingsDialog(QDialog):
    """Modales Fenster fuer die YAML-Konfiguration."""

    def __init__(self, config: Config, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.config = config

        self.setWindowTitle("Einstellungen")
        self.setModal(True)

        layout = QFormLayout(self)

        # Pfadfelder mit Browse-Buttons.
        self.input_edit = QLineEdit(self)
        layout.addRow("Input-Pfad", self._build_path_row(self.input_edit))

        self.output_edit = QLineEdit(self)
        layout.addRow("Output-Pfad", self._build_path_row(self.output_edit))

        self.backup_edit = QLineEdit(self)
        layout.addRow("Backup-Pfad", self._build_path_row(self.backup_edit))

        # Hardware-Optionen.
        self.flash_attn_checkbox = QCheckBox("Use Flash Attention", self)
        layout.addRow("Hardware", self.flash_attn_checkbox)

        self.cpu_offload_checkbox = QCheckBox("Force CPU Offload", self)
        layout.addRow("", self.cpu_offload_checkbox)

        # Quantisierungsauswahl.
        self.quantization_combo = QComboBox(self)
        self.quantization_combo.addItem("4-bit", "4bit")
        self.quantization_combo.addItem("8-bit", "8bit")
        self.quantization_combo.addItem("None", "none")
        layout.addRow("Quantisierung", self.quantization_combo)

        # Buttons.
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        self.button_box.accepted.connect(self._save_settings)
        self.button_box.rejected.connect(self.reject)
        layout.addRow(self.button_box)

        self._load_settings()

    def _build_path_row(self, line_edit: QLineEdit) -> QWidget:
        """Erzeugt eine Zeile mit Eingabefeld und Browse-Button."""
        container = QWidget(self)
        row_layout = QHBoxLayout(container)
        row_layout.setContentsMargins(0, 0, 0, 0)
        browse_button = QPushButton("Browse", container)
        browse_button.clicked.connect(lambda: self._browse_for_path(line_edit))
        row_layout.addWidget(line_edit)
        row_layout.addWidget(browse_button)
        return container

    def _browse_for_path(self, target: QLineEdit) -> None:
        """Oeffnet einen Ordnerdialog und uebernimmt die Auswahl."""
        start_dir = target.text() or str(Path.cwd())
        selected = QFileDialog.getExistingDirectory(self, "Ordner auswaehlen", start_dir)
        if selected:
            target.setText(selected)

    def _load_settings(self) -> None:
        """Laedt die Werte aus der Konfiguration in die UI."""
        paths = self.config.get("paths", {})
        system = self.config.get("system", {})
        models = self.config.get("models", {})
        ocr_settings = models.get("ocr", {})

        self.input_edit.setText(paths.get("input", "./input"))
        self.output_edit.setText(paths.get("output", "./output"))
        self.backup_edit.setText(paths.get("backup", "./backup"))

        self.flash_attn_checkbox.setChecked(bool(system.get("use_flash_attn", False)))
        self.cpu_offload_checkbox.setChecked(bool(system.get("cpu_offload", True)))

        quantization_value = ocr_settings.get("quantization", "4bit")
        index = self.quantization_combo.findData(quantization_value)
        if index < 0:
            index = self.quantization_combo.findData("4bit")
        self.quantization_combo.setCurrentIndex(index)

    def _save_settings(self) -> None:
        """Schreibt die neuen Werte in die Konfiguration."""
        paths = dict(self.config.get("paths", {}))
        paths.update(
            {
                "input": self.input_edit.text().strip() or "./input",
                "output": self.output_edit.text().strip() or "./output",
                "backup": self.backup_edit.text().strip() or "./backup",
            }
        )

        system = dict(self.config.get("system", {}))
        system.update(
            {
                "use_flash_attn": self.flash_attn_checkbox.isChecked(),
                "cpu_offload": self.cpu_offload_checkbox.isChecked(),
            }
        )

        models = dict(self.config.get("models", {}))
        ocr_settings = dict(models.get("ocr", {}))
        ocr_settings["quantization"] = self.quantization_combo.currentData()
        models["ocr"] = ocr_settings

        self.config.save({"paths": paths, "system": system, "models": models})
        self.config.reload()

        self.accept()
