# PMLA MVP Release Checklist

**Дата:** 2026-07-08
**Версия:** MVP 1.0
**Статус:** Ready for internal testing

---

## 1. Что входит в MVP

| # | Функционал | Статус |
|---|------------|--------|
| 1 | Карточка ОПО (список, детали) | ✅ |
| 2 | Анкета ПМЛА (создание, редактирование блоков) | ✅ |
| 3 | Заполнение блоков анкеты | ✅ |
| 4 | Справочники ПАСФ / АСФ | ✅ |
| 5 | Справочники аварийных служб | ✅ |
| 6 | Smart Import Excel/CSV для справочников | ✅ |
| 7 | Экспорт справочников в CSV | ✅ |
| 8 | Редактирование записей в справочниках | ✅ |
| 9 | Генерация ПМЛА (6 движков, 29 разделов) | ✅ |
| 10 | DOCX структура (титульный лист, заголовки, таблицы) | ✅ |
| 11 | Quality Review (10 проверок, скоринг) | ✅ |
| 12 | История версий документов | ✅ |
| 13 | Скачивание DOCX | ✅ |
| 14 | Ручная проверка документа (workflow) | ✅ |
| 15 | API smoke test (3 теста, 8 endpoints) | ✅ |
| 16 | Service-level E2E test (6 тестов) | ✅ |

---

## 2. Что не входит в MVP

| # | Функционал | Причина |
|---|------------|---------|
| 1 | Полноценный RAG по образцам ПМЛА | Требует индексации корпуса документов |
| 2 | Автоматический геокодинг адресов | Внешний API, требует ключа |
| 3 | Расчёт маршрута и времени прибытия | Геоданные, внешние API |
| 4 | Сложное согласование по ролям | Требует авторизации |
| 5 | Электронная подпись | Юридическая интеграция |
| 6 | Автоматическая отправка клиенту | Email/WhatsApp интеграция |
| 7 | Полная нормативная экспертиза без инженера | Юридическая ответственность |
| 8 | Production deployment | Инфраструктура, CI/CD |
| 9 | PDF экспорт | Конвертация LibreOffice |
| 10 | Уведомления о смене статуса | Email/webhook |

---

## 3. Проверенный пользовательский сценарий

```
1. Инженер открывает список ОПО.
2. Открывает карточку ОПО.
3. Создаёт / открывает анкету ПМЛА.
4. Заполняет данные анкеты:
   - история инцидентов
   - сценарии аварий
   - ресурсы организации
   - схема оповещения
   - финансовый резерв
   - страхование
   - приложения
5. Выбирает ПАСФ из справочника.
6. Добавляет аварийные службы из справочника.
7. Генерирует ПМЛА.
8. Проверяет quality review.
9. Открывает карточку документа.
10. Скачивает DOCX.
11. Проводит ручную проверку:
    - needs_review → in_review
    - in_review → approved
    - approved → ready_to_issue
    - ready_to_issue → issued
```

---

## 4. Проверенные backend endpoints

| Endpoint | Метод | Описание | Статус |
|----------|-------|----------|--------|
| `/api/v1/facilities/` | GET | Список ОПО | ✅ |
| `/api/v1/facilities/{id}` | GET | Карточка ОПО | ✅ |
| `/api/v1/pmla-questionnaires/facility/{id}` | GET | Анкета по ОПО | ✅ |
| `/api/v1/pmla-questionnaires/facility/{id}` | POST | Создать анкету | ✅ |
| `/api/v1/pmla-questionnaires/{id}/blocks/{name}` | PATCH | Обновить блок | ✅ |
| `/api/v1/pmla-questionnaires/{id}/generate` | POST | Генерация ПМЛА | ✅ |
| `/api/v1/pmla-questionnaires/{id}/documents` | GET | Список документов | ✅ |
| `/api/v1/pmla/{id}/download` | GET | Скачать DOCX | ✅ |
| `/api/v1/pmla/{id}/review` | GET | Статус проверки | ✅ |
| `/api/v1/pmla/{id}/review` | PATCH | Обновить статус | ✅ |
| `/api/v1/directories/pasf/` | GET | Список ПАСФ | ✅ |
| `/api/v1/directories/pasf/` | POST | Создать ПАСФ | ✅ |
| `/api/v1/directories/pasf/{id}` | PATCH | Редактировать ПАСФ | ✅ |
| `/api/v1/directories/pasf/{id}` | DELETE | Удалить ПАСФ | ✅ |
| `/api/v1/directories/pasf/export/csv` | GET | Экспорт ПАСФ | ✅ |
| `/api/v1/directories/emergency-services/` | GET | Список служб | ✅ |
| `/api/v1/directories/emergency-services/` | POST | Создать службу | ✅ |
| `/api/v1/directories/emergency-services/{id}` | PATCH | Редактировать | ✅ |
| `/api/v1/directories/emergency-services/{id}` | DELETE | Удалить | ✅ |
| `/api/v1/directories/emergency-services/export/csv` | GET | Экспорт служб | ✅ |
| `/api/v1/imports/{type}/preview` | POST | Preview импорта | ✅ |
| `/api/v1/imports/jobs/{id}/confirm` | POST | Подтвердить импорт | ✅ |

---

## 5. Проверенные frontend экраны

| Экран | Описание | Статус |
|-------|----------|--------|
| Overview | Главная страница с дашбордом | ✅ |
| OPO List | Список ОПО | ✅ |
| OPO Detail | Карточка ОПО с секцией ПМЛА | ✅ |
| Questionnaire | Анкета ПМЛА (вкладки, блоки) | ✅ |
| Directories | Справочники ПАСФ / Службы | ✅ |
| Document List | Список документов ПМЛА | ✅ |
| Document Detail | Карточка документа + review workflow | ✅ |
| Import Widget | Импорт Excel/CSV | ✅ |

---

## 6. DOCX generation checklist

| Проверка | Статус |
|----------|--------|
| Титульный лист с данными ОПО | ✅ |
| Заголовки разделов (Heading 1) | ✅ |
| Таблицы с границами (Table Grid) | ✅ |
| Шрифт Times New Roman 12pt | ✅ |
| Поля страницы A4 (3cm/1.5cm/2cm) | ✅ |
| Пустые значения = "не указано" | ✅ |
| Нет None/null/undefined в DOCX | ✅ |
| Качественные фразы на русском | ✅ |
| Приложения (checklist) | ✅ |

---

## 7. Review workflow checklist

| Проверка | Статус |
|----------|--------|
| Review status добавлен в DocumentModel | ✅ |
| Migration 017 создана | ✅ |
| GET/PATCH endpoints работают | ✅ |
| Transition rules определены | ✅ |
| Недопустимые переходы возвращают 400 | ✅ |
| UI показывает кнопки по allowed_transitions | ✅ |
| UX warning о обязательной проверке | ✅ |
| issued_at заполняется при issued | ✅ |

---

## 8. Smart Import checklist

| Проверка | Статус |
|----------|--------|
| Parser поддерживает Excel/CSV | ✅ |
| 3 профиля: fire_departments, emergency_services, pasf_units | ✅ |
| Дедупликация по name+address | ✅ |
| Frontend ImportWidget: preview → confirm | ✅ |
| Нормализация типов служб (RU → EN) | ✅ |

---

## 9. Git hygiene checklist

| Проверка | Статус |
|----------|--------|
| `.next` не коммитится | ✅ |
| `node_modules` не коммитится | ✅ |
| `.env.local` не коммитится | ✅ |
| `tsconfig.tsbuildinfo` не коммитится | ✅ |
| `*.log` не коммитится | ✅ |
| `output.docx` не коммитится | ✅ |
| `generated_documents/` не коммитится | ✅ |

---

## 10. Known limitations

1. **LLM генерация** — introduction генерируется через LLM (если доступен), остальные разделы детерминированы
2. **Нет авторизации** — все endpoints доступны без аутентификации
3. **Нет PDF** — только DOCX формат
4. **Нет email** — уведомления не реализованы
5. **Fuzzy search** — поиск в справочниках только по ILIKE, нет транслитерации
6. **Одна Organization** — тесты используют одну организацию
7. **Версионирование** — каждая генерация создаёт новую запись, старые не удаляются

---

## 11. Следующие этапы после MVP

| # | Приоритет | Задача |
|---|-----------|--------|
| 1 | HIGH | Авторизация (роли: admin, engineer, viewer) |
| 2 | HIGH | PDF экспорт (LibreOffice headless) |
| 3 | MEDIUM | Email уведомления о смене статуса |
| 4 | MEDIUM | Расширенный RAG по образцам ПМЛА |
| 5 | MEDIUM | Автоматический геокодинг |
| 6 | LOW | Электронная подпись |
| 7 | LOW | Мульти-tenant (несколько организаций) |
| 8 | LOW | Аудит-лог действий пользователя |

---

## Smoke commands

```powershell
# Backend tests
cd "D:\Git Hub\ISAP2\isap\backend"
python -m pytest -q

# Frontend build
cd "D:\Git Hub\ISAP2\isap\frontend"
npm run build

# Git hygiene
cd "D:\Git Hub\ISAP2"
git status
git ls-files | Select-String "\.next|node_modules|\.env.local|tsconfig.tsbuildinfo|\.log|\.zip|\.patch|output.docx|generated_documents"
```

---

## Current state

| Метрика | Значение |
|---------|----------|
| Backend tests | 359 passed |
| Frontend build | ✓ Compiled successfully |
| E2E service-level tests | 6 |
| E2E API smoke tests | 3 |
| Total E2E tests | 9 |
| Last commit | `5a4882c` |
