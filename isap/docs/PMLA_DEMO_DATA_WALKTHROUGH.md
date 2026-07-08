# PMLA Demo Data Walkthrough

This guide describes how to use the anonymized demo dataset for PMLA MVP 1.0 internal validation.

The demo data is local-only and is not intended for production deployment. It does not add RAG, geocoding, route calculation, electronic signature, or automatic client delivery.

## 1. Load Demo Data

From the backend folder, run the existing migrations first, then load the demo dataset:

```powershell
cd "D:\Git Hub\ISAP2\isap\backend"
alembic upgrade head
python scripts\load_demo_pmla_data.py
```

The script is idempotent. It searches the demo organization by conditional INN `0000000000`, the OPO by conditional registration number `А00-00000-0001`, and reference records by their demo identifiers.

The source data is stored in:

```text
backend/data/demo_pmla_validation.json
```

## 2. Start Backend And Frontend

Option A: Docker Compose from the project folder:

```powershell
cd "D:\Git Hub\ISAP2\isap"
docker-compose up --build
```

Option B: local development:

```powershell
cd "D:\Git Hub\ISAP2\isap\backend"
uvicorn src.main:app --reload
```

In a second terminal:

```powershell
cd "D:\Git Hub\ISAP2\isap\frontend"
npm run dev
```

Open:

```text
http://localhost:3000
```

Backend API docs are available at:

```text
http://localhost:8000/docs
```

## 3. Open The Demo OPO

In the frontend, open the OPO section and find:

```text
Сеть газопотребления демо-производственной площадки
```

Expected demo values:

- Organization: `ООО "Демо Промышленная Безопасность"`
- INN: `0000000000`
- OPO registration number: `А00-00000-0001`
- Hazard class: `3`
- Facility type: `Сеть газопотребления`

## 4. Open Or Create The PMLA Questionnaire

Open the OPO card and go to the PMLA questionnaire.

The seed script creates a pre-filled questionnaire. If the UI creates or refreshes the questionnaire, verify that the following blocks remain filled:

- Incident history: no accidents/incidents.
- Operation mode: one shift, dispatcher is available.
- Accident scenarios: gas leak, ignition, and a manual maintenance scenario.
- Organization resources: gas analyzer, fire extinguishing equipment, emergency tool kit.
- Notification scheme: dispatcher, engineer, PASF, fire service, meeting point.
- Financial reserve: demo reserve order and amount.
- Insurance: demo insurance contract.
- Attachments checklist: OPO layout, notification scheme, resources list, PASF certificate, insurance contract.

## 5. Verify PASF/ASF And Emergency Services

Open the directories section and verify that these records exist.

PASF/ASF:

```text
Демо ПАСФ "Безопасность"
```

Emergency services:

- `Демо пожарно-спасательная часть`
- `Демо станция скорой медицинской помощи`
- `Демо отдел полиции`
- `Демо аварийная газовая служба`
- `Демо ЕДДС муниципального образования`

In the questionnaire, verify that the demo PASF/ASF and all five emergency services are selected.

## 6. Generate DOCX

From the questionnaire page, run PMLA generation.

The expected flow:

1. Questionnaire data is converted into generation context.
2. DOCX is generated.
3. Quality review is produced.
4. A document version is saved.
5. DOCX download becomes available.

## 7. Open Quality Review

Open the generated document and inspect quality review.

Check:

- Whether missing-data warnings are reasonable.
- Whether PASF/ASF and emergency services are reflected.
- Whether accident scenarios are visible.
- Whether any generated text contains placeholders or irrelevant text.

## 8. Download DOCX

Download the generated DOCX from the document page.

Also available through the API:

```text
GET /api/v1/pmla/{document_id}/download
```

## 9. Engineer Review Checklist

An engineer should verify:

- OPO name, registration number, hazard class, and address.
- Organization name, conditional INN, manager, and contact person.
- Accident/incident history states that there were no incidents.
- Gas leak and ignition scenarios are present and technically plausible.
- PASF/ASF data is present and readable.
- Fire, medical, police, gas, and EDDS services are present.
- Notification order is understandable.
- Financial reserve and insurance blocks are present.
- Attachments checklist is included.
- The document can be used as a draft basis or findings are classified.

## 10. Validation Decision

After review, choose one decision:

- Can be used as a basis.
- Requires template improvement.
- Requires questionnaire expansion.
- Requires directory improvement.
- Requires manual text.

Record the result in the internal validation notes and keep post-MVP improvements separate from MVP release scope.
