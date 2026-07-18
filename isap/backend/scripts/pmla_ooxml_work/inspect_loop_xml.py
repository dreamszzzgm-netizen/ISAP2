"""Dump the full XML of the tr-loop control row and the data row."""
from __future__ import annotations

import re
import zipfile
from pathlib import Path

ROOT = Path(r"D:/Project ISAP/isap/isap")
TEMPLATE = ROOT / "files" / "pmla_v2_template.docx"

with zipfile.ZipFile(TEMPLATE) as z:
    data = z.read("word/document.xml").decode("utf-8", "replace")

for_open = data.find("{%")            # start of {%tr for ... %}
end_close = data.find("{%tr endfor %}")
end_close = data.find("</w:tr>", end_close) + len("</w:tr>")

# The endfor {%tr endfor%} — is it inside its own w:tr or the data row?
endfor_tok = data.find("{%tr endfor %}")
# enclosing w:tr for endfor
ef_tr_start = data.rfind("<w:tr", 0, endfor_tok)
ef_tr_close = data.find("</w:tr>", endfor_tok) + len("</w:tr>")
print("ENDFOR token inside its own <w:tr>?:", ef_tr_start < endfor_tok < ef_tr_close)
print("ENDFOR row w:t texts:")
ef_texts = re.findall(r"<w:t[^>]*>(.*?)</w:t>", data[ef_tr_start:ef_tr_close], re.S)
print("  ", ef_texts)

# Control row = the w:tr enclosing the '{%tr for' token
ctrl_start = data.rfind("<w:tr", 0, for_open)
ctrl_close = data.find("</w:tr>", for_open) + len("</w:tr>")
print("\nCONTROL row spans:", ctrl_start, ctrl_close)
ctrl = data[ctrl_start:ctrl_close]
print("  control row w:t texts:", re.findall(r"<w:t[^>]*>(.*?)</w:t>", ctrl, re.S))
# Is there a w:tc with {%tr for%} and another w:tc with {{ eq. ? or same?
print("  control row contains '{{ eq.':", "{{ eq." in ctrl)

# Data row = next w:tr after control row close that contains '{{ eq.'
data_region = data[ctrl_close:]
next_tr = data_region.find("<w:tr")
# find first w:tr containing eq.
idx = 0
while True:
    tr_s = data_region.find("<w:tr", idx)
    if tr_s < 0:
        break
    tr_e = data_region.find("</w:tr>", tr_s) + len("</w:tr>")
    seg = data_region[tr_s:tr_e]
    if "{{ eq." in seg:
        print("\nDATA row found @ region offset", tr_s)
        print("  data row w:t texts:", re.findall(r"<w:t[^>]*>(.*?)</w:t>", seg, re.S))
        break
    idx = tr_e
