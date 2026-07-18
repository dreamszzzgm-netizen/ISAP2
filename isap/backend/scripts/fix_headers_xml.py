"""Fix headers by directly modifying XML inside DOCX ZIP."""
import zipfile
import os
import shutil
import re

TEMPLATE = r"D:\Project ISAP\isap\isap\files\pmla_v2_template.docx"
TEMP_DIR = r"D:\Project ISAP\isap\isap\files\_temp_docx"

# Extract DOCX
if os.path.exists(TEMP_DIR):
    shutil.rmtree(TEMP_DIR)
os.makedirs(TEMP_DIR)

with zipfile.ZipFile(TEMPLATE, 'r') as zin:
    zin.extractall(TEMP_DIR)

# Find and fix all header XML files
fixed_files = []
for root, dirs, files in os.walk(TEMP_DIR):
    for fname in files:
        if fname.startswith("header") and fname.endswith(".xml"):
            fpath = os.path.join(root, fname)
            with open(fpath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if 'СПК' in content or 'ААА' in content:
                # Replace hardcoded org name with Jinja placeholder
                content = content.replace('СПК «ААА»', '{{ organization_short_name }}')
                content = content.replace('А34-00000-0001', '{{ facility_reg_number }}')
                
                with open(fpath, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                fixed_files.append(fname)
                print(f"  Fixed: {fname}")

# Repackage as DOCX
shutil.copy2(TEMPLATE, TEMPLATE + '.bak')
with zipfile.ZipFile(TEMPLATE, 'w', zipfile.ZIP_DEFLATED) as zout:
    for root, dirs, files in os.walk(TEMP_DIR):
        for file in files:
            file_path = os.path.join(root, file)
            arcname = os.path.relpath(file_path, TEMP_DIR)
            zout.write(file_path, arcname)

shutil.rmtree(TEMP_DIR)
print(f"\nFixed {len(fixed_files)} header files")
print(f"Saved: {TEMPLATE}")
