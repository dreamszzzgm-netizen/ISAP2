"""PMLA RAG Adapter — read-only retrieval for generated sections.

Provides structured context from a knowledge retrieval system (or in-memory
fallback) to enrich generated PMLA sections with relevant reference material.

This is a READ-ONLY adapter — it never modifies the retrieval source.
It returns structured chunks that generation engines can use as context.

Only applies to generated_block sections — static/variable/TOC/appendix
blocks are NOT affected by RAG.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class PmlaRagChunk:
    """A single retrieval chunk from the RAG system."""
    source_id: str
    source_title: str
    section_hint: str | None = None
    text: str = ""
    score: float | None = None


@dataclass
class PmlaRagContext:
    """Structured RAG context for a specific generated section."""
    chunks: list[PmlaRagChunk] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return len(self.chunks) == 0

    @property
    def summary(self) -> str:
        """Concatenated text from all chunks, for injection into prompts."""
        return "\n\n".join(c.text for c in self.chunks if c.text)


# ---------------------------------------------------------------------------
# In-memory RAG fallback — facility-type-specific reference material
# ---------------------------------------------------------------------------

_RAG_FALLBACK: dict[str, dict[str, list[dict]]] = {
    "сеть газопотребления": {
        "section_2": [
            {
                "source_id": "rag_gas_scenarios",
                "source_title": "Типичные аварии на сетях газопотребления",
                "text": (
                    "Основные сценарии аварий на сетях газопотребления: "
                    "разгерметизация газопровода вследствие коррозии, "
                    "отказ запорной арматуры, "
                    "неконтролируемое повышение давления из-за отказа регулятора, "
                    "образование взрывоопасной газовоздушной смеси в замкнутых помещениях."
                ),
            },
            {
                "source_id": "rag_gas_probability",
                "source_title": "Вероятность аварий на ГРПШ",
                "text": (
                    "Наиболее вероятные аварии на газорегуляторных пунктах: "
                    "отказ ПЗК/ПСК, заедание клапана, разгерметизация соединений. "
                    "Вероятность — средняя для объектов с опытом эксплуатации более 10 лет."
                ),
            },
        ],
        "section_5": [
            {
                "source_id": "rag_gas_interaction",
                "source_title": "Порядок взаимодействия при авариях на газе",
                "text": (
                    "При аварии на газопроводе необходимо: "
                    "1) перекрыть подачу газа до аварийного участка; "
                    "2) провентилировать загазованную зону; "
                    "3) вызвать аварийную газовую службу; "
                    "4) организовать встречу прибывающих служб у КПП."
                ),
            },
        ],
        "section_7": [
            {
                "source_id": "rag_gas_readiness",
                "source_title": "Готовность сил к ликвидации аварий на газе",
                "text": (
                    "Готовность сил и средств обеспечивается: "
                    "ежедневным дежурством оперативного персонала, "
                    "наличием газоанализаторов и средств связи, "
                    "проведением учебных тренировок не реже 1 раза в полугодие, "
                    "содержанием первичных средств пожаротушения в исправном состоянии."
                ),
            },
        ],
        "section_10": [
            {
                "source_id": "rag_gas_actions",
                "source_title": "Первоочередные действия при утечке газа",
                "text": (
                    "При обнаружении запаха газа: "
                    "1) немедленно сообщить диспетчеру; "
                    "2) не допускать открытого огня и искрообразования; "
                    "3) перекрыть газ на ближайшем вентиле; "
                    "4) проветрить помещение; "
                    "5) вывести людей из опасной зоны; "
                    "6) вызвать аварийную газовую службу."
                ),
            },
        ],
        "section_12": [
            {
                "source_id": "rag_gas_population",
                "source_title": "Безопасность населения при авариях на газе",
                "text": (
                    "При утечке газа на открытой территории: "
                    "организовать эвакуацию населения из зоны поражения (радиус определяется расчётом), "
                    "запретить использование открытого огня, "
                    "обеспечить оповещение через систему громкоговорящей связи."
                ),
            },
        ],
        "special_section": [
            {
                "source_id": "rag_gas_special",
                "source_title": "Оперативные действия при аварии на ГРПШ",
                "text": (
                    "При отказе регулятора давления: "
                    "1) проверить срабатывание ПЗК; "
                    "2) если ПЗК не сработал — перекрыть выходной кран; "
                    "3) при необходимости перекрыть входной кран; "
                    "4) вызвать газовую службу для ремонта; "
                    "5) после устранения — контрольная опрессовка."
                ),
            },
        ],
    },
    "котельная": {
        "section_2": [
            {
                "source_id": "rag_boiler_scenarios",
                "source_title": "Типичные аварии на котельных",
                "text": (
                    "Основные сценарии аварий на котельных: "
                    "взрыв котла из-за понижения уровня воды, "
                    "отказ системы автоматики безопасности, "
                    "пожар в топливоподаче, "
                    "утечка газа на газовом вводе."
                ),
            },
        ],
        "section_10": [
            {
                "source_id": "rag_boiler_actions",
                "source_title": "Первоочередные действия при аварии на котельной",
                "text": (
                    "При срабатывании сигнализации: "
                    "1) проверить показания приборов; "
                    "2) при аварийном сигнале — отключить котёл по аварийной защите; "
                    "3) при пожаре — вызвать пожарную охрану; "
                    "4) эвакуировать персонал из опасной зоны."
                ),
            },
        ],
    },
    "агзс": {
        "section_2": [
            {
                "source_id": "rag_agzs_scenarios",
                "source_title": "Типичные аварии на АГЗС",
                "text": (
                    "Основные сценарии аварий на АГЗС: "
                    "разгерметизация резервуара СУГ, "
                    "утечка СУГ при сливе из автоцистерны, "
                    "пожар в зоне заправочной колонки, "
                    "образование газовоздушного облака."
                ),
            },
        ],
        "section_5": [
            {
                "source_id": "rag_agzs_interaction",
                "source_title": "Взаимодействие служб при аварии на АГЗС",
                "text": (
                    "При аварии на АГЗС необходимо: "
                    "1) прекратить заправку/слив СУГ; "
                    "2) остановить насосное оборудование; "
                    "3) перекрыть запорную арматуру; "
                    "4) вызвать пожарную охрану и аварийную газовую службу; "
                    "5) организовать встречу служб у КПП."
                ),
            },
        ],
        "section_10": [
            {
                "source_id": "rag_agzs_actions",
                "source_title": "Первоочередные действия при аварии на АГЗС",
                "text": (
                    "При обнаружении утечки СУГ: "
                    "1) немедленно прекратить заправку/слив; "
                    "2) остановить насосное оборудование; "
                    "3) перекрыть запорную арматуру; "
                    "4) вывести людей из опасной зоны; "
                    "5) вызвать аварийные службы; "
                    "6) организовать оцепление."
                ),
            },
        ],
        "section_12": [
            {
                "source_id": "rag_agzs_population",
                "source_title": "Безопасность населения при аварии на АГЗС",
                "text": (
                    "При утечке СУГ на АГЗС: "
                    "организовать эвакуацию населения из зоны поражения, "
                    "запретить использование открытого огня, "
                    "обеспечить оповещение через систему громкоговорящей связи."
                ),
            },
        ],
        "special_section": [
            {
                "source_id": "rag_agzs_special",
                "source_title": "Оперативные действия при аварии на АГЗС",
                "text": (
                    "При утечке СУГ: "
                    "1) прекратить все операции с СУГ; "
                    "2) перекрыть арматуру на резервуаре; "
                    "3) провентилировать зону утечки; "
                    "4) вызвать аварийную газовую службу; "
                    "5) после ликвидации — контрольная проверка герметичности."
                ),
            },
        ],
    },
}

# Default fallback for unknown facility types
_DEFAULT_RAG: dict[str, list[dict]] = {
    "section_10": [
        {
            "source_id": "rag_default_actions",
            "source_title": "Первоочередные действия при аварии",
            "text": (
                "При обнаружении аварии: "
                "1) немедленно сообщить руководителю; "
                "2) прекратить работы в опасной зоне; "
                "3) вывести персонал; "
                "4) вызвать аварийные службы; "
                "5) организовать оцепление."
            ),
        },
    ],
}


def _match_facility_type(facility_type: str) -> str | None:
    """Find matching RAG fallback key for a facility type string.

    Uses longest-match-first to avoid short substrings claiming inputs.
    """
    lower = facility_type.lower().strip()
    for key in sorted(_RAG_FALLBACK, key=len, reverse=True):
        if key in lower:
            return key
    return None


class PmlaRagAdapter:
    """Read-only RAG adapter for PMLA generated sections.

    Currently uses an in-memory knowledge base. In the future, this can be
    swapped for a real vector DB (Chroma, Qdrant, etc.) without changing
    the caller interface.
    """

    def get_context(
        self,
        facility_context: dict,
        section_id: str,
    ) -> PmlaRagContext:
        """Get RAG context for a specific generated section.

        Args:
            facility_context: Dict with at least 'facility_type' key.
            section_id: The section being generated (e.g., 'section_2').

        Returns:
            PmlaRagContext with relevant chunks, or empty context with warnings.
        """
        warnings: list[str] = []
        # Support both top-level facility_type and nested facility.facility_type
        raw = facility_context.get("facility_type")
        if raw is None:
            facility_dict = facility_context.get("facility", {})
            if isinstance(facility_dict, dict):
                raw = facility_dict.get("facility_type")
        facility_type = str(raw).strip() if raw else ""

        if not facility_type:
            warnings.append("Тип ОПО не указан — RAG контекст пуст")
            return PmlaRagContext(warnings=warnings)

        matched_key = _match_facility_type(facility_type)
        if matched_key is None:
            warnings.append(
                f"Тип ОПО '{facility_type}' не найден в RAG базе — "
                f"используется контекст по умолчанию"
            )
            # Try default RAG
            default_chunks = _DEFAULT_RAG.get(section_id, [])
            chunks = [
                PmlaRagChunk(**c) for c in default_chunks
            ]
            return PmlaRagContext(chunks=chunks, warnings=warnings)

        facility_rag = _RAG_FALLBACK.get(matched_key, {})
        section_chunks = facility_rag.get(section_id, [])

        if not section_chunks:
            warnings.append(
                f"RAG контекст для '{section_id}' не найден для типа '{matched_key}'"
            )

        chunks = [PmlaRagChunk(**c) for c in section_chunks]

        # Cross-facility filter: remove chunks with mismatched facility hints
        from src.application.services.cross_facility_guardrails import check_cross_facility_contamination
        filtered = []
        for chunk in chunks:
            contaminants = check_cross_facility_contamination(chunk.text, facility_type)
            if not contaminants:
                filtered.append(chunk)
            else:
                warnings.append(
                    f"RAG chunk '{chunk.source_title}' содержит термины "
                    f"другого типа ОПО: {', '.join(contaminants)} — отфильтрован"
                )

        return PmlaRagContext(chunks=filtered, warnings=warnings)
