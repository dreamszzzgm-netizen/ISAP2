"""List all literal {{...}} placeholders present in the v2 template text parts."""
from __future__ import annotations

import re
import zipfile
from pathlib import Path

ROOT = Path(r"D:/Project ISAP/isap/isap")
TEMPLATE = ROOT / "files" / "pmla_v2_template.docx"

TEXT_PARTS = [
    "word/document.xml",
    "word/header1.xml", "word/header2.xml", "word/header3.xml",
    "word/footer1.xml", "word/footer2.xml", "word/footer3.xml",
    "word/footnotes.xml", "word/endnotes.xml",
]

PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")
SPLIT_RE = re.compile(r"\{\{|\}\}")


def main() -> int:
    with zipfile.ZipFile(TEMPLATE) as z:
        names = set(z.namelist())
        all_ph = {}
        for part in TEXT_PARTS:
            if part not in names:
                continue
            text = z.read(part).decode("utf-8", "replace")
            # only count placeholders that appear fully literal (not split across runs)
            for m in PLACEHOLDER_RE.findall(text):
                all_ph.setdefault(m, []).append(part)
            # also count dangling {{ or }} indicating split placeholders
            opens = len(re.findall(r"\{\{", text))
            closes = len(re.findall(r"\}\}", text))
            if opens != closes:
                print("  [SPLIT?] " + part + ": open=" + str(opens) + " close=" + str(closes))
        print("Literal complete placeholders found in template:")
        for k in sorted(all_ph):
            print(f"  {k:40s} -> {sorted(set(all_ph[k]))}")
        print(f"\nTotal distinct literal placeholders: {len(all_ph)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
