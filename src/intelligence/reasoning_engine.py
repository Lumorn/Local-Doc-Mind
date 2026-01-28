"""Reasoning-Schicht fuer Dateinamen und Ablage."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List

import torch
from transformers import AutoTokenizer

from src.core.model_manager import ModelManager

logger = logging.getLogger(__name__)


class ReasoningEngine:
    """Fuehrt LLM-Inferenz fuer Zusammenfassung und Sortierung aus."""

    def __init__(self) -> None:
        self._model_manager = ModelManager.instance()
        self._model_id = self._model_manager.model_ids["llm"]
        self._tokenizer = AutoTokenizer.from_pretrained(self._model_id)

    def analyze_and_sort(self, ocr_text: str, history_context: str) -> Dict[str, Any]:
        """Analysiert OCR-Text und liefert Summary, Dateiname und Zielordner."""
        # Erzwinge das Umschalten auf das LLM, um VRAM sauber zu halten.
        self._model_manager.switch_to("llm")
        messages = self._build_prompt(ocr_text, history_context)
        for attempt in range(2):
            response_text = self._run_inference(messages)
            try:
                parsed = self._parse_json(response_text)
                if not isinstance(parsed, dict):
                    raise json.JSONDecodeError("Kein JSON-Objekt", response_text, 0)
                return parsed
            except json.JSONDecodeError:
                logger.warning("JSON-Parsing fehlgeschlagen (Versuch %d).", attempt + 1)
                messages = self._build_prompt(
                    ocr_text,
                    history_context,
                    extra_instruction="Antworte ausschliesslich mit rohem JSON ohne Markdown.",
                )
        logger.error("LLM lieferte kein parsebares JSON, verwende Fallback.")
        return self._fallback_decision(ocr_text)

    def _run_inference(self, messages: List[dict]) -> str:
        """Fuehrt die LLM-Inferenz mit dem Chat-Template aus."""
        model = self._model_manager.switch_to("llm")
        prompt = self._tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        inputs = self._tokenizer(prompt, return_tensors="pt")
        device = next(model.parameters()).device
        inputs = {key: value.to(device) for key, value in inputs.items()}

        with torch.inference_mode():
            outputs = model.generate(
                **inputs,
                max_new_tokens=512,
                do_sample=False,
            )

        generated_tokens = outputs[0][inputs["input_ids"].shape[-1] :]
        response = self._tokenizer.decode(generated_tokens, skip_special_tokens=True)
        return response.strip()

    def _build_prompt(
        self,
        ocr_text: str,
        history_context: str,
        extra_instruction: str | None = None,
    ) -> List[dict]:
        """Erstellt das Chat-Prompt fuer Qwen 2.5."""
        system_prompt = (
            "Du bist ein praeziser Dokumenten-Archivar. Deine Aufgabe ist es, basierend auf dem "
            "Inhalt und der Historie einen Dateinamen und einen Zielordner zu bestimmen. "
            "Antworte AUSSCHLIESSLICH mit validem JSON."
        )
        user_prompt = (
            "DOKUMENT TEXT: {ocr_text}\n\n"
            "HISTORISCHE ENTSCHEIDUNGEN (Beispiele): {history_context}\n\n"
            "AUFGABE:\n\n"
            "Fasse den Inhalt in 1 Satz zusammen (summary).\n\n"
            "Generiere einen Dateinamen nach dem Muster der Historie (filename).\n\n"
            "Waehle/Erstelle einen passenden Zielordner (folder).\n\n"
            'OUTPUT JSON SCHEMA: {{"summary": "...", "filename": "YYYY-MM-DD_Name.pdf", '
            '"folder": "Kategorie/Unterkategorie"}}'
        ).format(ocr_text=ocr_text, history_context=history_context)

        if extra_instruction:
            user_prompt = f"{user_prompt}\n{extra_instruction}"

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def _parse_json(self, response_text: str) -> Dict[str, Any]:
        """Parst das JSON aus der LLM-Antwort robust mit Markdown-Strip."""
        cleaned = response_text.strip()

        fenced_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
        if fenced_match:
            cleaned = fenced_match.group(1).strip()
        else:
            brace_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if brace_match:
                cleaned = brace_match.group(0).strip()

        return json.loads(cleaned)

    def _fallback_decision(self, ocr_text: str) -> Dict[str, Any]:
        """Erzeugt eine konservative Fallback-Antwort, falls das LLM scheitert."""
        summary = ocr_text.strip().splitlines()[0] if ocr_text.strip() else "Keine Zusammenfassung verfuegbar."
        return {
            "summary": summary[:200],
            "filename": "Unbekannt.pdf",
            "folder": "Unsortiert",
        }
