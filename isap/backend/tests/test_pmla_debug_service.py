import pytest

from src.application.services.pmla_debug_service import PmlaDebugService


@pytest.mark.asyncio
async def test_pmla_debug_reference_generation_creates_quality_package():
    service = PmlaDebugService()
    context = service.reference_context()

    validation = service.validate_context(context)
    assert validation["passed"] is True

    package = await service.generate_test_package(context)
    assert package.section_count >= 10
    assert package.quality["context_validation"]["passed"] is True
    assert package.quality["summary"]["non_empty_section_count"] == package.section_count
    assert package.quality["summary"]["placeholder_marker_count"] == 0
    assert package.docx_path.endswith("output.docx")
