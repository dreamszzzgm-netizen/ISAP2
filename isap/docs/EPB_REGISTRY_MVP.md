# EPB Registry MVP

**Date:** 2026-07-10
**Status:** MVP Complete
**Next:** EPB enhancements (attachments, notifications, reports)

---

## Goal

Create a basic module for tracking Expertises of Industrial Safety (Экспертизы промышленной безопасности).

Business context: ~800 expertises per year.

---

## Data Model

### EpbExpertise

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| organization_id | UUID FK | Links to organizations |
| facility_id | UUID FK | Links to hazardous_facilities (optional) |
| registry_number | String | Registry number |
| conclusion_number | String | Conclusion number |
| conclusion_date | Date | Date of conclusion |
| valid_until | Date | Validity period end |
| expert_organization | String | Expert organization name |
| expert_name | String | Expert name |
| object_name | String | Object name |
| hazard_class | String | Hazard class |
| status | String | draft/active/expires_soon/expired/archived |
| notes | Text | Notes |
| created_at | DateTime | Creation timestamp |
| updated_at | DateTime | Last update timestamp |

### Status Logic

```
valid_until < today → expired
valid_until <= today + 90 days → expires_soon
else → active
```

Status is computed on read, stored for filtering.

---

## API

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | /api/v1/epb | List with filters |
| POST | /api/v1/epb | Create new |
| GET | /api/v1/epb/{id} | Get by ID |
| PATCH | /api/v1/epb/{id} | Update |
| DELETE | /api/v1/epb/{id} | Archive (soft delete) |

### Filters

- `organization_id` — filter by organization
- `facility_id` — filter by facility
- `status` — filter by status
- `expires_before` — filter by valid_until
- `expires_after` — filter by valid_until
- `search` — search in conclusion_number, registry_number, object_name, expert_organization

---

## UI

### EPB Registry Page

- List of expertises with status badges
- Search and filter controls
- Click to view detail

### EPB Detail Page

- Main info (conclusion number, dates, status)
- Expert organization info
- Notes
- File attachments (placeholder for future)

---

## MVP Limitations

| Limitation | Impact | Workaround |
|-----------|--------|------------|
| No file attachments | Can't store conclusion PDFs | Manual storage |
| No expiry notifications | Must check manually | Future: email reminders |
| No Excel import/export | Manual data entry | Future: Excel support |
| No reports/dashboard | No analytics | Future: reports module |

---

## Post-MVP Backlog

1. Excel import/export
2. File attachments for conclusions
3. Expiry notifications (email reminders)
4. Reports and dashboard widgets
5. Bulk update
6. Link to contracts
7. AI extraction from old conclusions

---

## Files

| File | Purpose |
|------|---------|
| `backend/src/domain/epb/models.py` | Domain model |
| `backend/src/infrastructure/database/models.py` | SQLAlchemy model |
| `backend/src/infrastructure/repositories/epb_repo.py` | Repository |
| `backend/src/api/routers/epb.py` | API router |
| `backend/alembic/versions/018_add_epb.py` | Migration |
| `frontend/src/components/dashboard/epb-page.tsx` | UI page |
