"""Test _fill_loop_row on a minimal split-token row."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(r"D:/Project ISAP/isap/isap/backend").resolve()))

from lxml import etree
from src.application.services.pmla_ooxml_flat_renderer import PmlaOoxmlFlatRenderer, W

SAMPLE = (
    b'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
    b'<w:body><w:p>'
    b'<w:r><w:t xml:space="preserve">{{ </w:t></w:r>'
    b'<w:r><w:t>eq.device_name</w:t></w:r>'
    b'<w:r><w:t> }}</w:t></w:r>'
    b'</w:p></w:body></w:document>'
)
row = etree.fromstring(SAMPLE)
item = {"location": "Площадка", "device_name": "ГРПШ-1", "hazard_characteristic": "x"}
PmlaOoxmlFlatRenderer._fill_loop_row(row, "eq", item, 1)
out = "".join(e.text for e in row.iter(W("t")) if e.text)
print("filled:", repr(out))
print("ГРПШ-1 present:", "ГРПШ-1" in out)
