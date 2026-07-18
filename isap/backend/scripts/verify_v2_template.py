"""Verify Jinja2 tags in the modified v2 template."""
from docx import Document

doc = Document(r'D:\Project ISAP\isap\isap\files\pmla_v2_template.docx')

for ti, table in enumerate(doc.tables):
    has_jinja = False
    for row in table.rows:
        for cell in row.cells:
            text = cell.text
            if '{{' in text or '{%' in text:
                has_jinja = True
                break
        if has_jinja:
            break
    
    if has_jinja:
        print(f'\n=== TABLE {ti} (JINJA) ===')
        for ri, row in enumerate(table.rows):
            cells = []
            for ci, cell in enumerate(row.cells):
                text = cell.text.strip()[:80].replace('\n', ' | ')
                cells.append(f'[{ci}]{text}')
            print(f'  Row {ri}: {" || ".join(cells)}')
