"""Smart Import Center API."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db
from src.application.services.smart_import.service import SmartImportService

router = APIRouter()


class ConfirmImportRequest(BaseModel):
    """Optional binding parameters for PMLA questionnaire import.

    All fields are optional.  When omitted the created questionnaire will
    not be linked to any organisation or facility (draft mode).
    """
    organization_id: UUID | None = None
    facility_id: UUID | None = None


@router.get("/profiles")
async def list_import_profiles(db: AsyncSession = Depends(get_db)):
    """Return available import profiles and expected fields."""
    return SmartImportService(db).list_profiles()


@router.post("/{import_type}/preview")
async def preview_import(
    import_type: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload Excel/CSV/DOCX, map columns, validate rows and create preview job."""
    try:
        content = await file.read()
        return await SmartImportService(db).create_preview(
            import_type=import_type,
            filename=file.filename or "import.xlsx",
            content=content,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/jobs/{job_id}")
async def get_import_job(job_id: UUID, db: AsyncSession = Depends(get_db)):
    try:
        return await SmartImportService(db).get_job(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/jobs/{job_id}/rows")
async def get_import_rows(
    job_id: UUID,
    limit: int = 200,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await SmartImportService(db).get_rows(job_id, limit=limit, offset=offset)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/jobs/{job_id}/confirm")
async def confirm_import(
    job_id: UUID,
    request: ConfirmImportRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Apply valid preview rows to target tables.

    For ``pmla_questionnaire`` imports, optional ``organization_id`` and
    ``facility_id`` can be provided to bind the created questionnaire to
    existing records.  When omitted the questionnaire is saved as a draft
    without binding.
    """
    try:
        return await SmartImportService(db).confirm_import(
            job_id,
            bind_params=request.model_dump() if request else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
