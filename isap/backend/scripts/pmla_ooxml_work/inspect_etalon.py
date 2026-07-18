"""Compare etalon vs template vs broken re: Jinja loops and equipment table."""
from __future__ import annotations

import re
import zipfile
from pathlib import Path

ROOT = Path(r"D:/Project ISAP/isap/isap")
ETALON = ROOT / "files" / "pmla_v2_template_etalon.docx"
TEMPLATE = ROOT / "files" / "pmla_v2_template.docx"
BROKEN = ROOT / "backend" / "pmla_v2_pilot_rendered.docx"


def info(path: Path, label: str):
    print("=" * 60)
    print(label, path.name)
    print("=" * 60)
    with zipfile.ZipFile(path) as z:
        doc = z.read("word/document.xml").decode("utf-8", "replace")
    print("has {%tr or {% :", bool(re.search(r"{%", doc)))
    print("has {{ :", bool(re.search(r"{{", doc)))
    print("count {% :", len(re.findall(r"{%", doc)))
    # equipment-related table: look for 'eq.' leftovers or rendered equipment
    print("contains 'eq.' leftover:", "eq." in doc)
    # how many table rows (w:tr) total
    print("w:tr count:", doc.count("<w:tr"))
    # sample: show any remaining Jinja-looking fragments
    frag = re.findall(r"{[{%].*?[}%]}", doc)
    print("Jinja-ish fragments:", len(frag))
    for f in frag[:5]:
        print("   ", repr(f[:80]))


for p, l in ((ETALON, "ETALON"), (TEMPLATE, "TEMPLATE"), (BROKEN, "BROKEN")):
    info(p, l)
