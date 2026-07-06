# Рефакторинг генератора ПМЛА — Отчёт прогресса

**Дата:** 2026-07-06
**Статус:** ✅ Полная архитектура 6 движков + интеграция + application services + Smart Import
**Коммиты:** `ce3f626` (движки), `7b24290` (интеграция), `70549a6` (шаблоны сценариев)

---

## Архитектура 6 движков

```
backend/src/application/engines/
├── __init__.py
├── base.py                    # BaseEngine, DocumentContext, SectionContent
├── router.py                  # EngineRouter
├── template_engine.py         # 10 разделов (0% AI)
├── data_engine.py             # 8 разделов (0% AI)
├── scenario_engine.py         # 2 раздела (0% AI)
├── rules_engine.py            # 6 разделов (0% AI)
├── narrative_engine.py        # 1 раздел (~10% AI)
└── table_engine.py            # Унифицированный рендер таблиц

backend/src/application/services/
├── engine_integration.py      # create_engine_router(), build_document_context()
└── enhanced_generator.py      # _generate_sections_via_engines() → EngineRouter

backend/templates/pmla/scenario_templates/
├── gas_network.json           # 5 сценариев (Сеть газопотребления)
├── oil_extraction.json        # 3 сценария (Нефтедобыча)
├── oil_refinery.json          # 3 сценария (Нефтепереработка)
├── chemical_production.json   # 2 сценария (Химическое производство)
├── gas_distribution.json      # 2 сценария (Газораспределение)
└── transport.json             # 2 сценария (Транспортировка)
```

### Движки по разделам:

| Движок | Разделы | AI | Статус |
|--------|---------|-----|--------|
| TemplateEngine | title_page, correction_log, toc, abbreviations, terms, appendix_1,2,5, bibliography, familiarization_sheet | 0% | ✅ |
| DataEngine | section_1,3,4,6,8,13, appendix_3,4 | 0% | ✅ |
| ScenarioEngine | section_2, special_section | 0% | ✅ |
| RulesEngine | section_5,7,9,10,11,12 | 0% | ✅ |
| NarrativeEngine | introduction | ~10% | ✅ |

### Шаблоны сценариев (17 сценариев):

| Тип ОПО | Кол-во | Коды |
|---------|--------|------|
| Сеть газопотребления | 5 | С-1...С-5 |
| Нефтедобыча | 3 | НД-1...НД-3 |
| Нефтепереработка | 3 | НП-1...НП-3 |
| Химическое производство | 2 | ХП-1...ХП-2 |
| Газораспределение | 2 | ГР-1...ГР-2 |
| Транспортировка | 2 | ТР-1...ТР-2 |

### Тесты:

- 101 тест на движки
- 201/201 общих тестов проходят

---

## Что сделано:

1. ✅ BaseEngine ABC + DocumentContext + SectionContent
2. ✅ TemplateEngine — 10 чистых Jinja2-шаблонов
3. ✅ TableEngine — унифицированный рендер таблиц
4. ✅ ScenarioEngine — 17 сценариев для 6 типов ОПО
5. ✅ DataEngine — 8 разделов из БД
6. ✅ RulesEngine — 6 разделов по правилам
7. ✅ NarrativeEngine — introduction с LLM + fallback
8. ✅ EngineRouter — маршрутизация + отчёт
9. ✅ Интеграция с EnhancedDocumentGenerator
10. ✅ Шаблоны для всех 6 типов ОПО из scenario_matrix
11. ✅ Рефакторинг роутеров (pmla.py 1112→~300, pmla_stream.py 313→~120)
12. ✅ Application services: PmlaGenerationService, PmlaQueryService, PmlaExportService, PmlaReviewWorkflowService
13. ✅ Smart Import Center: 3 профиля, 5 таблиц, API + тесты

---

## Дальнейшие шаги:

1. Подключение accident_samples из БД в DataEngine (сейчас 9 hardcoded)
2. Оптимизация времени генерации (параллельная генерация)
3. Сравнение с эталонным документом
