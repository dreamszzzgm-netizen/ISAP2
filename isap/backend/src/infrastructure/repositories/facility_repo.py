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
