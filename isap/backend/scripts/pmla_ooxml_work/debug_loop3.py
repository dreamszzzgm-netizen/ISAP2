"""Debug loop expansion with verbose tracing."""
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
    PmlaOoxmlFlatRenderer, W, TR_FOR_RE, TR_ENDFOR_RE,
)

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

W_tr = W("tr")
control_rows = []
for tr in root.iter(W_tr):
    if TR_FOR_RE.search(renderer._gather_text(etree.tostring(tr))):
        control_rows.append(tr)
print("control_rows found:", len(control_rows))

for ctrl in control_rows:
    parent = ctrl.getparent()
    m = TR_FOR_RE.search(renderer._gather_text(etree.tostring(ctrl)))
    var, list_key = m.group(1), m.group(2)
    items = renderer._loop_lists.get(list_key)
    print(f"  loop var={var} list={list_key} items={len(items) if items else 0}")
    ctrl_idx = parent.index(ctrl)
    print("  ctrl_idx:", ctrl_idx, "parent tag:", parent.tag.split('}')[-1])
    # Walk siblings
    data_row = endfor_row = None
    for i in range(ctrl_idx + 1, len(parent)):
        sib = parent[i]
        if sib.tag != W_tr:
            continue
        sib_text = renderer._gather_text(etree.tostring(sib))
        if ("{{ " + var + ".") in sib_text or "{{ loop.index }}" in sib_text:
            data_row = sib
            print("  data_row @ idx", i, "text snippet:", repr(sib_text[:60]))
            break
    if data_row is None:
        print("  !!! NO data_row found")
        continue
    for i in range(parent.index(data_row) + 1, len(parent)):
        sib = parent[i]
        if sib.tag != W_tr:
            continue
        if TR_ENDFOR_RE.search(renderer._gather_text(etree.tostring(sib))):
            endfor_row = sib
            print("  endfor_row @ idx", i)
            break
    if endfor_row is None:
        print("  !!! NO endfor_row found")
