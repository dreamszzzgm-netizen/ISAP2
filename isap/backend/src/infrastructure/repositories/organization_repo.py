from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models import OrganizationModel
from src.infrastructure.repositories.base import BaseRepository


def _normalize_text(value: str) -> str:
    """Normalise text for matching: strip, collapse spaces, casefold."""
    import re
    return re.sub(r"\s+", " ", value.strip()).casefold()


class OrganizationRepository(BaseRepository[OrganizationModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(OrganizationModel, session)

    async def search_by_name(self, name: str, limit: int = 10) -> list[OrganizationModel]:
        """Search organisations by name (ILIKE, case-insensitive)."""
        if not name or not name.strip():
            return []
        pattern = f"%{_normalize_text(name)}%"
        result = await self.session.execute(
            select(OrganizationModel)
            .where(OrganizationModel.name.ilike(pattern))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def search_by_inn(self, inn: str) -> OrganizationModel | None:
        """Find organisation by exact INN match."""
        if not inn or not inn.strip():
            return None
        result = await self.session.execute(
            select(OrganizationModel).where(OrganizationModel.inn == inn.strip())
        )
        return result.scalar_one_or_none()
