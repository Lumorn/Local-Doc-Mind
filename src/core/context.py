"""Kontextmodul fuer das Langzeitgedaechtnis."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class ContextManager:
    """Verwaltet den Kontext in Form einer .ai_context.md Datei."""

    def __init__(self, filename: str = ".ai_context.md") -> None:
        # Dateinamen fuer den Kontext merken.
        self.filename = filename

    def get_context(self, folder_path: str | Path) -> str:
        """Liest den Kontext aus dem angegebenen Ordner."""
        context_path = Path(folder_path) / self.filename
        if not context_path.exists():
            logger.debug("Kein Kontext gefunden unter %s.", context_path)
            return ""

        try:
            content = context_path.read_text(encoding="utf-8")
        except OSError as exc:
            logger.warning("Kontext konnte nicht gelesen werden (%s): %s", exc, context_path)
            return ""

        logger.debug("Kontext geladen aus %s.", context_path)
        return content

    def update_context(self, folder_path: str | Path, content: str) -> None:
        """Schreibt oder aktualisiert den Kontext im Zielordner."""
        context_path = Path(folder_path) / self.filename
        context_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            context_path.write_text(content, encoding="utf-8")
        except OSError as exc:
            logger.error("Kontext konnte nicht geschrieben werden (%s): %s", exc, context_path)
            return

        logger.info("Kontext aktualisiert unter %s.", context_path)
