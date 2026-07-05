from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.infrastructure.database.models import OpoDetailsModel
from src.infrastructure.repositories.base import BaseRepository


class OpoDetailsRepository(BaseRepository[OpoDetailsModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(OpoDetailsModel, session)

    async def get_by_facility_id(self, facility_id: UUID) -> OpoDetailsModel | None:
        result = await self.session.execute(
            select(OpoDetailsModel).where(OpoDetailsModel.facility_id == facility_id)
        )
        return result.scalar_one_or_none()

    async def upsert(self, facility_id: UUID, data: dict) -> OpoDetailsModel:
        # SELECT FOR UPDATE предотвращает race condition при параллельных запросах
        result = await self.session.execute(
            select(OpoDetailsModel)
            .where(OpoDetailsModel.facility_id == facility_id)
            .with_for_update()
        )
        existing = result.scalar_one_or_none()
        if existing:
            for key, value in data.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            await self.session.flush()
            await self.session.refresh(existing)
            return existing
        obj = OpoDetailsModel(facility_id=facility_id, **data)
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj
