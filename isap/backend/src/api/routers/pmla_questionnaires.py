"""PMLA Questionnaire Builder API."""
from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db, get_document_repo, get_regulatory_repo, get_scenario_matrix_repo, get_pmla_sample_repo
from src.application.services.pmla_questionnaire_service import PmlaQuestionnaireService
from src.application.services.pmla_generation_from_questionnaire_service import PmlaGenerationFromQuestionnaireService
from src.infrastructure.repositories.document_repo import DocumentRepository
from src.infrastructure.repositories.regulatory_repo import RegulatoryRepository
from src.infrastructure.repositories.scenario_matrix_repo import ScenarioMatrixRepository

router = APIRouter()


class BlockUpdateRequest(BaseModel):
    data: dict | list | str | int | float | bool | None


class CustomScenarioRequest(BaseModel):
    title: str
    description: str | None = None
    source_equipment: str | None = None
    substance: str | None = None
    consequences: str | None = None
    personnel_actions: str | None = None


class GenerateFromQuestionnaireRequest(BaseModel):
    template_version: str = "v1"
    regenerate_sections: list[str] | None = None
    save_debug_artifacts: bool = True
    generation_mode: str = "final"

    @field_validator("template_version")
    @classmethod
    def _validate_template_version(cls, v: str) -> str:
        v_lower = v.lower().strip()
        if v_lower not in ("v1", "v2"):
            raise ValueError("template_version must be 'v1' or 'v2'")
        return v_lower

    @field_validator("generation_mode")
    @classmethod
    def _validate_generation_mode(cls, v: str) -> str:
        v_lower = v.lower().strip()
        if v_lower not in ("draft", "final"):
            raise ValueError("generation_mode must be 'draft' or 'final'")
        return v_lower


@router.post("/facility/{facility_id}")
async def create_questionnaire_for_facility(facility_id: UUID, db: AsyncSession = Depends(get_db)):
    try:
        return await PmlaQuestionnaireService(db).create_for_facility(facility_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/facility/{facility_id}")
async def get_questionnaire_by_facility(facility_id: UUID, db: AsyncSession = Depends(get_db)):
    try:
        return await PmlaQuestionnaireService(db).get_by_facility(facility_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{questionnaire_id}")
async def get_questionnaire(questionnaire_id: UUID, db: AsyncSession = Depends(get_db)):
    try:
        return await PmlaQuestionnaireService(db).get_by_id(questionnaire_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/{questionnaire_id}/blocks/{block_name}")
async def update_questionnaire_block(
    questionnaire_id: UUID,
    block_name: str,
    request: BlockUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await PmlaQuestionnaireService(db).update_block(questionnaire_id, block_name, request.data)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{questionnaire_id}/custom-scenarios")
async def add_custom_scenario(
    questionnaire_id: UUID,
    request: CustomScenarioRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await PmlaQuestionnaireService(db).add_custom_scenario(questionnaire_id, request.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{questionnaire_id}/custom-scenarios/{index}")
async def delete_custom_scenario(
    questionnaire_id: UUID,
    index: int,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await PmlaQuestionnaireService(db).remove_custom_scenario(questionnaire_id, index)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{questionnaire_id}/context")
async def build_generation_context(questionnaire_id: UUID, db: AsyncSession = Depends(get_db)):
    try:
        return await PmlaQuestionnaireService(db).build_generation_context(questionnaire_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{questionnaire_id}/generate")
async def generate_from_questionnaire(
    questionnaire_id: UUID,
    request: GenerateFromQuestionnaireRequest | None = None,
    document_repo: DocumentRepository = Depends(get_document_repo),
    regulatory_repo: RegulatoryRepository = Depends(get_regulatory_repo),
    scenario_matrix_repo: ScenarioMatrixRepository = Depends(get_scenario_matrix_repo),
    sample_repo=Depends(get_pmla_sample_repo),
    db: AsyncSession = Depends(get_db),
):
    """Generate PMLA using questionnaire-derived context.

    Supports ``generation_mode`` ("draft" | "final").
    To run preflight only, use ``POST /{questionnaire_id}/preflight``.
    """
    request = request or GenerateFromQuestionnaireRequest()
    try:
        # Build typed generation context
        from src.application.services.pmla_context_builder import PmlaContextBuilder

        q_service = PmlaQuestionnaireService(db)
        builder = PmlaContextBuilder(db)
        gen_ctx = await builder.from_questionnaire(q_service, questionnaire_id)
        gen_ctx.generation_mode = request.generation_mode

        # Always run preflight
        from src.application.services.pmla_preflight import run_preflight

        preflight_report = run_preflight(gen_ctx, generation_mode=gen_ctx.generation_mode)
        gen_ctx.preflight_status = preflight_report.status

        # Check if generation is blocked in final mode
        if request.generation_mode == "final" and preflight_report.has_blockers:
            return {
                "status": "blocked",
                "questionnaire_id": str(questionnaire_id),
                "reason": "Preflight validation failed",
                "preflight": preflight_report.to_dict(),
            }

        service = PmlaGenerationFromQuestionnaireService(
            document_repo=document_repo,
            regulatory_repo=regulatory_repo,
            scenario_matrix_repo=scenario_matrix_repo,
            sample_repo=sample_repo,
        )
        result = await service.generate(
            questionnaire_id=questionnaire_id,
            template_version=request.template_version,
            regenerate_sections=request.regenerate_sections,
            save_debug_artifacts=request.save_debug_artifacts,
            generation_mode=request.generation_mode,
            preflight_report=preflight_report,
            generation_context=gen_ctx,
        )
        return {
            "document_id": str(result.document_id),
            "questionnaire_id": str(result.questionnaire_id),
            "facility_id": str(result.facility_id),
            "status": result.status,
            "version": result.version,
            "context_quality": result.context_quality,
            "quality_review": result.quality_review,
            "debug_artifacts": result.debug_artifacts,
            "preflight": preflight_report.to_dict(),
            "provenance": {
                k: v.to_dict() for k, v in gen_ctx.provenance.items()
            },
        }
    except ValueError as exc:
        detail = str(exc)
        if "PMLA_V2_CONTEXT_VALIDATION_FAILED" in detail:
            raise HTTPException(status_code=400, detail=detail) from exc
        raise HTTPException(status_code=404, detail=detail) from exc
    except Exception as exc:  # noqa: BLE001 - API boundary
        raise HTTPException(status_code=500, detail=f"Ошибка генерации ПМЛА из анкеты: {exc}") from exc


@router.post("/{questionnaire_id}/preflight")
async def preflight_questionnaire(
    questionnaire_id: UUID,
    generation_mode: str = "final",
    db: AsyncSession = Depends(get_db),
):
    """Run preflight validation on questionnaire data without generating a document.

    Returns detailed preflight report with BLOCKER, WARNING, and INFO issues.
    """
    from src.application.services.pmla_context_builder import PmlaContextBuilder

    try:
        q_service = PmlaQuestionnaireService(db)
        builder = PmlaContextBuilder(db)
        gen_ctx = await builder.from_questionnaire(q_service, questionnaire_id)
        gen_ctx.generation_mode = generation_mode

        from src.application.services.pmla_preflight import run_preflight

        report = run_preflight(gen_ctx, generation_mode=gen_ctx.generation_mode)

        return {
            "questionnaire_id": str(questionnaire_id),
            "facility_id": str(gen_ctx.facility.get("id", "")),
            "preflight": report.to_dict(),
            "generation_mode": generation_mode,
            "generation_blocked": report.has_blockers and generation_mode == "final",
            "provenance": {
                k: v.to_dict() for k, v in gen_ctx.provenance.items()
            },
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{questionnaire_id}/documents")
async def list_questionnaire_documents(
    questionnaire_id: UUID,
    document_repo: DocumentRepository = Depends(get_document_repo),
):
    """Return all documents generated from this questionnaire, newest first."""
    docs = await document_repo.get_by_questionnaire(questionnaire_id)
    return [
        {
            "document_id": str(doc.id),
            "version": doc.version,
            "status": doc.status,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
            "quality_score": (doc.generation_meta or {}).get("quality_review", {}).get("score"),
            "quality_status": (doc.generation_meta or {}).get("quality_review", {}).get("overall_status"),
            "download_available": bool(doc.content_docx),
        }
        for doc in docs
    ]
