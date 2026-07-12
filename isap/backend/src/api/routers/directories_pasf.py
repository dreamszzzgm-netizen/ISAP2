"""CRUD endpoints for ПАСФ / АСФ directory."""
from __future__ import annotations

import csv
import hashlib
import io
import os
import shutil
from datetime import UTC, date, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db, get_emergency_rescue_unit_repo
from src.infrastructure.database.models import (
    EmergencyRescueUnitModel,
    PasfDocumentModel,
)
from src.infrastructure.repositories.emergency_rescue_unit_repo import (
    EmergencyRescueUnitRepository,
)

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


# ── PASF Documents (certificates, passports, contracts, licenses) ─────

from src.core.settings import settings

PASF_DOCUMENTS_UPLOAD_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", settings.upload_root, "pasf_documents"
)
os.makedirs(PASF_DOCUMENTS_UPLOAD_DIR, exist_ok=True)

ALLOWED_PASF_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
}

ALLOWED_PASF_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}

MAX_PASF_FILE_SIZE = settings.max_upload_file_size_mb * 1024 * 1024

PASF_DOCUMENT_TYPES = ["certificate", "asf_passport", "contract", "license", "other"]


class PasfDocumentResponse(BaseModel):
    id: str
    pasf_id: str
    document_type: str
    document_number: str | None
    title: str | None
    issued_at: str | None
    valid_until: str | None
    file_name: str | None
    file_size: int | None
    mime_type: str | None
    checksum_sha256: str | None
    status: str
    verified_at: str | None
    verified_by: str | None
    notes: str | None
    created_at: str | None
    updated_at: str | None


class PasfDocumentUpdateRequest(BaseModel):
    document_type: str | None = None
    document_number: str | None = None
    title: str | None = None
    issued_at: str | None = None
    valid_until: str | None = None
    status: str | None = None
    verified_by: str | None = None
    notes: str | None = None


def _pasf_document_to_dict(doc: PasfDocumentModel) -> dict:
    return {
        "id": str(doc.id),
        "pasf_id": str(doc.pasf_id),
        "document_type": doc.document_type,
        "document_number": doc.document_number,
        "title": doc.title,
        "issued_at": doc.issued_at.isoformat() if doc.issued_at else None,
        "valid_until": doc.valid_until.isoformat() if doc.valid_until else None,
        "file_name": doc.file_name,
        "file_size": doc.file_size,
        "mime_type": doc.mime_type,
        "checksum_sha256": doc.checksum_sha256,
        "status": doc.status or "active",
        "verified_at": doc.verified_at.isoformat() if doc.verified_at else None,
        "verified_by": doc.verified_by,
        "notes": doc.notes,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
        "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
    }


def _validate_pasf_document_file(file: UploadFile) -> None:
    """Validate MIME type, extension, and size of uploaded file."""
    # Extension check
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_PASF_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Недопустимое расширение файла: {ext}. Разрешены: {', '.join(ALLOWED_PASF_EXTENSIONS)}",
        )
    # MIME type from upload
    if file.content_type and file.content_type not in ALLOWED_PASF_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Недопустимый MIME тип: {file.content_type}. Разрешены: PDF, JPEG, PNG",
        )


@router.get("/{pasf_id}/documents")
async def list_pasf_documents(
    pasf_id: UUID,
    document_type: str | None = Query(None),
    status: str | None = Query(None),
    include_expired: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    repo: EmergencyRescueUnitRepository = Depends(get_emergency_rescue_unit_repo),
):
    """List documents for a PASF unit."""
    # Verify PASF exists
    pasf = await repo.get(pasf_id)
    if not pasf:
        raise HTTPException(status_code=404, detail="ПАСФ не найден")

    query = select(PasfDocumentModel).where(PasfDocumentModel.pasf_id == pasf_id)
    if document_type:
        query = query.where(PasfDocumentModel.document_type == document_type)
    if status:
        query = query.where(PasfDocumentModel.status == status)
    if not include_expired:
        query = query.where(
            (PasfDocumentModel.valid_until >= date.today())
            | (PasfDocumentModel.valid_until.is_(None))
        )
    query = query.order_by(PasfDocumentModel.created_at.desc())

    result = await db.execute(query)
    docs = result.scalars().all()
    return [_pasf_document_to_dict(d) for d in docs]


@router.get("/{pasf_id}/documents/{document_id}")
async def get_pasf_document(
    pasf_id: UUID,
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    repo: EmergencyRescueUnitRepository = Depends(get_emergency_rescue_unit_repo),
):
    """Get a single PASF document by ID."""
    pasf = await repo.get(pasf_id)
    if not pasf:
        raise HTTPException(status_code=404, detail="ПАСФ не найден")

    result = await db.execute(
        select(PasfDocumentModel).where(
            PasfDocumentModel.id == document_id,
            PasfDocumentModel.pasf_id == pasf_id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Документ ПАСФ не найден")
    return _pasf_document_to_dict(doc)


@router.post("/{pasf_id}/documents", status_code=201)
async def upload_pasf_document(
    pasf_id: UUID,
    file: UploadFile = File(...),
    document_type: str = Form("certificate"),
    document_number: str | None = Form(None),
    title: str | None = Form(None),
    issued_at: str | None = Form(None),
    valid_until: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    repo: EmergencyRescueUnitRepository = Depends(get_emergency_rescue_unit_repo),
):
    """Upload a document for a PASF unit."""
    # Verify PASF exists
    pasf = await repo.get(pasf_id)
    if not pasf:
        raise HTTPException(status_code=404, detail="ПАСФ не найден")

    if document_type not in PASF_DOCUMENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Недопустимый тип документа: {document_type}. Допустимы: {', '.join(PASF_DOCUMENT_TYPES)}",
        )

    # Validate file
    _validate_pasf_document_file(file)

    # Read file content
    content = await file.read()
    if len(content) > MAX_PASF_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Файл слишком большой. Максимальный размер: {MAX_PASF_FILE_SIZE // (1024*1024)} MB",
        )

    # SHA-256
    checksum = hashlib.sha256(content).hexdigest()

    # Safe filename — store relative path (storage_key) in DB
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = f"{ts}_{pasf_id.hex[:8]}_{file.filename}"
    relative_path = os.path.join("pasf_documents", safe_name)
    absolute_path = os.path.normpath(os.path.join(PASF_DOCUMENTS_UPLOAD_DIR, safe_name))

    # Security: ensure resolved path stays within upload root
    upload_root_abs = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "..", settings.upload_root)
    )
    if not absolute_path.startswith(upload_root_abs):
        raise HTTPException(status_code=400, detail="Некорректный путь файла")

    # Write to disk
    try:
        with open(absolute_path, "wb") as buf:
            buf.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка сохранения файла: {e}")

    file_size = os.path.getsize(absolute_path)
    mime_type = file.content_type or "application/octet-stream"
    ext = os.path.splitext(file.filename or "")[1].lstrip(".")

    # Parse dates
    parsed_issued = None
    if issued_at:
        try:
            parsed_issued = date.fromisoformat(issued_at)
        except ValueError:
            pass
    parsed_valid = None
    if valid_until:
        try:
            parsed_valid = date.fromisoformat(valid_until)
        except ValueError:
            pass

    doc = PasfDocumentModel(
        pasf_id=pasf_id,
        document_type=document_type,
        document_number=document_number,
        title=title or file.filename,
        issued_at=parsed_issued,
        valid_until=parsed_valid,
        file_path=file_path,
        file_name=file.filename,
        file_size=file_size,
        mime_type=mime_type,
        checksum_sha256=checksum,
        status="active",
        created_at=datetime.now(UTC),
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return _pasf_document_to_dict(doc)


@router.patch("/{pasf_id}/documents/{document_id}")
async def update_pasf_document(
    pasf_id: UUID,
    document_id: UUID,
    data: PasfDocumentUpdateRequest,
    db: AsyncSession = Depends(get_db),
    repo: EmergencyRescueUnitRepository = Depends(get_emergency_rescue_unit_repo),
):
    """Update PASF document metadata."""
    pasf = await repo.get(pasf_id)
    if not pasf:
        raise HTTPException(status_code=404, detail="ПАСФ не найден")

    result = await db.execute(
        select(PasfDocumentModel).where(
            PasfDocumentModel.id == document_id,
            PasfDocumentModel.pasf_id == pasf_id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Документ ПАСФ не найден")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key in ("issued_at", "valid_until") and value:
            try:
                value = date.fromisoformat(str(value))
            except ValueError:
                continue
        if key == "verified_at" and value:
            try:
                value = datetime.fromisoformat(str(value))
            except ValueError:
                continue
        setattr(doc, key, value)

    doc.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(doc)
    return _pasf_document_to_dict(doc)


@router.delete("/{pasf_id}/documents/{document_id}")
async def delete_pasf_document(
    pasf_id: UUID,
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    repo: EmergencyRescueUnitRepository = Depends(get_emergency_rescue_unit_repo),
):
    """Delete PASF document (metadata only; file remains on disk)."""
    pasf = await repo.get(pasf_id)
    if not pasf:
        raise HTTPException(status_code=404, detail="ПАСФ не найден")

    result = await db.execute(
        select(PasfDocumentModel).where(
            PasfDocumentModel.id == document_id,
            PasfDocumentModel.pasf_id == pasf_id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Документ ПАСФ не найден")

    await db.delete(doc)
    await db.commit()
    return {"ok": True}


@router.get("/{pasf_id}/documents/{document_id}/download")
async def download_pasf_document(
    pasf_id: UUID,
    document_id: UUID,
    repo: EmergencyRescueUnitRepository = Depends(get_emergency_rescue_unit_repo),
    db: AsyncSession = Depends(get_db),
):
    """Download PASF document file."""
    pasf = await repo.get(pasf_id)
    if not pasf:
        raise HTTPException(status_code=404, detail="ПАСФ не найден")

    result = await db.execute(
        select(PasfDocumentModel).where(
            PasfDocumentModel.id == document_id,
            PasfDocumentModel.pasf_id == pasf_id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Документ ПАСФ не найден")
    if not doc.file_path or not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="Файл документа не найден на диске")
    if doc.status in ("revoked", "archived"):
        raise HTTPException(status_code=403, detail="Документ отозван или архивирован")

    return FileResponse(
        path=doc.file_path,
        filename=doc.file_name or f"document_{document_id}",
        media_type=doc.mime_type or "application/octet-stream",
    )
