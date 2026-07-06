"""Роутер ответственных лиц — CRUD операции."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict

from src.api.dependencies import get_person_repo
from src.infrastructure.repositories.person_repo import PersonRepository

router = APIRouter()


class PersonCreate(BaseModel):
    organization_id: UUID
    full_name: str
    position: str | None = None
    role: str | None = None
    phone: str | None = None
    email: str | None = None


class PersonUpdate(BaseModel):
    full_name: str | None = None
    position: str | None = None
    role: str | None = None
    phone: str | None = None
    email: str | None = None


class PersonResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    full_name: str
    position: str | None
    role: str | None
    phone: str | None
    email: str | None


@router.post("/", response_model=PersonResponse, status_code=201)
async def create_person(
    data: PersonCreate,
    repo: PersonRepository = Depends(get_person_repo),
):
    return await repo.create(data.model_dump())


@router.get("/", response_model=list[PersonResponse])
async def list_persons(
    organization_id: UUID | None = None,
    skip: int = 0,
    limit: int = 100,
    repo: PersonRepository = Depends(get_person_repo),
):
    filters = {}
    if organization_id:
        filters["organization_id"] = organization_id
    return await repo.get_multi(skip=skip, limit=limit, filters=filters)


@router.get("/{person_id}", response_model=PersonResponse)
async def get_person(
    person_id: UUID,
    repo: PersonRepository = Depends(get_person_repo),
):
    person = await repo.get(person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Лицо не найдено")
    return person


@router.put("/{person_id}", response_model=PersonResponse)
async def update_person(
    person_id: UUID,
    data: PersonUpdate,
    repo: PersonRepository = Depends(get_person_repo),
):
    person = await repo.update(person_id, data.model_dump(exclude_unset=True))
    if person is None:
        raise HTTPException(status_code=404, detail="Лицо не найдено")
    return person


@router.delete("/{person_id}", status_code=204)
async def delete_person(
    person_id: UUID,
    repo: PersonRepository = Depends(get_person_repo),
):
    if not await repo.delete(person_id):
        raise HTTPException(status_code=404, detail="Лицо не найдено")
