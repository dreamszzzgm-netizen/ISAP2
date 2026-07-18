#!/usr/bin/env python3
"""Edit pmla_v2_template.docx: add 6 table-row loops, remove hardcoded data."""
from __future__ import annotations

import copy
import io
import zipfile
from lxml import etree

DOC_PATH = "files/pmla_v2_template.docx"
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = lambda tag: f"{{{W_NS}}}{tag}"


def row_text(tr):
    return "".join(e.text or "" for e in tr.iter(W("t")))


def make_control_row(template_row: etree.Element, marker: str) -> etree.Element:
    """Clone a row, clear text, set the loop-control marker in first cell."""
    ctrl = copy.deepcopy(template_row)
    for t in ctrl.iter(W("t")):
        t.text = ""
    first_t = ctrl.find(".//" + W("t"))
    if first_t is not None:
        first_t.text = marker
        first_t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    return ctrl


def make_data_row(template_row: etree.Element, token_map: list[str]) -> etree.Element:
    """Clone a row and set the i-th cell text to the i-th token."""
    dr = copy.deepcopy(template_row)
    cells = dr.findall(".//" + W("tc"))
    for i, tok in enumerate(token_map):
        if i < len(cells):
            t = cells[i].find(".//" + W("t"))
            if t is not None:
                t.text = tok
                t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    return dr


def replace_data_rows(table_idx, header_rows, loop_marker, tokens, saved_doc):
    """Replace hardcoded data rows in a table with control+data+endfor."""
    root = etree.fromstring(saved_doc)
    tables = root.findall(".//" + W("tbl"))
    tbl = tables[table_idx]
    rows = tbl.findall(W("tr"))

    header = rows[:header_rows]
    data_rows = rows[header_rows:]

    if not data_rows:
        return saved_doc

    parent = rows[0].getparent()
    # Find the position of the first row
    all_children = list(parent)
    first_row_idx = all_children.index(rows[0])

    # Remove old data rows
    for tr in data_rows:
        parent.remove(tr)

    # Build new rows using the FIRST old data row as cell-style template
    style_template = data_rows[0]

    # Control row
    control = make_control_row(style_template, loop_marker)

    # Data row
    data = make_data_row(style_template, tokens)

    # Endfor row
    endfor = make_control_row(style_template, "{%tr endfor %}")

    # Insert after the last header row
    insert_pos = first_row_idx + header_rows
    parent.insert(insert_pos, control)
    parent.insert(insert_pos + 1, data)
    parent.insert(insert_pos + 2, endfor)

    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def main():
    # Load the template
    with zipfile.ZipFile(DOC_PATH) as z:
        original_parts = {name: z.read(name) for name in z.namelist()}

    doc_xml = original_parts["word/document.xml"]

    # ---- Table 6 (idx=6): substance_params ----
    # Header: 1 row. Cols: Параметр | Значение
    tokens_6 = ["{{ sp.parameter }}", "{{ sp.value }}"]
    doc_xml = replace_data_rows(6, 1, "{%tr for sp in substance_params %}", tokens_6, doc_xml)
    print("✓ Table 6: substance_params")

    # ---- Table 7 (idx=7): equipment_scenario_links ----
    # Header: 1 row. Cols: № п/п | Наименование элемента оборудования | Возможные сценарии аварий (номера) | Краткое описание сценария для данного элемента | Поражающие факторы
    tokens_7 = [
        "{{ loop.index }}",
        "{{ link.equipment_name }}",
        "{{ link.scenario_codes }}",
        "{{ link.description }}",
        "{{ link.damaging_factors }}",
    ]
    doc_xml = replace_data_rows(7, 1, "{%tr for link in equipment_scenario_links %}", tokens_7, doc_xml)
    print("✓ Table 7: equipment_scenario_links")

    # ---- Table 9 (idx=9): accident_scenarios ----
    # Header: 1 row. Cols: № сценария | Наименование сценария | Источник (место) возникновения | Предпосылки (причины) | Опознавательные признаки | Поражающие факторы
    tokens_9 = [
        "{{ sc.code }}",
        "{{ sc.name }}",
        "{{ sc.source }}",
        "{{ sc.preconditions }}",
        "{{ sc.signs }}",
        "{{ sc.damaging_factors }}",
    ]
    doc_xml = replace_data_rows(9, 1, "{%tr for sc in accident_scenarios %}", tokens_9, doc_xml)
    print("✓ Table 9: accident_scenarios")

    # ---- Table 13 (idx=13): material_reserve ----
    # Header: 1 row. Cols: № п/п | Наименование | Количество | Место расположения
    # We need TWO loops: one for actual, one for recommended
    # The template has fixed group headers: "Средства индивидуальной защиты (СИЗ)" and "Инструмент и приспособления"
    # We'll keep the structure: header row, group header (СИЗ), ACTUAL loop, group header (Инструмент), RECOMMENDED loop
    
    # Actually the requirement says: keep 2 fixed group headers, under each a separate {%tr for %}
    # So I need:
    # Row 0: header (№ п/п | Наименование | Количество | Место расположения)
    # Row 1: group header merged "Фактические силы и средства"
    # Row 2-?: data for actual loop
    # Row ?+1: group header merged "Рекомендуемые средства"  
    # Row ?+2-?: data for recommended loop
    
    # But the current table structure uses single-cell merged rows for group headers.
    # Let me check the current structure
    
    root = etree.fromstring(doc_xml)
    tables = root.findall(".//" + W("tbl"))
    tbl13 = tables[13]
    rows13 = tbl13.findall(W("tr"))
    
    print(f"\nT13 before: {len(rows13)} rows")
    for i, r in enumerate(rows13[:4]):
        cols = len(r.findall(W("tc")))
        print(f"  Row {i}: {cols} cols | {row_text(r)[:80]}")
    
    # Current T13 structure:
    # Row 0: header (4 cols: № п/п | Наименование | Количество | Место расположения)
    # Row 1: 1 col merged "Средства индивидуальной защиты (СИЗ)"  
    # Rows 2-6: data (5 items)
    # Row 7: 1 col merged "Инструмент и приспособления"
    # Rows 8-16: data (9 items)
    # Row 17: 1 col merged "Оборудование и материалы"
    # Rows 18-21: data (4 items)
    
    # Plan for D6:
    # Row 0: header (keep)
    # Row 1: fixed group header "Фактические силы и средства" (1 cell merged)
    # Row 2-4: {%tr for res in material_reserve_actual %} / {{ loop.index }}{{ res.name }}{{ res.quantity }}{{ res.location }} / {%tr endfor %}
    # Row 5: fixed group header "Рекомендуемые средства" (1 cell merged)
    # Row 6-8: {%tr for res in material_reserve_recommended %} / {{ loop.index }}{{ res.name }}{{ res.quantity }}{{ res.location }} / {%tr endfor %}
    
    # Keep header (row 0)
    # Keep group header rows (rows 1, 7, 17) - but modify their text
    # Replace data rows with loops
    
    # Actually, the requirement says: "оставь два фиксированных групповых заголовка"
    # So we need just 2 group headers: Фактические и Рекомендуемые
    
    # Let me rebuild: 
    # Row 0: header
    # Row 1: group "Фактические силы и средства" (merged cell)
    # Row 2: {%tr for res in material_reserve_actual %}
    # Row 3: {{ loop.index }} | {{ res.name }} | {{ res.quantity }} | {{ res.location }}
    # Row 4: {%tr endfor %}
    # Row 5: group "Рекомендуемые средства" (merged cell)
    # Row 6: {%tr for res in material_reserve_recommended %}
    # Row 7: {{ loop.index }} | {{ res.name }} | {{ res.quantity }} | {{ res.location }}
    # Row 8: {%tr endfor %}
    
    # I need to get the merged cell XML structure from existing group header rows.
    # Let me look at row 1 (Средства индивидуальной защиты)
    
    # For now, I'll keep it simpler: just replace ALL data rows with the two loops
    # Keep header (row 0)
    # Keep group header merged row (row 1) - modify text
    # Remove rows 2-21
    # Insert actual loop (control + data + endfor)
    # Insert group header row (row 17 style - cloned)
    # Insert recommended loop (control + data + endfor)
    
    # Save this for later - skip T13 for now, handle it after the simpler ones
    print("  (T13 will be handled as a special case)")
    
    # ---- Table 18 (idx=18): countermeasures ----
    tokens_18 = [
        "{{ cm.scenario_label }}",
        "{{ cm.signs }}",
        "{{ cm.protection }}",
        "{{ cm.technical_means }}",
        "{{ cm.executors }}",
    ]
    doc_xml = replace_data_rows(18, 1, "{%tr for cm in countermeasures %}", tokens_18, doc_xml)
    print("✓ Table 18: countermeasures")

    # ---- Now handle Table 13 separately ----
    # Reload
    root2 = etree.fromstring(doc_xml)
    tables2 = root2.findall(".//" + W("tbl"))
    tbl13 = tables2[13]
    rows13b = tbl13.findall(W("tr"))
    
    print(f"\nT13 before rebuild: {len(rows13b)} rows")
    for i, r in enumerate(rows13b):
        cols = len(r.findall(W("tc")))
        txt = row_text(r)[:60]
        print(f"  Row {i}: {cols} cols | {txt}")
    
    # Find a 1-cell merged row to use as template for group headers
    merged_row = None
    for r in rows13b:
        if len(r.findall(W("tc"))) == 1:
            merged_row = copy.deepcopy(r)
            break
    
    # Find a 4-cell data row to use as template for data rows
    data_template = None
    for r in rows13b:
        if len(r.findall(W("tc"))) >= 4:
            # Check if it has gridSpan or is a normal 4-col row
            spans = r.findall(".//" + W("gridSpan"))
            if not spans:
                data_template = copy.deepcopy(r)
                break
    if data_template is None:
        # Fallback: any 4+ cell row
        for r in rows13b:
            if len(r.findall(W("tc"))) >= 4:
                data_template = copy.deepcopy(r)
                break
    
    # Build the new table13
    parent13 = rows13b[0].getparent()
    all_kids = list(parent13)
    first_idx = all_kids.index(rows13b[0])
    
    # Remove ALL old rows (we'll rebuild from scratch)
    for tr in rows13b:
        parent13.remove(tr)
    
    # Row 0: header (keep original)
    header_row = copy.deepcopy(rows13b[0])
    parent13.insert(first_idx, header_row)
    pos = first_idx + 1
    
    # Row 1: group header "Фактические силы и средства"
    if merged_row is not None:
        grp1 = copy.deepcopy(merged_row)
        for t in grp1.iter(W("t")):
            t.text = ""
        first_t = grp1.find(".//" + W("t"))
        if first_t is not None:
            first_t.text = "Фактические силы и средства"
            first_t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        parent13.insert(pos, grp1)
        pos += 1
    
    # Row 2-4: actual loop
    if data_template is not None:
        ctrl_act = make_control_row(data_template, "{%tr for res in material_reserve_actual %}")
        parent13.insert(pos, ctrl_act); pos += 1
        
        data_act = make_data_row(data_template, ["{{ loop.index }}", "{{ res.name }}", "{{ res.quantity }}", "{{ res.location }}"])
        parent13.insert(pos, data_act); pos += 1
        
        end_act = make_control_row(data_template, "{%tr endfor %}")
        parent13.insert(pos, end_act); pos += 1
    
    # Row 5: group header "Рекомендуемые средства"
    if merged_row is not None:
        grp2 = copy.deepcopy(merged_row)
        for t in grp2.iter(W("t")):
            t.text = ""
        first_t = grp2.find(".//" + W("t"))
        if first_t is not None:
            first_t.text = "Рекомендуемые средства"
            first_t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        parent13.insert(pos, grp2)
        pos += 1
    
    # Row 6-8: recommended loop
    if data_template is not None:
        ctrl_rec = make_control_row(data_template, "{%tr for res in material_reserve_recommended %}")
        parent13.insert(pos, ctrl_rec); pos += 1
        
        data_rec = make_data_row(data_template, ["{{ loop.index }}", "{{ res.name }}", "{{ res.quantity }}", "{{ res.location }}"])
        parent13.insert(pos, data_rec); pos += 1
        
        end_rec = make_control_row(data_template, "{%tr endfor %}")
        parent13.insert(pos, end_rec); pos += 1
    
    doc_xml = etree.tostring(root2, xml_declaration=True, encoding="UTF-8", standalone=True)
    print("✓ Table 13: material_reserve_actual + material_reserve_recommended")

    # ---- Write back ----
    output_buf = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(original_parts["word/document.xml"]), "r") as zref:
        # We need to rebuild the DOCX preserving all parts
        pass
    
    # Simpler: just replace document.xml in-memory
    original_parts["word/document.xml"] = doc_xml
    
    with zipfile.ZipFile(output_buf, "w", zipfile.ZIP_DEFLATED) as zout:
        for name, data in original_parts.items():
            zout.writestr(name, data)
    
    # Write to a new file
    out_path = "files/pmla_v2_template.docx"
    with open(out_path, "wb") as f:
        f.write(output_buf.getvalue())
    
    print(f"\n✓ Saved modified template to {out_path}")
    print(f"  Size: {len(output_buf.getvalue())} bytes")


if __name__ == "__main__":
    main()
