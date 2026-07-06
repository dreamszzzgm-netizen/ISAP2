"""Роутер организаций — CRUD операции."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
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
