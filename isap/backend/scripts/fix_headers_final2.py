"""Final header fix: replace А34 split runs with placeholder."""
import zipfile, shutil, os
from lxml import etree

TEMPLATE = r"D:\Project ISAP\isap\isap\files\pmla_v2_template.docx"
NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

with zipfile.ZipFile(TEMPLATE, "r") as z:
    data = z.read("word/header1.xml")

root = etree.fromstring(data)

for p_elem in root.iter(f"{{{NS}}}p"):
    for t_elem in p_elem.iter(f"{{{NS}}}t"):
        if t_elem.text and "А34-" in t_elem.text:
            t_elem.text = "{{ facility_reg_number }}"
            run = t_elem.getparent()
            parent = run.getparent()
            nxt = run.getnext()
            while nxt is not None:
                nxt_t = nxt.find(f"{{{NS}}}t")
                if nxt_t is not None and nxt_t.text:
                    txt = nxt_t.text.strip()
                    if txt.isdigit() or txt == "-000" or txt == "-0001":
                        saved = nxt.getnext()
                        parent.remove(nxt)
                        nxt = saved
                    else:
                        break
                else:
                    break

new_data = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
xml_str = new_data.decode("utf-8")

has_old = "СПК" in xml_str or "ААА" in xml_str or "А34-00000" in xml_str
has_jinja = "organization_short_name" in xml_str and "facility_reg_number" in xml_str
print(f"Old data: {has_old}, Jinja: {has_jinja}")

shutil.copy2(TEMPLATE, TEMPLATE + ".bak6")
with zipfile.ZipFile(TEMPLATE, "r") as zin:
    with zipfile.ZipFile(TEMPLATE + ".tmp6", "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            if item.filename == "word/header1.xml":
                zout.writestr(item, new_data)
            else:
                zout.writestr(item, zin.read(item.filename))
os.remove(TEMPLATE)
os.rename(TEMPLATE + ".tmp6", TEMPLATE)
print("Saved:", TEMPLATE)
