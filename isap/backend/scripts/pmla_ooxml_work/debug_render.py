"""Debug the REAL renderer.render() output on the fixture."""
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

out = renderer.render(ctx)  # real pipeline
print("rendered bytes:", len(out))

with zipfile.ZipFile(io.BytesIO(out)) as z:
    doc = z.read("word/document.xml").decode("utf-8", "replace")

print("ns0: present (BUG if True):", "ns0:" in doc)
print("r:embed present (good):", "r:embed" in doc)
print("leftover '{{':", doc.count("{{"), "; '}}':", doc.count("}}"), "; '{%':", doc.count("{%"))
print("ГРПШ-1 present:", "ГРПШ-1" in doc)
print("Начальник ПАСФ present:", "Начальник ПАСФ" in doc)
print("organization_full_name present:", ctx["organization_full_name"] in doc)
i = doc.find("{{")
if i >= 0:
    print("sample leftover:", repr(doc[i-40:i+40]))
