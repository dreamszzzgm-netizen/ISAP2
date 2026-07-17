"""Fix headers by replacing text in individual XML runs."""
import zipfile
import os
import shutil
import re

TEMPLATE = r"D:\Project ISAP\isap\isap\files\pmla_v2_template.docx"

with zipfile.ZipFile(TEMPLATE, 'r') as zin:
    data = zin.read('word/header1.xml').decode('utf-8')

# Find and replace in individual <w:t> elements
# Pattern: <w:t>TEXT</w:t>
def replace_in_wt(content, old, new):
    """Replace text within <w:t> elements."""
    pattern = r'(<w:t[^>]*>)([^<]*?)(' + re.escape(old) + r')([^<]*?)(</w:t>)'
    def replacer(m):
        prefix = m.group(2)
        match = m.group(3)
        suffix = m.group(4)
        replacement = match.replace(old, new)
        return f'{m.group(1)}{prefix}{replacement}{suffix}{m.group(5)}'
    return re.sub(pattern, replacer, content)

# Apply replacements
data2 = data
data2 = replace_in_wt(data2, 'СПК «', '{{ organization_short_name }} ')
data2 = replace_in_wt(data2, 'ААА', '')
data2 = replace_in_wt(data2, 'А34-00000-0001', '{{ facility_reg_number }}')

# Clean up double spaces
data2 = re.sub(r'  +', ' ', data2)

# Save back to DOCX
shutil.copy2(TEMPLATE, TEMPLATE + '.bak')
with zipfile.ZipFile(TEMPLATE, 'r') as zin:
    with zipfile.ZipFile(TEMPLATE + '.tmp', 'w', zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            if item.filename == 'word/header1.xml':
                zout.writestr(item, data2.encode('utf-8'))
            else:
                zout.writestr(item, zin.read(item.filename))

# Replace original with fixed
os.remove(TEMPLATE)
os.rename(TEMPLATE + '.tmp', TEMPLATE)

# Verify
with zipfile.ZipFile(TEMPLATE, 'r') as z:
    fixed = z.read('word/header1.xml').decode('utf-8')
    has_old = 'СПК' in fixed or 'ААА' in fixed or 'А34-00000' in fixed
    has_new = 'organization_short_name' in fixed or 'facility_reg_number' in fixed
    print(f"Old data present: {has_old}")
    print(f"New placeholders: {has_new}")
    print(f"Saved: {TEMPLATE}")
