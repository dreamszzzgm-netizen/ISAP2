"""
Stage 1: Confirm root cause.

Compare pmla_v2_template.docx (clean) vs pmla_v2_pilot_rendered.docx
(broken docxtpl output). Count drawing objects, relationships, external
links, and graphics by LOCAL tag name (namespace-agnostic via lxml).
"""
from __future__ import annotations

import sys
import zipfile
from collections import Counter
from pathlib import Path

from lxml import etree

ROOT = Path(r"D:/Project ISAP/isap/isap")
TEMPLATE = ROOT / "files" / "pmla_v2_template.docx"
BROKEN = ROOT / "backend" / "pmla_v2_pilot_rendered.docx"

# Local tag names we care about
TAGS = [
    "drawing", "inline", "anchor", "AlternateContent",
    "pict", "object", "txbx", "imagedata",
]

R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

TEXT_PARTS = (
    "word/document.xml",
    "word/header1.xml", "word/header2.xml", "word/header3.xml",
    "word/footer1.xml", "word/footer2.xml", "word/footer3.xml",
    "word/footnotes.xml", "word/endnotes.xml",
)


def local_counts(xml_bytes: bytes) -> Counter:
    c = Counter()
    try:
        root = etree.fromstring(xml_bytes)
    except etree.XMLSyntaxError as e:
        c["__PARSE_ERROR__"] += 1
        return c
    for el in root.iter():
        tag = el.tag
        if not isinstance(tag, str):
            continue
        local = tag.split("}")[-1]
        if local in TAGS:
            c[local] += 1
    return c


def analyze(path: Path) -> dict:
    info: dict = {"path": str(path), "exists": path.exists()}
    if not path.exists():
        return info
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        info["parts"] = len(names)
        info["media"] = sorted(n for n in names if n.startswith("word/media/"))
        info["embeddings"] = sorted(n for n in names if n.startswith("word/embeddings/"))
        # relationships
        rels = {}
        for n in names:
            if n.endswith(".rels"):
                try:
                    rroot = etree.fromstring(z.read(n))
                except etree.XMLSyntaxError as e:
                    rels[n] = f"PARSE_ERROR {e}"
                    continue
                lst = []
                for rel in rroot.findall(".//{%s}Relationship" % R_NS):
                    lst.append({
                        "Id": rel.get("Id"),
                        "Type": rel.get("Type"),
                        "Target": rel.get("Target"),
                        "TargetMode": rel.get("TargetMode"),
                    })
                rels[n] = lst
        info["rels"] = rels
        # counts + r:embed / r:id across text parts
        counts = Counter()
        r_ids = set()
        external = []
        fields = []
        for n in names:
            if n in TEXT_PARTS or (n.endswith(".xml") and (
                n.startswith("word/header") or n.startswith("word/footer")
            )):
                data = z.read(n)
                counts.update(local_counts(data))
                text = data.decode("utf-8", "replace")
                for m in ("r:embed", "r:id", "r:link", "r:pict", "r:cs"):
                    for v in __import__("re").findall(r'%s="([^"]+)"' % m, text):
                        r_ids.add(v)
                if "word/_rels/document.xml.rels" in rels:
                    for rel in rels["word/_rels/document.xml.rels"]:
                        if isinstance(rel, dict) and rel.get("TargetMode") == "External":
                            external.append((n, rel["Id"], rel["Target"]))
                for m in __import__("re").findall(r'w:instrText[^>]*>([^<]*)<', text):
                    if __import__("re").search(r'\b(LINK|INCLUDEPICTURE|INCLUDETEXT|DDEAUTO)\b', m, __import__("re").I):
                        fields.append((n, m.strip()))
        info["counts"] = dict(counts)
        info["r_ids"] = sorted(r_ids)
        info["external"] = external
        info["external_fields"] = fields
    return info


def main() -> int:
    tpl = analyze(TEMPLATE)
    brk = analyze(BROKEN)
    for label, info in (("TEMPLATE", tpl), ("BROKEN(docxtpl)", brk)):
        print("=" * 64)
        print(label, info.get("path"))
        print("=" * 64)
        if not info.get("exists"):
            print("  MISSING"); continue
        print("parts:", info["parts"])
        print("media files:", len(info["media"]), info["media"][:20])
        print("embeddings:", info["embeddings"])
        print("counts:", info["counts"])
        print("r_ids:", info["r_ids"])
        dr = info["rels"].get("word/_rels/document.xml.rels", [])
        print("document.xml.rels count:", len(dr) if isinstance(dr, list) else dr)
        print("external rels:", len(info["external"]))
        for e in info["external"][:30]:
            print("   EXTERNAL:", e)
        print("external field instructions:", len(info["external_fields"]))
        for f in info["external_fields"][:30]:
            print("   FIELD:", f)
    print("\n" + "=" * 64)
    print("DIFF: what docxtpl lost")
    print("=" * 64)
    tc, bc = tpl.get("counts", {}), brk.get("counts", {})
    for t in TAGS + list(set(list(tc) + list(bc))):
        tv, bv = tc.get(t, 0), bc.get(t, 0)
        if tv or bv:
            d = bv - tv
            print(f"  {t:16s}: template={tv:3d} broken={bv:3d} delta={d:+d}")
    tm, bm = len(tpl.get("media", [])), len(brk.get("media", []))
    print(f"  {'media':16s}: template={tm} broken={bm} delta={bm-tm:+d}")
    tr, br = len(tpl.get("r_ids", [])), len(brk.get("r_ids", []))
    print(f"  {'r_ids':16s}: template={tr} broken={br} delta={br-tr:+d}")
    tdr = tpl["rels"].get("word/_rels/document.xml.rels", [])
    bdr = brk["rels"].get("word/_rels/document.xml.rels", [])
    tdc = len(tdr) if isinstance(tdr, list) else 0
    bdc = len(bdr) if isinstance(bdr, list) else 0
    print(f"  {'doc.rels':16s}: template={tdc} broken={bdc} delta={bdc-tdc:+d}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
