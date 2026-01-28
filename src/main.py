"""Startpunkt fuer Local-Doc-Mind."""

from __future__ import annotations

import importlib.util
import queue
import sys
from pathlib import Path

import yaml

# Stellt sicher, dass der Projektpfad und der src-Ordner fuer direkte Starts verfuegbar sind.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if path.exists() and str(path) not in sys.path:
        sys.path.insert(0, str(path))

from src.core.model_manager import ModelManager
from src.core.pipeline import ProcessingPipeline
from src.core.watcher import FileWatcher


def load_settings(config_path: Path) -> dict:
    """Lade die Konfiguration aus einer YAML-Datei."""
    # Wenn die Datei fehlt, geben wir eine leere Konfiguration zurueck.
    if not config_path.exists():
        print(f"Konfigurationsdatei nicht gefunden: {config_path}")
        return {}

    with config_path.open("r", encoding="utf-8") as config_file:
        return yaml.safe_load(config_file) or {}


def main() -> None:
    """Startet die GUI samt Watcher und Processing-Pipeline."""
    # Prueft, ob PyQt6 installiert ist, damit die Anwendung eine klare Meldung ausgeben kann.
    if importlib.util.find_spec("PyQt6") is None:
        print("PyQt6 ist nicht installiert. Bitte installiere es mit: pip install PyQt6")
        sys.exit(1)

    from PyQt6.QtWidgets import QApplication
    # GUI-Imports erst nach dem PyQt6-Check, damit fehlende Abhaengigkeiten sauber abgefangen werden.
    from src.gui.main_window import MainWindow, apply_dark_theme
    from src.gui.workers import PipelineWorker
    config_path = Path(__file__).resolve().parents[1] / "config" / "settings.yaml"
    settings = load_settings(config_path)
    settings["config_path"] = str(config_path)
    settings["queue"] = queue.Queue()

    app = QApplication(sys.argv)
    apply_dark_theme(app)

    model_manager = ModelManager.instance()
    _ = model_manager.get_device()

    window = MainWindow(settings)
    pipeline = ProcessingPipeline(settings, model_manager)
    worker = PipelineWorker(pipeline)
    watcher = FileWatcher(settings.get("paths", {}).get("input", "./input"), settings["queue"])

    window.attach_worker(worker)

    watcher_started = {"value": False}

    def start_processing() -> None:
        # Startet Watcher und Pipeline-Thread.
        if not watcher_started["value"]:
            watcher.start()
            watcher_started["value"] = True
        if not worker.isRunning():
            worker.start()
        window.append_log("Watchdog gestartet und Pipeline laeuft.")

    def stop_processing() -> None:
        # Stoppt Watcher und Pipeline-Thread.
        if watcher_started["value"]:
            watcher.stop()
            watcher_started["value"] = False
        if worker.isRunning():
            worker.stop()
            worker.wait(2000)
        window.append_log("Watchdog und Pipeline gestoppt.")

    window.start_watchdog_requested.connect(start_processing)
    window.stop_watchdog_requested.connect(stop_processing)

    def shutdown() -> None:
        # Sorgt fuer ein sauberes Herunterfahren aller Threads.
        stop_processing()

    app.aboutToQuit.connect(shutdown)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
