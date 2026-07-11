"""Tests for facility type normalization — positive, negative, and regression."""
import pytest

from src.application.services.cross_facility_guardrails import (
    normalize_facility_type,
    check_cross_facility_contamination,
)


# ---------------------------------------------------------------------------
# Positive cases — known facility types must normalize correctly
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "input_type, expected",
    [
        ("АГЗС", "агзс"),
        ("агзс", "агзс"),
        ("станция газозаправочная автомобильная", "агзс"),
        ("автомобильная газозаправочная станция", "агзс"),
        ("газозаправочная станция", "агзс"),
        ("Котельная", "котельная"),
        ("котельная", "котельная"),
        ("Сеть газопотребления", "сеть газопотребления"),
        ("сеть газопотребления", "сеть газопотребления"),
        ("Компрессорная станция", "компрессорная станция"),
        ("АЗС", "азс"),
        ("азс", "азс"),
        # Mixed case
        ("сеть ГАЗОПОТРЕБЛЕНИЯ", "сеть газопотребления"),
        ("  Котельная  ", "котельная"),
        # Whitespace normalization
        ("  агзс  ", "агзс"),
        ("   Сеть газопотребления   ", "сеть газопотребления"),
    ],
    ids=[
        "agzs_upper", "agzs_lower", "agzs_full_1", "agzs_full_2",
        "agzs_full_3", "boiler_title", "boiler_lower",
        "gas_network_title", "gas_network_lower",
        "compressor_title", "azs_upper", "azs_lower",
        "gas_network_mixed_case", "boiler_whitespace",
        "agzs_whitespace", "gas_network_whitespace",
    ],
)
def test_normalize_positive(input_type, expected):
    """Known facility types must normalize to their canonical form."""
    assert normalize_facility_type(input_type) == expected


# ---------------------------------------------------------------------------
# Negative cases — short/partial strings must NOT become known types
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "input_type",
    [
        "станция",
        "автомобильная",
        "газозаправочная",
        "газовая",
        "заправочная",
        "автомобильная станция",
        "газозаправочная автомобильная",
    ],
    ids=[
        "station", "automobile", "gas_filling", "gas_adj",
        "filling", "automobile_station", "gas_filling_automobile",
    ],
)
def test_normalize_negative_no_false_match(input_type):
    """Short or partial strings must NOT match a known facility type."""
    result = normalize_facility_type(input_type)
    known_types = {
        "сеть газопотребления", "котельная", "компрессорная станция",
        "азс", "агзс",
    }
    assert result not in known_types, (
        f"'{input_type}' incorrectly normalized to '{result}'"
    )


def test_empty_string():
    """Empty string should return empty string."""
    assert normalize_facility_type("") == ""


def test_whitespace_only():
    """Whitespace-only string should return empty string."""
    assert normalize_facility_type("   ") == ""


def test_unknown_type_returns_normalized_input():
    """Unknown type should return normalized (lowered, stripped) input."""
    assert normalize_facility_type("Неизвестный Тип") == "неизвестный тип"
    assert normalize_facility_type("  My Facility  ") == "my facility"


# ---------------------------------------------------------------------------
# Regression — existing facility types still work
# ---------------------------------------------------------------------------


def test_existing_types_still_recognized():
    """All previously working facility types must continue to work."""
    assert normalize_facility_type("Сеть газопотребления") == "сеть газопотребления"
    assert normalize_facility_type("Котельная") == "котельная"
    assert normalize_facility_type("Компрессорная станция") == "компрессорная станция"
    assert normalize_facility_type("АЗС") == "азс"
    assert normalize_facility_type("АГЗС") == "агзс"


# ---------------------------------------------------------------------------
# Regression — KG context for AGZS
# ---------------------------------------------------------------------------


def test_agzs_kg_returns_agzs_context():
    """AGZS must return AGZS-specific KG context, not gas network."""
    from src.application.services.pmla_knowledge_graph_adapter import PmlaKnowledgeGraphAdapter

    adapter = PmlaKnowledgeGraphAdapter()
    ctx = adapter.get_context({"facility_type": "АГЗС"})
    assert ctx.facility_type == "агзс"
    assert len(ctx.equipment_types) > 0
    equipment_text = " ".join(ctx.equipment_types).lower()
    assert "суг" in equipment_text or "резервуар" in equipment_text
    assert "грпш" not in equipment_text


def test_short_station_does_not_get_agzs_kg():
    """Short word 'станция' must NOT get AGZS KG context."""
    from src.application.services.pmla_knowledge_graph_adapter import PmlaKnowledgeGraphAdapter

    adapter = PmlaKnowledgeGraphAdapter()
    ctx = adapter.get_context({"facility_type": "станция"})
    # Should get default/warning, not AGZS context
    assert ctx.facility_type != "агзс"


# ---------------------------------------------------------------------------
# Regression — RAG context for AGZS
# ---------------------------------------------------------------------------


def test_agzs_rag_returns_chunks():
    """AGZS must return RAG chunks."""
    from src.application.services.pmla_rag_adapter import PmlaRagAdapter

    adapter = PmlaRagAdapter()
    ctx = adapter.get_context({"facility_type": "АГЗС"}, "section_2")
    assert not ctx.is_empty
    assert len(ctx.chunks) > 0


def test_short_station_does_not_get_agzs_rag():
    """Short word 'станция' must NOT get AGZS RAG chunks."""
    from src.application.services.pmla_rag_adapter import PmlaRagAdapter

    adapter = PmlaRagAdapter()
    ctx = adapter.get_context({"facility_type": "станция"}, "section_2")
    # Should be empty or default, not AGZS-specific
    for chunk in ctx.chunks:
        assert "суг" not in chunk.text.lower(), (
            "Short 'станция' incorrectly received AGZS RAG chunks"
        )


# ---------------------------------------------------------------------------
# Regression — guardrails for short strings
# ---------------------------------------------------------------------------


def test_short_station_no_agzs_contamination():
    """Short 'станция' must not trigger AGZS contamination check."""
    text = "Проверить котёл и теплосеть"
    found = check_cross_facility_contamination(text, "станция")
    # Unknown type → no forbidden terms → no contamination
    assert len(found) == 0


def test_boiler_contamination_still_detected():
    """Boiler contamination with ГРПШ must still be detected."""
    text = "Проверить ГРПШ"
    found = check_cross_facility_contamination(text, "котельная")
    assert "ГРПШ" in found


def test_agzs_contamination_still_detected():
    """AGZS contamination with boiler terms must still be detected."""
    text = "Проверить водогрейный котёл"
    found = check_cross_facility_contamination(text, "АГЗС")
    assert "водогрейный котёл" in found
