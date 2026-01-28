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
from typing import Callable

from src.core.context import ContextManager
from src.intelligence.analyzer import analyze_document
from src.intelligence.naming import NamingEngine
from src.intelligence.splitter import scan_for_splits

logger = logging.getLogger(__name__)


class ProcessingPipeline(threading.Thread):
    """Verarbeitet Dateien aus der Queue mit einem Backup-First-Schritt."""

    def __init__(
        self,
        config: dict,
        model_manager,
        callbacks: dict[str, Callable] | None = None,
    ) -> None:
        super().__init__(daemon=True)
        # Konfiguration und Modellmanager merken.
        self.config = config
        self.model_manager = model_manager
        self.queue = self._resolve_queue(config)
        self._stop_event = threading.Event()
        self.callbacks: dict[str, Callable] = {}
        if callbacks:
            self.set_callbacks(callbacks)

        paths = config.get("paths", {})
        self.backup_root = Path(paths.get("backup", "./backup"))
        self.processing_root = Path(paths.get("processing", "./processing"))
        self.output_root = Path(paths.get("output", "./output"))
        self.error_root = Path(paths.get("error", "./error"))
        self.context_manager = ContextManager()
        self.naming_engine = NamingEngine()

    def set_callbacks(self, callbacks: dict[str, Callable]) -> None:
        """Registriert optionale Callback-Funktionen fuer GUI-Events."""
        for name, handler in callbacks.items():
            if handler is not None:
                self.callbacks[name] = handler

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
        """Fuehrt den vollstaendigen Workflow fuer eine Datei aus."""
        if not file_path.exists():
            logger.warning("Datei nicht gefunden: %s", file_path)
            self._emit_log(f"Datei nicht gefunden: {file_path}")
            return

        start_time = time.time()
        target_path = None
        try:
            logger.info("Starte Backup fuer Datei: %s", file_path)
            self._emit_log(f"Starte Backup fuer Datei: {file_path.name}")
            self._emit_image(str(file_path))
            backup_path = self._create_backup(file_path)
            if backup_path is None:
                return

            if not self._verify_backup(file_path, backup_path):
                logger.error("Backup-Integritaet fehlgeschlagen: %s", file_path)
                self._emit_log(f"Backup-Integritaet fehlgeschlagen: {file_path.name}")
                return

            logger.info("Backup erfolgreich: %s", backup_path)
            self._emit_log(f"Backup erfolgreich: {backup_path.name}")
            target_path = self._move_to_processing(file_path)
        except Exception as exc:  # noqa: BLE001
            logger.error("Backup-Phase fehlgeschlagen: %s", exc)
            self._emit_log(f"Backup-Phase fehlgeschlagen: {file_path.name}")
            self._move_to_error(file_path)
            return

        processing_path = target_path or file_path
        self._emit_log("Aufteilen...")
        logger.info("Starte Split-Analyse fuer %s", processing_path)
        try:
            split_paths = scan_for_splits(str(processing_path))
        except Exception as exc:  # noqa: BLE001
            logger.error("Split-Analyse fehlgeschlagen: %s", exc)
            self._emit_log(f"Split-Analyse fehlgeschlagen: {processing_path.name}")
            self._move_to_error(processing_path)
            return

        if not split_paths:
            split_paths = [str(processing_path)]

        for split_index, split_path in enumerate(split_paths, start=1):
            part_path = Path(split_path)
            self._emit_log(f"Lesen... ({split_index}/{len(split_paths)})")
            self._emit_image(str(part_path))
            try:
                markdown = analyze_document(str(part_path))
                context_hint = self.context_manager.get_context(self.output_root)
                combined_input = markdown
                if context_hint:
                    combined_input = f"{markdown}\n\nKontext:\n{context_hint}"

                self._emit_log("Benennen...")
                suggested_name = self.naming_engine.suggest_name(combined_input)
                target_path = self._build_target_path(suggested_name)
                self._emit_log("Verschieben...")
                final_path = self._move_to_final(part_path, target_path)
                if final_path:
                    self._emit_file_processed(str(final_path))
            except Exception as exc:  # noqa: BLE001
                logger.error("Verarbeitung fehlgeschlagen: %s", exc)
                self._emit_log(f"Verarbeitung fehlgeschlagen: {part_path.name}")
                self._move_to_error(part_path)
                continue

        duration = time.time() - start_time
        logger.info(
            "Datei verarbeitet: %s (Dauer: %.2fs)",
            file_path.name,
            duration,
        )
        self._emit_overlay([])
        self._emit_log(f"Verarbeitung abgeschlossen: {file_path.name} ({duration:.2f}s)")

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

    def _move_to_processing(self, file_path: Path) -> Path | None:
        """Verschiebt die Datei in den Processing-Ordner."""
        self.processing_root.mkdir(parents=True, exist_ok=True)
        target_path = self.processing_root / file_path.name

        try:
            file_size = os.path.getsize(file_path)
            shutil.move(file_path, target_path)
        except OSError as exc:
            logger.error("Verschieben fehlgeschlagen (%s): %s", exc, file_path)
            self._emit_log(f"Verschieben fehlgeschlagen: {file_path.name}")
            return

        logger.info(
            "Datei in Processing verschoben: %s (Groesse: %d Bytes)",
            target_path,
            file_size,
        )
        self._emit_log(f"Datei verschoben: {target_path.name}")
        return target_path

    def _build_target_path(self, suggested_name: str) -> Path:
        """Ermittelt den Zielpfad basierend auf dem Vorschlag."""
        year = str(date.today().year)
        suggested_path = Path(suggested_name)
        category = "Unsortiert"

        if suggested_path.parent != Path("."):
            category = suggested_path.parent.parts[0]

        filename = suggested_path.name or "dokument.pdf"
        if not filename.lower().endswith(".pdf"):
            filename = f"{filename}.pdf"

        return self.output_root / year / category / filename

    def _move_to_final(self, source_path: Path, target_path: Path) -> Path | None:
        """Verschiebt die Datei in den finalen Zielordner."""
        target_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.move(str(source_path), str(target_path))
        except OSError as exc:
            logger.error("Finales Verschieben fehlgeschlagen (%s): %s", exc, source_path)
            self._emit_log(f"Finales Verschieben fehlgeschlagen: {source_path.name}")
            return None

        logger.info("Datei final verschoben nach %s.", target_path)
        self._emit_log(f"Datei final verschoben: {target_path.name}")
        return target_path

    def _move_to_error(self, file_path: Path) -> None:
        """Verschiebt eine Datei in den Fehlerordner."""
        self.error_root.mkdir(parents=True, exist_ok=True)
        target_path = self.error_root / file_path.name
        try:
            if file_path.exists():
                shutil.move(str(file_path), str(target_path))
        except OSError as exc:
            logger.error("Fehler-Handling fehlgeschlagen (%s): %s", exc, file_path)
            self._emit_log(f"Fehler-Handling fehlgeschlagen: {file_path.name}")
            return

        logger.info("Datei in Fehlerordner verschoben: %s", target_path)
        self._emit_log(f"Datei in Fehlerordner verschoben: {target_path.name}")

    @staticmethod
    def _resolve_queue(config: dict):
        """Holt die Queue aus der Konfiguration."""
        if "queue" not in config:
            raise ValueError("Konfiguration enthaelt keine Queue unter 'queue'.")
        return config["queue"]

    def _emit_log(self, message: str) -> None:
        """Sendet Log-Text an einen optionalen Callback."""
        handler = self.callbacks.get("log")
        if handler:
            handler(message)

    def _emit_image(self, image_path: str) -> None:
        """Sendet einen Bildpfad an einen optionalen Callback."""
        handler = self.callbacks.get("image")
        if handler:
            handler(image_path)

    def _emit_overlay(self, boxes: list) -> None:
        """Sendet Overlay-Informationen an einen optionalen Callback."""
        handler = self.callbacks.get("overlay")
        if handler:
            handler(boxes)

    def _emit_file_processed(self, file_path: str) -> None:
        """Meldet eine fertig verarbeitete Datei an einen optionalen Callback."""
        handler = self.callbacks.get("file_processed")
        if handler:
            handler(file_path)


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
