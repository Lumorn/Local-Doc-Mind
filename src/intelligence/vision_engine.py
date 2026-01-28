"""DeepSeek-OCR-2 Wrapper fuer die visuelle Dokumentenverarbeitung."""

from __future__ import annotations

import gc
import logging
from pathlib import Path
from typing import List

import torch
from PIL import Image
from transformers import AutoProcessor

from src.core.model_manager import ModelManager
from src.utils.image_processing import pdf_to_images

logger = logging.getLogger(__name__)

_OCR_PROMPT = "<image>\n<|grounding|>Convert the document to markdown."


class VisionEngine:
    """Stellt die OCR-Schnittstelle fuer DeepSeek-OCR-2 bereit."""

    _OCR_PROMPT = _OCR_PROMPT

    def __init__(self, model_id: str = "deepseek-ai/DeepSeek-OCR-2") -> None:
        self._model_manager = ModelManager.instance()
        self._model_id = model_id
        self._processor = AutoProcessor.from_pretrained(model_id)
        # Standardordner fuer OCR-Outputs, falls das Modell einen Ablagepfad erwartet.
        self._output_dir = Path("output") / "ocr_cache"

    def process_document(self, file_path: str) -> str:
        """Fuehrt OCR auf allen PDF-Seiten aus und liefert Markdown zurueck."""
        logger.info("Starte OCR fuer Datei %s", file_path)
        markdown_parts: List[str] = []

        images = pdf_to_images(file_path)
        try:
            for page_index, image in enumerate(images, start=1):
                logger.info("Seite %d wird verarbeitet...", page_index)
                try:
                    markdown = self._run_inference_with_retry(image)
                finally:
                    # Bild sofort freigeben, um Speicher zu sparen.
                    del image
                    # Nach jeder Seite aktiv aufraeumen, um RAM/VRAM zu entlasten.
                    gc.collect()
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                markdown_parts.append(markdown)
                logger.info("Seite %d verarbeitet.", page_index)
        finally:
            # Generator freigeben, um Speicher zu sparen.
            del images
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

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
        model = self._model_manager.load_model(self._model_id)

        if hasattr(model, "infer"):
            result = self._call_model_infer(model, image)
            return self._normalize_result(result)

        inputs = self._processor(text=self._OCR_PROMPT, images=image, return_tensors="pt")
        device = next(model.parameters()).device
        inputs = {key: value.to(device) for key, value in inputs.items()}

        with torch.inference_mode():
            outputs = model.generate(**inputs, max_new_tokens=2048)

        text = self._processor.batch_decode(outputs, skip_special_tokens=True)
        del inputs
        del outputs
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        return "\n".join(text)

    def _ensure_output_dir(self) -> Path:
        """Stellt sicher, dass der OCR-Output-Ordner existiert."""
        self._output_dir.mkdir(parents=True, exist_ok=True)
        return self._output_dir

    def _call_model_infer(self, model: torch.nn.Module, image: Image.Image) -> object:
        """Ruft model.infer mit einem festen Keyword-Call auf."""
        output_kwargs = {"output_path": str(self._ensure_output_dir())}
        images_payload = [image]
        logger.debug(
            "OCR infer Aufruf: images_typ=%s, image_typ=%s, images_ist_liste=%s",
            type(images_payload).__name__,
            type(image).__name__,
            isinstance(images_payload, list),
        )
        try:
            return model.infer(images=images_payload, prompt=self._OCR_PROMPT, **output_kwargs)
        except (IndexError, AttributeError) as exc:
            raise RuntimeError("Modell erwartet Liste, erhielt Einzelobjekt") from exc
        except TypeError:
            # Falls das Modell keine Output-Pfade akzeptiert, erneut ohne Pfadangabe versuchen.
            try:
                return model.infer(images=images_payload, prompt=self._OCR_PROMPT)
            except (IndexError, AttributeError) as exc:
                raise RuntimeError("Modell erwartet Liste, erhielt Einzelobjekt") from exc

    @staticmethod
    def _normalize_result(result: object) -> str:
        """Normalisiert verschiedene Rueckgabeformate des Modells."""
        if isinstance(result, list):
            return "\n".join(str(part) for part in result)
        return str(result)
