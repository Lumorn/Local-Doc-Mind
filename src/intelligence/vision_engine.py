"""DeepSeek-OCR-2 Wrapper fuer die visuelle Dokumentenverarbeitung."""

from __future__ import annotations

import gc
import logging
from typing import List

import fitz
import torch
from PIL import Image

from src.core.model_manager import ModelManager
from src.utils.image_processing import pdf_page_to_image

logger = logging.getLogger(__name__)

_OCR_PROMPT = "<image>\n<|grounding|>Convert the document to markdown."


class VisionEngine:
    """Stellt die OCR-Schnittstelle fuer DeepSeek-OCR-2 bereit."""

    def __init__(self) -> None:
        self._model_manager = ModelManager.instance()

    def process_document(self, pdf_path: str) -> str:
        """Fuehrt OCR auf allen PDF-Seiten aus und liefert Markdown zurueck."""
        logger.info("Starte OCR fuer Datei %s", pdf_path)
        markdown_parts: List[str] = []

        with fitz.open(pdf_path) as document:
            for page_index, page in enumerate(document, start=1):
                logger.info("Seite %d wird verarbeitet...", page_index)
                image = pdf_page_to_image(page)
                try:
                    markdown = self._run_inference_with_retry(image)
                finally:
                    # Bild sofort freigeben, um Speicher zu sparen.
                    del image
                markdown_parts.append(markdown)
                logger.info("Seite %d verarbeitet.", page_index)

        return "\n\n".join(markdown_parts)

    def _run_inference_with_retry(self, image: Image.Image) -> str:
        """Fuehrt die OCR-Inferenz aus und behandelt CUDA-OOM Fehler."""
        try:
            return self._run_inference(image)
        except RuntimeError as exc:
            if "CUDA out of memory" not in str(exc):
                raise
            logger.warning("CUDA OOM erkannt, versuche Bereinigung und Neustart.")
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            return self._run_inference(image)

    def _run_inference(self, image: Image.Image) -> str:
        """Ruft das DeepSeek-OCR-2 Modell auf und gibt Markdown zurueck."""
        model = self._model_manager.get_model("ocr")
        result = None

        if hasattr(model, "infer"):
            try:
                result = model.infer(_OCR_PROMPT, images=[image])
            except TypeError:
                result = model.infer(prompt=_OCR_PROMPT, images=[image])
        else:
            raise RuntimeError("OCR-Modell unterstuetzt keine infer-Methode.")

        if isinstance(result, list):
            return "\n".join(str(part) for part in result)
        return str(result)
