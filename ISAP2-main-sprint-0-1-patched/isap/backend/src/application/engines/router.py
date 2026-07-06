"""EngineRouter — маршрутизатор разделов по движкам."""
from __future__ import annotations

import json
import logging
from pathlib import Path

from src.application.engines.base import BaseEngine, DocumentContext, SectionContent
from src.application.engines.blocks import ParagraphBlock

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent.parent.parent.parent / "templates"


class EngineRouter:
    """
    Маршрутизатор: определяет, какой движок должен обработать каждый раздел,
    и запускает генерацию.

    Порядок движков важен: первый, который can_handle() → True, берёт раздел.
    """

    def __init__(self, engines: list[BaseEngine]):
        self._engines = engines

    def load_structure(self, document_type: str = "pmla") -> dict:
        """Загружает structure.json с определениями разделов."""
        structure_path = TEMPLATES_DIR / document_type / "structure.json"
        if not structure_path.exists():
            raise ValueError(f"Шаблон не найден: {document_type}")
        return json.loads(structure_path.read_text(encoding="utf-8"))

    def find_engine(self, section_id: str) -> BaseEngine | None:
        """Находит движок для указанного раздела."""
        for engine in self._engines:
            if engine.can_handle(section_id):
                return engine
        return None

    async def generate_section(self, section_id: str, section_def: dict, context: DocumentContext) -> SectionContent:
        """Генерирует один раздел, определяя нужный движок."""
        engine = self.find_engine(section_id)
        if engine is None:
            logger.warning("No engine found for section '%s', using fallback", section_id)
            return SectionContent(
                section_id=section_id,
                title=section_def.get("title", section_id),
                engine_name="none",
                blocks=[ParagraphBlock(text=f"[Движок не найден для раздела {section_id}]")],
            )
        return await engine.generate(section_id, section_def, context)

    async def generate_all(self, context: DocumentContext) -> dict[str, SectionContent]:
        """
        Генерирует все разделы документа.
        Возвращает {section_id: SectionContent}.
        """
        structure = self.load_structure("pmla")
        results: dict[str, SectionContent] = {}

        for section_def in structure["sections"]:
            section_id = section_def["id"]
            result = await self.generate_section(section_id, section_def, context)
            results[section_id] = result

        return results

    def get_engine_report(self) -> dict[str, list[str]]:
        """
        Возвращает отчёт: какой движок обрабатывает какие разделы.
        Полезно для отладки и валидации.
        """
        structure = self.load_structure("pmla")
        report: dict[str, list[str]] = {}

        for engine in self._engines:
            report[engine.name] = []

        report["unhandled"] = []

        for section_def in structure["sections"]:
            section_id = section_def["id"]
            engine = self.find_engine(section_id)
            if engine:
                report[engine.name].append(section_id)
            else:
                report["unhandled"].append(section_id)

        return report
