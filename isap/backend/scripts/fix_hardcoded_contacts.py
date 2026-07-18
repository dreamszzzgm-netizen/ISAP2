"""Replace hardcoded service phones and names with Jinja placeholders in template DOCX.

Strategy:
- Open DOCX as ZIP
- Read word/document.xml
- Replace text inside w:t elements ONLY (not drawings/shapes)
- Operate paragraph-by-paragraph, merge split runs into one w:t
- Preserve formatting of the first run in the paragraph
- Save back to template
"""
from __future__ import annotations

import re
import shutil
import zipfile
from pathlib import Path

TEMPLATE = Path("/files/pmla_v2_template.docx")
BACKUP = Path("/files/backups/pmla_v2_template_before_contacts_fix.docx")

# Mapping: (old_text_substring, new_jinja_placeholder)
# Order matters: longer/more-specific first
REPLACEMENTS: list[tuple[str, str]] = [
    # Gas supply (gas supply org phone)
    ("+7 (86630) 4-18-68, 4-18-53", "{{ notification_gas_phone }}"),
    ("+7 (86630) 4-18-68; 4-18-53", "{{ notification_gas_phone }}"),
    ("+7 (86630) 4-18-68", "{{ notification_gas_phone }}"),
    ("7 (86630) 4-18-68;", "{{ notification_gas_phone }}"),
    # Fire department
    ("+7 (8663) 04-14-91", "{{ notification_fire_phone }}"),
    ("+7(8663) 04-14-91", "{{ notification_fire_phone }}"),
    # PASF / contractor
    ("+7 (903) 495-75-57, +7 (903) 491-85-75", "{{ notification_pasf_phone }}"),
    ("+7 (903) 495-75-57", "{{ notification_pasf_phone }}"),
    ("+7 (903) 491-85-75", "{{ notification_pasf_phone }}"),
    # Rostekhnadzor
    ("+7 (928) 307-04-62", "{{ notification_rostechnadzor_phone }}"),
    # MChS
    ("+7 (8662) 39-99-99", "{{ notification_mchs_phone }}"),
    # Administration
    ("+7 (86630) 7-63-99", "{{ notification_admin_phone }}"),
    # Electric networks
    ("+7 (86630)4-27-70", "{{ notification_electric_phone }}"),
    ("+7 (86630) 4-27-70", "{{ notification_electric_phone }}"),
    # Service names (longer first)
    ("ГУ МЧС России по КБР", "{{ mchs_department_name }}"),
    ("Главного управления МЧС России по КБР", "Главного управления МЧС России {{ mchs_department_name }}"),
    ("Кавказское управление Ростехнадзора", "{{ rostechnadzor_department_name }}"),
    ("Чегемские Районные Электрические Сети", "{{ electric_network_name }}"),
    ("Чегемские РЭС", "{{ electric_network_name }}"),
    ("Местная администрация с.п. Чегем Второй", "{{ local_administration_name }}"),
    ("местную администрацию с.п. Чегем Второй", "местную администрацию ({{ local_administration_name }})"),
    ("ЕДДС Чегемского района", "{{ edds_name }}"),
    ("Председатель СПК «АЛБИР» Алакаев Инал Таламашевич", "Председатель ({{ organization_full_name }})"),
    ("Помощник председателя Алакаев Амир Иналович", "Помощник председателя"),
    ("СПАО «ИНГОССТРАХ»", "{{ opo_insurance_company_name }}"),
]


def extract_wt_text(p_xml: str) -> str:
    """Concatenate all w:t text content in a paragraph."""
    parts = re.findall(r"<w:t[^>]*>(.*?)</w:t>", p_xml, re.DOTALL)
    return "".join(parts)


def is_drawing_paragraph(p_xml: str) -> bool:
    """True if paragraph contains drawing/shape content we should not touch."""
    return (
        "<w:drawing" in p_xml
        or "<wps:txbx" in p_xml
        or "<mc:AlternateContent" in p_xml
        or "<a:t>" in p_xml  # drawing shape text uses a:t
    )


def replace_in_paragraph(p_xml: str) -> str:
    """Replace hardcoded values in a single paragraph XML, preserving structure.

    For paragraphs that contain target text split across multiple w:t runs,
    we collapse all w:t into a single w:t with the first run's rPr formatting.
    """
    if is_drawing_paragraph(p_xml):
        return p_xml

    original_text = extract_wt_text(p_xml)
    if not original_text:
        return p_xml

    # Apply replacements on the concatenated text
    new_text = original_text
    changed = False
    for old, new in REPLACEMENTS:
        if old in new_text:
            new_text = new_text.replace(old, new)
            changed = True

    if not changed:
        return p_xml

    # Replace all <w:t>...</w:t> with a single <w:t xml:space="preserve">{new_text}</w:t>
    # Preserve the first w:r with its rPr, drop the rest of text runs.
    # Strategy: find first <w:r>...<w:t>...</w:t>...</w:r>, modify its w:t to new_text,
    # and empty out all other <w:t> in the paragraph.

    # Get first w:r rPr (formatting)
    rpr_match = re.search(r"<w:r[^>]*>(\s*<w:rPr>.*?</w:rPr>)?\s*<w:t", p_xml, re.DOTALL)
    rpr = rpr_match.group(1) if rpr_match and rpr_match.group(1) else ""

    # Replace each <w:t...>content</w:t> — first one gets new_text, others get empty
    replacement_count = [0]

    def replace_wt(match: re.Match) -> str:
        replacement_count[0] += 1
        if replacement_count[0] == 1:
            return f'<w:t xml:space="preserve">{new_text}</w:t>'
        return ""

    # Pattern: <w:t...>content</w:t> (any attrs, multiline content)
    new_p_xml = re.sub(
        r"<w:t[^>]*>.*?</w:t>",
        replace_wt,
        p_xml,
        count=0,
        flags=re.DOTALL,
    )
    # If no <w:t>...</w:t> was found at all (self-closing?), skip
    if replacement_count[0] == 0:
        return p_xml
    return new_p_xml


def main() -> None:
    if not TEMPLATE.exists():
        raise SystemExit(f"Template not found: {TEMPLATE}")
    BACKUP.parent.mkdir(parents=True, exist_ok=True)
    if not BACKUP.exists():
        shutil.copy2(TEMPLATE, BACKUP)
        print(f"Backup created: {BACKUP}")

    # Read all entries
    with zipfile.ZipFile(TEMPLATE, "r") as zf:
        entries = {n: zf.read(n) for n in zf.namelist()}

    doc_xml = entries["word/document.xml"].decode("utf-8")

    # Process paragraphs
    paragraphs = re.findall(r"<w:p\b[^>]*>.*?</w:p>", doc_xml, re.DOTALL)
    print(f"Total paragraphs: {len(paragraphs)}")

    changes = 0
    new_doc_xml = doc_xml
    for p in paragraphs:
        new_p = replace_in_paragraph(p)
        if new_p != p:
            # Replace once (paragraphs may be similar; use count=1 to be safe)
            new_doc_xml = new_doc_xml.replace(p, new_p, 1)
            changes += 1
            text = extract_wt_text(new_p)
            snippet = re.sub(r"\s+", " ", text)[:200]
            print(f"  CHANGED: {snippet}")

    print(f"Paragraphs changed: {changes}")

    entries["word/document.xml"] = new_doc_xml.encode("utf-8")

    # Write back
    with zipfile.ZipFile(TEMPLATE, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in entries.items():
            zf.writestr(name, data)

    print(f"Template saved: {TEMPLATE}")


if __name__ == "__main__":
    main()
