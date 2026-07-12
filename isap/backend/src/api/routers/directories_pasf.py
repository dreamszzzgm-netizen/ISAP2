"""CRUD endpoints for ПАСФ / АСФ directory."""
from __future__ import annotations

import csv
import io
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db, get_emergency_rescue_unit_repo
from src.infrastructure.repositories.emergency_rescue_unit_repo import EmergencyRescueUnitRepository

router = APIRouter()


class PasfCreateRequest(BaseModel):
    name: str
    short_name: str | None = None
    organization_type: str | None = None
    director_name: str | None = None
    director_position: str | None = None
    legal_address: str | None = None
    actual_address: str | None = None
    dispatch_phone: str | None = None
    email: str | None = None
    manager_name: str | None = None
    certificate_number: str | None = None
    certificate_date: str | None = None
    certificate_valid_until: str | None = None
    permitted_work_types: list[str] | None = None
    equipment_passport: list[str] | None = None
    staff_count: str | None = None
    readiness_mode: str | None = None
    service_area: str | None = None
    region: str | None = None
    is_active: bool | None = None
    notes: str | None = None


class PasfUpdateRequest(BaseModel):
    name: str | None = None
    short_name: str | None = None
    organization_type: str | None = None
    director_name: str | None = None
    director_position: str | None = None
    legal_address: str | None = None
    actual_address: str | None = None
    dispatch_phone: str | None = None
    email: str | None = None
    manager_name: str | None = None
    certificate_number: str | None = None
    certificate_date: str | None = None
    certificate_valid_until: str | None = None
    permitted_work_types: list[str] | None = None
    equipment_passport: list[str] | None = None
    staff_count: str | None = None
    readiness_mode: str | None = None
    service_area: str | None = None
    region: str | None = None
    is_active: bool | None = None
    notes: str | None = None


def _to_dict(obj) -> dict:
    return {
        "id": str(obj.id),
        "name": obj.name,
        "short_name": obj.short_name,
        "organization_type": obj.organization_type,
        "director_name": obj.director_name,
        "director_position": obj.director_position,
        "legal_address": obj.legal_address,
        "actual_address": obj.actual_address,
        "dispatch_phone": obj.dispatch_phone,
        "email": obj.email,
        "manager_name": obj.manager_name,
        "certificate_number": obj.certificate_number,
        "certificate_date": obj.certificate_date,
        "certificate_valid_until": obj.certificate_valid_until,
        "permitted_work_types": obj.permitted_work_types or [],
        "equipment_passport": obj.equipment_passport or [],
        "staff_count": obj.staff_count,
        "readiness_mode": obj.readiness_mode,
        "service_area": obj.service_area,
        "region": obj.region,
        "is_active": bool(obj.is_active) if obj.is_active is not None else True,
        "notes": obj.notes,
        "created_at": obj.created_at.isoformat() if obj.created_at else None,
        "updated_at": obj.updated_at.isoformat() if obj.updated_at else None,
    }


@router.get("/")
async def list_pasf(
    search: str | None = Query(None),
    repo: EmergencyRescueUnitRepository = Depends(get_emergency_rescue_unit_repo),
):
    if search:
        items = await repo.search(search)
    else:
        items = await repo.get_multi(limit=200)
    return [_to_dict(item) for item in items]


@router.get("/{pasf_id}")
async def get_pasf(pasf_id: UUID, repo: EmergencyRescueUnitRepository = Depends(get_emergency_rescue_unit_repo)):
    item = await repo.get(pasf_id)
    if not item:
        raise HTTPException(status_code=404, detail="ПАСФ не найден")
    return _to_dict(item)


@router.post("/")
async def create_pasf(data: PasfCreateRequest, repo: EmergencyRescueUnitRepository = Depends(get_emergency_rescue_unit_repo)):
    item = await repo.create(data.model_dump(exclude_none=True))
    return _to_dict(item)


@router.patch("/{pasf_id}")
async def update_pasf(pasf_id: UUID, data: PasfUpdateRequest, repo: EmergencyRescueUnitRepository = Depends(get_emergency_rescue_unit_repo)):
    item = await repo.update(pasf_id, data.model_dump(exclude_unset=True))
    if not item:
        raise HTTPException(status_code=404, detail="ПАСФ не найден")
    return _to_dict(item)


@router.delete("/{pasf_id}")
async def delete_pasf(pasf_id: UUID, repo: EmergencyRescueUnitRepository = Depends(get_emergency_rescue_unit_repo)):
    deleted = await repo.delete(pasf_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="ПАСФ не найден")
    return {"ok": True}


@router.get("/export/csv")
async def export_pasf_csv(
    search: str | None = Query(None),
    repo: EmergencyRescueUnitRepository = Depends(get_emergency_rescue_unit_repo),
):
    if search:
        items = await repo.search(search)
    else:
        items = await repo.get_multi(limit=10000)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Наименование", "Краткое название", "Юридический адрес", "Фактический адрес",
        "Телефон диспетчера", "Email", "Руководитель", "Номер свидетельства",
        "Дата свидетельства", "Свидетельство действительно до", "Кол-во сотрудников",
        "Режим готовности", "Район обслуживания", "Примечания"
    ])
    for item in items:
        writer.writerow([
            item.name or "", item.short_name or "", item.legal_address or "",
            item.actual_address or "", item.dispatch_phone or "", item.email or "",
            item.manager_name or "", item.certificate_number or "",
            item.certificate_date or "", item.certificate_valid_until or "",
            item.staff_count or "", item.readiness_mode or "",
            item.service_area or "", item.notes or ""
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=pasf_export.csv"}
    )
