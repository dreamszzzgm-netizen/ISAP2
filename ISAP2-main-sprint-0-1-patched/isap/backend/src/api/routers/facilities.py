"""Роутер ОПО — CRUD операции."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, ConfigDict, field_serializer
from sqlalchemy import select

from src.api.dependencies import get_facility_repo, get_document_repo
from src.infrastructure.database.models import DocumentModel
from src.infrastructure.repositories.facility_repo import FacilityRepository
from src.infrastructure.repositories.document_repo import DocumentRepository

router = APIRouter()


class FacilityCreate(BaseModel):
    organization_id: UUID
    name: str
    reg_number: str | None = None
    hazard_class: int | None = None
    facility_type: str | None = None
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    commissioning_date: str | None = None
    inventory_number: str | None = None
    properties: dict = {}


class FacilityUpdate(BaseModel):
    name: str | None = None
    reg_number: str | None = None
    hazard_class: int | None = None
    facility_type: str | None = None
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    commissioning_date: str | None = None
    inventory_number: str | None = None
    properties: dict | None = None


class FacilityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    name: str
    reg_number: str | None
    hazard_class: int | None
    facility_type: str | None
    address: str | None
    latitude: float | None
    longitude: float | None
    commissioning_date: str | None = None
    inventory_number: str | None
    properties: dict


class FacilityFullResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    name: str
    reg_number: str | None
    hazard_class: int | None
    facility_type: str | None
    address: str | None
    latitude: float | None
    longitude: float | None
    commissioning_date: str | None
    inventory_number: str | None
    properties: dict
    equipment: list[dict] = []
    substances: list[dict] = []
    documents: list[dict] = []


@router.post("/", response_model=FacilityResponse, status_code=201)
async def create_facility(
    data: FacilityCreate,
    repo: FacilityRepository = Depends(get_facility_repo),
):
    payload = data.model_dump()
    if payload.get("commissioning_date"):
        from datetime import date
        payload["commissioning_date"] = date.fromisoformat(payload["commissioning_date"])

    # Автогеокодирование: если адрес есть, а координат нет — пробуем определить
    if payload.get("address") and not payload.get("latitude"):
        try:
            from src.infrastructure.geocoding.yandex import YandexGeocoder
            geocoder = YandexGeocoder()
            geo = await geocoder.geocode(payload["address"])
            if geo:
                payload["latitude"] = geo.lat
                payload["longitude"] = geo.lon
        except Exception:
            pass

    fac = await repo.create(payload)
    return {
        "id": fac.id,
        "organization_id": fac.organization_id,
        "name": fac.name,
        "reg_number": fac.reg_number,
        "hazard_class": fac.hazard_class,
        "facility_type": fac.facility_type,
        "address": fac.address,
        "latitude": float(fac.latitude) if fac.latitude else None,
        "longitude": float(fac.longitude) if fac.longitude else None,
        "commissioning_date": fac.commissioning_date.isoformat() if fac.commissioning_date else None,
        "inventory_number": fac.inventory_number,
        "properties": fac.properties or {},
    }


@router.get("/", response_model=list[FacilityResponse])
async def list_facilities(
    organization_id: UUID | None = None,
    skip: int = 0,
    limit: int = 100,
    repo: FacilityRepository = Depends(get_facility_repo),
):
    filters = {}
    if organization_id:
        filters["organization_id"] = organization_id
    facs = await repo.get_multi(skip=skip, limit=limit, filters=filters)
    # Конвертируем date в строку для JSON
    result = []
    for f in facs:
        result.append({
            "id": f.id,
            "organization_id": f.organization_id,
            "name": f.name,
            "reg_number": f.reg_number,
            "hazard_class": f.hazard_class,
            "facility_type": f.facility_type,
            "address": f.address,
            "latitude": float(f.latitude) if f.latitude else None,
            "longitude": float(f.longitude) if f.longitude else None,
            "commissioning_date": f.commissioning_date.isoformat() if f.commissioning_date else None,
            "inventory_number": f.inventory_number,
            "properties": f.properties or {},
        })
    return result


@router.get("/{facility_id}", response_model=FacilityResponse)
async def get_facility(
    facility_id: UUID,
    repo: FacilityRepository = Depends(get_facility_repo),
):
    fac = await repo.get(facility_id)
    if fac is None:
        raise HTTPException(status_code=404, detail="ОПО не найден")
    return {
        "id": fac.id,
        "organization_id": fac.organization_id,
        "name": fac.name,
        "reg_number": fac.reg_number,
        "hazard_class": fac.hazard_class,
        "facility_type": fac.facility_type,
        "address": fac.address,
        "latitude": float(fac.latitude) if fac.latitude else None,
        "longitude": float(fac.longitude) if fac.longitude else None,
        "commissioning_date": fac.commissioning_date.isoformat() if fac.commissioning_date else None,
        "inventory_number": fac.inventory_number,
        "properties": fac.properties or {},
    }


@router.get("/{facility_id}/full", response_model=FacilityFullResponse)
async def get_facility_full(
    facility_id: UUID,
    repo: FacilityRepository = Depends(get_facility_repo),
    document_repo: DocumentRepository = Depends(get_document_repo),
):
    """ОПО со всеми связанными данными: оборудование, вещества, документы."""
    fac_data = await repo.get_with_related(facility_id)
    if fac_data is None:
        raise HTTPException(status_code=404, detail="ОПО не найден")

    fac = fac_data.facility

    equipment_list = [
        {
            "id": str(e.id),
            "name": e.name,
            "equipment_type": e.equipment_type,
            "serial_number": e.serial_number,
            "manufacturer": e.manufacturer,
            "manufacture_year": e.manufacture_year,
        }
        for e in fac_data.equipment
    ]

    substances_list = [
        {
            "id": str(s.id),
            "name": s.name,
            "cas_number": s.cas_number,
            "quantity_kg": float(s.quantity_kg) if s.quantity_kg else None,
            "threshold_quantity_kg": float(s.threshold_quantity_kg) if s.threshold_quantity_kg else None,
        }
        for s in fac_data.substances
    ]

    docs_result = await document_repo.session.execute(
        select(DocumentModel).where(DocumentModel.hazardous_facility_id == facility_id)
    )
    documents = list(docs_result.scalars().all())
    documents_list = [
        {
            "id": str(d.id),
            "title": d.title,
            "status": d.status,
            "document_type": d.document_type,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in documents
    ]

    return FacilityFullResponse(
        id=fac.id,
        organization_id=fac.organization_id,
        name=fac.name,
        reg_number=fac.reg_number,
        hazard_class=fac.hazard_class,
        facility_type=fac.facility_type,
        address=fac.address,
        latitude=float(fac.latitude) if fac.latitude else None,
        longitude=float(fac.longitude) if fac.longitude else None,
        commissioning_date=fac.commissioning_date.isoformat() if fac.commissioning_date else None,
        inventory_number=fac.inventory_number,
        properties=fac.properties or {},
        equipment=equipment_list,
        substances=substances_list,
        documents=documents_list,
    )


@router.put("/{facility_id}", response_model=FacilityResponse)
async def update_facility(
    facility_id: UUID,
    data: FacilityUpdate,
    repo: FacilityRepository = Depends(get_facility_repo),
):
    update_data = data.model_dump(exclude_unset=True)
    if update_data.get("commissioning_date"):
        from datetime import date
        update_data["commissioning_date"] = date.fromisoformat(update_data["commissioning_date"])

    # Автогеокодирование: если адрес изменён и координаты не переданы — пробуем определить
    if update_data.get("address") and not update_data.get("latitude"):
        try:
            from src.infrastructure.geocoding.yandex import YandexGeocoder
            geocoder = YandexGeocoder()
            geo = await geocoder.geocode(update_data["address"])
            if geo:
                update_data["latitude"] = geo.lat
                update_data["longitude"] = geo.lon
        except Exception:
            pass

    fac = await repo.update(facility_id, update_data)
    if fac is None:
        raise HTTPException(status_code=404, detail="ОПО не найден")
    return {
        "id": fac.id,
        "organization_id": fac.organization_id,
        "name": fac.name,
        "reg_number": fac.reg_number,
        "hazard_class": fac.hazard_class,
        "facility_type": fac.facility_type,
        "address": fac.address,
        "latitude": float(fac.latitude) if fac.latitude else None,
        "longitude": float(fac.longitude) if fac.longitude else None,
        "commissioning_date": fac.commissioning_date.isoformat() if fac.commissioning_date else None,
        "inventory_number": fac.inventory_number,
        "properties": fac.properties or {},
    }


@router.delete("/{facility_id}", status_code=204)
async def delete_facility(
    facility_id: UUID,
    repo: FacilityRepository = Depends(get_facility_repo),
):
    deleted = await repo.delete(facility_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="ОПО не найден")


@router.post("/import-word")
async def import_facility_from_word(file: UploadFile = File(...)):
    """Импорт данных ОПО из Word-документа."""
    if not file.filename.endswith('.docx'):
        raise HTTPException(status_code=400, detail="Поддерживается только формат .docx")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Размер файла не должен превышать 10 МБ")

    try:
        from src.application.services.word_import_service import WordImportService
        service = WordImportService()
        result = service.import_from_word(content)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка обработки документа: {e}")
