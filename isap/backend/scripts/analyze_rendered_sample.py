"""Analyze all tables in the PMLA rendered sample."""
from docx import Document

doc = Document(r'D:\Project ISAP\isap\isap\files\pmla_rendered_sample.docx')

for ti, table in enumerate(doc.tables):
    print(f'=== TABLE {ti} ===')
    print(f'Rows: {len(table.rows)}, Cols: {len(table.columns)}')
    
    for ri, row in enumerate(table.rows):
        cells_text = []
        for ci, cell in enumerate(row.cells):
            text = cell.text.strip()[:80].replace('\n', ' | ')
            cells_text.append(f'[{ci}]{text}')
        joined = ' || '.join(cells_text)
        print(f'  Row {ri}: {joined}')
    
    has_jinja = False
    for row in table.rows:
        for cell in row.cells:
            if '{{' in cell.text or '{%' in cell.text:
                has_jinja = True
                break
    if has_jinja:
        print(f'  ** HAS UNRESOLVED JINJA **')
    print()
