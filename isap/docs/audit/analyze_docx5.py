#!/usr/bin/env python3
"""Fifth pass: Check for test data remnants, ООО ТестПром, and organization names."""
import zipfile
import re

for label, path in [('TEST', r'D:\Project ISAP\isap\isap\files\pmla_v2_rendered_test.docx'),
                     ('EMPTY', r'D:\Project ISAP\isap\isap\files\pmla_v2_rendered_empty.docx')]:
    with zipfile.ZipFile(path) as z:
        with z.open('word/document.xml') as f:
            doc = f.read().decode('utf-8', errors='ignore')
        
        print(f'=== {label} ===')
        
        # Check for test data
        test_patterns = {
            'ООО ТестПром': doc.count('ООО ТестПром'),
            'ООО Спас': doc.count('ООО Спас'),
            'КавказГазСервис': doc.count('КавказГазСервис'),
            'Иванов': doc.count('Иванов'),
            'АЛБИР': doc.count('АЛБИР'),
        }
        for k, v in test_patterns.items():
            if v > 0:
                print(f'  {k}: {v}')
        
        # Check header1 org name
        with z.open('word/header1.xml') as f:
            h1 = f.read().decode('utf-8', errors='ignore')
        h1_texts = re.findall(r'<ns0:t[^>]*>([^<]*)</ns0:t>', h1)
        org_in_header = [t for t in h1_texts if 'ООО' in t or 'СПК' in t or 'АО' in t or 'ПАО' in t]
        print(f'  Header org: {org_in_header}')
        
        # Check registration numbers in header
        reg_in_header = [t for t in h1_texts if 'А34' in t or '00000' in t or '99999' in t]
        print(f'  Header reg: {reg_in_header}')
        
        # Check for unfilled date fields (____)
        unfilled_dates = len(re.findall(r'_+', doc))
        print(f'  Unfilled date fields (____): {unfilled_dates}')
        
        # Check for "Класс" or class references
        class_refs = re.findall(r'класс[^а-яА-Я]*\w', doc)
        print(f'  Class references (first 3): {class_refs[:3]}')
        
        print()
