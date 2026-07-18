from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models import (
    EquipmentModel,
    HazardousFacilityModel,
    HazardousSubstanceModel,
)
from src.infrastructure.repositories.base import BaseRepository


def _normalize_text(value: str) -> str:
    """Normalise text for matching: strip, collapse spaces, casefold."""
    import re
    return re.sub(r"\s+", " ", value.strip()).casefold()


@dataclass
class FacilityWithData:
    """ОПО с загруженными связанными данными."""

    facility: HazardousFacilityModel
    equipment: list[EquipmentModel] = field(default_factory=list)
    substances: list[HazardousSubstanceModel] = field(default_factory=list)


class FacilityRepository(BaseRepository[HazardousFacilityModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(HazardousFacilityModel, session)

    async def get_with_related(self, facility_id: UUID) -> FacilityWithData | None:
        result = await self.session.execute(
            select(HazardousFacilityModel).where(HazardousFacilityModel.id == facility_id)
        )
        facility = result.scalar_one_or_none()
        if facility is None:
            return None

        eq_result = await self.session.execute(
            select(EquipmentModel).where(
                EquipmentModel.hazardous_facility_id == facility_id
            )
        )
        equipment = list(eq_result.scalars().all())

        sub_result = await self.session.execute(
            select(HazardousSubstanceModel).where(
                HazardousSubstanceModel.hazardous_facility_id == facility_id
            )
        )
        substances = list(sub_result.scalars().all())

        return FacilityWithData(facility=facility, equipment=equipment, substances=substances)

    async def search_by_reg_number(self, reg_number: str, limit: int = 10) -> list[HazardousFacilityModel]:
        """Search facilities by registration number (case-insensitive ILIKE)."""
        if not reg_number or not reg_number.strip():
            return []
        pattern = f"%{_normalize_text(reg_number)}%"
        result = await self.session.execute(
            select(HazardousFacilityModel)
            .where(HazardousFacilityModel.reg_number.ilike(pattern))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def search_by_name(
        self,
        name: str,
        organization_id: UUID | None = None,
        limit: int = 10,
    ) -> list[HazardousFacilityModel]:
        """Search facilities by name (ILIKE), optionally filtered by organisation."""
        if not name or not name.strip():
            return []
        pattern = f"%{_normalize_text(name)}%"
        query = select(HazardousFacilityModel).where(
            HazardousFacilityModel.name.ilike(pattern)
        )
        if organization_id is not None:
            query = query.where(
                HazardousFacilityModel.organization_id == organization_id
            )
        query = query.limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def search_by_name_and_address(
        self,
        name: str,
        address: str,
        limit: int = 5,
    ) -> list[HazardousFacilityModel]:
        """Search facilities by combination of name and address (ILIKE)."""
        if not name or not name.strip():
            return []
        pattern_name = f"%{_normalize_text(name)}%"
        query = select(HazardousFacilityModel).where(
            HazardousFacilityModel.name.ilike(pattern_name)
        )
        if address and address.strip():
            pattern_addr = f"%{_normalize_text(address)}%"
            query = query.where(
                HazardousFacilityModel.address.ilike(pattern_addr)
            )
        query = query.limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())
