# Frontend Migration — Next.js + shadcn/ui

## Цель

Перенести наработки современного интерфейса в ISAP как новую основу frontend-части.

## Что изменено

Старый frontend на `Vite + React` заменён на:

- Next.js
- React 19
- TypeScript
- Tailwind CSS v4
- shadcn/ui / Radix UI
- Zustand
- TanStack Query
- Recharts

## Архитектурное правило

Frontend не работает напрямую с базой данных.

Правильная схема:

```text
Next.js frontend
    ↓
FastAPI backend
    ↓
PostgreSQL
```

Запрещено:

```text
Next.js → Prisma → SQLite/PostgreSQL
```

Поэтому из пользовательского интерфейса не переносились:

- `prisma/`
- `db/custom.db`
- `src/lib/db.ts`
- `.env`
- `.git/`
- `mini-services/`
- `.zscripts/`

## Новые разделы меню ISAP

- Обзор
- Задачи
- Организации
- Договоры
- Аналитика
- Экспертизы
- ОПО
- ПМЛА
- Документы
- Справочники
- AI / LM Studio
- Настройки
- Помощь

## API-интеграция

Добавлен API-клиент:

```text
frontend/src/lib/api-client.ts
```

Браузерные запросы идут на same-origin пути `/api/...`; Next.js проксирует их в backend через rewrites. Для локального dev-сервера и Docker build используется серверная переменная:

```env
INTERNAL_API_BASE_URL=http://localhost:8000
```

## Новые страницы

```text
frontend/src/components/dashboard/pmla-page.tsx
frontend/src/components/dashboard/ai-page.tsx
```

`PmlaPage` подключается к backend endpoints:

```http
GET /api/v1/pmla/
GET /api/v1/pmla/expiring?days=30
```

`AiPage` подключается к endpoints:

```http
GET /api/v1/ai/config
GET /api/v1/ai/health
GET /api/v1/ai/embeddings/health
```

## Запуск

```bash
cd frontend
npm install
npm run dev
```

Или через Docker Compose:

```bash
docker compose up frontend
```

## Следующие шаги

1. Подключить реальные Organizations API к странице организаций.
2. Подключить реальные Facilities/OPO API к странице ОПО.
3. Добавить форму создания ПМЛА после Identity/RBAC.
4. Добавить авторизацию и хранение access token.
5. Постепенно заменить mock-данные на backend endpoints.
