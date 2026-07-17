#!/usr/bin/env python3
"""Third pass: Check Chegem context in empty file, and check for unfilled placeholders."""
import zipfile
import re

path = r'D:\Project ISAP\isap\isap\files\pmla_v2_rendered_empty.docx'

with zipfile.ZipFile(path) as z:
    with z.open('word/document.xml') as f:
        doc = f.read().decode('utf-8', errors='ignore')
    
    # Find ALL Чегем occurrences with full text context
    print('=== Чегем contexts in EMPTY file ===')
    for m in re.finditer('Чегем', doc):
        start = max(0, m.start() - 150)
        end = min(len(doc), m.end() + 150)
        ctx = doc[start:end]
        texts = re.findall(r'<ns0:t[^>]*>([^<]*)</ns0:t>', ctx)
        clean = ' | '.join(t for t in texts if t.strip())
        print(f'  [{m.start()}] ...{clean}...')
    
    # Check for placeholder patterns: ААА, 00000, empty org names
    print('\n=== Placeholder patterns in EMPTY ===')
    placeholders = {
        'ААА': len(re.findall(r'ААА', doc)),
        '00000': len(re.findall(r'00000', doc)),
        'Название_организации': len(re.findall(r'Название_организации', doc)),
        'Наименование_организации': len(re.findall(r'Наименование_организации', doc)),
        'Организация': len(re.findall(r'Организация', doc)),
    }
    for k, v in placeholders.items():
        if v > 0:
            print(f'  {k}: {v}')
    
    # Check for empty cell patterns - cells with just whitespace
    # Look for cells that have <w:t> with only spaces
    space_cells = re.findall(r'<ns0:t[^>]*>(\s+)</ns0:t>', doc)
    print(f'\nCells with only whitespace: {len(space_cells)}')
    
    # Look for the header content in the document (first table, approval block)
    parts = doc.split('</ns0:tbl>')
    # Table 1 - approval block
    if parts:
        first_tbl = parts[0]
        all_texts = re.findall(r'<ns0:t[^>]*>([^<]*)</ns0:t>', first_tbl)
        print(f'\nTable 1 (approval) all texts:')
        for t in all_texts:
            if t.strip():
                print(f'  "{t.strip()}"')
    
    # Check specific table content differences
    print('\n=== Table 6 comparison (equipment list) ===')
    if len(parts) > 5:
        t6_texts = re.findall(r'<ns0:t[^>]*>([^<]*)</ns0:t>', parts[5])
        for t in t6_texts:
            if t.strip():
                print(f'  "{t.strip()}"')
    
    print('\n=== Table 7 (parameters) ===')
    if len(parts) > 6:
        t7_texts = re.findall(r'<ns0:t[^>]*>([^<]*)</ns0:t>', parts[6])
        for t in t7_texts:
            if t.strip():
                print(f'  "{t.strip()}"')

    print('\n=== Table 14 (resources) ===')
    if len(parts) > 13:
        t14_texts = re.findall(r'<ns0:t[^>]*>([^<]*)</ns0:t>', parts[13])
        for t in t14_texts:
            if t.strip():
                print(f'  "{t.strip()}"')
