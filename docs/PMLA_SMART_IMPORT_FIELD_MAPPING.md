# PMLA Smart Import Field Mapping

> Матрица покрытия: соответствие между плоскими полями Smart Import `pmla_questionnaire`
> и целевой структурой `DEFAULT_QUESTIONNAIRE` для `PmlaQuestionnaireModel.data`.

## Легенда

| Статус | Значение |
|--------|----------|
| ✅ Полностью | Поле маппится на целевой путь с корректным преобразованием типа |
| ⚠️ Частично | Данные сохраняются, но часть информации может теряться |
| ❌ Не покрыто | Поле не маппится (остаётся в `unmapped_fields`) |

## Матрица

### Организация / ОПО

| Поле источника | Ключ Smart Import | Фактический тип | Целевой JSON path | Целевой тип | Преобразование | Статус |
|---|---|---|---|---|---|---|
| Организация | `organization_name` | str | `_import_meta.organization_name` + `organization_candidate.name` | str | Direct | ✅ |
| ОПО | `facility_name` | str | `_import_meta.facility_name` + `facility_candidate.name` | str | Direct | ✅ |
| Рег. номер ОПО | `facility_reg_number` | str | `_import_meta.facility_reg_number` + `facility_candidate.reg_number` | str | Direct | ✅ |

### Сведения об авариях

| Поле источника | Ключ Smart Import | Фактический тип | Целевой JSON path | Целевой тип | Преобразование | Статус |
|---|---|---|---|---|---|---|
| Были аварии/инциденты | `has_incidents` | str | `incident_history.has_incidents` | bool / None | `to_bool()` — "да"→True, "нет"→False, ""→None | ✅ |
| Описание аварий/инцидентов | `incident_description` | str | `incident_history.items[]` | list[dict] | Разбивка на абзацы → `{"description": "...", "date": "", "type": ""}` | ✅ |

### Режим работы

| Поле источника | Ключ Smart Import | Фактический тип | Целевой JSON path | Целевой тип | Преобразование | Статус |
|---|---|---|---|---|---|---|
| Режим работы | `operation_mode` | str | `operation_mode.mode` | str | Direct | ✅ |
| Персонал в смену | `staff_per_shift` | str | `operation_mode.staff_per_shift` | int / None | `to_int()` — "8"→8, ошибка→None + warning | ✅ |
| Ночная смена | `night_shift` | str | `operation_mode.night_shift` | bool / None | `to_bool()` | ✅ |
| Есть диспетчер | `has_dispatcher` | str | `operation_mode.has_dispatcher` | bool / None | `to_bool()` | ✅ |

### Сценарии

| Поле источника | Ключ Smart Import | Фактический тип | Целевой JSON path | Целевой тип | Преобразование | Статус |
|---|---|---|---|---|---|---|
| Сценарии | `selected_scenarios` | list[str] | `selected_scenarios` | list[str] | Direct (уже split_list) | ✅ |
| Доп. сценарии | `custom_scenarios` | list[str] | `custom_scenarios` | list[str] | Direct (уже split_list) | ✅ |

### Силы и средства

| Поле источника | Ключ Smart Import | Фактический тип | Целевой JSON path | Целевой тип | Преобразование | Статус |
|---|---|---|---|---|---|---|
| Силы и средства | `resources` | list[str] | `organization_resources.actual_items[]` | list[dict] | Каждый элемент → `{"name": ..., "quantity": "", "unit": ""}` | ✅ |

### ПАСФ

| Поле источника | Ключ Smart Import | Фактический тип | Целевой JSON path | Целевой тип | Преобразование | Статус |
|---|---|---|---|---|---|---|
| ПАСФ | `pasf_name` | str | `_import_meta.pasf_name` | str | Direct (вопрос связывания — следующий этап) | ✅ |

### Финансовый резерв

| Поле источника | Ключ Smart Import | Фактический тип | Целевой JSON path | Целевой тип | Преобразование | Статус |
|---|---|---|---|---|---|---|
| Финансовый резерв | `financial_reserve` | str | `financial_reserve.amount` | str | Direct | ✅ |

### Страхование

| Поле источника | Ключ Smart Import | Фактический тип | Целевой JSON path | Целевой тип | Преобразование | Статус |
|---|---|---|---|---|---|---|
| Наличие договора | `has_insurance` | str | `insurance.has_contract` | bool / None | `to_bool()` | ✅ |
| Страховая компания | `insurance_company` | str | `insurance.company` | str | Direct | ✅ |
| Номер договора | `insurance_contract` | str | `insurance.contract_number` | str | Direct | ✅ |
| Действителен до | `insurance_valid_until` | str | `insurance.valid_until` | str | Direct | ✅ |

### Обучение / тренировки

| Поле источника | Ключ Smart Import | Фактический тип | Целевой JSON path | Целевой тип | Преобразование | Статус |
|---|---|---|---|---|---|---|
| Тренировки | `training` | str | `training.conducted` | bool / None | `to_bool()` — неоднозначное значение → warning | ⚠️ |

### Приложения

| Поле источника | Ключ Smart Import | Фактический тип | Целевой JSON path | Целевой тип | Преобразование | Статус |
|---|---|---|---|---|---|---|
| Приложения | `attachments` | list[str] | `attachments_checklist` | list[str] | Direct (уже split_list) | ✅ |

### Схема оповещения

| Поле источника | Ключ Smart Import | Фактический тип | Целевой JSON path | Целевой тип | Преобразование | Статус |
|---|---|---|---|---|---|---|
| Первый получатель | `notification_first_receiver` | str | `notification_scheme.first_receiver` | str | Direct | ✅ |
| Отв. руководитель | `notification_responsible_manager` | str | `notification_scheme.responsible_manager` | str | Direct | ✅ |
| Вызов ПАСФ | `notification_calls_pasf` | str | `notification_scheme.calls_pasf` | str | Direct | ✅ |
| Вызов пожарных | `notification_calls_fire` | str | `notification_scheme.calls_fire` | str | Direct | ✅ |
| Встреча служб | `notification_meets_services` | str | `notification_scheme.meets_services` | str | Direct | ✅ |

## Сводка

### Поля Import Profile (14 полей профиля `pmla_questionnaire`)

| Категория | Количество |
|---|---|
| ✅ Полностью покрыто | 24 (плоских ключа, включая расширенные notification/insurance) |
| ⚠️ Частично покрыто | 1 (`training` — неоднозначный bool) |
| ❌ Не покрыто | 0 |

> **Примечание:** 24 покрытых плоских ключа включают как 14 базовых полей профиля,
> так и дополнительные плоские ключи, поддерживаемые нормализатором
> (ночные смены, диспетчер, поля страхования, схема оповещения и т.д.).
> Статус "0 не покрыто" означает, что **все ключи, которые может передать
> Smart Import, имеют маппинг**. Поля, которые парсер DOCX физически
> не может извлечь, не являются "непокрытыми" — они отсутствуют во входных данных.

> **Частичное покрытие (training):** Поле `training` из Smart Import — это текст произвольной формы ("ежеквартально", "раз в полгода", etc.). Нормализатор пытается преобразовать его в bool (`training.conducted`). Если значение не является однозначным да/нет, добавляется warning, и данные остаются в `_import_meta.raw_data` для ручной проверки.

### Поля DEFAULT_QUESTIONNAIRE (14 top-level ключей)

| Категория | Количество |
|---|---|
| ✅ Автоматически импортируются (полностью или частично) | 10 |
| ⚠️ Требуют ручного заполнения после импорта | 2 (`selected_pasf_id`, `selected_emergency_service_ids`) |
| 🔧 Формируются генерационным движком | 1 (`organization_resources.recommended_items`) |
| ❌ Не импортируются (нет источника) | 1 (`source_notes`) |

## Ограничения импорта (из DOCX parser)

Следующие поля анкеты не могут быть надёжно импортированы из текущего DOCX parser и требуют ручного ввода после импорта:

1. **Схема оповещения** — `notification_scheme.*` — DOCX содержит списки контактов без структуры
2. **Страхование** — `insurance.*` — если в DOCX нет таблицы страхования
3. **Пользовательские сценарии** — `custom_scenarios` — DOCX parser редко находит "Другое"
4. **Ресурсы организации** — `organization_resources.recommended_items` — рекомендации строятся движком, не импортируются
5. **Примечания** — `source_notes` — не маппится из импорта
