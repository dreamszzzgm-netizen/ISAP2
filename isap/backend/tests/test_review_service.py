"""Tests for ReviewService — автоматическая перегенерация при отклонении."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from src.application.services.review_service import ReviewService, MAX_REGENERATION_ATTEMPTS
from src.application.services.pmla_review_workflow_service import PmlaReviewWorkflowService
from src.application.services.types import Issue


@pytest.fixture
def mock_doc_repo():
    repo = AsyncMock()
    return repo


@pytest.fixture
def review_service(mock_doc_repo):
    return ReviewService(document_repo=mock_doc_repo)


class TestReviewServiceReject:
    @pytest.mark.asyncio
    async def test_reject_increments_regeneration_count(self, review_service, mock_doc_repo):
        doc = MagicMock()
        doc.id = uuid4()
        doc.status = "pending_review"
        doc.review_status = "in_review"
        doc.regeneration_count = 0
        mock_doc_repo.get.return_value = doc
        mock_doc_repo.get_latest_version.return_value = None

        issues = [Issue(section="section_1", reason="Ошибка", severity="error")]
        result = await review_service.reject(doc.id, "reviewer", issues)

        assert result["regeneration_count"] == 1
        assert result["action"] == "regenerated"
        assert "section_1" in result["sections"]
        update_data = mock_doc_repo.update.call_args_list[0].args[1]
        assert update_data["status"] == "needs_changes"
        assert update_data["review_status"] == "needs_changes"

    @pytest.mark.asyncio
    async def test_reject_sets_manual_intervention_after_max_attempts(self, review_service, mock_doc_repo):
        doc = MagicMock()
        doc.id = uuid4()
        doc.status = "pending_review"
        doc.review_status = "in_review"
        doc.regeneration_count = MAX_REGENERATION_ATTEMPTS - 1
        mock_doc_repo.get.return_value = doc
        mock_doc_repo.get_latest_version.return_value = None

        issues = [Issue(section="section_1", reason="Ошибка", severity="error")]
        result = await review_service.reject(doc.id, "reviewer", issues)

        assert result["action"] == "manual_required"
        assert result["regeneration_count"] == MAX_REGENERATION_ATTEMPTS

    @pytest.mark.asyncio
    async def test_reject_extracts_unique_sections(self, review_service, mock_doc_repo):
        doc = MagicMock()
        doc.id = uuid4()
        doc.status = "pending_review"
        doc.review_status = "in_review"
        doc.regeneration_count = 0
        mock_doc_repo.get.return_value = doc
        mock_doc_repo.get_latest_version.return_value = None

        issues = [
            Issue(section="section_1", reason="Ошибка 1", severity="error"),
            Issue(section="section_1", reason="Ошибка 2", severity="warning"),
            Issue(section="section_2", reason="Ошибка 3", severity="error"),
        ]
        result = await review_service.reject(doc.id, "reviewer", issues)

        assert len(result["sections"]) == 2
        assert "section_1" in result["sections"]
        assert "section_2" in result["sections"]

    @pytest.mark.asyncio
    async def test_reject_without_sections(self, review_service, mock_doc_repo):
        doc = MagicMock()
        doc.id = uuid4()
        doc.status = "pending_review"
        doc.review_status = "in_review"
        doc.regeneration_count = 0
        mock_doc_repo.get.return_value = doc
        mock_doc_repo.get_latest_version.return_value = None

        issues = [Issue(section="", reason="Общая ошибка", severity="warning")]
        result = await review_service.reject(doc.id, "reviewer", issues)

        assert result["sections"] == []
        assert result["action"] == "regenerated"

    @pytest.mark.asyncio
    async def test_approve_resets_regeneration_count(self, review_service, mock_doc_repo):
        doc = MagicMock()
        doc.id = uuid4()
        doc.status = "pending_review"
        doc.review_status = "in_review"
        doc.regeneration_count = 2
        mock_doc_repo.get.return_value = doc
        mock_doc_repo.get_latest_version.return_value = None

        await review_service.approve(doc.id, "reviewer")

        # Проверяем что regeneration_count сброшен
        call_args = mock_doc_repo.update.call_args
        update_data = call_args[0][1]  # Второй позиционный аргумент — dict
        assert update_data["regeneration_count"] == 0
        assert update_data["status"] == "approved"
        assert update_data["review_status"] == "approved"

    @pytest.mark.asyncio
    async def test_reject_is_forbidden_unless_review_is_in_progress(
        self, review_service, mock_doc_repo
    ):
        doc = MagicMock()
        doc.id = uuid4()
        doc.status = "pending_review"
        doc.review_status = "needs_review"
        mock_doc_repo.get.return_value = doc

        with pytest.raises(ValueError, match="in_review"):
            await review_service.reject(doc.id, "reviewer", [])

        mock_doc_repo.update.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_approve_is_forbidden_unless_review_is_in_progress(
        self, review_service, mock_doc_repo
    ):
        doc = MagicMock()
        doc.id = uuid4()
        doc.status = "pending_review"
        doc.review_status = "needs_changes"
        mock_doc_repo.get.return_value = doc

        with pytest.raises(ValueError, match="in_review"):
            await review_service.approve(doc.id, "reviewer")

        mock_doc_repo.update.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_get_status_includes_regeneration_count(self, review_service, mock_doc_repo):
        doc = MagicMock()
        doc.id = uuid4()
        doc.status = "rejected"
        doc.review_status = "needs_changes"
        doc.regeneration_count = 2
        mock_doc_repo.get.return_value = doc
        mock_doc_repo.get_latest_version.return_value = None

        status = await review_service.get_status(doc.id)

        assert status["regeneration_count"] == 2
        assert status["review_status"] == "needs_changes"


class TestPmlaReviewWorkflowStateConsistency:
    @pytest.mark.asyncio
    async def test_rejection_persists_needs_changes_after_auto_regeneration(self, monkeypatch):
        repo = AsyncMock()
        low_level_review = MagicMock()
        low_level_review.reject = AsyncMock(return_value={
            "action": "regenerated",
            "sections": ["section_1"],
            "regeneration_count": 1,
        })
        monkeypatch.setattr(
            "src.application.services.pmla_review_workflow_service.ReviewService",
            MagicMock(return_value=low_level_review),
        )
        service = PmlaReviewWorkflowService(repo)
        service._auto_regenerate_sections = AsyncMock()

        result = await service.review(
            document_id=uuid4(),
            reviewer_id="reviewer",
            decision="rejected",
            comments=[{"section": "section_1", "reason": "Ошибка"}],
        )

        persisted = repo.update.await_args.args[1]
        assert persisted["status"] == "needs_changes"
        assert persisted["review_status"] == "needs_changes"
        assert result["status"] == "needs_changes"
        assert result["review_status"] == "needs_changes"
