# PMLA v2 Test Context Audit

## Files Analyzed

| File | Context Name | Purpose |
|------|-------------|---------|
| `backend/scripts/test_pmla_v2_render.py` | `FULL_CONTEXT` / `EMPTY_CONTEXT` | Basic render test |
| `backend/scripts/full_render_and_pdf.py` | `FULL_CTX` / `EMPTY_CTX` | Full render + PDF + visual QA |
| `backend/scripts/verify_final_render.py` | `ctx` | Verify template Jinja loops |

## 1. Scalar Variables — Comparison Across Files

| Key | test_pmla_v2_render | full_render_and_pdf | verify_final_render | In Template |
|-----|:---:|:---:|:---:|:---:|
| `organization_full_name` | filled | filled | filled | YES |
| `organization_short_name` | filled | filled | filled | YES |
| `legal_address` | filled | filled | filled | YES |
| `inn` | filled | filled | filled | YES |
| `ogrn` | filled | filled | filled | YES |
| `phone` | filled | filled | filled | YES |
| `email` | filled | filled | filled | YES |
| `director_position_fullname` | filled | filled | filled | YES |
| `director_initials_surname` | filled | filled | filled | YES |
| `director_initials_surname_full` | filled | filled | filled | YES |
| `deputy_chairman_fullname` | filled | filled | filled | YES |
| `main_activity_description` | filled | filled | filled | YES |
| `facility_name` | filled | filled | filled | YES |
| `facility_reg_number` | filled | filled | filled | YES |
| `facility_location` | filled | filled | filled | YES |
| `hazard_class` | filled | filled | filled | YES |
| `hazardous_substances_info` | filled | filled | filled | YES |
| `hazard_characteristics_116fz` | filled | filled | filled | YES |
| `contractor_organization_name` | filled | filled | filled | YES |
| `contractor_organization_short_name` | filled | filled | filled | YES |
| `contractor_agreement_date` | filled | filled | filled | YES |
| `gas_supplier_name` | filled | filled | filled | YES |
| `total_hazardous_substance_quantity` | filled | filled | filled | YES |
| `settlement_name` | **MISSING** | filled | **MISSING** | YES |
| `gas_supplier_branch` | **MISSING** | **MISSING** | **MISSING** | YES |
| `dislocation_address` | **MISSING** | **MISSING** | **MISSING** | YES |
| `dislocation_district` | **MISSING** | **MISSING** | **MISSING** | YES |
| `edds_name` | **MISSING** | **MISSING** | **MISSING** | YES |
| `edds_district` | **MISSING** | **MISSING** | **MISSING** | YES |
| `electric_company` | **MISSING** | **MISSING** | **MISSING** | YES |
| `local_admin` | **MISSING** | **MISSING** | **MISSING** | YES |
| `settlement_district` | **MISSING** | **MISSING** | **MISSING** | YES |
| `notification_chairman_phone` | filled | filled | filled | **NO** (hardcoded) |
| `notification_deputy_phone` | filled | filled | filled | YES |
| `notification_edds_phone` | filled | filled | filled | **NO** (hardcoded) |
| `notification_pasf_phone` | filled | filled | filled | **NO** (hardcoded) |
| `notification_fire_phone` | filled | filled | filled | YES |
| `notification_ambulance_phone` | filled | filled | filled | YES |
| `notification_gas_phone` | filled | filled | filled | **NO** (hardcoded) |
| `notification_electric_phone` | filled | filled | filled | YES |
| `notification_mchs_phone` | filled | filled | filled | YES |
| `notification_rostechnadzor_phone` | filled | filled | filled | **NO** (hardcoded) |
| `notification_admin_phone` | filled | filled | filled | YES |

## 2. Array Variables — Template Loop vs Test Context

| Array Key | In Template | In test_pmla_v2_render | In full_render_and_pdf | In verify_final_render |
|-----------|:-----------:|:---------------------:|:---------------------:|:---------------------:|
| `equipment_list` | YES | 3 items | 3 items | 3 items |
| `substance_params` | YES | 8 items | 8 items | 2 items |
| `equipment_scenario_links` | YES | 3 items | 3 items | 1 item |
| `equipment_defects` | **NO** | 13 items | 13 items | 1 item |
| `accident_scenarios` | YES | 6 items | 6 items | 1 item |
| `injury_history` | YES | 0 items | 0 items | 0 items |
| `accident_history` | YES | 0 items | 0 items | 0 items |
| `material_reserve` | YES | 20 items | 20 items | 2 items |
| `countermeasures` | YES | 5 items | 5 items | 1 item |

### Array Item Fields — Template vs Test Context

**equipment_list** (template var: `eq`)
- Template uses: `location`, `hazard_characteristic`, `device_name`, `specifications`, `process_codes`
- Test context provides: `location`, `hazard_characteristic`, `device_name`, `specifications`, `process_codes`
- Status: **MATCH**

**substance_params** (template var: `param`)
- Template uses: `parameter`, `value`
- Test context provides: `parameter`, `value`
- Status: **MATCH**

**equipment_scenario_links** (template var: `link`)
- Template uses: `equipment_name`, `scenario_codes`, `description`, `damaging_factors`
- Test context provides: `equipment_name`, `scenario_codes`, `description`, `damaging_factors`
- Status: **MATCH**

**equipment_defects** — NOT IN TEMPLATE
- Test context provides: `equipment_name`, `defect`, `cause`, `source`, `scenario`
- Template does NOT have a loop for this array
- Status: **DEAD DATA** — provided by all 3 test contexts but never rendered

**accident_scenarios** (template var: `scenario`)
- Template uses: `code`, `name`, `source`, `preconditions`, `signs`, `damaging_factors`
- Test context provides: `code`, `name`, `source`, `preconditions`, `signs`, `damaging_factors`
- Status: **MATCH**

**injury_history** (template var: `injury`)
- Template uses: `year`, `incident_number`, `date`, `character`, `trauma`, `consequences`, `measures_percent`
- Test context provides: `[]` (empty — never tested with data)
- Status: **UNTESTED WITH DATA**

**accident_history** (template var: `accident`)
- Template uses: `year`, `incident_number`, `date`, `character`, `trauma`, `consequences`, `measures_percent`
- Test context provides: `[]` (empty — never tested with data)
- Status: **UNTESTED WITH DATA**

**material_reserve** (template var: `item`)
- Template uses: `is_group_header`, `group_name`, `name`, `quantity`, `location`
- Test context provides: `is_group_header`, `group_name`, `name`, `quantity`, `location`
- Status: **MATCH**

**countermeasures** (template var: `cm`)
- Template uses: `scenario_label`, `signs`, `protection`, `technical_means`, `executors`
- Test context provides: `scenario_label`, `signs`, `protection`, `technical_means`, `executors`
- Status: **MATCH**

## 3. Empty Context Analysis

### How Each File Creates Empty Context

| File | Method | What Gets Emptied |
|------|--------|-------------------|
| `test_pmla_v2_render.py` | Manual override: `EMPTY_CONTEXT["key"] = []` for 9 specific lists | Lists only; scalars unchanged |
| `full_render_and_pdf.py` | Dict comprehension: `{k: ([] if isinstance(v, list) else v) for k, v in FULL_CTX.items()}` | All lists; scalars unchanged |
| `verify_final_render.py` | Dict comprehension: `{k: ([] if isinstance(v, list) else v) for k, v in ctx.items()}` | All lists; scalars unchanged |

### Empty Context Coverage

All three approaches correctly:
1. Empty all 9 list-type keys
2. Keep all scalar values populated (no blank strings)
3. Use `[]` for empty lists (not `None` or missing key)

**Issue**: `test_pmla_v2_render.py` manually lists 9 keys to empty. If a new list key is added, it must be manually added to the empty override. The dict comprehension approach in the other two files is more robust.

### Empty Context Does NOT Test

- **Missing keys** (key absent entirely vs key present with empty list)
- **`None` values** (all scalars are non-None strings)
- **Partial emptiness** (e.g., some notification phones empty, others filled — only tested in `verify_final_render.py` where some phones are `''`)
- **`equipment_defects` not in template** — emptying it has no effect since the template doesn't use it

## 4. Hardcoded Phone Numbers in Template (Table 17)

The template has 5 phone numbers that are NOT parameterized despite test contexts providing values for them:

| Row | Hardcoded Value | Test Context Key | Status |
|-----|----------------|-----------------|--------|
| Chairman | `+7 928 709-95-15` | `notification_chairman_phone` | IGNORED |
| EDDS | `112`, `+7 (86630) 4-00-06` | `notification_edds_phone` | IGNORED |
| PASF | `+7 (903) 495-75-57`, `+7 (903) 491-85-75` | `notification_pasf_phone` | IGNORED |
| Gas supplier | `+7 (86630) 4-18-68; 4-18-53` | `notification_gas_phone` | IGNORED |
| Rostechnadzor | `+7 (928) 307-04-62`, `+7 (8793)-34-64-24`, `+7 (8662) 91-99-33` | `notification_rostechnadzor_phone` | IGNORED |

These were supposed to be parameterized by `agent_d_forces.py` / `modify_template_v2.py`, but the current `pmla_v2_template.docx` still contains hardcoded values for these rows.

## 5. Template Variables Missing From ALL Test Contexts

These variables exist in the template but are absent from all three test files:

| Variable | Used In | Notes |
|----------|---------|-------|
| `gas_supplier_branch` | Table 17 (gas supplier row) | Inserted by `replace_remaining_old.py` |
| `dislocation_address` | Table 17 (gas supplier row) | Inserted by `replace_remaining_old.py` |
| `dislocation_district` | Not found in any template tag | Dead variable |
| `edds_name` | Table 17 (EDDS row) | Inserted by `replace_remaining_old.py` |
| `edds_district` | Not found in any template tag | Dead variable |
| `electric_company` | Table 17 (electric company row) | Inserted by `replace_remaining_old.py` |
| `local_admin` | Table 17 (admin row) | Inserted by `replace_remaining_old.py` |
| `settlement_name` | Paragraph text (only in `full_render_and_pdf.py`) | Partial coverage |
| `settlement_district` | Not found in any template tag | Dead variable |

**Note**: `dislocation_district`, `edds_district`, and `settlement_district` are dead variables — they were inserted by `replace_remaining_old.py` XML replacements but never appear in the actual template XML as `{{ ... }}` tags. The XML replacements replaced static text but the resulting template still doesn't use these as Jinja variables.

## 6. Findings Summary

### CRITICAL
1. **`equipment_defects` is dead data** — All 3 test contexts provide it, but the template has NO loop for it. The `modify_table_8()` function in `modify_template_v2.py` was written but never applied to the current template.
2. **5 notification phones are hardcoded** — `notification_chairman_phone`, `notification_edds_phone`, `notification_pasf_phone`, `notification_gas_phone`, `notification_rostechnadzor_phone` are provided by test contexts but ignored by the template.
3. **9 template variables have no test coverage** — `gas_supplier_branch`, `dislocation_address`, `edds_name`, `electric_company`, `local_admin`, and several `*_district` variables are never tested.

### MODERATE
4. **`injury_history` and `accident_history` are never tested with data** — Only tested as empty lists. If the loop template has bugs, they won't be caught.
5. **`settlement_name` inconsistency** — Only present in `full_render_and_pdf.py`, missing from the other two test files.

### MINOR
6. **`test_pmla_v2_render.py` empty context is fragile** — Manual list override means new array keys won't be auto-emptied.
7. **`dislocation_district`, `edds_district`, `settlement_district` are dead variables** — Referenced in `replace_remaining_old.py` XML replacements but never appear as Jinja tags in the template.
