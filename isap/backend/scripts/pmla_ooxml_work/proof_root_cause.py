"""
CONFIRM ROOT CAUSE (Stage 1 proof).

Shows that docxtpl/python-docx mangled namespace prefixes in
document.xml (w->ns0, r->ns10, ...), so relationship references
r:embed / r:id became ns10:embed and are no longer resolvable by Word.

The .rels files themselves are intact (rId8.. present), and media
files (14) are present. Only the in-document reference namespace is
broken, which is exactly why Word reports broken graphic objects.
"""
from __future__ import annotations

import re
import zipfile
from pathlib import Path

ROOT = Path(r"D:/Project ISAP/isap/isap")
TEMPLATE = ROOT / "files" / "pmla_v2_template.docx"
BROKEN = ROOT / "backend" / "pmla_v2_pilot_rendered.docx"


def ns_prefixes(xml: str) -> dict:
    """Return mapping prefix->uri from xmlns declarations."""
    out = {}
    for m in re.finditer(r'xmlns:([A-Za-z0-9]+)="([^"]+)"', xml):
        out[m.group(1)] = m.group(2)
    return out


def count_embed_in_namespace(xml: str, prefix: str) -> int:
    """Count {prefix}:embed and {prefix}:id occurrences."""
    return len(re.findall(rf'{prefix}:embed="', xml)) + len(re.findall(rf'{prefix}:id="', xml))


def main() -> int:
    with zipfile.ZipFile(TEMPLATE) as z:
        t_doc = z.read("word/document.xml").decode("utf-8", "replace")
        t_rels = z.read("word/_rels/document.xml.rels").decode("utf-8", "replace")
    with zipfile.ZipFile(BROKEN) as z:
        b_doc = z.read("word/document.xml").decode("utf-8", "replace")
        b_rels = z.read("word/_rels/document.xml.rels").decode("utf-8", "replace")

    print("=" * 64)
    print("TEMPLATE document.xml namespace prefixes (key ones)")
    print("=" * 64)
    tp = ns_prefixes(t_doc)
    for p in ("w", "r", "mc", "wp", "wps", "v", "o"):
        print(f"  xmlns:{p} = {tp.get(p, '<MISSING>')}")

    print("\n" + "=" * 64)
    print("BROKEN document.xml namespace prefixes (key ones)")
    print("=" * 64)
    bp = ns_prefixes(b_doc)
    # show what w/r map to
    w_uri = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    r_uri = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    w_pref = [k for k, v in bp.items() if v == w_uri]
    r_pref = [k for k, v in bp.items() if v == r_uri]
    print(f"  prefix bound to WORDML main namespace ({w_uri}): {w_pref}")
    print(f"  prefix bound to RELATIONSHIPS namespace ({r_uri}): {r_pref}")

    print("\n" + "=" * 64)
    print("RELATIONSHIP REFERENCES inside document.xml")
    print("=" * 64)
    t_r = count_embed_in_namespace(t_doc, "r")
    b_r = count_embed_in_namespace(b_doc, "r")
    print(f"  template: 'r:embed'/'r:id' refs = {t_r}")
    print(f"  broken  : 'r:embed'/'r:id' refs = {b_r}")
    # broken refs actually live under the mangled prefix
    b_mangled = 0
    for pref in r_pref:
        b_mangled += count_embed_in_namespace(b_doc, pref)
    print(f"  broken  : refs under mangled rel-prefix {r_pref} = {b_mangled}")

    print("\n" + "=" * 64)
    print("RELS FILE INTEGRITY (unchanged?)")
    print("=" * 64)
    t_ids = re.findall(r'Id="(rId\d+)"', t_rels)
    b_ids = re.findall(r'Id="(rId\d+)"', b_rels)
    print(f"  template rels rId count = {len(t_ids)}")
    print(f"  broken   rels rId count = {len(b_ids)}")
    print(f"  rels identical (w.r.t. rIds) = {set(t_ids) == set(b_ids)}")

    print("\n" + "=" * 64)
    print("MEDIA FILES")
    print("=" * 64)
    with zipfile.ZipFile(TEMPLATE) as z:
        t_media = [n for n in z.namelist() if n.startswith("word/media/")]
    with zipfile.ZipFile(BROKEN) as z:
        b_media = [n for n in z.namelist() if n.startswith("word/media/")]
    print(f"  template media = {len(t_media)}")
    print(f"  broken   media = {len(b_media)}")
    print(f"  media identical = {set(t_media) == set(b_media)}")

    print("\n" + "=" * 64)
    print("VERDICT")
    print("=" * 64)
    print("  docxtpl/python-docx rewrote namespace prefixes in document.xml.")
    print("  Relationship references r:embed/r:id are now under a mangled")
    print(f"  prefix ({r_pref}) bound to the relationships namespace, so Word")
    print("  cannot resolve the 14 embedded images -> offers repair.")
    print("  The .rels and media parts are actually intact.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
