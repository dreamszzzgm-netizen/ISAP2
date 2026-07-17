# PMLA V2 Template Renderer Audit

**Date**: 2025-07-11
**File analyzed**: `backend/src/infrastructure/export/pmla_template_renderer.py`
**Schema**: `files/pmla_v2.schema.json`
**Test contexts**: `backend/scripts/test_pmla_v2_render.py`, `backend/scripts/full_render_and_pdf.py`

---

## 1. Architecture Summary

`PmlaTemplateRenderer` is a **thin pass-through wrapper** around `docxtpl.DocxTemplate.render()`. It:

1. Loads the `.docx` template
2. Calls `doc.render(context)` — passes the entire `context` dict as-is to Jinja2
3. Post-processes to remove Jinja artifacts (yellow highlights, empty control-tag lines)
4. Sets `w:updateFields` so TOC/NUMPAGES update on open
5. Second-pass XML cleanup removes stray `{{ }}` / `{% %}` tags from headers/footers

**The renderer itself computes zero fields, adds zero fallback values, formats zero dates/numbers, and validates zero inputs.** All intelligence lives in the caller who builds the context dict and in the Jinja2 template.

---

## 2. Keys the Renderer Reads from Context

The renderer does **not** read any specific key. It passes `context` to `doc.render(context)`, so Jinja2 resolves keys on demand from within the template. The renderer's own code never accesses `context["organization_full_name"]` or similar.

However, the **Jinja2 template** resolves the following keys (reconstructed from test contexts and `pmla_v2.schema.json`):

### Scalar Keys (28 total)

| # | Key | Description | Required by schema |
|---|-----|-------------|-------------------|
| 1 | `organization_full_name` | Full org name | YES |
| 2 | `organization_short_name` | Short org name | YES |
| 3 | `legal_address` | Legal address | YES |
| 4 | `inn` | INN (tax ID) | YES |
| 5 | `ogrn` | OGRN (registration ID) | YES |
| 6 | `phone` | Phone number | YES |
| 7 | `email` | Email | YES |
| 8 | `director_position_fullname` | Director position + full name | YES |
| 9 | `director_initials_surname` | Director initials + surname | YES |
| 10 | `director_initials_surname_full` | Director full name | YES |
| 11 | `deputy_chairman_fullname` | Deputy chairman full name | YES |
| 12 | `main_activity_description` | OKVED code + description | YES |
| 13 | `facility_name` | Facility name | YES |
| 14 | `facility_reg_number` | Facility registration number | YES |
| 15 | `facility_location` | Facility location | YES |
| 16 | `hazard_class` | Hazard class | YES |
| 17 | `hazardous_substances_info` | Hazardous substances info | YES |
| 18 | `hazard_characteristics_116fz` | Hazard characteristics per 116-FZ | YES |
| 19 | `contractor_organization_name` | PAS full name | YES |
| 20 | `contractor_organization_short_name` | PAS short name | YES |
| 21 | `contractor_agreement_date` | Contract date (string, DD.MM.YYYY) | YES |
| 22 | `gas_supplier_name` | Gas supplier name | YES |
| 23 | `total_hazardous_substance_quantity` | Total quantity (string, tons) | YES |
| 24 | `settlement_name` | Settlement name | **NO** — present in `full_render_and_pdf.py` only, absent from schema |
| 25-35 | `notification_*_phone` (11 keys) | Phone numbers for Table 17 | YES (per schema) |

### List Keys (9 total)

| # | Key | Schema table | Item fields | Required |
|---|-----|-------------|-------------|----------|
| 1 | `equipment_list` | Table 2 | `location`, `hazard_characteristic`, `device_name`, `specifications`, `process_codes` | YES |
| 2 | `substance_params` | Table 6 | `parameter`, `value` | NO |
| 3 | `equipment_scenario_links` | Table 7 | `equipment_name`, `scenario_codes`, `description`, `damaging_factors` | NO |
| 4 | `equipment_defects` | Table 8 | `equipment_name`, `defect`, `cause`, `source`, `scenario` | NO |
| 5 | `accident_scenarios` | Table 9 | `code`, `name`, `source`, `preconditions`, `signs`, `damaging_factors` | YES |
| 6 | `injury_history` | Table 10 | `year`, `incident_number`, `date`, `character`, `trauma`, `consequences`, `measures_percent` | NO |
| 7 | `accident_history` | Table 11 | `year`, `incident_number`, `date`, `character`, `trauma`, `consequences`, `measures_percent` | NO |
| 8 | `material_reserve` | Table 13 | `name`, `quantity`, `location`, `is_group_header`, `group_name` | NO |
| 9 | `countermeasures` | Table 18 | `scenario_label`, `signs`, `protection`, `technical_means`, `executors` | NO |

---

## 3. Fields the Renderer Computes Itself

**None.** The renderer is a pure pass-through. Every field in the context dict was assembled by the caller before reaching the renderer.

---

## 4. Fallback Values Added

**None by the renderer.** Fallback behavior is handled by:

- **Jinja2 template**: Uses `{% for %}` loops that produce no rows when lists are empty
- **Caller**: `full_render_and_pdf.py` creates `EMPTY_CTX` by replacing all list values with `[]` while keeping all scalar values from `FULL_CTX`
- **Test script**: `test_pmla_v2_render.py` manually sets lists to `[]`

---

## 5. List Names Expected

All 9 list variables consumed by Jinja2 `{% for %}` loops in the template:

1. `equipment_list`
2. `substance_params`
3. `equipment_scenario_links`
4. `equipment_defects`
5. `accident_scenarios`
6. `injury_history`
7. `accident_history`
8. `material_reserve`
9. `countermeasures`

---

## 6. Fields the Renderer Formats

**None.** All values are passed as raw strings. Specifically:

- **Dates**: Passed as plain strings (`"01.01.2026"`, `"15.12.2025"`). No `datetime` parsing or reformatting.
- **Numbers**: Passed as strings (`"0.5"` for quantity, `"4 шт."` for material quantities). No numeric conversion.
- **Phone numbers**: Passed as strings (`"+7 (495) 123-45-67"`). No normalization.

---

## 7. Required Fields

Per `pmla_v2.schema.json` `required_fields` (23 scalar fields):

```
organization_full_name, organization_short_name, legal_address, inn, ogrn,
phone, email, director_position_fullname, director_initials_surname,
director_initials_surname_full, deputy_chairman_fullname, main_activity_description,
facility_name, facility_reg_number, facility_location, hazard_class,
hazardous_substances_info, hazard_characteristics_116fz,
contractor_organization_name, contractor_organization_short_name,
contractor_agreement_date, gas_supplier_name, total_hazardous_substance_quantity
```

Per schema `required_tables`:
- `equipment_list` (min_items: 1)
- `accident_scenarios` (min_items: 1)
- All other lists: min_items: 0

**The renderer does NOT enforce any of these.** Missing keys cause Jinja2 `UndefinedError` at render time.

---

## 8. Exceptions Thrown

The renderer itself raises **no custom exceptions**. Error propagation:

| Error type | Source | When |
|-----------|--------|------|
| `jinja2.UndefinedError` | `docxtpl` / Jinja2 | Missing required variable in context |
| `jinja2.TemplateSyntaxError` | Jinja2 | Malformed template |
| `FileNotFoundError` | `Path(template_path)` | Template `.docx` not found at path |
| `zipfile.BadZipFile` | `_clean_xml_jinja` | Corrupt DOCX in XML cleanup pass |
| `ET.ParseError` | `_clean_xml_jinja` | Unparseable XML in document (caught, logged, skipped) |
| `OSError` | `_clean_xml_jinja` | Temp directory / file I/O failure |

No validation errors are raised for missing context keys — the renderer trusts the caller to provide a complete context.

---

## 9. Whether It Uses `pmla_v2.schema.json` for Validation

**No.** The schema file exists at `files/pmla_v2.schema.json` but is never imported or referenced by the renderer code. The renderer has zero validation logic. The schema is documentation only.

---

## 10. Whether It Passes Extra Keys to the Template

**Yes.** The renderer passes the **entire** `context` dict to `doc.render(context)`. Any extra keys the caller includes will be available in Jinja2 but ignored if the template doesn't reference them. No keys are stripped or filtered.

Extra keys present in test contexts but **not in the schema**:

| Key | Found in | Notes |
|-----|----------|-------|
| `settlement_name` | `full_render_and_pdf.py` | Present in one test context only; not in schema `required_fields` |

---

## 11. Keys in Renderer/Schema but Not Formed by Renderer

Since the renderer is a pass-through, **all keys** are "not formed by renderer." The schema defines keys the renderer never computes.

Additionally, `settlement_name` appears in `full_render_and_pdf.py` but is absent from both `pmla_v2.schema.json` and `test_pmla_v2_render.py` — suggesting it may be an extra template variable or an error in the test context.

---

## 12. Keys in Template but Not in Schema

Cannot be definitively determined without extracting the template DOCX and inspecting all `{% %}` / `{{ }}` tags. The schema notes:

- Tables 14, 15, 16 (forces and resources) are "partially parameterized" with `contractor_organization_name`, `contractor_organization_short_name`, and `gas_supplier_name`
- These scalar keys ARE in the schema, so no known gap

**Open question**: The template may reference additional variables not captured by the schema (e.g., the schema notes `settlement_name` is absent).

---

## 13. How Empty Lists Are Handled

**Jinja2 `{% for %}` loop produces zero iterations.** The template rows for the table body simply don't render, leaving only the header row.

Evidence from test contexts:
- `test_pmla_v2_render.py` (line 218-228): Sets `injury_history`, `accident_history`, and all other lists to `[]` for the "empty" render
- `full_render_and_pdf.py` (line 210): `{k: ([] if isinstance(v, list) else v) for k, v in FULL_CTX.items()}` — replaces all lists with `[]`
- Schema confirms `min_items: 0` for all lists except `equipment_list` and `accident_scenarios` (min_items: 1)

The renderer does **not** add placeholder rows, "no data" text, or any empty-state content. The Jinja template handles it by simply not producing table rows.

---

## 14. How Dates and Numbers Are Handled

**All values are strings.** No parsing, formatting, or type conversion:

- `contractor_agreement_date`: `"01.01.2026"` / `"15.12.2025"` — DD.MM.YYYY string format
- `total_hazardous_substance_quantity`: `"0.5"` — string, not float
- Material quantities: `"4 шт."`, `"2 компл."`, `"1 шт."` — pre-formatted strings with units
- Phone numbers: `"+7 (495) 123-45-67"`, `"112"`, `"112/03/103"` — strings

The renderer performs no locale-aware formatting, no `strftime`, no `Decimal` conversion.

---

## 15. Complete Mapping: Renderer Expectations vs Template Variables

### Scalar Variables

| Schema key | Test context present | Template usage (inferred) | Notes |
|-----------|---------------------|--------------------------|-------|
| `organization_full_name` | Both scripts | Title page, contract | Required |
| `organization_short_name` | Both scripts | Headers, contract | Required |
| `legal_address` | Both scripts | Contract, registration | Required |
| `inn` | Both scripts | Registration | Required |
| `ogrn` | Both scripts | Registration | Required |
| `phone` | Both scripts | Contact info | Required |
| `email` | Both scripts | Contact info | Required |
| `director_position_fullname` | Both scripts | Signature block | Required |
| `director_initials_surname` | Both scripts | Signature block | Required |
| `director_initials_surname_full` | Both scripts | Signature block | Required |
| `deputy_chairman_fullname` | Both scripts | Commission list | Required |
| `main_activity_description` | Both scripts | Organization info | Required |
| `facility_name` | Both scripts | Facility section | Required |
| `facility_reg_number` | Both scripts | Facility section | Required |
| `facility_location` | Both scripts | Facility section | Required |
| `hazard_class` | Both scripts | Hazard section | Required |
| `hazardous_substances_info` | Both scripts | Table 6 intro | Required |
| `hazard_characteristics_116fz` | Both scripts | Hazard section | Required |
| `contractor_organization_name` | Both scripts | Tables 14-16 | Required |
| `contractor_organization_short_name` | Both scripts | Tables 14-16 | Required |
| `contractor_agreement_date` | Both scripts | Contract | Required |
| `gas_supplier_name` | Both scripts | Tables 14-16 | Required |
| `total_hazardous_substance_quantity` | Both scripts | Table 6 | Required |
| `settlement_name` | `full_render_and_pdf.py` only | Unknown | **Not in schema** |

### Notification Phone Variables (11 keys)

| Schema key | Test context present |
|-----------|---------------------|
| `notification_chairman_phone` | Both scripts |
| `notification_deputy_phone` | Both scripts |
| `notification_edds_phone` | Both scripts |
| `notification_pasf_phone` | Both scripts |
| `notification_fire_phone` | Both scripts |
| `notification_ambulance_phone` | Both scripts |
| `notification_gas_phone` | Both scripts |
| `notification_electric_phone` | Both scripts |
| `notification_mchs_phone` | Both scripts |
| `notification_rostechnadzor_phone` | Both scripts |
| `notification_admin_phone` | Both scripts |

### Table Item Fields

| List key | Item field | Schema | Both test scripts |
|----------|-----------|--------|-------------------|
| `equipment_list` | `location` | Yes | Yes |
| `equipment_list` | `hazard_characteristic` | Yes | Yes |
| `equipment_list` | `device_name` | Yes | Yes |
| `equipment_list` | `specifications` | Yes | Yes |
| `equipment_list` | `process_codes` | Yes | Yes |
| `substance_params` | `parameter` | Yes | Yes |
| `substance_params` | `value` | Yes | Yes |
| `equipment_scenario_links` | `equipment_name` | Yes | Yes |
| `equipment_scenario_links` | `scenario_codes` | Yes | Yes |
| `equipment_scenario_links` | `description` | Yes | Yes |
| `equipment_scenario_links` | `damaging_factors` | Yes | Yes |
| `equipment_defects` | `equipment_name` | Yes | Yes |
| `equipment_defects` | `defect` | Yes | Yes |
| `equipment_defects` | `cause` | Yes | Yes |
| `equipment_defects` | `source` | Yes | Yes |
| `equipment_defects` | `scenario` | Yes | Yes |
| `accident_scenarios` | `code` | Yes | Yes |
| `accident_scenarios` | `name` | Yes | Yes |
| `accident_scenarios` | `source` | Yes | Yes |
| `accident_scenarios` | `preconditions` | Yes | Yes |
| `accident_scenarios` | `signs` | Yes | Yes |
| `accident_scenarios` | `damaging_factors` | Yes | Yes |
| `injury_history` | `year` | Yes | N/A (empty) |
| `injury_history` | `incident_number` | Yes | N/A (empty) |
| `injury_history` | `date` | Yes | N/A (empty) |
| `injury_history` | `character` | Yes | N/A (empty) |
| `injury_history` | `trauma` | Yes | N/A (empty) |
| `injury_history` | `consequences` | Yes | N/A (empty) |
| `injury_history` | `measures_percent` | Yes | N/A (empty) |
| `accident_history` | `year` | Yes | N/A (empty) |
| `accident_history` | `incident_number` | Yes | N/A (empty) |
| `accident_history` | `date` | Yes | N/A (empty) |
| `accident_history` | `character` | Yes | N/A (empty) |
| `accident_history` | `trauma` | Yes | N/A (empty) |
| `accident_history` | `consequences` | Yes | N/A (empty) |
| `accident_history` | `measures_percent` | Yes | N/A (empty) |
| `material_reserve` | `name` | Yes | Yes |
| `material_reserve` | `quantity` | Yes | Yes |
| `material_reserve` | `location` | Yes | Yes |
| `material_reserve` | `is_group_header` | Yes | Yes |
| `material_reserve` | `group_name` | Yes | Yes |
| `countermeasures` | `scenario_label` | Yes | Yes |
| `countermeasures` | `signs` | Yes | Yes |
| `countermeasures` | `protection` | Yes | Yes |
| `countermeasures` | `technical_means` | Yes | Yes |
| `countermeasures` | `executors` | Yes | Yes |

---

## 16. Key Findings and Risks

### No Validation Layer
The renderer performs zero input validation. Missing keys cause `jinja2.UndefinedError` at render time with no descriptive error message. The `pmla_v2.schema.json` exists but is not wired in.

### No Null/None Handling
All test contexts use empty lists `[]` for absent data. If a caller passes `None` for a list, Jinja2's `{% for %}` will raise `TypeError`. The renderer doesn't guard against this.

### Extra Key Injection
`settlement_name` is in `full_render_and_pdf.py` but not in the schema. The template may or may not use it. There is no documentation of which template variables the `.docx` actually references beyond what the schema describes.

### No Atomicity
The renderer saves to a temp ZIP and re-packages. If the process is interrupted mid-repackage, the output file may be corrupt. There's no write-to-temp-then-rename pattern.

### Post-processing Is Destructive
The `_clean_xml_jinja` method strips all `{{ }}` and `{% %}` patterns from the rendered XML — including legitimate content that happens to contain curly braces (e.g., JSON fragments, code samples). The regex is aggressive.

### Schema Coverage Gap
Schema `static_tables` includes tables 1, 2, 12, 14, 15, 16, 19, 20 — these are non-parameterized. Tables 14-16 are described as "partially parameterized" (using `contractor_organization_name`, `gas_supplier_name`), meaning the template likely has inline Jinja for these scalars mixed with static content.
