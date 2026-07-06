from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models import RegulatoryDocumentModel
from src.infrastructure.repositories.base import BaseRepository


class RegulatoryRepository(BaseRepository[RegulatoryDocumentModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(RegulatoryDocumentModel, session)

    async def get_by_method_id(self, method_id: str) -> RegulatoryDocumentModel | None:
        result = await self.session.execute(
            select(RegulatoryDocumentModel).where(
                RegulatoryDocumentModel.id == UUID(method_id)
            )
        )
        return result.scalar_one_or_none()

    async def get_active_documents(self) -> list[RegulatoryDocumentModel]:
        result = await self.session.execute(
            select(RegulatoryDocumentModel).where(
                RegulatoryDocumentModel.status == "действует"
            )
        )
        return list(result.scalars().all())

    async def get_active_for_rag(self) -> list[RegulatoryDocumentModel]:
        result = await self.session.execute(
            select(RegulatoryDocumentModel).where(
                RegulatoryDocumentModel.status.in_(["действует", "рекомендательный"])
            )
        )
        return list(result.scalars().all())

    async def get_by_category(self, category: str) -> list[RegulatoryDocumentModel]:
        result = await self.session.execute(
            select(RegulatoryDocumentModel).where(
                RegulatoryDocumentModel.category == category
            )
        )
        return list(result.scalars().all())

    async def verify_status(
        self,
        document_id: UUID,
        new_status: str,
        verification_source: str,
        notes: str | None = None,
    ) -> RegulatoryDocumentModel | None:
        doc = await self.get(document_id)
        if doc is None:
            return None
        doc.status = new_status
        doc.last_verified_at = datetime.now(UTC).replace(tzinfo=None)
        doc.verification_source = verification_source
        if notes:
            doc.notes = notes
        await self.session.commit()
        await self.session.refresh(doc)
        return doc

    async def get_replaced_documents(self) -> list[RegulatoryDocumentModel]:
        result = await self.session.execute(
            select(RegulatoryDocumentModel).where(
                RegulatoryDocumentModel.status == "заменён"
            )
        )
        return list(result.scalars().all())

    async def get_disputed_documents(self) -> list[RegulatoryDocumentModel]:
        result = await self.session.execute(
            select(RegulatoryDocumentModel).where(
                RegulatoryDocumentModel.status == "спорный"
            )
        )
        return list(result.scalars().all())
