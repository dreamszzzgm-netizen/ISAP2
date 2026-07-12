"""Regulatory coverage matrix for PP1437 (PMLA v2).

Checks the v2 mapping context against requirements of
Постановление Правительства РФ №1437 от 15.09.2020,
пункт 11 (Требования к содержанию ПМЛА).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Literal


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class RequirementStatus:
    """Status of a single regulatory requirement check."""
    id: str
    description: str
    status: Literal["COVERED", "PARTIAL", "MISSING", "NOT_APPLICABLE"]
    context_keys: list[str]
    missing_keys: list[str] = field(default_factory=list)
    justification: str | None = None  # mandatory for NOT_APPLICABLE


@dataclass
class RegulatoryCoverageResult:
    """Aggregated result of a regulatory coverage check."""
    requirements: list[RequirementStatus]
    total: int
    covered: int
    partial: int
    missing: int
    not_applicable: int
    passed: bool  # True if no MISSING for required=True requirements


# ---------------------------------------------------------------------------
# Requirement definition type
# ---------------------------------------------------------------------------


class RegulatoryRequirement:
    """Descriptor for a single regulatory requirement."""

    def __init__(
        self,
        id: str,
        description: str,
        context_key: str,
        section: str,
        required: bool = True,
        check: Callable[[dict], tuple[Literal["COVERED", "PARTIAL", "MISSING", "NOT_APPLICABLE"], list[str]]] | None = None,
        not_applicable_if: Callable[[dict], bool] | None = None,
        not_applicable_justification: str | None = None,
    ):
        self.id = id
        self.description = description
        self.context_keys = [k.strip() for k in context_key.split(",") if k.strip()]
        self.section = section
        self.required = required
        self._check = check
        self._not_applicable_if = not_applicable_if
        self._not_applicable_justification = not_applicable_justification

    def evaluate(self, ctx: dict) -> RequirementStatus:
        """Evaluate this requirement against the given context."""
        # Check if NOT_APPLICABLE
        if self._not_applicable_if is not None and self._not_applicable_if(ctx):
            return RequirementStatus(
                id=self.id,
                description=self.description,
                status="NOT_APPLICABLE",
                context_keys=self.context_keys,
                missing_keys=[],
                justification=self._not_applicable_justification,
            )

        # Use custom check if provided
        if self._check is not None:
            status, missing = self._check(ctx)
            return RequirementStatus(
                id=self.id,
                description=self.description,
                status=status,
                context_keys=self.context_keys,
                missing_keys=missing,
            )

        # Default logic: check presence of all context_keys
        present = [k for k in self.context_keys if ctx.get(k)]
        missing = [k for k in self.context_keys if not ctx.get(k)]

        if len(missing) == 0:
            status: Literal["COVERED", "PARTIAL", "MISSING"] = "COVERED"
        elif len(present) > 0:
            status = "PARTIAL"
        else:
            status = "MISSING"

        return RequirementStatus(
            id=self.id,
            description=self.description,
            status=status,
            context_keys=self.context_keys,
            missing_keys=missing,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _check_missing(ctx: dict, keys: list[str]) -> tuple[Literal["COVERED", "PARTIAL", "MISSING"], list[str]]:
    """Check that all given keys are present and truthy in context."""
    missing = [k for k in keys if not ctx.get(k)]
    if len(missing) == 0:
        return "COVERED", []
    present = [k for k in keys if ctx.get(k)]
    if len(present) > 0:
        return "PARTIAL", missing
    return "MISSING", missing


def _check_any_nonempty_list(ctx: dict, list_keys: list[str]) -> tuple[Literal["COVERED", "PARTIAL", "MISSING"], list[str]]:
    """Check that at least one of the given keys is a non-empty list."""
    missing = [k for k in list_keys if not isinstance(ctx.get(k), list) or len(ctx.get(k)) == 0]
    if len(missing) < len(list_keys):
        return "COVERED", missing if missing else []
    return "MISSING", missing

# ---------------------------------------------------------------------------
# Regulatory requirements matrix (paragraph 11 of PP RF No.1437)
# ---------------------------------------------------------------------------

REGULATORY_REQUIREMENTS: list[RegulatoryRequirement] = [

    # --- a) Characteristic of the facility ---
    RegulatoryRequirement(
        id="PP1437-11-a",
        description="Характеристика объекта: наименование, класс опасности, место нахождения, регистрационный номер",
        context_key="facility_name, hazard_class, facility_location, facility_reg_number",
        section="Раздел 1 — Общие сведения об организации и ОПО",
        required=True,
        check=lambda ctx: _check_missing(ctx, ["facility_name", "hazard_class", "facility_location", "facility_reg_number"]),
    ),

    # --- b) Accident scenarios ---
    RegulatoryRequirement(
        id="PP1437-11-b",
        description="Сценарии аварий: перечень возможных сценариев, источники, зоны поражающих факторов",
        context_key="accident_scenarios",
        section="Раздел 2 — Анализ опасностей и сценарии аварий",
        required=True,
        check=lambda ctx: _check_any_nonempty_list(ctx, ["accident_scenarios"]),
    ),

    # --- c) Forces and means ---
    RegulatoryRequirement(
        id="PP1437-11-c",
        description="Достаточность сил и средств для локализации и ликвидации аварий",
        context_key="material_reserve, countermeasures",
        section="Раздел 4 — Силы и средства для локализации и ликвидации",
        required=True,
        check=lambda ctx: _check_any_nonempty_list(ctx, ["material_reserve", "countermeasures"]),
    ),

    # --- d) Interaction with PASF and emergency services ---
    RegulatoryRequirement(
        id="PP1437-11-d",
        description="Взаимодействие сил и средств: порядок взаимодействия с ПАСФ, экстренными службами",
        context_key="contractor_organization_name, notification_pasf_phone, notification_fire_phone, notification_ambulance_phone, notification_edds_phone",
        section="Раздел 5 — Взаимодействие с ПАСФ и экстренными службами",
        required=True,
        check=lambda ctx: _check_missing(ctx, ["contractor_organization_name", "notification_pasf_phone", "notification_fire_phone", "notification_ambulance_phone"]),
    ),

    # --- e) Composition and dislocation of forces ---
    RegulatoryRequirement(
        id="PP1437-11-e",
        description="Состав и дислокация сил и средств: перечень и расположение",
        context_key="dislocation_address, material_reserve, equipment_list",
        section="Раздел 4 — Силы и средства",
        required=True,
        check=lambda ctx: _check_missing(ctx, ["dislocation_address"]),
    ),

    # --- f) Permanent readiness ---
    RegulatoryRequirement(
        id="PP1437-11-f",
        description="Постоянная готовность: порядок обеспечения готовности сил и средств",
        context_key="contractor_organization_name, contractor_agreement_date",
        section="Раздел 6 — Обеспечение готовности",
        required=True,
        check=lambda ctx: _check_missing(ctx, ["contractor_organization_name"]),
    ),

    # --- g) Management, communication, notification ---
    RegulatoryRequirement(
        id="PP1437-11-g",
        description="Управление, связь, оповещение: организация при аварии",
        context_key="notification_chairman_phone, notification_deputy_phone, notification_edds_phone, notification_fire_phone, notification_ambulance_phone, notification_gas_phone, notification_electric_phone",
        section="Раздел 7 — Управление, связь и оповещение",
        required=True,
        check=lambda ctx: _check_missing(ctx, ["notification_chairman_phone", "notification_edds_phone", "notification_fire_phone"]),
    ),

    # --- h) Mutual information exchange ---
    RegulatoryRequirement(
        id="PP1437-11-h",
        description="Взаимный обмен информацией между организациями-участниками",
        context_key="notification_edds_phone, notification_pasf_phone, notification_mchs_phone, notification_rostechnadzor_phone, notification_admin_phone",
        section="Раздел 7 — Управление, связь и оповещение",
        required=True,
        check=lambda ctx: _check_missing(ctx, ["notification_edds_phone", "notification_pasf_phone"]),
    ),

    # --- i) Priority actions at accident signal ---
    RegulatoryRequirement(
        id="PP1437-11-i",
        description="Первоочередные действия при сигнале об аварии",
        context_key="accident_scenarios, countermeasures",
        section="Раздел 8 — Действия по локализации и ликвидации",
        required=True,
        check=lambda ctx: _check_any_nonempty_list(ctx, ["accident_scenarios", "countermeasures"]),
    ),

    # --- j) Actions of personnel and ASF ---
    RegulatoryRequirement(
        id="PP1437-11-j",
        description="Действия персонала и АСФ по локализации и ликвидации аварий",
        context_key="countermeasures, material_reserve",
        section="Раздел 8 — Действия по локализации и ликвидации",
        required=True,
        check=lambda ctx: _check_any_nonempty_list(ctx, ["countermeasures", "material_reserve"]),
    ),

    # --- k) Public safety ---
    RegulatoryRequirement(
        id="PP1437-11-k",
        description="Безопасность населения: мероприятия по защите населения и территорий",
        context_key="settlement_name, settlement_district, local_admin, edds_name",
        section="Раздел 9 — Защита населения и территорий",
        required=True,
        check=lambda ctx: _check_missing(ctx, ["settlement_name", "edds_name"]),
    ),

    # --- l) Material, technical, engineering, financial support ---
    RegulatoryRequirement(
        id="PP1437-11-l",
        description="Материально-техническое, инженерное и финансовое обеспечение",
        context_key="material_reserve",
        section="Раздел 10 — Обеспечение",
        required=True,
        check=lambda ctx: _check_any_nonempty_list(ctx, ["material_reserve"]),
    ),

    # --- General section ---
    RegulatoryRequirement(
        id="PP1437-11-general",
        description="Общий раздел ПМЛА: охватывает все сценарии и системы ОПО в целом",
        context_key="organization_full_name, facility_name, main_activity_description, director_position_fullname",
        section="Общий раздел",
        required=True,
        check=lambda ctx: _check_missing(ctx, ["organization_full_name", "facility_name", "main_activity_description"]),
    ),

    # --- Special section ---
    RegulatoryRequirement(
        id="PP1437-11-special",
        description="Специальный раздел: по наиболее опасным сценариям аварий",
        context_key="accident_scenarios, equipment_scenario_links",
        section="Специальный раздел",
        required=True,
        check=lambda ctx: _check_any_nonempty_list(ctx, ["accident_scenarios"]),
        not_applicable_if=lambda ctx: str(ctx.get("hazard_class", "")) in ("IV", ""),
        not_applicable_justification="Для ОПО IV класса опасности специальный раздел может не разрабатываться (п. 8 ПП РФ N1437).",
    ),
]


# ---------------------------------------------------------------------------
# Check function
# ---------------------------------------------------------------------------


def check_regulatory_coverage(ctx: dict) -> RegulatoryCoverageResult:
    """
    Check v2 context for coverage of PP RF No.1437 requirements.

    Parameters
    ----------
    ctx : dict
        Flat v2 context dict as produced by ``map_to_v2_context()``.

    Returns
    -------
    RegulatoryCoverageResult
        Aggregated result with per-requirement status.
    """
    results: list[RequirementStatus] = []

    for req in REGULATORY_REQUIREMENTS:
        result = req.evaluate(ctx)
        results.append(result)

    covered = sum(1 for r in results if r.status == "COVERED")
    partial = sum(1 for r in results if r.status == "PARTIAL")
    missing = sum(1 for r in results if r.status == "MISSING")
    not_applicable = sum(1 for r in results if r.status == "NOT_APPLICABLE")

    # passed = no MISSING requirements
    required_missing = [r for r in results if r.status == "MISSING"]
    passed = len(required_missing) == 0

    return RegulatoryCoverageResult(
        requirements=results,
        total=len(results),
        covered=covered,
        partial=partial,
        missing=missing,
        not_applicable=not_applicable,
        passed=passed,
    )
