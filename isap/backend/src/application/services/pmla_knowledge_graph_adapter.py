"""Knowledge Graph Read Adapter for PMLA.

Provides structured context from a knowledge graph (or in-memory fallback)
to enrich PMLA generation with facility-type-specific data.

This is a READ-ONLY adapter — it never modifies the graph or generates content.
It returns structured hints that quality review and generation engines can use.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class PmlaKnowledgeGraphContext:
    """Structured context from the knowledge graph for PMLA generation.

    All fields are optional — empty lists/None mean "no data available".
    The adapter never raises; it returns a safe empty context on failure.
    """
    facility_type: str | None = None
    equipment_types: list[str] = field(default_factory=list)
    hazards: list[str] = field(default_factory=list)
    recommended_scenarios: list[str] = field(default_factory=list)
    required_services: list[str] = field(default_factory=list)
    required_appendices: list[str] = field(default_factory=list)
    applicable_regulations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not any([
            self.facility_type,
            self.equipment_types,
            self.hazards,
            self.recommended_scenarios,
            self.required_services,
            self.required_appendices,
            self.applicable_regulations,
        ])


# ---------------------------------------------------------------------------
# In-memory knowledge base — facility-type-specific data
# ---------------------------------------------------------------------------

_KNOWLEDGE_BASE: dict[str, dict] = {
    "сеть газопотребления": {
        "equipment_types": [
            "газопровод",
            "газорегуляторный пункт (ШРП/ГРПШ)",
            "запорная арматура",
            "сигнализатор загазованности",
            "предохранительные клапаны (ПЗК/ПСК)",
        ],
        "hazards": [
            "утечка природного газа",
            "образование взрывоопасной газовоздушной смеси",
            "пожар / возгорание газа",
            "взрыв газовоздушной смеси",
            "отравление / удушье газом",
            "повышение давления выше нормативного",
        ],
        "recommended_scenarios": [
            "разгерметизация участка газопровода",
            "отказ регулятора давления с повышением выходного давления",
            "утечка газа в районе ГРПШ/ШРП",
            "воспламенение газовоздушной смеси",
            "взрыв газовоздушной смеси на открытой площадке",
            "взрыв газовоздушной смеси в замкнутом объеме (шкаф ГРПШ)",
            "отказ запорной арматуры при техническом обслуживании",
        ],
        "required_services": [
            "пожарная охрана",
            "скорая медицинская помощь",
            "аварийная газовая служба",
            "ПАСФ / АСФ",
        ],
        "required_appendices": [
            "схема расположения ОПО",
            "схема оповещения",
            "перечень сил и средств",
            "документы ПАСФ",
            "сведения о страховании",
        ],
        "applicable_regulations": [
            "ГОСТ Р 22.10.03-2020",
            "Приказ Ростехнадзора №472 от 11.12.2020",
            "Приказ Ростехнадзора №443 от 04.11.2020",
            "ФЗ-116 «О промышленной безопасности»",
            "Постановление Правительства РФ №1437 от 15.09.2020",
        ],
    },
    "котельная": {
        "equipment_types": [
            "котёл",
            "горелка",
            "насос циркуляционный",
            "трубопроводы",
            "арматура запорная и регулирующая",
            "система автоматики безопасности (САБ)",
        ],
        "hazards": [
            "взрыв котла",
            "пожар",
            "отказ САБ",
            "понижение уровня воды",
            "повышение давления",
            "утечка газа (при газовом топливе)",
        ],
        "recommended_scenarios": [
            "отказ САБ с повышением температуры/давления",
            "понижение уровня воды ниже предельного",
            "взрыв газовоздушной смеси в топке",
            "пожар в топливоподаче",
            "утечка газа на газовом вводе",
        ],
        "required_services": [
            "пожарная охрана",
            "скорая медицинская помощь",
        ],
        "required_appendices": [
            "схема расположения ОПО",
            "схема оповещения",
            "перечень сил и средств",
        ],
        "applicable_regulations": [
            "ГОСТ Р 22.10.03-2020",
            "Приказ Ростехнадзора №472 от 11.12.2020",
            "ФЗ-116 «О промышленной безопасности»",
        ],
    },
    "компрессорная станция": {
        "equipment_types": [
            "компрессор",
            "промежуточные охладители",
            "сепаратор",
            "газопроводы",
            "запорная арматура",
        ],
        "hazards": [
            "взрыв компрессора",
            "пожар",
            "разгерметизация нагнетательного трубопровода",
            "отказ системы безопасности",
        ],
        "recommended_scenarios": [
            "разгерметизация нагнетательного трубопровода",
            "отказ системы безопасности компрессора",
            "пожар в компрессорном зале",
        ],
        "required_services": [
            "пожарная охрана",
            "скорая медицинская помощь",
        ],
        "required_appendices": [
            "схема расположения ОПО",
            "схема оповещения",
        ],
        "applicable_regulations": [
            "ГОСТ Р 22.10.03-2020",
            "Приказ Ростехнадзора №472 от 11.12.2020",
            "ФЗ-116 «О промышленной безопасности»",
        ],
    },
    "азс": {
        "equipment_types": [
            "tml (топливораздаточная колонка)",
            "танк-хранилище",
            "насосная группа",
            "система слива/налива",
            "противопожарный заслон",
        ],
        "hazards": [
            "утечка нефтепродуктов",
            "пожар",
            "взрыв паров нефтепродуктов",
            "загрязнение почвы/воды",
        ],
        "recommended_scenarios": [
            "утечка нефтепродуктов из танка",
            "пожар на топливораздаточной колонке",
            "взрыв паров бензина в зоне налива",
        ],
        "required_services": [
            "пожарная охрана",
            "скорая медицинская помощь",
        ],
        "required_appendices": [
            "схема расположения ОПО",
            "схема оповещения",
        ],
        "applicable_regulations": [
            "ГОСТ Р 22.10.03-2020",
            "Приказ Ростехнадзора №472 от 11.12.2020",
            "ФЗ-116 «О промышленной безопасности»",
        ],
    },
}

# Default fallback for unknown facility types
_DEFAULT_CONTEXT = {
    "equipment_types": [],
    "hazards": [],
    "recommended_scenarios": [],
    "required_services": [
        "пожарная охрана",
        "скорая медицинская помощь",
    ],
    "required_appendices": [
        "схема расположения ОПО",
        "схема оповещения",
    ],
    "applicable_regulations": [
        "ФЗ-116 «О промышленной безопасности»",
    ],
}


def _match_facility_type(facility_type: str) -> str | None:
    """Find matching knowledge base key for a facility type string."""
    lower = facility_type.lower().strip()
    for key in _KNOWLEDGE_BASE:
        if key in lower or lower in key:
            return key
    return None


class PmlaKnowledgeGraphAdapter:
    """Read-only adapter for knowledge graph context.

    Currently uses an in-memory knowledge base. In the future, this can be
    swapped for a real graph database (Neo4j, Neptune, etc.) without changing
    the caller interface.
    """

    def get_context(self, facility_context: dict) -> PmlaKnowledgeGraphContext:
        """Get structured knowledge graph context for PMLA generation.

        Args:
            facility_context: Dict with at least 'facility_type' key.

        Returns:
            PmlaKnowledgeGraphContext with available data, or empty context
            with warnings if data is insufficient.
        """
        warnings: list[str] = []
        raw = facility_context.get("facility_type")
        facility_type = str(raw).strip() if raw else ""

        if not facility_type:
            warnings.append("Тип ОПО не указан — контекст графа знаний пуст")
            return PmlaKnowledgeGraphContext(warnings=warnings)

        matched_key = _match_facility_type(facility_type)
        if matched_key is None:
            warnings.append(
                f"Тип ОПО '{facility_type}' не найден в базе знаний — "
                f"используется контекст по умолчанию"
            )
            data = _DEFAULT_CONTEXT
        else:
            data = _KNOWLEDGE_BASE[matched_key]

        return PmlaKnowledgeGraphContext(
            facility_type=matched_key or facility_type,
            equipment_types=data.get("equipment_types", []),
            hazards=data.get("hazards", []),
            recommended_scenarios=data.get("recommended_scenarios", []),
            required_services=data.get("required_services", []),
            required_appendices=data.get("required_appendices", []),
            applicable_regulations=data.get("applicable_regulations", []),
            warnings=warnings,
        )
