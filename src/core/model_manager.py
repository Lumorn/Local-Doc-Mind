"""ModelManager fuer das Speichermanagement der KI-Modelle."""

from __future__ import annotations

import gc
import importlib.util
import logging
import warnings
from typing import Dict, Optional

import torch
from sentence_transformers import SentenceTransformer
from transformers import AutoModel, AutoModelForCausalLM, BitsAndBytesConfig

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
        self.current_model: Optional[torch.nn.Module] = None
        self.current_type: Optional[str] = None
        self.embedding_model: Optional[SentenceTransformer] = None
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
        if model_type in self.model_ids:
            if model_type == "embedding":
                return self.get_embedding_model()
            return self.switch_to(model_type)
        return self.load_model(model_type)

    def switch_to(self, model_type: str) -> torch.nn.Module:
        """Wechselt strikt zwischen OCR und LLM, um VRAM zu schonen."""
        if model_type not in ("ocr", "llm"):
            raise ValueError(f"Unbekannter Modelltyp: {model_type}")

        if self.current_type == model_type and self.current_model is not None:
            return self.current_model

        if self.current_model is not None:
            logger.info("Entlade aktuelles Modell (%s) fuer Wechsel zu %s.", self.current_type, model_type)
            if self.current_type in self.model_ids:
                self.models.pop(self.model_ids[self.current_type], None)
            del self.current_model
            self.current_model = None
            self.current_type = None
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

        # Sicherheitsnetz: falls noch andere OCR/LLM-Modelle gecacht sind, sofort entfernen.
        removed_cached = False
        for cached_type in ("ocr", "llm"):
            model_id = self.model_ids.get(cached_type)
            if model_id and model_id in self.models:
                logger.debug("Entferne Modell-Cache %s fuer striktes Swapping.", model_id)
                self.models.pop(model_id, None)
                removed_cached = True

        if removed_cached:
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

        if model_type == "ocr":
            model = self._load_ocr_model()
        else:
            model = self._load_llm_model()

        self.current_model = model
        self.current_type = model_type
        return model

    def _has_flash_attn(self) -> bool:
        # Prueft, ob flash_attn installiert ist.
        return importlib.util.find_spec("flash_attn") is not None

    def load_model(self, model_id: str) -> torch.nn.Module:
        """Laedt DeepSeek-OCR-2 mit speichersparenden Einstellungen."""
        if model_id == self.model_ids.get("embedding"):
            return self.get_embedding_model()
        if model_id == self.model_ids.get("ocr"):
            return self.switch_to("ocr")
        if model_id == self.model_ids.get("llm"):
            return self.switch_to("llm")

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

        model = AutoModel.from_pretrained(model_id)

        self.models[model_id] = model
        return model

    def get_embedding_model(self) -> SentenceTransformer:
        """Laedt das Embedding-Modell dauerhaft auf die CPU."""
        if self.embedding_model is None:
            model_id = self.model_ids["embedding"]
            logger.info("Lade Embedding-Modell %s auf der CPU.", model_id)
            self.embedding_model = SentenceTransformer(model_id, device="cpu")
        return self.embedding_model

    def _load_ocr_model(self) -> torch.nn.Module:
        """Laedt DeepSeek-OCR-2 mit speichersparenden Einstellungen."""
        model_id = self.model_ids["ocr"]
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

        logger.info("Lade OCR-Modell %s mit Attention=%s.", model_id, attn_implementation)
        model = AutoModel.from_pretrained(
            model_id,
            device_map="auto" if torch.cuda.is_available() else None,
            quantization_config=quantization_config,
            torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
            attn_implementation=attn_implementation,
        )
        self.models[model_id] = model
        return model

    def _load_llm_model(self) -> torch.nn.Module:
        """Laedt Qwen2.5-7B-Instruct in 4-bit fuer die Reasoning-Schicht."""
        model_id = self.model_ids["llm"]
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
        )
        logger.info("Lade LLM %s mit 4-bit-Quantisierung.", model_id)
        model = AutoModelForCausalLM.from_pretrained(
            model_id,
            device_map="auto" if torch.cuda.is_available() else None,
            quantization_config=quantization_config,
            torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
        )
        self.models[model_id] = model
        return model

    def unload_model(self, model_id: str) -> None:
        """Entlaedt ein bestimmtes Modell und gibt Speicher frei."""
        if model_id in self.models:
            logger.info("Entlade Modell %s.", model_id)
            del self.models[model_id]
            if self.current_model is not None and self.current_type is not None:
                if self.model_ids.get(self.current_type) == model_id:
                    self.current_model = None
                    self.current_type = None
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    def unload_all(self) -> None:
        """Entlaedt alle Modelle auf einmal."""
        for model_id in list(self.models.keys()):
            self.unload_model(model_id)
