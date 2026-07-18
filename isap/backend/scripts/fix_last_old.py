"""Fix the last remaining Чегемский."""
from docx import Document

doc = Document(r"D:\Project ISAP\isap\isap\files\pmla_v2_template.docx")
p = doc.paragraphs[311]
print(f"Before: {p.text[:200]}")

for i, run in enumerate(p.runs):
    if "Чегемский" in run.text:
        run.text = run.text.replace("Чегемский а.", "{{ settlement_district }}")
        print(f"  Fixed run {i}")

print(f"After: {p.text[:200]}")
doc.save(r"D:\Project ISAP\isap\isap\files\pmla_v2_template.docx")
print("Saved")
