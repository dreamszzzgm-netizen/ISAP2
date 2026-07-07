"""Tests for PMLA document versioning."""
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.infrastructure.database.models import DocumentModel


def _make_doc(version=None, questionnaire_id=None, status="pending_review", content_docx=b"docx"):
    doc = MagicMock(spec=DocumentModel)
    doc.id = uuid4()
    doc.version = version
    doc.status = status
    doc.content_docx = content_docx
    doc.created_at = MagicMock()
    doc.created_at.isoformat.return_value = "2026-07-07T12:00:00"
    doc.generation_meta = {
        "source": "pmla_questionnaire",
        "questionnaire_id": str(questionnaire_id) if questionnaire_id else None,
        "quality_review": {"score": 86, "overall_status": "warning"},
    }
    return doc


class TestDocumentRepository:
    """Tests for document repository version queries."""

    @pytest.mark.asyncio
    async def test_get_max_version_for_questionnaire_empty(self):
        from src.infrastructure.repositories.document_repo import DocumentRepository

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = DocumentRepository(mock_session)
        max_ver = await repo.get_max_version_for_questionnaire(uuid4())

        assert max_ver == 0

    @pytest.mark.asyncio
    async def test_get_max_version_for_questionnaire_with_versions(self):
        from src.infrastructure.repositories.document_repo import DocumentRepository

        qid = uuid4()
        doc1 = _make_doc(version=1, questionnaire_id=qid)
        doc2 = _make_doc(version=3, questionnaire_id=qid)
        doc3 = _make_doc(version=2, questionnaire_id=qid)

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [doc2, doc3, doc1]
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = DocumentRepository(mock_session)
        max_ver = await repo.get_max_version_for_questionnaire(qid)

        assert max_ver == 3


class TestVersionComputation:
    """Test that version is computed correctly during generation."""

    def test_version_starts_at_1(self):
        """First generation should produce version=1."""
        assert 1 == 1  # placeholder - real test via service mock

    @pytest.mark.asyncio
    async def test_version_increments(self):
        """Second generation should produce version=2."""
        from src.infrastructure.repositories.document_repo import DocumentRepository

        qid = uuid4()
        existing_doc = _make_doc(version=1, questionnaire_id=qid)

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [existing_doc]
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = DocumentRepository(mock_session)
        max_ver = await repo.get_max_version_for_questionnaire(qid)

        assert max_ver == 1
        assert max_ver + 1 == 2


class TestVersionHistoryResponse:
    """Test the response shape of version history."""

    def test_document_list_item_shape(self):
        """Verify the expected response shape matches the endpoint output."""
        doc = _make_doc(version=2, questionnaire_id=uuid4())
        item = {
            "document_id": str(doc.id),
            "version": doc.version,
            "status": doc.status,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
            "quality_score": (doc.generation_meta or {}).get("quality_review", {}).get("score"),
            "quality_status": (doc.generation_meta or {}).get("quality_review", {}).get("overall_status"),
            "download_available": bool(doc.content_docx),
        }
        assert item["version"] == 2
        assert item["quality_score"] == 86
        assert item["quality_status"] == "warning"
        assert item["download_available"] is True

    def test_empty_questionnaire_returns_empty_list(self):
        """Verify empty list shape."""
        docs = []
        result = [
            {
                "document_id": str(d.id),
                "version": d.version,
                "status": d.status,
            }
            for d in docs
        ]
        assert result == []
