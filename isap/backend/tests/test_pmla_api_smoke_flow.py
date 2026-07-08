"""API Smoke Test: проверка реальных HTTP endpoints MVP-сценария ПМЛА.

Тестирует цепочку:
Facility → Questionnaire → PATCH blocks → Generate → Documents → Download → Review
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_mock_repo(return_value=None, list_value=None):
    """Create a mock repository with common methods."""
    repo = AsyncMock()
    repo.get = AsyncMock(return_value=return_value)
    repo.create = AsyncMock(return_value=return_value)
    repo.update = AsyncMock(return_value=return_value)
    repo.delete = AsyncMock(return_value=True)
    repo.get_multi = AsyncMock(return_value=list_value or [])
    repo.search = AsyncMock(return_value=list_value or [])
    return repo


class FakeModel:
    """Universal stub ORM model."""
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


# ---------------------------------------------------------------------------
# Test data
# ---------------------------------------------------------------------------

FACILITY_ID = str(uuid4())
ORGANIZATION_ID = str(uuid4())
QUESTIONNAIRE_ID = str(uuid4())
DOCUMENT_ID = str(uuid4())

FAKE_FACILITY = FakeModel(
    id=FACILITY_ID,
    name="Котельная №1",
    organization_id=ORGANIZATION_ID,
    facility_type="Сеть газопотребления",
    hazard_class="3",
    address="г. Тюмень, ул. Промышленная, 5",
    reg_number="77-1-2-0001-12345678",
    latitude=57.15,
    longitude=65.53,
    commissioning_date=None,
    inventory_number=None,
    properties=None,
)

FAKE_ORGANIZATION = FakeModel(
    id=ORGANIZATION_ID,
    name="ООО Газовый сервис",
    inn="7701234567",
    address="г. Тюмень, ул. Промышленная, 5",
    phone="+7(3452)12-34-56",
)

FAKE_QUESTIONNAIRE = FakeModel(
    id=QUESTIONNAIRE_ID,
    facility_id=FACILITY_ID,
    organization_id=ORGANIZATION_ID,
    title="ПМЛА Котельная №1",
    data={
        "incident_history": {"has_incidents": False, "items": []},
        "selected_scenarios": ["утечка опасного вещества"],
        "custom_scenarios": [],
        "organization_resources": {"actual_items": []},
        "notification_scheme": {"first_receiver": "оператор"},
        "financial_reserve": {"created": True, "order_number": "12-ПБ"},
        "insurance": {"has_contract": True, "company": "АО СК"},
        "attachments_checklist": [],
    },
    created_at="2026-07-08T10:00:00",
    updated_at="2026-07-08T10:00:00",
)

FAKE_DOCUMENT = FakeModel(
    id=DOCUMENT_ID,
    hazardous_facility_id=FACILITY_ID,
    organization_id=ORGANIZATION_ID,
    document_type="pmla",
    title="ПМЛА Котельная №1",
    status="pending_review",
    review_status="needs_review",
    version=1,
    content_docx=b"fake-docx-bytes",
    rendered_sections={},
    generation_meta={"version": "1.0", "source": "pmla_questionnaire"},
    regeneration_count=0,
    created_at="2026-07-08T10:00:00",
    updated_at="2026-07-08T10:00:00",
)

FAKE_VERSION = FakeModel(
    id=str(uuid4()),
    document_id=DOCUMENT_ID,
    version_number=1,
    status="pending_review",
    reviewer_id=None,
    reviewer_decision=None,
    reviewer_comments=[],
    quality_score=85,
    quality_status="ok",
    created_at="2026-07-08T10:00:00",
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.fixture(autouse=True)
def clear_overrides():
    yield
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestPmlaApiSmokeFlow:
    """API smoke test: полный MVP-сценарий через HTTP endpoints."""

    @pytest.mark.asyncio
    async def test_full_api_flow(self, client: AsyncClient):
        """Полный API flow: facility → questionnaire → generate → download → review."""
        from src.api.dependencies import (
            get_document_repo,
            get_facility_repo,
            get_regulatory_repo,
            get_scenario_matrix_repo,
        )

        # ── 1. Получить facility ──
        app.dependency_overrides[get_facility_repo] = lambda: make_mock_repo(
            return_value=FAKE_FACILITY,
            list_value=[FAKE_FACILITY],
        )

        resp = await client.get(f"/api/v1/facilities/{FACILITY_ID}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Котельная №1"

        # ── 2. Создать/получить анкету ──
        # Questionnaire endpoints use get_db directly, so we mock the service
        with patch(
            "src.api.routers.pmla_questionnaires.PmlaQuestionnaireService",
        ) as MockService:
            mock_service = MockService.return_value
            mock_service.get_by_facility = AsyncMock(return_value=FAKE_QUESTIONNAIRE)
            mock_service.update_block = AsyncMock(return_value=FAKE_QUESTIONNAIRE)
            mock_service.get_by_id = AsyncMock(return_value=FAKE_QUESTIONNAIRE)

            resp = await client.get(f"/api/v1/pmla-questionnaires/facility/{FACILITY_ID}")
            assert resp.status_code == 200

            # ── 3. PATCH blocks анкеты ──
            block_data = {
                "incident_history": {"has_incidents": False, "items": []},
                "selected_scenarios": ["утечка опасного вещества", "загазованность"],
            }

            for block_name, block_value in block_data.items():
                resp = await client.patch(
                    f"/api/v1/pmla-questionnaires/{QUESTIONNAIRE_ID}/blocks/{block_name}",
                    json={"data": block_value},
                )
                assert resp.status_code == 200, f"PATCH {block_name} failed: {resp.text}"

        # ── 4. Генерация ПМЛА ──
        app.dependency_overrides[get_document_repo] = lambda: make_mock_repo(
            return_value=FAKE_DOCUMENT,
            list_value=[FAKE_DOCUMENT],
        )
        app.dependency_overrides[get_regulatory_repo] = lambda: make_mock_repo()
        app.dependency_overrides[get_scenario_matrix_repo] = lambda: make_mock_repo()

        with patch(
            "src.api.routers.pmla_questionnaires.PmlaGenerationFromQuestionnaireService.generate",
            new_callable=AsyncMock,
        ) as mock_generate:
            # Create a mock result object with required attributes
            mock_result = MagicMock()
            mock_result.document_id = DOCUMENT_ID
            mock_result.questionnaire_id = QUESTIONNAIRE_ID
            mock_result.facility_id = FACILITY_ID
            mock_result.status = "pending_review"
            mock_result.version = 1
            mock_result.context_quality = {}
            mock_result.quality_review = {
                "overall_status": "ok",
                "score": 85,
                "checks": [],
            }
            mock_result.debug_artifacts = None
            mock_result.review_status = "needs_review"
            mock_generate.return_value = mock_result

            resp = await client.post(
                f"/api/v1/pmla-questionnaires/{QUESTIONNAIRE_ID}/generate",
                json={"regenerate_sections": None, "save_debug_artifacts": True},
            )
            if resp.status_code != 200:
                print(f"Generate failed: {resp.status_code} {resp.text}")
            assert resp.status_code == 200
            gen_data = resp.json()
            assert gen_data["document_id"] == DOCUMENT_ID
            assert gen_data["status"] == "pending_review"
            assert gen_data["version"] == 1
            assert "quality_review" in gen_data

        # ── 5. Получить список документов ──
        with patch(
            "src.api.routers.pmla_questionnaires.PmlaQuestionnaireService",
        ) as MockService:
            mock_service = MockService.return_value
            mock_service.get_documents = AsyncMock(return_value=[
                {"document_id": DOCUMENT_ID, "version": 1, "status": "pending_review"}
            ])

            resp = await client.get(f"/api/v1/pmla-questionnaires/{QUESTIONNAIRE_ID}/documents")
            assert resp.status_code == 200

        # ── 6. Скачать DOCX ──
        resp = await client.get(f"/api/v1/pmla/{DOCUMENT_ID}/download")
        assert resp.status_code == 200
        assert len(resp.content) > 0

        # ── 7. Review workflow ──
        def make_mock_doc(review_status, **kwargs):
            doc = MagicMock()
            doc.id = DOCUMENT_ID
            doc.review_status = review_status
            doc.review_comment = kwargs.get("review_comment", None)
            doc.reviewed_by = kwargs.get("reviewed_by", None)
            doc.reviewed_at = kwargs.get("reviewed_at", None)
            doc.issued_at = kwargs.get("issued_at", None)
            return doc

        # GET review status
        app.dependency_overrides[get_document_repo] = lambda: make_mock_repo(
            return_value=make_mock_doc("needs_review"),
        )

        resp = await client.get(f"/api/v1/pmla/{DOCUMENT_ID}/review")
        assert resp.status_code == 200
        review_data = resp.json()
        assert review_data["review_status"] == "needs_review"
        assert "in_review" in review_data["allowed_transitions"]

        # needs_review → in_review
        app.dependency_overrides[get_document_repo] = lambda: make_mock_repo(
            return_value=make_mock_doc("needs_review"),
        )

        resp = await client.patch(
            f"/api/v1/pmla/{DOCUMENT_ID}/review",
            json={"review_status": "in_review", "reviewed_by": "engineer"},
        )
        assert resp.status_code == 200

        # in_review → approved
        app.dependency_overrides[get_document_repo] = lambda: make_mock_repo(
            return_value=make_mock_doc("in_review"),
        )

        resp = await client.patch(
            f"/api/v1/pmla/{DOCUMENT_ID}/review",
            json={"review_status": "approved", "review_comment": "Проверено"},
        )
        assert resp.status_code == 200

        # approved → ready_to_issue
        app.dependency_overrides[get_document_repo] = lambda: make_mock_repo(
            return_value=make_mock_doc("approved"),
        )

        resp = await client.patch(
            f"/api/v1/pmla/{DOCUMENT_ID}/review",
            json={"review_status": "ready_to_issue"},
        )
        assert resp.status_code == 200

        # ready_to_issue → issued
        app.dependency_overrides[get_document_repo] = lambda: make_mock_repo(
            return_value=make_mock_doc("ready_to_issue"),
        )

        resp = await client.patch(
            f"/api/v1/pmla/{DOCUMENT_ID}/review",
            json={"review_status": "issued"},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_invalid_transition_returns_400(self, client: AsyncClient):
        """Invalid review transition returns 400."""
        from src.api.dependencies import get_document_repo

        mock_doc = MagicMock()
        mock_doc.id = DOCUMENT_ID
        mock_doc.review_status = "draft"
        mock_doc.review_comment = None
        mock_doc.reviewed_by = None
        mock_doc.reviewed_at = None
        mock_doc.issued_at = None

        app.dependency_overrides[get_document_repo] = lambda: make_mock_repo(
            return_value=mock_doc,
        )

        resp = await client.patch(
            f"/api/v1/pmla/{DOCUMENT_ID}/review",
            json={"review_status": "approved"},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_download_returns_docx_bytes(self, client: AsyncClient):
        """Download endpoint returns valid DOCX bytes."""
        from src.api.dependencies import get_document_repo

        mock_doc = MagicMock()
        mock_doc.id = DOCUMENT_ID
        mock_doc.content_docx = b"PK\x03\x04fake-docx"
        mock_doc.status = "approved"

        app.dependency_overrides[get_document_repo] = lambda: make_mock_repo(
            return_value=mock_doc,
        )

        resp = await client.get(f"/api/v1/pmla/{DOCUMENT_ID}/download")
        assert resp.status_code == 200
        assert len(resp.content) > 0
