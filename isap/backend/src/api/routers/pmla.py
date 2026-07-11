"""Роутер ПМЛА — генерация, статус, ревью, скачивание."""
import io
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator

from src.api.dependencies import (
    get_document_repo,
    get_facility_repo,
    get_opo_details_repo,
    get_pmla_sample_repo,
    get_regulatory_repo,
    get_scenario_matrix_repo,
)
from src.application.services.calculations import (
    CalculationRegistry,  # noqa: F401 — регистрация методик
)
from src.application.services.pmla_export_service import PmlaExportService
from src.application.services.pmla_generation_service import PmlaGenerationService
from src.application.services.pmla_query_service import PmlaQueryService
from src.application.services.pmla_review_workflow_service import (
    PmlaReviewWorkflowService,
)
from src.infrastructure.repositories.document_repo import DocumentRepository
from src.infrastructure.repositories.regulatory_repo import RegulatoryRepository
from src.infrastructure.repositories.scenario_matrix_repo import (
    ScenarioMatrixRepository,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Импорт модулей расчёта для регистрации методик
from src.application.services.calculations import (
    explosion_zone,  # noqa: F401
    thermal_radiation,  # noqa: F401
    toxic_exposure,  # noqa: F401
)


class GeneratePMLARequest(BaseModel):
    facility_id: UUID
    context: dict | None = None
    regenerate_sections: list[str] | None = None
    template_version: str = "v1"

    @field_validator("template_version")
    @classmethod
    def _validate_template_version(cls, v: str) -> str:
        v_lower = v.lower().strip()
        if v_lower not in ("v1", "v2"):
            raise ValueError("template_version must be 'v1' or 'v2'")
        return v_lower


class ReviewRequest(BaseModel):
    reviewer_id: str | UUID = "anonymous"
    decision: str  # approved | rejected
    comments: list[dict] | None = None


class RegenerateRequest(BaseModel):
    sections: list[str]


def _context_debug_checks(context: dict) -> dict:
    """Return a compact checklist for the context sent into PMLA generation."""
    checks = {}
    required_blocks = (
        "organization",
        "facility",
        "equipment",
        "substances",
        "responsible_persons",
        "emergency_services",
        "protective_equipment",
        "insurance",
    )
    for key in required_blocks:
        value = context.get(key)
        checks[key] = {
            "present": key in context,
            "non_empty": bool(value),
            "type": type(value).__name__ if value is not None else None,
        }

    reserve = context.get("financial_reserve", context.get("material_reserve"))
    checks["financial_reserve"] = {
        "present": "financial_reserve" in context or "material_reserve" in context,
        "non_empty": bool(reserve),
        "type": type(reserve).__name__ if reserve is not None else None,
        "source_key": "financial_reserve" if "financial_reserve" in context else "material_reserve",
    }
    return checks


def _build_generation_service(
    document_repo: DocumentRepository,
    regulatory_repo: RegulatoryRepository,
    scenario_matrix_repo: ScenarioMatrixRepository,
    sample_repo,
    opo_repo,
    facility_repo,
) -> PmlaGenerationService:
    return PmlaGenerationService(
        document_repo=document_repo,
        regulatory_repo=regulatory_repo,
        scenario_matrix_repo=scenario_matrix_repo,
        sample_repo=sample_repo,
        opo_repo=opo_repo,
        facility_repo=facility_repo,
    )


# ── Debug ──────────────────────────────────────────────────────────────

@router.get("/debug/context/{facility_id}")
async def debug_generation_context(
    facility_id: UUID,
    prefer_opo_context: bool = True,
    document_repo: DocumentRepository = Depends(get_document_repo),
    regulatory_repo: RegulatoryRepository = Depends(get_regulatory_repo),
    scenario_matrix_repo: ScenarioMatrixRepository = Depends(get_scenario_matrix_repo),
    sample_repo=Depends(get_pmla_sample_repo),
    opo_repo=Depends(get_opo_details_repo),
    facility_repo_dep=Depends(get_facility_repo),
):
    """Return the exact context that would be passed into PMLA generation."""
    service = _build_generation_service(
        document_repo, regulatory_repo, scenario_matrix_repo,
        sample_repo, opo_repo, facility_repo_dep,
    )
    try:
        context = await service.build_context(facility_id, prefer_opo_context=prefer_opo_context)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {
        "facility_id": str(facility_id),
        "prefer_opo_context": prefer_opo_context,
        "checks": _context_debug_checks(context),
        "context": context,
    }


# ── Generate ───────────────────────────────────────────────────────────

@router.post("/generate")
async def generate_pmla(
    request: GeneratePMLARequest,
    document_repo: DocumentRepository = Depends(get_document_repo),
    regulatory_repo: RegulatoryRepository = Depends(get_regulatory_repo),
    scenario_matrix_repo: ScenarioMatrixRepository = Depends(get_scenario_matrix_repo),
    sample_repo=Depends(get_pmla_sample_repo),
    opo_repo=Depends(get_opo_details_repo),
    facility_repo_dep=Depends(get_facility_repo),
):
    """Генерация ПМЛА. Возвращает document_id и статус processing."""
    service = _build_generation_service(
        document_repo, regulatory_repo, scenario_matrix_repo,
        sample_repo, opo_repo, facility_repo_dep,
    )
    try:
        result = await service.generate(
            facility_id=request.facility_id,
            context=request.context,
            regenerate_sections=request.regenerate_sections,
            template_version=request.template_version,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        logger.exception("PMLA generation failed")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера при генерации ПМЛА")


# ── Status / Preview ──────────────────────────────────────────────────

@router.get("/{document_id}/status")
async def get_pmla_status(
    document_id: UUID,
    document_repo: DocumentRepository = Depends(get_document_repo),
):
    """Получение статуса документа."""
    service = PmlaReviewWorkflowService(document_repo=document_repo)
    try:
        return await service.get_status(document_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/{document_id}/preview")
async def preview_pmla(
    document_id: UUID,
    document_repo: DocumentRepository = Depends(get_document_repo),
):
    """Превью документа ПМЛА — HTML-представление содержимого."""
    service = PmlaQueryService(document_repo)
    try:
        return await service.get_preview(document_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ── Review ─────────────────────────────────────────────────────────────

@router.post("/{document_id}/review")
async def review_pmla(
    document_id: UUID,
    request: ReviewRequest,
    document_repo: DocumentRepository = Depends(get_document_repo),
    regulatory_repo: RegulatoryRepository = Depends(get_regulatory_repo),
    scenario_matrix_repo: ScenarioMatrixRepository = Depends(get_scenario_matrix_repo),
    sample_repo=Depends(get_pmla_sample_repo),
):
    """Ревью документа (утверждение/возврат с авто-перегенерацией)."""
    service = PmlaReviewWorkflowService(
        document_repo=document_repo,
        regulatory_repo=regulatory_repo,
        scenario_matrix_repo=scenario_matrix_repo,
        sample_repo=sample_repo,
    )
    try:
        return await service.review(
            document_id=document_id,
            reviewer_id=request.reviewer_id,
            decision=request.decision,
            comments=request.comments,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ── Review Workflow (ручная проверка) ──────────────────────────────────

class ReviewWorkflowRequest(BaseModel):
    review_status: str
    review_comment: str | None = None
    reviewed_by: str | None = None


@router.get("/{document_id}/review")
async def get_document_review(
    document_id: UUID,
    document_repo: DocumentRepository = Depends(get_document_repo),
):
    """Получение статуса ручной проверки документа."""
    from src.application.services.document_review_service import DocumentReviewService
    service = DocumentReviewService(document_repo)
    try:
        return await service.get_review_status(document_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.patch("/{document_id}/review")
async def update_document_review(
    document_id: UUID,
    request: ReviewWorkflowRequest,
    document_repo: DocumentRepository = Depends(get_document_repo),
):
    """Обновление статуса ручной проверки документа."""
    from src.application.services.document_review_service import DocumentReviewService
    service = DocumentReviewService(document_repo)
    try:
        return await service.update_review_status(
            document_id=document_id,
            review_status=request.review_status,
            review_comment=request.review_comment,
            reviewed_by=request.reviewed_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ── Download ───────────────────────────────────────────────────────────

@router.get("/{document_id}/download")
async def download_pmla(
    document_id: UUID,
    document_repo: DocumentRepository = Depends(get_document_repo),
):
    """Скачивание DOCX по document_id."""
    service = PmlaExportService(document_repo)
    try:
        result = await service.get_docx(document_id)
        return StreamingResponse(
            io.BytesIO(result.content),
            media_type=result.media_type,
            headers={"Content-Disposition": f"attachment; filename={result.filename}"},
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/{document_id}/download/pdf")
async def download_pmla_pdf(
    document_id: UUID,
    document_repo: DocumentRepository = Depends(get_document_repo),
):
    """Скачивание PDF (конвертация из DOCX)."""
    service = PmlaExportService(document_repo)
    try:
        result = await service.get_pdf(document_id)
        return StreamingResponse(
            io.BytesIO(result.content),
            media_type=result.media_type,
            headers={"Content-Disposition": f"attachment; filename={result.filename}"},
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── List / Expiring / Overdue ─────────────────────────────────────────

@router.get("/")
async def list_pmla_documents(
    skip: int = 0,
    limit: int = 100,
    document_repo: DocumentRepository = Depends(get_document_repo),
):
    """Список документов ПМЛА."""
    service = PmlaQueryService(document_repo)
    return await service.list_documents(skip=skip, limit=limit)


@router.get("/expiring")
async def list_expiring_documents(
    days: int = 30,
    document_repo: DocumentRepository = Depends(get_document_repo),
):
    """Документы с истекающим сроком пересмотра."""
    service = PmlaQueryService(document_repo)
    return await service.list_expiring_documents(days=days)


@router.get("/overdue")
async def list_overdue_documents(
    document_repo: DocumentRepository = Depends(get_document_repo),
):
    """Просроченные документы."""
    service = PmlaQueryService(document_repo)
    return await service.list_overdue_documents()


# ── Regenerate ─────────────────────────────────────────────────────────

@router.post("/{document_id}/regenerate")
async def regenerate_sections(
    document_id: UUID,
    request: RegenerateRequest,
    document_repo: DocumentRepository = Depends(get_document_repo),
    regulatory_repo: RegulatoryRepository = Depends(get_regulatory_repo),
    scenario_matrix_repo: ScenarioMatrixRepository = Depends(get_scenario_matrix_repo),
    sample_repo=Depends(get_pmla_sample_repo),
):
    """Частичная перегенерация разделов ПМЛА."""
    service = _build_generation_service(
        document_repo, regulatory_repo, scenario_matrix_repo,
        sample_repo, None, None,
    )
    try:
        return await service.regenerate_sections(document_id, request.sections)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ── Version restore ────────────────────────────────────────────────────

@router.post("/{document_id}/restore/{version_id}")
async def restore_version(
    document_id: UUID,
    version_id: UUID,
    document_repo: DocumentRepository = Depends(get_document_repo),
):
    """Восстановление документа из старой версии."""
    service = PmlaReviewWorkflowService(document_repo=document_repo)
    try:
        return await service.restore_version(document_id, version_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ── AI Review ──────────────────────────────────────────────────────────

@router.post("/{document_id}/ai-review")
async def run_ai_review(
    document_id: UUID,
    document_repo: DocumentRepository = Depends(get_document_repo),
):
    """Запуск AI-ревью документа (ручной триггер)."""
    service = PmlaReviewWorkflowService(document_repo=document_repo)
    try:
        return await service.run_ai_review(document_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.get("/{document_id}/ai-review")
async def get_ai_review(
    document_id: UUID,
    document_repo: DocumentRepository = Depends(get_document_repo),
):
    """Результат AI-ревью документа."""
    service = PmlaReviewWorkflowService(document_repo=document_repo)
    try:
        return await service.get_ai_review(document_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ── Versions ───────────────────────────────────────────────────────────

@router.get("/{document_id}/versions")
async def list_document_versions(
    document_id: UUID,
    document_repo: DocumentRepository = Depends(get_document_repo),
):
    """История версий документа."""
    service = PmlaQueryService(document_repo)
    try:
        return await service.list_versions(document_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ── Calculation methods ────────────────────────────────────────────────

@router.get("/methods/list")
async def list_calculation_methods():
    """Список доступных расчётных методик."""
    return CalculationRegistry.list_methods()
