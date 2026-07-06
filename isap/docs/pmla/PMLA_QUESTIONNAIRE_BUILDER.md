# PMLA Questionnaire Builder

Анкета ПМЛА — центральный слой между карточкой ОПО, справочниками, умным импортом и генератором документа.

## Зачем нужна анкета

ПМЛА не должен генерироваться только из общего промпта. Факты должны приходить из базы, справочников и подтверждённых ответов пользователя.

Анкета фиксирует инженерные решения:

- были ли аварии и инциденты;
- какие сценарии аварий подтверждены;
- какие сценарии добавлены вручную через пункт «Другое»;
- какой ПАСФ выбран из справочника;
- какие пожарные/медицинские/газовые службы выбраны;
- какие силы и средства реально есть у организации;
- какие средства рекомендованы системой;
- как организовано оповещение;
- есть ли тренировки, финансовый резерв, страхование и приложения.

## API

### Создать или получить анкету по ОПО

```http
POST /api/v1/pmla/questionnaires/facility/{facility_id}
GET  /api/v1/pmla/questionnaires/facility/{facility_id}
```

### Получить анкету

```http
GET /api/v1/pmla/questionnaires/{questionnaire_id}
```

### Обновить блок анкеты

```http
PATCH /api/v1/pmla/questionnaires/{questionnaire_id}/blocks/{block_name}
Content-Type: application/json

{
  "data": {}
}
```

Примеры `block_name`:

```text
incident_history
operation_mode
selected_scenarios
selected_pasf_id
selected_emergency_service_ids
organization_resources
notification_scheme
training
financial_reserve
insurance
attachments_checklist
```

### Добавить пользовательский сценарий

```http
POST /api/v1/pmla/questionnaires/{questionnaire_id}/custom-scenarios
Content-Type: application/json

{
  "title": "Отказ запорной арматуры",
  "description": "При попытке прекращения подачи газа возможно неполное закрытие задвижки",
  "source_equipment": "запорная арматура",
  "substance": "природный газ",
  "consequences": "продолжение поступления газа, загазованность помещения"
}
```

### Собрать generation context

```http
GET /api/v1/pmla/questionnaires/{questionnaire_id}/context
```

Этот endpoint собирает единый JSON для генератора:

```text
organization
facility
equipment
substances
responsible_persons
questionnaire
incident_history
selected_scenarios
custom_scenarios
pasf
nearest_services
organization_resources
recommendations
```

## Принцип генерации

```text
Карточка организации
  + Карточка ОПО
  + Оборудование
  + Вещества
  + Ответственные лица
  + Справочник ПАСФ
  + Справочник аварийных служб
  + Анкета ПМЛА
  + Умный импорт
    ↓
Generation Context
    ↓
PMLA Generator
```

LLM не должна придумывать факты. Она получает подтверждённый context и пишет официальный текст.


## Следующий этап: генерация из анкеты

См. `docs/pmla/PMLA_GENERATION_FROM_QUESTIONNAIRE.md`.
