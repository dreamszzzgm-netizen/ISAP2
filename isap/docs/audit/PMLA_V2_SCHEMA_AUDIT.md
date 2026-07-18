# PMLA v2 Schema Audit

**Date**: 2026-07-11
**File**: `files/pmla_v2.schema.json`

---

## 1. JSON Schema Validity

**Verdict: NOT a valid JSON Schema.**

The file is a **custom domain-specific JSON document**, not a JSON Schema draft (Draft 4/7/2020-12). Missing:

| Required JSON Schema property | Present? | Notes |
|-------------------------------|----------|-------|
| `$schema` | NO | No meta-schema reference |
| `$id` | NO | No schema identifier |
| `type` | NO | No `"type": "object"` declaration |
| `properties` | NO | Uses custom keys (`required_fields`, `required_tables`, etc.) |
| `required` | NO | No required array |
| `additionalProperties` | NO | No constraint on extra keys |
| `definitions` / `$defs` | NO | No reusable definitions |

The file cannot be validated by any JSON Schema validator as-is.

---

## 2. Top-Level Key Inventory

| # | Key | Type | Description | Matches template/renderer/context? |
|---|-----|------|-------------|-------------------------------------|
| 1 | `doc_type` | string | `"PMLA"` | Metadata only |
| 2 | `template_version` | string | `"2.0"` | Metadata only |
| 3 | `template_file` | string | `"pmla_v2_template.docx"` | Yes — points to actual file |
| 4 | `description` | string | Human description | Metadata only |
| 5 | `required_fields` | object | Scalar template placeholders | Yes — all keys used in context dicts |
| 6 | `required_tables` | object | Loop-based table definitions | Yes — keys match `equipment_list`, `substance_params`, etc. |
| 7 | `notification_phones` | object | Scalar phone placeholders (Table 17) | Yes — `notification_chairman_phone` etc. match renderer |
| 8 | `static_tables` | array of ints | Tables 1, 2, 12, 14, 15, 16, 19, 20 | Matches `modify_template_v2.py` which skips these |
| 9 | `notes` | array of strings | Human-readable notes | Documentation only |

---

## 3. Array Structure Analysis

### Tables defined in `required_tables`

| Key | Table# | Has `item_fields`? | Has `min_items`? | Has `jinja_tag`? |
|-----|--------|---------------------|-------------------|-------------------|
| `equipment_list` | 5 | YES (5 fields) | YES (`1`) | YES |
| `substance_params` | 6 | YES (2 fields) | YES (`0`) | YES |
| `equipment_scenario_links` | 7 | YES (4 fields) | YES (`0`) | YES |
| `equipment_defects` | 8 | YES (5 fields) | YES (`0`) | YES |
| `accident_scenarios` | 9 | YES (6 fields) | YES (`1`) | YES |
| `injury_history` | 10 | YES (7 fields) | YES (`0`) | YES |
| `accident_history` | 11 | YES (7 fields) | YES (`0`) | YES |
| `material_reserve` | 13 | YES (5 fields) | YES (`0`) | YES |
| `countermeasures` | 18 | YES (5 fields) | YES (`0`) | YES |

**Observation**: `min_items` is defined but never enforced programmatically — the schema is documentation-only, not validation.

---

## 4. Date Formats, Numeric Types, Nullable Fields

**No type annotations exist.** All field values are described as Russian-language strings, not typed schemas.

| Field | Expected type | Actual schema type | Risk |
|-------|---------------|---------------------|------|
| `contractor_agreement_date` | date | string (untyped) | Could receive any format |
| `total_hazardous_substance_quantity` | numeric | string (untyped) | `"0.5"` — no min/max, no unit enforcement |
| `injury_history[].date` | date | string (untyped) | No format validation |
| `injury_history[].year` | integer | string (untyped) | No range validation |
| `injury_history[].measures_percent` | percentage | string (untyped) | No 0-100 enforcement |
| `material_reserve[].is_group_header` | boolean | string (untyped) | Description says "boolean" but no actual boolean type |
| `notification_*_phone` | phone string | string (untyped) | No phone format regex |

**Nullable fields**: No nullable annotations. The renderer uses `{{ field | default('', true) }}` pattern, implying all fields are implicitly nullable, but the schema doesn't document this.

---

## 5. Enum for `hazard_class`

**No enum defined.** The schema says:

```json
"hazard_class": "Класс опасности ОПО"
```

The actual codebase uses values like `"III"` (in `full_render_and_pdf.py:30`). PMLA regulations define hazard classes I-IV, but no enum constrains this.

**Recommendation**: Add:
```json
"hazard_class_enum": ["I", "II", "III", "IV"]
```

---

## 6. Duplicated Fields

### 6.1 `injury_history` vs `accident_history` — IDENTICAL item_fields

Both tables have **exactly the same 7 fields**:

```
year, incident_number, date, character, trauma, consequences, measures_percent
```

| Schema key | Table # | Fields |
|------------|---------|--------|
| `injury_history` | 10 | year, incident_number, date, character, trauma, consequences, measures_percent |
| `accident_history` | 11 | year, incident_number, date, character, trauma, consequences, measures_percent |

The only difference is the loop variable name (`injury` vs `accident`) and the description text. This is a **structural duplication** — the same data model serves two tables with different semantic meanings (trauma characteristics vs. accident/incident history).

**Risk**: Confusing for developers; could merge into a single type with a `type` discriminator field.

---

## 7. Name Conflicts Analysis

| Schema name | Alternative name (in codebase) | Conflict? | Resolution |
|-------------|-------------------------------|-----------|------------|
| `accident_scenarios` | (none) | OK | Unique |
| `material_reserve` | `material_reserves` (plural, in `enhanced_generator.py:251`) | **YES** | `material_reserves` is a separate key in enriched context; schema uses singular |
| `material_reserve` | `financial_reserve` (in `pmla.py:81`, quality service) | **YES** | `financial_reserve` is an alias/fallback in the API router: `context.get("financial_reserve", context.get("material_reserve"))` |
| `accident_history` | `accident_statistics` (not found) | No conflict | Not present |
| `injury_history` | `injury_history` | OK | Unique |
| `notification_phones` | `contact_list` (not found) | No conflict | Not present |

**Critical finding**: `material_reserve` vs `financial_reserve` — the PMLA API router (`pmla.py:81`) tries `financial_reserve` first, falling back to `material_reserve`. This means two different key names can point to the same data, creating ambiguity.

---

## 8. Presence of Required Fields

| Field | Present in schema? | Notes |
|-------|--------------------|-------|
| `substance_params` | YES | Table 6, defined in `required_tables` |
| `equipment_scenario_links` | YES | Table 7, defined in `required_tables` |
| `equipment_defects` | YES | Table 8, defined in `required_tables` |
| `countermeasures` | YES | Table 18, defined in `required_tables` |

All four fields are present and correctly defined with jinja tags matching the agents' usage.

---

## 9. Template Loop Verification

The schema describes 8 jinja `{%tr for ... %}` loops. Cross-referencing with `modify_template_v2.py` and agent scripts:

| Schema loop | Schema jinja_tag | Agent/Script | Actual jinja_tag | Match? |
|-------------|------------------|--------------|------------------|--------|
| `equipment_list` | `{%tr for eq in equipment_list %}` | (inline in full_render) | — | Schema-only |
| `substance_params` | `{%tr for param in substance_params %}` | `agent_a_scenarios.py:28` | `{%tr for param in substance_params %}` | YES |
| `equipment_scenario_links` | `{%tr for link in equipment_scenario_links %}` | `agent_a_scenarios.py:40` | `{%tr for link in equipment_scenario_links %}` | YES |
| `equipment_defects` | `{%tr for defect in equipment_defects %}` | `modify_template_v2.py:151` | `{%tr for defect in equipment_defects %}` | YES |
| `accident_scenarios` | `{%tr for scenario in accident_scenarios %}` | `agent_a_scenarios.py:58` | `{%tr for scenario in accident_scenarios %}` | YES |
| `injury_history` | `{%tr for injury in injury_history %}` | `agent_b_incidents.py:25` | `{%tr for injury in injury_history %}` | YES |
| `accident_history` | `{%tr for accident in accident_history %}` | `agent_b_incidents.py:45` | `{%tr for accident in accident_history %}` | YES |
| `material_reserve` | `{%tr for item in material_reserve %}` | `agent_c_resources.py:24` | `{%tr for item in material_reserve %}` | YES |
| `countermeasures` | `{%tr for cm in countermeasures %}` | `agent_a_scenarios.py:77` | `{%tr for cm in countermeasures %}` | YES |

**All loops match between schema and template/agents.**

---

## 10. Issues Summary

### Critical

| # | Issue | Location | Impact |
|---|-------|----------|--------|
| C1 | Not a valid JSON Schema | Whole file | Cannot be validated by tooling; no automated enforcement |
| C2 | `material_reserve` vs `financial_reserve` alias | `pmla.py:81`, `enhanced_generator.py:251` | Two key names for same data; API silently falls back |
| C3 | No type annotations on any field | All `item_fields` | No validation of dates, numbers, booleans, enums |

### High

| # | Issue | Location | Impact |
|---|-------|----------|--------|
| H1 | `injury_history` and `accident_history` are structurally identical | `required_tables` keys 10, 11 | Duplication; one type with discriminator would suffice |
| H2 | `hazard_class` has no enum constraint | `required_fields.hazard_class` | Any string accepted; should be `I`-`IV` |
| H3 | `material_reserve` schema uses `is_group_header` (boolean) but typed as string | `required_tables.material_reserve.item_fields` | Renderer relies on truthiness, not strict boolean |

### Medium

| # | Issue | Location | Impact |
|---|-------|----------|--------|
| M1 | `min_items` defined but never enforced | All table definitions | `min_items: 1` on `equipment_list` and `accident_scenarios` has no runtime check |
| M2 | `source` field in `equipment_defects` is ambiguous | `required_tables.equipment_defects.item_fields.source` | Named `source` but means "location of defect" — collides with `source` meaning "data origin" elsewhere |
| M3 | No `additionalProperties: false` | Whole schema | Extra keys silently accepted |

### Low

| # | Issue | Location | Impact |
|---|-------|----------|--------|
| L1 | `notification_phones` is a separate top-level key, not under `required_tables` | Top level | Inconsistent structure; phones are scalar, not arrays |
| L2 | `static_tables` list is magic numbers | `static_tables: [1, 2, 12, 14, 15, 16, 19, 20]` | No enum constraint on table numbers |
| L3 | `notes` array is documentation mixed with schema | Top level | Schema should be machine-readable; notes belong in README |

---

## 11. Recommendations

1. **Convert to JSON Schema Draft 2020-12** — Add `$schema`, `type: "object"`, `properties`, `required` array. This enables IDE validation and automated testing.

2. **Unify `material_reserve` / `financial_reserve`** — Pick one canonical name and update all references. The schema should document the alias.

3. **Add type constraints** — Define date formats (`"date": {"type": "string", "format": "date"}`), numeric ranges, and boolean types.

4. **Add `hazard_class` enum** — `["I", "II", "III", "IV"]` per PMLA regulations.

5. **Extract `injury_history` / `accident_history` into a shared definition** — Use `$defs` to define a single `IncidentRecord` type referenced by both tables.

6. **Rename `equipment_defects.source`** to `location` to avoid semantic collision with data-source fields.

7. **Move `notes` to a separate `NOTES.md`** or `description` field to keep schema machine-readable.
