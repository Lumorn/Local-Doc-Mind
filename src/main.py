"""Startpunkt fuer Local-Doc-Mind."""

from __future__ import annotations

import importlib.util
import queue
import re
import subprocess
import sys
from pathlib import Path
from importlib import metadata


# Stellt sicher, dass der Projektpfad und der src-Ordner fuer direkte Starts verfuegbar sind.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if path.exists() and str(path) not in sys.path:
        sys.path.insert(0, str(path))

from src.core.config import Config
from src.core.model_manager import ModelManager
from src.core.pipeline import ProcessingPipeline
from src.core.watcher import FileWatcher


def _extract_requirement_name(line: str) -> str | None:
    """Extrahiert den Paketnamen aus einer requirements-Zeile."""
    cleaned = line.split("#", 1)[0].strip()
    if not cleaned:
        return None
    cleaned = cleaned.split(";", 1)[0].strip()
    if not cleaned:
        return None
    name = re.split(r"[<>=!~ ]", cleaned, maxsplit=1)[0].strip()
    if "[" in name:
        name = name.split("[", 1)[0].strip()
    return name or None


def _find_missing_requirements(requirements_path: Path) -> list[str]:
    """Sammelt fehlende Pakete aus der requirements-Datei."""
    missing: list[str] = []
    if not requirements_path.exists():
        return missing
    for line in requirements_path.read_text(encoding="utf-8").splitlines():
        name = _extract_requirement_name(line)
        if not name:
            continue
        try:
            metadata.version(name)
        except metadata.PackageNotFoundError:
            missing.append(name)
    return missing


def _install_requirements(requirements_path: Path, missing: list[str]) -> None:
    """Installiert fehlende Abhaengigkeiten via pip."""
    missing_list = ", ".join(missing)
    print(f"Fehlende Abhaengigkeiten gefunden ({missing_list}). Installation wird gestartet...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(requirements_path)],
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        print(
            "Installation der Abhaengigkeiten ist fehlgeschlagen. Bitte pruefe die Ausgabe "
            "und fuehre 'pip install -r requirements.txt' manuell aus."
        )
        raise SystemExit(1) from exc


def main() -> None:
    """Startet die GUI samt Watcher und Processing-Pipeline."""
    # Prueft beim Start alle Abhaengigkeiten und installiert fehlende Pakete automatisch nach.
    requirements_path = PROJECT_ROOT / "requirements.txt"
    missing = _find_missing_requirements(requirements_path)
    if missing:
        _install_requirements(requirements_path, missing)

    # Prueft, ob PyQt6 installiert ist, damit die Anwendung eine klare Meldung ausgeben kann.
    if importlib.util.find_spec("PyQt6") is None:
        print(
            "PyQt6 ist nicht installiert. Bitte installiere es mit: "
            "pip install -r requirements.txt oder starte unter Windows start.bat."
        )
        sys.exit(1)

    from PyQt6.QtWidgets import QApplication
    # GUI-Imports erst nach dem PyQt6-Check, damit fehlende Abhaengigkeiten sauber abgefangen werden.
    from src.gui.main_window import MainWindow, apply_dark_theme
    from src.gui.workers import PipelineWorker
    config_path = Path(__file__).resolve().parents[1] / "config" / "settings.yaml"
    settings = Config(config_path)
    settings.set_runtime_value("queue", queue.Queue())

    app = QApplication(sys.argv)
    apply_dark_theme(app)

    model_manager = ModelManager.instance()
    _ = model_manager.get_device()

    window = MainWindow(settings)
    pipeline = ProcessingPipeline(settings, model_manager)
    worker = PipelineWorker(pipeline)
    watcher = FileWatcher(settings.get("paths", {}).get("input", "./input"), settings.get("queue"))

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
