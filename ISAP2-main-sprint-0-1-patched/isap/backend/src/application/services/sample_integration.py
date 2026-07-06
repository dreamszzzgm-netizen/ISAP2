"""Координация индексации и использования образцов при генерации."""
import logging
from uuid import UUID

from src.infrastructure.rag.sample_indexer import SampleIndexer
from src.infrastructure.rag.sample_retriever import SampleRetriever

logger = logging.getLogger(__name__)


class SampleIntegrationService:
    """Координация индексации и использования образцов."""

    def __init__(self, sample_repo):
        self._sample_repo = sample_repo
        self._indexer = SampleIndexer()
        self._retriever = SampleRetriever()

    async def on_sample_verified(self, sample_id: UUID) -> int:
        """Вызывается при верификации образца — индексирует в ChromaDB."""
        sample = await self._sample_repo.get(sample_id)
        if not sample:
            return 0

        return await self._indexer.index_sample(
            sample_id=sample.id,
            file_path=sample.file_path,
            file_type=sample.file_type,
            facility_type=sample.facility_type,
            hazard_class=sample.hazard_class,
        )

    async def on_sample_unverified(self, sample_id: UUID) -> None:
        """Вызывается при снятии верификации — удаляет из ChromaDB."""
        await self._indexer.remove_sample(sample_id)

    async def build_sample_context(
        self,
        section_title: str,
        facility_type: str,
        hazard_class: str,
    ) -> dict:
        """Собирает контекст из образцов для генератора.

        Возвращает:
            {
                "rag_context": str,        # RAG-фрагменты из образцов
                "few_shot_example": str,   # Текст раздела из лучшего образца
            }
        """
        result = {"rag_context": "", "few_shot_example": ""}

        # RAG-чанки
        rag_chunks = await self._retriever.retrieve_sample_chunks(
            query=section_title,
            facility_type=facility_type,
            hazard_class=hazard_class,
        )
        if rag_chunks:
            result["rag_context"] = "\n\n".join(c.content for c in rag_chunks)

        # Few-shot: ищем лучший образец и извлекаем нужный раздел
        best_sample_id = await self._find_best_sample(facility_type, hazard_class)
        if best_sample_id:
            result["few_shot_example"] = await self._retriever.get_sample_section(
                best_sample_id, section_title
            )

        return result

    async def _find_best_sample(self, facility_type: str, hazard_class: str) -> UUID | None:
        """Находит лучший верифицированный образец для данного типа ОПО."""
        try:
            from src.infrastructure.database.models import PmlaSampleModel
            from sqlalchemy import select, func, and_

            session = self._sample_repo.session
            query = (
                select(PmlaSampleModel)
                .where(PmlaSampleModel.is_verified == 1)
                .where(PmlaSampleModel.is_active == 1)
            )

            conditions = []
            if facility_type:
                conditions.append(func.lower(PmlaSampleModel.facility_type) == facility_type.lower())
            if hazard_class:
                conditions.append(func.lower(PmlaSampleModel.hazard_class) == hazard_class.lower())

            if conditions:
                query = query.where(and_(*conditions))

            query = query.order_by(PmlaSampleModel.usage_count.desc()).limit(1)
            result = await session.execute(query)
            sample = result.scalar_one_or_none()

            return sample.id if sample else None
        except Exception as e:
            logger.warning("Failed to find best sample: %s", e)
            return None
