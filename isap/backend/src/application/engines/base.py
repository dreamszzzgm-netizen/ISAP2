"""Базовые типы для движков генерации ПМЛА."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from src.application.engines.blocks import (
    Block,
    HeadingBlock,
    ImageBlock,
    ParagraphBlock,
    TableBlock,
)


@dataclass
class SectionContent:
    """Результат генерации одного раздела документа."""
    section_id: str
    title: str
    engine_name: str
    blocks: list[Block] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    # Старое поле content — для обратной совместимости с немигрированными движками.
    # Если блоки пусты, _build_docx() использует _content_str.
    _content_str: str = ""

    def __init__(
        self,
        section_id: str,
        title: str,
        engine_name: str,
        blocks: list[Block] | None = None,
        metadata: dict[str, Any] | None = None,
        content: str = "",
    ):
        self.section_id = section_id
        self.title = title
        self.engine_name = engine_name
        self.blocks = blocks if blocks is not None else []
        self.metadata = metadata if metadata is not None else {}
        self._content_str = content

    @property
    def content(self) -> str:
        """Fallback: блоки → текст, для кода, который ещё не мигрировал."""
        if self.blocks:
            return self._blocks_to_text()
        return self._content_str

    def _blocks_to_text(self) -> str:
        """Конвертация блоков в плоский текст (fallback)."""
        lines = []
        for b in self.blocks:
            if isinstance(b, HeadingBlock):
                lines.append(b.text.upper())
            elif isinstance(b, ParagraphBlock):
                lines.append(b.text)
            elif isinstance(b, TableBlock):
                if b.caption:
                    lines.append(b.caption)
                lines.append(" | ".join(b.headers))
                for row in b.rows:
                    lines.append(" | ".join(row))
            elif isinstance(b, ImageBlock):
                lines.append(f"[изображение: {b.path}]")
            lines.append("")
        return "\n".join(lines)


@dataclass
class DocumentContext:
    """
    Единый контекст документа, передаваемый между движками.
    Все данные — dict или list[dict], чтобы не зависеть от ORM-моделей.
    """
    organization: dict[str, Any]
    facility: dict[str, Any]
    equipment: list[dict[str, Any]]
    substances: list[dict[str, Any]]
    persons: list[dict[str, Any]]
    calculation_results: list[dict[str, Any]] = field(default_factory=list)
    scenarios: list[dict[str, Any]] = field(default_factory=list)
    regulatory: list[dict[str, Any]] = field(default_factory=list)
    year: int = 2026

    # Обогащённые данные (заполняются перед генерацией)
    approver: dict[str, str] = field(default_factory=lambda: {"name": "—", "position": "—"})
    personnel: list[dict[str, str]] = field(default_factory=list)
    facility_coords: dict[str, Any] = field(default_factory=lambda: {"latitude": None, "longitude": None})
    material_reserve: dict[str, Any] = field(default_factory=dict)
    emergency_services: list[dict[str, Any]] = field(default_factory=list)
    selected_scenarios: list[Any] = field(default_factory=list)
    custom_scenarios: list[dict[str, Any]] = field(default_factory=list)
    user_scenarios: list[dict[str, Any]] = field(default_factory=list)
    protective_equipment: list[dict[str, Any]] = field(default_factory=list)
    organization_resources: dict[str, Any] = field(default_factory=dict)
    notification_scheme: dict[str, Any] = field(default_factory=dict)
    incident_history: dict[str, Any] = field(default_factory=dict)
    insurance: dict[str, Any] = field(default_factory=dict)
    accident_samples: list[dict[str, Any]] | None = None  # Примеры аварий (None → hardcoded)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DocumentContext:
        """Создание из словаря (из API-запроса)."""
        return cls(
            organization=data.get("organization", {}),
            facility=data.get("facility", {}),
            equipment=data.get("equipment", []),
            substances=data.get("substances", []),
            persons=data.get("responsible_persons", []),
            calculation_results=data.get("calculation_results", []),
            scenarios=data.get("scenarios", []),
            regulatory=data.get("regulatory", []),
            year=data.get("year", 2026),
            approver=data.get("approver", {"name": "—", "position": "—"}),
            personnel=data.get("personnel", []),
            facility_coords=data.get("facility_coords", {"latitude": None, "longitude": None}),
            material_reserve=data.get("material_reserve", {}),
            emergency_services=data.get("emergency_services", []),
            selected_scenarios=data.get("selected_scenarios", []),
            custom_scenarios=data.get("custom_scenarios", []),
            user_scenarios=data.get("user_scenarios", []),
            protective_equipment=data.get("protective_equipment", []),
            organization_resources=data.get("organization_resources", {}),
            notification_scheme=data.get("notification_scheme", {}),
            incident_history=data.get("incident_history", {}),
            insurance=data.get("insurance", {}),
        )

    def to_dict(self) -> dict[str, Any]:
        """Конвертация в словарь для совместимости с Jinja2-шаблонами."""
        return {
            "organization": self.organization,
            "facility": self.facility,
            "equipment": self.equipment,
            "substances": self.substances,
            "responsible_persons": self.persons,
            "calculation_results": self.calculation_results,
            "scenarios": self.scenarios,
            "regulatory": self.regulatory,
            "year": self.year,
            "approver": self.approver,
            "personnel": self.personnel,
            "facility_coords": self.facility_coords,
            "material_reserve": self.material_reserve,
            "emergency_services": self.emergency_services,
            "selected_scenarios": self.selected_scenarios,
            "custom_scenarios": self.custom_scenarios,
            "user_scenarios": self.user_scenarios,
            "protective_equipment": self.protective_equipment,
            "organization_resources": self.organization_resources,
            "notification_scheme": self.notification_scheme,
            "incident_history": self.incident_history,
            "insurance": self.insurance,
        }


class BaseEngine(ABC):
    """
    Абстрактный базовый класс для движков генерации.
    Каждый движок обрабатывает определённый набор разделов.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Уникальное имя движка (например, 'template', 'data', 'scenario')."""

    @abstractmethod
    def can_handle(self, section_id: str) -> bool:
        """Проверяет, может ли этот движок обработать указанный раздел."""

    @abstractmethod
    async def generate(self, section_id: str, section_def: dict, context: DocumentContext) -> SectionContent:
        """Генерирует содержимое раздела."""
