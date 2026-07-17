"""Find ALL docxtpl table-row loops in the v2 template."""
from __future__ import annotations

import re
import zipfile
from pathlib import Path

ROOT = Path(r"D:/Project ISAP/isap/isap")
TEMPLATE = ROOT / "files" / "pmla_v2_template.docx"

with zipfile.ZipFile(TEMPLATE) as z:
    for part in ("word/document.xml", "word/header1.xml", "word/header2.xml",
                "word/footer1.xml", "word/footer2.xml"):
        if part not in z.namelist():
            continue
        data = z.read(part).decode("utf-8", "replace")
        # Reconstruct loop tokens across runs.
        text = "".join(re.findall(r"<w:t[^>]*>(.*?)</w:t>", data, re.S))
        for m in re.finditer(r"\{\%\s*tr\s+for\s+(\w+)\s+in\s+(\w+)\s*\%\}", text):
            print(f"{part}: for {m.group(1)} in {m.group(2)}")
