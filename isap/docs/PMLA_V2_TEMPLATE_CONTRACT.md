# PMLA v2 — Template Contract

> Дата: 15 июля 2026
> Статус: черновик по результатам аудита 4 субагентов
> Контракт синхронизирует: schema → mapper → template → DOCX

## Статусы полей

| Статус | Значение |
|--------|----------|
| READY | Присутствует во всех трёх артефактах (schema, mapper, template) |
| MAPPER_MISSING | Есть в template и/или schema, но mapper не производит |
| SCHEMA_MISSING | Есть в mapper и/или template, но не описан в schema |
| TEMPLATE_MISSING | Есть в schema и/или mapper, но не используется в template |
| TYPE_MISMATCH | Тип в schema не соответствует фактическому типу mapper |
| WRONG_SOURCE | Источник данных в mapper не соответствует ожидаемому |
| ENGINE_GENERATED | Поле добавляется downstream (enhanced_generator, не v2 pipeline) |

## Полная таблица контракта

### Scalars — организация

| № | Раздел ПМЛА | Поле | Источник | schema | mapper | template | Статус |
|---|------------|------|----------|--------|--------|----------|--------|
| 1 | Титул | organization_full_name | organization.name | ✅ string | ✅ | ✅ | READY |
| 2 | Титул | organization_short_name | organization.short_name | ✅ | ✅ | ✅ | READY |
| 3 | Титул | legal_address | organization.address | ✅ | ✅ | ✅ | READY |
| 4 | Титул | inn | organization.inn | ✅ string(pattern) | ✅ | ✅ | READY |
| 5 | Титул | ogrn | organization.ogrn | ✅ string(pattern) | ✅ | ✅ | READY |
| 6 | Титул | phone | organization.phone | ✅ | ✅ | ✅ | READY |
| 7 | Титул | email | organization.email | ✅ string(format=email) | ✅ | ✅ | READY |

### Scalars — руководитель

| № | Раздел | Поле | Источник | schema | mapper | template | Статус |
|---|-------|------|----------|--------|--------|----------|--------|
| 8 | Титул | director_position | responsible_persons[director].position | ❌ | ✅ | ✅ | **SCHEMA_MISSING** |
| 9 | Титул | director_full_name | responsible_persons[director].full_name | ❌ | ✅ | ❌ | SCHEMA_MISSING |
| 10 | Титул | director_phone | responsible_persons[director].phone | ❌ | ✅ | ❌ | SCHEMA_MISSING |
| 11 | Титул | director_position_fullname | f"{position} {name}" | ✅ | ✅ | ✅ | READY |
| 12 | Титул | director_initials_surname | _extract_initials_surname() | ✅ | ✅ | ✅ | READY |
| 13 | Титул | director_initials_surname_full | director.full_name | ✅ | ✅ | ✅ | READY |
| 14 | Подпись | deputy_chairman_fullname | deputy.full_name | ✅ | ✅ | ✅ | READY |
| 15 | Оперативная ч. | person.position | director.position | ❌ | ✅ | ✅ | **SCHEMA_MISSING** |
| 16 | Оперативная ч. | person.phone | director.phone | ❌ | ✅ | ✅ | **SCHEMA_MISSING** |

### Scalars — ОПО

| № | Раздел | Поле | Источник | schema | mapper | template | Статус |
|---|-------|------|----------|--------|--------|----------|--------|
| 17 | Общие сведения | main_activity_description | questionnaire.main_activity / facility.okved | ✅ | ✅ | ✅ | READY |
| 18 | Общие сведения | facility_name | facility.name | ✅ | ✅ | ✅ | READY |
| 19 | Общие сведения | facility_reg_number | facility.reg_number | ✅ | ✅ | ✅ | READY |
| 20 | Общие сведения | facility_location | facility.address | ✅ | ✅ | ✅ | READY |
| 21 | Общие сведения | hazard_class | facility.hazard_class (→римская) | ✅ enum(I-IV) | ✅ | ✅ | READY |
| 22 | Общие сведения | hazardous_substances_info | substances[].name (concat) | ✅ | ✅ | ✅ | READY |
| 23 | Общие сведения | hazard_characteristics_116fz | substances[].hazard_properties (concat) | ✅ | ✅ | ✅ | READY |
| 24 | Общие сведения | total_hazardous_substance_quantity | sum(substances[].quantity_kg) | ✅ number | ✅ | ✅ | READY |
| 25 | Общие сведения | settlement_name | _parse_settlement(facility.address) | ❌ APPROVED | ✅ | ✅ | **APPROVED** |
| 26 | Общие сведения | settlement_district | _parse_settlement(facility.address) | ❌ APPROVED | ✅ | ✅ | **APPROVED** |

### Scalars — ПАСФ

| № | Раздел | Поле | Источник | schema | mapper | template | Статус |
|---|-------|------|----------|--------|--------|----------|--------|
| 27 | ПАСФ | contractor_organization_name | pasf.name | ✅ | ✅ | ✅ | READY |
| 28 | ПАСФ | contractor_organization_short_name | pasf.short_name / pasf.name | ✅ | ✅ | ✅ | READY |
| 29 | ПАСФ | contractor_director_position | pasf.director_position | ❌ | ✅ | ✅ | **SCHEMA_MISSING** |
| 30 | ПАСФ | contractor_director_full_name | pasf.director_full_name | ❌ | ✅ | ❌ | SCHEMA_MISSING |
| 31 | ПАСФ | contractor_director_initials_surname | _extract_initials_surname() | ❌ | ✅ | ✅ | **SCHEMA_MISSING** |
| 32 | ПАСФ | contractor_dispatch_address | pasf.actual_address / dispatch_address | ❌ | ✅ | ✅ | **SCHEMA_MISSING** |
| 33 | ПАСФ | contractor_phone | pasf.dispatch_phone / phone | ❌ | ✅ | ✅ | **SCHEMA_MISSING** |
| 34 | ПАСФ | contractor_agreement_date | pasf_documents[contract].issued_at | ✅ | ✅ | ✅ | READY |
| 35 | ПАСФ | contractor_agreement_number | pasf_documents[contract].document_number | ✅ | ✅ | ✅ | READY |
| 36 | ПАСФ | dislocation_address | = contractor_dispatch_address | ✅ | ✅ (alias) | ✅ | READY |
| 37 | ПАСФ | appendices_manifest | attachments_checklist + pasf_documents | ❌ | ✅ | ❌ | SCHEMA_MISSING |

### Scalars — службы

| № | Раздел | Поле | Источник | schema | mapper | template | Статус |
|---|-------|------|----------|--------|--------|----------|--------|
| 38 | Службы | fire_department_name | services[fire].name | ❌ | ✅ | ✅ | **SCHEMA_MISSING** |
| 39 | Службы | fire_department_short_name | services[fire].short_name | ❌ | ✅ | ✅ | **SCHEMA_MISSING** |
| 40 | Службы | fire_department_address | services[fire].address | ❌ | ✅ | ✅ | **SCHEMA_MISSING** |
| 41 | Службы | ambulance_service_name | services[ambulance].name | ❌ | ✅ | ❌ | SCHEMA_MISSING |
| 42 | Службы | hospital_name | services[ambulance].hospital_name | ❌ | ✅ | ✅ | **SCHEMA_MISSING** |
| 43 | Службы | hospital_address | services[ambulance].hospital_address | ❌ | ✅ | ❌ | SCHEMA_MISSING |
| 44 | Службы | gas_service_name | services[gas].name | ❌ | ✅ | ❌ | SCHEMA_MISSING |
| 45 | Службы | gas_service_address | services[gas].address | ❌ | ✅ | ❌ | SCHEMA_MISSING |
| 46 | Службы | gas_supplier_name | = gas_service_name | ✅ | ✅ (alias) | ✅ | READY |
| 47 | Службы | gas_supplier_branch | services[gas].branch | ❌ APPROVED | ✅ | ✅ | **APPROVED** |
| 48 | Службы | electric_network_name | services[electric].name | ❌ | ✅ | ❌ | SCHEMA_MISSING |
| 49 | Службы | electric_network_short_name | services[electric].short_name | ❌ | ✅ | ❌ | SCHEMA_MISSING |
| 50 | Службы | electric_network_address | services[electric].address | ❌ | ✅ | ❌ | SCHEMA_MISSING |
| 51 | Службы | edds_name | services[edds].name | ❌ APPROVED | ✅ | ✅ | **APPROVED** |
| 52 | Службы | edds_short_name | services[edds].short_name | ❌ | ✅ | ❌ | SCHEMA_MISSING |
| 53 | Службы | edds_address | services[edds].address | ❌ | ✅ | ❌ | SCHEMA_MISSING |
| 54 | Службы | edds_additional_phone | services[edds].additional_phone | ❌ | ✅ | ❌ | SCHEMA_MISSING |
| 55 | Службы | edds_district | = settlement_district | ❌ APPROVED | ✅ | ✅ | **APPROVED** |
| 56 | Службы | mchs_department_name | services[mchs].name | ❌ | ✅ | ✅ | **SCHEMA_MISSING** |
| 57 | Службы | mchs_department_short_name | services[mchs].short_name | ❌ | ✅ | ❌ | SCHEMA_MISSING |
| 58 | Службы | mchs_department_address | services[mchs].address | ❌ | ✅ | ❌ | SCHEMA_MISSING |
| 59 | Службы | rostechnadzor_department_name | services[rostechnadzor].name | ❌ | ✅ | ✅ | **SCHEMA_MISSING** |
| 60 | Службы | rostechnadzor_department_short_name | services[rostechnadzor].short_name | ❌ | ✅ | ❌ | SCHEMA_MISSING |
| 61 | Службы | rostechnadzor_department_address | services[rostechnadzor].address | ❌ | ✅ | ❌ | SCHEMA_MISSING |
| 62 | Службы | local_administration_name | services[admin].name | ❌ | ✅ | ❌ | SCHEMA_MISSING |
| 63 | Службы | local_administration_short_name | services[admin].short_name | ❌ | ✅ | ❌ | SCHEMA_MISSING |
| 64 | Службы | local_administration_address | services[admin].address | ❌ | ✅ | ❌ | SCHEMA_MISSING |
| 65 | Службы | local_administration_additional_phone | services[admin].additional_phone | ❌ | ✅ | ❌ | SCHEMA_MISSING |
| 66 | Службы | electric_company | = electric_network_name | ❌ APPROVED | ✅ (alias) | ✅ | **APPROVED** |
| 67 | Службы | local_admin | = local_administration_name | ❌ APPROVED | ✅ (alias) | ✅ | **APPROVED** |

### Scalars — страхование и резерв

| № | Раздел | Поле | Источник | schema | mapper | template | Статус |
|---|-------|------|----------|--------|--------|----------|--------|
| 68 | Страхование | opo_insurance_company_name | insurance.company_name / company | ❌ | ✅ | ✅ | **SCHEMA_MISSING** |
| 69 | Страхование | opo_insurance_company_short_name | insurance.company_short_name / short_name | ❌ | ✅ | ❌ | SCHEMA_MISSING |
| 70 | Страхование | opo_insurance_policy_number | insurance.policy_number / contract_number | ❌ | ✅ | ✅ | **SCHEMA_MISSING** |
| 71 | Страхование | opo_insurance_policy_date | insurance.policy_date / contract_date | ❌ | ✅ | ✅ | **SCHEMA_MISSING** |
| 72 | Страхование | opo_insurance_valid_from | insurance.valid_from | ❌ | ✅ | ✅ | **SCHEMA_MISSING** |
| 73 | Страхование | opo_insurance_valid_until | insurance.valid_until | ❌ | ✅ | ✅ | **SCHEMA_MISSING** |
| 74 | Страхование | opo_insurance_amount | insurance.insured_amount / amount / sum | ❌ | ✅ | ❌ | SCHEMA_MISSING |
| 75 | Страхование | insurance_amount | **material_reserve.insurance_amount (LEGACY)** | ❌ | ✅ (**WRONG_SOURCE**) | ✅ | **WRONG_SOURCE** |
| 76 | Резерв | financial_reserve_order_number | financial_reserve.order_number | ❌ | ✅ | ✅ | **SCHEMA_MISSING** |
| 77 | Резерв | financial_reserve_order_date | financial_reserve.order_date | ❌ | ✅ | ✅ | **SCHEMA_MISSING** |
| 78 | Резерв | financial_reserve_amount | financial_reserve.amount | ❌ | ✅ | ❌ | SCHEMA_MISSING |
| 79 | Резерв | financial_reserve_source | financial_reserve.source | ❌ | ✅ | ❌ | SCHEMA_MISSING |
| 80 | Резерв | financial_reserve_purpose | financial_reserve.purpose | ❌ | ✅ | ❌ | SCHEMA_MISSING |
| 81-92 | Резерв | financial_reserve_insurance_* (12 flat) | financial_reserve_insurance.* | ❌ | ✅ | ❌ | SCHEMA_MISSING |
| 93 | Schema | financial_reserve (object) | — | ✅ **object** | ❌ **flat keys** | ❌ | **TYPE_MISMATCH** |

### Телефоны оповещения (таблица 17)

| № | Поле | Источник | schema | mapper | template | Статус |
|---|------|----------|--------|--------|----------|--------|
| 94 | notification_chairman_phone | = director_phone | ✅ | ✅ | **hardcoded** | **TEMPLATE_MISSING** |
| 95 | notification_deputy_phone | deputy.phone | ✅ | ✅ | ✅ | READY |
| 96 | notification_edds_phone | edds.dispatcher_phone | ✅ | ✅ | **hardcoded** | **TEMPLATE_MISSING** |
| 97 | notification_pasf_phone | = contractor_phone | ✅ | ✅ | **hardcoded** | **TEMPLATE_MISSING** |
| 98 | notification_fire_phone | fire.dispatcher_phone | ✅ | ✅ | ✅ | READY |
| 99 | notification_ambulance_phone | ambulance.dispatcher_phone | ✅ | ✅ | ✅ | READY |
| 100 | notification_gas_phone | gas.dispatcher_phone | ✅ | ✅ | **hardcoded** | **TEMPLATE_MISSING** |
| 101 | notification_electric_phone | electric.dispatcher_phone | ✅ | ✅ | ✅ | READY |
| 102 | notification_mchs_phone | mchs.dispatcher_phone | ✅ | ✅ | ✅ | READY |
| 103 | notification_rostechnadzor_phone | rostechnadzor.dispatcher_phone | ✅ | ✅ | **hardcoded** | **TEMPLATE_MISSING** |
| 104 | notification_admin_phone | admin.dispatcher_phone | ✅ | ✅ | ✅ | READY |
| 105 | notification_administration_phone | admin.dispatcher_phone | ❌ | ✅ | ❌ | SCHEMA_MISSING |

### Специальные

| № | Поле | Источник | schema | mapper | template | Статус |
|---|------|----------|--------|--------|----------|--------|
| 106 | **development_year** | ❌ **не назначен** | ❌ | ❌ | ✅ | **MAPPER_MISSING+SCHEMA_MISSING** |

### Массивы (табличные разделы)

| № | Поле | schema | mapper | template | Статус |
|---|------|--------|--------|----------|--------|
| 107 | equipment_list | ✅ array[EquipmentItem] | ✅ | ✅ 5 полей | READY |
| 108 | substance_params | ✅ array[SubstanceParam] | ✅ | ✅ 2 поля | READY |
| 109 | equipment_scenario_links | ✅ array[EquipmentScenarioLink] | ✅ | ✅ 4 поля | READY |
| 110 | accident_scenarios | ✅ array[AccidentScenario] | ✅ | ✅ 6 полей | READY |
| 111 | injury_history | ✅ array[IncidentRecord] | ✅ | ✅ 7 полей | READY |
| 112 | accident_history | ✅ array[IncidentRecord] | ✅ | ✅ 7 полей | READY |
| 113 | material_reserve | ✅ array[MaterialReserveItem] | ✅ | ✅ (сложная Jinja) | READY |
| 114 | countermeasures | ✅ array[Countermeasure] | ✅ | ✅ 5 полей | READY |
| 115 | equipment_defects | ✅ array[EquipmentDefect] | ❌ | ❌ | **DEPRECATED** |

## Итоговая статистика

| Статус | Количество |
|--------|-----------|
| READY | 60 |
| **SCHEMA_MISSING** | **28** |
| **MAPPER_MISSING** | **1** (development_year) |
| **TEMPLATE_MISSING** (hardcoded) | **5** |
| **TYPE_MISMATCH** | **1** (financial_reserve) |
| **WRONG_SOURCE** | **1** (insurance_amount) |
| APPROVED (computed, без схемы) | 6 |
| DEPRECATED | 1 (equipment_defects) |

## План исправлений

### 🔴 P0 — blocker (без этого DOCX не сгенерируется)

1. **`development_year`** (MAPPER_MISSING + SCHEMA_MISSING)
   - Добавить в mapper: `"development_year": str(datetime.now().year)` (fallback: questionnaire.development_year → source_context.development_year → текущий год)
   - Добавить в schema как `string` (pattern `^\d{4}$`)
   - Файл: `pmla_v2_context_mapper.py` после строки 739

2. **`insurance_amount`** (WRONG_SOURCE)
   - Заменить источник с `material_reserve.insurance_amount` на `opo_insurance_amount` (который уже есть из `insurance.insured_amount`)
   - Файл: `pmla_v2_context_mapper.py` строка 801

### 🟡 P1 — важно (без этого тесты audit будут красными)

3. **`person`** (SCHEMA_MISSING)
   - Добавить в schema `$defs/Person` (position, phone)
   - Добавить свойство `person: {"$ref": "#/$defs/Person"}`

4. **5 hardcoded phones** (TEMPLATE_MISSING)
   - Заменить в DOCX-шаблоне hardcoded номера на Jinja-переменные:
     - `{{ notification_chairman_phone }}`
     - `{{ notification_edds_phone }}`
     - `{{ notification_pasf_phone }}`
     - `{{ notification_gas_phone }}`
     - `{{ notification_rostechnadzor_phone }}`

### ⚪ P2 — качество

5. **financial_reserve** (TYPE_MISMATCH) — переделать schema на flat keys
6. **55 mapper keys** — добавить approved computed list в schema tests
7. **Schema tests** — обновить `APPROVED_COMPUTED_SCALARS`
