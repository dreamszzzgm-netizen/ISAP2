"""Find and dump the full Jinja table-row loop region in the v2 template."""
from __future__ import annotations

import re
import zipfile
from pathlib import Path

ROOT = Path(r"D:/Project ISAP/isap/isap")
TEMPLATE = ROOT / "files" / "pmla_v2_template.docx"

with zipfile.ZipFile(TEMPLATE) as z:
    data = z.read("word/document.xml").decode("utf-8", "replace")

# Find the whole {% ... %} tokens (may be split). Reconstruct by scanning w:t text.
# Simpler: locate '{{' and '{%' token starts and matching closers across runs.
# We'll just print a generous window around the first '{%' and the 'endfor'.
for_start = data.find("{%")
end_start = data.find("{%tr endfor %}")
print("for_start:", for_start, " endfor_start:", end_start)

if for_start >= 0:
    print("\n=== region from loop open to endfor (stripped of tags) ===")
    region = data[for_start: end_start + len("{%tr endfor %}")]
    # extract only w:t text to read the loop body semantically
    texts = re.findall(r"<w:t[^>]*>(.*?)</w:t>", region, re.S)
    print("loop text fragments:")
    for t in texts:
        print("  ", repr(t))
    # show raw region (abbreviated) to see structure
    print("\n=== raw region (first 1500 chars) ===")
    print(region[:1500])
