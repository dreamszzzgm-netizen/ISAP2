"""Find the exact data-row (with {{ eq.* }}) between the tr loop markers."""
from __future__ import annotations

import re
import zipfile
from pathlib import Path

ROOT = Path(r"D:/Project ISAP/isap/isap")
TEMPLATE = ROOT / "files" / "pmla_v2_template.docx"

with zipfile.ZipFile(TEMPLATE) as z:
    data = z.read("word/document.xml").decode("utf-8", "replace")

# The for-token is split: find '{%' then 'tr for' reassembled region.
for_open = data.find("{%")
end_open = data.find("{%tr endfor %}")
print("first '{%' @", for_open, "; endfor @", end_open)

# Count w:tr between for_open and end_open
region = data[for_open:end_open]
print("w:tr count in [for,endfor):", region.count("<w:tr"))

# Find positions of '{{ eq.' occurrences
eq_positions = [m.start() for m in re.finditer(r"\{\{\s*eq\.", region)]
print("'{{ eq.' occurrences in region:", len(eq_positions))
for p in eq_positions[:10]:
    # enclosing w:tr
    tr_start = region.rfind("<w:tr", 0, p)
    tr_end = region.find("</w:tr>", p) + len("</w:tr>")
    snippet = region[tr_start:tr_end]
    # is this the data row? show its w:t texts
    texts = re.findall(r"<w:t[^>]*>(.*?)</w:t>", snippet, re.S)
    print("  eq @", p, "texts:", texts[:8])
