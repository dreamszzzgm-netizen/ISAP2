# PMLA V2 Template Audit

## Summary

Полная параметризация DOCX-шаблона ПМЛА через docxtpl + Jinja2.

**Дата:** 2026-07-11
**Шаблон:** `pmla_v2_template.docx`
**Версия схемы:** `pmla_v2.schema.json`

---

## Parameterized Tables

| Table | Name | Jinja Variable | Items | Status |
|-------|------|----------------|-------|--------|
| 5 | Equipment list | `equipment_list` | `{%tr for eq in equipment_list %}` | ✅ Already done |
| 6 | Substance parameters | `substance_params` | `{%tr for param in substance_params %}` | ✅ NEW |
| 7 | Equipment-scenario links | `equipment_scenario_links` | `{%tr for link in equipment_scenario_links %}` | ✅ NEW |
| 8 | Equipment defects | `equipment_defects` | `{%tr for defect in equipment_defects %}` | ✅ NEW |
| 9 | Accident scenarios | `accident_scenarios` | `{%tr for scenario in accident_scenarios %}` | ✅ NEW |
| 10 | Injury history | `injury_history` | `{%tr for injury in injury_history %}` | ✅ NEW |
| 11 | Accident history | `accident_history` | `{%tr for accident in accident_history %}` | ✅ NEW |
| 13 | Material reserve | `material_reserve` | `{%tr for item in material_reserve %}` | ✅ NEW |
| 17 | Notification list | Scalar placeholders | `{{ notification_*_phone }}` | ✅ NEW |
| 18 | Countermeasures | `countermeasures` | `{%tr for cm in countermeasures %}` | ✅ NEW |

## Partially Parameterized (unchanged)

| Table | Name | Existing Placeholders |
|-------|------|-----------------------|
| 0 | Approval sheet | `contractor_organization_name`, `organization_short_name`, `director_initials_surname` |
| 3 | Abbreviations | `organization_short_name`, `organization_full_name`, `contractor_organization_short_name` |
| 4 | Organization info | All fields parameterized |
| 14-16 | Forces | `contractor_organization_name`, `gas_supplier_name` |

## Static Tables (unchanged)

| Table | Name | Reason |
|-------|------|--------|
| 1 | Correction log | Empty rows for manual fill |
| 2 | Table of contents | Auto-updated by Word |
| 12 | Reference accidents | Normalized examples from Rostechnadzor |
| 19 | Incident types | Static classification |
| 20 | Familiarization sheet | Empty rows for signatures |

---

## Rendered Outputs

| File | Description | Size |
|------|-------------|------|
| `pmla_v2_rendered_test.docx` | Full context render | ~12.5 MB |
| `pmla_v2_rendered_empty.docx` | Empty lists render | ~12.5 MB |

---

## QA Results

- ✅ No Jinja artifacts in rendered output
- ✅ All XML valid inside DOCX
- ✅ All 21 tables present
- ✅ No old test data leakage
- ✅ Empty lists render correctly
- ✅ File opens without errors

---

## Field Mapping (Tables 6-13, 18)

### Table 6: substance_params
```
{{ param.parameter }} | {{ param.value }}
```

### Table 7: equipment_scenario_links
```
{{ loop.index }} | {{ link.equipment_name }} | {{ link.scenario_codes }} | {{ link.description }} | {{ link.damaging_factors }}
```

### Table 8: equipment_defects
```
{{ loop.index }} | {{ defect.equipment_name }} | {{ defect.defect }} | {{ defect.cause }} | {{ defect.source }} | {{ defect.scenario }}
```

### Table 9: accident_scenarios
```
{{ scenario.code }} | {{ scenario.name }} | {{ scenario.source }} | {{ scenario.preconditions }} | {{ scenario.signs }} | {{ scenario.damaging_factors }}
```

### Table 10: injury_history
```
{{ injury.year }} | {{ injury.incident_number }} | {{ injury.date }} | {{ injury.character }} | {{ injury.trauma }} | {{ injury.consequences }} | {{ injury.measures_percent }}
```

### Table 11: accident_history
```
{{ accident.year }} | {{ accident.incident_number }} | {{ accident.date }} | {{ accident.character }} | {{ accident.trauma }} | {{ accident.consequences }} | {{ accident.measures_percent }}
```

### Table 13: material_reserve
```
{{ loop.index if not item.is_group_header else '' }} | {{ item.group_name if item.is_group_header else item.name }} | {{ '' if item.is_group_header else item.quantity }} | {{ '' if item.is_group_header else item.location }}
```

### Table 17: notification phones
```
{{ notification_chairman_phone | default('', true) }}
{{ notification_deputy_phone | default('', true) }}
... (11 phone placeholders total)
```

### Table 18: countermeasures
```
{{ cm.scenario_label }} | {{ cm.signs }} | {{ cm.protection }} | {{ cm.technical_means }} | {{ cm.executors }}
```

---

## Known Limitations

1. **Table 17 merged cells** — Phone numbers parameterized as scalar placeholders, not as a loop, to preserve merged cell structure
2. **Table 13 group headers** — Handled via `is_group_header` flag within the loop (conditional rendering)
3. **Empty lists** — Tables with empty arrays show only headers (no fallback rows)
4. **PDF export** — Requires LibreOffice (`soffice --headless --convert-to pdf`)

---

## Files Modified/Created

| File | Action |
|------|--------|
| `files/pmla_v1_template.docx.bak` | Backup of original |
| `files/pmla_v2_template.docx` | Modified template |
| `files/pmla_v2.schema.json` | New schema |
| `files/pmla_v2_rendered_test.docx` | Test render |
| `files/pmla_v2_rendered_empty.docx` | Empty render |
| `backend/src/infrastructure/export/pmla_template_renderer.py` | New renderer |
| `backend/scripts/modify_template_v2.py` | Template modification script |
| `backend/scripts/test_pmla_v2_render.py` | Test render script |
| `backend/scripts/pmla_export_qa.py` | QA verification |
| `docs/PMLA_V2_TEMPLATE_AUDIT.md` | This file |
