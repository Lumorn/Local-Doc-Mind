"""Datei-Watcher fuer neue Dokumente."""

from __future__ import annotations

import logging
import threading
import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

logger = logging.getLogger(__name__)


class FileWatcher:
    """Ueberwacht rekursiv einen Ordner und legt fertige Dateien in eine Queue."""

    def __init__(self, input_path: str | Path, queue) -> None:
        # Pfad und Queue fuer die Verarbeitung merken.
        self.input_path = Path(input_path)
        self.queue = queue
        self._observer = Observer()
        self._handler = _DebouncedCreateHandler(self.queue)

    def start(self) -> None:
        """Startet den Dateisystem-Observer."""
        self.input_path.mkdir(parents=True, exist_ok=True)
        self._observer.schedule(self._handler, str(self.input_path), recursive=True)
        self._observer.start()
        logger.info("Dateiueberwachung gestartet: %s", self.input_path)

    def stop(self) -> None:
        """Stoppt den Observer sauber."""
        self._observer.stop()
        self._observer.join()
        logger.info("Dateiueberwachung gestoppt: %s", self.input_path)


class _DebouncedCreateHandler(FileSystemEventHandler):
    """Handler fuer Debouncing bei neu angelegten Dateien."""

    def __init__(self, queue) -> None:
        # Queue zum Einreihen fertiger Dateien.
        self.queue = queue

    def on_created(self, event) -> None:
        """Reagiert auf neue Dateien."""
        if event.is_directory:
            return

        path = Path(event.src_path)
        if _is_temporary_file(path):
            logger.debug("Temporaere Datei ignoriert: %s", path)
            return

        if path.suffix.lower() != ".pdf":
            logger.debug("Nicht-PDF ignoriert: %s", path)
            return

        threading.Thread(
            target=self._debounce_and_enqueue,
            args=(path,),
            daemon=True,
        ).start()

    def _debounce_and_enqueue(self, path: Path) -> None:
        """Wartet auf stabile Dateigroesse und legt den Pfad in die Queue."""
        logger.info("Datei erkannt: %s", path)
        time.sleep(1)

        last_size: int | None = None
        stable_checks = 0

        for attempt in range(1, 11):
            if not path.exists():
                logger.warning("Datei nicht mehr vorhanden: %s", path)
                return

            try:
                current_size = path.stat().st_size
            except OSError as exc:
                logger.warning("Datei konnte nicht gelesen werden (%s): %s", exc, path)
                time.sleep(1)
                continue

            if last_size is not None and current_size == last_size:
                stable_checks += 1
            else:
                stable_checks = 0

            if stable_checks >= 1:
                logger.info("Datei stabil, in Queue: %s", path)
                self.queue.put(str(path))
                return

            last_size = current_size
            logger.debug(
                "Dateigroesse noch instabil (Versuch %d/10): %s", attempt, path
            )
            time.sleep(1)

        logger.warning("Datei blieb instabil, uebersprungen: %s", path)


def _is_temporary_file(path: Path) -> bool:
    """Prueft, ob es sich um eine temporaere Datei handelt."""
    name = path.name
    return name.startswith(".") or name.startswith("~")
