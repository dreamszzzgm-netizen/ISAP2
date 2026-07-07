from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models import (
    CalculationResultModel,
    DocumentModel,
    DocumentVersionModel,
)
from src.infrastructure.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[DocumentModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(DocumentModel, session)

    async def get_by_facility(
        self,
        facility_id: UUID,
        document_type: str | None = None,
    ) -> list[DocumentModel]:
        query = select(DocumentModel).where(
            DocumentModel.hazardous_facility_id == facility_id
        )
        if document_type:
            query = query.where(DocumentModel.document_type == document_type)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_questionnaire(self, questionnaire_id: UUID) -> list[DocumentModel]:
        """Return all documents generated from a specific questionnaire, newest first."""
        query = (
            select(DocumentModel)
            .where(
                DocumentModel.generation_meta["source"].as_string() == "pmla_questionnaire",
                DocumentModel.generation_meta["questionnaire_id"].as_string() == str(questionnaire_id),
            )
            .order_by(DocumentModel.version.desc().nullslast(), DocumentModel.created_at.desc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_max_version_for_questionnaire(self, questionnaire_id: UUID) -> int:
        """Return the max version number for documents from a questionnaire, or 0."""
        docs = await self.get_by_questionnaire(questionnaire_id)
        versions = [d.version for d in docs if d.version is not None]
        return max(versions) if versions else 0

    async def add_version(self, version: DocumentVersionModel) -> DocumentVersionModel:
        self.session.add(version)
        await self.session.commit()
        await self.session.refresh(version)
        return version

    async def get_latest_version(self, document_id: UUID) -> DocumentVersionModel | None:
        result = await self.session.execute(
            select(DocumentVersionModel)
            .where(DocumentVersionModel.document_id == document_id)
            .order_by(DocumentVersionModel.version_number.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def add_calculation_result(
        self, calc_result: CalculationResultModel
    ) -> CalculationResultModel:
        self.session.add(calc_result)
        await self.session.commit()
        await self.session.refresh(calc_result)
        return calc_result

    async def get_calculation_results(
        self, document_id: UUID
    ) -> list[CalculationResultModel]:
        result = await self.session.execute(
            select(CalculationResultModel).where(
                CalculationResultModel.document_id == document_id
            )
        )
        return list(result.scalars().all())
