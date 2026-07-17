"""Verify v2 template sectPr matches baseline."""
import json, re, zipfile
from docx import Document

with open(r"D:\Project ISAP\isap\isap\backend\scripts\sectpr_baseline.json") as f:
    baseline = json.load(f)

doc = Document(r"D:\Project ISAP\isap\isap\files\pmla_v2_template.docx")

current_orient = []
for sec in doc.sections:
    current_orient.append("landscape" if sec.orientation == 1 else "portrait")

with zipfile.ZipFile(r"D:\Project ISAP\isap\isap\files\pmla_v2_template.docx") as z:
    data = z.read("word/document.xml").decode("utf-8")
sects = re.findall(r"<w:sectPr[^>]*>.*?</w:sectPr>", data, re.DOTALL)

print(f"Baseline orientations: {baseline['orientations']}")
print(f"Current  orientations: {current_orient}")
print(f"Orientations match:    {baseline['orientations'] == current_orient}")
print(f"Section count: baseline={baseline['total_sections']}, current={len(doc.sections)}, match={baseline['total_sections'] == len(doc.sections)}")
print(f"XML sect count: baseline={baseline['xml_sect_count']}, current={len(sects)}, match={baseline['xml_sect_count'] == len(sects)}")

table_sect = 0
for table in doc.tables:
    for row in table.rows:
        if "sectPr" in row._tr.xml:
            table_sect += 1
print(f"Table sectPr: baseline={baseline['table_sect_count']}, current={table_sect}, match={baseline['table_sect_count'] == table_sect}")

ok = (baseline["orientations"] == current_orient and
       baseline["total_sections"] == len(doc.sections) and
       baseline["xml_sect_count"] == len(sects) and
       baseline["table_sect_count"] == table_sect)
print(f"\n{'PASS — sectPr baseline intact' if ok else 'FAIL — sectPr changed!'}")
