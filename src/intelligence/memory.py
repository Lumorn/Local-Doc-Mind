"""ChromaDB-Gedaechtnis fuer konsistente Dateibenennungen."""

from __future__ import annotations

import logging
from typing import List
from uuid import uuid4

import chromadb
from sentence_transformers import SentenceTransformer

from src.core.model_manager import ModelManager

logger = logging.getLogger(__name__)


class ContextMemory:
    """Speichert und laedt Kontext aus ChromaDB fuer konsistente Benennungen."""

    def __init__(self, path: str = "./chroma_db", collection_name: str = "document_memory") -> None:
        self._client = chromadb.PersistentClient(path=path)
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
        )
        self._embedding_model = self._load_embedding_model()

    def _load_embedding_model(self) -> SentenceTransformer:
        """Laedt das Embedding-Modell ueber den ModelManager oder lokal."""
        manager = ModelManager.instance()
        embedding_model = manager.get_embedding_model()
        if embedding_model is None:
            logger.warning("Embedding-Modell fehlte im Manager, lade lokal.")
            return SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2", device="cpu")
        return embedding_model

    def _embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Erstellt Embeddings fuer eine Liste von Texten."""
        embeddings = self._embedding_model.encode(texts, normalize_embeddings=True)
        return [embedding.tolist() for embedding in embeddings]

    def remember(self, filename: str, folder: str, text_summary: str) -> None:
        """Speichert eine neue Datei-Zusammenfassung als Vektor."""
        if not text_summary.strip():
            logger.debug("Leere Zusammenfassung, Kontext wird nicht gespeichert.")
            return
        document_id = str(uuid4())
        logger.debug("Speichere Kontext fuer %s mit ID %s.", filename, document_id)
        embedding = self._embed_texts([text_summary])[0]
        self._collection.add(
            ids=[document_id],
            documents=[text_summary],
            embeddings=[embedding],
            metadatas=[{"filename": filename, "folder": folder}],
        )

    def recall(self, text_content: str, k: int = 3) -> str:
        """Liefert den aehnlichsten Kontext als String fuer das LLM."""
        if not text_content.strip():
            logger.debug("Leerer Textinhalt, keine Kontextsuche moeglich.")
            return "Keine historischen Dokumente gefunden."
        if self._collection.count() == 0:
            return "Keine historischen Dokumente gefunden."

        query_embedding = self._embed_texts([text_content])[0]
        result = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            include=["documents", "metadatas", "distances"],
        )
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        if not documents:
            return "Keine historischen Dokumente gefunden."

        history_lines = []
        for index, (doc, meta) in enumerate(zip(documents, metadatas), start=1):
            filename = (meta or {}).get("filename", "unbekannt")
            folder = (meta or {}).get("folder", "Unbekannt")
            history_lines.append(
                f"Ähnliches Dokument {index}: Abgelegt unter '{folder}' als '{filename}'. "
                f"Zusammenfassung: {doc}"
            )
        return "\n".join(history_lines)
