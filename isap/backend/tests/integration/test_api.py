"""Интеграционные тесты API — мокаем зависимости через FastAPI dependency override."""
import uuid
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app
from src.api.dependencies import get_organization_repo, get_facility_repo, get_equipment_repo, get_substance_repo, get_person_repo


def make_mock_repo(return_value=None, list_value=None, delete_return=True):
    repo = AsyncMock()
    if return_value is not None:
        repo.create.return_value = return_value
        repo.get.return_value = return_value
        repo.update.return_value = return_value
    else:
        repo.get.return_value = None
    repo.get_multi.return_value = list_value or []
    repo.delete.return_value = delete_return
    return repo


class FakeModel:
    """Универсальная заглушка ORM-модели с нужными атрибутами."""
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


def fake_org(**kw):
    defaults = {"id": uuid.uuid4(), "name": "ТестОрг", "inn": "1234567890", "ogrn": None, "address": "г. Тест", "phone": "+79990001122", "email": "t@t.ru"}
    defaults.update(kw)
    return FakeModel(**defaults)


def fake_fac(**kw):
    defaults = {"id": uuid.uuid4(), "organization_id": uuid.uuid4(), "name": "ТестОПО", "reg_number": "РВ-00-00001", "hazard_class": 3, "facility_type": "КС", "address": "Адрес", "latitude": None, "longitude": None, "commissioning_date": None, "inventory_number": None, "properties": {}}
    defaults.update(kw)
    return FakeModel(**defaults)


def fake_eq(**kw):
    defaults = {"id": uuid.uuid4(), "hazardous_facility_id": uuid.uuid4(), "name": "Компрессор", "equipment_type": "Осевой", "serial_number": "SN-001", "manufacturer": "Завод", "manufacture_year": 2020, "specifications": {}}
    defaults.update(kw)
    return FakeModel(**defaults)


def fake_sub(**kw):
    defaults = {"id": uuid.uuid4(), "hazardous_facility_id": uuid.uuid4(), "name": "Метан", "cas_number": "74-82-8", "quantity_kg": 5000, "threshold_quantity_kg": 1000, "hazard_properties": {}}
    defaults.update(kw)
    return FakeModel(**defaults)


def fake_person(**kw):
    defaults = {"id": uuid.uuid4(), "organization_id": uuid.uuid4(), "full_name": "Иванов И.И.", "position": "Начальник ПБ", "role": "safety_manager", "phone": "+79991234567", "email": None}
    defaults.update(kw)
    return FakeModel(**defaults)


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


# ── Organizations ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestOrganizationsAPI:
    async def test_create(self, client):
        org = fake_org()
        app.dependency_overrides[get_organization_repo] = lambda: make_mock_repo(return_value=org)
        resp = await client.post("/api/v1/organizations/", json={"name": "ТестОрг", "inn": "1234567890"})
        assert resp.status_code == 201
        assert resp.json()["name"] == "ТестОрг"
        app.dependency_overrides.clear()

    async def test_list(self, client):
        app.dependency_overrides[get_organization_repo] = lambda: make_mock_repo(list_value=[fake_org(), fake_org()])
        resp = await client.get("/api/v1/organizations/")
        assert resp.status_code == 200
        assert len(resp.json()) == 2
        app.dependency_overrides.clear()

    async def test_get_found(self, client):
        org = fake_org()
        app.dependency_overrides[get_organization_repo] = lambda: make_mock_repo(return_value=org)
        resp = await client.get(f"/api/v1/organizations/{org.id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "ТестОрг"
        app.dependency_overrides.clear()

    async def test_get_not_found(self, client):
        app.dependency_overrides[get_organization_repo] = lambda: make_mock_repo(return_value=None)
        resp = await client.get(f"/api/v1/organizations/{uuid.uuid4()}")
        assert resp.status_code == 404
        app.dependency_overrides.clear()

    async def test_update(self, client):
        org = fake_org(name="Обновлено")
        app.dependency_overrides[get_organization_repo] = lambda: make_mock_repo(return_value=org)
        resp = await client.put(f"/api/v1/organizations/{org.id}", json={"name": "Обновлено"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "Обновлено"
        app.dependency_overrides.clear()

    async def test_delete(self, client):
        app.dependency_overrides[get_organization_repo] = lambda: make_mock_repo(delete_return=True)
        resp = await client.delete(f"/api/v1/organizations/{uuid.uuid4()}")
        assert resp.status_code == 204
        app.dependency_overrides.clear()

    async def test_delete_not_found(self, client):
        app.dependency_overrides[get_organization_repo] = lambda: make_mock_repo(delete_return=False)
        resp = await client.delete(f"/api/v1/organizations/{uuid.uuid4()}")
        assert resp.status_code == 404
        app.dependency_overrides.clear()


# ── Facilities ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestFacilitiesAPI:
    async def test_create(self, client):
        fac = fake_fac()
        app.dependency_overrides[get_facility_repo] = lambda: make_mock_repo(return_value=fac)
        resp = await client.post("/api/v1/facilities/", json={"organization_id": str(uuid.uuid4()), "name": "ТестОПО"})
        assert resp.status_code == 201
        app.dependency_overrides.clear()

    async def test_list(self, client):
        app.dependency_overrides[get_facility_repo] = lambda: make_mock_repo(list_value=[fake_fac()])
        resp = await client.get("/api/v1/facilities/")
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        app.dependency_overrides.clear()

    async def test_get_found(self, client):
        fac = fake_fac()
        app.dependency_overrides[get_facility_repo] = lambda: make_mock_repo(return_value=fac)
        resp = await client.get(f"/api/v1/facilities/{fac.id}")
        assert resp.status_code == 200
        app.dependency_overrides.clear()

    async def test_get_not_found(self, client):
        app.dependency_overrides[get_facility_repo] = lambda: make_mock_repo(return_value=None)
        resp = await client.get(f"/api/v1/facilities/{uuid.uuid4()}")
        assert resp.status_code == 404
        app.dependency_overrides.clear()

    async def test_delete(self, client):
        app.dependency_overrides[get_facility_repo] = lambda: make_mock_repo(delete_return=True)
        resp = await client.delete(f"/api/v1/facilities/{uuid.uuid4()}")
        assert resp.status_code == 204
        app.dependency_overrides.clear()


# ── Equipment ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestEquipmentAPI:
    async def test_create(self, client):
        eq = fake_eq()
        app.dependency_overrides[get_equipment_repo] = lambda: make_mock_repo(return_value=eq)
        resp = await client.post("/api/v1/equipment/", json={"hazardous_facility_id": str(uuid.uuid4()), "name": "Компрессор"})
        assert resp.status_code == 201
        app.dependency_overrides.clear()

    async def test_list(self, client):
        app.dependency_overrides[get_equipment_repo] = lambda: make_mock_repo(list_value=[fake_eq()])
        resp = await client.get("/api/v1/equipment/")
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        app.dependency_overrides.clear()

    async def test_delete(self, client):
        app.dependency_overrides[get_equipment_repo] = lambda: make_mock_repo(delete_return=True)
        resp = await client.delete(f"/api/v1/equipment/{uuid.uuid4()}")
        assert resp.status_code == 204
        app.dependency_overrides.clear()


# ── Substances ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestSubstancesAPI:
    async def test_create(self, client):
        sub = fake_sub()
        app.dependency_overrides[get_substance_repo] = lambda: make_mock_repo(return_value=sub)
        resp = await client.post("/api/v1/substances/", json={"hazardous_facility_id": str(uuid.uuid4()), "name": "Метан"})
        assert resp.status_code == 201
        app.dependency_overrides.clear()

    async def test_list(self, client):
        app.dependency_overrides[get_substance_repo] = lambda: make_mock_repo(list_value=[fake_sub()])
        resp = await client.get("/api/v1/substances/")
        assert resp.status_code == 200
        app.dependency_overrides.clear()

    async def test_delete(self, client):
        app.dependency_overrides[get_substance_repo] = lambda: make_mock_repo(delete_return=True)
        resp = await client.delete(f"/api/v1/substances/{uuid.uuid4()}")
        assert resp.status_code == 204
        app.dependency_overrides.clear()


# ── Persons ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestPersonsAPI:
    async def test_create(self, client):
        person = fake_person()
        app.dependency_overrides[get_person_repo] = lambda: make_mock_repo(return_value=person)
        resp = await client.post("/api/v1/persons/", json={"organization_id": str(uuid.uuid4()), "full_name": "Иванов И.И."})
        assert resp.status_code == 201
        app.dependency_overrides.clear()

    async def test_list(self, client):
        app.dependency_overrides[get_person_repo] = lambda: make_mock_repo(list_value=[fake_person()])
        resp = await client.get("/api/v1/persons/")
        assert resp.status_code == 200
        app.dependency_overrides.clear()

    async def test_delete(self, client):
        app.dependency_overrides[get_person_repo] = lambda: make_mock_repo(delete_return=True)
        resp = await client.delete(f"/api/v1/persons/{uuid.uuid4()}")
        assert resp.status_code == 204
        app.dependency_overrides.clear()


# ── Health ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestHealth:
    async def test_health(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
