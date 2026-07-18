"""Тесты расширенной карточки организации: модель, API, сериализация."""
import uuid
from datetime import date
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from src.main import app
from src.api.dependencies import get_organization_repo
from src.api.routers.organizations import (
    BankAccountCreate,
    BankAccountResponse,
    LicenseCreate,
    LicenseResponse,
    OkvedCodeCreate,
    OkvedCodeResponse,
    OrganizationCreate,
    OrganizationDetailResponse,
    OrganizationResponse,
    OrganizationUpdate,
)
from src.application.services.pmla_context_builder import build_organization_dict
from src.infrastructure.database.models import (
    BankAccountModel,
    LicenseModel,
    OkvedCodeModel,
    OrganizationModel,
)
from src.infrastructure.repositories.organization_repo import OrganizationRepository
from tests.integration.test_api import FakeModel, fake_org, make_mock_repo


# ── Pydantic Schema Tests ─────────────────────────────────────────────────────

class TestOrganizationCreateSchema:
    def test_minimal(self):
        """Только обязательные поля (обратная совместимость)."""
        s = OrganizationCreate(name="Тест", inn="1234567890")
        assert s.name == "Тест"
        assert s.inn == "1234567890"
        assert s.org_type == "legal"  # default

    def test_full(self):
        """Все поля заполнены."""
        s = OrganizationCreate(
            name="ООО Тест",
            inn="1234567890",
            ogrn="1027700000000",
            address="г. Москва",
            phone="+7 (495) 123-45-67",
            email="test@test.ru",
            org_type="legal",
            full_name="Общество с ограниченной ответственностью «Тест»",
            short_name="ООО «Тест»",
            legal_address="г. Москва, ул. Тестовая, д. 1",
            actual_address="г. Москва, ул. Тестовая, д. 2",
            postal_address="г. Москва, ул. Тестовая, д. 3",
            phone_additional="+7 (495) 234-56-78",
            phone_mobile="+7 (999) 111-22-33",
            fax="+7 (495) 345-67-89",
            website="https://test.ru",
            kpp="123456789",
            ogrnip="315770000000000",
            okpo="12345678",
            director_full_name="Иванов Иван Иванович",
            director_position="Генеральный директор",
            director_phone="+7 (999) 222-33-44",
            director_email="dir@test.ru",
            ip_last_name="Сидоров",
            ip_first_name="Петр",
            ip_middle_name="Алексеевич",
        )
        assert s.full_name == "Общество с ограниченной ответственностью «Тест»"
        assert s.kpp == "123456789"
        assert s.director_full_name == "Иванов Иван Иванович"

    def test_org_type_validation(self):
        """org_type должен быть legal или individual."""
        OrganizationCreate(name="Тест", inn="123", org_type="legal")
        OrganizationCreate(name="Тест", inn="123", org_type="individual")
        with pytest.raises(ValidationError):
            OrganizationCreate(name="Тест", inn="123", org_type="unknown")

    def test_no_nested_fields_in_organization_create(self):
        """Вложенные сущности НЕ принимаются в POST organization."""
        s = OrganizationCreate(name="Тест", inn="123")
        assert not hasattr(s, "bank_accounts")
        assert not hasattr(s, "okved_codes")
        assert not hasattr(s, "licenses")


class TestOrganizationUpdateSchema:
    def test_partial_update(self):
        """Частичное обновление — все поля опциональны."""
        s = OrganizationUpdate(name="Новое имя")
        assert s.name == "Новое имя"
        assert s.inn is None

    def test_update_new_fields(self):
        """Обновление новых полей."""
        s = OrganizationUpdate(full_name="Новое полное имя", director_position="Директор")
        assert s.full_name == "Новое полное имя"
        assert s.director_position == "Директор"


class TestOrganizationResponseSchema:
    def test_from_orm(self):
        """Десериализация из ORM-подобного объекта."""
        obj = FakeModel(
            id=uuid.uuid4(), name="Тест", inn="123", ogrn=None,
            address=None, phone=None, email=None,
            org_type="legal", full_name=None, short_name=None,
            legal_address=None, actual_address=None, postal_address=None,
            phone_additional=None, phone_mobile=None, fax=None, website=None,
            kpp=None, ogrnip=None, okpo=None,
            director_full_name=None, director_position=None,
            director_phone=None, director_email=None,
            ip_last_name=None, ip_first_name=None, ip_middle_name=None,
        )
        resp = OrganizationResponse.model_validate(obj)
        assert resp.name == "Тест"
        assert resp.org_type == "legal"


class TestOrganizationDetailResponse:
    def test_with_related(self):
        """Детальный ответ с вложенными таблицами."""
        org_id = uuid.uuid4()
        bank_acc = FakeModel(
            id=uuid.uuid4(), organization_id=org_id,
            account_number="40702810123450000001",
            bank_name="Сбербанк", bank_bik="044525225",
            bank_corr_account="30101810400000000225",
            currency="RUB", is_primary=1, notes=None,
        )
        okved = FakeModel(
            id=uuid.uuid4(), organization_id=org_id,
            code="43.22", description="Тест", is_primary=0,
        )
        lic = FakeModel(
            id=uuid.uuid4(), organization_id=org_id,
            activity_type="Эксплуатация ОПО",
            license_number="Л-001", issue_date=date(2024, 1, 1),
            status="active", file_path="licenses/2024_license.pdf",
            file_name="license.pdf", file_size=1024,
            mime_type="application/pdf", checksum_sha256="abc123",
        )
        lic_resp = LicenseResponse.from_model(lic)
        obj = FakeModel(
            id=org_id, name="Тест", inn="123", ogrn=None,
            address=None, phone=None, email=None,
            org_type="legal", full_name=None, short_name=None,
            legal_address=None, actual_address=None, postal_address=None,
            phone_additional=None, phone_mobile=None, fax=None, website=None,
            kpp=None, ogrnip=None, okpo=None,
            director_full_name=None, director_position=None,
            director_phone=None, director_email=None,
            ip_last_name=None, ip_first_name=None, ip_middle_name=None,
            bank_accounts=[bank_acc],
            okved_codes=[okved],
            licenses=[lic_resp],  # Pre-built responses for from_attributes passthrough
        )
        resp = OrganizationDetailResponse.model_validate(obj, from_attributes=True)
        assert len(resp.bank_accounts) == 1
        assert resp.bank_accounts[0].account_number == "40702810123450000001"
        assert resp.bank_accounts[0].is_primary is True
        assert len(resp.okved_codes) == 1
        assert resp.okved_codes[0].code == "43.22"
        assert len(resp.licenses) == 1
        assert resp.licenses[0].license_number == "Л-001"
        # License file_path is hidden, has_file flag is computed
        assert not hasattr(resp.licenses[0], "file_path")
        assert resp.licenses[0].has_file is True
        assert resp.licenses[0].file_name == "license.pdf"
        assert resp.licenses[0].checksum_sha256 == "abc123"


# ── Nested Schema Tests ───────────────────────────────────────────────────────

class TestBankAccount:
    def test_create_minimal(self):
        s = BankAccountCreate(account_number="40702810123450000001")
        assert s.currency == "RUB"
        assert s.is_primary is False


class TestOkvedCode:
    def test_create_minimal(self):
        s = OkvedCodeCreate(code="43.22")
        assert s.code == "43.22"


class TestLicense:
    def test_create_minimal(self):
        s = LicenseCreate(activity_type="Эксплуатация", license_number="Л-001")
        assert s.status == "active"
        # LicenseCreate only has agreed-upon fields
        assert not hasattr(s, "notes")
        assert not hasattr(s, "file_path")

    def test_response_hides_file_path(self):
        """LicenseResponse не возвращает file_path."""
        lic = FakeModel(
            id=uuid.uuid4(), organization_id=uuid.uuid4(),
            activity_type="Эксплуатация",
            license_number="Л-001", issue_date=date(2024, 6, 15),
            status="active", file_path="licenses/secret.pdf",
            file_name="license.pdf", file_size=1024,
            mime_type="application/pdf", checksum_sha256="abc123",
        )
        resp = LicenseResponse.from_model(lic)
        assert resp.activity_type == "Эксплуатация"
        assert resp.status == "active"
        assert resp.file_name == "license.pdf"
        assert resp.has_file is True
        # Critical: file_path is NEVER returned
        assert not hasattr(resp, "file_path")
        assert resp.checksum_sha256 == "abc123"


# ── API Endpoint Tests ────────────────────────────────────────────────────────

@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
class TestOrganizationCardAPI:
    async def test_create_with_new_fields(self, client):
        """Создание организации с новыми полями (обратная совместимость)."""
        org = fake_org(
            full_name="ООО «Тест»",
            director_position="Генеральный директор",
            director_full_name="Иванов Иван Иванович",
        )
        app.dependency_overrides[get_organization_repo] = lambda: make_mock_repo(return_value=org)
        resp = await client.post("/api/v1/organizations/", json={
            "name": "Тест", "inn": "1234567890",
            "full_name": "ООО «Тест»",
            "director_position": "Генеральный директор",
            "director_full_name": "Иванов Иван Иванович",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["full_name"] == "ООО «Тест»"
        assert data["director_full_name"] == "Иванов Иван Иванович"
        app.dependency_overrides.clear()

    async def test_create_individual(self, client):
        """Создание организации типа ИП."""
        org = fake_org(
            org_type="individual",
            ip_last_name="Сидоров",
            ip_first_name="Петр",
            ip_middle_name="Алексеевич",
        )
        app.dependency_overrides[get_organization_repo] = lambda: make_mock_repo(return_value=org)
        resp = await client.post("/api/v1/organizations/", json={
            "name": "ИП Сидоров П.А.", "inn": "1234567890", "org_type": "individual",
            "ip_last_name": "Сидоров", "ip_first_name": "Петр", "ip_middle_name": "Алексеевич",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["org_type"] == "individual"
        assert data["ip_last_name"] == "Сидоров"
        app.dependency_overrides.clear()

    async def test_get_detail_not_found(self, client):
        """GET /detail для несуществующей организации."""
        mock_repo = make_mock_repo(return_value=None)
        mock_repo.get_with_related = AsyncMock(return_value=None)
        app.dependency_overrides[get_organization_repo] = lambda: mock_repo
        resp = await client.get(f"/api/v1/organizations/{uuid.uuid4()}/detail")
        assert resp.status_code == 404
        app.dependency_overrides.clear()

    async def test_update_new_fields(self, client):
        """Обновление новых полей организации."""
        org = fake_org(full_name="Обновлено")
        app.dependency_overrides[get_organization_repo] = lambda: make_mock_repo(return_value=org)
        resp = await client.put(f"/api/v1/organizations/{org.id}", json={
            "full_name": "Обновлено",
            "director_position": "Технический директор",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["full_name"] == "Обновлено"
        app.dependency_overrides.clear()


# ── Repository Compatibility Tests ────────────────────────────────────────────

class TestOrgModelDefaults:
    """Проверка, что OrganizationModel создаётся со старыми полями."""

    def test_old_fields_still_work(self):
        """Создание модели только со старыми полями (обратная совместимость)."""
        org = OrganizationModel(name="Тест", inn="123")
        assert org.name == "Тест"
        assert org.inn == "123"
        assert org.org_type is None  # SQLAlchemy default применяется при INSERT, не в Python

    def test_new_fields_accessible(self):
        """Новые поля модели доступны."""
        org = OrganizationModel(
            name="Тест", inn="123",
            full_name="ООО «Тест»",
            director_full_name="Иванов И.И.",
            kpp="123456789",
        )
        assert org.full_name == "ООО «Тест»"
        assert org.kpp == "123456789"

    def test_related_models(self):
        """Связанные модели создаются корректно (минимальные поля)."""
        oid = uuid.uuid4()
        bank = BankAccountModel(account_number="40702810123450000001", organization_id=oid)
        assert bank.account_number == "40702810123450000001"

        okved = OkvedCodeModel(code="43.22", organization_id=oid)
        assert okved.code == "43.22"

        lic = LicenseModel(activity_type="Эксплуатация", license_number="Л-001", organization_id=oid)
        assert lic.activity_type == "Эксплуатация"
        assert lic.license_number == "Л-001"


# ── Compatibility Mapping Tests ───────────────────────────────────────────────

class TestBuildOrganizationDict:
    """Проверка единой функции маппинга build_organization_dict."""

    def test_old_org_without_new_fields(self):
        """Старая организация без новых полей генерирует старый contract."""
        org = OrganizationModel(id=uuid.uuid4(), name="ООО Старый", inn="7700123456",
                                 ogrn="1027700000000", address="г. Москва, ул. Старая",
                                 phone="+7 (495) 123-45-67", email="old@test.ru")
        d = build_organization_dict(org)
        # Старые поля сохраняются
        assert d["name"] == "ООО Старый"
        assert d["inn"] == "7700123456"
        assert d["ogrn"] == "1027700000000"
        assert d["address"] == "г. Москва, ул. Старая"
        assert d["phone"] == "+7 (495) 123-45-67"
        assert d["email"] == "old@test.ru"
        # Новые поля fallback к старым
        assert d["full_name"] == "ООО Старый"       # fallback → name
        assert d["short_name"] == "ООО Старый"      # fallback → name
        assert d["legal_address"] == "г. Москва, ул. Старая"  # fallback → address
        assert d["org_type"] == "legal"              # default

    def test_new_org_with_only_new_fields(self):
        """Новая организация только с новыми полями — старые поля тоже заполняются."""
        org = OrganizationModel(
            id=uuid.uuid4(), name="ООО Новый", inn="7700999999",
            full_name="Общество с ограниченной ответственностью «Новый»",
            short_name="ООО «Новый»",
            legal_address="г. Москва, ул. Новая, д. 1",
            actual_address="г. Москва, ул. Новая, д. 2",
            director_full_name="Петров Петр Петрович",
        )
        d = build_organization_dict(org)
        # Новые поля используются напрямую
        assert d["full_name"] == "Общество с ограниченной ответственностью «Новый»"
        assert d["short_name"] == "ООО «Новый»"
        assert d["legal_address"] == "г. Москва, ул. Новая, д. 1"
        assert d["actual_address"] == "г. Москва, ул. Новая, д. 2"
        assert d["director_full_name"] == "Петров Петр Петрович"
        # Старые поля тоже заполнены (требование обратной совместимости)
        assert d["name"] == "ООО Новый"
        assert d["address"] == ""  # не задано
        assert d["org_type"] == "legal"

    def test_change_full_name_propagates(self):
        """Изменение full_name обновляет значение для ПМЛА."""
        org = OrganizationModel(
            id=uuid.uuid4(), name="ООО Старое", inn="123",
            full_name="Общество с ограниченной ответственностью «Старое»",
        )
        d = build_organization_dict(org)
        assert d["full_name"] == "Общество с ограниченной ответственностью «Старое»"
        assert d["full_name"] != d["name"]  # разные значения

    def test_empty_new_fields_use_old(self):
        """Пустые новые поля используют старые значения (fallback)."""
        org = OrganizationModel(
            id=uuid.uuid4(), name="ООО Тест", inn="123",
            address="г. Тест", phone="+7 (999) 000-00-00", email="test@test.ru",
            full_name="",  # пустое
            short_name=None,
            legal_address=None,
        )
        d = build_organization_dict(org)
        assert d["full_name"] == "ООО Тест"               # fallback → name
        assert d["short_name"] == "ООО Тест"              # fallback → name
        assert d["legal_address"] == "г. Тест"             # fallback → address
        assert d["phone"] == "+7 (999) 000-00-00"          # старое поле напрямую
        assert d["email"] == "test@test.ru"                # старое поле напрямую

    def test_none_org_returns_empty(self):
        """None вместо организации возвращает пустой словарь."""
        assert build_organization_dict(None) == {}


class TestCascadeDelete:
    """Удаление организации каскадно удаляет связанные записи.

    Модели BankAccountModel, OkvedCodeModel, LicenseModel имеют
    ForeignKey("organizations.id", ondelete="CASCADE"), поэтому при удалении
    организации через DELETE endpoint связанные записи удаляются автоматически.
    Файлы лицензий на диске не удаляются (orphan-файлы зачищаются фоновой задачей).
    """

    def test_bank_account_foreign_key_has_cascade(self):
        """BankAccountModel FK имеет ondelete=CASCADE."""
        from sqlalchemy import ForeignKey
        # Проверяем через introspection constraints модели
        for c in BankAccountModel.__table__.foreign_key_constraints:
            if list(c.columns) == [BankAccountModel.__table__.c.organization_id]:
                assert c.ondelete == "CASCADE", (
                    f"Expected CASCADE, got {c.ondelete}"
                )
                return
        raise AssertionError("Foreign key on organization_id not found in BankAccountModel")

    def test_okved_code_foreign_key_has_cascade(self):
        """OkvedCodeModel FK имеет ondelete=CASCADE."""
        for c in OkvedCodeModel.__table__.foreign_key_constraints:
            if list(c.columns) == [OkvedCodeModel.__table__.c.organization_id]:
                assert c.ondelete == "CASCADE"
                return
        raise AssertionError("Foreign key on organization_id not found in OkvedCodeModel")

    def test_license_foreign_key_has_cascade(self):
        """LicenseModel FK имеет ondelete=CASCADE."""
        for c in LicenseModel.__table__.foreign_key_constraints:
            if list(c.columns) == [LicenseModel.__table__.c.organization_id]:
                assert c.ondelete == "CASCADE"
                return
        raise AssertionError("Foreign key on organization_id not found in LicenseModel")
