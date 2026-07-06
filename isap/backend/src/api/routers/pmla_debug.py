"""PMLA debug endpoints.

These endpoints are for development diagnostics and quality control of the
PMLA generation pipeline. They use a deterministic reference object and do not
require customer data.
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from src.application.services.pmla_debug_service import PmlaDebugService

router = APIRouter()


class DebugContextRequest(BaseModel):
    context: dict | None = None


@router.get("/context")
async def get_reference_context() -> dict:
    """Return deterministic reference context for gas-consumption PMLA debugging."""
    return PmlaDebugService().reference_context()


@router.post("/validate-context")
async def validate_context(request: DebugContextRequest) -> dict:
    """Validate supplied context or the deterministic reference context."""
    service = PmlaDebugService()
    context = request.context or service.reference_context()
    return service.validate_context(context)


@router.post("/generate-test")
async def generate_test(request: DebugContextRequest) -> dict:
    """Run deterministic generation and save debug artifacts under /tmp/isap_pmla_debug."""
    service = PmlaDebugService()
    package = await service.generate_test_package(request.context)
    return {
        "package_id": package.package_id,
        "artifact_dir": package.artifact_dir,
        "artifacts": {
            "context": package.context_path,
            "rendered_sections": package.rendered_sections_path,
            "validation_report": package.validation_report_path,
            "docx": package.docx_path,
        },
        "section_count": package.section_count,
        "engine_report": package.engine_report,
        "quality": package.quality,
    }
