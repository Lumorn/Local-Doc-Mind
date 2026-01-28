"""Konfigurationslogik fuer Local-Doc-Mind."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class Config:
    """Kapselt die YAML-Konfiguration und bietet komfortable Helfer."""

    config_path: Path
    data: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Nach der Initialisierung die Daten aus der Datei laden.
        self.config_path = Path(self.config_path)
        self.reload()

    def reload(self) -> None:
        """Laedt die Konfiguration neu aus der YAML-Datei."""
        if self.config_path.exists():
            with self.config_path.open("r", encoding="utf-8") as config_file:
                self.data = yaml.safe_load(config_file) or {}
        else:
            self.data = {}
        self.data["config_path"] = str(self.config_path)

    def save(self, new_data: dict[str, Any]) -> None:
        """Schreibt eine aktualisierte Konfiguration in die YAML-Datei."""
        self.data.update(new_data)
        self._write_to_disk()

    def _write_to_disk(self) -> None:
        """Persistiert die Konfiguration ohne Laufzeitdaten."""
        payload = {
            key: value
            for key, value in self.data.items()
            if key not in {"config_path", "queue"}
        }
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with self.config_path.open("w", encoding="utf-8") as config_file:
            yaml.safe_dump(payload, config_file, sort_keys=False, allow_unicode=True)

    def get(self, key: str, default: Any | None = None) -> Any:
        """Gibt einen Wert aus der Konfiguration zurueck."""
        return self.data.get(key, default)

    def set_runtime_value(self, key: str, value: Any) -> None:
        """Setzt Werte, die nicht in die YAML geschrieben werden sollen."""
        self.data[key] = value

    def get_model_path(self) -> Path:
        """Gibt den Pfad fuer Modelldownloads zurueck."""
        paths = self.data.get("paths", {})
        return Path(paths.get("models", "./models")).resolve()

    def __getitem__(self, key: str) -> Any:
        """Erlaubt dict-aehnlichen Zugriff auf die Daten."""
        return self.data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        """Erlaubt dict-aehnliches Setzen von Werten."""
        self.data[key] = value
