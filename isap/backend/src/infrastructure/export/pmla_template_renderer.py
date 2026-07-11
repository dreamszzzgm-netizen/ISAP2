"""PMLA Template Renderer — renders DOCX from template via docxtpl.

This is the core rendering engine for the v2 PMLA template. It takes a context
dict with all required fields and produces a rendered DOCX file.

Architecture:
- Uses docxtpl + Jinja2 for template rendering
- Post-processes to remove artifacts (yellow highlights, empty Jinja lines)
- Sets field-update-on-open for TOC/NUMPAGES
"""
from __future__ import annotations

import io
import logging
import os
import re
import tempfile
import zipfile
from copy import deepcopy
from pathlib import Path
from xml.etree import ElementTree as ET

from docx import Document
from docx.oxml.ns import qn

logger = logging.getLogger(__name__)

# backend/src/infrastructure/export/ → 5 levels up = isap/ (project root)
TEMPLATES_DIR = Path(__file__).parent.parent.parent.parent.parent / "files"

# Jinja artifacts to remove from rendered document
JINJA_LINE_RE = re.compile(r"^\s*\{%.*?%\}\s*$", re.DOTALL)
JINJA_TAG_RE = re.compile(r"\{[%{].*?[%}]\}")


class PmlaTemplateRenderer:
    """Renders PMLA DOCX from a Jinja2 template using docxtpl."""

    def __init__(self, template_path: str | Path | None = None):
        self.template_path = Path(template_path) if template_path else TEMPLATES_DIR / "pmla_v2_template.docx"

    def render(self, context: dict) -> bytes:
        """Render the template with the given context. Returns DOCX bytes.
        
        Args:
            context: Dict with all template variables (organization, facility,
                     equipment_list, substance_params, etc.)
        
        Returns:
            Rendered DOCX as bytes.
        """
        from docxtpl import DocxTemplate

        logger.info("Rendering PMLA template: %s", self.template_path)
        doc = DocxTemplate(str(self.template_path))
        doc.render(context)

        # Post-process
        self._remove_jinja_artifacts(doc)
        self._set_field_update_on_open(doc)

        # Save to bytes
        buf = io.BytesIO()
        doc.save(buf)
        docx_bytes = buf.getvalue()

        # Second pass: remove any remaining Jinja lines via XML
        docx_bytes = self._clean_xml_jinja(docx_bytes)

        logger.info("Rendered PMLA: %d bytes", len(docx_bytes))
        return docx_bytes

    def render_to_file(self, context: dict, output_path: str | Path) -> Path:
        """Render and save to a file."""
        output_path = Path(output_path)
        docx_bytes = self.render(context)
        output_path.write_bytes(docx_bytes)
        return output_path

    def _remove_jinja_artifacts(self, doc: Document) -> None:
        """Remove yellow highlight from Jinja placeholders and empty Jinja lines."""
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for para in cell.paragraphs:
                        text = para.text.strip()
                        # Remove paragraphs that are only Jinja control tags
                        if JINJA_LINE_RE.match(text):
                            # Clear the paragraph but keep it (don't remove XML element
                            # to avoid breaking table structure)
                            for run in para.runs:
                                run.text = ""

    def _set_field_update_on_open(self, doc: Document) -> None:
        """Set the document to update fields when opened in Word."""
        from lxml import etree
        # settings.element IS the lxml element in python-docx
        settings_el = doc.settings.element
        # Use lxml find on the element directly
        nsmap = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        update_fields = settings_el.find('.//w:updateFields', nsmap)
        if update_fields is None:
            update_fields = etree.SubElement(settings_el, qn("w:updateFields"))
        update_fields.set(qn("w:val"), "true")

    def _clean_xml_jinja(self, docx_bytes: bytes) -> bytes:
        """Remove any remaining Jinja artifacts from the DOCX XML.
        
        Processes word/document.xml, headers, and footers to remove
        any stray Jinja tags that docxtpl may have left behind.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Extract DOCX (it's a ZIP)
            docx_path = os.path.join(tmpdir, "input.docx")
            with open(docx_path, "wb") as f:
                f.write(docx_bytes)

            with zipfile.ZipFile(docx_path, "r") as zin:
                zin.extractall(tmpdir)

            # Process XML files
            xml_files = [
                "word/document.xml",
            ]
            # Also process headers and footers
            word_dir = os.path.join(tmpdir, "word")
            if os.path.isdir(word_dir):
                for fname in os.listdir(word_dir):
                    if fname.startswith("header") or fname.startswith("footer"):
                        xml_files.append(f"word/{fname}")

            for xml_rel in xml_files:
                xml_path = os.path.join(tmpdir, xml_rel)
                if not os.path.exists(xml_path):
                    continue
                try:
                    tree = ET.parse(xml_path)
                    root = tree.getroot()
                    # Find all text elements and clean Jinja artifacts
                    for t_elem in root.iter(qn("w:t")):
                        if t_elem.text and JINJA_TAG_RE.search(t_elem.text):
                            # Remove Jinja tags from text
                            t_elem.text = JINJA_TAG_RE.sub("", t_elem.text)
                    tree.write(xml_path, xml_declaration=True, encoding="UTF-8")
                except ET.ParseError:
                    logger.warning("Could not parse XML: %s", xml_rel)

            # Repackage as DOCX
            output_buf = io.BytesIO()
            with zipfile.ZipFile(output_buf, "w", zipfile.ZIP_DEFLATED) as zout:
                for root_dir, dirs, files in os.walk(tmpdir):
                    for file in files:
                        file_path = os.path.join(root_dir, file)
                        arcname = os.path.relpath(file_path, tmpdir)
                        zout.write(file_path, arcname)

            return output_buf.getvalue()


def render_pmla_document(context: dict, template_path: str | Path | None = None) -> bytes:
    """Convenience function to render a PMLA document.
    
    Args:
        context: Template context dict
        template_path: Optional custom template path
    
    Returns:
        Rendered DOCX bytes
    """
    renderer = PmlaTemplateRenderer(template_path)
    return renderer.render(context)
