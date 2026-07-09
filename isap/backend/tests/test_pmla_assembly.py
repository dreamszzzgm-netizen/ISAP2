"""
Тесты для PMLA Assembly Layer:
- Block registry completeness
- Correction journal DOCX table
- TOC placeholder
- Appendices manifest table
- Static blocks don't require LLM
- No raw HTML in DOCX
"""
from __future__ import annotations

import io
import pytest
from unittest.mock import AsyncMock, MagicMock

from docx import Document as DocxDocument


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_gen():
    """Создаёт EnhancedDocumentGenerator с моками."""
    from src.application.services.enhanced_generator import EnhancedDocumentGenerator
    retriever = AsyncMock()
    retriever.retrieve.return_value = []
    doc_repo = AsyncMock()
    reg_repo = AsyncMock()
    reg_repo.session = AsyncMock()
    return EnhancedDocumentGenerator(
        local_llm=None, external_llm=None, retriever=retriever,
        document_repo=doc_repo, regulatory_repo=reg_repo,
    )


def _extract_docx_text(docx_bytes: bytes) -> str:
    """Извлекает текст из DOCX."""
    doc = DocxDocument(io.BytesIO(docx_bytes))
    return "\n".join(p.text for p in doc.paragraphs)


def _extract_docx_tables(docx_bytes: bytes) -> list[list[list[str]]]:
    """Извлекает все таблицы из DOCX."""
    doc = DocxDocument(io.BytesIO(docx_bytes))
    tables = []
    for table in doc.tables:
        rows = []
        for row in table.rows:
            rows.append([cell.text for cell in row.cells])
        tables.append(rows)
    return tables


def _minimal_context():
    return {
        "organization": {"name": "ТестОрг", "inn": "1234567890"},
        "facility": {"name": "Объект", "facility_type": "Котельная", "hazard_class": "III"},
        "equipment": [{"name": "Котёл", "equipment_type": "Теплогенератор"}],
        "substances": [{"name": "Метан", "quantity_kg": 500}],
        "responsible_persons": [
            {"full_name": "Иванов И.И.", "phone": "+79991112233", "position": "Инженер"}
        ],
    }


# ===========================================================================
# 1. Block Registry
# ===========================================================================

class TestBlockRegistry:
    """Тесты реестра типов блоков."""

    def test_registry_covers_all_sections(self):
        """Все 27 разделов из structure.json имеют block_type."""
        import json
        from pathlib import Path
        from src.application.services.pmla_assembly_blocks import ASSEMBLY_REGISTRY

        structure_path = Path(__file__).parent.parent / "templates" / "pmla" / "structure.json"
        structure = json.loads(structure_path.read_text(encoding="utf-8"))
        section_ids = {s["id"] for s in structure["sections"]}

        registry_ids = set(ASSEMBLY_REGISTRY.keys())
        missing = section_ids - registry_ids
        extra = registry_ids - section_ids

        assert not missing, f"Sections in structure.json but not in registry: {missing}"
        assert not extra, f"Sections in registry but not in structure.json: {extra}"

    def test_static_sections_have_no_llm(self):
        """Static блоки не требуют LLM."""
        from src.application.services.pmla_assembly_blocks import (
            get_static_sections, requires_llm,
        )
        for sid in get_static_sections():
            assert not requires_llm(sid), f"Static section '{sid}' should not require LLM"

    def test_generated_sections_require_llm(self):
        """Generated блоки требуют LLM."""
        from src.application.services.pmla_assembly_blocks import (
            get_generated_sections, requires_llm,
        )
        for sid in get_generated_sections():
            assert requires_llm(sid), f"Generated section '{sid}' should require LLM"

    def test_get_block_type_returns_correct_types(self):
        """get_block_type возвращает правильные типы."""
        from src.application.services.pmla_assembly_blocks import get_block_type, BlockType
        assert get_block_type("correction_log") == BlockType.STATIC
        assert get_block_type("toc") == BlockType.WORD_TOC
        assert get_block_type("title_page") == BlockType.VARIABLE
        assert get_block_type("introduction") == BlockType.GENERATED
        assert get_block_type("appendix_1") == BlockType.APPENDIX_REF
        assert get_block_type("nonexistent") is None


# ===========================================================================
# 2. Correction Journal
# ===========================================================================

class TestCorrectionJournal:
    """Тесты журнала корректировки как DOCX-таблицы."""

    def test_correction_journal_appears_in_docx(self):
        """Журнал корректировки появляется в DOCX."""
        from src.infrastructure.export.docx_helpers import add_correction_journal
        doc = DocxDocument()
        add_correction_journal(doc)
        buf = io.BytesIO()
        doc.save(buf)
        text = _extract_docx_text(buf.getvalue())
        assert "Журнал корректировки документа" in text

    def test_correction_journal_has_table_columns(self):
        """Таблица журнала содержит нужные колонки."""
        from src.infrastructure.export.docx_helpers import add_correction_journal
        doc = DocxDocument()
        add_correction_journal(doc)
        buf = io.BytesIO()
        doc.save(buf)
        tables = _extract_docx_tables(buf.getvalue())
        assert len(tables) >= 1
        header_row = tables[0][0]
        assert "№ п/п" in header_row
        assert "Дата изменения" in header_row
        assert "Содержание изменения" in header_row

    def test_correction_journal_default_empty_row(self):
        """По умолчанию есть одна пустая строка данных."""
        from src.infrastructure.export.docx_helpers import add_correction_journal
        doc = DocxDocument()
        add_correction_journal(doc)
        buf = io.BytesIO()
        doc.save(buf)
        tables = _extract_docx_tables(buf.getvalue())
        # 1 header row + 1 empty data row
        assert len(tables[0]) == 2

    def test_correction_journal_with_corrections(self):
        """Журнал с данными заполняет строки."""
        from src.infrastructure.export.docx_helpers import add_correction_journal
        doc = DocxDocument()
        corrections = [
            {"date": "2026-01-15", "section_page": "раздел 3", "description": "Добавлена статистика", "basis": "приказ", "signature": ""}
        ]
        add_correction_journal(doc, corrections)
        buf = io.BytesIO()
        doc.save(buf)
        tables = _extract_docx_tables(buf.getvalue())
        # 1 header + 1 data row
        assert len(tables[0]) == 2
        assert "2026-01-15" in tables[0][1][1]


# ===========================================================================
# 3. TOC Placeholder
# ===========================================================================

class TestTocPlaceholder:
    """Тесты содержания (Word TOC field)."""

    def test_toc_placeholder_appears_in_docx(self):
        """Содержание появляется в DOCX."""
        from src.infrastructure.export.docx_helpers import add_toc_placeholder
        doc = DocxDocument()
        add_toc_placeholder(doc)
        buf = io.BytesIO()
        doc.save(buf)
        text = _extract_docx_text(buf.getvalue())
        assert "Содержание" in text

    def test_toc_has_update_hint(self):
        """Содержание содержит подсказку об обновлении."""
        from src.infrastructure.export.docx_helpers import add_toc_placeholder
        doc = DocxDocument()
        add_toc_placeholder(doc)
        buf = io.BytesIO()
        doc.save(buf)
        text = _extract_docx_text(buf.getvalue())
        assert "Обновите содержание" in text


# ===========================================================================
# 4. Appendices Manifest
# ===========================================================================

class TestAppendicesManifest:
    """Тесты манифеста приложений."""

    def test_appendices_manifest_renders_in_docx(self):
        """Манифест приложений появляется в DOCX."""
        from src.infrastructure.export.docx_helpers import add_appendices_manifest
        doc = DocxDocument()
        appendices = [
            {"appendix_number": 1, "title": "Порядок изучения ПМЛА", "filename": "", "present": False},
            {"appendix_number": 2, "title": "Форма сообщения", "filename": "form.docx", "present": True},
        ]
        add_appendices_manifest(doc, appendices)
        buf = io.BytesIO()
        doc.save(buf)
        tables = _extract_docx_tables(buf.getvalue())
        all_cell_text = " ".join(cell for row in tables for cells in row for cell in cells)
        assert "Приложения" in _extract_docx_text(buf.getvalue())
        assert "Порядок изучения ПМЛА" in all_cell_text
        assert "Форма сообщения" in all_cell_text

    def test_appendices_manifest_table_columns(self):
        """Таблица манифеста содержит нужные колонки."""
        from src.infrastructure.export.docx_helpers import add_appendices_manifest
        doc = DocxDocument()
        appendices = [
            {"appendix_number": 1, "title": "Тест", "filename": "", "present": False},
        ]
        add_appendices_manifest(doc, appendices)
        buf = io.BytesIO()
        doc.save(buf)
        tables = _extract_docx_tables(buf.getvalue())
        assert len(tables) >= 1
        header_row = tables[0][0]
        assert "№ приложения" in header_row
        assert "Наименование" in header_row
        assert "Файл" in header_row
        assert "Наличие" in header_row

    def test_appendices_manifest_status(self):
        """Статус наличия отображается корректно."""
        from src.infrastructure.export.docx_helpers import add_appendices_manifest
        doc = DocxDocument()
        appendices = [
            {"appendix_number": 1, "title": "Есть", "filename": "a.pdf", "present": True},
            {"appendix_number": 2, "title": "Нет", "filename": "", "present": False},
        ]
        add_appendices_manifest(doc, appendices)
        buf = io.BytesIO()
        doc.save(buf)
        tables = _extract_docx_tables(buf.getvalue())
        assert "представлен" in tables[0][1][3]
        assert "не представлен" in tables[0][2][3]

    def test_appendices_manifest_empty(self):
        """Пустой манифест — сообщение «Приложения не представлены»."""
        from src.infrastructure.export.docx_helpers import add_appendices_manifest
        doc = DocxDocument()
        add_appendices_manifest(doc, [])
        buf = io.BytesIO()
        doc.save(buf)
        text = _extract_docx_text(buf.getvalue())
        assert "не представлены" in text


# ===========================================================================
# 5. No Raw HTML
# ===========================================================================

class TestNoRawHtml:
    """Тесты отсутствия сырого HTML в DOCX."""

    def test_correction_journal_no_html(self):
        """Журнал корректировки не содержит HTML-тегов."""
        from src.infrastructure.export.docx_helpers import add_correction_journal
        doc = DocxDocument()
        add_correction_journal(doc)
        buf = io.BytesIO()
        doc.save(buf)
        text = _extract_docx_text(buf.getvalue())
        assert "<td>" not in text
        assert "<tr>" not in text
        assert "<table>" not in text

    def test_toc_placeholder_no_html(self):
        """Содержание не содержит HTML-тегов."""
        from src.infrastructure.export.docx_helpers import add_toc_placeholder
        doc = DocxDocument()
        add_toc_placeholder(doc)
        buf = io.BytesIO()
        doc.save(buf)
        text = _extract_docx_text(buf.getvalue())
        assert "<td>" not in text
        assert "<tr>" not in text

    def test_appendices_manifest_no_html(self):
        """Манифест приложений не содержит HTML-тегов."""
        from src.infrastructure.export.docx_helpers import add_appendices_manifest
        doc = DocxDocument()
        add_appendices_manifest(doc, [{"appendix_number": 1, "title": "Тест", "filename": "", "present": False}])
        buf = io.BytesIO()
        doc.save(buf)
        text = _extract_docx_text(buf.getvalue())
        assert "<td>" not in text
        assert "<tr>" not in text


# ===========================================================================
# 6. Static blocks don't require LLM
# ===========================================================================

class TestStaticBlocksNoLlm:
    """Static блоки генерируются без LLM."""

    def test_abbreviations_static(self):
        """Раздел abbreviations — static_block, не требует LLM."""
        from src.application.services.pmla_assembly_blocks import get_block_type, BlockType
        assert get_block_type("abbreviations") == BlockType.STATIC

    def test_terms_static(self):
        """Раздел terms — static_block."""
        from src.application.services.pmla_assembly_blocks import get_block_type, BlockType
        assert get_block_type("terms") == BlockType.STATIC

    def test_bibliography_static(self):
        """Раздел bibliography — static_block."""
        from src.application.services.pmla_assembly_blocks import get_block_type, BlockType
        assert get_block_type("bibliography") == BlockType.STATIC

    def test_correction_log_static(self):
        """Раздел correction_log — static_block."""
        from src.application.services.pmla_assembly_blocks import get_block_type, BlockType
        assert get_block_type("correction_log") == BlockType.STATIC
