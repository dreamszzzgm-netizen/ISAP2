# PMLA v2 Export QA Script Audit

**Date**: 2026-07-11
**Scripts analyzed**:
- `backend/scripts/pmla_export_qa.py` (212 lines)
- `backend/scripts/visual_qa_deep.py` (111 lines)

---

## 1. Which XML files are actually checked?

**`pmla_export_qa.py` `check_xml_validity()`** iterates all ZIP entries ending in `.xml` that do NOT start with `_`:

```python
if name.endswith(".xml") and not name.startswith("_"):
```

This covers:
- `word/document.xml` (main body)
- `word/styles.xml`, `word/numbering.xml`, `word/settings.xml`
- `word/_rels/document.xml.rels` (skipped — starts with `_`)
- `[Content_Types].xml`
- `docProps/core.xml`, `docProps/app.xml`

**Not checked**:
- `word/_rels/*.rels` (skipped by underscore filter — these are relationship files, not content XML, so this is reasonable)
- Any `.rels` files under `word/` that start with `_`

**Verdict**: All content-bearing XML files are checked. Relationship metadata is skipped intentionally. This is adequate.

---

## 2. Does it search Jinja in ALL parts of DOCX (paragraphs, tables, headers, footers)?

**NO.** `check_no_jinja_artifacts()` only searches **table cells**:

```python
for ti, table in enumerate(doc.tables):
    for ri, row in enumerate(table.rows):
        for ci, cell in enumerate(row.cells):
            if re.search(JINJA_RE, cell.text):
```

**Not searched**:
- **Paragraphs** outside tables (e.g., body text, preambles)
- **Headers** (`section.header`, `section.first_page_header`, `section.even_page_header`)
- **Footers** (`section.footer`, `section.first_page_footer`, `section.even_page_footer`)
- **Table cell paragraphs with formatting** — `cell.text` concatenates all text but is correct for Jinja detection
- **Headers/footers inside table cells** (rare but possible)

**`visual_qa_deep.py`** adds PDF-level Jinja checking but does NOT add DOCX header/footer checking.

**Verdict**: Significant gap. If the template has Jinja tags in headers/footers or standalone paragraphs, they will be missed.

---

## 3. Does it check old values?

**YES — with caveats.**

**`pmla_export_qa.py`**:
- Has `OLD_DATA_DENYLIST` (6 entries: test organizations, test person names, test network names)
- `check_old_data()` searches all table cells in the DOCX

**`visual_qa_deep.py`**:
- Has `OLD_DATA` (9 entries — superset, adds `СПК «ААА»`, `г. Чегем`, `Чегемский`)
- Searches all PDF pages

**Gaps**:
- Old data check does NOT search **paragraphs outside tables** in the DOCX
- Old data check does NOT search **headers/footers** in either script
- The two scripts have **inconsistent deny-lists** (`visual_qa_deep.py` has 3 extra entries)
- No check for partially-matched old values (e.g., old phone numbers, old INN codes, old addresses that aren't in the deny-list)

**Verdict**: Partially implemented. The deny-list approach is brittle — it only catches known strings, not structural old-data patterns.

---

## 4. Does it validate JSON Schema?

**NO.** Neither script performs JSON Schema validation. There is:
- No `jsonschema` import
- No schema file loading
- No validation of context data against a schema

**Verdict**: Missing entirely. If context JSON is malformed, the template will render with wrong data and only old-data checks would catch it indirectly.

---

## 5. Does it validate mapping?

**NO.** Neither script validates:
- Context key mapping to template variables
- Whether all required template variables are supplied
- Whether extra context keys are silently ignored
- Whether value types match expected types

**Verdict**: Missing entirely.

---

## 6. Does it check empty lists?

**YES — partially.**

`check_empty_lists_render()` checks that specific loop-tables (`[5,6,7,8,9,10,11,13,18]`) have at least 1 row in the empty render.

**Gaps**:
- Only checks for `>= 1` row — does not verify that exactly header rows exist (could have accidental data rows)
- Hardcoded table indices — will break if template structure changes
- Does NOT check that empty lists render with correct column counts
- Does NOT check that `{{ for item in items }}` loops produce zero data rows (only that at least 1 row exists, which is always true due to header)

**Verdict**: Minimal implementation. The check is effectively a no-op since tables with headers always have `>= 1` row even with empty lists.

---

## 7. Does it check table count?

**YES.** `check_table_count()` verifies exactly 21 tables:

```python
if len(doc.tables) != 21:
    issues.append(f"Expected 21 tables, found {len(doc.tables)}")
```

**Verdict**: Implemented correctly. Simple and effective.

---

## 8. Does it check DOCX ZIP integrity?

**YES — partially.** `check_xml_validity()` opens the DOCX as a ZIP and attempts `ET.fromstring()` on each XML file. If the ZIP is corrupted, the outer `except Exception` catches it.

**Gaps**:
- Does not check for missing required files (`word/document.xml`, `[Content_Types].xml`)
- Does not verify ZIP CRC checksums
- Does not check for zero-byte files
- Does not verify ZIP compression is valid (could pass corrupted-but-parseable data)

**Verdict**: Adequate for most failure modes. A corrupted ZIP will almost always fail `ZipFile()` or `ET.fromstring()`.

---

## 9. Does it check PDF?

**`pmla_export_qa.py`**: **NO.** Only checks DOCX.

**`visual_qa_deep.py`**: **YES** — checks:
- Page orientation (landscape detection)
- Old data in PDF text
- New data presence (positive assertion)
- Jinja artifacts in PDF text
- Key page content sampling

**`visual_qa_deep.py` gaps**:
- No page count validation
- No text extraction completeness check
- No table structure verification in PDF
- No font/encoding check (corrupted Cyrillic)
- Hardcoded file path (not parameterized)

**Verdict**: Partial. PDF visual QA exists in separate script but has no schema/structure validation.

---

## 10. Does it check pagination?

**NO.** Neither script validates:
- Expected total page count
- Page breaks at correct locations
- Landscape pages at expected positions (visual_qa_deep.py detects landscape pages but does not assert they are correct)
- Page numbering consistency

**Verdict**: Missing entirely.

---

## 11. What checks are claimed in the report but missing from code?

The module docstring of `pmla_export_qa.py` claims 7 checks:

| # | Claimed Check | In Code? | Notes |
|---|--------------|----------|-------|
| 1 | No unprocessed Jinja tags | **PARTIAL** | Tables only; misses paragraphs, headers, footers |
| 2 | Valid XML inside DOCX | **YES** | Adequate |
| 3 | File opens without errors | **YES** | Adequate |
| 4 | Row counts match context | **NO** | Not implemented anywhere |
| 5 | Empty lists render correctly | **PARTIAL** | Checks `>= 1 row` but not correctness |
| 6 | No yellow highlighting | **NO** | Not implemented anywhere |
| 7 | All 21 tables present | **YES** | Adequate |

**Specific missing implementations**:
- **Row counts match context**: No function verifies that rendered row counts match the input data arrays
- **No yellow highlighting**: No check for highlighting/color in DOCX XML (would require checking `w:highlight` or `w:shd` elements)

---

## Checklist Summary

| Check | Implemented? | Notes |
|-------|:------------:|-------|
| XML validity (all .xml in ZIP) | **YES** | Skips `_`-prefixed files (intentional) |
| Jinja tags in tables | **YES** | Table cells only |
| Jinja tags in paragraphs | **NO** | Not searched |
| Jinja tags in headers | **NO** | Not searched |
| Jinja tags in footers | **NO** | Not searched |
| Jinja tags in PDF | **YES** | Via `visual_qa_deep.py` |
| File opens as DOCX | **YES** | `python-docx` load |
| DOCX ZIP integrity | **PARTIAL** | Catches corruption, not missing files |
| Table count = 21 | **YES** | Hardcoded, correct |
| Old data check (DOCX tables) | **YES** | 6-entry deny-list |
| Old data check (PDF) | **YES** | 9-entry deny-list (inconsistent) |
| Old data check (paragraphs) | **NO** | Not searched |
| Old data check (headers/footers) | **NO** | Not searched |
| Empty list rendering | **PARTIAL** | `>= 1 row` check only |
| Row counts match context | **NO** | Claimed in docstring, not implemented |
| Yellow highlighting check | **NO** | Claimed in docstring, not implemented |
| JSON Schema validation | **NO** | Not implemented |
| Context mapping validation | **NO** | Not implemented |
| PDF page count | **NO** | Not checked |
| Page orientation validation | **PARTIAL** | Detected but not asserted |
| Pagination correctness | **NO** | Not implemented |
| New data presence (positive) | **YES** | Via `visual_qa_deep.py` (PDF only) |
| Font/encoding check | **NO** | Not implemented |

---

## Key Findings

1. **Docstring overpromises**: 2 of 7 claimed checks (row counts, yellow highlighting) are not implemented.
2. **Jinja search is table-only**: Headers, footers, and standalone paragraphs are never scanned for leftover Jinja tags.
3. **No data validation layer**: JSON Schema validation and context mapping checks are absent — wrong data will pass all QA if it doesn't match the deny-list.
4. **Inconsistent deny-lists**: `pmla_export_qa.py` (6 entries) vs `visual_qa_deep.py` (9 entries) — the PDF script catches more old data than the DOCX script.
5. **Empty list check is a no-op**: Checking `>= 1 row` will always pass for tables with headers, even when the data list is empty.
6. **No pagination validation**: Neither script verifies page count, page breaks, or landscape page placement.
7. **Two separate scripts, no integration**: DOCX QA and PDF QA run independently with no unified report or shared configuration.
