"""Интеграция EngineRouter с EnhancedDocumentGenerator."""
from __future__ import annotations

import logging

from src.application.engines.base import DocumentContext
from src.application.engines.data_engine import DataEngine
from src.application.engines.narrative_engine import NarrativeEngine
from src.application.engines.rules_engine import RulesEngine
from src.application.engines.router import EngineRouter
from src.application.engines.scenario_engine import ScenarioEngine
from src.application.engines.template_engine import TemplateEngine

logger = logging.getLogger(__name__)


def create_engine_router(
    llm_provider=None,
    retriever=None,
) -> EngineRouter:
    """
    Создаёт EngineRouter со всеми 6 движками.

    Args:
        llm_provider: LLM-провайдер для NarrativeEngine (если None — fallback)
        retriever: RAG-ретривер (пока не используется движками)

    Returns:
        Настроенный EngineRouter
    """
    return EngineRouter([
        TemplateEngine(),
        DataEngine(),
        ScenarioEngine(),
        RulesEngine(),
        NarrativeEngine(llm_provider=llm_provider, retriever=retriever),
    ])


def build_document_context(
    raw_context: dict,
    calculation_results: list[dict] | None = None,
    scenarios: list[dict] | None = None,
) -> DocumentContext:
    """
    Конвертирует raw dict из API в DocumentContext для движков.

    Args:
        raw_context: Словарь из API-запроса (с ключами organization, facility, equipment и т.д.)
        calculation_results: Результаты расчётов (взрыв, тепло, токсика)
        scenarios: Сценарии из матрицы

    Returns:
        DocumentContext
    """
    from datetime import datetime

    facility = raw_context.get("facility", {})
    organization = raw_context.get("organization", {})
    persons = raw_context.get("responsible_persons", [])

    # Approver (для титульного листа)
    approver = {"name": "—", "position": "—"}
    if persons:
        p = persons[0] if isinstance(persons[0], dict) else {
            "full_name": getattr(persons[0], "full_name", "—"),
            "position": getattr(persons[0], "position", "—"),
        }
        if isinstance(p, dict):
            approver = {
                "name": p.get("full_name", "—"),
                "position": p.get("position", "—"),
            }

    # Personnel (для разделов 11)
    personnel = []
    for p in persons:
        if isinstance(p, dict):
            personnel.append(p)
        else:
            personnel.append({
                "full_name": getattr(p, "full_name", "—"),
                "position": getattr(p, "position", "—"),
                "role": getattr(p, "role", "—"),
                "phone": getattr(p, "phone", "—"),
            })

    return DocumentContext(
        organization=organization,
        facility=facility,
        equipment=raw_context.get("equipment", []),
        substances=raw_context.get("substances", []),
        persons=persons,
        calculation_results=calculation_results or [],
        scenarios=scenarios or [],
        year=datetime.now().year,
        approver=approver,
        personnel=personnel,
        facility_coords={
            "latitude": facility.get("latitude"),
            "longitude": facility.get("longitude"),
        },
        material_reserve=raw_context.get("material_reserve", {}),
        emergency_services=raw_context.get("emergency_services", []),
    )
