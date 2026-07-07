from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models import EmergencyServiceModel
from src.infrastructure.repositories.base import BaseRepository


class EmergencyServiceRepository(BaseRepository[EmergencyServiceModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(EmergencyServiceModel, session)

    async def search(
        self,
        query_str: str | None = None,
        service_type: str | None = None,
        limit: int = 50,
    ) -> list[EmergencyServiceModel]:
        q = select(EmergencyServiceModel)
        if service_type:
            q = q.where(EmergencyServiceModel.service_type == service_type)
        if query_str:
            pattern = f"%{query_str}%"
            q = q.where(
                EmergencyServiceModel.name.ilike(pattern)
                | EmergencyServiceModel.address.ilike(pattern)
                | EmergencyServiceModel.municipality.ilike(pattern)
            )
        q = q.order_by(EmergencyServiceModel.name).limit(limit)
        result = await self.session.execute(q)
        return list(result.scalars().all())
