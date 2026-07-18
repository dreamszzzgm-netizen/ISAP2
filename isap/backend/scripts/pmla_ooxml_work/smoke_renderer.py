"""Smoke test the flat renderer against the fixture context."""
from __future__ import annotations

import io
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(r"D:/Project ISAP/isap/isap/backend").resolve()))

import logging
from lxml import etree
logging.basicConfig(level=logging.DEBUG)
from src.application.services.pmla_v2_context_mapper import map_to_v2_context
from src.application.services.pmla_ooxml_flat_renderer import PmlaOoxmlFlatRenderer

ROOT = Path(r"D:/Project ISAP/isap/isap")
TEMPLATE = ROOT / "files" / "pmla_v2_template.docx"
FIXTURE = ROOT / "backend" / "tests" / "fixtures" / "pmla_v2_pilot_case.json"
OUT = ROOT / "backend" / "pmla_v2_pilot_rendered_ooxml.docx"

fx = json.loads(FIXTURE.read_text(encoding="utf-8"))
ctx = map_to_v2_context(fx)

renderer = PmlaOoxmlFlatRenderer(TEMPLATE)
out = renderer.render(ctx)
OUT.write_bytes(out)
print("WROTE", OUT, len(out), "bytes")

with zipfile.ZipFile(OUT) as z:
    bad = z.testzip()
    print("testzip (None=OK):", bad)
    doc = z.read("word/document.xml").decode("utf-8", "replace")

print("ns0: present (BUG if True):", "ns0:" in doc)
print("r:embed present (good):", "r:embed" in doc)
print("leftover '{{':", doc.count("{{"), "; '}}':", doc.count("}}"), "; '{%':", doc.count("{%"))
print("equipment rows (ГРПШ-1):", "ГРПШ-1" in doc)
print("org present:", ctx["organization_full_name"] in doc)
print("development_year present:", ctx["development_year"] in doc)
print("insurance_amount present:", ctx["insurance_amount"] in doc)
print("contractor_director_position (Начальник ПАСФ):", "Начальник ПАСФ" in doc)
