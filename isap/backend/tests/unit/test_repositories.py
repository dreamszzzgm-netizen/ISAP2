"""Unit-тесты репозиториев (базовый CRUD)."""
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models import (
    OrganizationModel, HazardousFacilityModel, EquipmentModel,
    HazardousSubstanceModel, ResponsiblePersonModel,
)
from src.infrastructure.repositories.base import BaseRepository
from src.infrastructure.repositories.organization_repo import OrganizationRepository
from src.infrastructure.repositories.facility_repo import FacilityRepository
from src.infrastructure.repositories.equipment_repo import EquipmentRepository
from src.infrastructure.repositories.substance_repo import SubstanceRepository
from src.infrastructure.repositories.person_repo import PersonRepository

_SENTINEL = object()


def make_mock_session():
    session = AsyncMock(spec=AsyncSession)
    return session


def make_mock_result(scalar_values=None, one_or_none=_SENTINEL):
    mock_result = MagicMock()
    if one_or_none is not _SENTINEL:
        mock_result.scalar_one_or_none.return_value = one_or_none
    else:
        mock_result.scalars.return_value.all.return_value = scalar_values or []
    return mock_result


# ── BaseRepository ───────────────────────────────────────────────────────────

class TestBaseRepository:
    @pytest.mark.asyncio
    async def test_get_found(self):
        session = make_mock_session()
        fake_org = OrganizationModel(id=uuid.uuid4(), name="Test", inn="123")
        session.execute.return_value = make_mock_result(one_or_none=fake_org)

        repo = OrganizationRepository(session)
        result = await repo.get(uuid.uuid4())
        assert result is fake_org

    @pytest.mark.asyncio
    async def test_get_not_found(self):
        session = make_mock_session()
        session.execute.return_value = make_mock_result(one_or_none=None)

        repo = OrganizationRepository(session)
        result = await repo.get(uuid.uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_get_multi(self):
        session = make_mock_session()
        orgs = [OrganizationModel(id=uuid.uuid4(), name=f"Org {i}", inn=str(i)) for i in range(3)]
        session.execute.return_value = make_mock_result(scalar_values=orgs)

        repo = OrganizationRepository(session)
        result = await repo.get_multi()
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_create(self):
        session = make_mock_session()
        created = OrganizationModel(id=uuid.uuid4(), name="New", inn="999")
        session.refresh = AsyncMock()

        repo = OrganizationRepository(session)
        result = await repo.create({"name": "New", "inn": "999"})
        session.add.assert_called_once()
        session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_found(self):
        session = make_mock_session()
        fake_org = OrganizationModel(id=uuid.uuid4(), name="Old", inn="111")
        session.execute.return_value = make_mock_result(one_or_none=fake_org)
        session.refresh = AsyncMock()

        repo = OrganizationRepository(session)
        result = await repo.update(fake_org.id, {"name": "New"})
        assert fake_org.name == "New"

    @pytest.mark.asyncio
    async def test_update_not_found(self):
        session = make_mock_session()
        session.execute.return_value = make_mock_result(one_or_none=None)

        repo = OrganizationRepository(session)
        result = await repo.update(uuid.uuid4(), {"name": "X"})
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_found(self):
        session = make_mock_session()
        fake_org = OrganizationModel(id=uuid.uuid4(), name="X", inn="111")
        session.execute.return_value = make_mock_result(one_or_none=fake_org)

        repo = OrganizationRepository(session)
        result = await repo.delete(fake_org.id)
        assert result is True
        session.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(self):
        session = make_mock_session()
        session.execute.return_value = make_mock_result(one_or_none=None)

        repo = OrganizationRepository(session)
        result = await repo.delete(uuid.uuid4())
        assert result is False


# ── FacilityRepository ───────────────────────────────────────────────────────

class TestFacilityRepository:
    @pytest.mark.asyncio
    async def test_get_with_related(self):
        session = make_mock_session()
        fac_id = uuid.uuid4()
        facility = HazardousFacilityModel(id=fac_id, name="Fac", organization_id=uuid.uuid4())
        eq = EquipmentModel(id=uuid.uuid4(), hazardous_facility_id=fac_id, name="Compressor")
        sub = HazardousSubstanceModel(id=uuid.uuid4(), hazardous_facility_id=fac_id, name="Methane")

        # Three execute calls: facility, equipment, substances
        session.execute.side_effect = [
            make_mock_result(one_or_none=facility),
            make_mock_result(scalar_values=[eq]),
            make_mock_result(scalar_values=[sub]),
        ]

        repo = FacilityRepository(session)
        result = await repo.get_with_related(fac_id)
        assert result is not None
        assert result.facility is facility
        assert len(result.equipment) == 1
        assert len(result.substances) == 1

    @pytest.mark.asyncio
    async def test_get_with_related_not_found(self):
        session = make_mock_session()
        session.execute.return_value = make_mock_result(one_or_none=None)

        repo = FacilityRepository(session)
        result = await repo.get_with_related(uuid.uuid4())
        assert result is None


# ── EquipmentRepository ──────────────────────────────────────────────────────

class TestEquipmentRepository:
    @pytest.mark.asyncio
    async def test_get_by_facility(self):
        session = make_mock_session()
        fac_id = uuid.uuid4()
        eq = EquipmentModel(id=uuid.uuid4(), hazardous_facility_id=fac_id, name="K-500")
        session.execute.return_value = make_mock_result(scalar_values=[eq])

        repo = EquipmentRepository(session)
        result = await repo.get_by_facility(fac_id)
        assert len(result) == 1
        assert result[0].name == "K-500"


# ── SubstanceRepository ──────────────────────────────────────────────────────

class TestSubstanceRepository:
    @pytest.mark.asyncio
    async def test_get_by_facility(self):
        session = make_mock_session()
        fac_id = uuid.uuid4()
        sub = HazardousSubstanceModel(id=uuid.uuid4(), hazardous_facility_id=fac_id, name="Methane")
        session.execute.return_value = make_mock_result(scalar_values=[sub])

        repo = SubstanceRepository(session)
        result = await repo.get_by_facility(fac_id)
        assert len(result) == 1


# ── PersonRepository ─────────────────────────────────────────────────────────

class TestPersonRepository:
    @pytest.mark.asyncio
    async def test_get_by_organization(self):
        session = make_mock_session()
        org_id = uuid.uuid4()
        person = ResponsiblePersonModel(id=uuid.uuid4(), organization_id=org_id, full_name="Ivanov")
        session.execute.return_value = make_mock_result(scalar_values=[person])

        repo = PersonRepository(session)
        result = await repo.get_by_organization(org_id)
        assert len(result) == 1
        assert result[0].full_name == "Ivanov"
