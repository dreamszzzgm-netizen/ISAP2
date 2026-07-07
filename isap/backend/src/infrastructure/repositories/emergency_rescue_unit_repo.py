from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models import EmergencyRescueUnitModel
from src.infrastructure.repositories.base import BaseRepository


class EmergencyRescueUnitRepository(BaseRepository[EmergencyRescueUnitModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(EmergencyRescueUnitModel, session)

    async def search(self, query_str: str, limit: int = 50) -> list[EmergencyRescueUnitModel]:
        q = select(EmergencyRescueUnitModel)
        if query_str:
            pattern = f"%{query_str}%"
            q = q.where(
                EmergencyRescueUnitModel.name.ilike(pattern)
                | EmergencyRescueUnitModel.short_name.ilike(pattern)
                | EmergencyRescueUnitModel.actual_address.ilike(pattern)
            )
        q = q.order_by(EmergencyRescueUnitModel.name).limit(limit)
        result = await self.session.execute(q)
        return list(result.scalars().all())
