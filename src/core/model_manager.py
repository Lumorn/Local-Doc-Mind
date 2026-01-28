"""ModelManager fuer das Speichermanagement der KI-Modelle."""

from __future__ import annotations

import gc
from typing import Dict

import torch
from transformers import AutoModel, BitsAndBytesConfig


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
        # Ermittelt das bevorzugte Geraet fuer das Laden der Modelle.
        return "cuda" if torch.cuda.is_available() else "cpu"

    def load_model(self, model_type: str) -> torch.nn.Module:
        """Laedt ein Modell lazy und gibt die Instanz zurueck."""
        if model_type in self.models:
            return self.models[model_type]

        if torch.cuda.is_available():
            free_bytes, _ = torch.cuda.mem_get_info()
            if free_bytes < 2 * 1024**3:
                print("VRAM knapp, entlade alle Modelle.")
                self.unload_all()

        model_id = self.model_ids.get(model_type)
        if not model_id:
            raise ValueError(f"Unbekannter Modelltyp: {model_type}")

        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.bfloat16
            if torch.cuda.is_available()
            else torch.float16,
        )

        print(f"Lade Modell '{model_type}' ({model_id}).")
        model = AutoModel.from_pretrained(
            model_id,
            device_map="auto" if torch.cuda.is_available() else None,
            quantization_config=quantization_config,
            torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
        )

        self.models[model_type] = model
        return model

    def get_model(self, model_type: str) -> torch.nn.Module:
        """Alias fuer load_model, damit externe Module konsistent bleiben."""
        return self.load_model(model_type)

    def unload_model(self, model_type: str) -> None:
        """Entlaedt ein bestimmtes Modell und gibt Speicher frei."""
        if model_type in self.models:
            print(f"Entlade Modell '{model_type}'.")
            del self.models[model_type]
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    def unload_all(self) -> None:
        """Entlaedt alle Modelle auf einmal."""
        for model_type in list(self.models.keys()):
            self.unload_model(model_type)
