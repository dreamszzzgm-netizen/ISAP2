# -*- coding: utf-8 -*-
import json, sys
from docx import Document

DOCX_PATH = r"D:\GPT PMLA\Разработка\isap_skeleton\isap\ПМЛА ООО СПК ААА.docx"
OUTPUT_JSON = r"D:\GPT PMLA\Разработка\isap_skeleton\isap\docx_analysis.json"
OUTPUT_TXT = r"D:\GPT PMLA\Разработка\isap_skeleton\isap\docx_analysis.txt"

doc = Document(DOCX_PATH)

# 1. HEADINGS
headings = []
for i, p in enumerate(doc.paragraphs):
    sn = p.style.name if p.style else ""
    t = p.text.strip()
    if not t:
        continue
    sl = sn.lower()
    if sl.startswith("heading"):
        try:
            lv = int(sl.replace("heading", "").strip())
        except:
            lv = 1
        headings.append({"i": i, "lv": lv, "sty": sn, "txt": t[:300]})

print("=== HEADINGS ===")
for h in headings:
    ind = "  " * (h["lv"] - 1)
    print(f"{ind}[H{h['lv']}] {h['txt']}")

# 2. TABLES
tables = []
pat_map = {}
for ti, tbl in enumerate(doc.tables):
    cells = [[c.text.strip() for c in r.cells] for r in tbl.rows]
    rc, cc = len(tbl.rows), len(tbl.columns)
    hdr = cells[0] if cells else []
    content = cells[1:] if len(cells) > 1 else []

    # pattern detection
    hdrj = " ".join(h.lower() for h in hdr if h)
    pats = []
    kw = {
        "enum": ["наименов","название","номер","н/п","п/п","№"],
        "geo": ["адрес","местоположен","район","область"],
        "vol": ["объем","ёмкость","емкость","количеств","масс"],
        "coord": ["координат","широт","долгот"],
        "risk": ["опасн","риск","угроз","последстви"],
        "meas": ["мер","мероприяти","предупрежд","ликвид"],
        "scen": ["сценари","вариант","разлити","розлив","событи"],
        "zone": ["зоны","площад","территор"],
        "org": ["пункт","подразделен","структур"],
        "mat": ["материал","веществ","продукт","топлив"],
        "weather": ["услови","погод","ветер","температур"],
    }
    for p_name, ws in kw.items():
        if any(w in hdrj for w in ws):
            pats.append(p_name)
    if not pats:
        pats = ["kv"] if len(cells) > 2 and len(cells[0]) >= 2 and max((len(r[0]) for r in cells if r), default=0) < 30 else ["tabular"]
    pat = "+".join(pats)
    pat_map.setdefault(pat, []).append(ti)

    # caption
    cap = ""
    prev = tbl._tbl.getprevious()
    if prev is not None and hasattr(prev, "text") and prev.text:
        cap = prev.text.strip()[:200]

    # samples
    sv = {}
    if len(cells) > 1:
        for c in range(len(cells[0])):
            h = cells[0][c][:30] if c < len(cells[0]) else f"c{c}"
            sv[h] = [cells[r][c][:80] for r in range(1, min(len(cells), 6)) if c < len(cells[r]) and cells[r][c]]

    tables.append({
        "idx": ti, "rows": rc, "cols": cc,
        "headers": hdr, "caption": cap,
        "pattern": pat, "first3": content[:3], "samples": sv,
    })

print("\n=== TABLES ===")
for t in tables:
    print(f"T{t['idx']}: {t['rows']}x{t['cols']} pattern={t['pattern']}")
    print(f"  Headers: {t['headers']}")
    print(f"  Caption: {t['caption']}")
    for row in t["first3"]:
        print(f"    {row}")

print("\n=== DATA PATTERNS ===")
for p, ids in pat_map.items():
    print(f"  {p}: tables {ids}")

# 3. SECTIONS
sections = []
cur = None
for i, p in enumerate(doc.paragraphs):
    sn = p.style.name if p.style else ""
    t = p.text.strip()
    sl = sn.lower()
    is_h = sl.startswith("heading")
    lv = 0
    if is_h:
        try:
            lv = int(sl.replace("heading", "").strip())
        except:
            lv = 1
    if is_h and t:
        if cur:
            sections.append(cur)
        cur = {"title": t, "level": lv, "idx": i, "content": "", "pc": 0}
    elif cur is not None and t:
        cur["content"] += t + "\n"
        cur["pc"] += 1
if cur:
    sections.append(cur)

print("\n=== SECTIONS ===")
for s in sections:
    print(f"[H{s['level']}] {s['title']}")
    print(f"  {s['pc']} paragraphs, preview: {s['content'][:200]}")

# 4. SCENARIO SECTION (table 15)
s15 = {"title": "", "content": "", "tables": []}
for i, p in enumerate(doc.paragraphs):
    tl = p.text.strip().lower()
    if "таблица 15" in tl or "табл. 15" in tl:
        s15["title"] = p.text.strip()[:300]
        s15["content"] = p.text.strip()
        break

for ti, tbl in enumerate(doc.tables):
    tt = " ".join(c.text for r in tbl.rows for c in r.cells).lower()
    if "сценари" in tt or ("вариант" in tt and ("разлит" in tt or "утечк" in tt)):
        rd = [[c.text.strip() for c in r.cells] for r in tbl.rows]
        s15["tables"].append({
            "idx": ti, "rows": len(tbl.rows), "cols": len(tbl.columns),
            "headers": rd[0] if rd else [], "all_rows": rd[:30],
        })

if not s15["tables"]:
    for ti, tbl in enumerate(doc.tables):
        if len(tbl.rows) > 8:
            h = " ".join(c.text.strip() for c in tbl.rows[0].cells).lower()
            if any(w in h for w in ["сценари","вариант","опасн","зоны","площад"]):
                rd = [[c.text.strip() for c in r.cells] for r in tbl.rows]
                s15["tables"].append({
                    "idx": ti, "rows": len(tbl.rows), "cols": len(tbl.columns),
                    "headers": rd[0] if rd else [], "all_rows": rd[:30],
                })

print("\n=== SCENARIO SECTION (table 15) ===")
if s15["title"]:
    print(f"Title: {s15['title']}")
if s15["tables"]:
    for st in s15["tables"]:
        print(f"Table {st['idx']}: {st['rows']}x{st['cols']}")
        print(f"Headers: {st['headers']}")
        for row in st["all_rows"]:
            print(f"  {row}")
else:
    print("No scenario table found by keyword search. Large tables:")
    for t in tables:
        if t["rows"] > 8:
            print(f"  T{t['idx']}: {t['rows']}x{t['cols']} hdrs={t['headers']}")

# 5. ACCIDENT EXAMPLES (section 3)
in_s3 = False
s3 = []
for i, p in enumerate(doc.paragraphs):
    sn = p.style.name if p.style else ""
    t = p.text.strip()
    sl = sn.lower()
    if sl.startswith("heading"):
        try:
            lv = int(sl.replace("heading", "").strip())
        except:
            lv = 1
        if t and len(t) > 0:
            first_num = t.lstrip()[:3].replace(".", "").replace(" ", "")
            try:
                n = int(first_num[:1])
            except:
                n = 0
            if n == 3 and lv <= 3:
                in_s3 = True
                continue
            elif in_s3 and lv <= 2:
                in_s3 = False
                continue
    if in_s3 and t:
        s3.append(t)

accidents = []
cur_ex = None
for t in s3:
    tl = t.lower()
    is_start = any(w in tl for w in ["пример","случа","авари","происшестви","разлитие","розлив","загоран","выброс","утечк"])
    if is_start and (len(t) < 200 or t[0:1].isdigit()):
        if cur_ex:
            accidents.append(cur_ex)
        cur_ex = {"title": t[:200], "content": t}
    elif cur_ex:
        cur_ex["content"] += "\n" + t
if cur_ex:
    accidents.append(cur_ex)

print("\n=== ACCIDENT EXAMPLES (Section 3) ===")
print(f"Section 3 has {len(s3)} paragraphs")
for ex in accidents:
    print(f"\nExample: {ex['title'][:150]}")
    print(f"Content: {ex['content'][:500]}")
if not accidents:
    print("Raw section 3 content:")
    for t in s3[:20]:
        print(f"  {t[:200]}")

# 6. KEY TERMS
kt = {
    "org": ["организация","юридическ","адрес","инн","огрн","руководител"],
    "equip": ["оборудован","техник","машин","транспорт","топлив","хранилищ"],
    "scen": ["сценари","вариант","разлити","розлив","утечк","выброс"],
    "acc": ["авари","происшеств","инцидент","разлит","загоран","взрыв","пожар"],
    "zone": ["зона","территор","площад","участ"],
    "vol": ["объем","ёмкость","емкость","тонн"],
}
allt = " ".join(p.text for p in doc.paragraphs).lower()
for tbl in doc.tables:
    for r in tbl.rows:
        for c in r.cells:
            allt += " " + c.text.lower()

print("\n=== KEY TERMS ===")
for cat, terms in kt.items():
    cnt = 0
    found = []
    for term in terms:
        n = allt.count(term)
        if n > 0:
            cnt += n
            found.append(f"{term}({n})")
    print(f"  {cat}: {cnt} | {', '.join(found)}")

# 7. SAVE JSON
out = {
    "file": DOCX_PATH,
    "total_paragraphs": len(doc.paragraphs),
    "total_tables": len(doc.tables),
    "headings": headings,
    "tables": tables,
    "sections": [{"title": s["title"], "level": s["level"], "idx": s["idx"], "pc": s["pc"], "preview": s["content"][:500]} for s in sections],
    "special_section_15": s15,
    "accident_examples": accidents,
    "data_patterns": pat_map,
}
with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2, default=str)

# 8. SAVE TXT
with open(OUTPUT_TXT, "w", encoding="utf-8") as f:
    f.write("=" * 80 + "\nDOCX ANALYSIS: ПМЛА ООО СПК ААА.docx\n" + "=" * 80 + "\n\n")
    f.write(f"Paragraphs: {len(doc.paragraphs)}\nTables: {len(doc.tables)}\n\n")

    f.write("-" * 80 + "\nHEADINGS HIERARCHY\n" + "-" * 80 + "\n")
    for h in headings:
        ind = "  " * (h["lv"] - 1)
        f.write(f"{ind}[H{h['lv']}] {h['txt']}\n")

    f.write("\n" + "-" * 80 + "\nTABLE DETAILS\n" + "-" * 80 + "\n")
    for t in tables:
        f.write(f"\nTable T{t['idx']}: {t['rows']} rows x {t['cols']} cols\n")
        f.write(f"  Pattern: {t['pattern']}\n")
        f.write(f"  Headers: {t['headers']}\n")
        f.write(f"  Caption: {t['caption']}\n")
        f.write("  First 3 data rows:\n")
        for row in t["first3"]:
            f.write(f"    {row}\n")
        f.write(f"  Sample values:\n")
        for k, v in t["samples"].items():
            f.write(f"    {k}: {v}\n")

    f.write("\n" + "-" * 80 + "\nSECTIONS BREAKDOWN\n" + "-" * 80 + "\n")
    for s in sections:
        f.write(f"\n[H{s['level']}] {s['title']}\n")
        f.write(f"  {s['pc']} paragraphs\n")
        f.write(f"  Content preview:\n    {s['content'][:600]}\n")

    f.write("\n" + "-" * 80 + "\nSCENARIO SECTION (table 15)\n" + "-" * 80 + "\n")
    if s15["title"]:
        f.write(f"Title: {s15['title']}\n")
    for st in s15["tables"]:
        f.write(f"\nTable T{st['idx']}: {st['rows']}x{st['cols']}\n")
        f.write(f"Headers: {st['headers']}\n")
        for row in st["all_rows"]:
            f.write(f"  {row}\n")
    if not s15["tables"]:
        f.write("No scenario table found. Large candidate tables:\n")
        for t in tables:
            if t["rows"] > 8:
                f.write(f"  T{t['idx']}: {t['rows']}x{t['cols']} hdrs={t['headers']}\n")

    f.write("\n" + "-" * 80 + "\nACCIDENT EXAMPLES (Section 3)\n" + "-" * 80 + "\n")
    for ex in accidents:
        f.write(f"\n{ex['title']}\n{ex['content']}\n")
    if not accidents:
        f.write("Raw section 3 content:\n")
        for t in s3[:30]:
            f.write(f"  {t}\n")

    f.write("\n" + "-" * 80 + "\nDATA PATTERNS\n" + "-" * 80 + "\n")
    for p, ids in pat_map.items():
        f.write(f"  {p}: tables {ids}\n")

    f.write("\n" + "-" * 80 + "\nKEY TERMS\n" + "-" * 80 + "\n")
    for cat, terms in kt.items():
        cnt = sum(allt.count(term) for term in terms)
        found = [f"{term}({allt.count(term)})" for term in terms if allt.count(term) > 0]
        f.write(f"  {cat}: {cnt} | {', '.join(found)}\n")

    f.write("\n" + "=" * 80 + "\nEND\n" + "=" * 80 + "\n")

print(f"\nSaved JSON: {OUTPUT_JSON}")
print(f"Saved TXT: {OUTPUT_TXT}")
print("\n=== ANALYSIS COMPLETE ===")
