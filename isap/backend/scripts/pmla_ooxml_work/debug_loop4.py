"""Trace _expand_table_row_loops fully."""
from __future__ import annotations

import io
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(r"D:/Project ISAP/isap/isap/backend").resolve()))

from lxml import etree
from src.application.services.pmla_v2_context_mapper import map_to_v2_context
from src.application.services.pmla_ooxml_flat_renderer import PmlaOoxmlFlatRenderer, W, LOOP_TOKEN_RE

ROOT = Path(r"D:/Project ISAP/isap/isap")
TEMPLATE = ROOT / "files" / "pmla_v2_template.docx"
FIXTURE = ROOT / "backend" / "tests" / "fixtures" / "pmla_v2_pilot_case.json"

fx = json.loads(FIXTURE.read_text(encoding="utf-8"))
ctx = map_to_v2_context(fx)
renderer = PmlaOoxmlFlatRenderer(TEMPLATE)
flat, loops = renderer._split_context(ctx)
renderer._loop_lists = loops

with zipfile.ZipFile(TEMPLATE) as z:
    data = z.read("word/document.xml")
root = etree.fromstring(data)
renderer._expand_table_row_loops(root)

# After expansion, find all w:t containing 'ГРПШ' or 'eq.'
all_text = [e.text for e in root.iter(W("t")) if e.text]
joined = "".join(all_text)
print("ГРПШ-1 present after expansion:", "ГРПШ-1" in joined)
print("count device_name values:", joined.count("ГРПШ"))
# Show unresolved loop tokens still present
import re
left = re.findall(r"\{\{[^}]*\}\}", joined)
print("leftover {{...}} tokens:", len(left))
print("sample:", left[:5])
