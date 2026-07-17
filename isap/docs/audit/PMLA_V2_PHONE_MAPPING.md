# PMLA v2 — Canonical Phone Mapping

> Generated 2026-07-11 from template, schema, renderer, and test scripts.

## Summary

| Metric | Count |
|--------|-------|
| Total phone fields | 11 |
| HARDCODED in template (not Jinja) | 5 |
| JINJA placeholders (parameterized) | 6 |

**Critical finding:** 5 phone fields are physically hardcoded in the `.docx` template.
Context values passed to `PmlaTemplateRenderer.render()` for these keys are **silently ignored**.
Only the 6 Jinja-placeholder phones are actually rendered from context.

---

## Complete Mapping

### HARDCODED phones (template-only, context ignored)

| # | canonical_key | source | template_status | renderer_key | api_field | fallback_value | required |
|---|---------------|--------|-----------------|-------------|-----------|---------------|----------|
| 1 | `notification_chairman_phone` | organization | **HARDCODED** | *(same)* | `notification_phones.notification_chairman_phone` | `+7 928 709-95-15` | false |
| 2 | `notification_edds_phone` | edds | **HARDCODED** | *(same)* | `notification_phones.notification_edds_phone` | `112` | false |
| 3 | `notification_pasf_phone` | pasf | **HARDCODED** | *(same)* | `notification_phones.notification_pasf_phone` | `+7 (903) 495-75-57` | false |
| 4 | `notification_gas_phone` | gas | **HARDCODED** | *(same)* | `notification_phones.notification_gas_phone` | `+7 (86630) 4-18-68` | false |
| 5 | `notification_rostechnadzor_phone` | rostechnadzor | **HARDCODED** | *(same)* | `notification_phones.notification_rostechnadzor_phone` | `+7 (928) 307-04-62` | false |

### JINJA phones (parameterized, rendered from context)

| # | canonical_key | source | template_status | renderer_key | api_field | fallback_value | required |
|---|---------------|--------|-----------------|-------------|-----------|---------------|----------|
| 6 | `notification_deputy_phone` | organization | JINJA | *(same)* | `notification_phones.notification_deputy_phone` | `''` (empty) | false |
| 7 | `notification_fire_phone` | fire | JINJA | *(same)* | `notification_phones.notification_fire_phone` | `''` (empty) | false |
| 8 | `notification_ambulance_phone` | ambulance | JINJA | *(same)* | `notification_phones.notification_ambulance_phone` | `''` (empty) | false |
| 9 | `notification_electric_phone` | electric | JINJA | *(same)* | `notification_phones.notification_electric_phone` | `''` (empty) | false |
| 10 | `notification_mchs_phone` | mchs | JINJA | *(same)* | `notification_phones.notification_mchs_phone` | `''` (empty) | false |
| 11 | `notification_admin_phone` | admin | JINJA | *(same)* | `notification_phones.notification_admin_phone` | `''` (empty) | false |

---

## Detail: HARDCODED Phones

These 5 phones are typed literally into `pmla_v2_template.docx` (Table 17 / notification list).
The `agent_d_forces.py` script originally attempted to replace all 11 hardcoded phones with Jinja
placeholders, but 5 replacements failed, leaving the values baked into the template.

**Implication:** Even when the renderer receives a different value in the context dict for these keys,
the rendered output will always show the hardcoded phone. The context value is dead code.

### 1. `notification_chairman_phone`
- **Hardcoded value:** `+7 928 709-95-15`
- **Organization:** ОПО chairman
- **Note:** Same value used across all test scripts (`test_pmla_v2_render.py`, `full_render_and_pdf.py`).
  `verify_final_render.py` passes `+7 999 000-00-00` but it has no effect.

### 2. `notification_edds_phone`
- **Hardcoded value:** `112`
- **Organization:** ЕДДС (Единая дежурно-диспетчерская служба)
- **Note:** Universal emergency number. No variation across test scripts.

### 3. `notification_pasf_phone`
- **Hardcoded value:** `+7 (903) 495-75-57`
- **Organization:** ПАСФ (Противоаварийная служба фонда)
- **Note:** The original template also contained an alternate number `+7 (903) 491-85-75` that was
  part of the same cell but separated by `|`. The Jinja replacement only targets the first number.

### 4. `notification_gas_phone`
- **Hardcoded value:** `+7 (86630) 4-18-68`
- **Organization:** Gas supply organization (Газоснабжающая организация)
- **Note:** Original template also contained alternate `4-18-53` separated by `|`.

### 5. `notification_rostechnadzor_phone`
- **Hardcoded value:** `+7 (928) 307-04-62`
- **Organization:** Ростехнадзор
- **Note:** Original template also contained alternates `+7 (8793)-34-64-24` and `+7 (8662) 91-99-33`
  separated by `|`.

---

## Detail: JINJA Phones

These 6 phones are parameterized with `{{ notification_xxx_phone }}` (or with `| default('', true)`)
in the template. The renderer substitutes the value from the context dict.

### 6. `notification_deputy_phone`
- **Source:** Organization deputy chairman
- **Test value:** `+7 906 881-07-07`
- **Template Jinja:** `{{ notification_deputy_phone | default('', true) }}`

### 7. `notification_fire_phone`
- **Source:** Fire department (Пожарная часть)
- **Test value:** `+7 (8663) 04-14-91`
- **Template Jinja:** `{{ notification_fire_phone | default('', true) }}`

### 8. `notification_ambulance_phone`
- **Source:** Ambulance (Скорая помощь)
- **Test value:** `112/03/103`
- **Template Jinja:** `{{ notification_ambulance_phone | default('', true) }}`
- **Note:** Some test scripts use `103` instead of `112/03/103`.

### 9. `notification_electric_phone`
- **Source:** Electric utility (Электросети)
- **Test value:** `+7 (86630) 4-27-70`
- **Template Jinja:** `{{ notification_electric_phone | default('', true) }}`

### 10. `notification_mchs_phone`
- **Source:** МЧС (Ministry of Emergency Situations)
- **Test value:** `+7 (8662) 39-99-99`
- **Template Jinja:** `{{ notification_mchs_phone | default('', true) }}`

### 11. `notification_admin_phone`
- **Source:** Local administration (Местная администрация)
- **Test value:** `+7 (86630) 7-63-99`
- **Template Jinja:** `{{ notification_admin_phone | default('', true) }}`

---

## Source Files Analyzed

| File | Role |
|------|------|
| `files/pmla_v2_template.docx` | Template with 5 hardcoded + 6 Jinja phone fields |
| `files/pmla_v2.schema.json` | Schema declaring all 11 `notification_phones.fields` |
| `backend/src/infrastructure/export/pmla_template_renderer.py` | Renderer — passes context to `docxtpl`, no phone-specific logic |
| `backend/scripts/test_pmla_v2_render.py` | Test context with all 11 phone values |
| `backend/scripts/full_render_and_pdf.py` | Full render + PDF test with all 11 phone values |
| `backend/scripts/agent_d_forces.py` | Agent that maps hardcoded → Jinja replacements |
| `backend/scripts/modify_template_v2.py` | Template modification script (same replacement map) |
| `backend/tests/.../test_pmla_v2_schema_alignment.py` | Defines `KNOWN_HARDCODED_IN_TEMPLATE` set |
| `backend/scripts/verify_final_render.py` | Minimal context — empty strings for Jinja phones |

---

## Recommendations

1. **Decide on hardcoded phones:** Either (a) convert all 5 hardcoded phones to Jinja placeholders
   so they can be configured per-organization, or (b) document them as "regional defaults" that
   are intentionally fixed.

2. **Remove dead context keys:** If keeping hardcoded phones, remove `notification_chairman_phone`,
   `notification_edds_phone`, `notification_pasf_phone`, `notification_gas_phone`, and
   `notification_rostechnadzor_phone` from the renderer context to avoid confusion.

3. **Update schema:** The schema currently lists all 11 fields identically. Consider adding a
   `"template_status": "hardcoded"` annotation to the 5 hardcoded fields so consumers know
   context values have no effect.

4. **Normalize phone formats:** Some phones use `+7 (XXX) XXX-XX-XX`, others use `+7 XXX XXX-XX-XX`
   or `+7(XXXX) XX-XX-XX`. Standardize the format across all fields.
