"""Modul fuer das Zerlegen von gescannten Stapel-PDFs."""

from __future__ import annotations

import io
import json
import logging
import os
import re
import tempfile
from typing import Any, List

import fitz
from PIL import Image
from transformers import AutoTokenizer

from src.core.model_manager import ModelManager

logger = logging.getLogger(__name__)

_JSON_PATTERN = re.compile(r"\{.*\}", re.DOTALL)


def _parse_continuity(result: Any) -> bool:
    """Extrahiert das JSON-Flag fuer Kontinuitaet aus der Modellantwort."""
    if isinstance(result, dict) and "continuous" in result:
        return bool(result["continuous"])
    text = result if isinstance(result, str) else str(result)
    match = _JSON_PATTERN.search(text)
    if not match:
        raise ValueError("Kein JSON in der Modellantwort gefunden.")
    payload = json.loads(match.group(0))
    if "continuous" not in payload:
        raise ValueError("JSON enthaelt kein Feld 'continuous'.")
    return bool(payload["continuous"])


def _stitch_sections(bottom: Image.Image, top: Image.Image) -> Image.Image:
    """Fuegt zwei Bildausschnitte vertikal zusammen."""
    width = max(bottom.width, top.width)
    height = bottom.height + top.height
    canvas = Image.new("RGB", (width, height), color=(255, 255, 255))
    canvas.paste(top, (0, 0))
    canvas.paste(bottom, (0, top.height))
    return canvas


def scan_for_splits(pdf_path: str) -> List[str]:
    """Scannt ein PDF nach Dokumentgrenzen und speichert die Teile separat."""
    logger.info("Starte Split-Scan fuer %s.", pdf_path)
    manager = ModelManager.instance()
    model = manager.get_model("ocr")
    model_id = manager.model_ids["ocr"]
    tokenizer = AutoTokenizer.from_pretrained(model_id)

    split_points: List[int] = []
    temp_images: List[str] = []

    with fitz.open(pdf_path) as doc:
        if doc.page_count == 0:
            logger.warning("PDF %s enthaelt keine Seiten.", pdf_path)
            return []

        for page_index in range(doc.page_count - 1):
            page = doc.load_page(page_index)
            next_page = doc.load_page(page_index + 1)
            pixmap = page.get_pixmap()
            next_pixmap = next_page.get_pixmap()

            image = Image.open(io.BytesIO(pixmap.tobytes("png")))
            next_image = Image.open(io.BytesIO(next_pixmap.tobytes("png")))

            bottom_crop_start = int(image.height * 0.8)
            top_crop_end = int(next_image.height * 0.2)

            bottom_section = image.crop((0, bottom_crop_start, image.width, image.height))
            top_section = next_image.crop((0, 0, next_image.width, top_crop_end))

            stitched = _stitch_sections(bottom_section, top_section)
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
                stitched_path = tmp_file.name
            stitched.save(stitched_path)
            temp_images.append(stitched_path)
            logger.debug("Stitching-Bild erstellt: %s.", stitched_path)

            prompt = (
                "<image>\nDoes the text or layout flow logically from the top part "
                "to the bottom part? Reply ONLY JSON: {\"continuous\": true/false}"
            )

            result = model.infer(tokenizer, prompt=prompt, image_file=stitched_path)
            try:
                continuous = _parse_continuity(result)
            except (ValueError, json.JSONDecodeError) as exc:
                logger.warning(
                    "Antwort fuer Seite %s konnte nicht geparst werden: %s.",
                    page_index + 1,
                    exc,
                )
                continuous = True

            if not continuous:
                split_points.append(page_index)
                logger.info("Split erkannt bei Seite %s.", page_index + 1)

    for temp_path in temp_images:
        if os.path.exists(temp_path):
            os.remove(temp_path)
            logger.debug("Temporäres Stitching-Bild entfernt: %s.", temp_path)

    output_dir = tempfile.mkdtemp(prefix="doc_splits_")
    part_paths: List[str] = []

    with fitz.open(pdf_path) as doc:
        start_page = 0
        for part_index, split_page in enumerate(split_points + [doc.page_count - 1], start=1):
            part_doc = fitz.open()
            part_doc.insert_pdf(doc, from_page=start_page, to_page=split_page)
            part_path = os.path.join(output_dir, f"part_{part_index}.pdf")
            part_doc.save(part_path)
            part_doc.close()
            part_paths.append(part_path)
            logger.info("Teil %s gespeichert: %s.", part_index, part_path)
            start_page = split_page + 1

    logger.info("Split-Scan abgeschlossen fuer %s.", pdf_path)
    return part_paths
