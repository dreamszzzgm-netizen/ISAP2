"""Tests for document review workflow."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.application.services.document_review_service import (
    ALLOWED_TRANSITIONS,
    DOCUMENT_STATUS_BY_REVIEW_STATUS,
    REVIEW_STATUS_LABELS,
    DocumentReviewService,
)


# ---------------------------------------------------------------------------
# Test data
# ---------------------------------------------------------------------------

SAMPLE_DOCUMENT_ID = uuid4()


# ---------------------------------------------------------------------------
# Mock document
# ---------------------------------------------------------------------------

class MockDocument:
    def __init__(self, **kwargs):
        self.id = kwargs.get("id", SAMPLE_DOCUMENT_ID)
        self.review_status = kwargs.get("review_status", "needs_review")
        self.status = kwargs.get("status", "pending_review")
        self.review_comment = kwargs.get("review_comment", None)
        self.reviewed_by = kwargs.get("reviewed_by", None)
        self.reviewed_at = kwargs.get("reviewed_at", None)
        self.issued_at = kwargs.get("issued_at", None)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestDocumentReviewService:
    """Test DocumentReviewService review workflow."""

    def setup_method(self):
        self.mock_repo = MagicMock()
        self.service = DocumentReviewService(self.mock_repo)

    @pytest.mark.asyncio
    async def test_get_review_status_returns_current_status(self):
        """GET review returns current review status."""
        doc = MockDocument(review_status="needs_review")
        self.mock_repo.get = AsyncMock(return_value=doc)

        result = await self.service.get_review_status(SAMPLE_DOCUMENT_ID)

        assert result["document_id"] == str(SAMPLE_DOCUMENT_ID)
        assert result["status"] == "pending_review"
        assert result["review_status"] == "needs_review"
        assert result["review_status_label"] == "Требует проверки"
        assert "in_review" in result["allowed_transitions"]

    @pytest.mark.asyncio
    async def test_get_review_status_not_found(self):
        """GET review raises ValueError for non-existent document."""
        self.mock_repo.get = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="не найден"):
            await self.service.get_review_status(SAMPLE_DOCUMENT_ID)

    @pytest.mark.asyncio
    async def test_update_review_status_valid_transition(self):
        """PATCH review changes status on valid transition."""
        doc = MockDocument(review_status="needs_review")
        updated_doc = MockDocument(review_status="in_review", reviewed_by="engineer")
        self.mock_repo.get = AsyncMock(side_effect=[doc, updated_doc])
        self.mock_repo.update = AsyncMock()

        result = await self.service.update_review_status(
            SAMPLE_DOCUMENT_ID,
            review_status="in_review",
            reviewed_by="engineer",
        )

        assert result["review_status"] == "in_review"
        assert result["reviewed_by"] == "engineer"
        self.mock_repo.update.assert_called_once()
        update_data = self.mock_repo.update.call_args.args[1]
        assert update_data["status"] == "pending_review"
        assert update_data["review_status"] == "in_review"

    @pytest.mark.asyncio
    async def test_return_for_changes_updates_both_states_and_rereads_repository(self):
        """PATCH in_review -> needs_changes persists and rereads consistent DB state."""
        doc = MockDocument(review_status="in_review", status="pending_review")
        updated_doc = MockDocument(review_status="needs_changes", status="needs_changes")
        self.mock_repo.get = AsyncMock(side_effect=[doc, updated_doc])
        self.mock_repo.update = AsyncMock()

        result = await self.service.update_review_status(
            SAMPLE_DOCUMENT_ID,
            review_status="needs_changes",
            review_comment="Вернуть на доработку",
        )

        update_data = self.mock_repo.update.call_args.args[1]
        assert update_data["status"] == "needs_changes"
        assert update_data["review_status"] == "needs_changes"
        assert result["review_status"] == "needs_changes"
        assert result["status"] == "needs_changes"
        assert self.mock_repo.get.await_count == 2

    @pytest.mark.asyncio
    async def test_update_review_status_invalid_transition(self):
        """PATCH review rejects invalid transition."""
        doc = MockDocument(review_status="draft")
        self.mock_repo.get = AsyncMock(return_value=doc)

        with pytest.raises(ValueError, match="Недопустимый переход"):
            await self.service.update_review_status(
                SAMPLE_DOCUMENT_ID,
                review_status="approved",
            )

    @pytest.mark.asyncio
    async def test_update_review_status_with_comment(self):
        """PATCH review stores comment."""
        doc = MockDocument(review_status="in_review")
        updated_doc = MockDocument(
            review_status="approved",
            review_comment="Проверка пройдена",
            reviewed_by="engineer",
        )
        self.mock_repo.get = AsyncMock(side_effect=[doc, updated_doc])
        self.mock_repo.update = AsyncMock()

        result = await self.service.update_review_status(
            SAMPLE_DOCUMENT_ID,
            review_status="approved",
            review_comment="Проверка пройдена",
            reviewed_by="engineer",
        )

        assert result["review_comment"] == "Проверка пройдена"

    @pytest.mark.asyncio
    async def test_issued_fills_issued_at(self):
        """Transition to 'issued' sets issued_at timestamp."""
        doc = MockDocument(review_status="ready_to_issue")
        updated_doc = MockDocument(
            review_status="issued",
            issued_at="2026-07-08T10:00:00",
        )
        self.mock_repo.get = AsyncMock(side_effect=[doc, updated_doc])
        self.mock_repo.update = AsyncMock()

        result = await self.service.update_review_status(
            SAMPLE_DOCUMENT_ID,
            review_status="issued",
        )

        assert result["issued_at"] is not None

    @pytest.mark.asyncio
    async def test_approved_then_ready_to_issue_then_issued(self):
        """Full workflow: approved → ready_to_issue → issued."""
        # Step 1: approved → ready_to_issue
        doc1 = MockDocument(review_status="approved")
        updated_doc1 = MockDocument(review_status="ready_to_issue")
        self.mock_repo.get = AsyncMock(side_effect=[doc1, updated_doc1])
        self.mock_repo.update = AsyncMock()

        result1 = await self.service.update_review_status(
            SAMPLE_DOCUMENT_ID,
            review_status="ready_to_issue",
        )
        assert result1["review_status"] == "ready_to_issue"

        # Step 2: ready_to_issue → issued
        doc2 = MockDocument(review_status="ready_to_issue")
        updated_doc2 = MockDocument(review_status="issued", issued_at="2026-07-08T10:00:00")
        self.mock_repo.get = AsyncMock(side_effect=[doc2, updated_doc2])
        self.mock_repo.update = AsyncMock()

        result2 = await self.service.update_review_status(
            SAMPLE_DOCUMENT_ID,
            review_status="issued",
        )
        assert result2["review_status"] == "issued"

    @pytest.mark.asyncio
    async def test_set_initial_review_status_ok(self):
        """Initial review status is 'needs_review' for ok quality."""
        self.mock_repo.update = AsyncMock()

        await self.service.set_initial_review_status(SAMPLE_DOCUMENT_ID, quality_status="ok")

        call_args = self.mock_repo.update.call_args
        # update is called with (document_id, update_data)
        update_data = call_args[0][1]
        assert update_data["review_status"] == "needs_review"

    @pytest.mark.asyncio
    async def test_set_initial_review_status_critical(self):
        """Initial review status is 'needs_changes' for critical quality."""
        self.mock_repo.update = AsyncMock()

        await self.service.set_initial_review_status(SAMPLE_DOCUMENT_ID, quality_status="critical")

        call_args = self.mock_repo.update.call_args
        update_data = call_args[0][1]
        assert update_data["review_status"] == "needs_changes"

    @pytest.mark.asyncio
    async def test_set_initial_review_status_warning(self):
        """Initial review status is 'needs_review' for warning quality."""
        self.mock_repo.update = AsyncMock()

        await self.service.set_initial_review_status(SAMPLE_DOCUMENT_ID, quality_status="warning")

        call_args = self.mock_repo.update.call_args
        update_data = call_args[0][1]
        assert update_data["review_status"] == "needs_review"


class TestTransitionRules:
    """Test transition rules are correctly defined."""

    def test_all_statuses_have_labels(self):
        """All statuses should have human-readable labels."""
        for status in ALLOWED_TRANSITIONS:
            assert status in REVIEW_STATUS_LABELS, f"Missing label for status: {status}"

    def test_no_self_transitions(self):
        """No status should transition to itself."""
        for status, allowed in ALLOWED_TRANSITIONS.items():
            assert status not in allowed, f"Status {status} can transition to itself"

    def test_issued_only_to_archived(self):
        """issued can only go to archived."""
        assert ALLOWED_TRANSITIONS["issued"] == ["archived"]

    def test_draft_cannot_go_to_issued(self):
        """draft cannot go directly to issued."""
        assert "issued" not in ALLOWED_TRANSITIONS["draft"]

    def test_needs_changes_can_go_to_in_review(self):
        """needs_changes can go to in_review."""
        assert "in_review" in ALLOWED_TRANSITIONS["needs_changes"]

    def test_approved_can_go_to_ready_to_issue(self):
        """approved can go to ready_to_issue."""
        assert "ready_to_issue" in ALLOWED_TRANSITIONS["approved"]

    @pytest.mark.parametrize(
        ("source", "target"),
        [
            (source, target)
            for source, targets in ALLOWED_TRANSITIONS.items()
            for target in targets
        ],
    )
    @pytest.mark.asyncio
    async def test_every_declared_transition_is_persisted_and_reread(self, source, target):
        repo = MagicMock()
        repo.get = AsyncMock(side_effect=[
            MockDocument(review_status=source),
            MockDocument(
                review_status=target,
                status=DOCUMENT_STATUS_BY_REVIEW_STATUS[target],
            ),
        ])
        repo.update = AsyncMock()

        result = await DocumentReviewService(repo).update_review_status(
            SAMPLE_DOCUMENT_ID,
            review_status=target,
        )

        persisted = repo.update.call_args.args[1]
        assert persisted["review_status"] == target
        assert persisted["status"] == DOCUMENT_STATUS_BY_REVIEW_STATUS[target]
        assert result["review_status"] == target
        assert result["status"] == DOCUMENT_STATUS_BY_REVIEW_STATUS[target]
        assert repo.get.await_count == 2

    @pytest.mark.parametrize(
        ("source", "target"),
        [
            (source, target)
            for source in ALLOWED_TRANSITIONS
            for target in ALLOWED_TRANSITIONS
            if target not in ALLOWED_TRANSITIONS[source]
        ],
    )
    @pytest.mark.asyncio
    async def test_every_undeclared_transition_is_rejected(self, source, target):
        repo = MagicMock()
        repo.get = AsyncMock(return_value=MockDocument(review_status=source))
        repo.update = AsyncMock()

        with pytest.raises(ValueError, match="Недопустимый переход"):
            await DocumentReviewService(repo).update_review_status(
                SAMPLE_DOCUMENT_ID,
                review_status=target,
            )

        repo.update.assert_not_awaited()
