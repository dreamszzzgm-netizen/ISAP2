"""Inspect docxtpl table-row loop content in the v2 template."""
from __future__ import annotations

import re
import zipfile
from pathlib import Path

ROOT = Path(r"D:/Project ISAP/isap/isap")
TEMPLATE = ROOT / "files" / "pmla_v2_template.docx"

with zipfile.ZipFile(TEMPLATE) as z:
    data = z.read("word/document.xml").decode("utf-8", "replace")

print("{%tr occurrences:", len(re.findall(r"{%tr", data)))
print("{% occurrences (incl split):", len(re.findall(r"{%", data)))
print("%} occurrences:", len(re.findall(r"%\}", data)))

for m in re.finditer(r"{%tr[^%]*%\}", data):
    s = m.start()
    snippet = data[max(0, s - 100): s + 120]
    print("---")
    print(snippet.replace("\n", " "))
