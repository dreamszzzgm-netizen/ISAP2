"""Анализ структурных различий между рабочим DOCX и эталоном."""
import zipfile
from xml.etree import ElementTree as ET
from pathlib import Path
import json

NS = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
NS_W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
NS_R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
NS_WP = 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing'
NS_A = 'http://schemas.openxmlformats.org/drawingml/2006/main'
NS_R_DRAW = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'

WORK_DIR = Path("D:/Project ISAP/isap/isap")
WORK_FILE = WORK_DIR / "files" / "pmla_v2_template.docx"
ETALON_FILE = WORK_DIR / "files" / "pmla_v2_template_etalon.docx"


def register_ns():
    ET.register_namespace('w', NS_W)
    ET.register_namespace('r', NS_R)
    ET.register_namespace('wp', NS_WP)
    ET.register_namespace('a', NS_A)


def get_docx_xml(path, filename="word/document.xml"):
    """Read XML from DOCX zip."""
    with zipfile.ZipFile(path, 'r') as z:
        return ET.fromstring(z.read(filename))


def get_docx_styles(path):
    """Read styles.xml from DOCX zip."""
    with zipfile.ZipFile(path, 'r') as z:
        return ET.fromstring(z.read("word/styles.xml"))


def get_docx_media_list(path):
    """List media files in DOCX."""
    with zipfile.ZipFile(path, 'r') as z:
        return [n for n in z.namelist() if n.startswith('word/media/')]


def get_docx_file(path, filename):
    with zipfile.ZipFile(path, 'r') as z:
        return z.read(filename)


def all_text(element):
    """Get all w:t text from an XML element."""
    parts = []
    for t in element.iter(f'{NS}t'):
        if t.text:
            parts.append(t.text)
    return ''.join(parts)


def get_paragraphs(root):
    """Get all paragraphs with their index."""
    paragraphs = []
    for p in root.iter(f'{NS}p'):
        paras = []
        for ppr in p.findall(f'{NS}pPr'):
            paras.append(ppr)
        paragraphs.append(p)
    return paragraphs


def find_image_refs(paragraph):
    """Find image references (drawing/inline/anchor) in a paragraph."""
    drawings = paragraph.findall(f'.//{NS}drawing')
    refs = []
    for d in drawings:
        # Check for inline
        inline = d.find(f'.//{{{NS_WP}}}inline')
        anchor = d.find(f'.//{{{NS_WP}}}anchor')
        blip = d.find(f'.//{{{NS_A}}}blip')
        embed = None
        if blip is not None:
            embed = blip.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
        # Also check for any r:embed
        r_embed = None
        for elem in d.iter():
            r_emb = elem.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
            if r_emb:
                r_embed = r_emb
        refs.append({
            'has_inline': inline is not None,
            'has_anchor': anchor is not None,
            'embed_rid': r_embed or embed
        })
    return refs


def get_rels(path):
    """Get relationships to map rId to media file."""
    with zipfile.ZipFile(path, 'r') as z:
        rels_xml = z.read("word/_rels/document.xml.rels")
    root = ET.fromstring(rels_xml)
    rels = {}
    for rel in root:
        rid = rel.get('Id')
        target = rel.get('Target')
        rels[rid] = target
    return rels


def find_nearest_preceding_heading(paragraphs, idx, root):
    """Find the nearest preceding heading-like paragraph before index idx."""
    for pi in range(idx - 1, -1, -1):
        p = paragraphs[pi]
        ppr = p.find(f'{NS}pPr')
        if ppr is not None:
            pStyle = ppr.find(f'{NS}pStyle')
            if pStyle is not None and pStyle.get(f'{NS}val', '').startswith('Heading'):
                return pi, all_text(p)
            # Also check bold text as heading indicator
            text = all_text(p).strip()
            if text and (text.isupper() or len(text) > 3):
                # Check if it looks like a heading (bold runs)
                bolds = p.findall(f'.//{NS}b')
                if bolds:
                    return pi, text
    return None, None


def find_journal_blocks(paragraphs, file_label):
    """Find 'ЖУРНАЛ КОРРЕКТИРОВКИ' block."""
    results = []
    for i, p in enumerate(paragraphs):
        text = all_text(p).strip()
        if 'ЖУРНАЛ' in text.upper() and 'КОРРЕКТИРОВКИ' in text.upper():
            results.append({
                'para_index': i,
                'text': text,
                'paragraph_xml': ET.tostring(p, encoding='unicode')[:500]
            })
    return results


def find_text_occurrences(paragraphs, pattern):
    """Find all paragraphs containing pattern (case-insensitive)."""
    results = []
    for i, p in enumerate(paragraphs):
        text = all_text(p).strip()
        if pattern.lower() in text.lower():
            results.append({
                'para_index': i,
                'text': text[:200]
            })
    return results


def analyze_journal_block(root, paragraphs, file_label, file_path):
    """Find and analyze 'ЖУРНАЛ КОРРЕКТИРОВКИ' section."""
    marker = None
    marker_idx = None
    for i, p in enumerate(paragraphs):
        text = all_text(p).strip()
        if text.upper().startswith('ЖУРНАЛ') and 'КОРРЕКТИРОВКИ' in text.upper():
            marker_idx = i
            marker = text
            break
    
    if marker is None:
        return {'found': False, 'message': f'ЖУРНАЛ КОРРЕКТИРОВКИ не найден в {file_label}'}
    
    # Collect subsequent paragraphs until next major heading
    block = []
    next_heading_idx = None
    for j in range(marker_idx + 1, len(paragraphs)):
        p = paragraphs[j]
        text = all_text(p).strip()
        ppr = p.find(f'{NS}pPr')
        pStyle = None
        if ppr is not None:
            ps = ppr.find(f'{NS}pStyle')
            if ps is not None:
                pStyle = ps.get(f'{NS}val')
        
        # Stop at next major heading (Heading1-style or all-caps)
        if pStyle in ('Heading1', 'Heading2') or (text and text.isupper() and len(text) > 5 and not text.startswith('Таблица') and j > marker_idx + 1):
            next_heading_idx = j
            break
        # Stop at tables after a certain point
        if text.startswith('СОДЕРЖАНИЕ') or text.startswith('ПЕРЕЧЕНЬ'):
            break
        
        block.append({
            'para_index': j,
            'text': text,
            'pStyle': pStyle,
            'is_table': False,
            'xml_snippet': ET.tostring(p, encoding='unicode')[:300]
        })
    
    # Check for tables that follow (tables are w:tbl, not w:p)
    tables = root.findall(f'.//{NS}tbl')
    table_idx_in_doc = 0
    tables_after_marker = []
    # Get para indices for each table
    table_elements = []
    for t in tables:
        table_elements.append(t)
    
    # Find tables that appear after marker
    for t in tables:
        # Get table rows
        rows = t.findall(f'.//{NS}tr')
        first_row_text = all_text(rows[0]) if rows else ''
        table_para_before = t.find(f'.//{NS}p')
        # Check if this table is after the marker by finding all paragraphs before it
        # We'll approximate by checking if the first row text contains "корректировк"
        if 'корректировк' in first_row_text.lower():
            tables_after_marker.append({
                'first_row': first_row_text[:200],
                'row_count': len(rows),
                'xml_snippet': ET.tostring(t, encoding='unicode')[:500]
            })
    
    return {
        'found': True,
        'marker_index': marker_idx,
        'marker_text': marker,
        'paragraphs_after_marker': block,
        'tables_after_marker': tables_after_marker,
        'next_heading_index': next_heading_idx
    }


def find_tables(root):
    """Find all tables and their positions in the document."""
    tables = []
    for i, t in enumerate(root.findall(f'.//{NS}tbl')):
        rows = t.findall(f'.//{NS}tr')
        row_data = []
        for ri, r in enumerate(rows):
            cells = r.findall(f'.//{NS}tc')
            cell_texts = [all_text(c)[:100] for c in cells]
            row_data.append({
                'row_index': ri,
                'cell_count': len(cells),
                'cell_texts': cell_texts
            })
        
        # Find the paragraph before this table (caption)
        caption_text = ''
        # Get the first row's first cell text as caption
        if row_data:
            caption_text = ' | '.join([c[:80] for c in row_data[0]['cell_texts'] if c.strip()])
        
        tables.append({
            'table_index': i,
            'row_count': len(rows),
            'rows': row_data,
            'first_row_caption': caption_text
        })
    return tables


def analyze_toc(root, paragraphs):
    """Analyze TOC fields."""
    toc_fields = []
    for i, p in enumerate(paragraphs):
        # Check for field codes
        fields = p.findall(f'.//{NS}fldChar')
        instrText = p.findall(f'.//{NS}instrText')
        for instr in instrText:
            if instr.text and 'TOC' in instr.text:
                toc_fields.append({
                    'para_index': i,
                    'instrText': instr.text,
                    'field_code': instr.text
                })
    return toc_fields


def analyze_drawings(paragraphs, file_label, rels, file_path):
    """Analyze all drawings in the document."""
    drawings_info = []
    for i, p in enumerate(paragraphs):
        drawings = p.findall(f'.//{NS}drawing')
        for d in drawings:
            inline = d.find(f'.//{{{NS_WP}}}inline')
            anchor = d.find(f'.//{{{NS_WP}}}anchor')
            
            # Get image reference
            blip = d.find(f'.//{{{NS_A}}}blip')
            embed = None
            if blip is not None:
                embed = blip.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
            
            # Get description if available
            desc = ''
            for elem in d.iter():
                if 'descr' in elem.attrib:
                    desc = elem.attrib['descr']
            
            # Size info
            ext = d.find(f'.//{{{NS_A}}}ext')
            size_info = {}
            if ext is not None:
                size_info = {'cx': ext.get('cx'), 'cy': ext.get('cy')}
            
            # Map to media file
            media_file = rels.get(embed, 'unknown') if embed else 'unknown'
            
            para_text = all_text(p)[:200]
            
            drawings_info.append({
                'para_index': i,
                'has_inline': inline is not None,
                'has_anchor': anchor is not None,
                'embed_rid': embed,
                'media_file': media_file,
                'description': desc,
                'size': size_info,
                'surrounding_text': para_text
            })
    return drawings_info


def find_fonts_in_styles(styles_root, file_label):
    """Analyze fonts in styles.xml."""
    fonts_info = []
    
    # Check all style definitions
    styles = styles_root.findall(f'.//{NS}style')
    for s in styles:
        style_id = s.get(f'{NS}styleId', '')
        style_type = s.get(f'{NS}type', '')
        
        # Get rPr (run properties) for font info
        rPrs = s.findall(f'.//{NS}rPr')
        for rPr in rPrs:
            rFonts = rPr.find(f'{NS}rFonts')
            if rFonts is not None:
                fonts_info.append({
                    'style_id': style_id,
                    'style_type': style_type,
                    'ascii_font': rFonts.get(f'{NS}ascii', ''),
                    'hAnsi_font': rFonts.get(f'{NS}hAnsi', ''),
                    'cs_font': rFonts.get(f'{NS}cs', '')
                })
    
    # Also check default style
    docDefaults = styles_root.find(f'.//{NS}docDefaults')
    if docDefaults is not None:
        for rPr in docDefaults.findall(f'.//{NS}rPr'):
            rFonts = rPr.find(f'{NS}rFonts')
            if rFonts is not None:
                fonts_info.append({
                    'style_id': 'DEFAULT',
                    'style_type': 'docDefaults',
                    'ascii_font': rFonts.get(f'{NS}ascii', ''),
                    'hAnsi_font': rFonts.get(f'{NS}hAnsi', ''),
                    'cs_font': rFonts.get(f'{NS}cs', '')
                })
    
    return fonts_info


def find_local_fonts_in_paragraphs(paragraphs, file_label):
    """Find local font overrides in paragraphs (non-standard fonts)."""
    results = []
    for i, p in enumerate(paragraphs):
        rPrs = p.findall(f'.//{NS}rPr')
        for rPr in rPrs:
            rFonts = rPr.find(f'{NS}rFonts')
            if rFonts is not None:
                ascii_font = rFonts.get(f'{NS}ascii', '')
                hAnsi_font = rFonts.get(f'{NS}hAnsi', '')
                if ascii_font and ascii_font not in ('Times New Roman', ''):
                    text = all_text(p)[:100]
                    results.append({
                        'para_index': i,
                        'ascii_font': ascii_font,
                        'hAnsi_font': hAnsi_font,
                        'text_sample': text,
                        'type': 'local_override'
                    })
    return results


def extract_section_between(paragraphs, from_idx, to_idx):
    """Extract XML of paragraphs between two indices."""
    xml_parts = []
    for i in range(from_idx, to_idx + 1):
        if i < len(paragraphs):
            xml_parts.append(f'<!-- para {i} -->\n{ET.tostring(paragraphs[i], encoding="unicode")}')
    return '\n\n'.join(xml_parts)


def main():
    register_ns()
    
    work_rels = get_rels(WORK_FILE)
    etalon_rels = get_rels(ETALON_FILE)
    
    work_root = get_docx_xml(WORK_FILE)
    etalon_root = get_docx_xml(ETALON_FILE)
    
    work_styles = get_docx_styles(WORK_FILE)
    etalon_styles = get_docx_styles(ETALON_FILE)
    
    work_paras = get_paragraphs(work_root)
    etalon_paras = get_paragraphs(etalon_root)
    
    report = {}
    report['file_info'] = {
        'working': str(WORK_FILE),
        'working_size': WORK_FILE.stat().st_size,
        'etalon': str(ETALON_FILE),
        'etalon_size': ETALON_FILE.stat().st_size,
        'working_paragraphs': len(work_paras),
        'etalon_paragraphs': len(etalon_paras)
    }
    
    # ===== 1. ЖУРНАЛ КОРРЕКТИРОВКИ =====
    print("=" * 70)
    print("1. ЖУРНАЛ КОРРЕКТИРОВКИ")
    print("=" * 70)
    
    work_journal = find_journal_blocks(work_paras, 'рабочий')
    etalon_journal = find_journal_blocks(etalon_paras, 'эталон')
    
    print(f"Рабочий: {'НАЙДЕНО' if work_journal else 'НЕ НАЙДЕНО'}")
    print(f"Эталон: {'НАЙДЕНО' if etalon_journal else 'НЕ НАЙДЕНО'}")
    
    if work_journal:
        print(f"  Рабочий: индекс {work_journal[0]['para_index']}, текст: {work_journal[0]['text']}")
    if etalon_journal:
        print(f"  Эталон: индекс {etalon_journal[0]['para_index']}, текст: {etalon_journal[0]['text']}")
    
    # Detailed block analysis
    work_journal_block = analyze_journal_block(work_root, work_paras, 'рабочий', WORK_FILE)
    etalon_journal_block = analyze_journal_block(etalon_root, etalon_paras, 'эталон', ETALON_FILE)
    
    report['journal'] = {
        'working': work_journal_block,
        'etalon': etalon_journal_block
    }
    
    if work_journal_block['found']:
        print(f"  Working marker at para {work_journal_block['marker_index']}")
        print(f"  Paragraphs after marker: {len(work_journal_block['paragraphs_after_marker'])}")
        print(f"  Tables after marker: {len(work_journal_block['tables_after_marker'])}")
    if etalon_journal_block['found']:
        print(f"  Etalon marker at para {etalon_journal_block['marker_index']}")
        print(f"  Paragraphs after marker: {len(etalon_journal_block['paragraphs_after_marker'])}")
        print(f"  Tables after marker: {len(etalon_journal_block['tables_after_marker'])}")
    
    # If not found in working but found in etalon - extract full block
    if not work_journal and etalon_journal:
        ej = etalon_journal[0]
        marker_idx = ej['para_index']
        # Find next major heading
        next_heading = None
        for j in range(marker_idx + 1, len(etalon_paras)):
            p = etalon_paras[j]
            text = all_text(p).strip()
            ppr = p.find(f'{NS}pPr')
            pStyle = None
            if ppr is not None:
                ps = ppr.find(f'{NS}pStyle')
                if ps is not None:
                    pStyle = ps.get(f'{NS}val')
            if pStyle in ('Heading1', 'Heading2') or (text and text.isupper() and len(text) > 5):
                next_heading = (j, text)
                break
        
        print(f"\n*** ЖУРНАЛ КОРРЕКТИРОВКИ ОТСУТСТВУЕТ В РАБОЧЕМ ***")
        print(f"Полный блок из эталона (параграфы {marker_idx} - {next_heading[0] if next_heading else 'end'}):")
        
        if next_heading:
            end_idx = next_heading[0]
            print(f"  От параграфа {marker_idx} до параграфа {end_idx} (следующий заголовок: '{next_heading[1]}')")
        else:
            end_idx = len(etalon_paras) - 1
        
        # Extract XML for the block
        block_xml = extract_section_between(etalon_paras, marker_idx, marker_idx + 20)
        report['journal_extracted_block'] = {
            'start_para': marker_idx,
            'end_para': end_idx,
            'text_block': [all_text(etalon_paras[i]) for i in range(marker_idx, min(end_idx + 1, marker_idx + 50))],
            'xml_block': block_xml[:5000]  # First 5000 chars
        }
        print(f"  Текст после заголовка:")
        for j in range(marker_idx + 1, min(end_idx + 1, marker_idx + 30)):
            if j < len(etalon_paras):
                t = all_text(etalon_paras[j]).strip()
                if t:
                    print(f"    [{j}] {t[:150]}")
    
    # ===== 2. РИСУНКИ 1-4 =====
    print("\n" + "=" * 70)
    print("2. РИСУНКИ 1-4")
    print("=" * 70)
    
    # Find figure references in text
    for fig_num in range(1, 5):
        pattern = f"Рисунок {fig_num}"
        work_figs = find_text_occurrences(work_paras, pattern)
        etalon_figs = find_text_occurrences(etalon_paras, pattern)
        
        print(f"\n--- {pattern} ---")
        print(f"  Рабочий: {len(work_figs) if work_figs else 0} упоминаний")
        if work_figs:
            for f in work_figs:
                print(f"    [{f['para_index']}] {f['text'][:150]}")
        print(f"  Эталон: {len(etalon_figs) if etalon_figs else 0} упоминаний")
        if etalon_figs:
            for f in etalon_figs:
                print(f"    [{f['para_index']}] {f['text'][:150]}")
    
    # Analyze drawings
    work_drawings = analyze_drawings(work_paras, 'рабочий', work_rels, WORK_FILE)
    etalon_drawings = analyze_drawings(etalon_paras, 'эталон', etalon_rels, ETALON_FILE)
    
    print(f"\n--- РИСУНКИ (drawings) ---")
    print(f"  Рабочий: всего {len(work_drawings)} drawings")
    for d in work_drawings:
        print(f"    [{d['para_index']}] inline={d['has_inline']} anchor={d['has_anchor']} media={d['media_file']} text='{d['surrounding_text'][:80]}'")
    
    print(f"  Эталон: всего {len(etalon_drawings)} drawings")
    for d in etalon_drawings:
        print(f"    [{d['para_index']}] inline={d['has_inline']} anchor={d['has_anchor']} media={d['media_file']} text='{d['surrounding_text'][:80]}'")
    
    report['figures'] = {
        'working_drawings': work_drawings,
        'etalon_drawings': etalon_drawings,
        'working_media': get_docx_media_list(WORK_FILE),
        'etalon_media': get_docx_media_list(ETALON_FILE)
    }
    
    # ===== 3. ССЫЛКИ =====
    print("\n" + "=" * 70)
    print("3. ССЫЛКИ В ТЕКСТЕ")
    print("=" * 70)
    
    # Find "Форма 16" in working
    forma16_work = find_text_occurrences(work_paras, "Форма 16")
    forma16_etalon = find_text_occurrences(etalon_paras, "Форма 16")
    print(f"\n--- Форма 16 ---")
    print(f"  Рабочий: {len(forma16_work)}")
    for f in forma16_work:
        print(f"    [{f['para_index']}] {f['text'][:150]}")
    print(f"  Эталон: {len(forma16_etalon)}")
    for f in forma16_etalon:
        print(f"    [{f['para_index']}] {f['text'][:150]}")
    
    report['forma16'] = {
        'working': forma16_work,
        'etalon': forma16_etalon
    }
    
    # Find all "рисунок N" references
    import re
    for file_label, paragraphs in [('рабочий', work_paras), ('эталон', etalon_paras)]:
        print(f"\n--- Ссылки на 'рисунок N' в {file_label} ---")
        for i, p in enumerate(paragraphs):
            text = all_text(p).strip()
            matches = re.findall(r'[Рр]исун[ок|ка|ку|ке|ков]\s*\d+', text[:500])
            if matches:
                print(f"    [{i}] {text[:200]}")
    
    # ===== 4. ПРИЛОЖЕНИЯ =====
    print("\n" + "=" * 70)
    print("4. ПРИЛОЖЕНИЯ")
    print("=" * 70)
    
    def find_appendix_occurrences(paragraphs):
        results = []
        for i, p in enumerate(paragraphs):
            text = all_text(p).strip()
            import re
            matches = re.findall(r'Приложение\s+\d+', text)
            if matches:
                for m in matches:
                    num = re.search(r'\d+', m)
                    num_val = int(num.group()) if num else 0
                    results.append({
                        'para_index': i,
                        'text': text[:200],
                        'appendix_num': num_val,
                        'full_match': m
                    })
        return results
    
    work_appendix = find_appendix_occurrences(work_paras)
    etalon_appendix = find_appendix_occurrences(etalon_paras)
    
    print(f"\nРабочий:")
    work_nums = [a['appendix_num'] for a in work_appendix]
    print(f"  Номера приложений: {sorted(set(work_nums))}")
    from collections import Counter
    work_dupes = [k for k, v in Counter(work_nums).items() if v > 1]
    if work_dupes:
        print(f"  ДУБЛИКАТЫ: {work_dupes}")
    else:
        print(f"  Дубликатов нет")
    for a in work_appendix:
        print(f"    [{a['para_index']}] {a['text'][:150]}")
    
    print(f"\nЭталон:")
    etalon_nums = [a['appendix_num'] for a in etalon_appendix]
    print(f"  Номера приложений: {sorted(set(etalon_nums))}")
    etalon_dupes = [k for k, v in Counter(etalon_nums).items() if v > 1]
    if etalon_dupes:
        print(f"  ДУБЛИКАТЫ: {etalon_dupes}")
    else:
        print(f"  Дубликатов нет")
    for a in etalon_appendix:
        print(f"    [{a['para_index']}] {a['text'][:150]}")
    
    report['appendix'] = {
        'working': work_appendix,
        'working_nums': sorted(set(work_nums)),
        'working_duplicates': work_dupes,
        'etalon': etalon_appendix,
        'etalon_nums': sorted(set(etalon_nums)),
        'etalon_duplicates': etalon_dupes
    }
    
    # ===== 5. ШРИФТЫ =====
    print("\n" + "=" * 70)
    print("5. ШРИФТЫ")
    print("=" * 70)
    
    work_fonts = find_fonts_in_styles(work_styles, 'рабочий')
    etalon_fonts = find_fonts_in_styles(etalon_styles, 'эталон')
    
    print(f"\n--- w:ascii / w:hAnsi в styles.xml ---")
    print(f"\nРабочий ({len(work_fonts)} найденных):")
    for f in work_fonts:
        print(f"  style={f['style_id']} type={f['style_type']} ascii='{f['ascii_font']}' hAnsi='{f['hAnsi_font']}'")
    
    print(f"\nЭталон ({len(etalon_fonts)} найденных):")
    for f in etalon_fonts:
        print(f"  style={f['style_id']} type={f['style_type']} ascii='{f['ascii_font']}' hAnsi='{f['hAnsi_font']}'")
    
    # Find local font overrides with non-TNR fonts
    work_local_fonts = find_local_fonts_in_paragraphs(work_paras, 'рабочий')
    etalon_local_fonts = find_local_fonts_in_paragraphs(etalon_paras, 'эталон')
    
    # Filter to show only Calibri/Arial
    print(f"\n--- Calibri/Arial в рабочем vs Times New Roman в эталоне ---")
    print(f"Рабочий - локальные шрифты (не Times New Roman):")
    for f in work_local_fonts:
        if f['ascii_font'] in ('Calibri', 'Arial', 'Calibri Light'):
            print(f"  [{f['para_index']}] {f['ascii_font']}/{f['hAnsi_font']}: '{f['text_sample']}'")
    
    report['fonts'] = {
        'working_styles': work_fonts,
        'etalon_styles': etalon_fonts,
        'working_local_non_standard': work_local_fonts,
        'etalon_local_non_standard': etalon_local_fonts
    }
    
    # ===== 6. TOC =====
    print("\n" + "=" * 70)
    print("6. TOC (ОГЛАВЛЕНИЕ)")
    print("=" * 70)
    
    work_toc = analyze_toc(work_root, work_paras)
    etalon_toc = analyze_toc(etalon_root, etalon_paras)
    
    print(f"\nРабочий: {'TOC НАЙДЕН' if work_toc else 'TOC НЕ НАЙДЕН'}")
    for t in work_toc:
        print(f"  [{t['para_index']}] {t['field_code']}")
    
    print(f"\nЭталон: {'TOC НАЙДЕН' if etalon_toc else 'TOC НЕ НАЙДЕН'}")
    for t in etalon_toc:
        print(f"  [{t['para_index']}] {t['field_code']}")
    
    # Count TOC items by looking at structured document tags or TOC entries
    def count_toc_entries(root):
        entries = root.findall(f'.//{NS}sdt')
        toc_count = 0
        for sdt in entries:
            # Look for TOC entries via the sdtPr
            sdtPr = sdt.find(f'{NS}sdtPr')
            if sdtPr is not None:
                tag = sdtPr.find(f'{NS}tag')
                if tag is not None and tag.get(f'{NS}val', '').startswith('TOC'):
                    toc_count += 1
            # Also check if it contains a hyperlink (typical for TOC)
            if sdt.find(f'.//{NS}hyperlink') is not None:
                toc_count += 1
        return toc_count
    
    work_toc_count = count_toc_entries(work_root)
    etalon_toc_count = count_toc_entries(etalon_root)
    
    print(f"\nЭлементов в содержании (приблизительно):")
    print(f"  Рабочий: {work_toc_count}")
    print(f"  Эталон: {etalon_toc_count}")
    
    report['toc'] = {
        'working_exists': len(work_toc) > 0,
        'working_fields': work_toc,
        'working_toc_entries': work_toc_count,
        'etalon_exists': len(etalon_toc) > 0,
        'etalon_fields': etalon_toc,
        'etalon_toc_entries': etalon_toc_count
    }
    
    # ===== 7. ТАБЛИЦА 10 =====
    print("\n" + "=" * 70)
    print("7. ТАБЛИЦА 10")
    print("=" * 70)
    
    def analyze_table_captions_and_tables(paragraphs, root, caption_pattern):
        """Find tables with caption matching pattern."""
        # First find caption paragraphs
        caption_indices = []
        for i, p in enumerate(paragraphs):
            text = all_text(p).strip()
            if caption_pattern.lower() in text.lower():
                caption_indices.append(i)
        
        # Find all tables
        tables = root.findall(f'.//{NS}tbl')
        table_info = []
        for t in tables:
            rows = t.findall(f'.//{NS}tr')
            row_data = []
            for ri, r in enumerate(rows):
                cells = r.findall(f'.//{NS}tc')
                cell_texts = []
                for ci, c in enumerate(cells):
                    cell_texts.append(all_text(c).strip()[:80])
                row_data.append({
                    'row_index': ri,
                    'cell_count': len(cells),
                    'cell_texts': cell_texts,
                    'has_empty_paragraphs': any(all_text(c) == '' for c in cells)
                })
            # Get text from top-left cell as caption hint
            caption_hint = row_data[0]['cell_texts'][0] if row_data and row_data[0]['cell_texts'] else ''
            table_info.append({
                'row_count': len(rows),
                'rows': row_data,
                'caption_hint': caption_hint
            })
        
        return caption_indices, table_info
    
    # Поиск Таблица 10 и Место расположения
    work_t10_captions, work_t10_tables = analyze_table_captions_and_tables(work_paras, work_root, 'Таблица 10')
    etalon_t10_captions, etalon_t10_tables = analyze_table_captions_and_tables(etalon_paras, etalon_root, 'Таблица 10')
    
    work_mloc_captions, _ = analyze_table_captions_and_tables(work_paras, work_root, 'Место расположения')
    etalon_mloc_captions, _ = analyze_table_captions_and_tables(etalon_paras, etalon_root, 'Место расположения')
    
    print(f"\n--- 'Таблица 10' ---")
    print(f"Рабочий: {len(work_t10_captions)} упоминаний")
    for idx in work_t10_captions:
        text = all_text(work_paras[idx]).strip()
        print(f"  [{idx}] {text[:150]}")
    print(f"Эталон: {len(etalon_t10_captions)} упоминаний")
    for idx in etalon_t10_captions:
        text = all_text(etalon_paras[idx]).strip()
        print(f"  [{idx}] {text[:150]}")
    
    # Show table rows for the first matching table
    if work_t10_tables:
        print(f"\nРабочий - детали таблиц:")
        for ti, t in enumerate(work_t10_tables):
            if 'Таблица 10' in t['caption_hint'] or '10' in t['caption_hint']:
                print(f"  Таблица {ti}: {t['row_count']} строк")
                for row in t['rows']:
                    empty_cols = [ci for ci, ct in enumerate(row['cell_texts']) if not ct.strip()]
                    print(f"    Row {row['row_index']}: cells={row['cell_count']}, empty_cols={empty_cols}")
                    for ci, ct in enumerate(row['cell_texts']):
                        if ct:
                            print(f"      [{ci}] {ct[:60]}")
    
    if etalon_t10_tables:
        print(f"\nЭталон - детали таблиц:")
        for ti, t in enumerate(etalon_t10_tables):
            if 'Таблица 10' in t['caption_hint'] or '10' in t['caption_hint']:
                print(f"  Таблица {ti}: {t['row_count']} строк")
                for row in t['rows']:
                    empty_cols = [ci for ci, ct in enumerate(row['cell_texts']) if not ct.strip()]
                    print(f"    Row {row['row_index']}: cells={row['cell_count']}, empty_cols={empty_cols}")
                    for ci, ct in enumerate(row['cell_texts']):
                        if ct:
                            print(f"      [{ci}] {ct[:60]}")
    
    print(f"\n--- 'Место расположения' ---")
    print(f"Рабочий: {len(work_mloc_captions)} упоминаний")
    for idx in work_mloc_captions:
        text = all_text(work_paras[idx]).strip()
        print(f"  [{idx}] {text[:150]}")
    print(f"Эталон: {len(etalon_mloc_captions)} упоминаний")
    for idx in etalon_mloc_captions:
        text = all_text(etalon_paras[idx]).strip()
        print(f"  [{idx}] {text[:150]}")
    
    report['table10'] = {
        'working_captions': work_t10_captions,
        'working_mloc': work_mloc_captions,
        'working_tables_summary': [{'row_count': t['row_count'], 'rows': [{r['row_index']: r['cell_texts']} for r in t['rows']]} for t in work_t10_tables if '10' in t['caption_hint']],
        'etalon_captions': etalon_t10_captions,
        'etalon_mloc': etalon_mloc_captions,
        'etalon_tables_summary': [{'row_count': t['row_count'], 'rows': [{r['row_index']: r['cell_texts']} for r in t['rows']]} for t in etalon_t10_tables if '10' in t['caption_hint']]
    }
    
    # ===== 8. ТАБЛИЦА 15 =====
    print("\n" + "=" * 70)
    print("8. ТАБЛИЦА 15")
    print("=" * 70)
    
    work_t15_captions, work_t15_tables = analyze_table_captions_and_tables(work_paras, work_root, 'Таблица 15')
    etalon_t15_captions, etalon_t15_tables = analyze_table_captions_and_tables(etalon_paras, etalon_root, 'Таблица 15')
    
    print(f"\n--- 'Таблица 15' ---")
    print(f"Рабочий: {len(work_t15_captions)} упоминаний")
    for idx in work_t15_captions:
        text = all_text(work_paras[idx]).strip()
        print(f"  [{idx}] {text[:150]}")
    print(f"Эталон: {len(etalon_t15_captions)} упоминаний")
    for idx in etalon_t15_captions:
        text = all_text(etalon_paras[idx]).strip()
        print(f"  [{idx}] {text[:150]}")
    
    # Show table 15 details
    print(f"\nРабочий - детали таблиц 15:")
    for ti, t in enumerate(work_t15_tables):
        if '15' in t['caption_hint'] or '15' in t['caption_hint']:
            print(f"  Таблица {ti}: {t['row_count']} строк, caption_hint='{t['caption_hint']}'")
            for row in t['rows']:
                empty_cells = [ci for ci, ct in enumerate(row['cell_texts']) if not ct.strip()]
                empty_paras = [ci for ci, cr in enumerate(row['cell_texts']) if cr.strip() == '']
                print(f"    Row {row['row_index']}: {len(row['cell_texts'])} cells, empty={empty_cells}")
                # Check for empty paragraphs in cells
                for ci, ct in enumerate(row['cell_texts']):
                    if ct:
                        print(f"      [{ci}] '{ct[:60]}'")
                print(f"    -> has_empty_paragraphs={row['has_empty_paragraphs']}")
    
    print(f"\nЭталон - детали таблиц 15:")
    for ti, t in enumerate(etalon_t15_tables):
        if '15' in t['caption_hint'] or 'Таблица' in t['caption_hint']:
            print(f"  Таблица {ti}: {t['row_count']} строк, caption_hint='{t['caption_hint']}'")
            for row in t['rows']:
                empty_cells = [ci for ci, ct in enumerate(row['cell_texts']) if not ct.strip()]
                print(f"    Row {row['row_index']}: {len(row['cell_texts'])} cells, empty={empty_cells}")
                for ci, ct in enumerate(row['cell_texts']):
                    if ct:
                        print(f"      [{ci}] '{ct[:60]}'")
                print(f"    -> has_empty_paragraphs={row['has_empty_paragraphs']}")
    
    report['table15'] = {
        'working_captions': work_t15_captions,
        'working_tables_summary': [{'row_count': t['row_count'], 'rows': [{r['row_index']: r['cell_texts']} for r in t['rows']]} for t in work_t15_tables if '15' in t['caption_hint']],
        'etalon_captions': etalon_t15_captions,
        'etalon_tables_summary': [{'row_count': t['row_count'], 'rows': [{r['row_index']: r['cell_texts']} for r in t['rows']]} for t in etalon_t15_tables if '15' in t['caption_hint']]
    }
    
    # Сохраняем JSON-отчёт
    report_file = WORK_DIR / "docx_diff_analysis.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)
    
    text_report_file = WORK_DIR / "docx_diff_analysis.txt"
    print(f"\n\nОтчёт сохранён: {report_file}")
    print(f"Текстовый отчёт: {text_report_file}")

if __name__ == "__main__":
    main()
