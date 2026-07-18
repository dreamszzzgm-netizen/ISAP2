"""Check sectPr baseline in the v2 template — count sections and orientations."""
from docx import Document
import re

TEMPLATE = r"D:\Project ISAP\isap\isap\files\pmla_v2_template.docx"

doc = Document(TEMPLATE)

# 1. Count sections via python-docx
print(f"Document sections: {len(doc.sections)}")
for i, sec in enumerate(doc.sections):
    orient = "landscape" if sec.orientation == 1 else "portrait"
    w = sec.page_width
    h = sec.page_height
    print(f"  Section {i}: {orient} ({w}x{h} EMU, {w/914400:.1f}x{h/914400:.1f} inches)")

# 2. Check XML directly for sectPr in document.xml
import zipfile, os
with zipfile.ZipFile(TEMPLATE, 'r') as z:
    data = z.read('word/document.xml').decode('utf-8')

# Find all sectPr elements
sect_pattern = re.compile(r'<w:sectPr[^>]*>.*?</w:sectPr>', re.DOTALL)
sects = sect_pattern.findall(data)
print(f"\nXML sectPr count: {len(sects)}")
for i, s in enumerate(sects):
    orient = "landscape" if 'w:orient="landscape"' in s else "portrait"
    pgSz = re.search(r'<w:pgSz[^/]*', s)
    pgSz_attrs = pgSz.group(0) if pgSz else ""
    w_match = re.search(r'w:w="(\d+)"', pgSz_attrs)
    h_match = re.search(r'w:h="(\d+)"', pgSz_attrs)
    w = int(w_match.group(1)) if w_match else 0
    h = int(h_match.group(1)) if h_match else 0
    print(f"  sectPr {i}: {orient} w={w} h={h} ({w/20:.0f}x{h/20:.0f} EMU→{w/914400:.1f}x{h/914400:.1f} in)")

# 3. Check for sectPr inside table rows (risk of accidental removal)
table_sect_count = 0
for ti, table in enumerate(doc.tables):
    for ri, row in enumerate(table.rows):
        xml = row._tr.xml
        if 'sectPr' in xml:
            table_sect_count += 1
            print(f"  WARNING: sectPr in Table {ti}, Row {ri}")

print(f"\nsectPr inside table rows: {table_sect_count}")

# 4. Save baseline for comparison
baseline = {
    "total_sections": len(doc.sections),
    "xml_sect_count": len(sects),
    "orientations": [],
    "table_sect_count": table_sect_count,
}
for i, sec in enumerate(doc.sections):
    baseline["orientations"].append("landscape" if sec.orientation == 1 else "portrait")

import json
baseline_path = r"D:\Project ISAP\isap\isap\backend\scripts\sectpr_baseline.json"
with open(baseline_path, 'w') as f:
    json.dump(baseline, f, indent=2)
print(f"\nBaseline saved to: {baseline_path}")
print(f"Baseline: {json.dumps(baseline)}")
