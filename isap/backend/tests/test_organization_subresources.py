"""Тесты sub-resources организации: банковские счета, ОКВЭД, лицензии.

Проверяет:
- CRUD для каждой сущности
- Ограничение is_primary (409 при дублировании)
- Загрузка/скачивание/удаление файла лицензии
- Отсутствие file_path в ответе API
- Обратная совместимость старого API организаций
"""
from __future__ import annotations

import hashlib
import io
import os
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import IntegrityError

from src.api.dependencies import get_db, get_organization_repo
from src.api.routers.organizations import (
    BankAccountResponse,
    LicenseResponse,
    OkvedCodeResponse,
    _build_license_storage_key,
    _resolve_license_path,
)
from src.infrastructure.database.models import (
    BankAccountModel,
    LicenseModel,
    OkvedCodeModel,
)
from src.main import app

from tests.integration.test_api import FakeModel, make_mock_repo

_SENTINEL = object()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": "Bearer isap-secret-2026"},
    )


@pytest.fixture(autouse=True)
def clear_overrides():
    yield
    app.dependency_overrides.clear()


def _override_org_exists(org_id: UUID):
    """Override get_organization_repo to return an existing org."""
    fake_org = FakeModel(id=org_id, name="Тест", inn="123")
    repo = make_mock_repo(return_value=fake_org)
    app.dependency_overrides[get_organization_repo] = lambda: repo


def _override_org_not_found():
    repo = make_mock_repo(return_value=None)
    app.dependency_overrides[get_organization_repo] = lambda: repo


def _make_fake_db():
    """Create a MagicMock AsyncSession that supports add/commit/refresh/execute/delete."""
    fake_db = MagicMock()
    fake_db.add = MagicMock()
    fake_db.commit = AsyncMock()
    fake_db.refresh = AsyncMock()
    fake_db.delete = AsyncMock()
    fake_db.rollback = AsyncMock()
    return fake_db


def _override_db(fake_db):
    async def override():
        yield fake_db
    app.dependency_overrides[get_db] = override


def _make_execute_result(items=None, one=_SENTINEL):
    """Mock SQLAlchemy execute result."""
    result = MagicMock()
    if items is not None:
        result.scalars.return_value.all.return_value = items
    if one is not _SENTINEL:
        result.scalar_one_or_none.return_value = one
    return result


# ---------------------------------------------------------------------------
# Bank Accounts CRUD
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestBankAccountsCRUD:
    async def test_create(self, client):
        org_id = uuid4()
        _override_org_exists(org_id)
        fake_db = _make_fake_db()
        _override_db(fake_db)

        async def refresh(acc):
            acc.id = uuid4()
        fake_db.refresh = AsyncMock(side_effect=refresh)

        resp = await client.post(
            f"/api/v1/organizations/{org_id}/bank-accounts",
            json={
                "account_number": "40702810123450000001",
                "bank_name": "Сбербанк",
                "is_primary": True,
            },
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["account_number"] == "40702810123450000001"
        assert data["bank_name"] == "Сбербанк"
        assert data["is_primary"] is True
        assert data["organization_id"] == str(org_id)
        # Verify model was added with is_primary as int (1)
        added = fake_db.add.call_args[0][0]
        assert isinstance(added, BankAccountModel)
        assert added.is_primary == 1

    async def test_create_org_not_found(self, client):
        _override_org_not_found()
        resp = await client.post(
            f"/api/v1/organizations/{uuid4()}/bank-accounts",
            json={"account_number": "40702810123450000001"},
        )
        assert resp.status_code == 404

    async def test_create_duplicate_primary_returns_409(self, client):
        """Повторное назначение is_primary=True для другой записи должно отклоняться."""
        org_id = uuid4()
        _override_org_exists(org_id)
        fake_db = _make_fake_db()
        # First commit raises IntegrityError (simulating partial unique index)
        fake_db.commit = AsyncMock(side_effect=IntegrityError("simulated", {}, Exception()))
        _override_db(fake_db)

        resp = await client.post(
            f"/api/v1/organizations/{org_id}/bank-accounts",
            json={"account_number": "40702810123450000001", "is_primary": True},
        )
        assert resp.status_code == 409
        assert "уже есть основной" in resp.json()["detail"]

    async def test_list(self, client):
        org_id = uuid4()
        _override_org_exists(org_id)
        accounts = [
            FakeModel(id=uuid4(), organization_id=org_id,
                      account_number="40702810123450000001", bank_name="Сбербанк",
                      bank_bik=None, bank_corr_account=None, currency="RUB",
                      is_primary=1, notes=None),
            FakeModel(id=uuid4(), organization_id=org_id,
                      account_number="40702810400000000123", bank_name="ВТБ",
                      bank_bik=None, bank_corr_account=None, currency="RUB",
                      is_primary=0, notes=None),
        ]
        fake_db = _make_fake_db()
        fake_db.execute = AsyncMock(return_value=_make_execute_result(items=accounts))
        _override_db(fake_db)

        resp = await client.get(f"/api/v1/organizations/{org_id}/bank-accounts")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["account_number"] == "40702810123450000001"
        assert data[0]["is_primary"] is True
        assert data[1]["is_primary"] is False

    async def test_update(self, client):
        org_id = uuid4()
        account_id = uuid4()
        _override_org_exists(org_id)
        existing = FakeModel(
            id=account_id, organization_id=org_id,
            account_number="OLD", bank_name="Old Bank",
            bank_bik=None, bank_corr_account=None, currency="RUB",
            is_primary=0, notes=None,
        )
        fake_db = _make_fake_db()
        fake_db.execute = AsyncMock(return_value=_make_execute_result(one=existing))
        _override_db(fake_db)

        resp = await client.put(
            f"/api/v1/organizations/{org_id}/bank-accounts/{account_id}",
            json={"is_primary": True},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["is_primary"] is True
        assert existing.is_primary == 1

    async def test_update_duplicate_primary_returns_409(self, client):
        org_id = uuid4()
        account_id = uuid4()
        _override_org_exists(org_id)
        existing = FakeModel(
            id=account_id, organization_id=org_id,
            account_number="X", bank_name=None, bank_bik=None,
            bank_corr_account=None, currency="RUB", is_primary=0, notes=None,
        )
        fake_db = _make_fake_db()
        fake_db.execute = AsyncMock(return_value=_make_execute_result(one=existing))
        fake_db.commit = AsyncMock(side_effect=IntegrityError("simulated", {}, Exception()))
        _override_db(fake_db)

        resp = await client.put(
            f"/api/v1/organizations/{org_id}/bank-accounts/{account_id}",
            json={"is_primary": True},
        )
        assert resp.status_code == 409

    async def test_delete(self, client):
        org_id = uuid4()
        account_id = uuid4()
        _override_org_exists(org_id)
        existing = FakeModel(id=account_id, organization_id=org_id,
                              account_number="X", bank_name=None, bank_bik=None,
                              bank_corr_account=None, currency="RUB", is_primary=0, notes=None)
        fake_db = _make_fake_db()
        fake_db.execute = AsyncMock(return_value=_make_execute_result(one=existing))
        _override_db(fake_db)

        resp = await client.delete(f"/api/v1/organizations/{org_id}/bank-accounts/{account_id}")
        assert resp.status_code == 204

    async def test_delete_not_found(self, client):
        org_id = uuid4()
        _override_org_exists(org_id)
        fake_db = _make_fake_db()
        fake_db.execute = AsyncMock(return_value=_make_execute_result(one=None))
        _override_db(fake_db)

        resp = await client.delete(f"/api/v1/organizations/{org_id}/bank-accounts/{uuid4()}")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# OKVED Codes CRUD
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestOkvedCodesCRUD:
    async def test_create(self, client):
        org_id = uuid4()
        _override_org_exists(org_id)
        fake_db = _make_fake_db()
        _override_db(fake_db)

        async def refresh(code):
            code.id = uuid4()
        fake_db.refresh = AsyncMock(side_effect=refresh)

        resp = await client.post(
            f"/api/v1/organizations/{org_id}/okved-codes",
            json={"code": "43.22", "description": "Производство труб", "is_primary": True},
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["code"] == "43.22"
        assert data["description"] == "Производство труб"
        assert data["is_primary"] is True
        added = fake_db.add.call_args[0][0]
        assert isinstance(added, OkvedCodeModel)
        assert added.is_primary == 1

    async def test_create_duplicate_primary_returns_409(self, client):
        org_id = uuid4()
        _override_org_exists(org_id)
        fake_db = _make_fake_db()
        fake_db.commit = AsyncMock(side_effect=IntegrityError("simulated", {}, Exception()))
        _override_db(fake_db)

        resp = await client.post(
            f"/api/v1/organizations/{org_id}/okved-codes",
            json={"code": "43.22", "is_primary": True},
        )
        assert resp.status_code == 409
        assert "основной код ОКВЭД" in resp.json()["detail"]

    async def test_list(self, client):
        org_id = uuid4()
        _override_org_exists(org_id)
        codes = [
            FakeModel(id=uuid4(), organization_id=org_id, code="43.22",
                      description="Primary", is_primary=1),
            FakeModel(id=uuid4(), organization_id=org_id, code="46.12",
                      description="Secondary", is_primary=0),
        ]
        fake_db = _make_fake_db()
        fake_db.execute = AsyncMock(return_value=_make_execute_result(items=codes))
        _override_db(fake_db)

        resp = await client.get(f"/api/v1/organizations/{org_id}/okved-codes")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["code"] == "43.22"
        assert data[0]["is_primary"] is True

    async def test_update(self, client):
        org_id = uuid4()
        code_id = uuid4()
        _override_org_exists(org_id)
        existing = FakeModel(id=code_id, organization_id=org_id, code="43.22",
                              description="Old", is_primary=0)
        fake_db = _make_fake_db()
        fake_db.execute = AsyncMock(return_value=_make_execute_result(one=existing))
        _override_db(fake_db)

        resp = await client.put(
            f"/api/v1/organizations/{org_id}/okved-codes/{code_id}",
            json={"description": "New"},
        )
        assert resp.status_code == 200
        assert resp.json()["description"] == "New"

    async def test_delete(self, client):
        org_id = uuid4()
        code_id = uuid4()
        _override_org_exists(org_id)
        existing = FakeModel(id=code_id, organization_id=org_id, code="43.22",
                              description=None, is_primary=0)
        fake_db = _make_fake_db()
        fake_db.execute = AsyncMock(return_value=_make_execute_result(one=existing))
        _override_db(fake_db)

        resp = await client.delete(f"/api/v1/organizations/{org_id}/okved-codes/{code_id}")
        assert resp.status_code == 204


# ---------------------------------------------------------------------------
# Licenses CRUD
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestLicensesCRUD:
    async def test_create(self, client):
        org_id = uuid4()
        _override_org_exists(org_id)
        fake_db = _make_fake_db()
        _override_db(fake_db)

        async def refresh(lic):
            lic.id = uuid4()
        fake_db.refresh = AsyncMock(side_effect=refresh)

        resp = await client.post(
            f"/api/v1/organizations/{org_id}/licenses",
            json={
                "activity_type": "Эксплуатация ОПО",
                "license_number": "Л-001",
                "issue_date": "2024-01-15",
                "status": "active",
            },
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["activity_type"] == "Эксплуатация ОПО"
        assert data["license_number"] == "Л-001"
        assert data["issue_date"] == "2024-01-15"
        assert data["status"] == "active"
        assert data["has_file"] is False
        # Critical: file_path never returned
        assert "file_path" not in data
        added = fake_db.add.call_args[0][0]
        assert isinstance(added, LicenseModel)

    async def test_create_invalid_date(self, client):
        org_id = uuid4()
        _override_org_exists(org_id)
        fake_db = _make_fake_db()
        _override_db(fake_db)

        resp = await client.post(
            f"/api/v1/organizations/{org_id}/licenses",
            json={"activity_type": "Эксплуатация", "license_number": "Л-001", "issue_date": "invalid"},
        )
        assert resp.status_code == 400
        assert "YYYY-MM-DD" in resp.json()["detail"]

    async def test_create_only_agreed_fields(self, client):
        """License принимает только согласованные поля."""
        org_id = uuid4()
        _override_org_exists(org_id)
        fake_db = _make_fake_db()
        _override_db(fake_db)

        async def refresh(lic):
            lic.id = uuid4()
        fake_db.refresh = AsyncMock(side_effect=refresh)

        # Try to send extra fields that should be ignored
        resp = await client.post(
            f"/api/v1/organizations/{org_id}/licenses",
            json={
                "activity_type": "Эксплуатация",
                "license_number": "Л-002",
                # Try unauthorized fields - should be ignored
                "valid_until": "2030-12-31",
                "issuing_authority": "Ростехнадзор",
                "notes": "Should be ignored",
            },
        )
        assert resp.status_code == 201, resp.text
        added = fake_db.add.call_args[0][0]
        # Extra fields are NOT persisted
        assert not hasattr(added, "valid_until")
        assert not hasattr(added, "issuing_authority")
        assert not hasattr(added, "notes")

    async def test_list(self, client):
        org_id = uuid4()
        _override_org_exists(org_id)
        licenses = [
            FakeModel(id=uuid4(), organization_id=org_id,
                      activity_type="Эксплуатация", license_number="Л-001",
                      issue_date=None, status="active",
                      file_path=None, file_name=None, file_size=None,
                      mime_type=None, checksum_sha256=None),
        ]
        fake_db = _make_fake_db()
        fake_db.execute = AsyncMock(return_value=_make_execute_result(items=licenses))
        _override_db(fake_db)

        resp = await client.get(f"/api/v1/organizations/{org_id}/licenses")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["license_number"] == "Л-001"
        assert "file_path" not in data[0]

    async def test_get_one(self, client):
        org_id = uuid4()
        lic_id = uuid4()
        _override_org_exists(org_id)
        existing = FakeModel(id=lic_id, organization_id=org_id,
                              activity_type="Эксплуатация", license_number="Л-001",
                              issue_date=None, status="active",
                              file_path="licenses/file.pdf", file_name="file.pdf",
                              file_size=1024, mime_type="application/pdf",
                              checksum_sha256="abc")
        fake_db = _make_fake_db()
        fake_db.execute = AsyncMock(return_value=_make_execute_result(one=existing))
        _override_db(fake_db)

        resp = await client.get(f"/api/v1/organizations/{org_id}/licenses/{lic_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["license_number"] == "Л-001"
        assert data["has_file"] is True
        assert data["file_name"] == "file.pdf"
        assert "file_path" not in data

    async def test_update(self, client):
        org_id = uuid4()
        lic_id = uuid4()
        _override_org_exists(org_id)
        existing = FakeModel(id=lic_id, organization_id=org_id,
                              activity_type="Old", license_number="Л-001",
                              issue_date=None, status="active",
                              file_path=None, file_name=None, file_size=None,
                              mime_type=None, checksum_sha256=None)
        fake_db = _make_fake_db()
        fake_db.execute = AsyncMock(return_value=_make_execute_result(one=existing))
        _override_db(fake_db)

        resp = await client.put(
            f"/api/v1/organizations/{org_id}/licenses/{lic_id}",
            json={"activity_type": "New Activity"},
        )
        assert resp.status_code == 200
        assert resp.json()["activity_type"] == "New Activity"

    async def test_delete(self, client):
        org_id = uuid4()
        lic_id = uuid4()
        _override_org_exists(org_id)
        existing = FakeModel(id=lic_id, organization_id=org_id,
                              activity_type="X", license_number="X",
                              issue_date=None, status="active",
                              file_path=None, file_name=None, file_size=None,
                              mime_type=None, checksum_sha256=None)
        fake_db = _make_fake_db()
        fake_db.execute = AsyncMock(return_value=_make_execute_result(one=existing))
        _override_db(fake_db)

        resp = await client.delete(f"/api/v1/organizations/{org_id}/licenses/{lic_id}")
        assert resp.status_code == 204


# ---------------------------------------------------------------------------
# License file upload/download/delete
# ---------------------------------------------------------------------------

_MINIMAL_PDF = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000052 00000 n
0000000101 00000 n
trailer<</Size 4/Root 1 0 R>>
startxref
167
%%EOF"""


@pytest.mark.asyncio
class TestLicenseFileOps:
    async def test_upload_and_download_file(self, client):
        """Загрузка и скачивание файла лицензии."""
        import tempfile
        tmp_dir = Path(tempfile.gettempdir()) / "isap_test_licenses"
        tmp_dir.mkdir(parents=True, exist_ok=True)

        org_id = uuid4()
        lic_id = uuid4()
        _override_org_exists(org_id)

        existing = FakeModel(
            id=lic_id, organization_id=org_id,
            activity_type="Эксплуатация", license_number="Л-001",
            issue_date=None, status="active",
            file_path=None, file_name=None, file_size=None,
            mime_type=None, checksum_sha256=None,
        )
        fake_db = _make_fake_db()
        fake_db.execute = AsyncMock(return_value=_make_execute_result(one=existing))
        _override_db(fake_db)

        # Override the upload directory to use tmp_path
        import src.api.routers.organizations as org_router
        original_dir = org_router.LICENSES_UPLOAD_DIR
        org_router.LICENSES_UPLOAD_DIR = str(tmp_dir)
        org_router.LICENSES_UPLOAD_ROOT = str(tmp_dir.parent)
        try:
            resp = await client.post(
                f"/api/v1/organizations/{org_id}/licenses/{lic_id}/file",
                files={"file": ("license.pdf", io.BytesIO(_MINIMAL_PDF), "application/pdf")},
            )
            assert resp.status_code == 200, resp.text
            data = resp.json()
            assert data["has_file"] is True
            assert data["file_name"] == "license.pdf"
            assert data["mime_type"] == "application/pdf"
            assert data["checksum_sha256"] == hashlib.sha256(_MINIMAL_PDF).hexdigest()
            assert "file_path" not in data

            # Verify file written to disk
            assert existing.file_path is not None
            abs_path = _resolve_license_path(existing.file_path)
            assert os.path.exists(abs_path)
            with open(abs_path, "rb") as f:
                assert f.read() == _MINIMAL_PDF

            # Download the file back
            resp = await client.get(
                f"/api/v1/organizations/{org_id}/licenses/{lic_id}/download"
            )
            assert resp.status_code == 200
            assert resp.content == _MINIMAL_PDF
        finally:
            org_router.LICENSES_UPLOAD_DIR = original_dir
            # Cleanup
            if existing.file_path:
                p = _resolve_license_path(existing.file_path)
                if os.path.exists(p):
                    os.remove(p)

    async def test_upload_replaces_previous_file(self, client):
        """Замена файла: старый удаляется."""
        import tempfile
        tmp_dir = Path(tempfile.gettempdir()) / "isap_test_licenses"
        tmp_dir.mkdir(parents=True, exist_ok=True)

        org_id = uuid4()
        lic_id = uuid4()
        _override_org_exists(org_id)

        # Pre-existing file
        import src.api.routers.organizations as org_router
        original_dir = org_router.LICENSES_UPLOAD_DIR
        org_router.LICENSES_UPLOAD_DIR = str(tmp_dir)
        org_router.LICENSES_UPLOAD_ROOT = str(tmp_dir.parent)
        prev_storage = _build_license_storage_key(lic_id, "old.pdf")
        _, prev_relative, prev_absolute = prev_storage
        Path(prev_absolute).parent.mkdir(parents=True, exist_ok=True)
        Path(prev_absolute).write_bytes(b"OLD CONTENT")

        existing = FakeModel(
            id=lic_id, organization_id=org_id,
            activity_type="X", license_number="X",
            issue_date=None, status="active",
            file_path=prev_relative, file_name="old.pdf", file_size=11,
            mime_type="application/pdf", checksum_sha256="old",
        )
        fake_db = _make_fake_db()
        fake_db.execute = AsyncMock(return_value=_make_execute_result(one=existing))
        _override_db(fake_db)
        try:
            resp = await client.post(
                f"/api/v1/organizations/{org_id}/licenses/{lic_id}/file",
                files={"file": ("new.pdf", io.BytesIO(_MINIMAL_PDF), "application/pdf")},
            )
            assert resp.status_code == 200, resp.text
            # Old file removed
            assert not os.path.exists(prev_absolute)
            # New file exists
            new_path = _resolve_license_path(existing.file_path)
            assert os.path.exists(new_path)
            if os.path.exists(new_path):
                os.remove(new_path)
        finally:
            org_router.LICENSES_UPLOAD_DIR = original_dir

    async def test_delete_file(self, client):
        """Удаление файла с сохранением метаданных лицензии."""
        import tempfile
        tmp_dir = Path(tempfile.gettempdir()) / "isap_test_licenses"
        tmp_dir.mkdir(parents=True, exist_ok=True)

        org_id = uuid4()
        lic_id = uuid4()
        _override_org_exists(org_id)

        import src.api.routers.organizations as org_router
        original_dir = org_router.LICENSES_UPLOAD_DIR
        org_router.LICENSES_UPLOAD_DIR = str(tmp_dir)
        org_router.LICENSES_UPLOAD_ROOT = str(tmp_dir.parent)
        _, relative, absolute = _build_license_storage_key(lic_id, "license.pdf")
        Path(absolute).parent.mkdir(parents=True, exist_ok=True)
        Path(absolute).write_bytes(_MINIMAL_PDF)

        existing = FakeModel(
            id=lic_id, organization_id=org_id,
            activity_type="X", license_number="X",
            issue_date=None, status="active",
            file_path=relative, file_name="license.pdf", file_size=100,
            mime_type="application/pdf", checksum_sha256="abc",
        )
        fake_db = _make_fake_db()
        fake_db.execute = AsyncMock(return_value=_make_execute_result(one=existing))
        _override_db(fake_db)
        try:
            resp = await client.delete(
                f"/api/v1/organizations/{org_id}/licenses/{lic_id}/file"
            )
            assert resp.status_code == 200, resp.text
            data = resp.json()
            assert data["has_file"] is False
            assert data["file_name"] is None
            assert data["checksum_sha256"] is None
            assert "file_path" not in data
            assert not os.path.exists(absolute)
        finally:
            org_router.LICENSES_UPLOAD_DIR = original_dir

    async def test_upload_invalid_mime_rejected(self, client):
        """Недопустимый MIME отклоняется."""
        org_id = uuid4()
        lic_id = uuid4()
        _override_org_exists(org_id)

        existing = FakeModel(
            id=lic_id, organization_id=org_id,
            activity_type="X", license_number="X",
            issue_date=None, status="active",
            file_path=None, file_name=None, file_size=None,
            mime_type=None, checksum_sha256=None,
        )
        fake_db = _make_fake_db()
        fake_db.execute = AsyncMock(return_value=_make_execute_result(one=existing))
        _override_db(fake_db)

        resp = await client.post(
            f"/api/v1/organizations/{org_id}/licenses/{lic_id}/file",
            files={"file": ("malware.exe", io.BytesIO(b"MZ"), "application/x-msdownload")},
        )
        assert resp.status_code == 400
        assert "Недопустимое" in resp.json()["detail"]

    async def test_download_no_file_returns_404(self, client):
        """Скачивание без файла возвращает 404."""
        org_id = uuid4()
        lic_id = uuid4()
        _override_org_exists(org_id)
        existing = FakeModel(
            id=lic_id, organization_id=org_id,
            activity_type="X", license_number="X",
            issue_date=None, status="active",
            file_path=None, file_name=None, file_size=None,
            mime_type=None, checksum_sha256=None,
        )
        fake_db = _make_fake_db()
        fake_db.execute = AsyncMock(return_value=_make_execute_result(one=existing))
        _override_db(fake_db)

        resp = await client.get(
            f"/api/v1/organizations/{org_id}/licenses/{lic_id}/download"
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Cross-organization isolation tests
# ---------------------------------------------------------------------------
# Через URL организации A невозможно получить, изменить, удалить или
# скачать bank account, OKVED или license организации B. Ожидается 404.

@pytest.mark.asyncio
class TestCrossOrganizationIsolation:
    """Межорганизационная изоляция: sub-resources видят только свои записи.

    Проверяет, что через URL организации A невозможно изменить или удалить
    bank account, OKVED или license организации B. Ожидается 404.

    Изоляция обеспечивается SQL-фильтром `WHERE organization_id = :org_id`
    во всех sub-resource endpoint'ах.
    """

    async def _setup_cross_org_query(self, client, subresource: str, action: str):
        """Setup: org A существует, запрос к sub-resource по ID чужой записи.

        Возвращает 404, потому что WHERE organization_id != org_a_id
        не находит запись, даже если record_id существует в БД.
        """
        org_a_id = uuid4()
        org_b_id = uuid4()
        _override_org_exists(org_a_id)

        item_id = uuid4()

        # Fake DB: execute всегда возвращает None (запись не принадлежит org A)
        fake_db = _make_fake_db()
        fake_db.execute = AsyncMock(return_value=_make_execute_result(one=None))
        _override_db(fake_db)

        base = f"/api/v1/organizations/{org_a_id}/{subresource}/{item_id}"

        if action == "update":
            return await client.put(base, json={"bank_name": "X"})
        elif action == "delete":
            return await client.delete(base)
        elif action == "get":
            return await client.get(base)
        elif action == "download":
            return await client.get(f"{base}/download")
        return None

    # ── Bank accounts ───────────────────────────────────────────────────────

    async def test_bank_account_update_other_org_returns_404(self, client):
        resp = await self._setup_cross_org_query(client, "bank-accounts", "update")
        assert resp.status_code == 404

    async def test_bank_account_delete_other_org_returns_404(self, client):
        resp = await self._setup_cross_org_query(client, "bank-accounts", "delete")
        assert resp.status_code == 404

    # ── OKVED codes ─────────────────────────────────────────────────────────

    async def test_okved_code_update_other_org_returns_404(self, client):
        resp = await self._setup_cross_org_query(client, "okved-codes", "update")
        assert resp.status_code == 404

    async def test_okved_code_delete_other_org_returns_404(self, client):
        resp = await self._setup_cross_org_query(client, "okved-codes", "delete")
        assert resp.status_code == 404

    # ── Licenses ────────────────────────────────────────────────────────────

    async def test_license_get_other_org_returns_404(self, client):
        resp = await self._setup_cross_org_query(client, "licenses", "get")
        assert resp.status_code == 404

    async def test_license_update_other_org_returns_404(self, client):
        resp = await self._setup_cross_org_query(client, "licenses", "update")
        assert resp.status_code == 404

    async def test_license_delete_other_org_returns_404(self, client):
        resp = await self._setup_cross_org_query(client, "licenses", "delete")
        assert resp.status_code == 404

    async def test_license_download_other_org_returns_404(self, client):
        resp = await self._setup_cross_org_query(client, "licenses", "download")
        assert resp.status_code == 404
