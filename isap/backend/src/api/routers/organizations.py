"""Роутер организаций — CRUD операции."""
import re
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, ConfigDict

from src.api.dependencies import get_organization_repo
from src.infrastructure.repositories.organization_repo import OrganizationRepository

router = APIRouter()


class OrganizationCreate(BaseModel):
    name: str
    inn: str
    ogrn: str | None = None
    address: str | None = None
    phone: str | None = None
    email: str | None = None


class OrganizationUpdate(BaseModel):
    name: str | None = None
    inn: str | None = None
    ogrn: str | None = None
    address: str | None = None
    phone: str | None = None
    email: str | None = None


class OrganizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    inn: str
    ogrn: str | None
    address: str | None
    phone: str | None
    email: str | None


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
    org = await repo.get(organization_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Организация не найдена")
    return org


@router.put("/{organization_id}", response_model=OrganizationResponse)
async def update_organization(
    organization_id: UUID,
    data: OrganizationUpdate,
    repo: OrganizationRepository = Depends(get_organization_repo),
):
    update_data = data.model_dump(exclude_unset=True)
    org = await repo.update(organization_id, update_data)
    if org is None:
        raise HTTPException(status_code=404, detail="Организация не найдена")
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
        import io

        doc = Document(io.BytesIO(content))
        lines = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        full_text = '\n'.join(lines)

        # Извлекаем реквизиты
        result = {}

        # Наименование организации
        name_match = re.search(
            r'(?:Организация|Наименование|Общество|ООО|АО|ПАО)\s*[:\s]+(.+)',
            full_text,
            re.IGNORECASE
        )
        if name_match:
            result['name'] = name_match.group(1).strip()

        # ИНН
        inn_match = re.search(r'ИНН[:\s]*(\d{10,12})', full_text)
        if inn_match:
            result['inn'] = inn_match.group(1)

        # ОГРН
        ogrn_match = re.search(r'ОГРН[:\s]*(\d{13,15})', full_text)
        if ogrn_match:
            result['ogrn'] = ogrn_match.group(1)

        # Адрес
        addr_match = re.search(
            r'(?:Адрес|Юридический\s+адрес|Место\s+нахождения)[:\s]+(.+)',
            full_text,
            re.IGNORECASE
        )
        if addr_match:
            result['address'] = addr_match.group(1).strip()

        # Телефон
        phone_match = re.search(
            r'(?:Телефон|Тел\.|тел\.|контактный\s+телефон)[:\s]*([\+\d\s\-\(\)]{7,20})',
            full_text,
            re.IGNORECASE
        )
        if phone_match:
            result['phone'] = phone_match.group(1).strip()

        return {
            'success': bool(result),
            'data': result,
            'warnings': [] if result.get('name') else ['Не удалось извлечь наименование организации'],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка обработки документа: {e}")
