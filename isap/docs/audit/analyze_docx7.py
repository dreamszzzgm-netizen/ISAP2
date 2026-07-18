#!/usr/bin/env python3
"""Seventh pass: Check all org names in both files."""
import zipfile
import re

for label, path in [('TEST', r'D:\Project ISAP\isap\isap\files\pmla_v2_rendered_test.docx'),
                     ('EMPTY', r'D:\Project ISAP\isap\isap\files\pmla_v2_rendered_empty.docx')]:
    with zipfile.ZipFile(path) as z:
        with z.open('word/document.xml') as f:
            doc = f.read().decode('utf-8', errors='ignore')
        
        print(f'=== {label} ===')
        patterns = {
            'ООО ТестПром': doc.count('ООО ТестПром'),
            'ООО Спас': doc.count('ООО Спас'),
            'КавказГазСервис': doc.count('КавказГазСервис'),
            'Иванов': doc.count('Иванов'),
            'АЛБИР': doc.count('АЛБИР'),
            'ГАЗ': doc.count('г. ГАЗ'),
        }
        for k, v in patterns.items():
            print(f'  {k}: {v}')
        
        # Find first occurrence of each with context
        for pattern in ['ООО ТестПром', 'ООО Спас', 'КавказГазСервис']:
            m = re.search(re.escape(pattern), doc)
            if m:
                start = max(0, m.start() - 80)
                end = min(len(doc), m.end() + 80)
                ctx = doc[start:end]
                texts = re.findall(r'<ns0:t[^>]*>([^<]*)</ns0:t>', ctx)
                clean = ' | '.join(t for t in texts if t.strip())
                print(f'  First {pattern}: ...{clean}...')
            else:
                print(f'  {pattern}: NOT FOUND')
        print()
