"""Isolate _stream_rewrite behaviour."""
from __future__ import annotations

import io
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(r"D:/Project ISAP/isap/isap/backend").resolve()))

from lxml import etree
from src.application.services.pmla_v2_context_mapper import map_to_v2_context
from src.application.services.pmla_ooxml_flat_renderer import (
    PmlaOoxmlFlatRenderer, W, PLACEHOLDER_RE,
)

ROOT = Path(r"D:/Project ISAP/isap/isap")
TEMPLATE = ROOT / "files" / "pmla_v2_template.docx"
FIXTURE = ROOT / "backend" / "tests" / "fixtures" / "pmla_v2_pilot_case.json"

fx = json.loads(FIXTURE.read_text(encoding="utf-8"))
ctx = map_to_v2_context(fx)
renderer = PmlaOoxmlFlatRenderer(TEMPLATE)
flat, loops = renderer._split_context(ctx)
safe = renderer._prepare_context(flat)
renderer._loop_lists = loops

with zipfile.ZipFile(TEMPLATE) as z:
    data = z.read("word/document.xml")
root = etree.fromstring(data)
renderer._expand_table_row_loops(root)
renderer._replace_flat_placeholders(root, safe)

t_elems = [e for e in root.iter(W("t")) if e.text]
combined = "".join((e.text or "") for e in t_elems)
print("combined has '{{':", "{{" in combined)
i = combined.find("{{")
print("around first {{ (show raw bytes repr):")
print(repr(combined[i-5:i+50]))
# apply regex directly
replaced = PLACEHOLDER_RE.sub(lambda mo: renderer._resolve_flat(mo.group(1), safe), combined)
print("replaced has '{{':", "{{" in replaced)
j = replaced.find("{{")
if j >= 0:
    print("replaced around {{ :", repr(replaced[j-5:j+50]))
# which exact token fails?
import re
for m in PLACEHOLDER_RE.finditer(combined):
    tok = m.group(1)
    val = renderer._resolve_flat(tok, safe)
    if "{{" in val:
        print("UNRESOLVED token:", repr(tok), "->", repr(val))
