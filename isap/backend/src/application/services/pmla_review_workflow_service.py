"""Review/version application service for PMLA documents."""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update

from src.application.services.ai_reviewer import AIReviewer
from src.application.services.pmla_generation_service import PmlaGenerationService
from src.application.services.review_service import ReviewService
from src.application.services.types import Issue
from src.infrastructure.database.models import DocumentVersionModel
from src.infrastructure.llm.providers import get_llm_provider
from src.infrastructure.repositories.document_repo import DocumentRepository
from src.infrastructure.repositories.regulatory_repo import RegulatoryRepository
from src.infrastructure.repositories.scenario_matrix_repo import (
    ScenarioMatrixRepository,
)

logger = logging.getLogger(__name__)


class PmlaReviewWorkflowService:
    """Coordinates human review, automatic regeneration and AI review."""

    def __init__(
        self,
        document_repo: DocumentRepository,
        regulatory_repo: RegulatoryRepository | None = None,
        scenario_matrix_repo: ScenarioMatrixRepository | None = None,
        sample_repo=None,
    ) -> None:
        self.document_repo = document_repo
        self.regulatory_repo = regulatory_repo
        self.scenario_matrix_repo = scenario_matrix_repo
        self.sample_repo = sample_repo

    async def get_status(self, document_id: UUID) -> dict:
        review_service = ReviewService(self.document_repo)
        return await review_service.get_status(document_id)

    async def review(
        self,
        *,
        document_id: UUID,
        reviewer_id: str | UUID,
        decision: str,
        comments: list[dict] | None = None,
    ) -> dict:
        """Approve/reject a document and optionally auto-regenerate rejected sections."""
        review_service = ReviewService(self.document_repo)
        if decision == "approved":
            await review_service.approve(
                document_id=document_id,
                reviewer_id=reviewer_id,
                comments=comments,
            )
            return {"status": "approved", "review_status": "approved"}

        if decision != "rejected":
            raise ValueError("decision должен быть 'approved' или 'rejected'")

        issues = [
            Issue(
                section=comment.get("section", ""),
                reason=comment.get("reason", ""),
                severity=comment.get("severity", "error"),
            )
            for comment in (comments or [])
        ]
        reject_result = await review_service.reject(
            document_id=document_id,
            reviewer_id=reviewer_id,
            issues=issues,
        )

        if reject_result["action"] == "regenerated" and reject_result["sections"]:
            await self._auto_regenerate_sections(document_id, reject_result["sections"])

        # Section regeneration uses the generation pipeline, which normally
        # resets a document to pending_review/needs_review.  A reviewer return
        # is still a needs-changes decision, so persist that decision last.
        await self.document_repo.update(
            document_id,
            {
                "status": "needs_changes",
                "review_status": "needs_changes",
                "updated_at": datetime.now(UTC).replace(tzinfo=None),
            },
        )

        return {
            "status": "needs_changes",
            "review_status": "needs_changes",
            "action": reject_result["action"],
            "regenerated_sections": reject_result["sections"],
            "regeneration_count": reject_result["regeneration_count"],
        }

    async def restore_version(self, document_id: UUID, version_id: UUID) -> dict:
        doc = await self.document_repo.get(document_id)
        if doc is None:
            raise ValueError("Документ не найден")

        result = await self.document_repo.session.execute(
            select(DocumentVersionModel).where(DocumentVersionModel.id == version_id)
        )
        version = result.scalar_one_or_none()
        if version is None:
            raise LookupError("Версия не найдена")
        if not version.content_docx:
            raise ValueError("Версия не содержит DOCX")

        await self.document_repo.update(
            document_id,
            {
                "content_docx": version.content_docx,
                "rendered_sections": (
                    version.input_data.get("rendered_sections", {})
                    if isinstance(version.input_data, dict)
                    else {}
                ),
                "status": "pending_review",
                "review_status": "needs_review",
                "updated_at": datetime.now(UTC).replace(tzinfo=None),
            },
        )
        return {
            "document_id": str(document_id),
            "restored_from_version": version.version_number,
            "status": "pending_review",
            "review_status": "needs_review",
        }

    async def run_ai_review(self, document_id: UUID) -> dict:
        doc = await self.document_repo.get(document_id)
        if doc is None:
            raise ValueError("Документ не найден")
        if not doc.rendered_sections:
            raise ValueError("Документ не содержит отрендеренных разделов")

        version = await self._get_latest_version(document_id)
        context = version.input_data if version and isinstance(version.input_data, dict) else {}

        try:
            llm = get_llm_provider()
        except Exception as exc:  # noqa: BLE001 - caller maps to 503
            raise ConnectionError("LLM недоступен") from exc

        reviewer = AIReviewer(llm)
        ai_result = await reviewer.review(doc.rendered_sections, context)
        if version:
            await self.document_repo.session.execute(
                update(DocumentVersionModel)
                .where(DocumentVersionModel.id == version.id)
                .values(
                    ai_review_confidence=ai_result.overall_confidence,
                    ai_review_decision=ai_result.decision,
                    ai_review_items=[
                        {
                            "id": item.check_id,
                            "name": item.check_name,
                            "passed": item.passed,
                            "confidence": item.confidence,
                            "details": item.details,
                        }
                        for item in ai_result.items
                    ],
                    ai_review_summary=ai_result.summary,
                )
            )
            await self.document_repo.session.commit()

        return {
            "document_id": str(document_id),
            "confidence": ai_result.overall_confidence,
            "decision": ai_result.decision,
            "items": [
                {
                    "id": item.check_id,
                    "name": item.check_name,
                    "passed": item.passed,
                    "confidence": item.confidence,
                    "details": item.details,
                }
                for item in ai_result.items
            ],
            "summary": ai_result.summary,
        }

    async def get_ai_review(self, document_id: UUID) -> dict:
        doc = await self.document_repo.get(document_id)
        if doc is None:
            raise ValueError("Документ не найден")

        version = await self._get_latest_version(document_id)
        if version is None or version.ai_review_decision is None:
            raise LookupError("AI-ревью не проводилось")

        return {
            "document_id": str(document_id),
            "version_number": version.version_number,
            "confidence": float(version.ai_review_confidence) if version.ai_review_confidence else None,
            "decision": version.ai_review_decision,
            "items": version.ai_review_items or [],
            "summary": version.ai_review_summary,
        }

    async def _get_latest_version(self, document_id: UUID) -> DocumentVersionModel | None:
        result = await self.document_repo.session.execute(
            select(DocumentVersionModel)
            .where(DocumentVersionModel.document_id == document_id)
            .order_by(DocumentVersionModel.version_number.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _auto_regenerate_sections(self, document_id: UUID, sections: list[str]) -> None:
        if self.regulatory_repo is None:
            logger.warning("Auto-regeneration skipped: regulatory repository is not configured")
            return
        service = PmlaGenerationService(
            document_repo=self.document_repo,
            regulatory_repo=self.regulatory_repo,
            scenario_matrix_repo=self.scenario_matrix_repo,
            sample_repo=self.sample_repo,
        )
        try:
            await service.auto_regenerate_sections(document_id, sections)
        except Exception as exc:  # noqa: BLE001 - review must still return successfully
            logger.warning("Auto-regeneration failed: %s", exc)
