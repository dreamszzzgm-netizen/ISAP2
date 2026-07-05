"""Роутер опасных веществ ОПО — CRUD операции."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict

from src.api.dependencies import get_substance_repo
from src.infrastructure.repositories.substance_repo import SubstanceRepository

router = APIRouter()


class SubstanceCreate(BaseModel):
    hazardous_facility_id: UUID
    name: str
    cas_number: str | None = None
    quantity_kg: float | None = None
    threshold_quantity_kg: float | None = None
    hazard_properties: dict = {}


class SubstanceUpdate(BaseModel):
    name: str | None = None
    cas_number: str | None = None
    quantity_kg: float | None = None
    threshold_quantity_kg: float | None = None
    hazard_properties: dict | None = None


class SubstanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    hazardous_facility_id: UUID
    name: str
    cas_number: str | None
    quantity_kg: float | None
    threshold_quantity_kg: float | None
    hazard_properties: dict


@router.post("/", response_model=SubstanceResponse, status_code=201)
async def create_substance(
    data: SubstanceCreate,
    repo: SubstanceRepository = Depends(get_substance_repo),
):
    return await repo.create(data.model_dump())


@router.get("/", response_model=list[SubstanceResponse])
async def list_substances(
    hazardous_facility_id: UUID | None = None,
    skip: int = 0,
    limit: int = 100,
    repo: SubstanceRepository = Depends(get_substance_repo),
):
    filters = {}
    if hazardous_facility_id:
        filters["hazardous_facility_id"] = hazardous_facility_id
    return await repo.get_multi(skip=skip, limit=limit, filters=filters)


@router.get("/{substance_id}", response_model=SubstanceResponse)
async def get_substance(
    substance_id: UUID,
    repo: SubstanceRepository = Depends(get_substance_repo),
):
    sub = await repo.get(substance_id)
    if sub is None:
        raise HTTPException(status_code=404, detail="Вещество не найдено")
    return sub


@router.put("/{substance_id}", response_model=SubstanceResponse)
async def update_substance(
    substance_id: UUID,
    data: SubstanceUpdate,
    repo: SubstanceRepository = Depends(get_substance_repo),
):
    sub = await repo.update(substance_id, data.model_dump(exclude_unset=True))
    if sub is None:
        raise HTTPException(status_code=404, detail="Вещество не найдено")
    return sub


@router.delete("/{substance_id}", status_code=204)
async def delete_substance(
    substance_id: UUID,
    repo: SubstanceRepository = Depends(get_substance_repo),
):
    if not await repo.delete(substance_id):
        raise HTTPException(status_code=404, detail="Вещество не найдено")
