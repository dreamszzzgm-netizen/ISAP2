from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models import EquipmentModel
from src.infrastructure.repositories.base import BaseRepository


class EquipmentRepository(BaseRepository[EquipmentModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(EquipmentModel, session)

    async def get_by_facility(self, facility_id: UUID) -> list[EquipmentModel]:
        result = await self.session.execute(
            select(EquipmentModel).where(
                EquipmentModel.hazardous_facility_id == facility_id
            )
        )
        return list(result.scalars().all())
