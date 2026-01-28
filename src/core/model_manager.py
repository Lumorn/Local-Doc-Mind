"""ModelManager fuer das Speichermanagement der KI-Modelle."""

from __future__ import annotations

import gc
import importlib.util
import logging
import warnings
from typing import Dict

import torch
from transformers import AutoModel, BitsAndBytesConfig

logger = logging.getLogger(__name__)


class ModelManager:
    """Singleton-Manager fuer das Lazy-Loading und Unloading von Modellen."""

    _instance: "ModelManager | None" = None

    def __new__(cls) -> "ModelManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_state()
        return cls._instance

    @classmethod
    def instance(cls) -> "ModelManager":
        """Gibt die Singleton-Instanz zurueck."""
        return cls()

    def _init_state(self) -> None:
        # Interner Zustand fuer geladene Modelle.
        self.models: Dict[str, torch.nn.Module] = {}
        self.model_ids = {
            "ocr": "deepseek-ai/DeepSeek-OCR-2",
            "embedding": "sentence-transformers/all-MiniLM-L6-v2",
            "llm": "Qwen/Qwen2.5-7B-Instruct",
        }

    def get_device(self) -> str:
        """Ermittelt das bevorzugte Geraet fuer das Laden der Modelle."""
        return "cuda" if torch.cuda.is_available() else "cpu"

    def get_model(self, model_type: str) -> torch.nn.Module:
        """Alias fuer load_model, um bestehende Aufrufe zu unterstuetzen."""
        resolved_id = self.model_ids.get(model_type, model_type)
        return self.load_model(resolved_id)

    def _has_flash_attn(self) -> bool:
        # Prueft, ob flash_attn installiert ist.
        return importlib.util.find_spec("flash_attn") is not None

    def load_model(self, model_id: str) -> torch.nn.Module:
        """Laedt DeepSeek-OCR-2 mit speichersparenden Einstellungen."""
        if model_id in self.models:
            return self.models[model_id]

        if model_id != "deepseek-ai/DeepSeek-OCR-2":
            logger.warning(
                "Unerwartetes Modell angefragt (%s), lade trotzdem via transformers.",
                model_id,
            )

        if torch.cuda.is_available():
            free_bytes, _ = torch.cuda.mem_get_info()
            if free_bytes < 2 * 1024**3:
                logger.warning("VRAM knapp, entlade bestehende Modelle.")
                self.unload_all()

        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
        )

        if self._has_flash_attn():
            attn_implementation = "flash_attention_2"
        else:
            attn_implementation = "eager"
            warnings.warn(
                "flash_attn ist nicht installiert; nutze eager Attention fuer bessere "
                "Windows-Kompatibilitaet.",
                RuntimeWarning,
            )

        logger.info("Lade Modell %s mit Attention=%s.", model_id, attn_implementation)
        model = AutoModel.from_pretrained(
            model_id,
            device_map="auto" if torch.cuda.is_available() else None,
            quantization_config=quantization_config,
            torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
            attn_implementation=attn_implementation,
        )

        self.models[model_id] = model
        return model

    def unload_model(self, model_id: str) -> None:
        """Entlaedt ein bestimmtes Modell und gibt Speicher frei."""
        if model_id in self.models:
            logger.info("Entlade Modell %s.", model_id)
            del self.models[model_id]
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    def unload_all(self) -> None:
        """Entlaedt alle Modelle auf einmal."""
        for model_id in list(self.models.keys()):
            self.unload_model(model_id)
