"""Поиск и извлечение данных из образцов ПМЛА."""
import logging
from uuid import UUID

from src.infrastructure.rag.pipeline import Chunk, Embedder, VectorStore
from src.infrastructure.rag.sample_indexer import SAMPLES_COLLECTION

logger = logging.getLogger(__name__)


class SampleRetriever:
    """Ищет релевантные фрагменты и извлекает целые разделы из образцов."""

    def __init__(self):
        self._embedder = Embedder()
        try:
            self._store = VectorStore(collection_name=SAMPLES_COLLECTION)
        except Exception:
            self._store = None

    async def retrieve_sample_chunks(
        self,
        query: str,
        facility_type: str,
        hazard_class: str,
        top_k: int = 5,
    ) -> list[Chunk]:
        """RAG-поиск по коллекции образцов с фильтром по типу/классу."""
        if self._store is None:
            return []

        try:
            query_embedding = await self._embedder.embed_query(query)
            where_filter = {}
            conditions = []
            if facility_type:
                conditions.append({"facility_type": facility_type.strip()})
            if hazard_class:
                conditions.append({"hazard_class": hazard_class.strip()})

            if len(conditions) == 1:
                where_filter = conditions[0]
            elif len(conditions) > 1:
                where_filter = {"$and": conditions}

            results = self._store._collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where_filter if where_filter else None,
                include=["documents", "metadatas"],
            )

            chunks = []
            for doc, meta in zip(
                results["documents"][0] if results["documents"] else [],
                results["metadatas"][0] if results["metadatas"] else [],
            ):
                chunks.append(Chunk(
                    content=doc,
                    source=meta.get("source", ""),
                    chunk_index=meta.get("chunk_index", 0),
                    metadata=meta,
                ))
            return chunks
        except Exception as e:
            logger.warning("Sample retrieval failed: %s", e)
            return []

    async def get_sample_section(self, sample_id: UUID, section_title: str) -> str:
        """Извлекает текст конкретного раздела из DOCX образца."""
        try:
            from sqlalchemy import select

            from src.infrastructure.database.engine import async_session_factory
            from src.infrastructure.database.models import PmlaSampleModel

            async with async_session_factory() as session:
                result = await session.execute(
                    select(PmlaSampleModel).where(PmlaSampleModel.id == sample_id)
                )
                sample = result.scalar_one_or_none()

                if not sample or not sample.file_path:
                    return ""
                if sample.file_type != "docx":
                    return ""

                import docx as _docx
                doc = _docx.Document(sample.file_path)

                in_section = False
                lines = []
                title_lower = section_title.lower()

                for para in doc.paragraphs:
                    text = para.text.strip()
                    if not text:
                        continue

                    style_name = para.style.name if para.style else ""
                    is_heading = "Heading" in style_name or (
                        para.runs and para.runs[0].bold and len(text) > 5
                    )

                    if is_heading:
                        if in_section:
                            break
                        if title_lower in text.lower() or text.lower() in title_lower:
                            in_section = True
                            continue

                    if in_section:
                        lines.append(text)

                return "\n".join(lines)
        except Exception as e:
            logger.warning("Failed to extract section from sample %s: %s", sample_id, e)
            return ""
