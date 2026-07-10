# Knowledge Graph Read Adapter for PMLA

## Зачем нужен

Knowledge Graph (Граф Знаний) — это структурированный источник данных о типах ОПО, оборудовании, опасностях, сценариях аварий и нормативных документах. Интеграция графа знаний с ПМЛА позволяет:

1. **Автоматически подсказывать** инженеру недостающие данные (службы, сценарии, приложения)
2. **Проверять полноту** документа через quality review
3. **Обогащать контекст** для генерируемых разделов

## Что делает

- Принимает данные ОПО / анкеты
- Возвращает `PmlaKnowledgeGraphContext` с рекомендациями
- Quality review использует контекст для warning-checks

## Что НЕ делает

- **Не генерирует весь ПМЛА** — только структурные подсказки
- **Не заменяет Assembly Layer** — работает рядом
- **Не модифицирует граф знаний** — read-only
- **Не требует реального граф-сервера** — использует in-memory fallback

## Архитектура

```
Knowledge Graph (in-memory / future DB)
        ↓
PmlaKnowledgeGraphAdapter.get_context()
        ↓
PmlaKnowledgeGraphContext (structured data)
        ↓
┌───────────────────┬──────────────────────┐
│ Quality Review    │ Generation Engines   │
│ (warning checks)  │ (context enrichment) │
└───────────────────┴──────────────────────┘
        ↓
Assembly Layer → DOCX
```

## Модель данных

```python
@dataclass
class PmlaKnowledgeGraphContext:
    facility_type: str | None           # Тип ОПО
    equipment_types: list[str]          # Типичное оборудование
    hazards: list[str]                  # Опасности
    recommended_scenarios: list[str]    # Рекомендуемые сценарии аварий
    required_services: list[str]        # Обязательные аварийные службы
    required_appendices: list[str]      # Обязательные приложения
    applicable_regulations: list[str]   # Применимые нормативы
    warnings: list[str]                 # Предупреждения
```

## Fallback стратегия

1. **Граф доступен** → используется полный контекст
2. **Граф недоступен** → in-memory fallback для известных типов ОПО
3. **Тип ОПО неизвестен** → default context (только обязательные службы)
4. **Adapter падает** → quality review продолжает работу без graph checks

## Текущая реализация

In-memory knowledge base для 4 типов ОПО:
- Сеть газопотребления
- Котельная
- Компрессорная станция
- АЗС / АГНКС

## Future integration

Для подключения реального граф-сервера (Neo4j, Neptune, etc.):

1. Создать `PmlaKnowledgeGraphNeo4jAdapter` наследующий тот же интерфейс
2. Настроить connection string через environment variables
3. Переключить `PmlaKnowledgeGraphAdapter` на новый адаптер
4. Caller code не меняется — тот же `get_context()` интерфейс

## Quality Review checks

| Check | Level | Описание |
|-------|-------|----------|
| `graph_context_empty` | ok | Контекст графа пуст |
| `graph_required_service_missing` | warning | Отсутствует рекомендуемая служба |
| `graph_required_scenario_missing` | warning | Отсутствует рекомендуемый сценарий |
| `graph_required_appendix_missing` | warning | Отсутствует обязательное приложение |

Все graph checks — **warning** (не critical).

## Тесты

13 unit tests в `tests/test_pmla_knowledge_graph_adapter.py`:
- Adapter tests: gas, boiler, unknown, empty, partial match
- Quality review integration: graph checks, warnings, fallback
