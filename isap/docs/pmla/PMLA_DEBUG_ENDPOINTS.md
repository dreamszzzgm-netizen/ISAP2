# PMLA Debug Endpoints

Цель — отладить качество генерации ПМЛА отдельно от frontend, RBAC и клиентских данных.

## Reference context

```http
GET /api/v1/pmla/debug/context
```

Возвращает эталонный JSON-контекст для объекта:

- организация: хлебокомбинат;
- ОПО: сеть газопотребления;
- класс опасности: III;
- вещество: природный газ / метан;
- оборудование: газопровод, ГРУ, газовые котлы, СИЗ, огнетушители;
- службы: ПАСФ, пожарная охрана, скорая помощь.

## Validate context

```http
POST /api/v1/pmla/debug/validate-context
Content-Type: application/json

{
  "context": null
}
```

Если `context=null`, используется эталонный контекст.

## Generate deterministic test package

```http
POST /api/v1/pmla/debug/generate-test
Content-Type: application/json

{
  "context": null
}
```

Результат сохраняется в `/tmp/isap_pmla_debug/<package_id>/`:

```text
context.json
rendered_sections.json
validation_report.json
output.docx
```

## Как интерпретировать результат

Сначала смотрим `validation_report.json`:

- `context_validation.passed` — полнота входных данных;
- `non_empty_section_count` — сколько разделов заполнено;
- `missing_required_phrases` — потеря ключевых терминов;
- `placeholders_found` — остались ли заглушки;
- `passed` — итоговая диагностическая оценка.

Если `context_validation` не прошёл — проблема во входных данных.
Если есть пустые разделы — проблема в engine routing.
Если есть placeholder markers — проблема в deterministic template/fallback.
Если DOCX не создан — проблема в export/render layer.

## Проверка через curl

```bash
curl http://localhost:8000/api/v1/pmla/debug/context

curl -X POST http://localhost:8000/api/v1/pmla/debug/generate-test \
  -H "Content-Type: application/json" \
  -d '{"context": null}'
```

Если включён `API_KEY`, добавьте:

```bash
-H "Authorization: Bearer dev-secret"
```
