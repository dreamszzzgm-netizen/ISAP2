# PMLA Real Data Validation Plan

Date: 2026-07-08
Stage: PMLA MVP 1.0 internal validation

## Goal

Validate PMLA MVP 1.0 on a real or anonymized OPO and determine whether the generated DOCX can be used as an engineering draft.

This stage does not add RAG, geocoding, route calculation, electronic signature, automatic client delivery, or production deployment.

## Input Data

Use one real or anonymized validation case:

- Organization.
- OPO card data.
- PMLA questionnaire data.
- PASF/ASF directory entries.
- Emergency services directory entries.
- Any known engineering constraints or comments for the selected OPO.

## Validation Scenario

1. Select an organization.
2. Select an existing OPO or create a new OPO.
3. Fill in the PMLA questionnaire.
4. Import or verify PASF/ASF directory data.
5. Import or verify emergency services directory data.
6. Select the required PASF/ASF units and emergency services.
7. Generate DOCX.
8. Open quality review.
9. Download DOCX.
10. Have an engineer review the document.
11. Record comments and findings.
12. Make a validation decision.

## Engineer Review Checklist

During review, check:

- Whether the generated document can be used as a draft basis.
- Whether OPO and organization data are correctly reflected.
- Whether questionnaire answers appear in the expected sections.
- Whether PASF/ASF and emergency services are present and readable.
- Whether quality review flags useful issues.
- Whether generated text contains placeholders, missing values, or incorrect assumptions.
- Whether the document requires template, questionnaire, directory, or manual text improvements.

## Finding Categories

Each comment should be assigned to one of these categories:

- Template gap: the DOCX structure, wording, or section layout needs improvement.
- Questionnaire gap: the system needs additional input fields.
- Directory gap: PASF/ASF or emergency service reference data is missing or insufficient.
- Manual text required: the content depends on expert judgement and should remain manual.
- Data issue: source OPO, organization, or directory data is incomplete or inconsistent.
- No action: acceptable for MVP internal validation.

## Decision Options

After review, choose one decision:

- Can be used as a basis.
- Requires template improvement.
- Requires questionnaire expansion.
- Requires directory improvement.
- Requires manual text.

## Validation Output

Record the result with:

- Organization and OPO identifier or anonymized label.
- Generated document version.
- Review date.
- Engineer reviewer.
- Decision option.
- Findings grouped by category.
- Recommended next action.

## Exit Criteria

Internal validation is complete when:

- At least one real or anonymized OPO scenario has been executed end to end.
- DOCX output has been reviewed by an engineer.
- Findings have been classified.
- A decision has been recorded.
- Post-MVP work items are separated from MVP release scope.
