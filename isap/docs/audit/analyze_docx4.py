#!/usr/bin/env python3
"""Fourth pass: Check 00000 patterns and the header1.xml content in detail."""
import zipfile
import re

# Check 00000 context in EMPTY
path = r'D:\Project ISAP\isap\isap\files\pmla_v2_rendered_empty.docx'
with zipfile.ZipFile(path) as z:
    with z.open('word/document.xml') as f:
        doc = f.read().decode('utf-8', errors='ignore')
    
    # Find 00000 contexts (first 5 only)
    print('=== 00000 contexts in EMPTY document.xml (first 5) ===')
    count = 0
    for m in re.finditer('00000', doc):
        if count >= 5:
            break
        start = max(0, m.start() - 100)
        end = min(len(doc), m.end() + 100)
        ctx = doc[start:end]
        texts = re.findall(r'<ns0:t[^>]*>([^<]*)</ns0:t>', ctx)
        clean = ' | '.join(t for t in texts if t.strip())
        print(f'  [{m.start()}] ...{clean}...')
        count += 1

# Check header1.xml in detail for EMPTY
print('\n=== EMPTY header1.xml full text ===')
with zipfile.ZipFile(path) as z:
    with z.open('word/header1.xml') as f:
        h1 = f.read().decode('utf-8', errors='ignore')
    texts = re.findall(r'<ns0:t[^>]*>([^<]*)</ns0:t>', h1)
    for t in texts:
        if t.strip():
            print(f'  "{t.strip()}"')

# Check TEST header1.xml
print('\n=== TEST header1.xml full text ===')
path_test = r'D:\Project ISAP\isap\isap\files\pmla_v2_rendered_test.docx'
with zipfile.ZipFile(path_test) as z:
    with z.open('word/header1.xml') as f:
        h1 = f.read().decode('utf-8', errors='ignore')
    texts = re.findall(r'<ns0:t[^>]*>([^<]*)</ns0:t>', h1)
    for t in texts:
        if t.strip():
            print(f'  "{t.strip()}"')

# Check for "А34-99999-0099" in both files - the OLD registration number
print('\n=== Old reg number А34-99999-0099 check ===')
for label, p in [('TEST', path_test), ('EMPTY', path)]:
    with zipfile.ZipFile(p) as z:
        found = False
        for name in z.namelist():
            if name.endswith('.xml'):
                with z.open(name) as f:
                    xc = f.read().decode('utf-8', errors='ignore')
                if '99999' in xc and '0099' in xc:
                    contexts = [(m.start(), xc[max(0,m.start()-50):m.end()+50]) for m in re.finditer(r'99999-0099', xc)]
                    if contexts:
                        found = True
                        print(f'  {label}: Found in {name}')
                        for pos, ctx in texts:
                            print(f'    ...{ctx}...')
        if not found:
            print(f'  {label}: NOT FOUND (good)')

# Check the А34-99999-0001 reg number in EMPTY
print('\n=== Registration number А34-99999-0001 in EMPTY ===')
with zipfile.ZipFile(path) as z:
    for name in z.namelist():
        if name.endswith('.xml'):
            with z.open(name) as f:
                xc = f.read().decode('utf-8', errors='ignore')
            if 'А34-99999-0001' in xc:
                contexts = [(m.start(), xc[max(0,m.start()-80):m.end()+80]) for m in re.finditer('А34-99999-0001', xc)]
                print(f'  Found in {name}: {len(contexts)} occurrences')
                for pos, ctx in contexts[:3]:
                    t = re.findall(r'<ns0:t[^>]*>([^<]*)</ns0:t>', ctx)
                    print(f'    texts: {t}')

# Summary: check the А34-00000-0001 in header
print('\n=== А34-00000-0001 in EMPTY header ===')
with zipfile.ZipFile(path) as z:
    with z.open('word/header1.xml') as f:
        h1 = f.read().decode('utf-8', errors='ignore')
    if '00000' in h1:
        texts = re.findall(r'<ns0:t[^>]*>([^<]*)</ns0:t>', h1)
        print(f'  Header texts: {texts}')
        # Find the specific context
        for m in re.finditer('00000', h1):
            start = max(0, m.start() - 80)
            end = min(len(h1), m.end() + 80)
            t = re.findall(r'<ns0:t[^>]*>([^<]*)</ns0:t>', h1[start:end])
            print(f'  Context: {t}')
