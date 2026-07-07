"""CRUD endpoints for emergency services directory."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db, get_emergency_service_repo
from src.infrastructure.repositories.emergency_service_repo import EmergencyServiceRepository

router = APIRouter()

SERVICE_TYPES = ["fire", "medical", "police", "gas", "edds", "other"]


class EmergencyServiceCreateRequest(BaseModel):
    service_type: str = "fire"
    name: str
    address: str | None = None
    phone: str | None = None
    dispatcher_phone: str | None = None
    municipality: str | None = None
    settlement: str | None = None
    latitude: str | None = None
    longitude: str | None = None
    service_area: str | None = None
    notes: str | None = None


class EmergencyServiceUpdateRequest(BaseModel):
    service_type: str | None = None
    name: str | None = None
    address: str | None = None
    phone: str | None = None
    dispatcher_phone: str | None = None
    municipality: str | None = None
    settlement: str | None = None
    latitude: str | None = None
    longitude: str | None = None
    service_area: str | None = None
    notes: str | None = None


def _to_dict(obj) -> dict:
    return {
        "id": str(obj.id),
        "service_type": obj.service_type,
        "name": obj.name,
        "address": obj.address,
        "phone": obj.phone,
        "dispatcher_phone": obj.dispatcher_phone,
        "municipality": obj.municipality,
        "settlement": obj.settlement,
        "latitude": obj.latitude,
        "longitude": obj.longitude,
        "service_area": obj.service_area,
        "notes": obj.notes,
        "created_at": obj.created_at.isoformat() if obj.created_at else None,
        "updated_at": obj.updated_at.isoformat() if obj.updated_at else None,
    }


@router.get("/")
async def list_emergency_services(
    search: str | None = Query(None),
    service_type: str | None = Query(None),
    repo: EmergencyServiceRepository = Depends(get_emergency_service_repo),
):
    items = await repo.search(query_str=search, service_type=service_type)
    return [_to_dict(item) for item in items]


@router.get("/types")
async def list_service_types():
    return SERVICE_TYPES


@router.get("/{service_id}")
async def get_emergency_service(service_id: UUID, repo: EmergencyServiceRepository = Depends(get_emergency_service_repo)):
    item = await repo.get(service_id)
    if not item:
        raise HTTPException(status_code=404, detail="Служба не найдена")
    return _to_dict(item)


@router.post("/")
async def create_emergency_service(data: EmergencyServiceCreateRequest, repo: EmergencyServiceRepository = Depends(get_emergency_service_repo)):
    item = await repo.create(data.model_dump(exclude_none=True))
    return _to_dict(item)


@router.patch("/{service_id}")
async def update_emergency_service(service_id: UUID, data: EmergencyServiceUpdateRequest, repo: EmergencyServiceRepository = Depends(get_emergency_service_repo)):
    item = await repo.update(service_id, data.model_dump(exclude_unset=True))
    if not item:
        raise HTTPException(status_code=404, detail="Служба не найдена")
    return _to_dict(item)


@router.delete("/{service_id}")
async def delete_emergency_service(service_id: UUID, repo: EmergencyServiceRepository = Depends(get_emergency_service_repo)):
    deleted = await repo.delete(service_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Служба не найдена")
    return {"ok": True}
