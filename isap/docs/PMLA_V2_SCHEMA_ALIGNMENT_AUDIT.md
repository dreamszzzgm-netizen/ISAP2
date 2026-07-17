# PMLA V2 Schema Alignment Audit — Final Report

**Date**: 2026-07-11
**Auditor**: agent-coordinator (compiled from 7 sub-agent audits)
**Files cross-referenced**:
- `files/pmla_v2.schema.json` (current schema — documentation-only, NOT JSON Schema)
- `files/pmla_v2_template.docx` (Jinja2 template via docxtpl)
- `backend/src/infrastructure/export/pmla_template_renderer.py`
- `backend/scripts/test_pmla_v2_render.py`, `full_render_and_pdf.py`, `verify_final_render.py`
- `backend/scripts/pmla_export_qa.py`, `visual_qa_deep.py`
- `docs/audit/pmla_v2.schema.proposed.json` (proposed JSON Schema Draft 2020-12)

---

## 1. Executive Summary

| Metric | Count |
|--------|-------|
| **Template keys** (scalar + list variables) | **45** (37 scalars + 8 list loops) |
| **Renderer/Context keys** (test context scripts) | **44** (43 common + 1 variant) |
| **Schema keys** (current `pmla_v2.schema.json`) | **43** (23 required_fields + 11 notification_phones + 9 required_tables) |
| **Full alignments** (present in all 4 sources) | **37** |
| **Name conflicts** | **6** (5 hardcoded phones + `financial_reserve` alias) |
| **Missing fields** (in template but NOT in schema) | **8** |
| **Type conflicts** (schema lacks type constraints) | **6** field-level issues |
| **Unused schema fields** (in schema/context but NOT in template) | **1** (`equipment_defects` loop absent from template) |

### Overall Verdict

> **BLOCKING SCHEMA MISMATCHES**
>
> The current `pmla_v2.schema.json` is not a valid JSON Schema, is missing 8 template fields, lacks type constraints on all 43 keys, and 5 notification phone keys are hardcoded in the template ignoring context values. The proposed schema (`pmla_v2.schema.proposed.json`) resolves most issues but the current system cannot be validated automatically.

---

## 2. Key Counts by Source

### 2.1 Template Keys (45 total)

**Scalar variables (37)** — extracted from `word/document.xml` and `word/header1.xml` via Jinja tag analysis:

| # | Key | Occurrences | In Schema? |
|---|-----|-------------|:----------:|
| 1 | `organization_short_name` | 64 | YES |
| 2 | `facility_name` | 36 | YES |
| 3 | `facility_reg_number` | 29 | YES |
| 4 | `contractor_organization_name` | 24 | YES |
| 5 | `gas_supplier_branch` | 12 | **NO** |
| 6 | `gas_supplier_name` | 10 | YES |
| 7 | `hazard_class` | 7 | YES |
| 8 | `dislocation_address` | 3 | **NO** |
| 9 | `facility_location` | 2 | YES |
| 10 | `settlement_name` | 2 | **NO** |
| 11 | `organization_full_name` | 2 | YES |
| 12 | `edds_district` | 2 | **NO** |
| 13 | `director_initials_surname` | 1 | YES |
| 14 | `contractor_organization_short_name` | 1 | YES |
| 15 | `legal_address` | 1 | YES |
| 16 | `inn` | 1 | YES |
| 17 | `ogrn` | 1 | YES |
| 18 | `phone` | 1 | YES |
| 19 | `email` | 1 | YES |
| 20 | `director_position_fullname` | 1 | YES |
| 21 | `main_activity_description` | 1 | YES |
| 22 | `hazardous_substances_info` | 1 | YES |
| 23 | `hazard_characteristics_116fz` | 1 | YES |
| 24 | `total_hazardous_substance_quantity` | 1 | YES |
| 25 | `settlement_district` | 1 | **NO** |
| 26 | `contractor_agreement_date` | 1 | YES |
| 27 | `director_initials_surname_full` | 1 | YES |
| 28 | `deputy_chairman_fullname` | 1 | YES |
| 29 | `notification_deputy_phone` | 1 | YES |
| 30 | `edds_name` | 1 | **NO** |
| 31 | `notification_fire_phone` | 1 | YES |
| 32 | `notification_ambulance_phone` | 1 | YES |
| 33 | `electric_company` | 1 | **NO** |
| 34 | `notification_electric_phone` | 1 | YES |
| 35 | `notification_mchs_phone` | 1 | YES |
| 36 | `local_admin` | 1 | **NO** |
| 37 | `notification_admin_phone` | 1 | YES |

**List loops (8)**:

| # | List Name | Loop Variable | In Schema? |
|---|-----------|---------------|:----------:|
| 1 | `equipment_list` | `eq` | YES |
| 2 | `substance_params` | `param` | YES |
| 3 | `equipment_scenario_links` | `link` | YES |
| 4 | `accident_scenarios` | `scenario` | YES |
| 5 | `injury_history` | `injury` | YES |
| 6 | `accident_history` | `accident` | YES |
| 7 | `material_reserve` | `item` | YES |
| 8 | `countermeasures` | `cm` | YES |

**NOTE**: `equipment_defects` has a loop tag `{%tr for defect in equipment_defects %}` defined in the schema but is **NOT present** in the current template DOCX.

### 2.2 Renderer/Context Keys (44 total)

All 3 test context scripts provide these **43 keys** in common:

- 23 required_fields scalars
- 11 notification phones
- 9 list keys (including `equipment_defects`)

Plus `settlement_name` in `full_render_and_pdf.py` only (1 extra key).

### 2.3 Schema Keys (43 total)

- `required_fields`: 23 scalar keys
- `notification_phones.fields`: 11 phone keys
- `required_tables`: 9 list keys
- `static_tables`: 8 table numbers (not keys, just metadata)
- `notes`: documentation array (not keys)

### 2.4 Proposed Schema Keys (50 total)

The proposed JSON Schema (`pmla_v2.schema.proposed.json`) adds 7 new required scalar keys:
`settlement_name`, `settlement_district`, `gas_supplier_branch`, `dislocation_address`, `edds_name`, `edds_district`, `electric_company`, `local_admin`

And uses `$defs` for reusable types: `HazardClass`, `DateStr`, `PhoneNumber`, `EquipmentItem`, `SubstanceParam`, `EquipmentScenarioLink`, `EquipmentDefect`, `AccidentScenario`, `IncidentRecord`, `MaterialReserveItem`, `Countermeasure`.

---

## 3. Alignment Table

### 3.1 Scalar Keys

| Key | Template | Renderer/Context | Schema | Status | Action |
|-----|:--------:|:----------------:|:------:|--------|--------|
| `organization_full_name` | YES (2×) | YES (all) | YES | **ALIGNED** | — |
| `organization_short_name` | YES (64×) | YES (all) | YES | **ALIGNED** | — |
| `legal_address` | YES (1×) | YES (all) | YES | **ALIGNED** | — |
| `inn` | YES (1×) | YES (all) | YES | **ALIGNED** | — |
| `ogrn` | YES (1×) | YES (all) | YES | **ALIGNED** | — |
| `phone` | YES (1×) | YES (all) | YES | **ALIGNED** | — |
| `email` | YES (1×) | YES (all) | YES | **ALIGNED** | — |
| `director_position_fullname` | YES (1×) | YES (all) | YES | **ALIGNED** | — |
| `director_initials_surname` | YES (1×) | YES (all) | YES | **ALIGNED** | — |
| `director_initials_surname_full` | YES (1×) | YES (all) | YES | **ALIGNED** | — |
| `deputy_chairman_fullname` | YES (1×) | YES (all) | YES | **ALIGNED** | — |
| `main_activity_description` | YES (1×) | YES (all) | YES | **ALIGNED** | — |
| `facility_name` | YES (36×) | YES (all) | YES | **ALIGNED** | — |
| `facility_reg_number` | YES (29×) | YES (all) | YES | **ALIGNED** | — |
| `facility_location` | YES (2×) | YES (all) | YES | **ALIGNED** | — |
| `hazard_class` | YES (7×) | YES (all) | YES | **TYPE_CONFLICT** | Schema untyped; should be `enum ["I","II","III","IV"]` |
| `hazardous_substances_info` | YES (1×) | YES (all) | YES | **ALIGNED** | — |
| `hazard_characteristics_116fz` | YES (1×) | YES (all) | YES | **ALIGNED** | — |
| `contractor_organization_name` | YES (24×) | YES (all) | YES | **ALIGNED** | — |
| `contractor_organization_short_name` | YES (1×) | YES (all) | YES | **ALIGNED** | — |
| `contractor_agreement_date` | YES (1×) | YES (all) | YES | **TYPE_CONFLICT** | Schema untyped; should be `DateStr` (DD.MM.YYYY) |
| `gas_supplier_name` | YES (10×) | YES (all) | YES | **ALIGNED** | — |
| `total_hazardous_substance_quantity` | YES (1×) | YES (all) | YES | **TYPE_CONFLICT** | Schema untyped; should be `number` |
| `settlement_name` | YES (2×) | partial (1 of 3 scripts) | NO | **TEMPLATE_ONLY** | Add to schema; fix test coverage |
| `settlement_district` | YES (1×) | NO | NO | **TEMPLATE_ONLY** | Dead variable — not in any test context; investigate |
| `gas_supplier_branch` | YES (12×) | NO | NO | **TEMPLATE_ONLY** | Add to schema; add to test contexts |
| `dislocation_address` | YES (3×) | NO | NO | **TEMPLATE_ONLY** | Add to schema; add to test contexts |
| `edds_name` | YES (1×) | NO | NO | **TEMPLATE_ONLY** | Add to schema; add to test contexts |
| `edds_district` | YES (2×) | NO | NO | **TEMPLATE_ONLY** | Dead variable — not in any test context; investigate |
| `electric_company` | YES (1×) | NO | NO | **TEMPLATE_ONLY** | Add to schema; add to test contexts |
| `local_admin` | YES (1×) | NO | NO | **TEMPLATE_ONLY** | Add to schema; add to test contexts |
| `notification_chairman_phone` | HARDCODED | YES (all) | YES | **NAME_CONFLICT** | Template hardcodes `+7 928 709-95-15`; ignores context |
| `notification_deputy_phone` | YES (1×) | YES (all) | YES | **ALIGNED** | — |
| `notification_edds_phone` | HARDCODED | YES (all) | YES | **NAME_CONFLICT** | Template hardcodes `112`; ignores context |
| `notification_pasf_phone` | HARDCODED | YES (all) | YES | **NAME_CONFLICT** | Template hardcodes `+7 (903) 495-75-57`; ignores context |
| `notification_fire_phone` | YES (1×) | YES (all) | YES | **ALIGNED** | — |
| `notification_ambulance_phone` | YES (1×) | YES (all) | YES | **ALIGNED** | — |
| `notification_gas_phone` | HARDCODED | YES (all) | YES | **NAME_CONFLICT** | Template hardcodes `+7 (86630) 4-18-68`; ignores context |
| `notification_electric_phone` | YES (1×) | YES (all) | YES | **ALIGNED** | — |
| `notification_mchs_phone` | YES (1×) | YES (all) | YES | **ALIGNED** | — |
| `notification_rostechnadzor_phone` | HARDCODED | YES (all) | YES | **NAME_CONFLICT** | Template hardcodes `+7 (928) 307-04-62`; ignores context |
| `notification_admin_phone` | YES (1×) | YES (all) | YES | **ALIGNED** | — |

### 3.2 List Keys

| Key | Template | Renderer/Context | Schema | Status | Action |
|-----|:--------:|:----------------:|:------:|--------|--------|
| `equipment_list` | YES | YES | YES | **ALIGNED** | — |
| `substance_params` | YES | YES | YES | **ALIGNED** | — |
| `equipment_scenario_links` | YES | YES | YES | **ALIGNED** | — |
| `equipment_defects` | **NO** | YES (context only) | YES | **UNUSED** | Template has no loop; data provided but never rendered |
| `accident_scenarios` | YES | YES | YES | **ALIGNED** | — |
| `injury_history` | YES | YES (always `[]`) | YES | **ALIGNED** | UNTESTED WITH DATA — only tested empty |
| `accident_history` | YES | YES (always `[]`) | YES | **ALIGNED** | UNTESTED WITH DATA — only tested empty |
| `material_reserve` | YES | YES | YES | **ALIGNED** | NAME_CONFLICT: `financial_reserve` alias in `pmla.py:81` |
| `countermeasures` | YES | YES | YES | **ALIGNED** | — |

---

## 4. Critical Mismatches

### C1: Current Schema Is NOT Valid JSON Schema

**Impact**: Cannot be validated by any JSON Schema tooling. No automated enforcement possible.

The file `pmla_v2.schema.json` uses custom keys (`required_fields`, `required_tables`, `notification_phones`, `static_tables`, `notes`) instead of standard JSON Schema properties (`type`, `properties`, `required`, `$defs`). Missing:
- `$schema` meta-reference
- `type: "object"` declaration
- `properties` definitions
- `required` array
- `additionalProperties` constraint
- Any type annotations

**Fix**: Adopt the proposed schema (`pmla_v2.schema.proposed.json`) which is Draft 2020-12 compliant.

### C2: 8 Template Fields Missing From Schema

These variables are referenced in the Jinja template but have NO definition in `pmla_v2.schema.json`:

| Field | Template Occurrences | Current Schema | Proposed Schema | Risk |
|-------|---------------------|----------------|-----------------|------|
| `gas_supplier_branch` | 12 | MISSING | Added as required | Template renders blank if absent |
| `dislocation_address` | 3 | MISSING | Added as required | Template renders blank if absent |
| `edds_name` | 1 | MISSING | Added as required | Template renders blank if absent |
| `edds_district` | 2 | MISSING | Added as required | Template renders blank if absent |
| `electric_company` | 1 | MISSING | Added as required | Template renders blank if absent |
| `local_admin` | 1 | MISSING | Added as required | Template renders blank if absent |
| `settlement_name` | 2 | MISSING | Added as required | Only 1 of 3 test scripts provides this |
| `settlement_district` | 1 | MISSING | Added as required | Dead variable — not in any test context |

### C3: 5 Notification Phones Hardcoded in Template

The template has hardcoded phone numbers for 5 notification rows, ignoring the context values provided by test scripts:

| Context Key | Hardcoded Value in Template | Expected Behavior |
|-------------|-----------------------------|-------------------|
| `notification_chairman_phone` | `+7 928 709-95-15` | Should use `{{ notification_chairman_phone }}` |
| `notification_edds_phone` | `112`, `+7 (86630) 4-00-06` | Should use `{{ notification_edds_phone }}` |
| `notification_pasf_phone` | `+7 (903) 495-75-57`, `+7 (903) 491-85-75` | Should use `{{ notification_pasf_phone }}` |
| `notification_gas_phone` | `+7 (86630) 4-18-68; 4-18-53` | Should use `{{ notification_gas_phone }}` |
| `notification_rostechnadzor_phone` | `+7 (928) 307-04-62`, etc. | Should use `{{ notification_rostechnadzor_phone }}` |

**Impact**: These values are baked into the template and cannot be changed per-organization without modifying the DOCX. The schema and test scripts both define these as parameterized keys, creating a false sense of configurability.

### C4: No Type Constraints on Any Field

The current schema describes all fields as Russian-language strings with no type information. The proposed schema adds:
- `hazard_class`: `enum ["I", "II", "III", "IV"]`
- `contractor_agreement_date`: `DateStr` pattern `^[0-9]{2}\.[0-9]{2}\.[0-9]{4}$`
- `total_hazardous_substance_quantity`: `number` with `minimum: 0`
- `inn`: pattern `^[0-9]{10,12}$`
- `ogrn`: pattern `^[0-9]{13,15}$`
- `email`: `format: "email"`
- `material_reserve[].is_group_header`: `boolean` (currently untyped)
- `injury_history[].year` / `accident_history[].year`: `integer` with range 2000-2099

---

## 5. Name Conflicts

| # | Key | Schema Name | Alternative Name | Location | Resolution |
|---|-----|-------------|------------------|----------|------------|
| N1 | `material_reserve` | `material_reserve` | `financial_reserve` | `pmla.py:81` — API router: `context.get("financial_reserve", context.get("material_reserve"))` | Pick canonical name; document alias |
| N2 | `material_reserve` | `material_reserve` | `material_reserves` (plural) | `enhanced_generator.py:251` | Pick canonical name |
| N3 | `notification_chairman_phone` | Schema/context: `notification_chairman_phone` | Template: hardcoded string | Template DOCX | Replace hardcoded with `{{ notification_chairman_phone }}` |
| N4 | `notification_edds_phone` | Schema/context: `notification_edds_phone` | Template: hardcoded string | Template DOCX | Replace hardcoded with `{{ notification_edds_phone }}` |
| N5 | `notification_pasf_phone` | Schema/context: `notification_pasf_phone` | Template: hardcoded string | Template DOCX | Replace hardcoded with `{{ notification_pasf_phone }}` |
| N6 | `notification_gas_phone` | Schema/context: `notification_gas_phone` | Template: hardcoded string | Template DOCX | Replace hardcoded with `{{ notification_gas_phone }}` |
| N7 | `notification_rostechnadzor_phone` | Schema/context: `notification_rostechnadzor_phone` | Template: hardcoded string | Template DOCX | Replace hardcoded with `{{ notification_rostechnadzor_phone }}` |

---

## 6. Type Conflicts

| # | Field | Current Schema | Expected Type | Proposed Schema | Risk |
|---|-------|----------------|---------------|-----------------|------|
| T1 | `hazard_class` | Untyped string | `enum ["I", "II", "III", "IV"]` | `HazardClass` enum | Any string accepted; PMLA regs require I-IV |
| T2 | `contractor_agreement_date` | Untyped string | `DateStr` (DD.MM.YYYY) | `DateStr` pattern | Could receive any format |
| T3 | `total_hazardous_substance_quantity` | Untyped string | `number` | `number` with `minimum: 0` | `"0.5"` passed as string |
| T4 | `inn` | Untyped string | 10-12 digit string | Pattern `^[0-9]{10,12}$` | No validation |
| T5 | `ogrn` | Untyped string | 13-15 digit string | Pattern `^[0-9]{13,15}$` | No validation |
| T6 | `material_reserve[].is_group_header` | Described as "boolean" in text | `boolean` | `boolean` | Renderer relies on truthiness |

---

## 7. Unused Schema Fields

| # | Key | In Schema | In Context | In Template | Impact |
|---|-----|:---------:|:----------:|:-----------:|--------|
| U1 | `equipment_defects` | YES (Table 8) | YES (all 3 test scripts, 13 items) | **NO** (loop not in template) | Data provided but never rendered; dead data path |

The `modify_table_8()` function in `modify_template_v2.py` was written to add this loop to the template, but the current `pmla_v2_template.docx` does not contain it.

---

## 8. Jinja Fields Without Schema Definition

These 8 scalar variables exist in the Jinja template but have NO definition in `pmla_v2.schema.json`:

| # | Variable | Occurrences | Loop Context | Proposed Schema | Status |
|---|----------|-------------|--------------|-----------------|--------|
| 1 | `gas_supplier_branch` | 12 | scalar | Required string | Template renders blank without data |
| 2 | `dislocation_address` | 3 | scalar | Required string | Template renders blank without data |
| 3 | `edds_name` | 1 | scalar | Required string | Template renders blank without data |
| 4 | `edds_district` | 2 | scalar | Required string | Template renders blank without data |
| 5 | `electric_company` | 1 | scalar | Required string | Template renders blank without data |
| 6 | `local_admin` | 1 | scalar | Required string | Template renders blank without data |
| 7 | `settlement_name` | 2 | scalar | Required string | Only 1 test script provides this |
| 8 | `settlement_district` | 1 | scalar | Required string | Dead variable — never in any test context |

---

## 9. Renderer Fields Without Template

| # | Key | Renderer/Context | Template | Impact |
|---|-----|:----------------:|:--------:|--------|
| 1 | `notification_chairman_phone` | Provided in context | Hardcoded in template | Context value ignored |
| 2 | `notification_edds_phone` | Provided in context | Hardcoded in template | Context value ignored |
| 3 | `notification_pasf_phone` | Provided in context | Hardcoded in template | Context value ignored |
| 4 | `notification_gas_phone` | Provided in context | Hardcoded in template | Context value ignored |
| 5 | `notification_rostechnadzor_phone` | Provided in context | Hardcoded in template | Context value ignored |
| 6 | `equipment_defects` (list) | Provided in context (13 items) | No `{% for %}` loop | Data never rendered |

---

## 10. Template Fields Without Renderer

These 8 template variables have no corresponding context value in any test script:

| # | Variable | Template Occurrences | In Any Test Script | Risk |
|---|----------|---------------------|--------------------|----|
| 1 | `gas_supplier_branch` | 12 | NO | Template renders blank |
| 2 | `dislocation_address` | 3 | NO | Template renders blank |
| 3 | `edds_name` | 1 | NO | Template renders blank |
| 4 | `edds_district` | 2 | NO | Template renders blank |
| 5 | `electric_company` | 1 | NO | Template renders blank |
| 6 | `local_admin` | 1 | NO | Template renders blank |
| 7 | `settlement_name` | 2 | 1 of 3 scripts | Partial coverage |
| 8 | `settlement_district` | 1 | NO | Dead variable |

---

## 11. Phone/Address Duplication

### 11.1 Phone Number Duplication

- **6 phone keys** are properly parameterized in both template and schema (`notification_deputy_phone`, `notification_fire_phone`, `notification_ambulance_phone`, `notification_electric_phone`, `notification_mchs_phone`, `notification_admin_phone`)
- **5 phone keys** are in schema/context but HARDCODED in template (see Section 5, N3-N7)
- **1 phone key** (`phone`) is the organization's main contact phone — separate from notification phones

### 11.2 Address Duplication

- `legal_address` — organization's legal address (schema required)
- `facility_location` — facility physical location (schema required)
- `dislocation_address` — forces/resources dislocation address (template only, not in schema)
- `settlement_name` / `settlement_district` — settlement geographic identifiers (template only, not in schema)

No direct data duplication detected — these represent distinct physical locations.

### 11.3 `injury_history` vs `accident_history` Structural Duplication

Both tables share **identical item_fields** (7 fields: `year`, `incident_number`, `date`, `character`, `trauma`, `consequences`, `measures_percent`). The only difference is semantic meaning (trauma characteristics vs. accident/incident history). The proposed schema uses a shared `IncidentRecord` `$defs` type for both.

---

## 12. Image Risks

The rendered DOCX files contain 13 images (mix of PNG, JPEG, WMF). All 13 images are preserved in both TEST and EMPTY renders with identical file sizes.

**Risk**: None detected. Images are static template assets, not dynamically generated. The `docxtpl` renderer preserves image parts correctly.

---

## 13. Empty List Risks

### 13.1 Current Behavior

All 3 test scripts correctly empty lists to `[]`:
- `test_pmla_v2_render.py`: Manual key-by-key override (fragile)
- `full_render_and_pdf.py`: Dict comprehension `{k: ([] if isinstance(v, list) else v) for k, v in FULL_CTX.items()}`
- `verify_final_render.py`: Same dict comprehension pattern

Jinja2 `{% for %}` loops produce zero iterations when lists are empty, leaving only header rows.

### 13.2 Risks

| # | Risk | Severity | Mitigation |
|---|------|----------|------------|
| R1 | `None` values for lists cause `TypeError` in Jinja2 `{% for %}` | HIGH | All scripts use `[]`, not `None` — but no runtime guard in renderer |
| R2 | `test_pmla_v2_render.py` manual empty list override is fragile | MEDIUM | Switch to dict comprehension pattern |
| R3 | Empty render still contains test data (`ООО ТестПром`, `ООО Спас`) | HIGH | Investigate empty render pipeline; ensure scalars are truly empty |
| R4 | `min_items` constraints in schema are never enforced | LOW | No runtime validation layer exists |
| R5 | Header in EMPTY file shows `СПК «ААА»` and `А34-00000-0001` | MEDIUM | Template defaults not replaced by empty context |

### 13.3 Rendered Empty File Audit Results

| Criterion | TEST | EMPTY |
|-----------|------|-------|
| Jinja artifacts | 0 | 0 |
| Table count (= 21) | 21 | 21 |
| Empty lists render correctly | Yes | Yes |
| Old data (А34-99999-0099) | Not found | Not found |
| Unfilled mandatory fields | Date placeholders only | Header placeholder + 72 whitespace cells |
| Test data in EMPTY | N/A | `ООО ТестПром` (65×), `ООО Спас` (24×), `Иванов И.И.` (4×) |
| Images preserved | 13 | 13 |

---

## 14. RAG Integration Risks

### 14.1 No Validation Layer

The renderer performs **zero input validation**:
- Missing keys cause `jinja2.UndefinedError` with no descriptive message
- No JSON Schema validation exists
- No context mapping validation exists
- Extra keys are silently passed through to Jinja2

### 14.2 QA Script Gaps

| Check | `pmla_export_qa.py` | `visual_qa_deep.py` | Gap |
|-------|:-------------------:|:-------------------:|-----|
| XML validity | YES | — | Adequate |
| Jinja in tables | YES | — | Tables only; misses paragraphs, headers, footers |
| Jinja in headers/footers | NO | NO | Significant gap |
| Old data check | YES (6 entries) | YES (9 entries) | Inconsistent deny-lists |
| JSON Schema validation | NO | NO | Missing entirely |
| Context mapping validation | NO | NO | Missing entirely |
| Table count = 21 | YES | — | Hardcoded |
| Empty list rendering | PARTIAL (no-op) | — | Always passes for header+data tables |
| Row counts match context | NO | — | Claimed in docstring, not implemented |
| Yellow highlighting check | NO | — | Claimed in docstring, not implemented |
| Pagination validation | NO | NO | Missing entirely |

### 14.3 Docstring Overpromises

`pmla_export_qa.py` claims 7 checks but only implements 5 adequately:
- **Row counts match context**: NOT IMPLEMENTED
- **No yellow highlighting**: NOT IMPLEMENTED

---

## 15. Proposed Canonical Mapping

The proposed schema (`pmla_v2.schema.proposed.json`) resolves the following:

### 15.1 Structural Fixes

| Issue | Current | Proposed | Status |
|-------|---------|----------|--------|
| Not valid JSON Schema | Custom DSL | JSON Schema Draft 2020-12 | FIXED |
| No `$schema` | Missing | Added | FIXED |
| No `type` declaration | Missing | `"type": "object"` | FIXED |
| No `properties` | Custom keys | Standard `properties` | FIXED |
| No `required` array | Implicit | Explicit required list (37 items) | FIXED |
| No `additionalProperties` | Missing | `false` | FIXED |
| No `$defs` | Missing | 11 reusable type definitions | FIXED |

### 15.2 Type Fixes

| Field | Current | Proposed | Fix |
|-------|---------|----------|-----|
| `hazard_class` | Untyped string | `enum ["I", "II", "III", "IV"]` | PMLA regulation compliance |
| `inn` | Untyped string | Pattern `^[0-9]{10,12}$` | Russian INN validation |
| `ogrn` | Untyped string | Pattern `^[0-9]{13,15}$` | Russian OGRN validation |
| `email` | Untyped string | `format: "email"` | Standard email validation |
| `contractor_agreement_date` | Untyped string | `DateStr` (DD.MM.YYYY pattern) | Date format enforcement |
| `total_hazardous_substance_quantity` | Untyped string | `number` with `minimum: 0` | Numeric validation |
| `material_reserve[].is_group_header` | Untyped | `boolean` | Type safety |
| `injury_history[].year` | Untyped | `integer` (2000-2099) | Year range validation |

### 15.3 Naming Fixes

| Current | Proposed | Fix |
|---------|----------|-----|
| `equipment_defects[].source` | `equipment_defects[].location` | Semantic clarity; `source` collides with data-origin meaning |
| Shared `IncidentRecord` | Used for both `injury_history` and `accident_history` | Eliminates structural duplication |

### 15.4 New Fields Added

| Field | Type | Added To |
|-------|------|----------|
| `settlement_name` | string | required |
| `settlement_district` | string | required |
| `gas_supplier_branch` | string | required |
| `dislocation_address` | string | required |
| `edds_name` | string | required |
| `edds_district` | string | required |
| `electric_company` | string | required |
| `local_admin` | string | required |

---

## 16. Recommended Fix Order

### Phase 1: Critical (Blocking Integration)

| # | Fix | Effort | Impact |
|---|-----|--------|--------|
| 1 | Adopt proposed JSON Schema (`pmla_v2.schema.proposed.json`) as the canonical schema | LOW | Enables IDE validation and automated testing |
| 2 | Replace 5 hardcoded phone numbers in template with `{{ notification_*_phone }}` Jinja tags | LOW | Enables per-organization phone configuration |
| 3 | Add 8 missing template variables to schema `required` | LOW | Documents the full contract |
| 4 | Add type constraints (`hazard_class` enum, `DateStr`, `number`, `inn`/`ogrn` patterns) | MEDIUM | Prevents malformed data at render time |

### Phase 2: High (Data Integrity)

| # | Fix | Effort | Impact |
|---|-----|--------|--------|
| 5 | Wire `pmla_v2.schema.json` into renderer for runtime validation | MEDIUM | Catches missing/wrong keys before render |
| 6 | Unify `material_reserve` / `financial_reserve` naming | LOW | Eliminates ambiguity in API router |
| 7 | Add test data for `injury_history` and `accident_history` | LOW | Catches template bugs in these loops |
| 8 | Add test context for `gas_supplier_branch`, `dislocation_address`, `edds_name`, `electric_company`, `local_admin` | LOW | Tests 5 currently-untested template variables |
| 9 | Remove `equipment_defects` from test contexts OR apply `modify_table_8()` to template | MEDIUM | Eliminates dead data path |

### Phase 3: Medium (QA Coverage)

| # | Fix | Effort | Impact |
|---|-----|--------|--------|
| 10 | Extend Jinja artifact check to paragraphs, headers, footers | LOW | Catches Jinja remnants in non-table content |
| 11 | Fix empty render to not include test data (`ООО ТестПром`) | MEDIUM | Empty renders should be truly empty |
| 12 | Implement row count validation (claimed in QA docstring) | MEDIUM | Catches data/render mismatches |
| 13 | Unify deny-lists between `pmla_export_qa.py` (6) and `visual_qa_deep.py` (9) | LOW | Consistent old data detection |

### Phase 4: Low (Cleanup)

| # | Fix | Effort | Impact |
|---|-----|--------|--------|
| 14 | Investigate `settlement_district` and `edds_district` dead variables | LOW | Either parameterize in template or remove |
| 15 | Rename `material_reserve[].is_group_header` — ensure boolean type at render | LOW | Type safety |
| 16 | Move `notes` array from schema to separate documentation | LOW | Clean schema |

---

## 17. Alignment Summary by Status

| Status | Count | Keys |
|--------|-------|------|
| **ALIGNED** | 37 | 23 required_fields + 6 notification phones + 8 list keys |
| **TEMPLATE_ONLY** | 8 | `gas_supplier_branch`, `dislocation_address`, `edds_name`, `edds_district`, `electric_company`, `local_admin`, `settlement_name`, `settlement_district` |
| **NAME_CONFLICT** | 6 | 5 hardcoded phones + `financial_reserve` alias |
| **TYPE_CONFLICT** | 6 | `hazard_class`, `contractor_agreement_date`, `total_hazardous_substance_quantity`, `inn`, `ogrn`, `material_reserve[].is_group_header` |
| **UNUSED** | 1 | `equipment_defects` (in context/schema but no template loop) |
| **REVIEW_REQUIRED** | 2 | `injury_history`, `accident_history` (never tested with data) |

---

## 18. Final Verdict

### **BLOCKING SCHEMA MISMATCHES**

**Rationale**:

1. The current schema is **not a valid JSON Schema** — cannot be validated by any tooling.
2. **8 template variables** have no schema definition — the schema does not describe the full data contract.
3. **5 notification phone values** are hardcoded in the template, making the schema/context contract a lie — these keys are "parameterized" in code but baked into the DOCX.
4. **Zero type constraints** exist on any of the 43 schema keys.
5. The `equipment_defects` list is provided by all test contexts but **never rendered** — a dead data path.
6. The rendered EMPTY file contains **test data remnants** (`ООО ТестПром`, `ООО Спас`) — the empty render pipeline is broken.
7. QA scripts **claim checks they don't implement** (row counts, yellow highlighting) and **miss critical coverage** (headers, footers, paragraphs for Jinja artifacts).

**The proposed schema (`pmla_v2.schema.proposed.json`) resolves issues 1-4 and should be adopted as the canonical schema.** Issues 5-7 require separate template and pipeline fixes.

**Recommended next step**: Adopt the proposed schema, then execute Phase 1 fixes (template phone parameterization + missing field additions) to reach **MINOR FIXES REQUIRED** status.
