"""Глубокий анализ DOCX - детальные ответы на все вопросы."""
import zipfile
from xml.etree import ElementTree as ET
from pathlib import Path
import re
from collections import Counter

NS_W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
NS_WP = 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing'
NS_A = 'http://schemas.openxmlformats.org/drawingml/2006/main'
NS_R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'

def register_ns():
    ET.register_namespace('w', 'http://schemas.openxmlformats.org/wordprocessingml/2006/main')
    ET.register_namespace('r', 'http://schemas.openxmlformats.org/officeDocument/2006/relationships')
    ET.register_namespace('wp', NS_WP)
    ET.register_namespace('a', NS_A)

register_ns()

WORK = Path("D:/Project ISAP/isap/isap/files/pmla_v2_template.docx")
ETALON = Path("D:/Project ISAP/isap/isap/files/pmla_v2_template_etalon.docx")

def get_xml(path):
    with zipfile.ZipFile(path, 'r') as z:
        return ET.fromstring(z.read("word/document.xml"))

def get_rels(path):
    with zipfile.ZipFile(path, 'r') as z:
        rels_xml = z.read("word/_rels/document.xml.rels")
    root = ET.fromstring(rels_xml)
    rels = {}
    for rel in root:
        rid = rel.get('Id')
        target = rel.get('Target')
        rels[rid] = target
    return rels

def get_styles(path):
    with zipfile.ZipFile(path, 'r') as z:
        return ET.fromstring(z.read("word/styles.xml"))

def all_text(elem):
    return ''.join(t.text or '' for t in elem.iter(f'{NS_W}t') if t.text)

def get_paras(root):
    return list(root.iter(f'{NS_W}p'))

def get_tables(root):
    return list(root.iter(f'{NS_W}tbl'))

def find_drawings_in_para(p):
    return list(p.iter(f'{NS_W}drawing'))

def get_image_rid(p):
    """Get the first r:embed from a paragraph's drawings."""
    for d in p.iter(f'{NS_W}drawing'):
        for elem in d.iter():
            rid = elem.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
            if rid:
                return rid
    return None

def get_media_list(path):
    with zipfile.ZipFile(path, 'r') as z:
        return [n for n in z.namelist() if n.startswith('word/media/')]

print("=" * 80)
print("ГЛУБОКИЙ АНАЛИЗ СТРУКТУРЫ DOCX-ШАБЛОНОВ")
print("=" * 80)

work_root = get_xml(WORK)
etalon_root = get_xml(ETALON)
work_rels = get_rels(WORK)
etalon_rels = get_rels(ETALON)
work_paras = get_paras(work_root)
etalon_paras = get_paras(etalon_root)
work_tables = get_tables(work_root)
etalon_tables = get_tables(etalon_root)
work_styles = get_styles(WORK)
etalon_styles = get_styles(ETALON)

print(f"\nРабочий: {len(work_paras)} параграфов, {len(work_tables)} таблиц")
print(f"Эталон: {len(etalon_paras)} параграфов, {len(etalon_tables)} таблиц")

# ============================================================
# 1. ЖУРНАЛ КОРРЕКТИРОВКИ — детальный поиск
# ============================================================
print("\n" + "=" * 70)
print("1. ЖУРНАЛ КОРРЕКТИРОВКИ")
print("=" * 70)

for label, paras, root, tables in [
    ("Рабочий", work_paras, work_root, work_tables),
    ("Эталон", etalon_paras, etalon_root, etalon_tables)
]:
    print(f"\n--- {label} ---")
    
    # Search for journal marker
    marker_idx = None
    for i, p in enumerate(paras):
        text = all_text(p).strip()
        if 'ЖУРНАЛ' in text.upper() and 'КОРРЕКТИРОВКИ' in text.upper():
            marker_idx = i
            print(f"Заголовок НАЙДЕН: параграф [{i}], текст: '{text}'")
            # Show para XML for marker
            ppr = p.find(f'{NS_W}pPr')
            pStyle = None
            if ppr is not None:
                ps = ppr.find(f'{NS_W}pStyle')
                if ps is not None:
                    pStyle = ps.get(f'{NS_W}val')
            print(f"  pStyle: {pStyle}")
            print(f"  XML (первые 400): {ET.tostring(p, encoding='unicode')[:400]}")
            break
    
    if marker_idx is None:
        print("ЖУРНАЛ КОРРЕКТИРОВКИ НЕ НАЙДЕН")
        # Search broader
        for i, p in enumerate(paras):
            text = all_text(p).strip()
            if 'корректировк' in text.lower():
                print(f"  Ближайшее совпадение [{i}]: '{text[:100]}'")
    else:
        # Analyze content after marker
        print(f"\n  Содержимое после заголовка (первые 15 параграфов/таблиц):")
        count = 0
        j = marker_idx + 1
        while j < len(paras) and count < 15:
            p = paras[j]
            text = all_text(p).strip()
            
            # Check if this para is inside a table
            is_in_table = False
            for tbl in tables:
                # Check if this paragraph or its parent is in the table
                if tbl.find(f'.//{NS_W}p[{id(p)}]') is not None:
                    pass
                # We check differently - see if this paragraph element is descendant of a table
                for p_in_tbl in tbl.iter(f'{NS_W}p'):
                    if p_in_tbl is p:  # same object identity check
                        is_in_table = True
                        break
            
            if text:
                ppr = p.find(f'{NS_W}pPr')
                pStyle = None
                if ppr is not None:
                    ps = ppr.find(f'{NS_W}pStyle')
                    if ps is not None:
                        pStyle = ps.get(f'{NS_W}val')
                
                # Check for heading
                is_heading = pStyle and pStyle.startswith('Heading')
                prefix = "  [ЗАГОЛОВОК]" if is_heading else ""
                print(f"    [{j}] {prefix} '{text[:150]}' (style={pStyle})")
                count += 1
            
            # Also check for tables at this position
            for t_idx, tbl in enumerate(tables):
                # Get first cell text
                first_cells = tbl.findall(f'.//{NS_W}tc')
                first_text = all_text(first_cells[0])[:80] if first_cells else ''
                # Crude positioning: find paragraphs before this table
                # We'll just list all tables after marker
                pass
            
            j += 1
        
        if count == 0:
            print("    (пусто - все параграфы пустые или в таблицах)")
        
        # Find tables that might be part of the journal
        print(f"\n  Поиск таблицы журнала корректировки:")
        for t_idx, tbl in enumerate(tables):
            rows = tbl.findall(f'.//{NS_W}tr')
            if not rows:
                continue
            first_cell_text = all_text(rows[0].findall(f'.//{NS_W}tc')[0]) if rows[0].findall(f'.//{NS_W}tc') else ''
            # Journal table typically has columns like №, Дата, Раздел, etc.
            if any(kw in first_cell_text.lower() for kw in ['№', 'дата', 'раздел', 'корректировк', 'изменени']):
                print(f"    Таблица [{t_idx}]: {len(rows)} строк")
                print(f"    Первая строка: {first_cell_text[:200]}")
                for ri, row in enumerate(rows[:6]):
                    cells = row.findall(f'.//{NS_W}tc')
                    cell_texts = [all_text(c)[:60] for c in cells]
                    print(f"      Row {ri}: {' | '.join(cell_texts)}")

# ============================================================
# 2. РИСУНКИ 1-4 - детальный поиск изображений
# ============================================================
print("\n" + "=" * 70)
print("2. РИСУНКИ 1-4")
print("=" * 70)

for fig_num in range(1, 5):
    pattern = f"Рисунок {fig_num}"
    print(f"\n--- {pattern} ---")
    
    for label, paras, rels in [
        ("Рабочий", work_paras, work_rels),
        ("Эталон", etalon_paras, etalon_rels)
    ]:
        for i, p in enumerate(paras):
            text = all_text(p).strip()
            if pattern in text:
                print(f"  [{label}] [{i}] {text[:200]}")
                
                # Check for drawings in this paragraph or nearby
                drawings = find_drawings_in_para(p)
                if drawings:
                    print(f"    -> В ЭТОМ ЖЕ ПАРАГРАФЕ {len(drawings)} drawing(s):")
                    for di, d in enumerate(drawings):
                        inline = d.find(f'{{{NS_WP}}}inline')
                        anchor = d.find(f'{{{NS_WP}}}anchor')
                        rid = None
                        for elem in d.iter():
                            r = elem.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
                            if r:
                                rid = r
                                break
                        media = rels.get(rid, 'unknown') if rid else 'unknown'
                        blip = d.find(f'.//{{{NS_A}}}blip')
                        if blip is not None:
                            rid2 = blip.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
                            if rid2 and not rid:
                                media = rels.get(rid2, 'unknown')
                        
                        print(f"      Drawing {di}: inline={inline is not None}, anchor={anchor is not None}, media={media}")
                else:
                    # Check nearby paragraphs
                    for offset in [1, 2, -1]:
                        ni = i + offset
                        if 0 <= ni < len(paras):
                            nd = find_drawings_in_para(paras[ni])
                            if nd:
                                print(f"    -> Параграф [{ni}] ({'+' if offset > 0 else ''}{offset}) содержит {len(nd)} drawing(s)")
                                for di, d in enumerate(nd):
                                    inline = d.find(f'{{{NS_WP}}}inline')
                                    anchor = d.find(f'{{{NS_WP}}}anchor')
                                    rid = None
                                    for elem in d.iter():
                                        r = elem.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
                                        if r:
                                            rid = r
                                            break
                                    media = rels.get(rid, 'unknown') if rid else 'unknown'
                                    blip = d.find(f'.//{{{NS_A}}}blip')
                                    if blip is not None:
                                        rid2 = blip.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
                                        if rid2 and not rid:
                                            media = rels.get(rid2, 'unknown')
                                    print(f"      Drawing {di}: inline={inline is not None}, anchor={anchor is not None}, media={media}")

# ============================================================
# 3. ССЫЛКИ - Форма 16 и другие
# ============================================================
print("\n" + "=" * 70)
print("3. ССЫЛКИ В ТЕКСТЕ")
print("=" * 70)

# Find "Форма 16" specifically
print("\n--- 'Форма 16' ---")
for label, paras in [("Рабочий", work_paras), ("Эталон", etalon_paras)]:
    for i, p in enumerate(paras):
        text = all_text(p).strip()
        if 'Форма' in text and '16' in text:
            print(f"  [{label}] [{i}] {text[:300]}")

# Find all "рисунок N" references
print("\n--- 'рисунок N' в тексте ---")
for label, paras in [("Рабочий", work_paras), ("Эталон", etalon_paras)]:
    print(f"\n  {label}:")
    found = False
    for i, p in enumerate(paras):
        text = all_text(p).strip()
        # Match various forms: рис., рисунок, рисунка, рисунку, рисунке, рисунков
        matches = re.findall(r'(?:рис\.?\s*\d+|рисун[оккакуке]\w*\s*\d+)', text, re.IGNORECASE)
        if matches:
            found = True
            print(f"    [{i}] {text[:250]}")
    if not found:
        print("    (не найдено)")

# Find "форма N" references
print("\n--- 'форма N' ---")
for label, paras in [("Рабочий", work_paras), ("Эталон", etalon_paras)]:
    print(f"\n  {label}:")
    for i, p in enumerate(paras):
        text = all_text(p).strip()
        matches = re.findall(r'форм[аыуе]?\s*\d+', text, re.IGNORECASE)
        if matches:
            print(f"    [{i}] {text[:250]}")

# ============================================================
# 4. ПРИЛОЖЕНИЯ — полный поиск
# ============================================================
print("\n" + "=" * 70)
print("4. ПРИЛОЖЕНИЯ")
print("=" * 70)

for label, paras in [("Рабочий", work_paras), ("Эталон", etalon_paras)]:
    print(f"\n--- {label} ---")
    appendices = []
    for i, p in enumerate(paras):
        text = all_text(p).strip()
        # Match "Приложение N" anywhere in text
        matches = list(re.finditer(r'Приложение\s*\n*\s*([№#]?\s*\d+)', text, re.IGNORECASE))
        if matches:
            for m in matches:
                num_str = re.search(r'\d+', m.group(1))
                num_val = int(num_str.group()) if num_str else 0
                appendices.append({
                    'index': i,
                    'text': text[:200],
                    'num': num_val,
                    'full_match': m.group(0)
                })
        # Also check for "Приложение №N"
        if 'Приложение' in text and ('№' in text or 'No' in text):
            m = re.search(r'Приложение\s*[№#]?\s*(\d+)', text)
            if m and not any(a['index'] == i for a in appendices):
                num_val = int(m.group(1))
                appendices.append({
                    'index': i,
                    'text': text[:200],
                    'num': num_val,
                    'full_match': m.group(0)
                })
    
    # Also check heading styles with "Приложение"
    for i, p in enumerate(paras):
        text = all_text(p).strip()
        ppr = p.find(f'{NS_W}pPr')
        pStyle = None
        if ppr is not None:
            ps = ppr.find(f'{NS_W}pStyle')
            if ps is not None:
                pStyle = ps.get(f'{NS_W}val')
        if pStyle and 'Heading' in pStyle and 'Приложение' in text:
            if not any(a['index'] == i for a in appendices):
                m = re.search(r'\d+', text)
                num_val = int(m.group()) if m else 0
                appendices.append({
                    'index': i,
                    'text': text[:200],
                    'num': num_val,
                    'full_match': text[:50]
                })
    
    appendices.sort(key=lambda x: x['index'])
    
    nums = [a['num'] for a in appendices]
    print(f"  Найдено приложений: {len(appendices)}")
    print(f"  Номера: {nums}")
    
    dupes = [n for n, c in Counter(nums).items() if c > 1]
    if dupes:
        print(f"  ДУБЛИКАТЫ: {dupes}")
    else:
        print(f"  Дубликатов нет")
    
    for a in appendices:
        print(f"    [{a['index']}] №{a['num']}: {a['text'][:150]}")

# ============================================================
# 5. ШРИФТЫ — детальный анализ
# ============================================================
print("\n" + "=" * 70)
print("5. ШРИФТЫ")
print("=" * 70)

for label, styles_root in [("Рабочий", work_styles), ("Эталон", etalon_styles)]:
    print(f"\n--- {label} styles.xml ---")
    
    # Check docDefaults
    docDefaults = styles_root.find(f'.//{NS_W}docDefaults')
    if docDefaults is not None:
        for rPr in docDefaults.findall(f'.//{NS_W}rPr'):
            rFonts = rPr.find(f'{NS_W}rFonts')
            if rFonts is not None:
                print(f"  docDefaults: ascii='{rFonts.get(f'{NS_W}ascii', '')}' hAnsi='{rFonts.get(f'{NS_W}hAnsi', '')}'")
    
    # Check all styles with non-standard fonts (not Times New Roman)
    print(f"\n  Стили с Calibri/Arial (не Times New Roman):")
    for style in styles_root.findall(f'.//{NS_W}style'):
        style_id = style.get(f'{NS_W}styleId', '')
        for rPr in style.findall(f'.//{NS_W}rPr'):
            rFonts = rPr.find(f'{NS_W}rFonts')
            if rFonts is not None:
                ascii_f = rFonts.get(f'{NS_W}ascii', '')
                hAnsi_f = rFonts.get(f'{NS_W}hAnsi', '')
                if ascii_f and ascii_f not in ('Times New Roman', 'Courier New', 'Tahoma', 'TimesNewRomanPSMT', ''):
                    style_type = style.get(f'{NS_W}type', '')
                    print(f"    {style_id} (type={style_type}): ascii='{ascii_f}' hAnsi='{hAnsi_f}'")

# Compare per-file: are there styles that differ?
print(f"\n  Сравнение шрифтов: Calibri/Arial в рабочем и эталоне:")
work_calibri = []
etalon_calibri = []
for style in work_styles.findall(f'.//{NS_W}style'):
    style_id = style.get(f'{NS_W}styleId', '')
    for rPr in style.findall(f'.//{NS_W}rPr'):
        rFonts = rPr.find(f'{NS_W}rFonts')
        if rFonts is not None:
            ascii_f = rFonts.get(f'{NS_W}ascii', '')
            if ascii_f in ('Calibri', 'Arial', 'Calibri Light'):
                work_calibri.append((style_id, ascii_f))
for style in etalon_styles.findall(f'.//{NS_W}style'):
    style_id = style.get(f'{NS_W}styleId', '')
    for rPr in style.findall(f'.//{NS_W}rPr'):
        rFonts = rPr.find(f'{NS_W}rFonts')
        if rFonts is not None:
            ascii_f = rFonts.get(f'{NS_W}ascii', '')
            if ascii_f in ('Calibri', 'Arial', 'Calibri Light'):
                etalon_calibri.append((style_id, ascii_f))

work_set = set((s, f) for s, f in work_calibri)
etalon_set = set((s, f) for s, f in etalon_calibri)
print(f"  Рабочий стили с Calibri/Arial: {work_calibri}")
print(f"  Эталон стили с Calibri/Arial: {etalon_calibri}")
print(f"  Только в рабочем: {work_set - etalon_set}")
print(f"  Только в эталоне: {etalon_set - work_set}")

# ============================================================
# 6. TOC - оглавление
# ============================================================
print("\n" + "=" * 70)
print("6. TOC (ОГЛАВЛЕНИЕ)")
print("=" * 70)

for label, root, paras in [("Рабочий", work_root, work_paras), ("Эталон", etalon_root, etalon_paras)]:
    print(f"\n--- {label} ---")
    
    # Search for TOC field
    toc_found = False
    for i, p in enumerate(paras):
        text = all_text(p).strip()
        instrTexts = p.findall(f'.//{NS_W}instrText')
        for instr in instrTexts:
            if instr.text and 'TOC' in instr.text:
                toc_found = True
                print(f"  TOC field [{i}]: {instr.text}")
                # Show surrounding paragraph
                print(f"  Контекст: '{all_text(p)[:200]}'")
        
        # Also check fldChar (begin/end markers)
        fldChars = p.findall(f'.//{NS_W}fldChar')
        if fldChars and 'TOC' in text.upper():
            toc_found = True
            print(f"  TOC fldChar [{i}]: {text[:200]}")
    
    if not toc_found:
        print(f"  TOC НЕ НАЙДЕН")
    
    # Search for "СОДЕРЖАНИЕ" header
    for i, p in enumerate(paras):
        text = all_text(p).strip()
        if text == 'СОДЕРЖАНИЕ' or text == 'ОГЛАВЛЕНИЕ':
            print(f"  Заголовок '{text}' [{i}]")
            # Check following paragraphs for TOC entries
            print(f"  Параграфы после содержания:")
            for j in range(i+1, min(i+30, len(paras))):
                t = all_text(paras[j]).strip()
                if t:
                    # Check if it looks like a TOC entry (has dots or page numbers)
                    has_dots = '…' in t or '.'*10 in t or '......' in t
                    has_number = bool(re.search(r'\d+\s*$', t))
                    if has_dots or has_number or t.isupper():
                        print(f"    [{j}] '{t[:150]}'")
                    if len(t) < 3:
                        continue
            break

# ============================================================
# 7. ТАБЛИЦА 10
# ============================================================
print("\n" + "=" * 70)
print("7. ТАБЛИЦА 10")
print("=" * 70)

for label, root, paras, tables in [
    ("Рабочий", work_root, work_paras, work_tables),
    ("Эталон", etalon_root, etalon_paras, etalon_tables)
]:
    print(f"\n--- {label} ---")
    
    # Find caption "Таблица 10"
    for i, p in enumerate(paras):
        text = all_text(p).strip()
        if 'Таблица 10' in text or 'таблица 10' in text:
            print(f"  Упоминание 'Таблица 10' [{i}]: '{text[:200]}'")
    
    # Find "Место расположения" 
    for i, p in enumerate(paras):
        text = all_text(p).strip()
        if 'Место расположения' in text:
            print(f"  Упоминание 'Место расположения' [{i}]: '{text[:200]}'")
    
    # Find table that has "Место расположения" in one of its cells
    print(f"  Поиск таблицы с 'Место расположения':")
    for t_idx, tbl in enumerate(tables):
        all_cells = tbl.findall(f'.//{NS_W}tc')
        full_text = all_text(tbl)
        if 'Место расположения' in full_text or 'место расположения' in full_text.lower():
            rows = tbl.findall(f'.//{NS_W}tr')
            print(f"    Таблица [{t_idx}]: {len(rows)} строк, всего {len(all_cells)} ячеек")
            for ri, row in enumerate(rows):
                cells = row.findall(f'.//{NS_W}tc')
                cell_texts = [all_text(c)[:80] for c in cells]
                empty = [ci for ci, ct in enumerate(cell_texts) if not ct.strip()]
                print(f"      Row {ri}: {len(cells)} ячеек, пустые={empty}")
                for ci, ct in enumerate(cell_texts):
                    if ct:
                        print(f"        [{ci}] '{ct}'")
            break

# ============================================================
# 8. ТАБЛИЦА 15
# ============================================================
print("\n" + "=" * 70)
print("8. ТАБЛИЦА 15")
print("=" * 70)

for label, root, paras, tables in [
    ("Рабочий", work_root, work_paras, work_tables),
    ("Эталон", etalon_root, etalon_paras, etalon_tables)
]:
    print(f"\n--- {label} ---")
    
    # Find caption "Таблица 15"
    for i, p in enumerate(paras):
        text = all_text(p).strip()
        if 'Таблица 15' in text or 'таблица 15' in text:
            print(f"  Упоминание 'Таблица 15' [{i}]: '{text[:250]}'")
    
    # Find table 15 by context
    print(f"  Поиск таблицы 15:")
    for t_idx, tbl in enumerate(tables):
        all_cells = tbl.findall(f'.//{NS_W}tc')
        full_text = all_text(tbl)
        if 'Таблица 15' in full_text or 'таблица 15' in full_text:
            rows = tbl.findall(f'.//{NS_W}tr')
            print(f"    Таблица [{t_idx}]: {len(rows)} строк")
            for ri, row in enumerate(rows):
                cells = row.findall(f'.//{NS_W}tc')
                cell_texts = [all_text(c)[:80] for c in cells]
                empty = [ci for ci, ct in enumerate(cell_texts) if not ct.strip()]
                has_empty_para = False
                for c in cells:
                    paras_in_cell = c.findall(f'{NS_W}p')
                    empty_paras = [pi for pi, pp in enumerate(paras_in_cell) if not all_text(pp).strip()]
                    if empty_paras and not all_text(c).strip():
                        has_empty_para = True
                
                print(f"      Row {ri}: {len(cells)} ячеек, пустые={empty}, пустые_абзацы={has_empty_para}")
                for ci, ct in enumerate(cell_texts):
                    if ct:
                        print(f"        [{ci}] '{ct}'")
            
            # Check for empty paragraphs in cells specifically
            print(f"    Проверка пустых абзацев в ячейках:")
            for ri, row in enumerate(rows):
                cells = row.findall(f'.//{NS_W}tc')
                for ci, c in enumerate(cells):
                    paras_in_cell = c.findall(f'{NS_W}p')
                    for pi, pp in enumerate(paras_in_cell):
                        pt = all_text(pp).strip()
                        if not pt:
                            print(f"      Row {ri}, Cell [{ci}], Para [{pi}]: ПУСТОЙ АБЗАЦ")
            break
    else:
        print("    Таблица 15 не найдена (возможно, таблица не содержит маркер 'Таблица 15' в ячейках)")

print("\n" + "=" * 80)
print("АНАЛИЗ ЗАВЕРШЕН")
print("=" * 80)
