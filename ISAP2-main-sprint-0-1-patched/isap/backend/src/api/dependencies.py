from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.engine import async_session_factory
from src.infrastructure.repositories import (
    DocumentRepository,
    EquipmentRepository,
    FacilityRepository,
    OrganizationRepository,
    PersonRepository,
    PmlaSampleRepository,
    RegulatoryRepository,
    ScenarioMatrixRepository,
    SubstanceRepository,
)
from src.infrastructure.repositories.opo_details_repo import OpoDetailsRepository


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session


def get_organization_repo(db: AsyncSession = Depends(get_db)) -> OrganizationRepository:
    return OrganizationRepository(db)


def get_facility_repo(db: AsyncSession = Depends(get_db)) -> FacilityRepository:
    return FacilityRepository(db)


def get_equipment_repo(db: AsyncSession = Depends(get_db)) -> EquipmentRepository:
    return EquipmentRepository(db)


def get_substance_repo(db: AsyncSession = Depends(get_db)) -> SubstanceRepository:
    return SubstanceRepository(db)


def get_person_repo(db: AsyncSession = Depends(get_db)) -> PersonRepository:
    return PersonRepository(db)


def get_document_repo(db: AsyncSession = Depends(get_db)) -> DocumentRepository:
    return DocumentRepository(db)


def get_regulatory_repo(db: AsyncSession = Depends(get_db)) -> RegulatoryRepository:
    return RegulatoryRepository(db)


def get_pmla_sample_repo(db: AsyncSession = Depends(get_db)) -> PmlaSampleRepository:
    return PmlaSampleRepository(db)


def get_scenario_matrix_repo(db: AsyncSession = Depends(get_db)) -> ScenarioMatrixRepository:
    return ScenarioMatrixRepository(db)


def get_opo_details_repo(db: AsyncSession = Depends(get_db)) -> OpoDetailsRepository:
    return OpoDetailsRepository(db)
