"""Deep visual QA — check parameterized content, landscape pages, old data."""
import fitz  # PyMuPDF
import os

PDF = r"D:\Project ISAP\isap\isap\files\pmla_v2_rendered_test.pdf"

# Old data that should NOT appear
OLD_DATA = [
    "СПК «ААА»",
    "СПК «Тест»",
    "Тестовая сеть газопотребления",
    "А34-99999-0099",
    "ООО «ТестГаз»",
    "ООО «ТестСпас»",
    "Тестов Тест Тестович",
    "г. Чегем",
    "Чегемский",
]

# Expected new data
NEW_DATA = [
    "КавказГазСервис",
    "Кумахов Ахмед Абдуллаевич",
    "Кумахов А.А.",
    "Батов Руслан",
    "0703123456",
    "Нальчик",
    "Газпром газораспределение КБР",
]

doc = fitz.open(PDF)
print(f"PDF: {PDF}")
print(f"Total pages: {len(doc)}")

# 1. Check all pages for landscape
print("\n=== Page orientations ===")
landscape_pages = []
for i in range(len(doc)):
    page = doc[i]
    rect = page.rect
    if rect.width > rect.height:
        landscape_pages.append(i + 1)
print(f"Landscape pages: {landscape_pages}")

# 2. Check for old data
print("\n=== Old data check ===")
old_found = []
for i in range(len(doc)):
    text = doc[i].get_text()
    for old in OLD_DATA:
        if old in text:
            old_found.append((i + 1, old))
if old_found:
    for page, data in old_found:
        print(f"  Page {page}: OLD DATA '{data}'")
else:
    print("  No old data found")

# 3. Check for expected new data
print("\n=== New data check ===")
new_found = []
for i in range(len(doc)):
    text = doc[i].get_text()
    for new in NEW_DATA:
        if new in text:
            new_found.append((i + 1, new))
            break  # One match per page is enough
if new_found:
    for page, data in new_found[:10]:
        print(f"  Page {page}: contains '{data}'")
    if len(new_found) > 10:
        print(f"  ... and {len(new_found) - 10} more pages with new data")
else:
    print("  WARNING: No new data found!")

# 4. Check for Jinja artifacts in PDF
print("\n=== Jinja artifact check ===")
import re
jinja_pattern = re.compile(r'\{[%{].*?[%}]\}')
jinja_found = []
for i in range(len(doc)):
    text = doc[i].get_text()
    matches = jinja_pattern.findall(text)
    if matches:
        for m in matches:
            jinja_found.append((i + 1, m[:50]))
if jinja_found:
    for page, match in jinja_found[:5]:
        print(f"  Page {page}: {match}")
else:
    print("  No Jinja artifacts in PDF")

# 5. Sample specific pages
print("\n=== Key page samples ===")
key_pages = [
    (1, "Approval sheet"),
    (2, "Title page"),
]
for page_num, desc in key_pages:
    if page_num <= len(doc):
        text = doc[page_num - 1].get_text()[:300].replace('\n', ' | ')
        print(f"  Page {page_num} ({desc}): {text[:200]}...")

# 6. Check landscape pages have table content
print("\n=== Landscape page content ===")
for pg in landscape_pages[:3]:
    text = doc[pg - 1].get_text()[:200].replace('\n', ' | ')
    print(f"  Page {pg}: {text[:150]}...")

doc.close()
print("\nDone!")
