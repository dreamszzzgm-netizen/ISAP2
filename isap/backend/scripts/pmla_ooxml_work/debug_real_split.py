"""Dump the run structure around the first '{{' in the template."""
from __future__ import annotations

import re
import zipfile
from pathlib import Path

ROOT = Path(r"D:/Project ISAP/isap/isap")
TEMPLATE = ROOT / "files" / "pmla_v2_template.docx"

with zipfile.ZipFile(TEMPLATE) as z:
    doc = z.read("word/document.xml").decode("utf-8", "replace")

# Find the split placeholder: 'contractor_director_position' sits in a run
# between '{{ ' and ' }}'.
name_idx = doc.find("contractor_director_position")
print("name idx:", name_idx)
first = name_idx
print("first placeholder idx:", first)
# Expand window to capture enclosing runs.
start = doc.rfind("<w:tc>", 0, first)
end = doc.find("</w:tc>", first) + len("</w:tc>")
seg = doc[max(0, start): end]
print("seg len:", len(seg))

# Split into runs by <w:r ...> ... </w:r>
for m in re.finditer(r"<w:r[^>]*>.*?</w:r>", seg, re.S):
    run = m.group(0)
    texts = re.findall(r"<w:t[^>]*>(.*?)</w:t>", run, re.S)
    print("RUN texts:", texts)
