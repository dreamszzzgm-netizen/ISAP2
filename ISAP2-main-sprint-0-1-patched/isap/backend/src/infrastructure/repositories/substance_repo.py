from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models import HazardousSubstanceModel
from src.infrastructure.repositories.base import BaseRepository


class SubstanceRepository(BaseRepository[HazardousSubstanceModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(HazardousSubstanceModel, session)

    async def get_by_facility(self, facility_id: UUID) -> list[HazardousSubstanceModel]:
        result = await self.session.execute(
            select(HazardousSubstanceModel).where(
                HazardousSubstanceModel.hazardous_facility_id == facility_id
            )
        )
        return list(result.scalars().all())
