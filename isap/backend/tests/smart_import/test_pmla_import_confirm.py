"""Integration test: Smart Import confirm → PmlaQuestionnaireModel with normalised data.

This test verifies that after ``confirm_import`` with ``pmla_questionnaire``
profile, the created ``PmlaQuestionnaireModel`` has:

* ``data`` conforming to ``DEFAULT_QUESTIONNAIRE`` structure
* No flat keys (``organization_name``, ``facility_name``) at the data root
* ``_import_meta`` metadata block preserved
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.application.services.pmla_import_normalizer import PmlaImportNormalizer
from src.application.services.pmla_questionnaire_service import DEFAULT_QUESTIONNAIRE
from src.application.services.smart_import.service import SmartImportService


@pytest.fixture
def mock_session():
    """Create a fully mocked async session."""
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
        "incident_description": "За период эксплуатации аварии и инциденты не зарегистрированы.",
        "operation_mode": "две смены по 12 часов",
        "staff_per_shift": "8",
        "selected_scenarios": ["утечка природного газа", "воспламенение газовоздушной смеси"],
        "custom_scenarios": ["отказ задвижки"],
        "resources": ["Газоанализатор переносной", "СИЗОД"],
        "pasf_name": "ПАСФ ООО ГазСпасСервис",
        "financial_reserve": "5 000 000 рублей",
        "training": "ежеквартально",
        "attachments": ["схема расположения ОПО"],
    }
    return row


@pytest.mark.asyncio
async def test_confirm_pmla_questionnaire_creates_normalised_model(
    mock_session, mock_job, mock_row
):
    """Confirm import creates PmlaQuestionnaireModel with structured data."""
    service = SmartImportService(mock_session)

    # Need to mock _get_job_model to return our job
    service._get_job_model = AsyncMock(return_value=mock_job)

    # Mock the rows query to return our single row
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_row]
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Execute confirm
    result = await service.confirm_import(mock_job.id)

    # Verify job was completed
    assert result["status"] in ("completed", "completed_with_errors")

    # Grab the PmlaQuestionnaireModel that was added to session
    added_model = mock_session.add.call_args[0][0]
    from src.infrastructure.database.models import PmlaQuestionnaireModel
    assert isinstance(added_model, PmlaQuestionnaireModel)

    data = added_model.data

    # --- Assertions ---

    # 1. Data contains all DEFAULT_QUESTIONNAIRE top-level keys
    for key in DEFAULT_QUESTIONNAIRE:
        assert key in data, f"Ключ {key} отсутствует в data после нормализации"

    # 2. Flat keys NOT at the root level
    assert "organization_name" not in data or isinstance(data.get("organization_name"), str) is False, (
        "organization_name не должен быть строкой на верхнем уровне data"
    )
    assert "facility_name" not in data or isinstance(data.get("facility_name"), str) is False, (
        "facility_name не должен быть строкой на верхнем уровне data"
    )

    # 3. has_incidents is properly typed (bool/None)
    assert data["incident_history"]["has_incidents"] is False, (
        "'нет' должно быть преобразовано в False"
    )

    # 4. operation_mode is nested
    assert data["operation_mode"]["mode"] == "две смены по 12 часов"
    assert data["operation_mode"]["staff_per_shift"] == 8

    # 5. Selected scenarios are a list
    assert isinstance(data["selected_scenarios"], list)
    assert len(data["selected_scenarios"]) == 2

    # 6. _import_meta is preserved
    assert "_import_meta" in data
    meta = data["_import_meta"]
    assert meta["profile"] == "pmla_questionnaire"
    assert meta["normalizer_version"] == 1
    assert "raw_data" in meta
    assert meta["raw_data"]["organization_name"] == "АО Хлебокомбинат"

    # 7. Unmapped fields are empty
    assert meta["unmapped_fields"] == {}


@pytest.mark.asyncio
async def test_confirm_full_questionnaire_structure(mock_session, mock_job, mock_row):
    """Verify the full data structure matches DEFAULT_QUESTIONNAIRE + _import_meta."""
    service = SmartImportService(mock_session)
    service._get_job_model = AsyncMock(return_value=mock_job)
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_row]
    mock_session.execute = AsyncMock(return_value=mock_result)

    await service.confirm_import(mock_job.id)
    added_model = mock_session.add.call_args[0][0]
    data = added_model.data

    # Every DEFAULT_QUESTIONNAIRE key must exist
    for key in DEFAULT_QUESTIONNAIRE:
        assert key in data, f"Пропущен ключ DEFAULT_QUESTIONNAIRE: {key}"
        # The type should match (dict → dict, list → list, etc.)
        if isinstance(DEFAULT_QUESTIONNAIRE[key], dict):
            assert isinstance(data[key], dict), (
                f"Ключ {key} должен быть dict"
            )
        elif isinstance(DEFAULT_QUESTIONNAIRE[key], list):
            assert isinstance(data[key], list), (
                f"Ключ {key} должен быть list"
            )

    # Extra key
    assert "_import_meta" in data
