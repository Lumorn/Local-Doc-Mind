"""Worker-Thread fuer die GUI-Integration."""

from __future__ import annotations

from typing import Callable

from PIL import Image
from PyQt6.QtCore import QThread, pyqtSignal

from src.core.pipeline import ProcessingPipeline


class PipelineWorker(QThread):
    """Fuehrt die Processing-Pipeline in einem GUI-kompatiblen Thread aus."""

    new_log = pyqtSignal(str)
    update_image = pyqtSignal(str)
    update_overlay = pyqtSignal(list)
    file_processed = pyqtSignal(str)

    def __init__(self, pipeline: ProcessingPipeline) -> None:
        super().__init__()
        # Pipeline merken, damit wir sie im Thread starten koennen.
        self.pipeline = pipeline
        self._callbacks_registered = False

    def run(self) -> None:
        """Startet die Pipeline und leitet Statusmeldungen an die GUI weiter."""
        self._register_callbacks()
        self.pipeline.run()

    def stop(self) -> None:
        """Stoppt die Pipeline kontrolliert."""
        self.pipeline.stop()

    def _register_callbacks(self) -> None:
        """Bindet GUI-Signale als Callback-Ziele an die Pipeline."""
        if self._callbacks_registered:
            return

        callbacks: dict[str, Callable] = {
            "log": self.new_log.emit,
            "image": self.update_image.emit,
            "overlay": self.update_overlay.emit,
            "file_processed": self.file_processed.emit,
        }

        if hasattr(self.pipeline, "set_callbacks"):
            self.pipeline.set_callbacks(callbacks)
        else:
            # Fallback, falls die Pipeline keine Callback-Funktion kennt.
            self.pipeline.callbacks = callbacks

        self._callbacks_registered = True
        _ = Image
