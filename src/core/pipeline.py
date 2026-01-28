"""OCR-Orchestrator fuer die Dokumentenverarbeitung."""

from __future__ import annotations

import hashlib
import logging
import shutil
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import torch

from src.intelligence.vision_engine import VisionEngine

logger = logging.getLogger(__name__)


@dataclass
class DocumentPipeline:
    """Orchestriert Backup, OCR und Output-Handling fuer Dokumente."""

    backup_root: Path = Path("backup")
    output_root: Path = Path("output")

    def process(self, file_path: str) -> Path:
        """Validiert, erstellt Backup, fuehrt OCR aus und speichert Markdown."""
        path = Path(file_path)
        if not path.exists():
            logger.error("Datei nicht gefunden: %s", path)
            raise FileNotFoundError(f"Datei nicht gefunden: {path}")

        logger.info("Starte Backup fuer Datei: %s", path.name)
        backup_path = self._create_backup(path)
        if not self._verify_backup(path, backup_path):
            raise RuntimeError(f"Backup-Integritaet fehlgeschlagen: {path.name}")

        logger.info("Starte OCR fuer Datei: %s", path.name)
        engine = VisionEngine()
        markdown = engine.process_document(str(path))
        del engine

        output_path = self._write_output(path, markdown)
        del markdown
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        logger.info("OCR abgeschlossen: %s", output_path)
        return output_path

    def _create_backup(self, file_path: Path) -> Path:
        """Erstellt ein Backup der Datei im datierten Ordner."""
        date_folder = self.backup_root / date.today().isoformat()
        date_folder.mkdir(parents=True, exist_ok=True)
        backup_path = date_folder / file_path.name
        shutil.copy2(file_path, backup_path)
        return backup_path

    def _verify_backup(self, source_path: Path, backup_path: Path) -> bool:
        """Prueft die Integritaet des Backups via SHA256."""
        source_hash = self._calculate_sha256(source_path)
        backup_hash = self._calculate_sha256(backup_path)
        logger.debug("SHA256 Quelle: %s", source_hash)
        logger.debug("SHA256 Backup: %s", backup_hash)
        return source_hash == backup_hash

    def _calculate_sha256(self, file_path: Path) -> str:
        """Berechnet den SHA256-Hash fuer eine Datei."""
        sha256 = hashlib.sha256()
        with file_path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _write_output(self, source_path: Path, markdown: str) -> Path:
        """Schreibt das OCR-Ergebnis in den Output-Ordner."""
        self.output_root.mkdir(parents=True, exist_ok=True)
        output_name = f"{source_path.stem}_ocr.md"
        output_path = self.output_root / output_name
        output_path.write_text(markdown, encoding="utf-8")
        return output_path
