"""Inspect etalon equipment table: how many rows, any eq./loop leftovers."""
from __future__ import annotations

import re
import zipfile
from pathlib import Path

ROOT = Path(r"D:/Project ISAP/isap/isap")
ETALON = ROOT / "files" / "pmla_v2_template_etalon.docx"

with zipfile.ZipFile(ETALON) as z:
    names = z.namelist()
    doc_part = "word/document.xml" if "word/document.xml" in names else None
    doc = z.read(doc_part).decode("utf-8", "replace")

print("etalon w:tr count:", doc.count("<w:tr"))
print("etalon {{ count:", doc.count("{{"))
print("etalon {% count:", doc.count("{%"))
print("etalon 'eq.' leftover:", "eq." in doc)
# Look for equipment item values that appear in fixture: 'ГРПШ-1', 'Площадка ГРП'
for needle in ["ГРПШ-1", "Площадка ГРП", "Газорегуляторный", "2.1"]:
    print(f"  contains {needle!r}:", needle in doc)
# Show any leftover Jinja tokens
frag = re.findall(r"{[{%][^}%]*[}%]}", doc)
print("jinja-ish fragments:", len(frag))
for f in frag[:10]:
    print("   ", repr(f[:80]))
