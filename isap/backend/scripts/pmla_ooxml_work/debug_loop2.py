"""Debug loop expansion in isolation."""
from __future__ import annotations

import io
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(r"D:/Project ISAP/isap/isap/backend").resolve()))

from lxml import etree
from src.application.services.pmla_v2_context_mapper import map_to_v2_context
from src.application.services.pmla_ooxml_flat_renderer import PmlaOoxmlFlatRenderer, W

ROOT = Path(r"D:/Project ISAP/isap/isap")
TEMPLATE = ROOT / "files" / "pmla_v2_template.docx"
FIXTURE = ROOT / "backend" / "tests" / "fixtures" / "pmla_v2_pilot_case.json"

fx = json.loads(FIXTURE.read_text(encoding="utf-8"))
ctx = map_to_v2_context(fx)
renderer = PmlaOoxmlFlatRenderer(TEMPLATE)
flat, loops = renderer._split_context(ctx)
renderer._loop_lists = loops
print("equipment_list:", type(loops.get("equipment_list")).__name__,
      len(loops.get("equipment_list", [])), "items")
print("first item keys:", list(loops["equipment_list"][0].keys()) if loops.get("equipment_list") else None)

with zipfile.ZipFile(TEMPLATE) as z:
    data = z.read("word/document.xml")
root = etree.fromstring(data)
renderer._expand_table_row_loops(root)
out = etree.tostring(root).decode("utf-8", "replace")
print("after loop: '{{ eq.':", "{{ eq." in out, "; '{{ loop.index':", "{{ loop.index" in out)
print("ГРПШ-1 present:", "ГРПШ-1" in out)
print("count ГРПШ-1:", out.count("ГРПШ-1"))
