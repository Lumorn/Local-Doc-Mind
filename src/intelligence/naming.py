"""Modul fuer RAG-gestuetzte Dateibenennung."""

from __future__ import annotations

import logging
import os
import uuid
from typing import Any, List

import chromadb
import torch
from transformers import AutoTokenizer

from src.core.model_manager import ModelManager

logger = logging.getLogger(__name__)


class NamingEngine:
    """Engine fuer Lernen und Vorschlagen von Dateinamen."""

    def __init__(self, persist_path: str | None = None) -> None:
        # Initialisiert die ChromaDB und laedt das Embedding-Modell.
        self.persist_path = persist_path or os.path.join("data", "chroma")
        os.makedirs(self.persist_path, exist_ok=True)
        self.client = chromadb.PersistentClient(path=self.persist_path)
        self.collection = self.client.get_or_create_collection("local_doc_mind")
        self.manager = ModelManager.instance()
        self.embedding_model = self.manager.get_model("embedding")
        self.embedding_model_id = self.manager.model_ids["embedding"]

    def _embed_text(self, content: str) -> List[float]:
        """Erstellt ein Embedding fuer den angegebenen Text."""
        if hasattr(self.embedding_model, "encode"):
            embedding = self.embedding_model.encode(content)
            return embedding.tolist() if hasattr(embedding, "tolist") else list(embedding)

        tokenizer = AutoTokenizer.from_pretrained(self.embedding_model_id)
        inputs = tokenizer(content, return_tensors="pt", truncation=True)
        device = (
            self.embedding_model.device
            if hasattr(self.embedding_model, "device")
            else self.manager.get_device()
        )
        inputs = {key: value.to(device) for key, value in inputs.items()}
        self.embedding_model.to(device)
        with torch.no_grad():
            outputs = self.embedding_model(**inputs)
        hidden_state = outputs.last_hidden_state
        pooled = hidden_state.mean(dim=1).squeeze(0)
        return pooled.detach().cpu().tolist()

    def learn(self, filename: str, content: str) -> None:
        """Speichert das Embedding zusammen mit Metadaten in ChromaDB."""
        embedding = self._embed_text(content)
        doc_id = str(uuid.uuid4())
        self.collection.add(
            ids=[doc_id],
            embeddings=[embedding],
            documents=[content],
            metadatas=[{"filename": filename}],
        )
        logger.info("Dokument %s in ChromaDB gespeichert.", filename)

    def suggest_name(self, content: str) -> str:
        """Schlaegt basierend auf RAG einen Dateinamen vor."""
        embedding = self._embed_text(content)
        rag_data = self.collection.query(
            query_embeddings=[embedding],
            n_results=3,
            include=["documents", "metadatas", "distances"],
        )

        rag_results = []
        for doc, meta, distance in zip(
            rag_data.get("documents", [[]])[0],
            rag_data.get("metadatas", [[]])[0],
            rag_data.get("distances", [[]])[0],
        ):
            filename = meta.get("filename") if isinstance(meta, dict) else None
            rag_results.append(
                {
                    "filename": filename,
                    "distance": distance,
                    "content": doc,
                }
            )

        llm_model = self.manager.get_model("llm")
        llm_tokenizer = AutoTokenizer.from_pretrained(self.manager.model_ids["llm"])
        prompt = (
            "Hier ist ein Dokumenteninhalt: "
            f"{content}. Hier sind ähnliche Dokumente aus der Vergangenheit: "
            f"{rag_results}. Generiere einen Dateinamen nach genau demselben Muster. "
            "Antworte NUR mit dem Dateinamen."
        )

        inputs = llm_tokenizer(prompt, return_tensors="pt")
        device = llm_model.device if hasattr(llm_model, "device") else self.manager.get_device()
        inputs = {key: value.to(device) for key, value in inputs.items()}
        llm_model.to(device)

        try:
            output_ids = llm_model.generate(
                **inputs,
                max_new_tokens=64,
                do_sample=False,
            )
            decoded = llm_tokenizer.decode(output_ids[0], skip_special_tokens=True)
        except Exception as exc:  # noqa: BLE001
            logger.error("LLM-Ausgabe fehlgeschlagen: %s.", exc)
            return "dokument.pdf"

        suggestion = decoded.replace(prompt, "").strip()
        if not suggestion:
            logger.warning("LLM hat keinen Namen geliefert, Standard wird genutzt.")
            return "dokument.pdf"

        logger.info("Dateiname vorgeschlagen: %s.", suggestion)
        return suggestion
