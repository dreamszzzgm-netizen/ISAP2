from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models import OrganizationModel
from src.infrastructure.repositories.base import BaseRepository


class OrganizationRepository(BaseRepository[OrganizationModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(OrganizationModel, session)
