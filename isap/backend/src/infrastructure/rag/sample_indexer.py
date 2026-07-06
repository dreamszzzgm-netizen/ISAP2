"""Индексация образцов ПМЛА в ChromaDB."""
import logging
from uuid import UUID

from src.infrastructure.rag.pipeline import (
    Chunker,
    DocumentLoader,
    Embedder,
    VectorStore,
)

logger = logging.getLogger(__name__)

SAMPLES_COLLECTION = "isap_samples"


class SampleIndexer:
    """Индексирует верифицированные образцы в отдельную коллекцию ChromaDB."""

    def __init__(self):
        self._loader = DocumentLoader()
        self._chunker = Chunker(chunk_size=100, overlap=20)
        self._embedder = Embedder()

    async def index_sample(
        self,
        sample_id: UUID,
        file_path: str,
        file_type: str,
        facility_type: str | None,
        hazard_class: str | None,
    ) -> int:
        """Парсит DOCX/PDF, чанкует, эмбеддит, сохраняет в ChromaDB.

        Возвращает количество проиндексированных чанков.
        """
        try:
            docs = self._loader.load(file_path)
        except Exception as e:
            logger.warning("Failed to load sample %s: %s", sample_id, e)
            return 0

        if not docs:
            return 0

        chunks = self._chunker.chunk(docs)
        if not chunks:
            return 0

        for chunk in chunks:
            chunk.metadata.update({
                "sample_id": str(sample_id),
                "facility_type": (facility_type or "").strip(),
                "hazard_class": (hazard_class or "").strip(),
                "doc_type": "sample",
            })

        try:
            embedded = await self._embedder.embed_chunks(chunks)
            store = VectorStore(collection_name=SAMPLES_COLLECTION)
            store.add(embedded)
            logger.info("Indexed %d chunks for sample %s", len(embedded), sample_id)
            return len(embedded)
        except Exception as e:
            logger.warning("Failed to index sample %s: %s", sample_id, e)
            return 0

    async def remove_sample(self, sample_id: UUID) -> None:
        """Удаляет все чанки образца из ChromaDB."""
        try:
            store = VectorStore(collection_name=SAMPLES_COLLECTION)
            store.delete(where={"sample_id": str(sample_id)})
            logger.info("Removed sample %s from ChromaDB", sample_id)
        except Exception as e:
            logger.warning("Failed to remove sample %s: %s", sample_id, e)
