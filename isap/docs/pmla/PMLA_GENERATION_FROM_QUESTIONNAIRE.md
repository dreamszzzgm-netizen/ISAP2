# PMLA Generation From Questionnaire

Этот этап соединяет инженерную анкету ПМЛА с существующим генератором документа.

## Назначение

Раньше генерация ПМЛА могла запускаться от свободного `context` или от fallback-данных ОПО. Теперь основной целевой путь:

```text
ОПО
  ↓
Анкета ПМЛА
  ↓
ПАСФ / аварийные службы / сценарии / аварии / силы и средства
  ↓
questionnaire generation context
  ↓
EnhancedDocumentGenerator
  ↓
DOCX
```

## Новый endpoint

```http
POST /api/v1/pmla-questionnaires/{questionnaire_id}/generate
Content-Type: application/json
```

Тело запроса:

```json
{
  "regenerate_sections": null,
  "save_debug_artifacts": true
}
```

Ответ:

```json
{
  "document_id": "...",
  "questionnaire_id": "...",
  "facility_id": "...",
  "status": "pending_review",
  "version": 1,
  "context_quality": {
    "passed": true,
    "errors": [],
    "warnings": [],
    "summary": {}
  },
  "debug_artifacts": {
    "artifact_dir": "/tmp/isap_pmla_questionnaire_generation/...",
    "context": ".../context.json",
    "context_quality": ".../context_quality.json",
    "generation_meta": ".../generation_meta.json",
    "rendered_sections": ".../rendered_sections.json",
    "docx": ".../output.docx"
  }
}
```

## Как работает адаптация context

Сервис `PmlaGenerationFromQuestionnaireService` берёт context из `PmlaQuestionnaireService.build_generation_context()` и нормализует его под движки генерации:

- `incident_history` превращается в `accidents_and_incidents`;
- `selected_scenarios` и `custom_scenarios` объединяются в `user_scenarios`;
- выбранный ПАСФ добавляется в `emergency_services` как служба типа `pasf`;
- финансовый резерв и страхование попадают в `material_reserve` и `context_params`;
- фактические силы и средства организации попадают в `protective_equipment`;
- весь итоговый context сохраняется в `generation_meta.context_snapshot`.

## Валидация

Генерация не блокируется из-за неполных необязательных данных, но возвращает предупреждения:

- не заполнен блок аварий/инцидентов;
- не выбран ПАСФ;
- не выбраны аварийные службы;
- не подтверждены сценарии аварий;
- не заполнены фактические силы и средства организации.

Ошибки используются только для действительно обязательных данных:

- организация;
- ОПО;
- тип ОПО;
- класс опасности;
- вещества;
- оборудование.

## Debug artifacts

Если `save_debug_artifacts=true`, создаётся папка:

```text
/tmp/isap_pmla_questionnaire_generation/<timestamp>-<document_id>/
```

Внутри:

```text
context.json
context_quality.json
generation_meta.json
rendered_sections.json
output.docx
```

Эти файлы позволяют быстро понять, почему ПМЛА получился хорошим или плохим.

## Пример curl

```bash
curl -X POST "http://localhost:8000/api/v1/pmla-questionnaires/{questionnaire_id}/generate" \
  -H "Authorization: Bearer dev-secret" \
  -H "Content-Type: application/json" \
  -d '{"save_debug_artifacts": true}'
```
