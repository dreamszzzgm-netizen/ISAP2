"""Helper functions for DOCX document generation.

Provides reusable formatting helpers for building professional DOCX documents
without mixing formatting logic into business logic.
"""
from __future__ import annotations

import re
from io import BytesIO

from docx import Document as DocxDocument
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt, RGBColor
from docx.oxml.ns import qn

BODY_FONT_NAME = "Times New Roman"
BODY_FONT_SIZE_PT = 12
HEADING_FONT_SIZE_PT = 14
FIRST_LINE_INDENT_CM = 1.25

BOLD_RE = re.compile(r"\*\*(.+?)\*\*")


def safe_text(value) -> str:
    """Convert value to safe string, replacing None/null/undefined with 'не указано'."""
    if value is None:
        return "не указано"
    if isinstance(value, bool):
        return "да" if value else "нет"
    if isinstance(value, (list, dict)):
        if not value:
            return "не указано"
        return str(value)
    s = str(value).strip()
    if not s or s in ("None", "null", "undefined", "{}", "[]"):
        return "не указано"
    return s


def set_document_margins(doc: DocxDocument, top: float = 2.0, bottom: float = 2.0, left: float = 3.0, right: float = 1.5) -> None:
    """Set page margins in centimeters."""
    section = doc.sections[0]
    section.top_margin = Cm(top)
    section.bottom_margin = Cm(bottom)
    section.left_margin = Cm(left)
    section.right_margin = Cm(right)


def set_default_font(doc: DocxDocument, font_name: str = BODY_FONT_NAME, font_size: int = BODY_FONT_SIZE_PT) -> None:
    """Set the default document font."""
    normal = doc.styles["Normal"]
    normal.font.name = font_name
    normal.font.size = Pt(font_size)
    # Set East Asian font
    rpr = normal.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = rpr.makeelement(qn("w:rFonts"), {})
        rpr.append(rfonts)
    rfonts.set(qn("w:eastAsia"), font_name)


def add_heading(doc: DocxDocument, text: str, level: int = 1, center: bool = False) -> None:
    """Add a heading with proper formatting."""
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER if center else WD_ALIGN_PARAGRAPH.LEFT
    paragraph.paragraph_format.first_line_indent = Cm(0)
    run = paragraph.add_run(safe_text(text))
    run.font.name = BODY_FONT_NAME
    run.font.bold = True
    run.font.size = Pt(HEADING_FONT_SIZE_PT if level == 0 else max(HEADING_FONT_SIZE_PT - 2 * (level - 1), 12))
    run.font.color.rgb = RGBColor(0, 0, 0)


def add_body_paragraph(doc: DocxDocument, text: str, bold: bool = False) -> None:
    """Add a body paragraph with optional bold formatting."""
    paragraph = doc.add_paragraph()
    if bold:
        paragraph.paragraph_format.first_line_indent = Cm(FIRST_LINE_INDENT_CM)
        run = paragraph.add_run(safe_text(text))
        run.font.name = BODY_FONT_NAME
        run.font.bold = True
        run.font.size = Pt(BODY_FONT_SIZE_PT)
    else:
        # Handle **bold** markdown
        pos = 0
        for match in BOLD_RE.finditer(text):
            if match.start() > pos:
                paragraph.add_run(text[pos:match.start()])
            bold_run = paragraph.add_run(match.group(1))
            bold_run.font.bold = True
            pos = match.end()
        if pos < len(text):
            paragraph.add_run(text[pos:])


def add_kv_table(doc: DocxDocument, rows: list[tuple[str, str]], caption: str | None = None) -> None:
    """Add a key-value table (2 columns: label, value)."""
    if caption:
        cap = doc.add_paragraph()
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cap.paragraph_format.first_line_indent = Cm(0)
        run = cap.add_run(caption)
        run.font.name = BODY_FONT_NAME
        run.font.bold = True
        run.font.size = Pt(BODY_FONT_SIZE_PT)

    table = doc.add_table(rows=len(rows), cols=2)
    table.style = "Table Grid"
    table.alignment = 1  # WD_TABLE_ALIGNMENT.CENTER

    for i, (label, value) in enumerate(rows):
        # Label cell (bold)
        cell_label = table.rows[i].cells[0]
        cell_label.text = ""
        p = cell_label.paragraphs[0]
        run = p.add_run(safe_text(label))
        run.font.name = BODY_FONT_NAME
        run.font.bold = True
        run.font.size = Pt(BODY_FONT_SIZE_PT)

        # Value cell
        cell_value = table.rows[i].cells[1]
        cell_value.text = ""
        p = cell_value.paragraphs[0]
        run = p.add_run(safe_text(value))
        run.font.name = BODY_FONT_NAME
        run.font.size = Pt(BODY_FONT_SIZE_PT)

    doc.add_paragraph()


def add_data_table(doc: DocxDocument, headers: list[str], rows: list[list[str]], caption: str | None = None) -> None:
    """Add a data table with headers and rows."""
    if caption:
        cap = doc.add_paragraph()
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cap.paragraph_format.first_line_indent = Cm(0)
        run = cap.add_run(caption)
        run.font.name = BODY_FONT_NAME
        run.font.bold = True
        run.font.size = Pt(BODY_FONT_SIZE_PT)

    num_cols = len(headers)
    num_rows = len(rows) + 1
    table = doc.add_table(rows=num_rows, cols=num_cols)
    table.style = "Table Grid"
    table.alignment = 1  # WD_TABLE_ALIGNMENT.CENTER

    # Headers (bold)
    for i, header in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = ""
        p = cell.paragraphs[0]
        run = p.add_run(safe_text(header))
        run.font.name = BODY_FONT_NAME
        run.font.bold = True
        run.font.size = Pt(BODY_FONT_SIZE_PT)

    # Data rows
    for row_idx, row_data in enumerate(rows, 1):
        for col_idx, cell_text in enumerate(row_data):
            if col_idx < num_cols:
                cell = table.rows[row_idx].cells[col_idx]
                cell.text = ""
                p = cell.paragraphs[0]
                run = p.add_run(safe_text(cell_text))
                run.font.name = BODY_FONT_NAME
                run.font.size = Pt(BODY_FONT_SIZE_PT)

    doc.add_paragraph()


def create_title_page(doc: DocxDocument, context: dict) -> None:
    """Create a professional title page for the PMLA document."""
    # Organization info
    org = context.get("organization", {})
    facility = context.get("facility", {})

    # Add some spacing at the top
    for _ in range(3):
        p = doc.add_paragraph()
        p.paragraph_format.first_line_indent = Cm(0)

    # Main title
    title_text = "ПЛАН МЕРОПРИЯТИЙ\nпо локализации и ликвидации последствий аварий\nна опасном производственном объекте"
    add_heading(doc, title_text, level=0, center=True)

    # Spacing
    doc.add_paragraph()
    doc.add_paragraph()

    # Info table
    info_rows = [
        ("Наименование организации", safe_text(org.get("name"))),
        ("Наименование ОПО", safe_text(facility.get("name"))),
        ("Регистрационный номер ОПО", safe_text(facility.get("reg_number"))),
        ("Класс опасности", safe_text(facility.get("hazard_class"))),
        ("Адрес ОПО", safe_text(facility.get("address"))),
    ]
    add_kv_table(doc, info_rows)

    # Spacing
    for _ in range(3):
        doc.add_paragraph()

    # Year
    from datetime import datetime
    year = str(datetime.now().year)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Cm(0)
    run = p.add_run(f"Год: {year}")
    run.font.name = BODY_FONT_NAME
    run.font.size = Pt(BODY_FONT_SIZE_PT)

    # Page break
    doc.add_page_break()


def add_appendices_section(doc: DocxDocument, attachments_checklist: list[dict] | None = None) -> None:
    """Add the Appendices section with checklist."""
    add_heading(doc, "Приложения", level=1, center=False)

    if not attachments_checklist:
        add_body_paragraph(doc, "Приложения не представлены.")
        return

    appendix_num = 1
    for attachment in attachments_checklist:
        name = attachment.get("name", f"Приложение {appendix_num}")
        present = attachment.get("present", False)
        status = "" if present else " — не представлено"
        add_body_paragraph(doc, f"Приложение {appendix_num}. {name}{status}")
        appendix_num += 1
