"""Роутер организаций — CRUD операции с расширенной карточкой организации.

Связанные сущности (банковские счета, коды ОКВЭД, лицензии) управляются через
отдельные sub-resources:
    POST   /api/v1/organizations/{org_id}/bank-accounts
    GET    /api/v1/organizations/{org_id}/bank-accounts
    PUT    /api/v1/organizations/{org_id}/bank-accounts/{id}
    DELETE /api/v1/organizations/{org_id}/bank-accounts/{id}
    .../okved-codes/...
    .../licenses/...
    GET    /api/v1/organizations/{org_id}/licenses/{id}/download
    POST   /api/v1/organizations/{org_id}/licenses/{id}/file (загрузка/замена файла)
    DELETE /api/v1/organizations/{org_id}/licenses/{id}/file

Вложенные массивы не принимаются в POST/PUT organization — используйте
отдельные endpoints выше.
"""
import hashlib
import io
import os
import re
from datetime import UTC, date as date_type, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db, get_organization_repo
from src.core.settings import settings
from src.infrastructure.database.models import (
    BankAccountModel,
    LicenseModel,
    OkvedCodeModel,
    OrganizationModel,
)
from src.infrastructure.repositories.organization_repo import OrganizationRepository

router = APIRouter()


# ── Вложенные схемы ─────────────────────────────────────────────────────────

class BankAccountCreate(BaseModel):
    account_number: str
    bank_name: str | None = None
    bank_bik: str | None = None
    bank_corr_account: str | None = None
    currency: str = "RUB"
    is_primary: bool = False
    notes: str | None = None


class BankAccountUpdate(BaseModel):
    account_number: str | None = None
    bank_name: str | None = None
    bank_bik: str | None = None
    bank_corr_account: str | None = None
    currency: str | None = None
    is_primary: bool | None = None
    notes: str | None = None


class BankAccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    account_number: str
    bank_name: str | None
    bank_bik: str | None
    bank_corr_account: str | None
    currency: str
    is_primary: bool
    notes: str | None

    @field_validator("is_primary", mode="before")
    @classmethod
    def _coerce_int_bool(cls, v):
        # БД хранит SmallInteger (0/1), клиенту отдаём bool.
        return bool(v) if v is not None else False


class OkvedCodeCreate(BaseModel):
    code: str
    description: str | None = None
    is_primary: bool = False


class OkvedCodeUpdate(BaseModel):
    code: str | None = None
    description: str | None = None
    is_primary: bool | None = None


class OkvedCodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    code: str
    description: str | None
    is_primary: bool

    @field_validator("is_primary", mode="before")
    @classmethod
    def _coerce_int_bool(cls, v):
        return bool(v) if v is not None else False


# ── Лицензии: согласованные поля только ──────────────────────────────────────
# Вид деятельности, номер, дата выдачи, статус, файл.
# file_path (storage_key) НИКОГДА не возвращается клиенту.

class LicenseCreate(BaseModel):
    """Метаданные лицензии. Файл загружается отдельным запросом."""
    activity_type: str
    license_number: str
    issue_date: str | None = None
    status: str = "active"


class LicenseUpdate(BaseModel):
    activity_type: str | None = None
    license_number: str | None = None
    issue_date: str | None = None
    status: str | None = None


class LicenseResponse(BaseModel):
    """Лицензия в ответе API. Внутренний file_path скрыт."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    activity_type: str
    license_number: str
    issue_date: str | None = None
    status: str
    # Файловые метаданные (без file_path)
    file_name: str | None = None
    file_size: int | None = None
    mime_type: str | None = None
    checksum_sha256: str | None = None
    has_file: bool = False

    @field_validator("issue_date", mode="before")
    @classmethod
    def _coerce_date(cls, v):
        if v is None:
            return None
        if isinstance(v, date_type):
            return v.isoformat()
        return str(v)

    @classmethod
    def from_model(cls, lic: LicenseModel) -> "LicenseResponse":
        return cls(
            id=lic.id,
            organization_id=lic.organization_id,
            activity_type=lic.activity_type,
            license_number=lic.license_number,
            issue_date=lic.issue_date,
            status=lic.status or "active",
            file_name=lic.file_name,
            file_size=lic.file_size,
            mime_type=lic.mime_type,
            checksum_sha256=lic.checksum_sha256,
            has_file=bool(lic.file_path),
        )


# ── Основные схемы организации ───────────────────────────────────────────────
# Вложенные сущности НЕ принимаются — используйте отдельные endpoints.

class OrganizationCreate(BaseModel):
    name: str
    inn: str
    ogrn: str | None = None
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    org_type: str | None = "legal"
    full_name: str | None = None
    short_name: str | None = None
    legal_address: str | None = None
    actual_address: str | None = None
    postal_address: str | None = None
    phone_additional: str | None = None
    phone_mobile: str | None = None
    fax: str | None = None
    website: str | None = None
    kpp: str | None = None
    ogrnip: str | None = None
    okpo: str | None = None
    director_full_name: str | None = None
    director_position: str | None = None
    director_phone: str | None = None
    director_email: str | None = None
    ip_last_name: str | None = None
    ip_first_name: str | None = None
    ip_middle_name: str | None = None

    @field_validator("org_type")
    @classmethod
    def validate_org_type(cls, v: str | None) -> str | None:
        if v is not None and v not in ("legal", "individual"):
            raise ValueError("org_type должен быть 'legal' или 'individual'")
        return v


class OrganizationUpdate(BaseModel):
    name: str | None = None
    inn: str | None = None
    ogrn: str | None = None
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    org_type: str | None = None
    full_name: str | None = None
    short_name: str | None = None
    legal_address: str | None = None
    actual_address: str | None = None
    postal_address: str | None = None
    phone_additional: str | None = None
    phone_mobile: str | None = None
    fax: str | None = None
    website: str | None = None
    kpp: str | None = None
    ogrnip: str | None = None
    okpo: str | None = None
    director_full_name: str | None = None
    director_position: str | None = None
    director_phone: str | None = None
    director_email: str | None = None
    ip_last_name: str | None = None
    ip_first_name: str | None = None
    ip_middle_name: str | None = None

    @field_validator("org_type")
    @classmethod
    def validate_org_type(cls, v: str | None) -> str | None:
        if v is not None and v not in ("legal", "individual"):
            raise ValueError("org_type должен быть 'legal' или 'individual'")
        return v


class OrganizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    inn: str
    ogrn: str | None
    address: str | None
    phone: str | None
    email: str | None
    org_type: str | None
    full_name: str | None
    short_name: str | None
    legal_address: str | None
    actual_address: str | None
    postal_address: str | None
    phone_additional: str | None
    phone_mobile: str | None
    fax: str | None
    website: str | None
    kpp: str | None
    ogrnip: str | None
    okpo: str | None
    director_full_name: str | None
    director_position: str | None
    director_phone: str | None
    director_email: str | None
    ip_last_name: str | None
    ip_first_name: str | None
    ip_middle_name: str | None


class OrganizationDetailResponse(OrganizationResponse):
    """Полный ответ с вложенными таблицами."""
    bank_accounts: list[BankAccountResponse] = []
    okved_codes: list[OkvedCodeResponse] = []
    licenses: list[LicenseResponse] = []


# ── Helper: проверка организации ────────────────────────────────────────────

async def _require_org(repo: OrganizationRepository, organization_id: UUID) -> OrganizationModel:
    org = await repo.get(organization_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Организация не найдена")
    return org


# ── Endpoints: организации ────────────────────────────────────────────────────

@router.post("/", response_model=OrganizationResponse, status_code=201)
async def create_organization(
    data: OrganizationCreate,
    repo: OrganizationRepository = Depends(get_organization_repo),
):
    org = await repo.create(data.model_dump())
    return org


@router.get("/", response_model=list[OrganizationResponse])
async def list_organizations(
    skip: int = 0,
    limit: int = 100,
    repo: OrganizationRepository = Depends(get_organization_repo),
):
    orgs = await repo.get_multi(skip=skip, limit=limit)
    return orgs


@router.get("/{organization_id}", response_model=OrganizationResponse)
async def get_organization(
    organization_id: UUID,
    repo: OrganizationRepository = Depends(get_organization_repo),
):
    org = await _require_org(repo, organization_id)
    return org


@router.get("/{organization_id}/detail", response_model=OrganizationDetailResponse)
async def get_organization_detail(
    organization_id: UUID,
    repo: OrganizationRepository = Depends(get_organization_repo),
):
    """Получить организацию со всеми связанными таблицами."""
    org = await repo.get_with_related(organization_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Организация не найдена")
    return org


@router.put("/{organization_id}", response_model=OrganizationResponse)
async def update_organization(
    organization_id: UUID,
    data: OrganizationUpdate,
    repo: OrganizationRepository = Depends(get_organization_repo),
):
    await _require_org(repo, organization_id)
    update_data = data.model_dump(exclude_unset=True)
    org = await repo.update(organization_id, update_data)
    return org


@router.delete("/{organization_id}", status_code=204)
async def delete_organization(
    organization_id: UUID,
    repo: OrganizationRepository = Depends(get_organization_repo),
):
    deleted = await repo.delete(organization_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Организация не найдена")


@router.post("/import-word")
async def import_organization_from_word(file: UploadFile = File(...)):
    """Импорт реквизитов организации из Word-документа."""
    if not file.filename or not file.filename.lower().endswith('.docx'):
        raise HTTPException(status_code=400, detail="Поддерживается только формат .docx")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Размер файла не должен превышать 10 МБ")

    try:
        from docx import Document
        doc = Document(io.BytesIO(content))
        lines = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        full_text = '\n'.join(lines)
        result = {}

        name_match = re.search(r'(?:Организация|Наименование|Общество|ООО|АО|ПАО)\s*[:\s]+(.+)', full_text, re.IGNORECASE)
        if name_match:
            result['name'] = name_match.group(1).strip()
        inn_match = re.search(r'ИНН[:\s]*(\d{10,12})', full_text)
        if inn_match:
            result['inn'] = inn_match.group(1)
        ogrn_match = re.search(r'ОГРН[:\s]*(\d{13,15})', full_text)
        if ogrn_match:
            result['ogrn'] = ogrn_match.group(1)
        addr_match = re.search(r'(?:Адрес|Юридический\s+адрес|Место\s+нахождения)[:\s]+(.+)', full_text, re.IGNORECASE)
        if addr_match:
            result['address'] = addr_match.group(1).strip()
        phone_match = re.search(r'(?:Телефон|Тел\.|тел\.|контактный\s+телефон)[:\s]*([\+\d\s\-\(\)]{7,20})', full_text, re.IGNORECASE)
        if phone_match:
            result['phone'] = phone_match.group(1).strip()

        return {
            'success': bool(result),
            'data': result,
            'warnings': [] if result.get('name') else ['Не удалось извлечь наименование организации'],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка обработки документа: {e}")


# ── Bank accounts sub-resource ───────────────────────────────────────────────

@router.post("/{organization_id}/bank-accounts", response_model=BankAccountResponse, status_code=201)
async def create_bank_account(
    organization_id: UUID,
    data: BankAccountCreate,
    repo: OrganizationRepository = Depends(get_organization_repo),
    db: AsyncSession = Depends(get_db),
):
    await _require_org(repo, organization_id)
    payload = data.model_dump()
    payload["is_primary"] = 1 if payload["is_primary"] else 0
    account = BankAccountModel(organization_id=organization_id, **payload)
    db.add(account)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="У организации уже есть основной банковский счёт",
        )
    await db.refresh(account)
    return account


@router.get("/{organization_id}/bank-accounts", response_model=list[BankAccountResponse])
async def list_bank_accounts(
    organization_id: UUID,
    repo: OrganizationRepository = Depends(get_organization_repo),
    db: AsyncSession = Depends(get_db),
):
    await _require_org(repo, organization_id)
    result = await db.execute(
        select(BankAccountModel)
        .where(BankAccountModel.organization_id == organization_id)
        .order_by(BankAccountModel.is_primary.desc(), BankAccountModel.created_at)
    )
    return list(result.scalars().all())


@router.put("/{organization_id}/bank-accounts/{account_id}", response_model=BankAccountResponse)
async def update_bank_account(
    organization_id: UUID,
    account_id: UUID,
    data: BankAccountUpdate,
    repo: OrganizationRepository = Depends(get_organization_repo),
    db: AsyncSession = Depends(get_db),
):
    await _require_org(repo, organization_id)
    result = await db.execute(
        select(BankAccountModel).where(
            BankAccountModel.id == account_id,
            BankAccountModel.organization_id == organization_id,
        )
    )
    account = result.scalar_one_or_none()
    if account is None:
        raise HTTPException(status_code=404, detail="Банковский счёт не найден")
    update_data = data.model_dump(exclude_unset=True)
    if "is_primary" in update_data:
        update_data["is_primary"] = 1 if update_data["is_primary"] else 0
    for key, value in update_data.items():
        setattr(account, key, value)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="У организации уже есть основной банковский счёт",
        )
    await db.refresh(account)
    return account


@router.delete("/{organization_id}/bank-accounts/{account_id}", status_code=204)
async def delete_bank_account(
    organization_id: UUID,
    account_id: UUID,
    repo: OrganizationRepository = Depends(get_organization_repo),
    db: AsyncSession = Depends(get_db),
):
    await _require_org(repo, organization_id)
    result = await db.execute(
        select(BankAccountModel).where(
            BankAccountModel.id == account_id,
            BankAccountModel.organization_id == organization_id,
        )
    )
    account = result.scalar_one_or_none()
    if account is None:
        raise HTTPException(status_code=404, detail="Банковский счёт не найден")
    await db.delete(account)
    await db.commit()


# ── OKVED codes sub-resource ─────────────────────────────────────────────────

@router.post("/{organization_id}/okved-codes", response_model=OkvedCodeResponse, status_code=201)
async def create_okved_code(
    organization_id: UUID,
    data: OkvedCodeCreate,
    repo: OrganizationRepository = Depends(get_organization_repo),
    db: AsyncSession = Depends(get_db),
):
    await _require_org(repo, organization_id)
    payload = data.model_dump()
    payload["is_primary"] = 1 if payload["is_primary"] else 0
    code = OkvedCodeModel(organization_id=organization_id, **payload)
    db.add(code)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="У организации уже есть основной код ОКВЭД",
        )
    await db.refresh(code)
    return code


@router.get("/{organization_id}/okved-codes", response_model=list[OkvedCodeResponse])
async def list_okved_codes(
    organization_id: UUID,
    repo: OrganizationRepository = Depends(get_organization_repo),
    db: AsyncSession = Depends(get_db),
):
    await _require_org(repo, organization_id)
    result = await db.execute(
        select(OkvedCodeModel)
        .where(OkvedCodeModel.organization_id == organization_id)
        .order_by(OkvedCodeModel.is_primary.desc(), OkvedCodeModel.created_at)
    )
    return list(result.scalars().all())


@router.put("/{organization_id}/okved-codes/{code_id}", response_model=OkvedCodeResponse)
async def update_okved_code(
    organization_id: UUID,
    code_id: UUID,
    data: OkvedCodeUpdate,
    repo: OrganizationRepository = Depends(get_organization_repo),
    db: AsyncSession = Depends(get_db),
):
    await _require_org(repo, organization_id)
    result = await db.execute(
        select(OkvedCodeModel).where(
            OkvedCodeModel.id == code_id,
            OkvedCodeModel.organization_id == organization_id,
        )
    )
    code = result.scalar_one_or_none()
    if code is None:
        raise HTTPException(status_code=404, detail="Код ОКВЭД не найден")
    update_data = data.model_dump(exclude_unset=True)
    if "is_primary" in update_data:
        update_data["is_primary"] = 1 if update_data["is_primary"] else 0
    for key, value in update_data.items():
        setattr(code, key, value)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="У организации уже есть основной код ОКВЭД",
        )
    await db.refresh(code)
    return code


@router.delete("/{organization_id}/okved-codes/{code_id}", status_code=204)
async def delete_okved_code(
    organization_id: UUID,
    code_id: UUID,
    repo: OrganizationRepository = Depends(get_organization_repo),
    db: AsyncSession = Depends(get_db),
):
    await _require_org(repo, organization_id)
    result = await db.execute(
        select(OkvedCodeModel).where(
            OkvedCodeModel.id == code_id,
            OkvedCodeModel.organization_id == organization_id,
        )
    )
    code = result.scalar_one_or_none()
    if code is None:
        raise HTTPException(status_code=404, detail="Код ОКВЭД не найден")
    await db.delete(code)
    await db.commit()


# ── Licenses sub-resource ────────────────────────────────────────────────────

LICENSES_UPLOAD_DIR = os.path.normpath(os.path.join(
    os.path.dirname(__file__), "..", "..", settings.upload_root, "licenses"
))
os.makedirs(LICENSES_UPLOAD_DIR, exist_ok=True)
LICENSES_UPLOAD_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", settings.upload_root)
)
MAX_LICENSE_FILE_SIZE = settings.max_upload_file_size_mb * 1024 * 1024
ALLOWED_LICENSE_MIME_TYPES = {"application/pdf", "image/jpeg", "image/png"}
ALLOWED_LICENSE_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}


def _resolve_license_path(storage_key: str) -> str:
    """Resolve storage_key (relative path inside licenses/) and stay within upload root."""
    resolved = os.path.normpath(os.path.join(LICENSES_UPLOAD_DIR, storage_key))
    try:
        inside_root = os.path.commonpath([LICENSES_UPLOAD_DIR, resolved]) == LICENSES_UPLOAD_DIR
    except ValueError:
        inside_root = False
    if not inside_root:
        raise HTTPException(status_code=400, detail="Некорректный путь файла")
    return resolved


def _build_license_storage_key(license_id: UUID, filename: str | None) -> tuple[str, str, str]:
    """Build (safe_filename, storage_key, absolute_path).

    storage_key is a plain filename relative to LICENSES_UPLOAD_DIR
    (which already points at .../uploads/licenses). The same string is
    both the DB file_path and what _resolve_license_path joins back.
    """
    safe_filename = os.path.basename((filename or "").replace("\\", "/")).strip()
    if not safe_filename or safe_filename in {".", ".."}:
        raise HTTPException(status_code=400, detail="Некорректное имя файла")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = f"{ts}_{license_id.hex[:8]}_{safe_filename}"
    storage_key = safe_name  # relative to LICENSES_UPLOAD_DIR
    absolute_path = os.path.normpath(os.path.join(LICENSES_UPLOAD_DIR, safe_name))
    try:
        inside_dir = os.path.commonpath([LICENSES_UPLOAD_DIR, absolute_path]) == LICENSES_UPLOAD_DIR
    except ValueError:
        inside_dir = False
    if not inside_dir:
        raise HTTPException(status_code=400, detail="Некорректный путь файла")
    return safe_filename, storage_key, absolute_path


def _validate_license_file(file: UploadFile) -> None:
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_LICENSE_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Недопустимое расширение файла: {ext}. Разрешены: {', '.join(ALLOWED_LICENSE_EXTENSIONS)}",
        )
    if file.content_type and file.content_type not in ALLOWED_LICENSE_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Недопустимый MIME тип: {file.content_type}. Разрешены: PDF, JPEG, PNG",
        )


@router.post("/{organization_id}/licenses", response_model=LicenseResponse, status_code=201)
async def create_license(
    organization_id: UUID,
    data: LicenseCreate,
    repo: OrganizationRepository = Depends(get_organization_repo),
    db: AsyncSession = Depends(get_db),
):
    """Создать лицензию (только метаданные). Файл — отдельным запросом."""
    await _require_org(repo, organization_id)
    issue_date = None
    if data.issue_date:
        try:
            issue_date = date_type.fromisoformat(data.issue_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="issue_date должен быть в формате YYYY-MM-DD")
    license_obj = LicenseModel(
        organization_id=organization_id,
        activity_type=data.activity_type,
        license_number=data.license_number,
        issue_date=issue_date,
        status=data.status or "active",
    )
    db.add(license_obj)
    await db.commit()
    await db.refresh(license_obj)
    return LicenseResponse.from_model(license_obj)


@router.get("/{organization_id}/licenses", response_model=list[LicenseResponse])
async def list_licenses(
    organization_id: UUID,
    repo: OrganizationRepository = Depends(get_organization_repo),
    db: AsyncSession = Depends(get_db),
):
    await _require_org(repo, organization_id)
    result = await db.execute(
        select(LicenseModel)
        .where(LicenseModel.organization_id == organization_id)
        .order_by(LicenseModel.created_at.desc())
    )
    return [LicenseResponse.from_model(l) for l in result.scalars().all()]


@router.get("/{organization_id}/licenses/{license_id}", response_model=LicenseResponse)
async def get_license(
    organization_id: UUID,
    license_id: UUID,
    repo: OrganizationRepository = Depends(get_organization_repo),
    db: AsyncSession = Depends(get_db),
):
    await _require_org(repo, organization_id)
    result = await db.execute(
        select(LicenseModel).where(
            LicenseModel.id == license_id,
            LicenseModel.organization_id == organization_id,
        )
    )
    lic = result.scalar_one_or_none()
    if lic is None:
        raise HTTPException(status_code=404, detail="Лицензия не найдена")
    return LicenseResponse.from_model(lic)


@router.put("/{organization_id}/licenses/{license_id}", response_model=LicenseResponse)
async def update_license(
    organization_id: UUID,
    license_id: UUID,
    data: LicenseUpdate,
    repo: OrganizationRepository = Depends(get_organization_repo),
    db: AsyncSession = Depends(get_db),
):
    await _require_org(repo, organization_id)
    result = await db.execute(
        select(LicenseModel).where(
            LicenseModel.id == license_id,
            LicenseModel.organization_id == organization_id,
        )
    )
    lic = result.scalar_one_or_none()
    if lic is None:
        raise HTTPException(status_code=404, detail="Лицензия не найдена")
    update_data = data.model_dump(exclude_unset=True)
    if "issue_date" in update_data and update_data["issue_date"]:
        try:
            update_data["issue_date"] = date_type.fromisoformat(update_data["issue_date"])
        except ValueError:
            raise HTTPException(status_code=400, detail="issue_date должен быть в формате YYYY-MM-DD")
    for key, value in update_data.items():
        setattr(lic, key, value)
    await db.commit()
    await db.refresh(lic)
    return LicenseResponse.from_model(lic)


@router.delete("/{organization_id}/licenses/{license_id}", status_code=204)
async def delete_license(
    organization_id: UUID,
    license_id: UUID,
    repo: OrganizationRepository = Depends(get_organization_repo),
    db: AsyncSession = Depends(get_db),
):
    await _require_org(repo, organization_id)
    result = await db.execute(
        select(LicenseModel).where(
            LicenseModel.id == license_id,
            LicenseModel.organization_id == organization_id,
        )
    )
    lic = result.scalar_one_or_none()
    if lic is None:
        raise HTTPException(status_code=404, detail="Лицензия не найдена")
    # Remove file from disk if present
    if lic.file_path:
        resolved = _resolve_license_path(lic.file_path)
        if os.path.exists(resolved):
            try:
                os.remove(resolved)
            except OSError:
                pass
    await db.delete(lic)
    await db.commit()


@router.post("/{organization_id}/licenses/{license_id}/file", response_model=LicenseResponse)
async def upload_license_file(
    organization_id: UUID,
    license_id: UUID,
    file: UploadFile = File(...),
    repo: OrganizationRepository = Depends(get_organization_repo),
    db: AsyncSession = Depends(get_db),
):
    """Загрузить или заменить файл лицензии."""
    await _require_org(repo, organization_id)
    result = await db.execute(
        select(LicenseModel).where(
            LicenseModel.id == license_id,
            LicenseModel.organization_id == organization_id,
        )
    )
    lic = result.scalar_one_or_none()
    if lic is None:
        raise HTTPException(status_code=404, detail="Лицензия не найдена")

    _validate_license_file(file)
    content = await file.read()
    if len(content) > MAX_LICENSE_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Файл слишком большой. Максимум: {MAX_LICENSE_FILE_SIZE // (1024 * 1024)} MB",
        )
    checksum = hashlib.sha256(content).hexdigest()
    safe_filename, relative_path, absolute_path = _build_license_storage_key(license_id, file.filename)

    # Replace: remove previous file
    if lic.file_path:
        prev = _resolve_license_path(lic.file_path)
        if os.path.exists(prev):
            try:
                os.remove(prev)
            except OSError:
                pass

    try:
        with open(absolute_path, "wb") as buf:
            buf.write(content)
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Ошибка сохранения файла: {e}")

    lic.file_path = relative_path
    lic.file_name = safe_filename
    lic.file_size = os.path.getsize(absolute_path)
    lic.mime_type = file.content_type or "application/octet-stream"
    lic.checksum_sha256 = checksum
    await db.commit()
    await db.refresh(lic)
    return LicenseResponse.from_model(lic)


@router.delete("/{organization_id}/licenses/{license_id}/file", response_model=LicenseResponse)
async def delete_license_file(
    organization_id: UUID,
    license_id: UUID,
    repo: OrganizationRepository = Depends(get_organization_repo),
    db: AsyncSession = Depends(get_db),
):
    """Удалить файл лицензии (метаданные остаются)."""
    await _require_org(repo, organization_id)
    result = await db.execute(
        select(LicenseModel).where(
            LicenseModel.id == license_id,
            LicenseModel.organization_id == organization_id,
        )
    )
    lic = result.scalar_one_or_none()
    if lic is None:
        raise HTTPException(status_code=404, detail="Лицензия не найдена")
    if lic.file_path:
        resolved = _resolve_license_path(lic.file_path)
        if os.path.exists(resolved):
            try:
                os.remove(resolved)
            except OSError:
                pass
    lic.file_path = None
    lic.file_name = None
    lic.file_size = None
    lic.mime_type = None
    lic.checksum_sha256 = None
    await db.commit()
    await db.refresh(lic)
    return LicenseResponse.from_model(lic)


@router.get("/{organization_id}/licenses/{license_id}/download")
async def download_license_file(
    organization_id: UUID,
    license_id: UUID,
    repo: OrganizationRepository = Depends(get_organization_repo),
    db: AsyncSession = Depends(get_db),
):
    """Скачать файл лицензии."""
    await _require_org(repo, organization_id)
    result = await db.execute(
        select(LicenseModel).where(
            LicenseModel.id == license_id,
            LicenseModel.organization_id == organization_id,
        )
    )
    lic = result.scalar_one_or_none()
    if lic is None:
        raise HTTPException(status_code=404, detail="Лицензия не найдена")
    if not lic.file_path:
        raise HTTPException(status_code=404, detail="Файл лицензии не найден")
    resolved = _resolve_license_path(lic.file_path)
    if not os.path.exists(resolved):
        raise HTTPException(status_code=404, detail="Файл лицензии не найден на диске")
    return FileResponse(
        path=resolved,
        filename=lic.file_name or f"license_{license_id}",
        media_type=lic.mime_type or "application/octet-stream",
    )
