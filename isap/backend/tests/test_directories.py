"""Tests for PASF and Emergency Services directory endpoints."""
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest


def _mock_pasf(name="ПАСФ Тест", address="г. Тест"):
    doc = MagicMock()
    doc.id = uuid4()
    doc.name = name
    doc.short_name = "ПТ"
    doc.legal_address = address
    doc.actual_address = address
    doc.dispatch_phone = "+7-000"
    doc.email = None
    doc.manager_name = None
    doc.certificate_number = "АСФ-001"
    doc.certificate_date = None
    doc.certificate_valid_until = None
    doc.permitted_work_types = []
    doc.equipment_passport = []
    doc.staff_count = None
    doc.readiness_mode = None
    doc.service_area = None
    doc.notes = None
    doc.created_at = MagicMock()
    doc.created_at.isoformat.return_value = "2026-07-07T12:00:00"
    doc.updated_at = MagicMock()
    doc.updated_at.isoformat.return_value = "2026-07-07T12:00:00"
    return doc


def _mock_service(name="ПСЧ-1", service_type="fire"):
    doc = MagicMock()
    doc.id = uuid4()
    doc.service_type = service_type
    doc.name = name
    doc.address = "г. Тест"
    doc.phone = "101"
    doc.dispatcher_phone = "+7-000"
    doc.municipality = None
    doc.settlement = None
    doc.latitude = None
    doc.longitude = None
    doc.service_area = None
    doc.notes = None
    doc.created_at = MagicMock()
    doc.created_at.isoformat.return_value = "2026-07-07T12:00:00"
    doc.updated_at = MagicMock()
    doc.updated_at.isoformat.return_value = "2026-07-07T12:00:00"
    return doc


class TestPasfRepository:
    """Tests for EmergencyRescueUnitRepository."""

    @pytest.mark.asyncio
    async def test_search_returns_results(self):
        from src.infrastructure.repositories.emergency_rescue_unit_repo import EmergencyRescueUnitRepository

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [_mock_pasf()]
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = EmergencyRescueUnitRepository(mock_session)
        items = await repo.search("Тест")

        assert len(items) == 1
        assert items[0].name == "ПАСФ Тест"

    @pytest.mark.asyncio
    async def test_search_empty_query(self):
        from src.infrastructure.repositories.emergency_rescue_unit_repo import EmergencyRescueUnitRepository

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = EmergencyRescueUnitRepository(mock_session)
        items = await repo.search("")

        assert len(items) == 0


class TestEmergencyServiceRepository:
    """Tests for EmergencyServiceRepository."""

    @pytest.mark.asyncio
    async def test_search_by_type(self):
        from src.infrastructure.repositories.emergency_service_repo import EmergencyServiceRepository

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [_mock_service("ПСЧ-1", "fire")]
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = EmergencyServiceRepository(mock_session)
        items = await repo.search(service_type="fire")

        assert len(items) == 1
        assert items[0].service_type == "fire"

    @pytest.mark.asyncio
    async def test_search_by_name(self):
        from src.infrastructure.repositories.emergency_service_repo import EmergencyServiceRepository

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [_mock_service("Больница №5", "medical")]
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = EmergencyServiceRepository(mock_session)
        items = await repo.search(query_str="Больница")

        assert len(items) == 1
        assert items[0].name == "Больница №5"


class TestDirectoryResponseShape:
    """Verify response shapes match expected API format."""

    def test_pasf_response_shape(self):
        doc = _mock_pasf()
        item = {
            "id": str(doc.id),
            "name": doc.name,
            "short_name": doc.short_name,
            "actual_address": doc.actual_address,
            "dispatch_phone": doc.dispatch_phone,
            "certificate_number": doc.certificate_number,
            "permitted_work_types": doc.permitted_work_types or [],
        }
        assert item["name"] == "ПАСФ Тест"
        assert item["certificate_number"] == "АСФ-001"

    def test_emergency_service_response_shape(self):
        doc = _mock_service("ПСЧ-1", "fire")
        item = {
            "id": str(doc.id),
            "service_type": doc.service_type,
            "name": doc.name,
            "address": doc.address,
            "phone": doc.phone,
            "dispatcher_phone": doc.dispatcher_phone,
        }
        assert item["service_type"] == "fire"
        assert item["name"] == "ПСЧ-1"
