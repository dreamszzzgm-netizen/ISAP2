#!/usr/bin/env python3
"""Sixth pass: Check ООО ТестПром and ООО Спас contexts in EMPTY file."""
import zipfile
import re

path = r'D:\Project ISAP\isap\isap\files\pmla_v2_rendered_empty.docx'
with zipfile.ZipFile(path) as z:
    with z.open('word/document.xml') as f:
        doc = f.read().decode('utf-8', errors='ignore')
    
    # ООО ТестПром contexts (first 5)
    print('=== ООО ТестПром in EMPTY (first 5) ===')
    count = 0
    for m in re.finditer('ООО ТестПром', doc):
        if count >= 5:
            break
        start = max(0, m.start() - 100)
        end = min(len(doc), m.end() + 100)
        ctx = doc[start:end]
        texts = re.findall(r'<ns0:t[^>]*>([^<]*)</ns0:t>', ctx)
        clean = ' | '.join(t for t in texts if t.strip())
        print(f'  [{m.start()}] ...{clean}...')
        count += 1
    
    # ООО Спас contexts (first 5)
    print('\n=== ООО Спас in EMPTY (first 5) ===')
    count = 0
    for m in re.finditer('ООО Спас', doc):
        if count >= 5:
            break
        start = max(0, m.start() - 100)
        end = min(len(doc), m.end() + 100)
        ctx = doc[start:end]
        texts = re.findall(r'<ns0:t[^>]*>([^<]*)</ns0:t>', ctx)
        clean = ' | '.join(t for t in texts if t.strip())
        print(f'  [{m.start()}] ...{clean}...')
        count += 1

    # Check Иванов contexts
    print('\n=== Иванов in EMPTY ===')
    count = 0
    for m in re.finditer('Иванов', doc):
        if count >= 3:
            break
        start = max(0, m.start() - 100)
        end = min(len(doc), m.end() + 100)
        ctx = doc[start:end]
        texts = re.findall(r'<ns0:t[^>]*>([^<]*)</ns0:t>', ctx)
        clean = ' | '.join(t for t in texts if t.strip())
        print(f'  [{m.start()}] ...{clean}...')
        count += 1

    # Also check the same for TEST file
print('\n=== ООО ТестПром in TEST ===')
path_test = r'D:\Project ISAP\isap\isap\files\pmla_v2_rendered_test.docx'
with zipfile.ZipFile(path_test) as z:
    with z.open('word/document.xml') as f:
        doc = f.read().decode('utf-8', errors='ignore')
    count = doc.count('ООО ТестПром')
    print(f'  Count: {count}')
    if count > 0:
        m = re.search('ООО ТестПром', doc)
        start = max(0, m.start() - 100)
        end = min(len(doc), m.end() + 100)
        ctx = doc[start:end]
        texts = re.findall(r'<ns0:t[^>]*>([^<]*)</ns0:t>', ctx)
        clean = ' | '.join(t for t in texts if t.strip())
        print(f'  First context: ...{clean}...')
