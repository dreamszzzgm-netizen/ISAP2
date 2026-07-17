"""Deep inspection of relationship files and r:embed in document.xml."""
from __future__ import annotations

import zipfile
from pathlib import Path

ROOT = Path(r"D:/Project ISAP/isap/isap")
TEMPLATE = ROOT / "files" / "pmla_v2_template.docx"
BROKEN = ROOT / "backend" / "pmla_v2_pilot_rendered.docx"


def rel_files(path: Path):
    with zipfile.ZipFile(path) as z:
        return [n for n in z.namelist() if n.endswith(".rels")]


def dump(path: Path, label: str):
    print("=" * 64)
    print(label, path)
    print("=" * 64)
    with zipfile.ZipFile(path) as z:
        rels = [n for n in z.namelist() if n.endswith(".rels")]
        print("rels files:", rels)
        for rn in rels:
            data = z.read(rn).decode("utf-8", "replace")
            print(f"\n--- {rn} ---")
            print(data[:3000])
        # document.xml r:embed sample
        doc = z.read("word/document.xml").decode("utf-8", "replace")
        import re
        embeds = re.findall(r'r:embed="[^"]+"', doc)
        print("\ndocument.xml r:embed count:", len(embeds))
        print("sample r:embed:", embeds[:5])
        # show first 1500 chars of document.xml
        print("\n--- document.xml head ---")
        print(doc[:1500])


dump(TEMPLATE, "TEMPLATE")
dump(BROKEN, "BROKEN")
