"""Test _rewrite_split_placeholders on the real two-adjacent case."""
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
    b'<w:r><w:t>contractor_director_position</w:t></w:r>'
    b'<w:r><w:t> }}</w:t></w:r>'
    b'<w:r><w:t xml:space="preserve">{{ </w:t></w:r>'
    b'<w:r><w:t>contractor_organization_name</w:t></w:r>'
    b'<w:r><w:t> }}</w:t></w:r>'
    b'<w:r><w:t> trailing</w:t></w:r>'
    b'</w:p></w:body></w:document>'
)
root = etree.fromstring(SAMPLE)
t_elems = [e for e in root.iter(W("t")) if e.text is not None]
safe = {"contractor_director_position": "Начальник ПАСФ",
        "contractor_organization_name": "ООО ГазСпас"}
PmlaOoxmlFlatRenderer._rewrite_split_placeholders(t_elems, safe)
out = "".join((e.text or "") for e in t_elems)
print("RESULT:", repr(out))
print("leftover {{:", out.count("{{"))
