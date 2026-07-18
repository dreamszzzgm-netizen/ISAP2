# PMLA v2 Template Jinja Audit Report

## Overview

This audit analyzes the Jinja2 template syntax embedded in the DOCX file.

**Template:** `files/pmla_v2_template.docx`

**Note:** This template uses a custom `{%tr ... %}` syntax for table row operations, in addition to standard Jinja2 `{{ }}` variable syntax.

## Summary

| Metric | Count |
|--------|-------|
| XML Files Scanned | 16 |
| Total Variable Occurrences | 260 |
| Unique Variable Names | 78 |
| Scalar Variables | 37 |
| Nested Variables | 39 |
| Loop Variables | 2 |
| For Loops | 8 |
| Conditionals | 0 |
| Filters | 1 |

## Custom Syntax: `{%tr ... %}`

This template uses a custom Jinja extension for table row operations:
- `{%tr for var in list %}` - Start a table row loop
- `{%tr endfor %}` - End a table row loop
- `{%tr if condition %}` - Conditional table row (not found in this template)
- `{%tr endif %}` - End conditional (not found in this template)

## Files with Jinja Content

| File | Variables | Loops |
|------|-----------|-------|
| `word\document.xml` | 258 | 8 |
| `word\header1.xml` | 2 | 0 |

## Scalar Variables

These are simple key-value variables without dot notation.

| Variable | Occurrences | Files |
|----------|-------------|-------|
| `organization_short_name` | 64 | `word\document.xml`, `word\header1.xml` |
| `facility_name` | 36 | `word\document.xml` |
| `facility_reg_number` | 29 | `word\document.xml`, `word\header1.xml` |
| `contractor_organization_name` | 24 | `word\document.xml` |
| `gas_supplier_branch` | 12 | `word\document.xml` |
| `gas_supplier_name` | 10 | `word\document.xml` |
| `hazard_class` | 7 | `word\document.xml` |
| `dislocation_address` | 3 | `word\document.xml` |
| `facility_location` | 2 | `word\document.xml` |
| `settlement_name` | 2 | `word\document.xml` |
| `organization_full_name` | 2 | `word\document.xml` |
| `edds_district` | 2 | `word\document.xml` |
| `director_initials_surname` | 1 | `word\document.xml` |
| `contractor_organization_short_name` | 1 | `word\document.xml` |
| `legal_address` | 1 | `word\document.xml` |
| `inn` | 1 | `word\document.xml` |
| `ogrn` | 1 | `word\document.xml` |
| `phone` | 1 | `word\document.xml` |
| `email` | 1 | `word\document.xml` |
| `director_position_fullname` | 1 | `word\document.xml` |
| `main_activity_description` | 1 | `word\document.xml` |
| `hazardous_substances_info` | 1 | `word\document.xml` |
| `hazard_characteristics_116fz` | 1 | `word\document.xml` |
| `total_hazardous_substance_quantity` | 1 | `word\document.xml` |
| `settlement_district` | 1 | `word\document.xml` |
| `contractor_agreement_date` | 1 | `word\document.xml` |
| `director_initials_surname_full` | 1 | `word\document.xml` |
| `deputy_chairman_fullname` | 1 | `word\document.xml` |
| `notification_deputy_phone | default('', true)` | 1 | `word\document.xml` |
| `edds_name` | 1 | `word\document.xml` |
| `notification_fire_phone | default('', true)` | 1 | `word\document.xml` |
| `notification_ambulance_phone | default('112/03/103', true)` | 1 | `word\document.xml` |
| `electric_company` | 1 | `word\document.xml` |
| `notification_electric_phone | default('', true)` | 1 | `word\document.xml` |
| `notification_mchs_phone | default('', true)` | 1 | `word\document.xml` |
| `local_admin` | 1 | `word\document.xml` |
| `notification_admin_phone | default('', true)` | 1 | `word\document.xml` |

## Nested Variables (Dot Notation)

These variables access properties of objects or list items.

### Equipment (`eq.*`)

| Variable | Property |
|----------|----------|
| `eq.device_name` | device_name |
| `eq.hazard_characteristic` | hazard_characteristic |
| `eq.location` | location |
| `eq.process_codes` | process_codes |
| `eq.specifications` | specifications |

### Substance Parameters (`param.*`)

| Variable | Property |
|----------|----------|
| `param.parameter` | parameter |
| `param.value` | value |

### Equipment-Scenario Links (`link.*`)

| Variable | Property |
|----------|----------|
| `link.damaging_factors` | damaging_factors |
| `link.description` | description |
| `link.equipment_name` | equipment_name |
| `link.scenario_codes` | scenario_codes |

### Accident Scenarios (`scenario.*`)

| Variable | Property |
|----------|----------|
| `scenario.code` | code |
| `scenario.damaging_factors` | damaging_factors |
| `scenario.name` | name |
| `scenario.preconditions` | preconditions |
| `scenario.signs` | signs |
| `scenario.source` | source |

### Injury History (`injury.*`)

| Variable | Property |
|----------|----------|
| `injury.character` | character |
| `injury.consequences` | consequences |
| `injury.date` | date |
| `injury.incident_number` | incident_number |
| `injury.measures_percent` | measures_percent |
| `injury.trauma` | trauma |
| `injury.year` | year |

### Accident History (`accident.*`)

| Variable | Property |
|----------|----------|
| `accident.character` | character |
| `accident.consequences` | consequences |
| `accident.date` | date |
| `accident.incident_number` | incident_number |
| `accident.measures_percent` | measures_percent |
| `accident.trauma` | trauma |
| `accident.year` | year |

### Material Reserve Items (`item.*`)

| Variable | Property |
|----------|----------|
| `item.group_name if item.is_group_header else item.name` | group_name if item |

### Countermeasures (`cm.*`)

| Variable | Property |
|----------|----------|
| `cm.executors` | executors |
| `cm.protection` | protection |
| `cm.scenario_label` | scenario_label |
| `cm.signs` | signs |
| `cm.technical_means` | technical_means |

## Loop Variables

Variables automatically available inside `{% for %}` loops.

| Variable | Occurrences |
|----------|-------------|
| `loop.index` | 2 |
| `loop.index if not item.is_group_header else ''` | 1 |

## For Loops

| File | Loop Definition | Syntax |
|------|-----------------|--------|
| `word\document.xml` | `eq in equipment_list` | `tr` |
| `word\document.xml` | `param in substance_params` | `tr` |
| `word\document.xml` | `link in equipment_scenario_links` | `tr` |
| `word\document.xml` | `scenario in accident_scenarios` | `tr` |
| `word\document.xml` | `injury in injury_history` | `tr` |
| `word\document.xml` | `accident in accident_history` | `tr` |
| `word\document.xml` | `item in material_reserve` | `tr` |
| `word\document.xml` | `cm in countermeasures` | `tr` |

## Loop Lists (Data Structures)

These are the list variables iterated over in `{% for %}` loops.

| List Name | Loop Variable | File |
|-----------|---------------|------|
| `equipment_list` | `eq` | `word\document.xml` |
| `substance_params` | `param` | `word\document.xml` |
| `equipment_scenario_links` | `link` | `word\document.xml` |
| `accident_scenarios` | `scenario` | `word\document.xml` |
| `injury_history` | `injury` | `word\document.xml` |
| `accident_history` | `accident` | `word\document.xml` |
| `material_reserve` | `item` | `word\document.xml` |
| `countermeasures` | `cm` | `word\document.xml` |

## Filters

| Filter | Occurrences | Example Usage |
|--------|-------------|---------------|
| `default` | 6 | `notification_deputy_phone | default('', true)` |

## Required Data Structure

Based on the analysis, the template expects this JSON structure:

```json
{
  // Scalar context variables
  "contractor_agreement_date": "...",
  "contractor_organization_name": "...",
  "contractor_organization_short_name": "...",
  "deputy_chairman_fullname": "...",
  "director_initials_surname": "...",
  "director_initials_surname_full": "...",
  "director_position_fullname": "...",
  "dislocation_address": "...",
  "edds_district": "...",
  "edds_name": "...",
  "electric_company": "...",
  "email": "...",
  "facility_location": "...",
  "facility_name": "...",
  "facility_reg_number": "...",
  "gas_supplier_branch": "...",
  "gas_supplier_name": "...",
  "hazard_characteristics_116fz": "...",
  "hazard_class": "...",
  "hazardous_substances_info": "...",
  "inn": "...",
  "legal_address": "...",
  "local_admin": "...",
  "main_activity_description": "...",
  "ogrn": "...",
  "organization_full_name": "...",
  "organization_short_name": "...",
  "phone": "...",
  "settlement_district": "...",
  "settlement_name": "...",
  "total_hazardous_substance_quantity": "...",

  // List context variables
  "equipment_list": [
    {
      "location": "..."
      "hazard_characteristic": "..."
      "device_name": "..."
      "specifications": "..."
      "process_codes": "..."
    }
  ]
  "substance_params": [
    {
      "parameter": "..."
      "value": "..."
    }
  ]
  "equipment_scenario_links": [
    {
      "equipment_name": "..."
      "scenario_codes": "..."
      "description": "..."
      "damaging_factors": "..."
    }
  ]
  "accident_scenarios": [
    {
      "code": "..."
      "name": "..."
      "source": "..."
      "preconditions": "..."
      "signs": "..."
      "damaging_factors": "..."
    }
  ]
  "injury_history": [
    {
      "year": "..."
      "incident_number": "..."
      "date": "..."
      "character": "..."
      "trauma": "..."
      "consequences": "..."
      "measures_percent": "..."
    }
  ]
  "accident_history": [
    {
      "year": "..."
      "incident_number": "..."
      "date": "..."
      "character": "..."
      "trauma": "..."
      "consequences": "..."
      "measures_percent": "..."
    }
  ]
  "material_reserve": [
    {
      "group_name if item": "..."
    }
  ]
  "countermeasures": [
    {
      "scenario_label": "..."
      "signs": "..."
      "protection": "..."
      "technical_means": "..."
      "executors": "..."
    }
  ]
}
```
