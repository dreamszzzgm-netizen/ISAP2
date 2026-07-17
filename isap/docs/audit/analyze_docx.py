#!/usr/bin/env python3
"""Audit script for PMLA v2 rendered DOCX files."""
import zipfile
import re
import xml.etree.ElementTree as ET
import json
import os

FILES = {
    'test': r'D:\Project ISAP\isap\isap\files\pmla_v2_rendered_test.docx',
    'empty': r'D:\Project ISAP\isap\isap\files\pmla_v2_rendered_empty.docx',
}

NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
results = {}

for label, path in FILES.items():
    r = {}
    r['path'] = path
    r['size'] = os.path.getsize(path)

    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        r['zip_files'] = len(names)
        r['xml_files'] = [n for n in names if n.endswith('.xml') or n.endswith('.rels')]
        r['image_files'] = [n for n in names if 'media/' in n]
        r['image_count'] = len(r['image_files'])

        # XML validity
        xml_errors = []
        for name in r['xml_files']:
            try:
                with z.open(name) as f:
                    ET.fromstring(f.read())
            except ET.ParseError as e:
                xml_errors.append({'file': name, 'error': str(e)})
            except Exception as e:
                xml_errors.append({'file': name, 'error': str(e)})
        r['xml_valid'] = len(xml_errors) == 0
        r['xml_errors'] = xml_errors

        # Document XML analysis
        with z.open('word/document.xml') as f:
            doc = f.read().decode('utf-8', errors='ignore')
        r['doc_size'] = len(doc)

        # Tables
        tbl_open = len(re.findall(r'<ns0:tbl[ >]', doc))
        parts = doc.split('</ns0:tbl>')
        table_rows = []
        for part in parts[:-1]:
            rows = len(re.findall(r'<ns0:tr[ >]', part))
            table_rows.append(rows)
        r['table_count'] = tbl_open
        r['table_rows'] = table_rows
        r['total_rows'] = sum(table_rows)

        # Jinja in document.xml
        r['jinja_doc'] = {
            '{{': len(re.findall(r'\{\{', doc)),
            '}}': len(re.findall(r'\}\}', doc)),
            '{%': len(re.findall(r'\{%', doc)),
            '%}': len(re.findall(r'%\}', doc)),
        }

        # Jinja in ALL XML files
        jinja_all = {}
        for name in r['xml_files']:
            with z.open(name) as f:
                xc = f.read().decode('utf-8', errors='ignore')
            jd = len(re.findall(r'\{\{', xc))
            jp = len(re.findall(r'\{%', xc))
            if jd > 0 or jp > 0:
                jinja_all[name] = {'double': jd, 'percent': jp}
        r['jinja_all'] = jinja_all

        # Old data in document.xml
        r['old_data'] = {
            'SPK': doc.count('СПК'),
            'reg_A34-99999-0099': doc.count('А34-99999-0099'),
            'Chegem': doc.count('Чегем'),
        }

        # Old data in ALL XML
        old_data_all = {}
        for name in r['xml_files']:
            with z.open(name) as f:
                xc = f.read().decode('utf-8', errors='ignore')
            found = {}
            if 'А34-99999-0099' in xc:
                found['reg_A34-99999-0099'] = xc.count('А34-99999-0099')
            if 'Чегем' in xc:
                found['Chegem'] = xc.count('Чегем')
            if found:
                old_data_all[name] = found
        r['old_data_all'] = old_data_all

        # Headers and footers
        headers_footers = {}
        for name in ['word/header1.xml', 'word/header2.xml', 'word/footer1.xml', 'word/footer2.xml']:
            if name in names:
                with z.open(name) as f:
                    content = f.read().decode('utf-8', errors='ignore')
                texts = re.findall(r'<ns0:t[^>]*>([^<]*)</ns0:t>', content)
                headers_footers[name] = {
                    'exists': True,
                    'texts': texts,
                    'jinja': {
                        '{{': len(re.findall(r'\{\{', content)),
                        '{%': len(re.findall(r'\{%', content)),
                    }
                }
            else:
                headers_footers[name] = {'exists': False}
        r['headers_footers'] = headers_footers

        # Empty text elements (potential unfilled mandatory fields)
        r['empty_text_elements'] = len(re.findall(r'<ns0:t/>\s*', doc))

        # Image sizes
        image_info = []
        for name in r['image_files']:
            info = z.getinfo(name)
            image_info.append({'name': name, 'size': info.file_size})
        r['image_info'] = image_info

        # Check for remaining loop markers
        r['endfor_count'] = doc.count('endfor')
        r['endif_count'] = doc.count('endif')
        r['for_count'] = doc.count('for ')

        # Empty rows analysis (rows with only empty cells)
        empty_rows_detail = []
        for i, part in enumerate(parts[:-1]):
            row_matches = list(re.finditer(r'<ns0:tr[ >](.*?)</ns0:tr>', part, re.DOTALL))
            for j, rm in enumerate(row_matches):
                row_content = rm.group(1)
                # Check if row has only empty text
                texts_in_row = re.findall(r'<ns0:t[^>]*>([^<]*)</ns0:t>', row_content)
                non_empty = [t for t in texts_in_row if t.strip()]
                if len(texts_in_row) > 0 and len(non_empty) == 0:
                    empty_rows_detail.append({'table': i+1, 'row': j+1})
        r['empty_rows'] = empty_rows_detail

        # Look for unfilled fields - patterns like "________" or empty between markers
        r['underscore_fields'] = len(re.findall(r'_+', doc))

        # Check content types
        with z.open('[Content_Types].xml') as f:
            ct = f.read().decode('utf-8', errors='ignore')
        r['content_types_valid'] = True  # parsed above

    results[label] = r

# Output as JSON for processing
print(json.dumps(results, ensure_ascii=False, indent=2))
