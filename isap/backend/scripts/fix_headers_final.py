"""Fix header XML: remove » and consolidate registration number."""
import zipfile, shutil, os
from lxml import etree

TEMPLATE = r"D:\Project ISAP\isap\isap\files\pmla_v2_template.docx"
NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

with zipfile.ZipFile(TEMPLATE, "r") as z:
    data = z.read("word/header1.xml")

root = etree.fromstring(data)

# Step 1: Remove standalone » runs
for p_elem in root.iter(f"{{{NS}}}p"):
    p_text = "".join((t.text or "") for t in p_elem.iter(f"{{{NS}}}t"))
    if "organization_short_name" not in p_text:
        continue
    runs = list(p_elem.findall(f"{{{NS}}}r"))
    for run in runs:
        t = run.find(f"{{{NS}}}t")
        if t is not None and t.text and t.text.strip() == "»":
            p_elem.remove(run)

# Step 2: Consolidate split registration number
for p_elem in root.iter(f"{{{NS}}}p"):
    p_text = "".join((t.text or "") for t in p_elem.iter(f"{{{NS}}}t"))
    if "facility_reg_number" not in p_text:
        continue
    for t_elem in p_elem.iter(f"{{{NS}}}t"):
        if t_elem.text and "А34" in t_elem.text:
            t_elem.text = "{{ facility_reg_number }}"
            run = t_elem.getparent()
            parent = run.getparent()
            next_run = run.getnext()
            while next_run is not None:
                next_t = next_run.find(f"{{{NS}}}t")
                if next_t is not None and next_t.text and (next_t.text.isdigit() or next_t.text.startswith("-")):
                    saved = next_run.getnext()
                    parent.remove(next_run)
                    next_run = saved
                else:
                    break

# Serialize and save
new_data = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
xml_str = new_data.decode("utf-8")

has_old = "СПК" in xml_str or "ААА" in xml_str or "А34-00000" in xml_str
has_jinja = "organization_short_name" in xml_str and "facility_reg_number" in xml_str
print("Old data:", has_old)
print("Jinja placeholders:", has_jinja)

shutil.copy2(TEMPLATE, TEMPLATE + ".bak4")
with zipfile.ZipFile(TEMPLATE, "r") as zin:
    with zipfile.ZipFile(TEMPLATE + ".tmp4", "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            if item.filename == "word/header1.xml":
                zout.writestr(item, new_data)
            else:
                zout.writestr(item, zin.read(item.filename))

os.remove(TEMPLATE)
os.rename(TEMPLATE + ".tmp4", TEMPLATE)
print("Fixed:", TEMPLATE)
