"""Read/query application service for PMLA documents.

Keeps database read-model preparation out of FastAPI routers. The service is
intentionally side-effect free: it only reads documents and returns API-ready
plain dictionaries.
"""
from __future__ import annotations

import io
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, select

from src.application.services.calculations import CalculationRegistry
from src.infrastructure.database.models import (
    DocumentModel,
    DocumentVersionModel,
    HazardousFacilityModel,
    OrganizationModel,
)
from src.infrastructure.repositories.document_repo import DocumentRepository


class PmlaQueryService:
    """Read-model queries for PMLA screens and document metadata."""

    def __init__(self, document_repo: DocumentRepository) -> None:
        self.document_repo = document_repo

    async def get_preview(self, document_id: UUID) -> dict:
        """Return HTML-preview friendly structure for a PMLA document."""
        doc = await self.document_repo.get(document_id)
        if doc is None:
            raise ValueError("Документ не найден")

        facility_name = ""
        org_name = ""
        if doc.hazardous_facility_id:
            result = await self.document_repo.session.execute(
                select(HazardousFacilityModel.name, OrganizationModel.name.label("org_name"))
                .outerjoin(
                    OrganizationModel,
                    HazardousFacilityModel.organization_id == OrganizationModel.id,
                )
                .where(HazardousFacilityModel.id == doc.hazardous_facility_id)
            )
            row = result.first()
            if row:
                facility_name = row[0] or ""
                org_name = row[1] or ""

        generation_meta = doc.generation_meta or {}
        return {
            "document_id": str(doc.id),
            "title": doc.title or "ПМЛА",
            "facility_name": facility_name,
            "organization_name": org_name,
            "status": doc.status,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
            "sections": self._extract_sections(doc.content_docx),
            "calculations": generation_meta.get("calculation_results", []),
            "issues": generation_meta.get("validation_issues", []),
        }

    async def list_documents(self, *, skip: int = 0, limit: int = 100) -> list[dict]:
        """List PMLA documents with facility names."""
        query = (
            select(DocumentModel, HazardousFacilityModel.name.label("facility_name"))
            .outerjoin(
                HazardousFacilityModel,
                DocumentModel.hazardous_facility_id == HazardousFacilityModel.id,
            )
            .where(DocumentModel.document_type == "pmla")
            .order_by(DocumentModel.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.document_repo.session.execute(query)
        rows = result.all()
        return [
            {
                "id": str(doc.id),
                "title": doc.title,
                "status": doc.status,
                "facility_id": str(doc.hazardous_facility_id) if doc.hazardous_facility_id else None,
                "facility_name": facility_name,
                "organization_id": str(doc.organization_id) if doc.organization_id else None,
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
            }
            for doc, facility_name in rows
        ]

    async def list_expiring_documents(self, *, days: int = 30) -> list[dict]:
        """List approved PMLA documents whose review date is near."""
        now = datetime.now(UTC).replace(tzinfo=None)
        threshold = now + timedelta(days=days)
        query = (
            select(DocumentModel, HazardousFacilityModel.name.label("facility_name"))
            .outerjoin(
                HazardousFacilityModel,
                DocumentModel.hazardous_facility_id == HazardousFacilityModel.id,
            )
            .where(
                and_(
                    DocumentModel.document_type == "pmla",
                    DocumentModel.status == "approved",
                    DocumentModel.review_date.isnot(None),
                    DocumentModel.review_date <= threshold,
                    DocumentModel.review_date >= now,
                )
            )
            .order_by(DocumentModel.review_date.asc())
        )
        result = await self.document_repo.session.execute(query)
        rows = result.all()
        return [
            {
                "id": str(doc.id),
                "title": doc.title,
                "facility_name": facility_name,
                "status": doc.status,
                "review_date": doc.review_date.isoformat() if doc.review_date else None,
                "days_remaining": (doc.review_date - now).days if doc.review_date else None,
            }
            for doc, facility_name in rows
        ]

    async def list_overdue_documents(self) -> list[dict]:
        """List approved PMLA documents with overdue review date."""
        now = datetime.now(UTC).replace(tzinfo=None)
        query = (
            select(DocumentModel, HazardousFacilityModel.name.label("facility_name"))
            .outerjoin(
                HazardousFacilityModel,
                DocumentModel.hazardous_facility_id == HazardousFacilityModel.id,
            )
            .where(
                and_(
                    DocumentModel.document_type == "pmla",
                    DocumentModel.status == "approved",
                    DocumentModel.review_date.isnot(None),
                    DocumentModel.review_date < now,
                )
            )
            .order_by(DocumentModel.review_date.asc())
        )
        result = await self.document_repo.session.execute(query)
        rows = result.all()
        return [
            {
                "id": str(doc.id),
                "title": doc.title,
                "facility_name": facility_name,
                "status": doc.status,
                "review_date": doc.review_date.isoformat() if doc.review_date else None,
                "days_overdue": (now - doc.review_date).days if doc.review_date else None,
            }
            for doc, facility_name in rows
        ]

    async def list_versions(self, document_id: UUID) -> list[dict]:
        """Return version history of a PMLA document."""
        doc = await self.document_repo.get(document_id)
        if doc is None:
            raise ValueError("Документ не найден")

        result = await self.document_repo.session.execute(
            select(DocumentVersionModel)
            .where(DocumentVersionModel.document_id == document_id)
            .order_by(DocumentVersionModel.version_number.desc())
        )
        versions = list(result.scalars().all())
        return [
            {
                "id": str(version.id),
                "version_number": version.version_number,
                "reviewer_id": str(version.reviewer_id) if version.reviewer_id else None,
                "reviewer_decision": version.reviewer_decision,
                "reviewer_comments": version.reviewer_comments or [],
                "regulatory_snapshot": version.regulatory_snapshot or [],
                "prompt_version": version.prompt_version,
                "template_version": version.template_version,
                "created_at": version.created_at.isoformat() if version.created_at else None,
            }
            for version in versions
        ]

    def list_calculation_methods(self) -> list[dict]:
        """Return available deterministic calculation methods."""
        return CalculationRegistry.list_methods()

    def _extract_sections(self, content_docx: bytes | None) -> list[dict]:
        if not content_docx:
            return []
        try:
            import docx

            document = docx.Document(io.BytesIO(content_docx))
        except Exception:
            return []

        sections: list[dict] = []
        current_section: dict | None = None
        for para in document.paragraphs:
            text = para.text.strip()
            if not text:
                continue
            style_name = para.style.name if para.style else ""
            is_heading = "Heading" in style_name or (
                bool(para.runs) and bool(para.runs[0].bold) and len(text) > 5
            )
            if is_heading:
                if current_section:
                    sections.append(current_section)
                current_section = {"title": text, "content": []}
            elif current_section is not None:
                current_section["content"].append(text)
            else:
                current_section = {"title": "", "content": [text]}
        if current_section:
            sections.append(current_section)
        return sections
