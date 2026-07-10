# PMLA RAG Strategy

## Зачем нужен RAG

RAG (Retrieval-Augmented Generation) обогащает генерируемые разделы ПМЛА релевантными справочными данными из базы знаний. Это повышает содержательность текста без увеличения зависимости от LLM.

## Почему только generated_block

```
static_block       → шаблон / код (RAG не нужен)
variable_block     → данные / справочники (RAG не нужен)
generated_block    → LLM + KG + RAG ← вот здесь
appendix_reference → manifest (RAG не нужен)
word_toc_block     → Word TOC (RAG не нужен)
```

RAG нужен только для разделов, которые требуют аналитического текста:
- accident_scenarios (section_2, special_section)
- first_actions (section_10)
- forces_and_resources (section_4, section_6)
- notification (section_8)
- population_safety (section_12)

## Отличие KG от RAG

| Аспект | Knowledge Graph | RAG |
|--------|-----------------|-----|
| Что | Структурные связи (тип → оборудование → опасности) | Справочный текст (нормы, инструкции, примеры) |
| Формат | Списки, связи | Текстовые чанки |
| Использование | Quality review checks | Обогащение generated sections |
| Источник | In-memory / Neo4j | Vector DB / in-memory |

## Текущая реализация

In-memory fallback для 2 типов ОПО:
- Сеть газопотребления (6 разделов)
- Котельная (2 раздела)

## Fallback стратегия

1. **RAG доступен** → используется полный контекст
2. **RAG недоступен** → in-memory fallback для известных типов ОПО
3. **Тип ОПО неизвестен** → default context (только section_10)
4. **Adapter падает** → generation продолжает работу без RAG context

## Интеграция с Assembly Layer

```
RAG Context → enriched_context["rag_contexts"]
            → DocumentContext.rag_contexts
            → RulesEngine / ScenarioEngine (для generated_block)
            → Assembly Layer
            → DOCX
```

## Future integration

Для подключения реальной vector DB (Chroma, Qdrant):

1. Создать `PmlaRagChromaAdapter` наследующий тот же интерфейс
2. Настроить connection string через environment variables
3. Индексировать нормативные документы и примеры ПМЛА
4. Переключить `PmlaRagAdapter` на новый адаптер

## Quality Review

RAG-related checks (warning level):
- `rag_context_unavailable` — RAG adapter недоступен
- `generated_block_without_rag` — generated section без RAG context

## Тесты

14 unit tests в `tests/test_pmla_rag_adapter.py`:
- Adapter tests: gas, boiler, unknown, empty, partial match
- Integration: enriched context includes RAG
- Fallback: works when RAG unavailable
