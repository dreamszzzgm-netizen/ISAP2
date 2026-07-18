"""Роутер ОПО — CRUD операции.

Источники истины:
- name, reg_number, hazard_class, address, commissioning_date — HazаrdousFacilityModel (существующие поля)
- opo_full_name — расширенное наименование ОПО
- classification — признаки классификации 4.1–4.12 (JSONB array)
- work_processes — процессы и работы 2.1–2.6 (JSONB dict)
- licensed_activities — ссылки на LicenseModel (JSONB array)
- composition_structures — здания, сооружения, площадки (JSONB array)
- nearby_hazardous — опасные вещества на других ОПО ближе 500м (JSONB array)
- properties.okved — отраслевой код ОКВЭД
- properties.oktmo — код ОКТМО
- properties.owner — сведения о собственнике

Composition API (GET /{id}/composition) агрегирует:
  composition_structures + EquipmentModel + HazardousSubstanceModel
"""
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy import select

from src.api.dependencies import get_document_repo, get_facility_repo, get_db
from src.infrastructure.database.models import (
    DocumentModel, EquipmentModel, HazardousSubstanceModel, LicenseModel,
)
from src.infrastructure.repositories.document_repo import DocumentRepository
from src.infrastructure.repositories.facility_repo import FacilityRepository

router = APIRouter()


# ═══════════════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════════════

VALID_CLASSIFICATION_CODES = {
    f"4.{i}" for i in range(1, 13)
}
VALID_WORK_PROCESS_KEYS = {f"2.{i}" for i in range(1, 7)}

# Разрешённые ключи properties ОПО
VALID_PROPERTIES_KEYS = {
    "okved",       # отраслевой код ОКВЭД
    "oktmo",       # код ОКТМО
    "owner",       # собственник при ином законном основании
    "owner_basis", # основание права собственности
}


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _facility_to_dict(fac) -> dict:
    """Build facility response dict including ОПО card fields."""
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
        "opo_full_name": getattr(fac, "opo_full_name", None) or "",
        "classification": getattr(fac, "classification", None) or [],
        "work_processes": getattr(fac, "work_processes", None) or {},
        "licensed_activities": getattr(fac, "licensed_activities", None) or [],
        "composition_structures": getattr(fac, "composition_structures", None) or [],
        "nearby_hazardous": getattr(fac, "nearby_hazardous", None) or [],
    }


async def _validate_license_ids(session, organization_id: UUID, license_ids: list[str]):
    """Validate that all license_id references exist and belong to the organization."""
    if not license_ids:
        return
    result = await session.execute(
        select(LicenseModel.id).where(
            LicenseModel.organization_id == organization_id,
            LicenseModel.id.in_([UUID(lid) for lid in license_ids]),
        )
    )
    valid_ids = {str(row[0]) for row in result.all()}
    invalid = set(license_ids) - valid_ids
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Лицензии не найдены или принадлежат другой организации: {invalid}",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Pydantic schemas
# ═══════════════════════════════════════════════════════════════════════════

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
    # --- ОПО card fields ---
    opo_full_name: str | None = None
    classification: list[str] | None = None
    work_processes: dict | None = None
    licensed_activities: list | None = None
    composition_structures: list | None = None
    nearby_hazardous: list | None = None

    @field_validator("properties")
    @classmethod
    def validate_properties(cls, v):
        if v:
            unknown = set(v.keys()) - VALID_PROPERTIES_KEYS
            if unknown:
                raise ValueError(
                    f"Недопустимые ключи в properties: {unknown}. "
                    f"Допустимы: {sorted(VALID_PROPERTIES_KEYS)}"
                )
        return v

    @field_validator("classification")
    @classmethod
    def validate_classification(cls, v):
        if v is not None:
            invalid = set(v) - VALID_CLASSIFICATION_CODES
            if invalid:
                raise ValueError(
                    f"Недопустимые коды классификации: {invalid}. "
                    f"Допустимы: {sorted(VALID_CLASSIFICATION_CODES)}"
                )
        return v

    @field_validator("work_processes")
    @classmethod
    def validate_work_processes(cls, v):
        if v is not None:
            unknown = set(v.keys()) - VALID_WORK_PROCESS_KEYS
            if unknown:
                raise ValueError(
                    f"Недопустимые ключи процессов: {unknown}. "
                    f"Допустимы: {sorted(VALID_WORK_PROCESS_KEYS)}"
                )
        return v

    @field_validator("licensed_activities")
    @classmethod
    def validate_licensed_activities(cls, v):
        if v is not None:
            for i, item in enumerate(v):
                if not isinstance(item, dict):
                    raise ValueError(f"Элемент {i}: должен быть объектом")
                if "license_id" not in item:
                    raise ValueError(f"Элемент {i}: отсутствует license_id")
        return v

    @field_validator("nearby_hazardous")
    @classmethod
    def validate_nearby_hazardous(cls, v):
        if v is not None:
            for i, item in enumerate(v):
                if not isinstance(item, dict):
                    raise ValueError(f"Элемент {i}: должен быть объектом")
                if "name" not in item:
                    raise ValueError(f"Элемент {i}: отсутствует name")
        return v


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
    # --- ОПО card fields ---
    opo_full_name: str | None = None
    classification: list[str] | None = None
    work_processes: dict | None = None
    licensed_activities: list | None = None
    composition_structures: list | None = None
    nearby_hazardous: list | None = None

    @field_validator("properties")
    @classmethod
    def validate_properties(cls, v):
        if v:
            unknown = set(v.keys()) - VALID_PROPERTIES_KEYS
            if unknown:
                raise ValueError(
                    f"Недопустимые ключи в properties: {unknown}. "
                    f"Допустимы: {sorted(VALID_PROPERTIES_KEYS)}"
                )
        return v

    @field_validator("classification")
    @classmethod
    def validate_classification(cls, v):
        if v is not None:
            invalid = set(v) - VALID_CLASSIFICATION_CODES
            if invalid:
                raise ValueError(
                    f"Недопустимые коды классификации: {invalid}. "
                    f"Допустимы: {sorted(VALID_CLASSIFICATION_CODES)}"
                )
        return v

    @field_validator("work_processes")
    @classmethod
    def validate_work_processes(cls, v):
        if v is not None:
            unknown = set(v.keys()) - VALID_WORK_PROCESS_KEYS
            if unknown:
                raise ValueError(
                    f"Недопустимые ключи процессов: {unknown}. "
                    f"Допустимы: {sorted(VALID_WORK_PROCESS_KEYS)}"
                )
        return v

    @field_validator("licensed_activities")
    @classmethod
    def validate_licensed_activities(cls, v):
        if v is not None:
            for i, item in enumerate(v):
                if not isinstance(item, dict):
                    raise ValueError(f"Элемент {i}: должен быть объектом")
                if "license_id" not in item:
                    raise ValueError(f"Элемент {i}: отсутствует license_id")
        return v

    @field_validator("nearby_hazardous")
    @classmethod
    def validate_nearby_hazardous(cls, v):
        if v is not None:
            for i, item in enumerate(v):
                if not isinstance(item, dict):
                    raise ValueError(f"Элемент {i}: должен быть объектом")
                if "name" not in item:
                    raise ValueError(f"Элемент {i}: отсутствует name")
        return v


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
    # --- ОПО card fields ---
    opo_full_name: str | None = None
    classification: list | None = None
    work_processes: dict | None = None
    licensed_activities: list | None = None
    composition_structures: list | None = None
    nearby_hazardous: list | None = None


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
    # --- ОПО card fields ---
    opo_full_name: str | None = None
    classification: list | None = None
    work_processes: dict | None = None
    licensed_activities: list | None = None
    composition_structures: list | None = None
    nearby_hazardous: list | None = None
    equipment: list[dict] = []
    substances: list[dict] = []
    documents: list[dict] = []


# ═══════════════════════════════════════════════════════════════════════════
# CRUD Endpoints
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/", response_model=FacilityResponse, status_code=201)
async def create_facility(
    data: FacilityCreate,
    repo: FacilityRepository = Depends(get_facility_repo),
    session=Depends(get_db),
):
    payload = data.model_dump()
    if payload.get("commissioning_date"):
        from datetime import date
        payload["commissioning_date"] = date.fromisoformat(payload["commissioning_date"])

    lic_ids = [item["license_id"] for item in (payload.get("licensed_activities") or [])]
    await _validate_license_ids(session, data.organization_id, lic_ids)

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
    return _facility_to_dict(fac)


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
    return [_facility_to_dict(f) for f in facs]


@router.get("/{facility_id}", response_model=FacilityResponse)
async def get_facility(
    facility_id: UUID,
    repo: FacilityRepository = Depends(get_facility_repo),
):
    fac = await repo.get(facility_id)
    if fac is None:
        raise HTTPException(status_code=404, detail="ОПО не найден")
    return _facility_to_dict(fac)


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

    base = _facility_to_dict(fac)
    base["equipment"] = equipment_list
    base["substances"] = substances_list
    base["documents"] = documents_list
    return FacilityFullResponse(**base)


@router.get("/{facility_id}/composition")
async def get_facility_composition(
    facility_id: UUID,
    repo: FacilityRepository = Depends(get_facility_repo),
    session=Depends(get_db),
):
    """Единый состав ОПО: площадки + здания/сооружения + оборудование + вещества.

    Источники:
    - composition_structures — здания, сооружения, площадки (JSONB на facility)
    - EquipmentModel — технические устройства (нормализованная таблица)
    - HazardousSubstanceModel — опасные вещества (нормализованная таблица)
    """
    fac = await repo.get(facility_id)
    if fac is None:
        raise HTTPException(status_code=404, detail="ОПО не найден")

    structures = getattr(fac, "composition_structures", None) or []

    eq_result = await session.execute(
        select(EquipmentModel).where(EquipmentModel.hazardous_facility_id == facility_id)
    )
    equipment = [
        {
            "id": str(e.id),
            "type": "equipment",
            "name": e.name,
            "equipment_type": e.equipment_type,
            "serial_number": e.serial_number,
            "manufacturer": e.manufacturer,
            "manufacture_year": e.manufacture_year,
            "specifications": e.specifications or {},
        }
        for e in eq_result.scalars().all()
    ]

    sub_result = await session.execute(
        select(HazardousSubstanceModel).where(
            HazardousSubstanceModel.hazardous_facility_id == facility_id
        )
    )
    substances = [
        {
            "id": str(s.id),
            "type": "substance",
            "name": s.name,
            "cas_number": s.cas_number,
            "quantity_kg": float(s.quantity_kg) if s.quantity_kg else None,
            "threshold_quantity_kg": float(s.threshold_quantity_kg) if s.threshold_quantity_kg else None,
            "hazard_properties": s.hazard_properties or {},
        }
        for s in sub_result.scalars().all()
    ]

    return {
        "facility_id": str(fac.id),
        "structures": structures,
        "equipment": equipment,
        "substances": substances,
        "total_equipment": len(equipment),
        "total_substances": len(substances),
        "total_structures": len(structures),
    }


@router.put("/{facility_id}", response_model=FacilityResponse)
async def update_facility(
    facility_id: UUID,
    data: FacilityUpdate,
    repo: FacilityRepository = Depends(get_facility_repo),
    session=Depends(get_db),
):
    update_data = data.model_dump(exclude_unset=True)
    if update_data.get("commissioning_date"):
        from datetime import date
        update_data["commissioning_date"] = date.fromisoformat(update_data["commissioning_date"])

    lic_activities = update_data.get("licensed_activities")
    if lic_activities is not None:
        existing = await repo.get(facility_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="ОПО не найден")
        lic_ids = [item["license_id"] for item in lic_activities]
        await _validate_license_ids(session, existing.organization_id, lic_ids)

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
    return _facility_to_dict(fac)


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
        svc = WordImportService()
        result = svc.import_facility(content)
        return result
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Ошибка импорта: {str(e)}")
