# ISAP2 PMLA MVP Release Checklist

Date: 2026-07-08
Version: PMLA MVP 1.0
Stage: internal validation

## 1. MVP Scope

PMLA MVP 1.0 includes the technical path needed to prepare a first generated PMLA document for engineering review:

- OPO registry and OPO card.
- PMLA questionnaire linked to an OPO.
- PASF/ASF directories.
- Emergency services directories.
- Smart Import from Excel/CSV for directory data.
- DOCX generation.
- Quality review for generated PMLA documents.
- Document version history.
- DOCX download.
- Manual document review workflow.
- Service-level E2E tests.
- API smoke tests.

## 2. Out Of MVP Scope

The following items are intentionally not part of PMLA MVP 1.0:

- Full RAG over PMLA samples.
- Automatic geocoding.
- Route and arrival-time calculation.
- Electronic signature.
- Automatic delivery to the client.
- Full regulatory expert review without an engineer.
- Production deployment.

These items must not be added during the internal validation stage unless a separate post-MVP task explicitly changes scope.

## 3. Verified User Scenario

The MVP validation scenario already covered by current checks is:

1. Open an OPO.
2. Open or create a PMLA questionnaire.
3. Fill in questionnaire data.
4. Select PASF/ASF units and emergency services.
5. Generate a PMLA document.
6. Open quality review.
7. Download DOCX.
8. Perform manual document review.
9. Move the document to "Ready to issue" or "Issued to client".

## 4. Verified Endpoint Groups

The internal validation baseline covers these endpoint groups:

- Questionnaire: open/create questionnaire and update questionnaire blocks.
- Generate: generate a PMLA document from questionnaire data.
- Documents: list generated documents and versions.
- Download: download generated DOCX.
- Review workflow: read review state and update manual review status.

## 5. Known Limitations

- Engineer review remains mandatory before using a generated document as a client-facing result.
- Generated text may require manual correction, especially for site-specific operational details.
- Full RAG over real PMLA samples is not included.
- Automatic geocoding is not included.
- Route and arrival-time calculations are not included.
- Electronic signature is not included.
- Automatic client delivery is not included.
- Production deployment, monitoring, backups, and CI/CD hardening are not included.
- Production-grade authorization and role separation still require hardening before real deployment.

## 6. Next Steps After MVP

- Run internal validation on real or anonymized OPO data.
- Record engineer comments against generated DOCX output.
- Classify findings as template, questionnaire, directory, or manual-text gaps.
- Stabilize the questionnaire fields that real data shows are missing.
- Improve templates only where repeated validation findings justify it.
- Decide which post-MVP items should enter the next milestone.
- Keep production deployment out of scope until validation results are reviewed.
