"""Integration tests for PMLA import binding flow (preview + confirm with binding)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.application.services.pmla_import_normalizer import PmlaImportNormalizer
from src.application.services.smart_import.service import SmartImportService


class _FakeOrg:
    """Minimal stand-in for OrganizationModel."""
    def __init__(self, **kw):
        self.id = kw.get("id", uuid4())
        self.name = kw.get("name", "АО Хлебокомбинат")
        self.inn = kw.get("inn", "1234567890")
        self.ogrn = kw.get("ogrn", "1234567890123")
        self.address = kw.get("address", "г. Тест")


class _FakeFac:
    """Minimal stand-in for HazardousFacilityModel."""
    def __init__(self, **kw):
        self.id = kw.get("id", uuid4())
        self.organization_id = kw.get("organization_id", uuid4())
        self.name = kw.get("name", "Сеть газопотребления")
        self.reg_number = kw.get("reg_number", "А01-0001-0005")
        self.hazard_class = kw.get("hazard_class", 3)
        self.facility_type = kw.get("facility_type", "Сеть газопотребления")
        self.address = kw.get("address", "г. Тест, ул. Тестовая, 1")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture
def mock_job():
    job = MagicMock()
    job.id = uuid4()
    job.status = "preview"
    job.import_type = "pmla_questionnaire"
    job.filename = "test_pmla.docx"
    return job


@pytest.fixture
def mock_row():
    row = MagicMock()
    row.id = uuid4()
    row.status = "valid"
    row.action = "create"
    row.errors = []
    row.normalized_data = {
        "organization_name": "АО Хлебокомбинат",
        "facility_name": "Сеть газопотребления Хлебозавода №2",
        "facility_reg_number": "А01-0001-0005",
        "has_incidents": "нет",
        "operation_mode": "две смены по 12 часов",
        "staff_per_shift": "8",
        "selected_scenarios": ["утечка газа"],
        "custom_scenarios": [],
        "resources": [],
        "pasf_name": "ПАСФ ООО ГазСпасСервис",
        "financial_reserve": "5 млн рублей",
        "training": "ежеквартально",
        "attachments": ["схема"],
    }
    return row


# ---------------------------------------------------------------------------
# Test 1: Preview candidates are extracted by normalizer
# ---------------------------------------------------------------------------


def test_preview_includes_candidates_in_job_report(mock_row):
    """The normalizer should extract and store candidates in _import_meta."""
    result = PmlaImportNormalizer().normalize(dict(mock_row.normalized_data))

    assert result.organization_candidate == {"name": "АО Хлебокомбинат"}
    assert result.facility_candidate == {
        "name": "Сеть газопотребления Хлебозавода №2",
        "reg_number": "А01-0001-0005",
    }
    meta = result.questionnaire_data["_import_meta"]
    assert meta["organization_candidate"] == {"name": "АО Хлебокомбинат"}
    assert meta["facility_candidate"] == {
        "name": "Сеть газопотребления Хлебозавода №2",
        "reg_number": "А01-0001-0005",
    }


# ---------------------------------------------------------------------------
# Test 2: Confirm with explicit facility_id
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_confirm_with_explicit_facility_id(mock_session, mock_job, mock_row):
    org_id = uuid4()
    fac_id = uuid4()
    fac = _FakeFac(id=fac_id, organization_id=org_id)

    # First execute call: get job (not used here since we mock _get_job_model)
    # Second: fetch rows
    mock_rows_result = MagicMock()
    mock_rows_result.scalars.return_value.all.return_value = [mock_row]

    # Third: facility lookup
    mock_fac_result = MagicMock()
    mock_fac_result.scalar_one_or_none.return_value = fac

    mock_session.execute = AsyncMock(side_effect=[mock_rows_result, mock_fac_result])

    service = SmartImportService(mock_session)
    service._get_job_model = AsyncMock(return_value=mock_job)

    await service.confirm_import(
        mock_job.id,
        bind_params={"organization_id": None, "facility_id": str(fac_id)},
    )

    added_model = mock_session.add.call_args[0][0]
    from src.infrastructure.database.models import PmlaQuestionnaireModel

    assert isinstance(added_model, PmlaQuestionnaireModel)
    assert added_model.facility_id == fac_id
    assert added_model.organization_id == org_id

    meta = added_model.data["_import_meta"]
    assert meta["binding_method"] == "explicit"
    assert meta["requires_binding"] is False
    assert meta["organization_candidate"] == {"name": "АО Хлебокомбинат"}


# ---------------------------------------------------------------------------
# Test 3: Facility-org mismatch → error
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_confirm_facility_org_mismatch(mock_session, mock_job, mock_row):
    org_id = uuid4()
    wrong_org_id = uuid4()
    fac_id = uuid4()
    fac = _FakeFac(id=fac_id, organization_id=org_id)

    mock_rows_result = MagicMock()
    mock_rows_result.scalars.return_value.all.return_value = [mock_row]

    mock_fac_result = MagicMock()
    mock_fac_result.scalar_one_or_none.return_value = fac

    mock_session.execute = AsyncMock(side_effect=[mock_rows_result, mock_fac_result])

    service = SmartImportService(mock_session)
    service._get_job_model = AsyncMock(return_value=mock_job)

    result = await service.confirm_import(
        mock_job.id,
        bind_params={
            "organization_id": str(wrong_org_id),
            "facility_id": str(fac_id),
        },
    )

    # Row-level error — job completes_with_errors, model NOT created
    assert result["status"] == "completed_with_errors"
    assert result["error_rows"] >= 1
    # Model should NOT have been added (error prevented creation)
    added_args = mock_session.add.call_args
    if added_args is not None:
        # If any model was added, verify it's not a PmlaQuestionnaireModel
        from src.infrastructure.database.models import PmlaQuestionnaireModel
        for args in mock_session.add.call_args_list:
            model = args[0][0]
            if isinstance(model, PmlaQuestionnaireModel):
                pytest.fail("PmlaQuestionnaireModel should not have been created")


# ---------------------------------------------------------------------------
# Test 4: Unknown facility → error
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_confirm_unknown_facility(mock_session, mock_job, mock_row):
    mock_rows_result = MagicMock()
    mock_rows_result.scalars.return_value.all.return_value = [mock_row]

    mock_fac_result = MagicMock()
    mock_fac_result.scalar_one_or_none.return_value = None  # facility not found

    mock_session.execute = AsyncMock(side_effect=[mock_rows_result, mock_fac_result])

    service = SmartImportService(mock_session)
    service._get_job_model = AsyncMock(return_value=mock_job)

    result = await service.confirm_import(
        mock_job.id,
        bind_params={
            "organization_id": None,
            "facility_id": str(uuid4()),
        },
    )

    # Row-level error — job completes_with_errors
    assert result["status"] == "completed_with_errors"
    assert result["error_rows"] >= 1
    # Row should be marked invalid
    assert mock_row.status == "invalid"
    assert len(mock_row.errors) >= 1
    assert "не найден" in mock_row.errors[0]


# ---------------------------------------------------------------------------
# Test 5: Confirm without IDs → draft
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_confirm_without_ids_creates_draft(mock_session, mock_job, mock_row):
    # When bind_params is None, auto-binding kicks in.
    # _resolve_pmla_binding will call session.execute for:
    # 1. rows query
    # 2. facility search (auto-binding will search by reg_number)
    # All return empty/no matches

    mock_rows_result = MagicMock()
    mock_rows_result.scalars.return_value.all.return_value = [mock_row]

    mock_fac_search_result = MagicMock()
    mock_fac_search_result.scalars.return_value.all.return_value = []

    mock_org_search_result = MagicMock()
    mock_org_search_result.scalar_one_or_none.return_value = None

    mock_session.execute = AsyncMock(
        side_effect=[
            mock_rows_result,       # row fetch
            mock_fac_search_result, # reg_number search (0 results)
            mock_org_search_result, # org search (0 results)
        ]
    )

    service = SmartImportService(mock_session)
    service._get_job_model = AsyncMock(return_value=mock_job)

    await service.confirm_import(mock_job.id, bind_params=None)

    added_model = mock_session.add.call_args[0][0]
    assert added_model.organization_id is None
    assert added_model.facility_id is None

    meta = added_model.data["_import_meta"]
    assert meta["requires_binding"] is True
    assert meta["binding_method"] == "none"


# ---------------------------------------------------------------------------
# Test 6: FK fields persisted with explicit IDs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fk_fields_persisted(mock_session, mock_job, mock_row):
    org_id = uuid4()
    fac_id = uuid4()
    fac = _FakeFac(id=fac_id, organization_id=org_id)

    mock_rows_result = MagicMock()
    mock_rows_result.scalars.return_value.all.return_value = [mock_row]

    mock_fac_result = MagicMock()
    mock_fac_result.scalar_one_or_none.return_value = fac

    mock_session.execute = AsyncMock(side_effect=[mock_rows_result, mock_fac_result])

    service = SmartImportService(mock_session)
    service._get_job_model = AsyncMock(return_value=mock_job)

    await service.confirm_import(
        mock_job.id,
        bind_params={"organization_id": str(org_id), "facility_id": str(fac_id)},
    )

    added_model = mock_session.add.call_args[0][0]
    assert added_model.facility_id == fac_id
    assert added_model.organization_id == org_id
    assert added_model.source_import_job_id == mock_job.id
