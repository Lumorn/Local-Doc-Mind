"""Analysemodul fuer OCR und Inhaltsgewinnung."""

from __future__ import annotations

import logging
import os
import tempfile
from typing import Any

import fitz
from transformers import AutoTokenizer

from src.core.model_manager import ModelManager

logger = logging.getLogger(__name__)


def _extract_markdown(result: Any) -> str:
    """Versucht, den Markdown-Text aus dem Modellresultat zu extrahieren."""
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        for key in ("text", "markdown", "output", "result"):
            value = result.get(key)
            if isinstance(value, str):
                return value
    return str(result)


def analyze_document(pdf_path: str) -> str:
    """Analysiert die erste Seite eines PDFs per DeepSeek-OCR-2."""
    logger.info("Starte OCR-Analyse fuer %s.", pdf_path)
    manager = ModelManager.instance()
    model = manager.get_model("ocr")
    model_id = manager.model_ids["ocr"]
    tokenizer = AutoTokenizer.from_pretrained(model_id)

    image_path = None
    try:
        with fitz.open(pdf_path) as doc:
            if doc.page_count == 0:
                logger.warning("PDF %s enthaelt keine Seiten.", pdf_path)
                return ""
            page = doc.load_page(0)
            pixmap = page.get_pixmap()

            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
                image_path = tmp_file.name
            pixmap.save(image_path)
            logger.debug("OCR-Bild gespeichert unter %s.", image_path)

        result = model.infer(
            tokenizer,
            prompt="<image>\n<|grounding|>Convert the document to markdown.",
            image_file=image_path,
        )
        markdown = _extract_markdown(result)
        logger.info("OCR-Analyse abgeschlossen fuer %s.", pdf_path)
        return markdown
    finally:
        if image_path and os.path.exists(image_path):
            os.remove(image_path)
            logger.debug("Temporäre Bilddatei %s entfernt.", image_path)
