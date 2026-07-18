"""Precisely locate the w:tr rows that bracket the docxtpl tr-loop."""
from __future__ import annotations

import re
import zipfile
from pathlib import Path

ROOT = Path(r"D:/Project ISAP/isap/isap")
TEMPLATE = ROOT / "files" / "pmla_v2_template.docx"

with zipfile.ZipFile(TEMPLATE) as z:
    data = z.read("word/document.xml").decode("utf-8", "replace")

# Find byte offsets of each <w:tr ...> opening and its matching close.
# We'll locate the loop tokens and the tr boundaries near them.
for_tok = data.find("{%tr for")
end_tok = data.find("{%tr endfor %}")

print("for token @", for_tok, " endfor token @", end_tok)

# Find the nearest preceding '<w:tr' and following '</w:tr>' for the for token.
def enclosing_tr_open(s: int) -> int:
    return data.rfind("<w:tr", 0, s)

def enclosing_tr_close(s: int) -> int:
    return data.find("</w:tr>", s) + len("</w:tr>")

for_open = enclosing_tr_open(for_tok)
for_close = enclosing_tr_close(for_tok)
print("\nFOR control row spans:", for_open, "->", for_close)
print("  FOR row text:", repr(data[for_open:for_close][:200]))

end_open = enclosing_tr_open(end_tok)
end_close = enclosing_tr_close(end_tok)
print("\nENDFOR control row spans:", end_open, "->", end_close)
print("  ENDFOR row text:", repr(data[end_open:end_close][:200]))

# Is there a data row strictly between for_close and end_open?
between = data[for_close:end_open]
print("\nBETWEEN for-close and endfor-open (data region):")
print("  length:", len(between))
print("  contains {{ eq.:", "{{ eq." in between)
print("  w:tr count in between:", between.count("<w:tr"))
# Print the region with tags but truncated
print("\n  --- region (first 1600 chars, tags kept) ---")
print(between[:1600])
