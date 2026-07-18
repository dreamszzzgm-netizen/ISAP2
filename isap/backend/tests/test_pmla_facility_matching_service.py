"""Unit tests for PmlaFacilityMatchingService."""

from uuid import uuid4

import pytest

from src.application.services.pmla_facility_matching_service import (
    MatchResult,
    PmlaFacilityMatchingService,
)
from src.infrastructure.repositories.facility_repo import FacilityRepository
from src.infrastructure.repositories.organization_repo import OrganizationRepository


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def org_repo():
    """Returns an OrganizationRepository with an overridden search_by_name."""
    from unittest.mock import AsyncMock

    repo = AsyncMock(spec=OrganizationRepository)

    async def _search_by_name(name: str, limit: int = 10):
        if not name or not name.strip():
            return []
        text = name.strip().lower()
        if text == "ао хлебокомбинат":
            org = AsyncMock()
            org.id = uuid4()
            org.name = "АО Хлебокомбинат"
            return [org]
        if text == "ооо газпром":
            org = AsyncMock()
            org.id = uuid4()
            org.name = 'ООО "Газпром"'
            return [org]
        if text == "ооо рога и копыта":
            # Multiple organisations with same name
            org1 = AsyncMock()
            org1.id = uuid4()
            org1.name = "ООО Рога и Копыта"
            org2 = AsyncMock()
            org2.id = uuid4()
            org2.name = "ООО Рога и Копыта"
            return [org1, org2]
        return []

    repo.search_by_name.side_effect = _search_by_name
    return repo


@pytest.fixture
def fac_repo():
    """Returns a FacilityRepository with overridden search methods."""
    from unittest.mock import AsyncMock

    repo = AsyncMock(spec=FacilityRepository)

    _facilities = {}
    _by_reg = {}

    def _make_fac(**kw):
        f = AsyncMock()
        f.id = kw.get("id", uuid4())
        f.name = kw.get("name", "Тестовое ОПО")
        f.reg_number = kw.get("reg_number", "А01-00001-0001")
        f.organization_id = kw.get("organization_id", uuid4())
        f.address = kw.get("address", "г. Тест, ул. Тестовая, 1")
        return f

    fac_a = _make_fac(
        name="Сеть газопотребления Хлебозавода №2",
        reg_number="А01-0001-0005",
    )
    fac_b = _make_fac(
        name="Сеть газопотребления Хлебозавода №3",
        reg_number="А01-0001-0006",
    )
    fac_c = _make_fac(name="Нефтебаза", reg_number="В00-00001-0001")

    async def _search_by_reg_number(reg_number: str, limit: int = 10):
        if not reg_number or not reg_number.strip():
            return []
        rn = reg_number.strip().lower()
        if "а01-0001-0005" in rn:
            return [fac_a]
        if "а01-0001-0006" in rn:
            return [fac_b]
        if "shared" in rn:
            # Multiple facilities with similar reg_number
            return [fac_a, fac_b]
        if "unknown" in rn:
            return []
        return []

    async def _search_by_name(name: str, organization_id=None, limit: int = 10):
        if not name or not name.strip():
            return []
        text = name.strip().lower()
        if "газопотребления" in text:
            if organization_id:
                if organization_id == fac_a.organization_id:
                    return [fac_a]
                if organization_id == fac_b.organization_id:
                    return [fac_b]
            return [fac_a, fac_b]
        if "нефтебаза" in text:
            return [fac_c]
        return []

    async def _search_by_name_and_address(name: str, address: str, limit: int = 5):
        if not name or not name.strip():
            return []
        text = name.strip().lower()
        if "газопотребления" in text:
            return [fac_a, fac_b]
        if "нефтебаза" in text:
            return [fac_c]
        return []

    repo.search_by_reg_number.side_effect = _search_by_reg_number
    repo.search_by_name.side_effect = _search_by_name
    repo.search_by_name_and_address.side_effect = _search_by_name_and_address
    return repo


@pytest.fixture
def matching_service(org_repo, fac_repo):
    return PmlaFacilityMatchingService(org_repo, fac_repo)


# ---------------------------------------------------------------------------
# Test 1: Exact registration number → 1 match
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_exact_reg_number_one_result(matching_service):
    results = await matching_service.find_facility_candidates(
        name="", reg_number="А01-0001-0005"
    )
    assert len(results) == 1
    assert results[0].match_reason == "registration_number"
    assert results[0].confidence == 1.0


# ---------------------------------------------------------------------------
# Test 2: Registration number → multiple results, no auto-bind
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reg_number_multiple_results_no_autobind(org_repo, fac_repo):
    """When >1 facility matches reg_number, auto-binding must be skipped."""
    service = PmlaFacilityMatchingService(org_repo, fac_repo)
    resolution = await service.resolve_auto_binding(
        {"name": "АО Хлебокомбинат"},
        {"name": "Сеть газопотребления", "reg_number": "shared"},
    )
    assert resolution.auto_bind_skipped is True
    assert resolution.facility_id is None
    assert resolution.binding_method == "none"
    assert resolution.requires_binding is True


# ---------------------------------------------------------------------------
# Test 3: Exact organisation name
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_exact_organisation_name(matching_service):
    results = await matching_service.find_organization_candidates(
        "АО Хлебокомбинат"
    )
    assert len(results) == 1
    assert results[0].match_reason == "exact_name"
    assert results[0].confidence == 0.9


# ---------------------------------------------------------------------------
# Test 4: Name + address facility match
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_facility_name_and_address(matching_service):
    results = await matching_service.find_facility_candidates(
        name="Сеть газопотребления Хлебозавода №2"
    )
    # Should find via registration_number first
    assert len(results) >= 1


# ---------------------------------------------------------------------------
# Test 5: No candidates
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_candidates(matching_service):
    orgs = await matching_service.find_organization_candidates(
        "Несуществующая организация ООО"
    )
    assert orgs == []

    facs = await matching_service.find_facility_candidates(
        name="Несуществующий объект",
        reg_number="unknown-12345",
    )
    assert facs == []


# ---------------------------------------------------------------------------
# Test 6: Case and whitespace normalisation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_case_and_whitespace_normalisation(matching_service):
    orgs = await matching_service.find_organization_candidates(
        "  ао хлебокомбинат  "
    )
    assert len(orgs) == 1
    assert orgs[0].name == "АО Хлебокомбинат"

    facs = await matching_service.find_facility_candidates(
        name="",
        reg_number="  а01-0001-0005  ",
    )
    assert len(facs) >= 1


# ---------------------------------------------------------------------------
# Test 7: Empty values produce no false matches
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_values_no_false_matches(matching_service):
    orgs = await matching_service.find_organization_candidates("")
    assert orgs == []

    orgs = await matching_service.find_organization_candidates("   ")
    assert orgs == []

    facs = await matching_service.find_facility_candidates(name="", reg_number=None)
    assert facs == []


# ---------------------------------------------------------------------------
# Additional: Auto-binding via unique reg_number
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_auto_bind_via_unique_reg_number(org_repo, fac_repo):
    """Unique registration number should auto-bind."""
    service = PmlaFacilityMatchingService(org_repo, fac_repo)
    resolution = await service.resolve_auto_binding(
        {"name": "АО Хлебоккомбинат"},
        {"name": "Сеть газопотребления Хлебозавода №2", "reg_number": "А01-0001-0005"},
    )
    assert resolution.facility_id is not None
    assert resolution.organization_id is not None
    assert resolution.binding_method == "exact_registration_number"
    assert resolution.requires_binding is False


# ---------------------------------------------------------------------------
# Additional: Auto-binding skipped when no reg_number
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_auto_bind_skipped_when_no_reg_number(org_repo, fac_repo):
    """Without registration number, auto-binding must not happen."""
    service = PmlaFacilityMatchingService(org_repo, fac_repo)
    resolution = await service.resolve_auto_binding(
        {"name": "АО Хлебокомбинат"},
        {"name": "Неизвестный объект", "reg_number": ""},
    )
    assert resolution.facility_id is None
    assert resolution.auto_bind_skipped is False
    assert resolution.requires_binding is True
