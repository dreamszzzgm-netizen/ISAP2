"""E2E test: questionnaire data appears in generated DOCX."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from docx import Document as DocxDocument

from src.application.engines.base import DocumentContext
from src.application.services.pmla_generation_from_questionnaire_service import (
    PmlaGenerationFromQuestionnaireService,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def extract_docx_text(docx_bytes: bytes) -> str:
    """Extract all text from DOCX bytes (paragraphs + tables)."""
    import io
    doc = DocxDocument(io.BytesIO(docx_bytes))
    parts = []
    for p in doc.paragraphs:
        if p.text:
            parts.append(p.text)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                if cell.text:
                    parts.append(cell.text)
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Test data
# ---------------------------------------------------------------------------

SAMPLE_QUESTIONNAIRE_DATA = {
    "questionnaire": {
        "incident_history": {
            "has_incidents": False,
            "period": "за период эксплуатации",
            "items": [],
        },
        "selected_scenarios": [
            "утечка опасного вещества",
            "загазованность помещения",
            "отказ автоматики",
        ],
        "custom_scenarios": [
            {
                "name": "Отказ запорной арматуры",
                "title": "Отказ запорной арматуры",
                "description": "Нарушение герметичности или невозможность полного перекрытия подачи газа.",
                "place": "газопровод / ГРУ",
                "source_equipment": "газопровод / ГРУ",
                "equipment": "запорная арматура",
                "hazardous_substance": "природный газ",
                "consequences": "загазованность, пожар, взрыв",
            }
        ],
        "organization_resources": {
            "actual_items": [
                {
                    "name": "Газоанализатор",
                    "type": "control",
                    "quantity": "1",
                    "storage_place": "операторная",
                    "responsible_person": "ответственный за производственный контроль",
                    "purpose": "контроль загазованности",
                },
                {
                    "name": "Огнетушитель порошковый",
                    "type": "firefighting",
                    "quantity": "4",
                    "storage_place": "котельная",
                    "responsible_person": "начальник участка",
                    "purpose": "ликвидация начального возгорания",
                },
            ]
        },
        "notification_scheme": {
            "first_receiver": "оператор котельной",
            "incident_commander": "ответственный руководитель работ",
            "pasf_caller": "дежурный диспетчер",
            "fire_caller": "оператор котельной",
            "medical_caller": "специалист по охране труда",
            "shutdown_responsible": "слесарь-ремонтник",
            "evacuation_responsible": "начальник смены",
            "service_meeting_responsible": "представитель администрации",
        },
        "financial_reserve": {
            "created": True,
            "order_number": "12-ПБ",
            "order_date": "2026-01-15",
            "amount": "500000",
            "responsible": "главный бухгалтер",
        },
        "insurance": {
            "has_contract": True,
            "company": "АО Страховая компания",
            "contract_number": "ГО-123456",
            "valid_until": "2027-01-15",
            "insured_amount": "10000000",
        },
    },
    "organization": {
        "id": str(uuid4()),
        "name": "ООО Газовый сервис",
        "inn": "7701234567",
        "address": "г. Тюмень, ул. Промышленная, 5",
        "phone": "+7(3452)12-34-56",
    },
    "facility": {
        "id": str(uuid4()),
        "name": "Котельная №1",
        "facility_type": "Сеть газопотребления",
        "hazard_class": "3",
        "address": "г. Тюмень, ул. Промышленная, 5",
        "reg_number": "77-1-2-0001-12345678",
        "latitude": 57.15,
        "longitude": 65.53,
    },
    "equipment": [
        {"name": "Котёл газовый", "equipment_type": "Теплогенератор", "serial_number": "KG-001", "manufacture_year": "2020"},
        {"name": "ГРУ", "equipment_type": "Газорегуляторный узел", "serial_number": "GRU-001", "manufacture_year": "2019"},
    ],
    "substances": [
        {"name": "природный газ", "cas_number": "74-82-8", "quantity_kg": 500},
    ],
    "responsible_persons": [
        {"full_name": "Иванов И.И.", "position": "Начальник участка", "phone": "+7(3452)12-34-57"},
    ],
    "emergency_services": [],
    "pasf": None,
    "material_reserve": {
        "fin_reserve_order": "12-ПБ от 2026-01-15",
        "fin_reserve_amount": "500000",
        "insurance_company": "АО Страховая компания",
        "insurance_contract": "ГО-123456",
    },
    "protective_equipment": [
        {"name": "Газоанализатор", "type": "control", "quantity": "1", "location": "операторная"},
        {"name": "Огнетушитель порошковый", "type": "firefighting", "quantity": "4", "location": "котельная"},
    ],
}


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

class TestAdaptContextForGenerator:
    """Test adapt_context_for_generator maps questionnaire fields correctly."""

    def setup_method(self):
        self.service = PmlaGenerationFromQuestionnaireService(
            document_repo=MagicMock(),
            regulatory_repo=MagicMock(),
            scenario_matrix_repo=MagicMock(),
        )

    def test_incident_history_no_incidents(self):
        ctx = self.service.adapt_context_for_generator(SAMPLE_QUESTIONNAIRE_DATA)
        items = ctx.get("accidents_and_incidents", [])
        assert len(items) == 1
        assert "не зарегистрированы" in items[0].get("description", "").lower()

    def test_custom_scenarios_appear(self):
        ctx = self.service.adapt_context_for_generator(SAMPLE_QUESTIONNAIRE_DATA)
        user_scenarios = ctx.get("user_scenarios", [])
        custom_names = [s.get("name", "") for s in user_scenarios if s.get("source") == "custom"]
        assert any("Отказ запорной арматуры" in name for name in custom_names)

    def test_protective_equipment_appears(self):
        ctx = self.service.adapt_context_for_generator(SAMPLE_QUESTIONNAIRE_DATA)
        pe = ctx.get("protective_equipment", [])
        names = [item.get("name", "") for item in pe]
        assert "Газоанализатор" in names
        assert any("Огнетушитель" in n for n in names)

    def test_notification_scheme_preserved(self):
        ctx = self.service.adapt_context_for_generator(SAMPLE_QUESTIONNAIRE_DATA)
        ns = ctx.get("notification_scheme", {})
        assert ns.get("first_receiver") == "оператор котельной"
        assert ns.get("pasf_caller") == "дежурный диспетчер"

    def test_material_reserve_financial(self):
        ctx = self.service.adapt_context_for_generator(SAMPLE_QUESTIONNAIRE_DATA)
        mr = ctx.get("material_reserve", {})
        assert "12-ПБ" in mr.get("fin_reserve_order", "")

    def test_insurance_in_material_reserve(self):
        ctx = self.service.adapt_context_for_generator(SAMPLE_QUESTIONNAIRE_DATA)
        mr = ctx.get("material_reserve", {})
        assert mr.get("insurance_company") == "АО Страховая компания"
        assert mr.get("insurance_contract") == "ГО-123456"


class TestDocumentContextFromDict:
    """Test DocumentContext.from_dict maps fields correctly."""

    def test_from_dict_maps_all_fields(self):
        ctx = self.service.adapt_context_for_generator(SAMPLE_QUESTIONNAIRE_DATA)
        doc_ctx = DocumentContext.from_dict(ctx)

        assert doc_ctx.facility.get("name") == "Котельная №1"
        assert doc_ctx.organization.get("name") == "ООО Газовый сервис"
        assert len(doc_ctx.equipment) == 2
        assert len(doc_ctx.substances) == 1
        assert len(doc_ctx.protective_equipment) == 2
        assert doc_ctx.notification_scheme.get("first_receiver") == "оператор котельной"
        assert "12-ПБ" in doc_ctx.material_reserve.get("fin_reserve_order", "")

    def setup_method(self):
        self.service = PmlaGenerationFromQuestionnaireService(
            document_repo=MagicMock(),
            regulatory_repo=MagicMock(),
            scenario_matrix_repo=MagicMock(),
        )


class TestDocxOutputContainsQuestionnaireData:
    """Test that DOCX output contains questionnaire data via engines."""

    def setup_method(self):
        self.service = PmlaGenerationFromQuestionnaireService(
            document_repo=MagicMock(),
            regulatory_repo=MagicMock(),
            scenario_matrix_repo=MagicMock(),
        )

    def _make_doc_context(self):
        ctx = self.service.adapt_context_for_generator(SAMPLE_QUESTIONNAIRE_DATA)
        return DocumentContext.from_dict(ctx)

    @pytest.mark.asyncio
    async def test_scenario_engine_renders_custom_scenario(self):
        from src.application.engines.scenario_engine import ScenarioEngine

        engine = ScenarioEngine()
        doc_ctx = self._make_doc_context()
        # Set scenarios from user_scenarios
        doc_ctx.scenarios = doc_ctx.user_scenarios

        result = await engine.generate("section_2", {"title": "Сценарии"}, doc_ctx)
        text = result.content
        assert "Отказ запорной арматуры" in text, f"Custom scenario missing in section_2: {text[:500]}"

    @pytest.mark.asyncio
    async def test_data_engine_renders_protective_equipment(self):
        from src.application.engines.data_engine import DataEngine

        engine = DataEngine()
        doc_ctx = self._make_doc_context()

        result = await engine.generate("section_4", {"title": "Силы и средства"}, doc_ctx)
        text = result.content
        assert "Газоанализатор" in text, f"Protective equipment missing in section_4: {text[:500]}"
        assert "Огнетушитель" in text, f"Fire extinguisher missing in section_4: {text[:500]}"

    @pytest.mark.asyncio
    async def test_data_engine_renders_notification_scheme(self):
        from src.application.engines.data_engine import DataEngine

        engine = DataEngine()
        doc_ctx = self._make_doc_context()

        result = await engine.generate("section_8", {"title": "Управление, связь"}, doc_ctx)
        text = result.content
        assert "оператор котельной" in text, f"Notification role missing in section_8: {text[:500]}"
        assert "дежурный диспетчер" in text, f"PASF caller missing in section_8: {text[:500]}"

    @pytest.mark.asyncio
    async def test_data_engine_renders_financial_reserve(self):
        from src.application.engines.data_engine import DataEngine

        engine = DataEngine()
        doc_ctx = self._make_doc_context()

        result = await engine.generate("section_13", {"title": "Материально-техническое обеспечение"}, doc_ctx)
        text = result.content
        assert "12-ПБ" in text, f"Financial order missing in section_13: {text[:500]}"
        assert "500000" in text, f"Financial amount missing in section_13: {text[:500]}"

    @pytest.mark.asyncio
    async def test_data_engine_renders_insurance(self):
        from src.application.engines.data_engine import DataEngine

        engine = DataEngine()
        doc_ctx = self._make_doc_context()

        result = await engine.generate("section_13", {"title": "Материально-техническое обеспечение"}, doc_ctx)
        text = result.content
        assert "АО Страховая компания" in text, f"Insurance company missing in section_13: {text[:500]}"
        assert "ГО-123456" in text, f"Insurance contract missing in section_13: {text[:500]}"

    @pytest.mark.asyncio
    async def test_special_section_renders_custom_scenario(self):
        from src.application.engines.scenario_engine import ScenarioEngine

        engine = ScenarioEngine()
        doc_ctx = self._make_doc_context()
        doc_ctx.scenarios = doc_ctx.user_scenarios

        result = await engine.generate("special_section", {"title": "Специальный раздел"}, doc_ctx)
        text = result.content
        assert "Отказ запорной арматуры" in text, f"Custom scenario missing in special_section: {text[:500]}"


class TestValidateContext:
    """Test validate_questionnaire_context warnings."""

    def setup_method(self):
        self.service = PmlaGenerationFromQuestionnaireService(
            document_repo=MagicMock(),
            regulatory_repo=MagicMock(),
            scenario_matrix_repo=MagicMock(),
        )

    def test_full_context_passes(self):
        ctx = self.service.adapt_context_for_generator(SAMPLE_QUESTIONNAIRE_DATA)
        result = self.service.validate_questionnaire_context(ctx)
        assert result["passed"] is True
        assert result["summary"]["selected_scenarios"] == 3
        assert result["summary"]["custom_scenarios"] == 1

    def test_missing_facility_fails(self):
        data = dict(SAMPLE_QUESTIONNAIRE_DATA)
        data["facility"] = {}
        ctx = self.service.adapt_context_for_generator(data)
        result = self.service.validate_questionnaire_context(ctx)
        assert result["passed"] is False
        assert any("facility" in e for e in result["errors"])


class TestDocxExtraction:
    """Test DOCX text extraction utility."""

    def test_extract_docx_text(self):
        doc = DocxDocument()
        doc.add_paragraph("Тестовый абзац")
        table = doc.add_table(rows=1, cols=2)
        table.cell(0, 0).text = "Ячейка 1"
        table.cell(0, 1).text = "Ячейка 2"
        import io
        buf = io.BytesIO()
        doc.save(buf)
        text = extract_docx_text(buf.getvalue())
        assert "Тестовый абзац" in text
        assert "Ячейка 1" in text
        assert "Ячейка 2" in text


class TestFullDocxBuildFromEngines:
    """Build a full DOCX from engine output and verify all questionnaire data appears."""

    def setup_method(self):
        self.service = PmlaGenerationFromQuestionnaireService(
            document_repo=MagicMock(),
            regulatory_repo=MagicMock(),
            scenario_matrix_repo=MagicMock(),
        )

    def _make_doc_context(self):
        ctx = self.service.adapt_context_for_generator(SAMPLE_QUESTIONNAIRE_DATA)
        return DocumentContext.from_dict(ctx)

    def _build_docx_text(self, all_blocks: dict) -> str:
        """Simulate DOCX building from engine block output and extract text."""
        import io
        from docx.shared import Pt, Cm
        from src.application.engines.blocks import HeadingBlock, ParagraphBlock, TableBlock

        doc = DocxDocument()
        section_layout = doc.sections[0]
        section_layout.top_margin = Cm(2.0)
        section_layout.bottom_margin = Cm(2.0)
        section_layout.left_margin = Cm(3.0)
        section_layout.right_margin = Cm(1.5)

        style = doc.styles["Normal"]
        style.font.name = "Times New Roman"
        style.font.size = Pt(12)

        for title, blocks_or_str in all_blocks.items():
            if isinstance(blocks_or_str, str):
                doc.add_paragraph(blocks_or_str)
            elif isinstance(blocks_or_str, list):
                for block in blocks_or_str:
                    if isinstance(block, HeadingBlock):
                        h = doc.add_heading(level=block.level)
                        h.text = block.text
                    elif isinstance(block, ParagraphBlock):
                        p = doc.add_paragraph()
                        run = p.add_run(block.text)
                        run.font.name = "Times New Roman"
                        run.font.size = Pt(12)
                    elif isinstance(block, TableBlock):
                        num_rows = 1 + len(block.rows)
                        num_cols = len(block.headers)
                        t = doc.add_table(rows=num_rows, cols=num_cols)
                        for j, hdr in enumerate(block.headers):
                            t.cell(0, j).text = str(hdr)
                        for i, row in enumerate(block.rows):
                            for j, val in enumerate(row):
                                t.cell(i + 1, j).text = str(val)

        buf = io.BytesIO()
        doc.save(buf)
        return extract_docx_text(buf.getvalue())

    @pytest.mark.asyncio
    async def test_full_pipeline_text_contains_all_questionnaire_data(self):
        """Run DataEngine + ScenarioEngine for all relevant sections and build DOCX."""
        from src.application.engines.data_engine import DataEngine
        from src.application.engines.scenario_engine import ScenarioEngine

        doc_ctx = self._make_doc_context()
        doc_ctx.scenarios = doc_ctx.user_scenarios

        title_map = {
            "section_1": "Характеристика объекта",
            "section_2": "Сценарии аварий",
            "section_3": "Аварийность",
            "section_4": "Силы и средства",
            "section_6": "Состав и дислокация",
            "section_8": "Управление, связь, оповещение",
            "section_13": "Материально-техническое обеспечение",
            "special_section": "Специальный раздел",
        }

        sections = {}
        for engine in [DataEngine(), ScenarioEngine()]:
            ids = {
                DataEngine: ["section_1", "section_3", "section_4", "section_6", "section_8", "section_13"],
                ScenarioEngine: ["section_2", "special_section"],
            }
            for sid in ids[type(engine)]:
                result = await engine.generate(sid, {"title": title_map[sid]}, doc_ctx)
                sections[title_map[sid]] = result.blocks or result.content

        text = self._build_docx_text(sections)

        required = [
            "Отказ запорной арматуры",
            "Газоанализатор",
            "Огнетушитель",
            "оператор котельной",
            "дежурный диспетчер",
            "12-ПБ",
            "АО Страховая компания",
            "ГО-123456",
            "не зарегистрированы",
        ]

        found = []
        missing = []
        for item in required:
            if item in text:
                found.append(item)
            else:
                missing.append(item)

        assert not missing, f"Missing in DOCX: {missing}\n\nDOCX text preview:\n{text[:3000]}"
        assert len(found) == len(required), f"Only {len(found)}/{len(required)} found"
