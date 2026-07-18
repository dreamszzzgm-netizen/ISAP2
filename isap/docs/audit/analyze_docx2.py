#!/usr/bin/env python3
"""Second pass analysis: old data context, row diffs, empty cells."""
import zipfile
import re
import json

FILES = {
    'test': r'D:\Project ISAP\isap\isap\files\pmla_v2_rendered_test.docx',
    'empty': r'D:\Project ISAP\isap\isap\files\pmla_v2_rendered_empty.docx',
}

for label, path in FILES.items():
    with zipfile.ZipFile(path) as z:
        with z.open('word/document.xml') as f:
            doc = f.read().decode('utf-8', errors='ignore')
        
        print(f'=== {label.upper()} ===')
        
        # Find all occurrences of СПК with context
        spk_matches = [(m.start(), doc[max(0,m.start()-80):m.end()+80]) for m in re.finditer('СПК', doc)]
        print(f'\nСПК occurrences: {len(spk_matches)}')
        for pos, ctx in spk_matches:
            # Extract surrounding text elements
            texts = re.findall(r'<ns0:t[^>]*>([^<]*)</ns0:t>', ctx)
            print(f'  pos {pos}: texts around = {texts}')
        
        # Find all occurrences of Чегем with context
        ch_matches = [(m.start(), doc[max(0,m.start()-100):m.end()+100]) for m in re.finditer('Чегем', doc)]
        print(f'\nЧегем occurrences: {len(ch_matches)}')
        for pos, ctx in ch_matches[:10]:
            texts = re.findall(r'<ns0:t[^>]*>([^<]*)</ns0:t>', ctx)
            print(f'  pos {pos}: texts around = {texts}')
        if len(ch_matches) > 10:
            print(f'  ... and {len(ch_matches)-10} more')
        
        # Analyze each table: find table headers and data patterns
        parts = doc.split('</ns0:tbl>')
        for i, part in enumerate(parts[:-1]):
            rows = re.findall(r'<ns0:tr[ >](.*?)</ns0:tr>', part, re.DOTALL)
            # Get first row text (header)
            if rows:
                first_row_texts = re.findall(r'<ns0:t[^>]*>([^<]*)</ns0:t>', rows[0])
                header_clean = [t.strip() for t in first_row_texts if t.strip()]
                # Count data rows (non-header)
                data_rows = len(rows) - 1 if len(rows) > 1 else 0
                
                # Check for empty cells in data rows
                empty_cells = 0
                for row in rows[1:]:
                    cell_texts = re.findall(r'<ns0:t[^>]*>([^<]*)</ns0:t>', row)
                    non_empty = [t.strip() for t in cell_texts if t.strip()]
                    if len(cell_texts) > 0 and len(non_empty) == 0:
                        empty_cells += 1
                
                print(f'  Table {i+1}: {len(rows)} rows, header: {header_clean[:3]}..., data rows with empty cells: {empty_cells}')
        
        print()
