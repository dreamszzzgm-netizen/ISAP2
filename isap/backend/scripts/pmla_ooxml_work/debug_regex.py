"""Debug: does PLACEHOLDER_RE match the split token in a combined stream?"""
from __future__ import annotations

import re
import zipfile
from pathlib import Path

ROOT = Path(r"D:/Project ISAP/isap/isap")
TEMPLATE = ROOT / "files" / "pmla_v2_template.docx"

# Replicate the renderer's regex + gather logic on a tiny XML snippet with a
# split placeholder.
SAMPLE = (
    b'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
    b'<w:body><w:p><w:r><w:t xml:space="preserve">{{ </w:t></w:r>'
    b'<w:r><w:t>contractor_director_position</w:t></w:r>'
    b'<w:r><w:t> }}</w:t></w:r></w:p></w:body></w:document>'
)

from lxml import etree
W = lambda t: f"{{http://schemas.openxmlformats.org/wordprocessingml/2006/main}}{t}"
root = etree.fromstring(SAMPLE)
combined = "".join((e.text or "") for e in root.iter(W("t")))
print("combined:", repr(combined))

PLACEHOLDER_RE = re.compile(r"\{\{\s*([A-Za-z_][\w.]*)\s*\}\}")
print("regex matches:", PLACEHOLDER_RE.findall(combined))
replaced = PLACEHOLDER_RE.sub(lambda mo: "<VAL:%s>" % mo.group(1), combined)
print("replaced:", repr(replaced))
