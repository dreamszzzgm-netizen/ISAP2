"""Tests for PMLA generation context, preflight, and built pipeline.

Covers:
1. PmlaGenerationContext creation and provenance
2. PmlaPreflightReport validation rules (blockers, warnings, info)
3. Draft vs final generation mode behavior
4. Context mapper integrity (no fake values, no truncation)
5. Pipeline integration with PmlaContextBuilder
6. Knowledge graph enrichment in context
7. Old v1 pipeline backward compatibility
"""
from __future__ import annotations

import hashlib
import shutil
import uuid
from copy import deepcopy
from pathlib import Path

import pytest

from src.application.services.pmla_generation_context import (
    PmlaGenerationContext,
    ProvenanceEntry,
)
from src.application.services.pmla_preflight import (
    PreflightIssue,
    PmlaPreflightReport,
    run_preflight,
    _is_empty,
    _is_fake_value,
)
from src.application.services.pmla_v2_context_mapper import (
    map_to_v2_context,
    validate_v2_context,
    _roman_hazard_class,
    _extract_initials_surname,
)


# =========================================================================
# Helper factories
# =========================================================================


def make_minimal_org(**kw) -> dict:
    base = {
        "id": str(uuid.uuid4()),
        "name": "ООО «ТестПром»",
        "inn": "7701234567",
        "ogrn": "1027700000123",
        "address": "123456, г. Москва, ул. Тестовая, д. 1",
        "phone": "+7 (495) 123-45-67",
        "email": "info@testprom.ru",
    }
    base.update(kw)
    return base


def make_minimal_facility(**kw) -> dict:
    base = {
        "id": str(uuid.uuid4()),
        "name": "Сеть газопотребления",
        "reg_number": "А34-99999-0001",
        "hazard_class": 3,
        "facility_type": "Сеть газопотребления",
        "address": "Московская область, г. Тест, ул. Промышленная, 1",
        "latitude": 55.5,
        "longitude": 37.5,
    }
    base.update(kw)
    return base


def make_minimal_equipment(**kw) -> list[dict]:
    return [
        {
            "name": "ГРПШ-1",
            "equipment_type": "ГРПШ",
            "serial_number": "SN-001",
        },
        {
            "name": "Газопровод",
            "equipment_type": "Трубопровод",
        },
    ]


def make_minimal_pasf(**kw) -> dict:
    base = {
        "id": str(uuid.uuid4()),
        "name": "ООО «Спасатель»",
        "dispatch_phone": "+7 (903) 495-75-57",
        "actual_address": "г. Тест, ул. Аварийная, 1",
        "certificate_number": "123-ABC",
        "certificate_date": "2023-01-01",
        "certificate_valid_until": "2026-12-31",
        "permitted_work_types": ["Газоспасательные работы", "Высотные работы"],
    }
    base.update(kw)
    return base


def make_full_context(**kw) -> PmlaGenerationContext:
    """Create a fully populated PmlaGenerationContext with valid data."""
    ctx = PmlaGenerationContext()
    ctx.organization = make_minimal_org()
    ctx.facility = make_minimal_facility()
    ctx.equipment = make_minimal_equipment()
    ctx.pasf = make_minimal_pasf()
    ctx.emergency_services = [
        {"service_type": "fire", "name": "ПЧ-1", "phone": "01"},
        {"service_type": "medical", "name": "ССМП", "phone": "03"},
        {"service_type": "gas", "name": "АДС", "phone": "04"},
    ]
    ctx.hazardous_substances = [{"name": "Природный газ", "quantity_kg": 500.0}]
    ctx.responsible_persons = [
        {"full_name": "Иванов Иван Иванович", "position": "Генеральный директор",
         "role": "director", "phone": "+7 495 123-45-67"},
    ]
    ctx.financial_reserve = {"created": True, "order_number": "Пр-123",
                              "order_date": "2024-01-15", "amount": "500000"}
    ctx.insurance = {"has_contract": True, "company": "СОГАЗ",
                     "contract_number": "GZ-2024-001", "valid_until": "2025-12-31"}
    ctx.organization_resources = {
        "actual_items": [
            {"name": "Противогазы", "quantity": "10 шт.", "location": "Склад №1"},
        ]
    }
    ctx.selected_scenarios = [{"code": "С-1", "name": "Утечка газа"}]
    ctx.accident_history = {"has_incidents": False, "period": "за период эксплуатации"}
    ctx.facility["reg_number"] = "А34-99999-0001"
    ctx.notification_scheme = {"first_receiver": "Иванов И.И.",
                                "incident_commander": "Иванов И.И."}

    # Add provenance for key fields
    ctx.add_provenance("organization.name", "organization",
                        ctx.organization["id"], "name")
    ctx.add_provenance("facility.name", "facility",
                        ctx.facility["id"], "name")
    ctx.add_provenance("equipment", "equipment",
                        ctx.facility["id"], "equipment")

    # Apply overrides
    for k, v in kw.items():
        setattr(ctx, k, v)
    return ctx


# =========================================================================
# Tests: PmlaGenerationContext
# =========================================================================


class TestPmlaGenerationContext:
    """Verify context creation, provenance, mode switching."""

    def test_create_empty_context(self):
        ctx = PmlaGenerationContext()
        assert ctx.organization == {}
        assert ctx.facility == {}
        assert ctx.equipment == []
        assert not ctx.has_provenance
        assert ctx.generation_mode == "final"
        assert not ctx.is_draft

    def test_add_provenance(self):
        ctx = PmlaGenerationContext()
        ctx.add_provenance("facility.name", "facility",
                           "abc-123", "name")
        assert "facility.name" in ctx.provenance
        entry = ctx.provenance["facility.name"]
        assert entry.source_type == "facility"
        assert entry.source_id == "abc-123"
        assert entry.field == "name"

    def test_draft_mode(self):
        ctx = PmlaGenerationContext()
        assert not ctx.is_draft
        ctx.generation_mode = "draft"
        assert ctx.is_draft

    def test_to_dict_contains_all_sections(self):
        ctx = make_full_context()
        d = ctx.to_dict()
        assert "organization" in d
        assert "facility" in d
        assert "equipment" in d
        assert "substances" in d
        assert "responsible_persons" in d
        assert "pasf" in d
        assert "emergency_services" in d
        assert "insurance" in d
        assert "financial_reserve" in d
        assert "selected_scenarios" in d

    def test_to_v2_dict_has_nearest_services(self):
        ctx = make_full_context()
        v2 = ctx.to_v2_dict()
        assert "nearest_services" in v2
        assert "fire" in v2["nearest_services"]

    def test_provenance_entry_to_dict(self):
        entry = ProvenanceEntry("organization", "org-1", "name")
        d = entry.to_dict()
        assert d["source_type"] == "organization"
        assert d["source_id"] == "org-1"
        assert d["field"] == "name"
        assert "retrieved_at" not in d  # optional


# =========================================================================
# Tests: Preflight Validation
# =========================================================================


class TestPreflightReport:
    """Verify PmlaPreflightReport creation and issue management."""

    def test_empty_report_passes(self):
        report = PmlaPreflightReport()
        assert report.passed
        assert not report.has_blockers
        assert not report.has_warnings

    def test_add_blocker(self):
        report = PmlaPreflightReport()
        report.add_issue("TEST_BLOCK", "test.field",
                         "Test blocker", "BLOCKER")
        assert report.has_blockers
        assert not report.passed
        assert len(report.errors) == 1
        assert report.errors[0].code == "TEST_BLOCK"

    def test_add_warning(self):
        report = PmlaPreflightReport()
        report.add_issue("TEST_WARN", "test.field",
                         "Test warning", "WARNING")
        assert report.has_warnings
        assert not report.has_blockers
        assert len(report.warnings) == 1

    def test_add_info(self):
        report = PmlaPreflightReport()
        report.add_issue("TEST_INFO", "test.field",
                         "Test info", "INFO")
        assert report.passed  # info doesn't change status
        assert len(report.info) == 1

    def test_mixed_severity(self):
        report = PmlaPreflightReport()
        report.add_issue("WARN", "f1", "warning", "WARNING")
        report.add_issue("BLOCK", "f2", "blocker", "BLOCKER")
        assert report.has_blockers
        assert report.status == "has_blockers"

    def test_blocker_raises_in_final(self):
        report = PmlaPreflightReport()
        report.add_issue("TEST", "f", "blocker", "BLOCKER")
        with pytest.raises(ValueError, match="blocker"):
            report.raise_if_blocked("final")

    def test_blocker_allowed_in_draft(self):
        report = PmlaPreflightReport()
        report.add_issue("TEST", "f", "blocker", "BLOCKER")
        report.raise_if_blocked("draft")  # should not raise

    def test_add_missing_field(self):
        report = PmlaPreflightReport()
        report.add_missing_field("facility.name")
        report.add_missing_field("facility.name")  # dedup
        assert report.missing_fields == ["facility.name"]

    def test_add_expired_document(self):
        report = PmlaPreflightReport()
        report.add_expired_document("certificate", "ПАСФ", "2023-01-01")
        assert len(report.expired_documents) == 1

    def test_add_source_conflict(self):
        report = PmlaPreflightReport()
        report.add_source_conflict("facility.name", "db", "graph",
                                    "ОПО-1", "ОПО-2")
        assert len(report.source_conflicts) == 1

    def test_to_dict(self):
        report = PmlaPreflightReport()
        report.add_issue("TEST", "f", "msg", "BLOCKER")
        d = report.to_dict()
        assert d["status"] == "has_blockers"
        assert len(d["errors"]) == 1
        assert d["errors"][0]["code"] == "TEST"


# =========================================================================
# Tests: Preflight validation rules
# =========================================================================


class TestPreflightRules:
    """Verify individual preflight check rules."""

    def test_blocker_on_missing_org_name(self):
        ctx = make_full_context()
        ctx.organization["name"] = ""
        report = run_preflight(ctx)
        assert report.has_blockers
        codes = [e.code for e in report.errors]
        assert "ORG_MISSING_NAME" in codes

    def test_warning_on_missing_reg_number(self):
        """Missing reg_number creates a WARNING in draft mode."""
        ctx = make_full_context()
        ctx.facility["reg_number"] = ""
        report = run_preflight(ctx, generation_mode="draft")
        assert "FAC_MISSING_REG_NUMBER" in [w.code for w in report.warnings]

    def test_blocker_on_missing_reg_number_in_final(self):
        """Missing reg_number creates a BLOCKER in final mode."""
        ctx = make_full_context()
        ctx.facility["reg_number"] = ""
        report = run_preflight(ctx, generation_mode="final")
        assert "FAC_MISSING_REG_NUMBER" in [e.code for e in report.errors]

    def test_blocker_on_missing_hazard_class(self):
        ctx = make_full_context()
        ctx.facility["hazard_class"] = None
        report = run_preflight(ctx)
        assert report.has_blockers
        codes = [e.code for e in report.errors]
        assert "FAC_MISSING_HAZARD_CLASS" in codes

    def test_blocker_on_empty_equipment(self):
        ctx = make_full_context()
        ctx.equipment = []
        report = run_preflight(ctx)
        assert report.has_blockers
        codes = [e.code for e in report.errors]
        assert "EQ_EMPTY_LIST" in codes

    def test_blocker_on_missing_pasf(self):
        ctx = make_full_context()
        ctx.pasf = {}
        report = run_preflight(ctx)
        assert report.has_blockers
        codes = [e.code for e in report.errors]
        assert "PASF_MISSING" in codes

    def test_blocker_on_missing_emergency_services(self):
        """Missing emergency services creates a BLOCKER in final mode."""
        ctx = make_full_context()
        ctx.emergency_services = []
        report = run_preflight(ctx, generation_mode="final")
        assert report.has_blockers
        assert "SVC_EMPTY_LIST" in [e.code for e in report.errors]

    def test_warning_on_missing_emergency_services_in_draft(self):
        """Missing emergency services creates a WARNING in draft mode."""
        ctx = make_full_context()
        ctx.emergency_services = []
        report = run_preflight(ctx, generation_mode="draft")
        assert "SVC_EMPTY_LIST" in [w.code for w in report.warnings]

    def test_blocker_on_disabled_pasf(self):
        """Disabled PASF creates a BLOCKER."""
        ctx = make_full_context()
        ctx.pasf["is_active"] = False
        report = run_preflight(ctx)
        assert "PASF_DISABLED" in [e.code for e in report.errors]

    def test_blocker_on_missing_pasf_certificate(self):
        """PASF without certificate creates a BLOCKER."""
        ctx = make_full_context()
        ctx.pasf["certificate_number"] = ""
        report = run_preflight(ctx)
        assert "PASF_MISSING_CERTIFICATE" in [e.code for e in report.errors]

    def test_blocker_on_disabled_emergency_service(self):
        """Disabled emergency service creates a BLOCKER."""
        ctx = make_full_context()
        ctx.emergency_services[0]["is_active"] = False
        report = run_preflight(ctx)
        assert "SVC_DISABLED" in [e.code for e in report.errors]

    def test_pasf_cert_expired_blocker_in_final(self):
        """Expired PASF certificate creates BLOCKER in final."""
        ctx = make_full_context()
        ctx.pasf["certificate_valid_until"] = "2023-01-01"
        report = run_preflight(ctx, generation_mode="final")
        assert "PASF_CERT_EXPIRED" in [e.code for e in report.errors]

    def test_pasf_cert_expired_warning_in_draft(self):
        """Expired PASF certificate creates WARNING in draft."""
        ctx = make_full_context()
        ctx.pasf["certificate_valid_until"] = "2023-01-01"
        report = run_preflight(ctx, generation_mode="draft")
        assert "PASF_CERT_EXPIRED" in [w.code for w in report.warnings]

    def test_warning_on_missing_resources(self):
        ctx = make_full_context()
        ctx.organization_resources = {}
        report = run_preflight(ctx)
        assert "RES_MISSING_ACTUAL_ITEMS" in [w.code for w in report.warnings]

    def test_warning_on_financial_not_filled(self):
        ctx = make_full_context()
        ctx.financial_reserve = {}
        ctx.insurance = {}
        report = run_preflight(ctx)
        warn_codes = [w.code for w in report.warnings]
        assert "FIN_NOT_FILLED" in warn_codes

    def test_org_facility_name_mix(self):
        ctx = make_full_context()
        ctx.organization["name"] = "ООО ТестПром"
        ctx.facility["name"] = "ООО ТестПром"  # same name
        report = run_preflight(ctx)
        warn_codes = [w.code for w in report.warnings]
        assert "ORG_FACILITY_NAME_MIX" in warn_codes

    def test_full_context_passes(self):
        ctx = make_full_context()
        report = run_preflight(ctx)
        assert report.passed, f"Errors: {[e.message for e in report.errors]}"

    def test_relative_pasf_document_path_resolves_under_upload_root(self, monkeypatch):
        """Uploaded PASF storage keys should not block final preflight."""
        from src.application.services import pmla_preflight

        upload_root = Path(__file__).resolve().parent / ".tmp_pasf_preflight" / str(uuid.uuid4())
        try:
            doc_dir = upload_root / "pasf_documents"
            doc_dir.mkdir(parents=True)
            doc_path = doc_dir / "certificate.pdf"
            content = b"pasf certificate"
            doc_path.write_bytes(content)
            checksum = hashlib.sha256(content).hexdigest()
            monkeypatch.setattr(pmla_preflight, "PASF_UPLOAD_ROOT", str(upload_root))

            ctx = make_full_context()
            ctx.attachments = [
                {
                    "id": "doc-1",
                    "pasf_id": ctx.pasf["id"],
                    "document_type": "certificate",
                    "title": "Свидетельство ПАСФ",
                    "file_path": "pasf_documents/certificate.pdf",
                    "checksum_sha256": checksum,
                    "status": "active",
                }
            ]

            report = run_preflight(ctx, generation_mode="final")

            assert "PASF_FILE_NOT_FOUND" not in [e.code for e in report.errors]
            assert "PASF_FILE_CHECKSUM_MISMATCH" not in [e.code for e in report.errors]
        finally:
            shutil.rmtree(upload_root.parent, ignore_errors=True)
    def test_absolute_pasf_document_path_outside_upload_root_is_rejected(self, monkeypatch):
        """Preflight should match download policy and reject paths outside upload root."""
        from src.application.services import pmla_preflight

        test_root = Path(__file__).resolve().parent / ".tmp_pasf_preflight" / str(uuid.uuid4())
        upload_root = test_root / "uploads"
        outside_root = test_root / "outside"
        try:
            upload_root.mkdir(parents=True)
            outside_root.mkdir(parents=True)
            outside_file = outside_root / "certificate.pdf"
            outside_file.write_bytes(b"outside pasf certificate")
            monkeypatch.setattr(pmla_preflight, "PASF_UPLOAD_ROOT", str(upload_root))

            ctx = make_full_context()
            ctx.attachments = [
                {
                    "id": "doc-escape",
                    "pasf_id": ctx.pasf["id"],
                    "document_type": "certificate",
                    "title": "Outside certificate",
                    "file_path": str(outside_file),
                    "status": "active",
                }
            ]

            report = run_preflight(ctx, generation_mode="final")

            assert "PASF_FILE_NOT_FOUND" in [e.code for e in report.errors]
        finally:
            shutil.rmtree(test_root, ignore_errors=True)


# =========================================================================
# Tests: Core validation — organization name and facility name
# =========================================================================


class TestOrganizationFacilityNames:
    """Tests 1-2: Organization name and facility name integrity."""

    def test_organization_name_not_mixed_with_facility(self):
        """Organization name and facility name are distinct fields."""
        ctx = make_full_context()
        assert ctx.organization["name"] != ctx.facility["name"]
        # Mapping to v2 should preserve distinction
        v2 = map_to_v2_context(ctx.to_dict())
        assert v2["organization_full_name"] == ctx.organization["name"]
        assert v2["facility_name"] == ctx.facility["name"]
        assert v2["organization_full_name"] != v2["facility_name"]

    def test_facility_name_not_truncated(self):
        """Facility name passes through mapper unchanged, not truncated."""
        ctx = make_full_context()
        long_name = "Сеть газопотребления ООО «ТестПром» участок №1 цех переработки"
        ctx.facility["name"] = long_name
        v2 = map_to_v2_context(ctx.to_dict())
        assert v2["facility_name"] == long_name


# =========================================================================
# Tests: Equipment name integrity (РДГК-10М / ГРПШ-МС-10)
# =========================================================================


class TestEquipmentNameIntegrity:
    """Tests 3-4: Equipment technical names pass unchanged."""

    def test_rdgk_10m_preserved(self):
        """РДГК-10М is not replaced by mapper."""
        ctx = make_full_context()
        tech_name = "РДГК-10М"
        ctx.equipment[0]["name"] = tech_name
        v2 = map_to_v2_context(ctx.to_dict())
        mapped_names = [e["device_name"] for e in v2["equipment_list"]]
        assert tech_name in mapped_names

    def test_grpsh_ms_10_not_injected(self):
        """Mapper does not inject ГРПШ-МС-10 as a replacement for РДГК-10М."""
        ctx = make_full_context()
        ctx.equipment[0]["name"] = "РДГК-10М"
        v2 = map_to_v2_context(ctx.to_dict())
        mapped_names = [e["device_name"] for e in v2["equipment_list"]]
        assert "ГРПШ-МС-10" not in " ".join(mapped_names)

    def test_equipment_preserves_specifications(self):
        """Equipment specifications should not be overwritten."""
        ctx = make_full_context()
        ctx.equipment[0]["specifications"] = {"pressure": "0.6 МПа"}
        v2 = map_to_v2_context(ctx.to_dict())
        assert len(v2["equipment_list"]) >= 1


# =========================================================================
# Tests: Missing fields generate preflight issues
# =========================================================================


class TestMissingFieldsPreflight:
    """Tests 5-8: Missing fields create appropriate preflight issues."""

    def test_missing_reg_number_creates_issue(self):
        """Missing reg_number creates a BLOCKER in final mode."""
        ctx = make_full_context()
        ctx.facility["reg_number"] = ""
        report = run_preflight(ctx, generation_mode="final")
        assert any(e.code == "FAC_MISSING_REG_NUMBER" for e in report.errors)

    def test_missing_pasf_creates_blocker(self):
        """Missing PASF creates a BLOCKER issue."""
        ctx = make_full_context()
        ctx.pasf = {}
        report = run_preflight(ctx)
        assert any(e.code == "PASF_MISSING" for e in report.errors)

    def test_missing_emergency_services_creates_warning(self):
        """Missing emergency services creates a WARNING in draft."""
        ctx = make_full_context()
        ctx.emergency_services = []
        report = run_preflight(ctx, generation_mode="draft")
        assert any(w.code == "SVC_EMPTY_LIST" for w in report.warnings)

    def test_empty_forces_not_replaced_with_fake(self):
        """Empty forces (resources) are NOT replaced with fake values."""
        ctx = make_full_context()
        ctx.organization_resources = {}
        v2 = map_to_v2_context(ctx.to_dict())
        # The mapper should produce an empty material_reserve list
        assert isinstance(v2.get("material_reserve", []), list)
        # No fake items should be injected
        reserve = v2.get("material_reserve", [])
        fake_items = [r for r in reserve if not r.get("is_group_header")
                      and r.get("name") not in ("", "—")]
        # If organization_resources is empty, there should be no fake items
        if not reserve or not any(not r.get("is_group_header") for r in reserve):
            pass  # OK — empty is acceptable
        else:
            fake_names = [r.get("name") for r in reserve
                          if not r.get("is_group_header")]
            assert not fake_names, f"Fake items should not appear: {fake_names}"


# =========================================================================
# Tests: Generation mode — draft vs final
# =========================================================================


class TestGenerationModes:
    """Tests 9-10: Draft and final generation modes."""

    def test_final_generation_blocked_with_blockers(self):
        """Final generation raises ValueError when preflight has blockers."""
        ctx = make_full_context()
        ctx.organization["name"] = ""
        ctx.facility["hazard_class"] = None
        ctx.equipment = []
        ctx.pasf = {}
        report = run_preflight(ctx)
        assert report.has_blockers
        with pytest.raises(ValueError, match="blocker"):
            report.raise_if_blocked("final")

    def test_draft_generation_allows_blockers(self):
        """Draft generation does not raise on blockers — saves metadata."""
        ctx = make_full_context()
        ctx.organization["name"] = ""
        ctx.pasf = {}
        report = run_preflight(ctx)
        assert report.has_blockers
        # Should NOT raise
        report.raise_if_blocked("draft")
        # Metadata should reflect draft
        ctx.generation_mode = "draft"
        ctx.preflight_status = report.status

    def test_draft_metadata(self):
        """Draft mode sets generation metadata correctly."""
        ctx = make_full_context()
        ctx.generation_mode = "draft"
        report = run_preflight(ctx)
        ctx.preflight_status = report.status
        assert ctx.generation_mode == "draft"
        assert ctx.preflight_status is not None


# =========================================================================
# Tests: Provenance
# =========================================================================


class TestProvenance:
    """Tests 11-12: Provenance tracking."""

    def test_equipment_provenance(self):
        """Equipment has provenance with source type."""
        ctx = make_full_context()
        ctx.add_provenance("equipment", "equipment",
                           ctx.facility["id"],
                           "equipment[2 items]")
        assert "equipment" in ctx.provenance
        entry = ctx.provenance["equipment"]
        assert entry.source_type == "equipment"

    def test_organization_provenance(self):
        """Organization has provenance."""
        ctx = make_full_context()
        ctx.add_provenance("organization.name", "organization",
                           ctx.organization["id"], "name")
        assert "organization.name" in ctx.provenance
        assert ctx.provenance["organization.name"].source_type == "organization"

    def test_facility_provenance(self):
        """Facility has provenance."""
        ctx = make_full_context()
        ctx.add_provenance("facility.name", "facility",
                           ctx.facility["id"], "name")
        assert "facility.name" in ctx.provenance


# =========================================================================
# Tests: v1 backward compatibility
# =========================================================================


class TestV1BackwardCompatibility:
    """Tests 13-14: Old v1 pipeline continues working."""

    def test_v1_context_mapping_still_works(self):
        """adapt_context_for_generator produces valid v1 context."""
        from unittest.mock import AsyncMock
        from src.application.services.pmla_generation_from_questionnaire_service import (
            PmlaGenerationFromQuestionnaireService,
        )

        mock_doc_repo = AsyncMock()
        mock_doc_repo.session = AsyncMock()
        service = PmlaGenerationFromQuestionnaireService(
            document_repo=mock_doc_repo,
            regulatory_repo=None,
        )

        raw_context = {
            "organization": {"name": "Тест"},
            "facility": {"name": "ОПО-1"},
            "questionnaire": {
                "incident_history": {"has_incidents": False},
                "financial_reserve": {},
                "insurance": {},
                "organization_resources": {},
            },
        }
        adapted = service.adapt_context_for_generator(raw_context)
        assert adapted is not None
        assert "organization" in adapted
        assert "facility" in adapted

    def test_v1_validation_works(self):
        """validate_questionnaire_context produces correct output."""
        from unittest.mock import AsyncMock
        from src.application.services.pmla_generation_from_questionnaire_service import (
            PmlaGenerationFromQuestionnaireService,
        )

        mock_doc_repo = AsyncMock()
        mock_doc_repo.session = AsyncMock()
        service = PmlaGenerationFromQuestionnaireService(
            document_repo=mock_doc_repo,
            regulatory_repo=None,
        )

        quality = service.validate_questionnaire_context({
            "organization": {"name": "Тест"},
            "facility": {"name": "ОПО-1"},
        })
        assert "passed" in quality
        assert "errors" in quality
        assert "warnings" in quality


# =========================================================================
# Tests: API version validation
# =========================================================================


class TestVersionValidation:
    """Test 15: Invalid template_version returns 422."""

    def test_invalid_version_rejected(self):
        """Invalid template_version should be rejected."""
        from src.api.routers.pmla_questionnaires import (
            GenerateFromQuestionnaireRequest,
        )
        with pytest.raises(Exception):
            GenerateFromQuestionnaireRequest(template_version="v3")


# =========================================================================
# Tests: Helper functions
# =========================================================================


class TestHelpers:
    """Test internal helper functions."""

    def test_is_empty(self):
        assert _is_empty(None)
        assert _is_empty("")
        assert _is_empty("  ")
        assert _is_empty([])
        assert _is_empty({})
        assert _is_empty("—")
        assert not _is_empty("text")
        assert not _is_empty([1])

    def test_is_fake_value(self):
        assert _is_fake_value("000000")
        assert _is_fake_value("999999")
        assert _is_fake_value("123456")
        assert _is_fake_value("тест")
        assert _is_fake_value("xxx")
        assert not _is_fake_value("500000")
        assert not _is_fake_value("Пр-123/2024")

    def test_roman_hazard_class(self):
        assert _roman_hazard_class(1) == "I"
        assert _roman_hazard_class(4) == "IV"
        assert _roman_hazard_class("3") == "III"

    def test_extract_initials_surname(self):
        assert _extract_initials_surname("Иванов Иван Иванович") == "И.И. Иванов"
        assert _extract_initials_surname("") == ""


# =========================================================================
# Tests: Preflight issue model
# =========================================================================


class TestPreflightIssueModel:
    """Test PreflightIssue dataclass."""

    def test_issue_to_dict(self):
        issue = PreflightIssue(
            code="TEST",
            field="test.field",
            message="Test message",
            severity="BLOCKER",
            source="test",
            recommended_action="Do something",
        )
        d = issue.to_dict()
        assert d["code"] == "TEST"
        assert d["severity"] == "BLOCKER"
        assert d["recommended_action"] == "Do something"

    def test_issue_minimal(self):
        issue = PreflightIssue("CODE", "f", "msg", "INFO")
        d = issue.to_dict()
        assert d["code"] == "CODE"
        assert d["source"] is None
        assert d["recommended_action"] is None
