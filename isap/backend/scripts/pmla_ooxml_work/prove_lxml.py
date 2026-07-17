"""Prove lxml preserves namespace prefixes on round-trip (unlike docxtpl/ET)."""
from __future__ import annotations

import zipfile
from pathlib import Path

from lxml import etree

ROOT = Path(r"D:/Project ISAP/isap/isap")
TEMPLATE = ROOT / "files" / "pmla_v2_template.docx"

with zipfile.ZipFile(TEMPLATE) as z:
    data = z.read("word/document.xml")

root = etree.fromstring(data)
out = etree.tostring(root, xml_declaration=True, encoding="UTF-8")

text = out.decode("utf-8", "replace")
print("lxml starts with w:document:", text.startswith("<w:document"))
print("lxml contains r:embed:", "r:embed" in text)
print("lxml contains ns0:document:", "ns0:document" in text)
print("lxml preserves mc:Ignorable w14 wp14:", 'mc:Ignorable="w14 wp14"' in text)
print("first 200 bytes:")
print(text[:200])
