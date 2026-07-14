"""PmlaFacilityMatchingService — candidate search and binding resolution for PMLA import.

This service bridges the gap between the ``organization_candidate`` /
``facility_candidate`` dicts produced by ``PmlaImportNormalizer`` and the
real ``OrganizationModel`` / ``HazardousFacilityModel`` records in the database.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from src.infrastructure.repositories.facility_repo import FacilityRepository
from src.infrastructure.repositories.organization_repo import OrganizationRepository

# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class MatchResult:
    """A single candidate match found in the database.

    Attributes:
        id: UUID of the matched record.
        name: Human-readable name.
        match_reason: How the match was made (registration_number, exact_name, …).
        confidence: Fixed confidence score for the rule (1.0, 0.9, 0.7, …).
    """
    id: str
    name: str
    match_reason: str  # "registration_number" | "exact_name" | "name_and_address"
    confidence: float  # 1.0 | 0.9 | 0.7


@dataclass
class BindingResolution:
    """Result of resolving organisation / facility binding.

    Attributes:
        organization_id: Resolved organisation UUID (or None).
        facility_id: Resolved facility UUID (or None).
        binding_method: How the binding was determined:
            "explicit" — user-provided IDs,
            "exact_registration_number" — auto-resolved via unique reg_number,
            "none" — no binding could be determined.
        requires_binding: True when both IDs are still None.
        auto_bind_skipped: True when auto-binding was attempted but skipped
            due to ambiguity (>1 match or no match).
        warnings: Human-readable warnings.
    """
    organization_id: UUID | None = None
    facility_id: UUID | None = None
    binding_method: str = "none"
    requires_binding: bool = True
    auto_bind_skipped: bool = False
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Public service
# ---------------------------------------------------------------------------


class PmlaFacilityMatchingService:
    """Search for matching organisations and facilities, and resolve binding."""

    def __init__(
        self,
        org_repo: OrganizationRepository,
        fac_repo: FacilityRepository,
    ) -> None:
        self._org_repo = org_repo
        self._fac_repo = fac_repo

    # --- Organisation candidates ------------------------------------------

    async def find_organization_candidates(
        self,
        name: str,
    ) -> list[MatchResult]:
        """Find organisation candidates by name (ILIKE).

        Returns a ranked list of matches.  Confidence is based on the matching
        rule; only exact-name hints are produced here.
        """
        if not name or not name.strip():
            return []
        models = await self._org_repo.search_by_name(name)
        return [
            MatchResult(
                id=str(m.id),
                name=m.name,
                match_reason="exact_name",
                confidence=0.9,
            )
            for m in models
        ]

    # --- Facility candidates ----------------------------------------------

    async def find_facility_candidates(
        self,
        name: str,
        reg_number: str | None = None,
        organization_id: UUID | None = None,
    ) -> list[MatchResult]:
        """Find facility candidates, prioritising registration number.

        Priority order:
        1. Registration number match (confidence 1.0)
        2. Name + address match (confidence 0.9)
        3. Name match within organisation (confidence 0.9)
        4. Plain name match (confidence 0.7)
        """
        results: list[MatchResult] = []
        seen_ids: set[str] = set()

        # 1. Registration number (highest priority)
        if reg_number:
            models = await self._fac_repo.search_by_reg_number(reg_number)
            for m in models:
                mid = str(m.id)
                if mid not in seen_ids:
                    seen_ids.add(mid)
                    results.append(
                        MatchResult(
                            id=mid,
                            name=m.name,
                            match_reason="registration_number",
                            confidence=1.0,
                        )
                    )

        # 2. Name + address
        if name:
            models = await self._fac_repo.search_by_name_and_address(
                name, name  # reuse name as address hint
            )
            for m in models:
                mid = str(m.id)
                if mid not in seen_ids:
                    seen_ids.add(mid)
                    results.append(
                        MatchResult(
                            id=mid,
                            name=m.name,
                            match_reason="name_and_address",
                            confidence=0.9,
                        )
                    )

        # 3. Name within organisation
        if name and organization_id:
            models = await self._fac_repo.search_by_name(
                name, organization_id=organization_id
            )
            for m in models:
                mid = str(m.id)
                if mid not in seen_ids:
                    seen_ids.add(mid)
                    results.append(
                        MatchResult(
                            id=mid,
                            name=m.name,
                            match_reason="organization_and_name",
                            confidence=0.9,
                        )
                    )

        # 4. Plain name
        if name:
            models = await self._fac_repo.search_by_name(name)
            for m in models:
                mid = str(m.id)
                if mid not in seen_ids:
                    seen_ids.add(mid)
                    results.append(
                        MatchResult(
                            id=mid,
                            name=m.name,
                            match_reason="facility_name",
                            confidence=0.7,
                        )
                    )

        return results

    # --- Auto-binding resolution ------------------------------------------

    async def resolve_auto_binding(
        self,
        org_candidate: dict[str, Any],
        fac_candidate: dict[str, Any],
    ) -> BindingResolution:
        """Attempt to auto-bind when there is exactly one unambiguous match.

        Rules:
        * Registration number exists and matches exactly one facility → auto-bind.
        * Everything else → return candidates but do NOT auto-bind.
        """
        warnings: list[str] = []
        org_id: UUID | None = None
        fac_id: UUID | None = None
        binding_method = "none"
        auto_bind_skipped = False

        # --- Try facility matching first ---
        fac_name = fac_candidate.get("name", "")
        fac_reg = fac_candidate.get("reg_number")

        if fac_reg:
            matches = await self._fac_repo.search_by_reg_number(fac_reg)
            if len(matches) == 1:
                fac_id = matches[0].id
                org_id = matches[0].organization_id
                binding_method = "exact_registration_number"
                warnings.append(
                    f"ОПО автоматически привязан по рег. номеру: {matches[0].name}"
                )
            elif len(matches) > 1:
                auto_bind_skipped = True
                warnings.append(
                    f"Найдено {len(matches)} ОПО с рег. номером «{fac_reg}» — "
                    f"автопривязка не выполнена."
                )
            else:
                # No facility match - need manual binding.
                pass
        else:
            warnings.append(
                "Регистрационный номер ОПО не указан — автопривязка невозможна."
            )

        # If facility wasn't auto-bound, try organisation
        if fac_id is None:
            org_name = org_candidate.get("name", "")
            if org_name:
                org_matches = await self._org_repo.search_by_name(org_name)
                if len(org_matches) == 1:
                    # Store organisation but NOT facility (still need manual binding)
                    org_id = org_matches[0].id
                    warnings.append(
                        f"Организация найдена: {org_matches[0].name}, "
                        f"но ОПО не определён — требуется ручная привязка."
                    )
                elif len(org_matches) > 1:
                    auto_bind_skipped = True
                    warnings.append(
                        f"Найдено {len(org_matches)} организаций с названием "
                        f"«{org_name}» — требуется ручной выбор."
                    )
                else:
                    warnings.append(
                        f"Организация «{org_name}» не найдена в системе."
                    )

        requires_binding = org_id is None or fac_id is None

        return BindingResolution(
            organization_id=org_id,
            facility_id=fac_id,
            binding_method=binding_method,
            requires_binding=requires_binding,
            auto_bind_skipped=auto_bind_skipped,
            warnings=warnings,
        )
