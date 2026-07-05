"""Роутер оборудования ОПО — CRUD операции."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict

from src.api.dependencies import get_equipment_repo
from src.infrastructure.repositories.equipment_repo import EquipmentRepository

router = APIRouter()


class EquipmentCreate(BaseModel):
    hazardous_facility_id: UUID
    name: str
    equipment_type: str | None = None
    serial_number: str | None = None
    manufacturer: str | None = None
    manufacture_year: int | None = None
    specifications: dict = {}


class EquipmentUpdate(BaseModel):
    name: str | None = None
    equipment_type: str | None = None
    serial_number: str | None = None
    manufacturer: str | None = None
    manufacture_year: int | None = None
    specifications: dict | None = None


class EquipmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    hazardous_facility_id: UUID
    name: str
    equipment_type: str | None
    serial_number: str | None
    manufacturer: str | None
    manufacture_year: int | None
    specifications: dict


@router.post("/", response_model=EquipmentResponse, status_code=201)
async def create_equipment(
    data: EquipmentCreate,
    repo: EquipmentRepository = Depends(get_equipment_repo),
):
    return await repo.create(data.model_dump())


@router.get("/", response_model=list[EquipmentResponse])
async def list_equipment(
    hazardous_facility_id: UUID | None = None,
    skip: int = 0,
    limit: int = 100,
    repo: EquipmentRepository = Depends(get_equipment_repo),
):
    filters = {}
    if hazardous_facility_id:
        filters["hazardous_facility_id"] = hazardous_facility_id
    return await repo.get_multi(skip=skip, limit=limit, filters=filters)


@router.get("/{equipment_id}", response_model=EquipmentResponse)
async def get_equipment(
    equipment_id: UUID,
    repo: EquipmentRepository = Depends(get_equipment_repo),
):
    eq = await repo.get(equipment_id)
    if eq is None:
        raise HTTPException(status_code=404, detail="Оборудование не найдено")
    return eq


@router.put("/{equipment_id}", response_model=EquipmentResponse)
async def update_equipment(
    equipment_id: UUID,
    data: EquipmentUpdate,
    repo: EquipmentRepository = Depends(get_equipment_repo),
):
    eq = await repo.update(equipment_id, data.model_dump(exclude_unset=True))
    if eq is None:
        raise HTTPException(status_code=404, detail="Оборудование не найдено")
    return eq


@router.delete("/{equipment_id}", status_code=204)
async def delete_equipment(
    equipment_id: UUID,
    repo: EquipmentRepository = Depends(get_equipment_repo),
):
    if not await repo.delete(equipment_id):
        raise HTTPException(status_code=404, detail="Оборудование не найдено")
