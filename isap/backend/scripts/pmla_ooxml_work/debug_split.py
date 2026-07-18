"""Debug: how is {{ contractor_director_position }} split across runs?"""
from __future__ import annotations

import re
import zipfile
from pathlib import Path

ROOT = Path(r"D:/Project ISAP/isap/isap")
TEMPLATE = ROOT / "files" / "pmla_v2_template.docx"

with zipfile.ZipFile(TEMPLATE) as z:
    doc = z.read("word/document.xml").decode("utf-8", "replace")

# Find the region around contractor_director_position
idx = doc.find("contractor_director_position")
print("idx:", idx)
seg = doc[idx - 250: idx + 60]
print(seg)
# show w:t texts with their full content split by tag
texts = re.findall(r"<w:t[^>]*>(.*?)</w:t>", seg, re.S)
print("\nw:t fragments in window:")
for t in texts:
    print("  ", repr(t))
