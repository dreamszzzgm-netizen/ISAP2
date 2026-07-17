# PMLA v2 Rendered DOCX Audit Report

**Date:** 2026-07-11
**Auditor:** agent-rendered-docx-audit
**Files analyzed:**
- `files/pmla_v2_rendered_test.docx` (12,477,979 bytes, 33 ZIP entries)
- `files/pmla_v2_rendered_empty.docx` (12,476,216 bytes, 33 ZIP entries)

---

## Executive Summary

| Criterion | TEST | EMPTY | Verdict |
|-----------|------|-------|---------|
| Jinja artifacts | 0 | 0 | **PASS** |
| XML validity (all 19 XML files) | Valid | Valid | **PASS** |
| Table count (= 21) | 21 | 21 | **PASS** |
| Headers/footers preserved | 2+2 | 2+2 | **PASS** |
| Empty lists render correctly | Yes | Yes | **PASS** |
| Old data: А34-99999-0099 | Not found | Not found | **PASS** |
| Old data: СПК | Legitimate | Legitimate | **PASS** |
| Old data: Чегем | 2 (legit) | 27 (template defaults) | **WARN** |
| Images preserved | 13 | 13 (identical sizes) | **PASS** |
| Leftover loop markers | 0 | 0 | **PASS** |
| Unfilled mandatory fields | Date placeholders only | Header placeholder + 72 whitespace cells | **FAIL** |
| Test data in EMPTY | N/A | "ООО ТестПром", "ООО Спас", "Иванов" | **FAIL** |

---

## 1. Jinja Artifact Check

| Pattern | TEST doc | TEST all XML | EMPTY doc | EMPTY all XML |
|---------|----------|-------------|-----------|---------------|
| `{{` | 0 | 0 | 0 | 0 |
| `}}` | 0 | 0 | 0 | 0 |
| `{%` | 0 | 0 | 0 | 0 |
| `%}` | 0 | 0 | 0 | 0 |

**Result: PASS** — No Jinja template artifacts found in any XML file within either DOCX.

---

## 2. XML Validity

All 19 XML files + 1 `[Content_Types].xml` in both DOCX archives parsed successfully with `xml.etree.ElementTree.fromstring()`. No parse errors.

Files validated per DOCX:
- `[Content_Types].xml`, `_rels/.rels`, `docProps/app.xml`, `docProps/core.xml`
- `word/document.xml`, `word/endnotes.xml`, `word/fontTable.xml`
- `word/footer1.xml`, `word/footer2.xml`, `word/footnotes.xml`
- `word/header1.xml`, `word/header2.xml`, `word/numbering.xml`
- `word/settings.xml`, `word/styles.xml`, `word/stylesWithEffects.xml`
- `word/webSettings.xml`, `word/theme/theme1.xml`, `word/_rels/document.xml.rels`

**Result: PASS**

---

## 3. Table Count and Row Analysis

Both files contain exactly **21 tables**. Row counts per table:

| Table # | Description (approx) | Rows (TEST) | Rows (EMPTY) | Delta | Notes |
|---------|----------------------|-------------|--------------|-------|-------|
| 1 | Approval block (СОГЛАСОВАНО/УТВЕРЖДАЮ) | 6 | 6 | 0 | Static |
| 2 | Revision history | 43 | 43 | 0 | Static |
| 3 | Abbreviations list | 22 | 22 | 0 | Static |
| 4 | Abbreviations cont. | 19 | 19 | 0 | Static |
| 5 | Parameters (Наименование/Значение) | 16 | 16 | 0 | Static |
| 6 | OPO equipment list | 4 | 3 | -1 | Dynamic: 1 data row in TEST |
| 7 | Hazardous substance parameters | 2 | 1 | -1 | Dynamic: 1 data row in TEST |
| 8 | Equipment elements | 2 | 1 | -1 | Dynamic: 1 data row in TEST |
| 9 | Equipment defects list | 14 | 14 | 0 | Static (14 pre-defined items) |
| 10 | Accident scenarios | 2 | 1 | -1 | Dynamic: 1 data row in TEST |
| 11 | Accident history (year 1) | 1 | 1 | 0 | Header only (both) |
| 12 | Accident history (year 2) | 1 | 1 | 0 | Header only (both) |
| 13 | Accident details | 10 | 10 | 0 | Static |
| 14 | Resources/materials | 3 | 1 | -2 | Dynamic: 2 data rows in TEST |
| 15 | Forces & resources purpose | 5 | 5 | 0 | Static |
| 16 | Forces composition | 5 | 5 | 0 | Static |
| 17 | Forces deployment location | 5 | 5 | 0 | Static |
| 18 | Notification list | 14 | 14 | 0 | Static (pre-defined list) |
| 19 | PAZ methods | 2 | 1 | -1 | Dynamic: 1 data row in TEST |
| 20 | Incident types | 4 | 4 | 0 | Static |
| 21 | Signatures list | 44 | 44 | 0 | Static |
| **Total** | | **224** | **217** | **-7** | |

**Row difference analysis:** The EMPTY file has 7 fewer rows, all from tables that contain dynamic data (equipment, scenarios, resources). In the EMPTY version, these tables contain only their header row — no empty/placeholder data rows. This is correct behavior for an "empty" render.

**Result: PASS** — Tables render correctly; empty lists show headers only with no broken rows.

---

## 4. Headers and Footers

| File | Exists | Content |
|------|--------|---------|
| `word/header1.xml` | Both | Main document header with title, org name, reg number |
| `word/header2.xml` | Both | Blank (space only) |
| `word/footer1.xml` | Both | Page number "68" |
| `word/footer2.xml` | Both | Page number "69" |

**Header1 content — TEST:**
```
План мероприятий по локализации и ликвидации последствий аварий на ОПО
«Сеть газопотребления
ООО «КавказГазСервис»
рег. № А34-99999-0001
```

**Header1 content — EMPTY:**
```
План мероприятий по локализации и ликвидации последствий аварий на ОПО
«Сеть газопотребления
СПК «ААА»                          ← UNFILLED PLACEHOLDER
рег. № А34-00000-0001              ← UNFILLED PLACEHOLDER
```

**Result: FAIL (EMPTY file)** — Header in EMPTY file contains unfilled placeholders:
- Organization name: `СПК «ААА»` instead of actual org name
- Registration number: `А34-00000-0001` instead of actual reg number

---

## 5. Empty Lists Rendering

Tables with dynamic data (6, 7, 8, 10, 14, 19) in the EMPTY file contain **only their header row**. No empty/placeholder data rows, no broken formatting, no whitespace-only cells in these tables.

**Result: PASS** — Empty lists render correctly as header-only tables.

---

## 6. Old Data Check

### А34-99999-0099 (old registration number)
- TEST: **Not found**
- EMPTY: **Not found**

### СПК
- TEST: 2 occurrences — `Председатель СПК «АЛБИР»` (in signatures table, Table 21)
- EMPTY: 2 occurrences — same content

These are **legitimate references** to a council chairman ("Председатель СПК «АЛБИР»"), not template placeholders.

### Чегем
- TEST: 2 occurrences — `Чегемские Районные` (legitimate geographic name)
- EMPTY: 27 occurrences — all are **template default addresses**:
  - `ООО «Газпром» филиал в Чегемском районе` (×8)
  - `ул. им. Героя России Кярова А.С., 69, г. Чегем, Чегемский муниципальный район, КБР` (×3)
  - `ул. им. Героя России Кярова А.С., 62, г. Чегем...` (×2)
  - `ул. им. Героя России Кярова А.С., 8, г. Чегем...` (×2)
  - `ЕДДС Чегемского района` (×3)
  - `Чегемские Районные Электрические Сети` (×1)
  - `Местная администрация сельского поселения Чегем Второй` (×1)
  - `в Чегемском районе` (×4)

**Result: WARN (EMPTY file)** — Чегем references in EMPTY are template default data. While not "old data" per se, they represent hardcoded template defaults that should be replaced with actual data during rendering. In a truly empty render, these should either be blank or use generic placeholders.

---

## 7. Unfilled Mandatory Fields

### Date fields (both files)
158 underscore patterns (`___...`) found in both files — these are standard Russian date placeholders (`«____»_______________________2026 г.`). This is expected for an unfilled template.

### Header placeholders (EMPTY only)
- Organization name: `СПК «ААА»` — **should be actual org name**
- Registration number: `А34-00000-0001` — **should be actual reg number**

### Whitespace-only cells (EMPTY only)
72 cells contain only whitespace. These are in static tables (approval block, revision history, etc.) where the cell structure is preserved but no data is filled. This is expected behavior.

### Test data remnants (EMPTY only) ⚠️ CRITICAL
The EMPTY file contains **test data** that should not be present:
- `ООО ТестПром` — 65 occurrences (body text)
- `ООО Спас` — 24 occurrences (organization name)
- `Иванов И.И.` — 4 occurrences (person name in signatures)
- `г. ГАЗ` — 2 occurrences (city name)

The TEST file correctly uses `ООО «КавказГазСервис»` (65 occurrences) instead.

**Result: FAIL** — EMPTY file contains test data remnants instead of truly empty values.

---

## 8. Image Preservation

Both files contain identical 13 images with identical file sizes:

| Image | Type | Size (bytes) |
|-------|------|-------------|
| image1.png | PNG | 1,298,079 |
| image2.png | PNG | 2,593 |
| image3.png | PNG | 252,388 |
| image4.jpeg | JPEG | 499,559 |
| image5.jpg | JPEG | 110,204 |
| image6.png | PNG | 761,437 |
| image7.png | PNG | 970,193 |
| image8.wmf | WMF | 578 |
| image9.jpg | JPEG | 717,144 |
| image10.jpg | JPEG | 234,635 |
| image11.jpg | JPEG | 518,435 |
| image12.jpg | JPEG | 633,008 |
| image13.png | PNG | 148,302 |

**Result: PASS** — All 13 images preserved with identical sizes.

---

## 9. Leftover Loop Markers

| Pattern | TEST | EMPTY |
|---------|------|-------|
| `endfor` | 0 | 0 |
| `endif` | 0 | 0 |
| `for ` | 0 | 0 |

**Result: PASS** — No leftover Jinja loop/control flow markers.

---

## Issues Summary

### CRITICAL

1. **EMPTY file contains test data** — `ООО ТестПром` (65×), `ООО Спас` (24×), `Иванов И.И.` (4×) appear in the EMPTY render. These are test-specific values that should be blank or use generic placeholders in an empty render.

### HIGH

2. **EMPTY header has unfilled placeholders** — `СПК «ААА»` and `А34-00000-0001` in header1.xml are clearly template defaults, not actual rendered values. The empty render should either leave these blank or use descriptive placeholders like `[Наименование организации]`.

### MEDIUM

3. **Чегем template defaults in EMPTY** — 27 hardcoded address references to Чегем district appear in the EMPTY file. These are template defaults (e.g., "ООО «Газпром» филиал в Чегемском районе") that should be replaced with actual data or left blank.

### LOW

4. **Date placeholders** — 158 underscore patterns are expected for an unfilled template but worth noting for completeness.

---

## Recommendations

1. **Fix EMPTY render logic**: Investigate why the empty render produces "ООО ТестПром" instead of truly empty values. The render pipeline may be falling back to test data when no actual data is provided.
2. **Fix header rendering for empty case**: The header1.xml should use generic placeholders (e.g., `[Наименование организации]`, `[Рег. №]`) instead of `СПК «ААА»` / `А34-00000-0001`.
3. **Replace Чегем defaults**: Template default addresses should be parameterized and replaced during rendering, not hardcoded.
