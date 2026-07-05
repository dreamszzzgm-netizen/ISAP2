from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models import ResponsiblePersonModel
from src.infrastructure.repositories.base import BaseRepository


class PersonRepository(BaseRepository[ResponsiblePersonModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(ResponsiblePersonModel, session)

    async def get_by_organization(self, organization_id: UUID) -> list[ResponsiblePersonModel]:
        result = await self.session.execute(
            select(ResponsiblePersonModel).where(
                ResponsiblePersonModel.organization_id == organization_id
            )
        )
        return list(result.scalars().all())
