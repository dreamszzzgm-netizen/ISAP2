"""E2E: Smart Import normalizer → context → mapper — _import_meta does not break pipeline.

Tests the critical E2E contracts:
1. Normalize flat import data → questionnaire with _import_meta
2. Build full generation context containing questionnaire with _import_meta
3. map_to_v2_context() — must NOT crash on _import_meta
4. validate_v2_context() — must NOT crash on _import_meta
5. Generated v2 context structure is correct with _import_meta present
"""

from __future__ import annotations

import pytest

from src.application.services.pmla_import_normalizer import PmlaImportNormalizer
from src.application.services.pmla_questionnaire_service import DEFAULT_QUESTIONNAIRE
from src.application.services.pmla_v2_context_mapper import (
    map_to_v2_context,
    validate_v2_context,
)


SAMPLE_FLAT = {
    "organization_name": "АО Хлебокомбинат",
    "facility_name": "Сеть газопотребления Хлебозавода №2",
    "facility_reg_number": "А01-0001-0005",
    "has_incidents": "нет",
    "incident_description": "За период эксплуатации аварии и инциденты не зарегистрированы.",
    "operation_mode": "две смены по 12 часов",
    "staff_per_shift": "8",
    "selected_scenarios": ["утечка природного газа", "воспламенение газовоздушной смеси"],
    "custom_scenarios": [],
    "resources": ["Газоанализатор переносной", "СИЗОД"],
    "pasf_name": "ПАСФ ООО ГазСпасСервис",
    "financial_reserve": "5 000 000 рублей",
    "training": "ежеквартально",
    "attachments": ["схема расположения ОПО", "ситуационный план"],
}


def _make_full_context(questionnaire_data: dict) -> dict:
    """Build a minimal but realistic generation context around questionnaire data."""
    return {
        "organization": {
            "id": "org-uuid",
            "name": "АО Хлебокомбинат",
            "short_name": "АО Хлебокомбинат",
            "inn": "7701234567",
            "ogrn": "1234567890123",
            "address": "г. Тест",
            "phone": "+7 (000) 000-00-00",
            "email": "test@test.test",
        },
        "facility": {
            "id": "fac-uuid",
            "name": "Сеть газопотребления Хлебозавода №2",
            "reg_number": "А01-0001-0005",
            "hazard_class": 3,
            "facility_type": "Сеть газопотребления",
            "object_type": "Сеть газопотребления",
            "address": "г. Тест",
            "latitude": None,
            "longitude": None,
            "inventory_number": None,
        },
        "equipment": [],
        "substances": [],
        "responsible_persons": [
            {
                "id": "rp-1",
                "full_name": "Иванов Иван Иванович",
                "position": "Генеральный директор",
                "role": "director",
                "phone": "+7 (000) 000-00-01",
                "email": "director@test.test",
            }
        ],
        "questionnaire": questionnaire_data,
        "incident_history": questionnaire_data.get("incident_history", {}),
        "selected_scenarios": questionnaire_data.get("selected_scenarios", []),
        "custom_scenarios": questionnaire_data.get("custom_scenarios", []),
        "pasf": None,
        "pasf_documents": [],
        "nearest_services": {},
        "emergency_services": [],
        "organization_resources": questionnaire_data.get("organization_resources", {}),
        "recommendations": {},
        "selected_pasf_id": None,
        "selected_emergency_service_ids": [],
        "attachments_checklist": questionnaire_data.get("attachments_checklist", []),
    }


class TestSmartImportToGenerateV2E2E:
    """E2E: normalizer → context → mapper with _import_meta."""

    def test_normalizer_produces_valid_structure(self):
        """Normalizer output conforms to DEFAULT_QUESTIONNAIRE structure."""
        result = PmlaImportNormalizer().normalize(SAMPLE_FLAT)
        qdata = result.questionnaire_data

        # All DEFAULT_QUESTIONNAIRE keys present
        for key in DEFAULT_QUESTIONNAIRE:
            assert key in qdata, f"Missing key: {key}"

        # _import_meta is the only extra key
        extra_keys = set(qdata.keys()) - set(DEFAULT_QUESTIONNAIRE.keys()) - {"_import_meta"}
        assert extra_keys == set(), f"Unexpected keys in questionnaire_data: {extra_keys}"

        # Correctly converted types
        assert qdata["incident_history"]["has_incidents"] is False
        assert qdata["operation_mode"]["mode"] == "две смены по 12 часов"
        assert qdata["operation_mode"]["staff_per_shift"] == 8
        assert isinstance(qdata["selected_scenarios"], list)
        assert len(qdata["selected_scenarios"]) == 2

        # Candidates preserved
        assert result.organization_candidate == {"name": "АО Хлебокомбинат"}
        assert result.facility_candidate == {
            "name": "Сеть газопотребления Хлебозавода №2",
            "reg_number": "А01-0001-0005",
        }

    def test_import_meta_contents(self):
        """_import_meta block contains all expected fields."""
        result = PmlaImportNormalizer().normalize(SAMPLE_FLAT)
        meta = result.questionnaire_data["_import_meta"]

        assert meta["profile"] == "pmla_questionnaire"
        assert meta["normalizer_version"] == 1
        assert "raw_data" in meta
        assert "unmapped_fields" in meta
        assert "warnings" in meta
        assert meta["organization_candidate"] == {"name": "АО Хлебокомбинат"}
        assert meta["facility_candidate"] == {
            "name": "Сеть газопотребления Хлебозавода №2",
            "reg_number": "А01-0001-0005",
        }

        # raw_data must contain all original keys
        for key in SAMPLE_FLAT:
            assert key in meta["raw_data"], f"Missing key in raw_data: {key}"

        # No unmapped fields for known keys
        assert meta["unmapped_fields"] == {}

    def test_map_to_v2_context_with_import_meta(self):
        """map_to_v2_context must NOT crash when questionnaire has _import_meta."""
        result = PmlaImportNormalizer().normalize(SAMPLE_FLAT)
        context = _make_full_context(result.questionnaire_data)

        try:
            v2_ctx = map_to_v2_context(context)
        except Exception as exc:
            pytest.fail(
                f"map_to_v2_context raised {type(exc).__name__}: {exc}\n"
                f"_import_meta in questionnaire.data broke the mapper"
            )

        # Verify basic v2 fields are populated from questionnaire data
        assert isinstance(v2_ctx, dict)
        assert "organization_full_name" in v2_ctx
        assert v2_ctx["organization_full_name"] == "АО Хлебокомбинат"
        assert "facility_name" in v2_ctx
        assert v2_ctx["facility_name"] == "Сеть газопотребления Хлебозавода №2"

        # Fields that come from questionnaire via mapper
        # selected_scenarios → accident_scenarios
        assert "accident_scenarios" in v2_ctx
        # incident_history → accident_history, injury_history
        assert "accident_history" in v2_ctx

        # Verify _import_meta keys did NOT leak into v2 context
        v2_keys_lower = {k.lower() for k in v2_ctx}
        assert "import_meta" not in v2_keys_lower, (
            "_import_meta leaked into map_to_v2_context output keys!"
        )
        assert "organization_candidate" not in v2_keys_lower
        assert "facility_candidate" not in v2_keys_lower

    def test_validate_v2_context_with_import_meta(self):
        """validate_v2_context must NOT crash with _import_meta present."""
        result = PmlaImportNormalizer().normalize(SAMPLE_FLAT)
        context = _make_full_context(result.questionnaire_data)

        # validate against source context (as done in the real pipeline)
        try:
            errors = validate_v2_context(context)
        except Exception as exc:
            pytest.fail(
                f"validate_v2_context raised {type(exc).__name__}: {exc}\n"
                f"_import_meta in questionnaire.data broke the validator"
            )

        # In draft mode with full context, errors are expected to be empty
        # or contain only soft warnings — but NOT crash
        assert isinstance(errors, list)

    def test_candidates_not_in_questionnaire_root(self):
        """Flat organization/facility names must NOT be at questionnaire root."""
        result = PmlaImportNormalizer().normalize(SAMPLE_FLAT)
        qdata = result.questionnaire_data

        # These flat keys should NOT be at the top level
        assert "organization_name" not in qdata, (
            "organization_name leaked to questionnaire root"
        )
        assert "facility_name" not in qdata, (
            "facility_name leaked to questionnaire root"
        )
        assert "facility_reg_number" not in qdata, (
            "facility_reg_number leaked to questionnaire root"
        )

    def test_import_meta_does_not_break_build_generation_context(self):
        """build_generation_context pattern with _import_meta must work.

        The real build_generation_context does:
            qdata = deepcopy(DEFAULT_QUESTIONNAIRE)
            qdata.update(questionnaire.data or {})
        Then returns questionnaire in context. This test simulates that.
        """
        from copy import deepcopy

        # Simulate what happens in PmlaQuestionnaireService.build_generation_context
        result = PmlaImportNormalizer().normalize(SAMPLE_FLAT)
        qdata = deepcopy(DEFAULT_QUESTIONNAIRE)
        qdata.update(result.questionnaire_data)

        # The update must not break the structure
        for key in DEFAULT_QUESTIONNAIRE:
            assert key in qdata, f"Key {key} lost after update"

        # _import_meta must survive the round-trip
        assert "_import_meta" in qdata
        assert qdata["_import_meta"]["organization_candidate"] == {"name": "АО Хлебокомбинат"}
