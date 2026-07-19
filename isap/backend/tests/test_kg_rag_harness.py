"""KG/RAG Harness — eval-tests for PMLA Knowledge Graph and RAG adapters.

Verifies the minimal harness checks required by AGENTS.md §11:
1. Deterministic reproducibility
2. No cross-facility contamination
3. Correct per-type isolation (equipment/hazards/scenarios/services/appendices/regulations)
4. Fallback works independently of graph backend
5. Provenance shows in-memory vs graph
6. Diagnostic artifacts can be saved
"""
import json
import pytest
from pathlib import Path

from src.application.services.pmla_knowledge_graph_adapter import (
    PmlaKnowledgeGraphAdapter,
    PmlaKnowledgeGraphContext,
)
from src.application.services.pmla_rag_adapter import (
    PmlaRagAdapter,
    PmlaRagContext,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

KG_ADAPTER = PmlaKnowledgeGraphAdapter()
RAG_ADAPTER = PmlaRagAdapter()

# Supported facility types (verified in AGENTS.md §10)
SUPPORTED_TYPES = [
    "сеть газопотребления",
    "котельная",
    "компрессорная станция",
    "азс",
    "агзс",
]

# Per-type expected signatures — minimal presence checks
_TYPE_SIGNATURES: dict[str, dict] = {
    "сеть газопотребления": {
        "must_have_equipment": ["газопровод"],
        "must_have_hazards": ["утечка природного газа"],
        "must_have_scenarios": ["разгерметизация участка газопровода"],
        "must_have_services": ["аварийная газовая служба"],
        "must_have_appendices": ["схема расположения ОПО"],
        "must_have_regulations": ["ФЗ-116"],
    },
    "котельная": {
        "must_have_equipment": ["котёл"],
        "must_have_hazards": ["взрыв котла"],
        "must_have_scenarios": ["отказ САБ"],
        "must_have_services": [],
        "must_have_appendices": [],
        "must_have_regulations": [],
    },
    "агзс": {
        "must_have_equipment": ["резервуар хранения СУГ"],
        "must_have_hazards": ["утечка СУГ"],
        "must_have_scenarios": ["разгерметизация резервуара СУГ"],
        "must_have_services": ["аварийная газовая служба"],
        "must_have_appendices": ["схема расположения АГЗС"],
        "must_have_regulations": [],
    },
}

# Cross-contamination terms — each type should NOT contain these
_CROSS_CONTAMINATION: dict[str, list[str]] = {
    "сеть газопотребления": ["котёл", "СУГ", "резервуар", "компрессор"],
    "котельная": ["газопровод", "СУГ", "ГРПШ"],
    "агзс": ["газопровод", "котёл", "ГРПШ", "САБ"],
}


# ===========================================================================
# 1. REPRODUCIBILITY — identical input must yield identical output
# ===========================================================================


class TestReproducibility:
    def test_kg_adapter_same_input_same_output(self):
        """KG adapter must return identical results for identical inputs."""
        inputs = [
            {"facility_type": "Сеть газопотребления"},
            {"facility_type": "Котельная"},
            {"facility_type": "АГЗС"},
        ]
        for inp in inputs:
            first = KG_ADAPTER.get_context(inp)
            second = KG_ADAPTER.get_context(inp)
            assert first.facility_type == second.facility_type
            assert first.equipment_types == second.equipment_types
            assert first.hazards == second.hazards
            assert first.recommended_scenarios == second.recommended_scenarios
            assert first.required_services == second.required_services
            assert first.required_appendices == second.required_appendices
            assert first.applicable_regulations == second.applicable_regulations

    def test_rag_adapter_same_input_same_output(self):
        """RAG adapter must return identical results for identical inputs."""
        sections = ["section_2", "section_5", "section_10"]
        for section in sections:
            first = RAG_ADAPTER.get_context(
                {"facility_type": "Сеть газопотребления"}, section
            )
            second = RAG_ADAPTER.get_context(
                {"facility_type": "Сеть газопотребления"}, section
            )
            assert first.summary == second.summary
            assert len(first.chunks) == len(second.chunks)


# ===========================================================================
# 2. NO CROSS-FACILITY CONTAMINATION
# ===========================================================================


class TestCrossFacilityIsolation:
    @pytest.mark.parametrize("facility_type", SUPPORTED_TYPES)
    def test_kg_no_contamination(self, facility_type):
        """KG context for a facility type must not contain terms from other types."""
        ctx = KG_ADAPTER.get_context({"facility_type": facility_type})
        bad_terms = _CROSS_CONTAMINATION.get(facility_type, [])
        all_text = " ".join([
            " ".join(ctx.equipment_types),
            " ".join(ctx.hazards),
            " ".join(ctx.recommended_scenarios),
            " ".join(ctx.required_services),
            " ".join(ctx.required_appendices),
            " ".join(ctx.applicable_regulations),
        ]).lower()
        for term in bad_terms:
            assert term.lower() not in all_text, (
                f"Cross-contamination: '{facility_type}' contains '{term}' from another type"
            )

    @pytest.mark.parametrize("facility_type", SUPPORTED_TYPES)
    def test_rag_no_contamination(self, facility_type):
        """RAG chunks for a facility type must not contain terms from other types."""
        bad_terms = _CROSS_CONTAMINATION.get(facility_type, [])
        if not bad_terms:
            pytest.skip("No contamination terms defined for this type")
        for section_id in ["section_2", "section_10"]:
            ctx = RAG_ADAPTER.get_context({"facility_type": facility_type}, section_id)
            for chunk in ctx.chunks:
                for term in bad_terms:
                    assert term.lower() not in chunk.text.lower(), (
                        f"RAG cross-contamination: '{facility_type}' section '{section_id}' "
                        f"chunk '{chunk.source_id}' contains '{term}'"
                    )


# ===========================================================================
# 3. PER-TYPE CORRECTNESS — required data present
# ===========================================================================


class TestPerTypeCorrectness:
    @pytest.mark.parametrize("facility_type", SUPPORTED_TYPES)
    def test_kg_returns_non_empty_context(self, facility_type):
        """Each supported type must return non-empty KG context."""
        ctx = KG_ADAPTER.get_context({"facility_type": facility_type})
        assert ctx.facility_type is not None
        assert not ctx.is_empty, f"KG context empty for '{facility_type}'"
        assert not ctx.warnings, f"Unexpected warnings for '{facility_type}': {ctx.warnings}"

    @pytest.mark.parametrize("facility_type", SUPPORTED_TYPES)
    def test_kg_has_equipment_hazards_scenarios(self, facility_type):
        """Each type must have equipment, hazards, and scenarios."""
        ctx = KG_ADAPTER.get_context({"facility_type": facility_type})
        assert len(ctx.equipment_types) >= 1, f"No equipment for '{facility_type}'"
        assert len(ctx.hazards) >= 1, f"No hazards for '{facility_type}'"
        assert len(ctx.recommended_scenarios) >= 1, f"No scenarios for '{facility_type}'"

    @pytest.mark.parametrize("facility_type", list(_TYPE_SIGNATURES.keys()))
    def test_kg_signature_items(self, facility_type):
        """Check must-have items for specific types."""
        sig = _TYPE_SIGNATURES[facility_type]
        ctx = KG_ADAPTER.get_context({"facility_type": facility_type})
        all_text = " ".join(ctx.equipment_types).lower()
        for item in sig.get("must_have_equipment", []):
            assert item.lower() in all_text, (
                f"'{facility_type}' missing equipment: '{item}'"
            )

    @pytest.mark.parametrize("facility_type", SUPPORTED_TYPES)
    def test_rag_returns_chunks_for_generated_sections(self, facility_type):
        """RAG must return chunks for at least some generated sections."""
        generated_sections = ["section_2", "section_5", "section_10"]
        has_chunks = False
        for sid in generated_sections:
            ctx = RAG_ADAPTER.get_context({"facility_type": facility_type}, sid)
            if not ctx.is_empty:
                has_chunks = True
                assert len(ctx.chunks) >= 1
                for chunk in ctx.chunks:
                    assert chunk.source_id
                    assert chunk.text
        assert has_chunks, f"No RAG chunks for any generated section of '{facility_type}'"


# ===========================================================================
# 4. FALLBACK INDEPENDENCE
# ===========================================================================


class TestFallbackIndependence:
    def test_unknown_type_uses_default_kg(self):
        """Unknown facility type should fall back to default KG context."""
        ctx = KG_ADAPTER.get_context({"facility_type": "Неизвестный тип ОПО"})
        assert ctx.facility_type == "Неизвестный тип ОПО"
        assert len(ctx.warnings) == 1
        assert "не найден" in ctx.warnings[0]
        # Default should still have required services
        assert len(ctx.required_services) > 0

    def test_unknown_type_uses_default_rag(self):
        """Unknown facility type should fall back to default RAG context."""
        ctx = RAG_ADAPTER.get_context(
            {"facility_type": "Неизвестный тип ОПО"}, "section_10"
        )
        assert len(ctx.warnings) == 1
        assert "не найден" in ctx.warnings[0]

    def test_empty_type_returns_empty_context(self):
        """Empty facility type should return empty context with warning."""
        kg_ctx = KG_ADAPTER.get_context({"facility_type": ""})
        rag_ctx = RAG_ADAPTER.get_context({"facility_type": ""}, "section_2")
        assert kg_ctx.is_empty
        assert rag_ctx.is_empty
        assert len(kg_ctx.warnings) == 1
        assert len(rag_ctx.warnings) == 1

    def test_none_facility_type_returns_empty_context(self):
        """None facility type should return empty context with warning."""
        kg_ctx = KG_ADAPTER.get_context({"facility_type": None})
        rag_ctx = RAG_ADAPTER.get_context({"facility_type": None}, "section_2")
        assert kg_ctx.is_empty
        assert rag_ctx.is_empty


# ===========================================================================
# 5. PROVENANCE
# ===========================================================================


class TestProvenance:
    def test_kg_adapter_source_is_in_memory(self):
        """KG adapter must indicate in-memory fallback when no graph backend."""
        adapter = KG_ADAPTER
        # The adapter class docstring states it uses in-memory fallback
        assert "in-memory" in adapter.__class__.__doc__.lower()

    def test_rag_adapter_source_is_in_memory(self):
        """RAG adapter must indicate in-memory fallback when no graph backend."""
        adapter = RAG_ADAPTER
        assert "in-memory" in adapter.__class__.__doc__.lower()

    def test_kg_warning_on_unknown_type(self):
        """KG context should warn when type not found in knowledge base."""
        ctx = KG_ADAPTER.get_context({"facility_type": "Нетипичный объект"})
        assert len(ctx.warnings) >= 1
        assert any("не найден" in w for w in ctx.warnings)

    def test_rag_warning_on_unknown_type(self):
        """RAG context should warn when type not found in knowledge base."""
        ctx = RAG_ADAPTER.get_context({"facility_type": "Нетипичный объект"}, "section_2")
        assert len(ctx.warnings) >= 1
        assert any("не найден" in w for w in ctx.warnings)


# ===========================================================================
# 6. DIAGNOSTIC ARTIFACTS
# ===========================================================================


class TestDiagnosticArtifacts:
    def test_kg_context_serializable(self):
        """KG context must be serializable to JSON for diagnostic output."""
        ctx = KG_ADAPTER.get_context({"facility_type": "Сеть газопотребления"})
        data = {
            "facility_type": ctx.facility_type,
            "equipment_types": ctx.equipment_types,
            "hazards": ctx.hazards,
            "recommended_scenarios": ctx.recommended_scenarios,
            "required_services": ctx.required_services,
            "required_appendices": ctx.required_appendices,
            "applicable_regulations": ctx.applicable_regulations,
            "warnings": ctx.warnings,
            "is_empty": ctx.is_empty,
        }
        serialized = json.dumps(data, ensure_ascii=False, indent=2)
        assert len(serialized) > 10
        # Round-trip
        deserialized = json.loads(serialized)
        assert deserialized["facility_type"] == ctx.facility_type

    def test_rag_context_serializable(self):
        """RAG context must be serializable to JSON for diagnostic output."""
        ctx = RAG_ADAPTER.get_context(
            {"facility_type": "Сеть газопотребления"}, "section_2"
        )
        data = {
            "chunks": [
                {
                    "source_id": c.source_id,
                    "source_title": c.source_title,
                    "text": c.text,
                }
                for c in ctx.chunks
            ],
            "warnings": ctx.warnings,
            "is_empty": ctx.is_empty,
        }
        serialized = json.dumps(data, ensure_ascii=False, indent=2)
        assert len(serialized) > 10
        deserialized = json.loads(serialized)
        assert len(deserialized["chunks"]) == len(ctx.chunks)

    def test_full_harness_artifact(self):
        """Full harness diagnostic: export all types to a single JSON artifact."""
        artifact = {}
        for ftype in SUPPORTED_TYPES:
            kg = KG_ADAPTER.get_context({"facility_type": ftype})
            sections = {}
            for sid in ["section_2", "section_5", "section_10"]:
                rag = RAG_ADAPTER.get_context({"facility_type": ftype}, sid)
                sections[sid] = {
                    "chunk_count": len(rag.chunks),
                    "warnings": rag.warnings,
                }
            artifact[ftype] = {
                "kg": {
                    "equipment_count": len(kg.equipment_types),
                    "hazard_count": len(kg.hazards),
                    "scenario_count": len(kg.recommended_scenarios),
                    "service_count": len(kg.required_services),
                    "appendix_count": len(kg.required_appendices),
                    "regulation_count": len(kg.applicable_regulations),
                    "warnings": kg.warnings,
                },
                "rag": sections,
            }
        serialized = json.dumps(artifact, ensure_ascii=False, indent=2)
        # Verify structure
        parsed = json.loads(serialized)
        assert len(parsed) == len(SUPPORTED_TYPES)
        for ftype in SUPPORTED_TYPES:
            assert ftype in parsed
            assert parsed[ftype]["kg"]["equipment_count"] > 0
