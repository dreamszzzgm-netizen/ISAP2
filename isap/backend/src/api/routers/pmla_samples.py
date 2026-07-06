"""Роутер образцов ПМЛА."""
import os
import shutil
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict

from src.api.dependencies import get_pmla_sample_repo
from src.infrastructure.repositories.pmla_sample_repo import PmlaSampleRepository

router = APIRouter()

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "uploads", "pmla_samples")
os.makedirs(UPLOAD_DIR, exist_ok=True)


class PmlaSampleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str | None
    file_name: str
    file_size: int
    file_type: str
    facility_type: str | None
    hazard_class: str | None
    is_active: int
    is_verified: int
    usage_count: int
    created_at: datetime | None


@router.post("/upload", response_model=PmlaSampleResponse, status_code=201)
async def upload_sample(
    file: UploadFile = File(...),
    title: str = Form(...),
    description: str | None = Form(None),
    facility_type: str | None = Form(None),
    hazard_class: str | None = Form(None),
    repo: PmlaSampleRepository = Depends(get_pmla_sample_repo),
):
    """Загрузить образец ПМЛА (DOCX или PDF)."""
    allowed = [".docx", ".pdf"]
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in allowed:
        raise HTTPException(status_code=400, detail=f"Разрешены: {', '.join(allowed)}")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = f"{ts}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_name)

    try:
        with open(file_path, "wb") as buf:
            shutil.copyfileobj(file.file, buf)
        file_size = os.path.getsize(file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка сохранения: {e}")

    sample = await repo.create({
        "title": title,
        "description": description,
        "file_path": file_path,
        "file_name": file.filename,
        "file_size": file_size,
        "file_type": ext.lstrip("."),
        "facility_type": facility_type,
        "hazard_class": hazard_class,
        "is_active": 1,
        "is_verified": 0,
        "usage_count": 0,
    })
    return sample


@router.get("/", response_model=list[PmlaSampleResponse])
async def list_samples(
    skip: int = 0,
    limit: int = 100,
    facility_type: str | None = None,
    hazard_class: str | None = None,
    repo: PmlaSampleRepository = Depends(get_pmla_sample_repo),
):
    """Список образцов ПМЛА."""
    filters = {"is_active": 1}
    if facility_type:
        filters["facility_type"] = facility_type
    if hazard_class:
        filters["hazard_class"] = hazard_class
    return await repo.get_multi(skip=skip, limit=limit, filters=filters)


@router.get("/{sample_id}", response_model=PmlaSampleResponse)
async def get_sample(
    sample_id: UUID,
    repo: PmlaSampleRepository = Depends(get_pmla_sample_repo),
):
    """Получить образец по ID."""
    sample = await repo.get(sample_id)
    if not sample:
        raise HTTPException(status_code=404, detail="Образец не найден")
    return sample


@router.get("/{sample_id}/preview")
async def preview_sample(
    sample_id: UUID,
    repo: PmlaSampleRepository = Depends(get_pmla_sample_repo),
):
    """Превью содержимого образца — секции и текст."""
    sample = await repo.get(sample_id)
    if not sample:
        raise HTTPException(status_code=404, detail="Образец не найден")
    if not os.path.exists(sample.file_path):
        raise HTTPException(status_code=404, detail="Файл не найден на диске")

    sections = []
    if sample.file_type == "docx":
        try:
            import docx
            d = docx.Document(sample.file_path)
            current_section = None
            for para in d.paragraphs:
                text = para.text.strip()
                if not text:
                    continue
                style_name = para.style.name if para.style else ""
                if "Heading" in style_name or (para.runs and para.runs[0].bold and len(text) > 5):
                    if current_section:
                        sections.append(current_section)
                    current_section = {"title": text, "content": []}
                elif current_section is not None:
                    current_section["content"].append(text)
                else:
                    current_section = {"title": "", "content": [text]}
            if current_section:
                sections.append(current_section)
        except Exception:
            sections = [{"title": "Ошибка чтения", "content": ["Не удалось прочитать DOCX файл"]}]

    return {
        "id": str(sample.id),
        "title": sample.title,
        "file_name": sample.file_name,
        "file_type": sample.file_type,
        "facility_type": sample.facility_type,
        "hazard_class": sample.hazard_class,
        "sections": sections,
    }


@router.get("/{sample_id}/download")
async def download_sample(
    sample_id: UUID,
    repo: PmlaSampleRepository = Depends(get_pmla_sample_repo),
):
    """Скачать файл образца."""
    sample = await repo.get(sample_id)
    if not sample:
        raise HTTPException(status_code=404, detail="Образец не найден")
    if not os.path.exists(sample.file_path):
        raise HTTPException(status_code=404, detail="Файл не найден на диске")

    await repo.update(sample_id, {"usage_count": (sample.usage_count or 0) + 1})

    media_type = (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if sample.file_type == "docx"
        else "application/pdf"
    )
    return FileResponse(
        path=sample.file_path,
        filename=sample.file_name,
        media_type=media_type,
    )


@router.put("/{sample_id}/verify")
async def verify_sample(
    sample_id: UUID,
    is_verified: bool = True,
    repo: PmlaSampleRepository = Depends(get_pmla_sample_repo),
):
    """Верифицировать образец (индексирует/удаляет из ChromaDB)."""
    sample = await repo.get(sample_id)
    if not sample:
        raise HTTPException(status_code=404, detail="Образец не найден")
    await repo.update(sample_id, {"is_verified": 1 if is_verified else 0})

    # Индексация/удаление из ChromaDB
    try:
        from src.application.services.sample_integration import SampleIntegrationService
        integration = SampleIntegrationService(repo)
        if is_verified:
            await integration.on_sample_verified(sample_id)
        else:
            await integration.on_sample_unverified(sample_id)
    except Exception:
        pass  # ChromaDB недоступен — не блокируем верификацию

    return {"status": "ok", "is_verified": is_verified}


@router.delete("/{sample_id}", status_code=204)
async def delete_sample(
    sample_id: UUID,
    repo: PmlaSampleRepository = Depends(get_pmla_sample_repo),
):
    """Удалить образец (мягкое удаление)."""
    sample = await repo.get(sample_id)
    if not sample:
        raise HTTPException(status_code=404, detail="Образец не найден")
    await repo.update(sample_id, {"is_active": 0})
