"""Processing-Pipeline fuer neue Dokumente."""

from __future__ import annotations

import hashlib
import logging
import os
import queue
import shutil
import threading
import time
from datetime import date
from pathlib import Path

logger = logging.getLogger(__name__)


class ProcessingPipeline(threading.Thread):
    """Verarbeitet Dateien aus der Queue mit einem Backup-First-Schritt."""

    def __init__(self, config: dict, model_manager) -> None:
        super().__init__(daemon=True)
        # Konfiguration und Modellmanager merken.
        self.config = config
        self.model_manager = model_manager
        self.queue = self._resolve_queue(config)
        self._stop_event = threading.Event()

        paths = config.get("paths", {})
        self.backup_root = Path(paths.get("backup", "./backup"))
        self.processing_root = Path(paths.get("processing", "./processing"))

    def stop(self) -> None:
        """Signalisiert der Pipeline das Stoppen."""
        self._stop_event.set()

    def run(self) -> None:
        """Thread-Loop fuer die Verarbeitung."""
        logger.info("Processing-Pipeline gestartet.")
        while not self._stop_event.is_set():
            try:
                file_path = self.queue.get(timeout=0.5)
            except queue.Empty:
                continue

            try:
                self._process_file(Path(file_path))
            finally:
                self.queue.task_done()

        logger.info("Processing-Pipeline gestoppt.")

    def _process_file(self, file_path: Path) -> None:
        """Fuehrt den Backup-First-Schritt und das Verschieben aus."""
        if not file_path.exists():
            logger.warning("Datei nicht gefunden: %s", file_path)
            return

        start_time = time.time()
        logger.info("Starte Backup fuer Datei: %s", file_path)
        backup_path = self._create_backup(file_path)
        if backup_path is None:
            return

        if not self._verify_backup(file_path, backup_path):
            logger.error("Backup-Integritaet fehlgeschlagen: %s", file_path)
            return

        logger.info("Backup erfolgreich: %s", backup_path)
        self._move_to_processing(file_path)

        # Hier wuerde die weitere KI-Verarbeitung starten.
        duration = time.time() - start_time
        logger.info(
            "Datei bereit fuer Verarbeitung: %s (Dauer: %.2fs)",
            file_path.name,
            duration,
        )

    def _create_backup(self, file_path: Path) -> Path | None:
        """Erstellt ein Backup der Datei im datierten Ordner."""
        date_folder = self.backup_root / date.today().isoformat()
        date_folder.mkdir(parents=True, exist_ok=True)
        backup_path = date_folder / file_path.name

        try:
            shutil.copy2(file_path, backup_path)
        except OSError as exc:
            logger.error("Backup fehlgeschlagen (%s): %s", exc, file_path)
            return None

        return backup_path

    def _verify_backup(self, source_path: Path, backup_path: Path) -> bool:
        """Prueft die Integritaet des Backups via SHA256."""
        source_hash = _calculate_sha256(source_path)
        backup_hash = _calculate_sha256(backup_path)
        logger.debug("SHA256 Quelle: %s", source_hash)
        logger.debug("SHA256 Backup: %s", backup_hash)
        return source_hash == backup_hash

    def _move_to_processing(self, file_path: Path) -> None:
        """Verschiebt die Datei in den Processing-Ordner."""
        self.processing_root.mkdir(parents=True, exist_ok=True)
        target_path = self.processing_root / file_path.name

        try:
            file_size = os.path.getsize(file_path)
            shutil.move(file_path, target_path)
        except OSError as exc:
            logger.error("Verschieben fehlgeschlagen (%s): %s", exc, file_path)
            return

        logger.info(
            "Datei in Processing verschoben: %s (Groesse: %d Bytes)",
            target_path,
            file_size,
        )

    @staticmethod
    def _resolve_queue(config: dict):
        """Holt die Queue aus der Konfiguration."""
        if "queue" not in config:
            raise ValueError("Konfiguration enthaelt keine Queue unter 'queue'.")
        return config["queue"]


def _calculate_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Berechnet einen SHA256-Hash fuer eine Datei."""
    sha256 = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            sha256.update(chunk)
    return sha256.hexdigest()

