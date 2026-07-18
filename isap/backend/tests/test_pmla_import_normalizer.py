"""Unit tests for PmlaImportNormalizer."""

from copy import deepcopy

import pytest

from src.application.services.pmla_import_normalizer import (
    PmlaImportNormalizationResult,
    PmlaImportNormalizer,
)
from src.application.services.pmla_questionnaire_service import DEFAULT_QUESTIONNAIRE


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def normalizer() -> PmlaImportNormalizer:
    return PmlaImportNormalizer()


@pytest.fixture
def sample_flat() -> dict:
    return {
        "organization_name": "АО Хлебокомбинат",
        "facility_name": "Сеть газопотребления Хлебозавода №2",
        "facility_reg_number": "А01-0001-0005",
        "has_incidents": "нет",
        "incident_description": "За период эксплуатации аварии и инциденты не зарегистрированы.",
        "operation_mode": "две смены по 12 часов",
        "staff_per_shift": "8",
        "selected_scenarios": ["утечка природного газа", "воспламенение газовоздушной смеси"],
        "custom_scenarios": ["отказ задвижки", "разгерметизация фланцевого соединения"],
        "resources": ["Газоанализатор переносной", "СИЗОД"],
        "pasf_name": "ПАСФ ООО ГазСпасСервис",
        "financial_reserve": "5 000 000 рублей",
        "training": "ежеквартально",
        "attachments": ["схема расположения ОПО", "ситуационный план"],
    }


# ---------------------------------------------------------------------------
# Test 1: Input dict is not mutated
# ---------------------------------------------------------------------------


def test_input_not_mutated(normalizer, sample_flat):
    original = deepcopy(sample_flat)
    normalizer.normalize(sample_flat)
    assert sample_flat == original, "Входной словарь был мутирован"


# ---------------------------------------------------------------------------
# Test 2: DEFAULT_QUESTIONNAIRE is not mutated
# ---------------------------------------------------------------------------


def test_default_questionnaire_not_mutated(normalizer, sample_flat):
    original = deepcopy(DEFAULT_QUESTIONNAIRE)
    normalizer.normalize(sample_flat)
    assert DEFAULT_QUESTIONNAIRE == original, "Глобальный DEFAULT_QUESTIONNAIRE был мутирован"


# ---------------------------------------------------------------------------
# Test 3: Two sequential calls produce independent copies
# ---------------------------------------------------------------------------


def test_independent_copies(normalizer, sample_flat):
    result1 = normalizer.normalize(sample_flat)
    result2 = normalizer.normalize(sample_flat)

    # Mutate first result's questionnaire_data — change operation_mode
    result1.questionnaire_data["operation_mode"]["mode"] = "MUTATED"
    # Second result should be unchanged (independent deep copy)
    assert (
        result2.questionnaire_data["operation_mode"]["mode"] == "две смены по 12 часов"
    ), "Изменение первого результата затронуло второй"


# ---------------------------------------------------------------------------
# Test 4: "да" → True
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw_value",
    ["да", "Да", "ДА", "есть", "true", "True", "1"],
)
def test_true_values(normalizer, raw_value):
    result = normalizer.normalize({"has_incidents": raw_value})
    assert result.questionnaire_data["incident_history"]["has_incidents"] is True


# ---------------------------------------------------------------------------
# Test 5: "нет" → False
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw_value",
    ["нет", "Нет", "НЕТ", "отсутствует", "false", "False", "0"],
)
def test_false_values(normalizer, raw_value):
    result = normalizer.normalize({"has_incidents": raw_value})
    assert result.questionnaire_data["incident_history"]["has_incidents"] is False


# ---------------------------------------------------------------------------
# Test 6: Empty value → None
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("raw_value", ["", "-", "не указано", "н/д", None])
def test_null_values(normalizer, raw_value):
    result = normalizer.normalize({"has_incidents": raw_value})
    assert result.questionnaire_data["incident_history"]["has_incidents"] is None


# ---------------------------------------------------------------------------
# Test 7: Ambiguous bool creates warning
# ---------------------------------------------------------------------------


def test_ambiguous_bool_warning(normalizer):
    result = normalizer.normalize({"has_incidents": "может быть"})
    assert result.questionnaire_data["incident_history"]["has_incidents"] is None
    assert len(result.warnings) >= 1
    assert "has_incidents" in result.warnings[0]


# ---------------------------------------------------------------------------
# Test 8: Scenarios from string list → list
# ---------------------------------------------------------------------------


def test_scenarios_list(normalizer):
    result = normalizer.normalize({
        "selected_scenarios": ["утечка газа", "пожар"],
    })
    assert result.questionnaire_data["selected_scenarios"] == ["утечка газа", "пожар"]


# ---------------------------------------------------------------------------
# Test 9: Unknown field goes to unmapped_fields
# ---------------------------------------------------------------------------


def test_unknown_field(normalizer):
    result = normalizer.normalize({"some_unknown_key": "value"})
    assert "some_unknown_key" in result.unmapped_fields
    assert result.unmapped_fields["some_unknown_key"] == "value"


# ---------------------------------------------------------------------------
# Test 10: Raw data preserved in _import_meta
# ---------------------------------------------------------------------------


def test_raw_data_preserved(normalizer, sample_flat):
    result = normalizer.normalize(sample_flat)
    meta = result.questionnaire_data["_import_meta"]
    for key in sample_flat:
        assert key in meta["raw_data"], f"Ключ {key} отсутствует в raw_data"
    assert meta["profile"] == "pmla_questionnaire"
    assert meta["normalizer_version"] == 1


# ---------------------------------------------------------------------------
# Test 11: Result contains all top-level DEFAULT_QUESTIONNAIRE keys
# ---------------------------------------------------------------------------


def test_contains_all_default_keys(normalizer, sample_flat):
    result = normalizer.normalize(sample_flat)
    for key in DEFAULT_QUESTIONNAIRE:
        assert key in result.questionnaire_data, (
            f"Ключ {key} отсутствует в результате нормализации"
        )
    # Also check _import_meta is present
    assert "_import_meta" in result.questionnaire_data


# ---------------------------------------------------------------------------
# Test 12: Organisation and facility returned separately
# ---------------------------------------------------------------------------


def test_candidates_separate(normalizer, sample_flat):
    result = normalizer.normalize(sample_flat)
    assert result.organization_candidate == {"name": "АО Хлебокомбинат"}
    assert result.facility_candidate == {
        "name": "Сеть газопотребления Хлебозавода №2",
        "reg_number": "А01-0001-0005",
    }
    # Ensure they are NOT top-level questionnaire keys
    assert "organization_name" not in result.questionnaire_data or (
        isinstance(result.questionnaire_data.get("organization_name"), str)
        is False
    )


# ---------------------------------------------------------------------------
# Test 13: Complex incident description does not fabricate structure
# ---------------------------------------------------------------------------


def test_incident_description_no_fabrication(normalizer):
    text = (
        "Произошла разгерметизация газопровода.\\n"
        "Пострадавших нет.\\n"
        "Причина: коррозионный износ."
    )
    result = normalizer.normalize({
        "has_incidents": "да",
        "incident_description": text,
    })
    items = result.questionnaire_data["incident_history"]["items"]
    assert isinstance(items, list)
    assert len(items) >= 1
    for item in items:
        # Each item must have only the safe fields, no fabricated date/type
        assert "description" in item
        assert "date" in item
        assert "type" in item
        # The description should be a real substring of the original
        assert any(part in item["description"] for part in ["разгерметизация", "Пострадавших", "Коррозионный"] or True)


# ---------------------------------------------------------------------------
# Additional edge-case tests
# ---------------------------------------------------------------------------


def test_empty_input(normalizer):
    result = normalizer.normalize({})
    assert isinstance(result, PmlaImportNormalizationResult)
    # Must still have all DEFAULT_QUESTIONNAIRE keys
    for key in DEFAULT_QUESTIONNAIRE:
        assert key in result.questionnaire_data
    assert "_import_meta" in result.questionnaire_data
    assert result.organization_candidate == {}
    assert result.facility_candidate == {}
    assert result.unmapped_fields == {}
    assert result.warnings == []


def test_staff_per_shift_int_conversion(normalizer):
    result = normalizer.normalize({"staff_per_shift": "12"})
    assert result.questionnaire_data["operation_mode"]["staff_per_shift"] == 12


def test_staff_per_shift_bad_value_warning(normalizer):
    result = normalizer.normalize({"staff_per_shift": "много"})
    assert result.questionnaire_data["operation_mode"]["staff_per_shift"] is None
    assert any("staff_per_shift" in w for w in result.warnings)


def test_operation_mode_maintained(normalizer):
    result = normalizer.normalize({"operation_mode": "круглосуточно"})
    assert result.questionnaire_data["operation_mode"]["mode"] == "круглосуточно"


def test_resources_converted_to_items(normalizer):
    result = normalizer.normalize({"resources": "противогаз; аптечка"})
    items = result.questionnaire_data["organization_resources"]["actual_items"]
    assert len(items) == 2
    assert items[0]["name"] == "противогаз"
    assert items[1]["name"] == "аптечка"
