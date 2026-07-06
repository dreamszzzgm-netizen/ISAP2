"""Роутер матрицы сценариев."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict

from src.api.dependencies import get_scenario_matrix_repo
from src.infrastructure.repositories.scenario_matrix_repo import ScenarioMatrixRepository

router = APIRouter()


class ScenarioMatrixResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    facility_type: str
    hazard_class: str
    scenario_code: str
    scenario_name: str
    factor_type: str | None
    calculation_method: str | None
    probability: str
    is_active: int


class ScenarioMatrixCreate(BaseModel):
    facility_type: str
    hazard_class: str
    scenario_code: str
    scenario_name: str
    factor_type: str | None = None
    calculation_method: str | None = None
    probability: str = "средняя"


@router.get("/", response_model=list[ScenarioMatrixResponse])
async def list_scenarios(
    facility_type: str | None = None,
    hazard_class: str | None = None,
    repo: ScenarioMatrixRepository = Depends(get_scenario_matrix_repo),
):
    """Список сценариев с фильтрацией (регистронезависимо)."""
    if facility_type and hazard_class:
        return await repo.get_by_type_and_class(facility_type, hazard_class)
    filters = {"is_active": 1}
    if facility_type:
        filters["facility_type"] = facility_type
    if hazard_class:
        filters["hazard_class"] = hazard_class
    return await repo.get_multi(filters=filters)


@router.get("/{scenario_id}", response_model=ScenarioMatrixResponse)
async def get_scenario(
    scenario_id: UUID,
    repo: ScenarioMatrixRepository = Depends(get_scenario_matrix_repo),
):
    """Получить сценарий по ID."""
    scenario = await repo.get(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Сценарий не найден")
    return scenario


@router.post("/", response_model=ScenarioMatrixResponse, status_code=201)
async def create_scenario(
    data: ScenarioMatrixCreate,
    repo: ScenarioMatrixRepository = Depends(get_scenario_matrix_repo),
):
    """Создать сценарий."""
    return await repo.create(data.model_dump())


@router.delete("/{scenario_id}", status_code=204)
async def delete_scenario(
    scenario_id: UUID,
    repo: ScenarioMatrixRepository = Depends(get_scenario_matrix_repo),
):
    """Удалить сценарий."""
    if not await repo.delete(scenario_id):
        raise HTTPException(status_code=404, detail="Сценарий не найден")
