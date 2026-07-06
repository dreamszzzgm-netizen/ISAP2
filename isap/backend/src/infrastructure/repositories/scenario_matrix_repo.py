"""Репозиторий матрицы сценариев."""
from sqlalchemy import func, select

from src.infrastructure.database.models import ScenarioMatrixModel
from src.infrastructure.repositories.base import BaseRepository


class ScenarioMatrixRepository(BaseRepository[ScenarioMatrixModel]):
    def __init__(self, session):
        super().__init__(ScenarioMatrixModel, session)

    async def get_by_type_and_class(
        self, facility_type: str, hazard_class: str
    ) -> list[ScenarioMatrixModel]:
        """Поиск сценариев по типу объекта и классу (регистронезависимо)."""
        query = select(ScenarioMatrixModel).where(
            ScenarioMatrixModel.is_active == 1,
            func.lower(ScenarioMatrixModel.facility_type) == facility_type.lower(),
            func.lower(ScenarioMatrixModel.hazard_class) == str(hazard_class).lower(),
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
