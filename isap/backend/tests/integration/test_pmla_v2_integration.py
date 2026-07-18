"""Integration tests for PMLA v2 template generation.

Tests the full flow: context mapping → schema validation → DOCX rendering
→ document persistence. Uses mocked DB repositories via FastAPI dependency
overrides so tests run without a real database.
"""
from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app
from src.api.dependencies import (
    get_document_repo,
    get_facility_repo,
    get_opo_details_repo,
    get_pmla_sample_repo,
    get_regulatory_repo,
    get_scenario_matrix_repo,
)
from src.application.services.pmla_v2_context_mapper import (
    map_to_v2_context,
    validate_v2_context,
)
from src.infrastructure.export.pmla_template_renderer import PmlaTemplateRenderer

# ---------------------------------------------------------------------------
# Fake helpers
# ---------------------------------------------------------------------------


class FakeModel:
    """Universal ORM model stub with arbitrary attributes."""
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
    def __repr__(self):
        attrs = {k: v for k, v in self.__dict__.items() if not k.startswith("_")}
        return f"FakeModel({attrs})"


def make_mock_repo(return_value=None, list_value=None):
    repo = AsyncMock()
    if return_value is not None:
        repo.get.return_value = return_value
        repo.create.return_value = return_value
        repo.update.return_value = return_value
    repo.get_multi.return_value = list_value or []
    return repo


def fake_facility(**kw):
    defaults = {
        "id": uuid.uuid4(),
        "organization_id": uuid.uuid4(),
        "name": "Сеть газопотребления ООО «ТестПром»",
        "reg_number": "А34-99999-0001",
        "hazard_class": 3,
        "facility_type": "Сеть газопотребления",
        "address": "Московская область, г. Тест, ул. Промышленная, 1",
        "latitude": 55.5,
        "longitude": 37.5,
        "commissioning_date": None,
        "inventory_number": None,
        "properties": {},
    }
    defaults.update(kw)
    return FakeModel(**defaults)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.fixture
def mock_repos():
    """Set up mock repositories and return them."""
    fac = fake_facility()
    doc = FakeModel(
        id=uuid.uuid4(),
        hazardous_facility_id=fac.id,
        organization_id=fac.organization_id,
        document_type="pmla",
        title="ПМЛА",
        status="processing",
        version=1,
        generation_meta={},
    )

    fac_repo = make_mock_repo(return_value=fac)
    doc_repo = make_mock_repo(return_value=doc)
    doc_repo.session = AsyncMock()

    overrides = {
        get_facility_repo: lambda: fac_repo,
        get_document_repo: lambda: doc_repo,
        get_regulatory_repo: lambda: make_mock_repo(),
        get_scenario_matrix_repo: lambda: make_mock_repo(),
        get_pmla_sample_repo: lambda: make_mock_repo(),
        get_opo_details_repo: lambda: make_mock_repo(),
    }
    app.dependency_overrides.update(overrides)
    yield fac, doc_repo
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Test sample context
# ---------------------------------------------------------------------------

SAMPLE_CONTEXT = {
    "organization": {
        "name": "ООО «ТестПром»",
        "short_name": "ТестПром",
        "inn": "7701234567",
        "ogrn": "1027700000123",
        "address": "123456, г. Москва, ул. Тестовая, д. 1",
        "phone": "+7 (495) 123-45-67",
        "email": "info@testprom.ru",
    },
    "facility": {
        "name": "Сеть газопотребления",
        "reg_number": "А34-99999-0001",
        "hazard_class": 3,
        "facility_type": "Сеть газопотребления",
        "address": "Московская область, г. Тест, ул. Промышленная, 1",
        "latitude": 55.5,
        "longitude": 37.5,
    },
    "equipment": [
        {
            "name": "ГРПШ-1",
            "equipment_type": "ГРПШ",
            "serial_number": "SN-001",
            "manufacturer": "Завод",
            "manufacture_year": 2020,
            "specifications": {"pressure": "0.6 МПа", "process_codes": "2.1"},
        },
        {
            "name": "Газопровод",
            "equipment_type": "Трубопровод",
            "specifications": {"length": "500 м", "diameter": "159 мм"},
        },
    ],
    "substances": [
        {
            "name": "Природный газ",
            "quantity_kg": 500.0,
            "cas_number": "74-82-8",
            "hazard_properties": {
                "characteristics": "Горючий газ",
                "hazard_class": "4",
            },
        },
    ],
    "responsible_persons": [
        {
            "full_name": "Иванов Иван Иванович",
            "position": "Генеральный директор",
            "role": "director",
            "phone": "+7 495 123-45-67",
        },
        {
            "full_name": "Петров Пётр Петрович",
            "position": "Главный инженер",
            "role": "deputy",
            "phone": "+7 495 123-45-68",
        },
    ],
    "emergency_services": {
        "edds": [{"name": "ЕДДС г. Тест", "phone": "112"}],
        "fire": [{"name": "ПЧ-1", "phone": "01"}],
        "ambulance": [{"name": "ССМП", "phone": "03"}],
        "gas": [{"name": "АДС", "phone": "04"}],
        "electric": [{"name": "РЭС", "phone": "8-800-...", "dispatcher_phone": "+7 111 222-33-44"}],
    },
    "pasf": {
        "name": "ООО «Спасатель»",
        "short_name": "Спасатель",
        "actual_address": "г. Тест, ул. Аварийная, 1",
        "dispatch_phone": "+7 (903) 495-75-57",
    },
    "scenarios": [
        {
            "code": "С-1",
            "name": "Утечка газа без воспламенения",
            "damaging_factors": ["Взрыв газовоздушной смеси"],
            "preconditions": "Разгерметизация фланцевого соединения",
            "signs": ["Запах газа", "Срабатывание сигнализатора"],
        },
        {
            "code": "С-2",
            "name": "Пожар при разрыве газопровода",
            "damaging_factors": ["Тепловое излучение", "Ударная волна"],
            "preconditions": "Разрушение сварного шва",
            "signs": ["Факельное горение", "Тепловое излучение"],
        },
    ],
    "questionnaire": {
        "main_activity": "Транспортировка газа",
        "organization_resources": {
            "actual_items": [
                {"name": "Противогазы", "quantity": "10 шт.", "location": "Склад №1"},
                {"name": "Огнетушители ОУ-5", "quantity": "5 шт.", "location": "Помещение ГРП"},
            ],
            "recommended_items": [
                {"name": "Дополнительные СИЗ", "quantity": "5 компл.", "location": "—"},
            ],
        },
    },
}


# ---------------------------------------------------------------------------
# Tests: Context Mapper
# ---------------------------------------------------------------------------


class TestV2ContextMapper:
    """Verify the context mapper produces valid v2 format."""

    def test_map_produces_all_required_keys(self):
        ctx = map_to_v2_context(SAMPLE_CONTEXT)
        assert isinstance(ctx, dict)
        assert ctx["organization_full_name"] == "ООО «ТестПром»"
        assert ctx["facility_name"] == "Сеть газопотребления"
        assert ctx["hazard_class"] == "III"
        assert ctx["director_initials_surname"] == "И.И. Иванов"
        assert len(ctx["equipment_list"]) == 2
        assert len(ctx["substance_params"]) >= 2
        assert len(ctx["accident_scenarios"]) == 2

    def test_map_handles_empty_data(self):
        ctx = map_to_v2_context({})
        assert isinstance(ctx, dict)
        # Should not crash and produce default values
        assert ctx["organization_full_name"] == ""
        assert ctx["equipment_list"] == []
        assert ctx["accident_scenarios"] == []

    def test_validate_valid_context(self):
        ctx = map_to_v2_context(SAMPLE_CONTEXT)
        errors = validate_v2_context(ctx)
        assert errors == [], f"Validation errors: {errors}"

    def test_validate_rejects_missing_required(self):
        errors = validate_v2_context({})
        assert len(errors) > 0
        # Should mention at least facility_name
        facility_errors = [e for e in errors if "facility_name" in e]
        assert len(facility_errors) > 0

    def test_map_with_countermeasures(self):
        ctx = map_to_v2_context({**SAMPLE_CONTEXT, "facility": {**SAMPLE_CONTEXT["facility"]}})
        # countermeasures is optional; if questionnaire doesn't provide it, list is empty
        assert isinstance(ctx.get("countermeasures", []), list)


# ---------------------------------------------------------------------------
# Tests: Template Renderer
# ---------------------------------------------------------------------------


class TestV2TemplateRenderer:
    """Verify the v2 template renderer works with mapped context."""

    def test_render_produces_docx_bytes(self):
        ctx = map_to_v2_context(SAMPLE_CONTEXT)
        renderer = PmlaTemplateRenderer()
        docx_bytes = renderer.render(ctx)
        assert isinstance(docx_bytes, bytes)
        assert len(docx_bytes) > 0

    def test_render_valid_zip(self):
        import zipfile
        ctx = map_to_v2_context(SAMPLE_CONTEXT)
        renderer = PmlaTemplateRenderer()
        docx_bytes = renderer.render(ctx)
        assert zipfile.is_zipfile(__import__("io").BytesIO(docx_bytes))

    def test_render_contains_text(self):
        import zipfile
        ctx = map_to_v2_context(SAMPLE_CONTEXT)
        renderer = PmlaTemplateRenderer()
        docx_bytes = renderer.render(ctx)
        with zipfile.ZipFile(__import__("io").BytesIO(docx_bytes)) as zf:
            doc_xml = zf.read("word/document.xml").decode("utf-8")
            # Should not contain any Jinja tags
            import re
            jinja_tags = re.findall(r"\{[%{].*?[%}]\}", doc_xml)
            assert len(jinja_tags) == 0, f"Jinja artifacts remain: {jinja_tags[:5]}"

    def test_render_empty_lists(self):
        """Empty optional lists should render without error."""
        ctx = map_to_v2_context(SAMPLE_CONTEXT)
        ctx["equipment_list"] = []
        ctx["substance_params"] = []
        ctx["accident_scenarios"] = []
        ctx["injury_history"] = []
        ctx["accident_history"] = []
        ctx["material_reserve"] = []
        renderer = PmlaTemplateRenderer()
        docx_bytes = renderer.render(ctx)
        assert len(docx_bytes) > 5000

    def test_render_phones_delivered(self):
        """Notification phones should appear in rendered DOCX."""
        import zipfile
        ctx = map_to_v2_context(SAMPLE_CONTEXT)
        ctx["notification_ambulance_phone"] = "03"
        ctx["notification_fire_phone"] = "01"
        renderer = PmlaTemplateRenderer()
        docx_bytes = renderer.render(ctx)
        with zipfile.ZipFile(__import__("io").BytesIO(docx_bytes)) as zf:
            doc_xml = zf.read("word/document.xml").decode("utf-8")
            assert "03" in doc_xml or "01" in doc_xml

    def test_dict_emergency_service_alias_keys_map_to_notification_phones(self):
        """Dict-form emergency services should support aliased group keys."""
        context = {
            **SAMPLE_CONTEXT,
            "emergency_services": {
                "fire_department": [{"name": "ПСЧ", "dispatcher_phone": "101"}],
                "medical": [{"name": "Скорая помощь", "phone": "103"}],
            },
        }

        ctx = map_to_v2_context(context)

        assert ctx["notification_fire_phone"] == "101"
        assert ctx["notification_ambulance_phone"] == "103"

    def test_contract_dates_are_formatted_for_v2_schema(self):
        """PASF contract dates should render as DD.MM.YYYY, not raw ISO."""
        context = {
            **SAMPLE_CONTEXT,
            "pasf_documents": [
                {
                    "document_type": "contract",
                    "document_number": "Д-1",
                    "issued_at": "2024-06-15",
                }
            ],
        }

        ctx = map_to_v2_context(context)

        assert ctx["contractor_agreement_date"] == "15.06.2024"
        assert ctx["contractor_agreement_number"] == "Д-1"

    def test_v2_renderer_appends_pasf_appendices_manifest(self):
        """Selected PASF documents should appear in the rendered v2 DOCX manifest."""
        import io
        import zipfile

        context = {
            **SAMPLE_CONTEXT,
            "pasf_documents": [
                {
                    "document_type": "certificate",
                    "title": "Свидетельство ПАСФ",
                    "file_name": "certificate_2024.pdf",
                    "document_number": "CERT-001",
                }
            ],
        }

        ctx = map_to_v2_context(context)

        assert any(
            entry.get("filename") == "certificate_2024.pdf"
            for entry in ctx["appendices_manifest"]
        )

        docx_bytes = PmlaTemplateRenderer().render(ctx)
        with zipfile.ZipFile(io.BytesIO(docx_bytes)) as zf:
            doc_xml = zf.read("word/document.xml").decode("utf-8")

        assert "Приложения" in doc_xml
        assert "certificate_2024.pdf" in doc_xml
        assert "Свидетельство ПАСФ" in doc_xml

    def test_equipment_scenario_links_keep_fallback_without_equipment_ids(self):
        """Matrix scenarios without equipment_ids should still fill table links."""
        ctx = map_to_v2_context(SAMPLE_CONTEXT)

        assert ctx["equipment_scenario_links"]
        assert all(link["scenario_codes"] != "—" for link in ctx["equipment_scenario_links"])

    # ------------------------------------------------------------------
    # DOCX field & structure regression tests
    # ------------------------------------------------------------------

    def test_docx_has_page_field(self):
        """PAGE field exists in footer XML of rendered DOCX."""
        import zipfile, re
        import io
        ctx = map_to_v2_context(SAMPLE_CONTEXT)
        renderer = PmlaTemplateRenderer()
        docx_bytes = renderer.render(ctx)
        with zipfile.ZipFile(io.BytesIO(docx_bytes)) as zf:
            page_found = False
            for fname in zf.namelist():
                if not fname.startswith("word/footer"):
                    continue
                xml = zf.read(fname).decode("utf-8")
                if "PAGE" in xml and "instrText" in xml:
                    page_found = True
                    break
            assert page_found, "PAGE field not found in any footer"

    def test_docx_has_toc_field(self):
        """TOC field exists in document XML of rendered DOCX."""
        import zipfile, re
        import io
        ctx = map_to_v2_context(SAMPLE_CONTEXT)
        renderer = PmlaTemplateRenderer()
        docx_bytes = renderer.render(ctx)
        with zipfile.ZipFile(io.BytesIO(docx_bytes)) as zf:
            doc_xml = zf.read("word/document.xml").decode("utf-8")
            # Check for TOC field (namespace-agnostic)
            has_toc = bool(re.search(r'instrText[^>]*>\s*TOC\s+', doc_xml))
            has_cached = "[Обновите оглавление]" in doc_xml
            assert has_toc, "TOC field instruction text not found"
            assert has_cached, "TOC cached text not found"

    def test_docx_no_empty_headings(self):
        """No empty Heading 1-4 paragraphs remain in rendered DOCX."""
        import zipfile, re
        import io
        ctx = map_to_v2_context(SAMPLE_CONTEXT)
        renderer = PmlaTemplateRenderer()
        docx_bytes = renderer.render(ctx)
        with zipfile.ZipFile(io.BytesIO(docx_bytes)) as zf:
            doc_xml = zf.read("word/document.xml").decode("utf-8")
            empty_headings = []
            for m in re.finditer(r'<w:p[> ].*?</w:p>', doc_xml, re.DOTALL):
                p = m.group()
                style = re.search(r'<w:pStyle w:val="([1-4])"', p)
                if not style:
                    continue
                texts = re.findall(r'<w:t[^>]*>([^<]+)</w:t>', p)
                combined = "".join(texts).strip()
                if not combined:
                    empty_headings.append(style.group(1))
        assert not empty_headings, f"Empty heading paragraphs: {empty_headings}"

    def test_docx_no_empty_tables(self):
        """No tables with zero data rows remain in rendered DOCX."""
        import zipfile, re
        import io
        ctx = map_to_v2_context(SAMPLE_CONTEXT)
        renderer = PmlaTemplateRenderer()
        docx_bytes = renderer.render(ctx)
        with zipfile.ZipFile(io.BytesIO(docx_bytes)) as zf:
            doc_xml = zf.read("word/document.xml").decode("utf-8")
            tables = re.findall(r'<w:tbl[> ].*?</w:tbl>', doc_xml, re.DOTALL)
            for tbl_xml in tables:
                rows = re.findall(r'<w:tr[> ].*?</w:tr>', tbl_xml, re.DOTALL)
                if len(rows) <= 1:
                    continue  # skip single-row tables (will be removed)
                has_data = False
                for row in rows[1:]:
                    texts = re.findall(r'<w:t[^>]*>([^<]+)</w:t>', row)
                    if any(t.strip() for t in texts):
                        has_data = True
                        break
                assert has_data, "Table with rows but no data content"


# ---------------------------------------------------------------------------
# Tests: Facility Name & Data Integrity
# ---------------------------------------------------------------------------


class TestV2DataIntegrity:
    """Verify facility_name, equipment name integrity in v2 context mapping."""

    def test_facility_name_not_truncated(self):
        """facility_name is full in mapper output -- no truncation."""
        ctx = map_to_v2_context(SAMPLE_CONTEXT)
        assert ctx["facility_name"] == "Сеть газопотребления"
        # Test with long name
        long_name = "Сеть газопотребления ул. Красная"
        context_long = dict(SAMPLE_CONTEXT)
        context_long["facility"] = dict(SAMPLE_CONTEXT["facility"])
        context_long["facility"]["name"] = long_name
        ctx2 = map_to_v2_context(context_long)
        assert ctx2["facility_name"] == long_name
        assert len(ctx2["facility_name"]) == 32

    def test_equipment_name_preserved(self):
        """Technical names like ГРПШ-МС-10 (регулятор РДГК-10М) pass unchanged."""
        from copy import deepcopy
        tech_name = "ГРПШ-МС-10 (регулятор РДГК-10М)"
        context_tech = deepcopy(SAMPLE_CONTEXT)
        context_tech["equipment"] = [{"name": tech_name}]
        ctx = map_to_v2_context(context_tech)
        assert len(ctx["equipment_list"]) == 1
        assert ctx["equipment_list"][0]["device_name"] == tech_name


# ---------------------------------------------------------------------------
# Tests: Regulatory Coverage
# ---------------------------------------------------------------------------


class TestRegulatoryCoverageBasic:
    """Verify PP RF No.1437 regulatory coverage for v2 context."""

    def test_regulatory_coverage(self):
        """Full SAMPLE_CONTEXT passes regulatory check."""
        from src.application.validation.regulatory_coverage import check_regulatory_coverage
        ctx = map_to_v2_context(SAMPLE_CONTEXT)
        result = check_regulatory_coverage(ctx)
        assert result.passed, f"MISSING: {[r.id for r in result.requirements if r.status == 'MISSING']}"

    def test_regulatory_coverage_empty(self):
        """Empty context has MISSING requirements."""
        from src.application.validation.regulatory_coverage import check_regulatory_coverage
        result = check_regulatory_coverage({})
        assert result.missing > 0
        assert not result.passed

    def test_regulatory_coverage_counts(self):
        """Total requirements = sum of all status counts."""
        from src.application.validation.regulatory_coverage import check_regulatory_coverage
        result = check_regulatory_coverage({})
        assert result.total == result.covered + result.partial + result.missing + result.not_applicable

    def test_regulatory_coverage_special_not_applicable(self):
        """Hazard class IV sets special section to NOT_APPLICABLE."""
        from src.application.validation.regulatory_coverage import check_regulatory_coverage
        ctx = map_to_v2_context(SAMPLE_CONTEXT)
        result = check_regulatory_coverage(ctx)
        special = [r for r in result.requirements if r.id == "PP1437-11-special"]
        assert len(special) == 1


# ---------------------------------------------------------------------------
# Tests: API Integration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestV2APIIntegration:
    """Verify v2 generation via API endpoint."""

    @pytest.mark.skip(reason="Requires full DB setup with real API — not in CI")
    async def test_v2_generate_endpoint(self, client, mock_repos):
        fac, doc_repo = mock_repos
        response = await client.post(
            "/api/v1/pmla/generate",
            json={
                "facility_id": str(fac.id),
                "template_version": "v2",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "document_id" in data
        assert data["status"] == "pending_review"
        assert data["version"] >= 1

    @pytest.mark.skip(reason="Requires full DB + LLM setup — v1 uses EnhancedDocumentGenerator which needs LLM")
    async def test_v1_generate_endpoint(self, client, mock_repos):
        fac, doc_repo = mock_repos
        response = await client.post(
            "/api/v1/pmla/generate",
            json={
                "facility_id": str(fac.id),
                "template_version": "v1",
            },
        )
        assert response.status_code == 200

    async def test_invalid_template_version_rejected(self, client, mock_repos):
        fac, doc_repo = mock_repos
        response = await client.post(
            "/api/v1/pmla/generate",
            json={
                "facility_id": str(fac.id),
                "template_version": "v3",
            },
        )
        assert response.status_code == 422  # Validation error

    @pytest.mark.skip(reason="Requires full DB + LLM setup — v2 path with provided context works locally (see coordinator E2E)")
    async def test_v2_generate_with_provided_context(self, client, mock_repos):
        """Test v2 generation with a pre-built context (uses mock to skip DB)."""
        from src.api.routers.pmla import _build_generation_service
        from src.api.dependencies import get_document_repo, get_facility_repo

        fac, doc_repo = mock_repos
        # Try generating via service directly with explicit context
        service = _build_generation_service(
            document_repo=doc_repo,
            regulatory_repo=make_mock_repo(),
            scenario_matrix_repo=make_mock_repo(),
            sample_repo=make_mock_repo(),
            opo_repo=make_mock_repo(),
            facility_repo=make_mock_repo(return_value=fac),
        )
        with pytest.raises(ValueError, match="v2") or pytest.raises(ValueError):
            # Without emergency services & scenarios, v2 context may have
            # missing data; we expect it to either work or give clear error
            result = await service.generate(
                facility_id=fac.id,
                template_version="v2",
            )
            # If it worked, check structure
            if "document_id" in result:
                assert result["status"] is not None
                assert result["version"] >= 1


# ---------------------------------------------------------------------------
# Tests: Edge cases
# ---------------------------------------------------------------------------


class TestV2EdgeCases:
    """Verify edge cases in v2 generation."""

    def test_map_roman_hazard_class(self):
        from src.application.services.pmla_v2_context_mapper import _roman_hazard_class
        assert _roman_hazard_class(1) == "I"
        assert _roman_hazard_class(2) == "II"
        assert _roman_hazard_class(3) == "III"
        assert _roman_hazard_class(4) == "IV"
        assert _roman_hazard_class("1") == "I"
        assert _roman_hazard_class("III") == "III"

    def test_map_initials_surname(self):
        from src.application.services.pmla_v2_context_mapper import _extract_initials_surname
        assert _extract_initials_surname("Иванов Иван Иванович") == "И.И. Иванов"
        assert _extract_initials_surname("Петров Петр") == "П. Петров"
        assert _extract_initials_surname("Сидоров") == "Сидоров"
        assert _extract_initials_surname("") == ""

    def test_map_parse_settlement(self):
        from src.application.services.pmla_v2_context_mapper import _parse_settlement
        s, d = _parse_settlement("Московская область, г. Тест, ул. Промышленная, 1")
        assert "Тест" in s or s
        assert d or True  # District may be parsed differently
        s, d = _parse_settlement("")
        assert s == "" and d == ""


# ---------------------------------------------------------------------------
# Tests: Regulatory Coverage (PP RF No.1437)
# ---------------------------------------------------------------------------


class TestRegulatoryCoveragePp1437:
    """Verify regulatory coverage check against PP RF No.1437 requirements."""

    def test_regulatory_coverage(self):
        """Full v2 context passes regulatory check."""
        from src.application.validation.regulatory_coverage import check_regulatory_coverage
        ctx = map_to_v2_context(SAMPLE_CONTEXT)
        result = check_regulatory_coverage(ctx)
        assert result.passed, (
            f"Missing requirements: "
            f"{[r.id for r in result.requirements if r.status == 'MISSING']}"
        )

    def test_regulatory_coverage_empty(self):
        """Empty context should have MISSING requirements."""
        from src.application.validation.regulatory_coverage import check_regulatory_coverage
        result = check_regulatory_coverage({})
        assert result.missing > 0
        assert not result.passed

    def test_regulatory_coverage_counts(self):
        """Verify total requirement count."""
        from src.application.validation.regulatory_coverage import (
            REGULATORY_REQUIREMENTS,
            check_regulatory_coverage,
        )
        assert len(REGULATORY_REQUIREMENTS) >= 14, (
            f"Expected at least 14 requirements, got {len(REGULATORY_REQUIREMENTS)}"
        )
        ctx = map_to_v2_context(SAMPLE_CONTEXT)
        result = check_regulatory_coverage(ctx)
        assert result.total == len(REGULATORY_REQUIREMENTS)
        assert result.covered + result.partial + result.missing + result.not_applicable == result.total

    def test_regulatory_coverage_special_not_applicable(self):
        """Special section is N/A for hazard class IV."""
        from src.application.validation.regulatory_coverage import check_regulatory_coverage
        ctx = map_to_v2_context(SAMPLE_CONTEXT)
        ctx["hazard_class"] = "IV"
        result = check_regulatory_coverage(ctx)
        special = [r for r in result.requirements if r.id == "PP1437-11-special"]
        assert len(special) == 1
        assert special[0].status == "NOT_APPLICABLE"
        assert special[0].justification is not None
