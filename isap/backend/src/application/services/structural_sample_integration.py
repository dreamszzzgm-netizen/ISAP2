"""Координация индексации и использования образцов через структурный RAG-пайплайн."""
import logging
from uuid import UUID

from src.infrastructure.rag.structural_pipeline import (
    StructuralSampleIndexer,
    StructuralSampleRetriever,
    parse_pmla_docx,
)

logger = logging.getLogger(__name__)


# Маппинг section_id → ключевые слова для RAG-запроса
_SECTION_RAG_QUERIES: dict[str, str] = {
    "section_1": "характеристика объекта опасного производственного",
    "section_2": "сценарии аварий вероятных аварийных ситуаций",
    "section_3": "аварийность травматизм статистика",
    "section_4": "количество сил средств ликвидация",
    "section_5": "взаимодействие сил средств координация",
    "section_6": "состав дислокация сил средств",
    "section_7": "готовность сил средств подготовка учения",
    "section_8": "управление связь оповещение",
    "section_9": "обмен информацией коммуникации",
    "section_10": "первоочередные действия локализация авария",
    "section_11": "действия персонала эвакуация безопасность",
    "section_12": "безопасность населения защита эвакуация",
    "section_13": "материально-техническое обеспечение финансирование",
    "special_section": "оперативные действия ликвидация аварий сценарии",
}


class StructuralSampleIntegrationService:
    """Координация индексации и использования образцов через структурный RAG.

    Использует SectionDetector для определения границ разделов
    и StructuralChunker для создания осмысленных чанков.
    """

    def __init__(self, sample_repo):
        self._sample_repo = sample_repo
        self._indexer = StructuralSampleIndexer()
        self._retriever = StructuralSampleRetriever()

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
        section_id: str,
        section_title: str,
        facility_type: str,
        hazard_class: str,
    ) -> dict:
        """Собирает контекст из образцов для конкретного раздела.

        Args:
            section_id: ID раздела (например, "section_2").
            section_title: Название раздела.
            facility_type: Тип объекта.
            hazard_class: Класс опасности.

        Returns:
            {
                "rag_context": str,        # RAG-фрагменты из образцов
                "few_shot_example": str,   # Текст раздела из лучшего образца
            }
        """
        result = {"rag_context": "", "few_shot_example": ""}

        # Формируем запрос для RAG
        rag_query = _SECTION_RAG_QUERIES.get(section_id, section_title)

        # RAG-чанки с фильтром по section_id
        rag_chunks = await self._retriever.retrieve_by_section(
            query=rag_query,
            section_id=section_id,
            facility_type=facility_type,
            hazard_class=hazard_class,
            top_k=3,
        )
        if rag_chunks:
            result["rag_context"] = "\n\n".join(c.content for c in rag_chunks)

        # Few-shot: ищем лучший образец и извлекаем нужный раздел
        best_sample_id = await self._find_best_sample(facility_type, hazard_class)
        if best_sample_id:
            few_shot = await self._extract_section_from_sample(best_sample_id, section_id)
            if few_shot:
                result["few_shot_example"] = few_shot

        return result

    async def _extract_section_from_sample(
        self, sample_id: UUID, section_id: str
    ) -> str:
        """Извлекает текст конкретного раздела из DOCX образца.

        Использует SectionDetector для точного определения границ раздела.
        """
        try:
            sample = await self._sample_repo.get(sample_id)
            if not sample or not sample.file_path:
                return ""
            if sample.file_type != "docx":
                return ""

            result = parse_pmla_docx(sample.file_path)

            # Находим нужный раздел
            for section in result.report.detected_sections:
                if section.section_id == section_id:
                    # Извлекаем текст раздела
                    start = section.start_para_idx
                    end = section.end_para_idx if section.end_para_idx is not None else len(result.paragraphs)

                    section_text_parts = []
                    for i in range(start, end):
                        if i < len(result.paragraphs):
                            text = result.paragraphs[i][0]
                            if text and text.strip():
                                section_text_parts.append(text.strip())

                    return "\n".join(section_text_parts)

            return ""
        except Exception as e:
            logger.warning("Failed to extract section %s from sample %s: %s", section_id, sample_id, e)
            return ""

    async def _find_best_sample(self, facility_type: str, hazard_class: str) -> UUID | None:
        """Находит лучший верифицированный образец для данного типа ОПО."""
        try:
            from src.infrastructure.database.engine import async_session_factory
            from src.infrastructure.database.models import PmlaSampleModel
            from sqlalchemy import select

            async with async_session_factory() as session:
                query = (
                    select(PmlaSampleModel)
                    .where(PmlaSampleModel.is_verified == 1)
                    .where(PmlaSampleModel.is_active == 1)
                )

                conditions = []
                if facility_type:
                    from sqlalchemy import func
                    conditions.append(func.lower(PmlaSampleModel.facility_type) == facility_type.lower())
                if hazard_class:
                    from sqlalchemy import func
                    conditions.append(func.lower(PmlaSampleModel.hazard_class) == hazard_class.lower())

                if conditions:
                    from sqlalchemy import and_
                    query = query.where(and_(*conditions))

                query = query.order_by(PmlaSampleModel.usage_count.desc()).limit(1)
                result = await session.execute(query)
                sample = result.scalar_one_or_none()

                return sample.id if sample else None
        except Exception as e:
            logger.warning("Failed to find best sample: %s", e)
            return None
