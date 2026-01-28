"""ChromaDB-Gedaechtnis fuer konsistente Dateibenennungen."""

from __future__ import annotations

import logging
from typing import List
from uuid import uuid4

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

logger = logging.getLogger(__name__)


class ContextMemory:
    """Speichert und laedt Kontext aus ChromaDB fuer konsistente Benennungen."""

    def __init__(self, path: str = "./chroma_db", collection_name: str = "document_memory") -> None:
        self._client = chromadb.PersistentClient(path=path)
        self._embedding_function = SentenceTransformerEmbeddingFunction(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            device="cpu",
        )
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            embedding_function=self._embedding_function,
        )

    def remember(self, filename: str, text_summary: str) -> None:
        """Speichert eine neue Datei-Zusammenfassung als Vektor."""
        document_id = str(uuid4())
        logger.debug("Speichere Kontext fuer %s mit ID %s.", filename, document_id)
        self._collection.add(
            ids=[document_id],
            documents=[text_summary],
            metadatas=[{"filename": filename}],
        )

    def recall(self, text_summary: str, k: int = 3) -> List[dict]:
        """Liefert die aehnlichsten Dokumente zurueck."""
        if self._collection.count() == 0:
            return []

        result = self._collection.query(
            query_texts=[text_summary],
            n_results=k,
            include=["documents", "metadatas", "distances"],
        )
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        history = []
        for doc, meta, distance in zip(documents, metadatas, distances):
            history.append(
                {
                    "summary": doc,
                    "filename": (meta or {}).get("filename", "unbekannt"),
                    "distance": distance,
                }
            )
        return history
