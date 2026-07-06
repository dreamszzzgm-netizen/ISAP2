"""Streaming API для генерации ПМЛА с прогрессом (SSE)."""
import asyncio
import json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from src.api.dependencies import (
    get_document_repo,
    get_facility_repo,
    get_opo_details_repo,
    get_pmla_sample_repo,
    get_regulatory_repo,
    get_scenario_matrix_repo,
)
from src.application.services.pmla_generation_service import PmlaGenerationService
from src.infrastructure.repositories.document_repo import DocumentRepository
from src.infrastructure.repositories.regulatory_repo import RegulatoryRepository
from src.infrastructure.repositories.scenario_matrix_repo import ScenarioMatrixRepository

logger = logging.getLogger(__name__)
router = APIRouter()


async def generate_with_progress(
    facility_id: UUID,
    document_repo: DocumentRepository,
    regulatory_repo: RegulatoryRepository,
    scenario_matrix_repo: ScenarioMatrixRepository | None = None,
    sample_repo=None,
    opo_repo=None,
    facility_repo=None,
):
    """Генератор SSE-событий с прогрессом."""

    yield _sse("progress", {"step": "init", "message": "Инициализация компонентов...", "percent": 0})
    await asyncio.sleep(0.1)

    service = PmlaGenerationService(
        document_repo=document_repo,
        regulatory_repo=regulatory_repo,
        scenario_matrix_repo=scenario_matrix_repo,
        sample_repo=sample_repo,
        opo_repo=opo_repo,
        facility_repo=facility_repo,
    )

    # Сборка контекста
    yield _sse("progress", {"step": "context", "message": "Сборка контекста...", "percent": 15})
    await asyncio.sleep(0.1)

    try:
        context = await service.build_context(facility_id)
        eq_count = len(context.get("equipment", []))
        sub_count = len(context.get("substances", []))
        persons_count = len(context.get("responsible_persons", []))
        yield _sse("progress", {
            "step": "context_ready",
            "message": f"Контекст: {eq_count} оборудование, {sub_count} веществ, {persons_count} лиц",
            "percent": 25,
            "context": {
                "equipment_count": eq_count,
                "substances_count": sub_count,
                "persons_count": persons_count,
            },
        })
    except ValueError as exc:
        yield _sse("error", {"message": str(exc)})
        return

    await asyncio.sleep(0.1)

    # Создание записи документа
    yield _sse("progress", {"step": "create_doc", "message": "Создание документа...", "percent": 30})
    await asyncio.sleep(0.1)

    try:
        result = await service.generate(facility_id=facility_id, context=context)
    except Exception as exc:
        logger.exception("PMLA stream generation failed")
        yield _sse("error", {"message": f"Ошибка генерации: {exc}"})
        return

    yield _sse("progress", {
        "step": "complete",
        "message": "Документ успешно сгенерирован",
        "percent": 100,
        "document_id": result["document_id"],
        "status": result["status"],
    })


def _sse(event: str, data: dict) -> str:
    """Форматирование SSE-события."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/generate/stream")
async def generate_stream(
    facility_id: UUID,
    document_repo: DocumentRepository = Depends(get_document_repo),
    regulatory_repo: RegulatoryRepository = Depends(get_regulatory_repo),
    scenario_matrix_repo: ScenarioMatrixRepository = Depends(get_scenario_matrix_repo),
    sample_repo=Depends(get_pmla_sample_repo),
    opo_repo=Depends(get_opo_details_repo),
    facility_repo_dep=Depends(get_facility_repo),
):
    """Генерация ПМЛА с прогрессом в реальном времени (SSE)."""
    return StreamingResponse(
        generate_with_progress(
            facility_id, document_repo, regulatory_repo,
            scenario_matrix_repo, sample_repo, opo_repo, facility_repo_dep,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
