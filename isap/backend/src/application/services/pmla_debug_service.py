"""PMLA generation debug service.

The debug pipeline is intentionally database-independent. It allows developers
and domain experts to isolate generation quality issues before touching UI,
auth, RBAC or customer data.
"""
from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.application.engines.blocks import serialize_blocks
from src.application.services.engine_integration import build_document_context, create_engine_router
from src.application.services.enhanced_generator import EnhancedDocumentGenerator
from src.application.services.pmla_debug_sample import get_gas_consumption_bakery_context

DEBUG_ARTIFACTS_DIR = Path(tempfile.gettempdir()) / "isap_pmla_debug"
REQUIRED_CONTEXT_KEYS = [
    "organization",
    "facility",
    "equipment",
    "substances",
    "responsible_persons",
]


@dataclass(frozen=True)
class PmlaDebugPackage:
    package_id: str
    artifact_dir: str
    context_path: str
    rendered_sections_path: str
    validation_report_path: str
    docx_path: str
    section_count: int
    engine_report: dict[str, list[str]]
    quality: dict[str, Any]


class PmlaDebugService:
    """Runs deterministic PMLA generation diagnostics."""

    def __init__(self, artifacts_dir: Path = DEBUG_ARTIFACTS_DIR) -> None:
        self.artifacts_dir = artifacts_dir

    def reference_context(self) -> dict:
        return get_gas_consumption_bakery_context()

    def validate_context(self, context: dict) -> dict:
        issues: list[dict[str, str]] = []
        for key in REQUIRED_CONTEXT_KEYS:
            if key not in context or not context.get(key):
                issues.append({"severity": "error", "field": key, "message": "Обязательный блок отсутствует"})

        facility = context.get("facility", {})
        if not facility.get("name"):
            issues.append({"severity": "error", "field": "facility.name", "message": "Не указано наименование ОПО"})
        if not facility.get("facility_type") and not facility.get("object_type"):
            issues.append({"severity": "error", "field": "facility.facility_type", "message": "Не указан тип ОПО"})
        if not facility.get("hazard_class"):
            issues.append({"severity": "error", "field": "facility.hazard_class", "message": "Не указан класс опасности"})

        if not context.get("substances"):
            issues.append({"severity": "error", "field": "substances", "message": "Не указаны опасные вещества"})
        if not context.get("equipment"):
            issues.append({"severity": "error", "field": "equipment", "message": "Не указано оборудование"})

        persons = context.get("responsible_persons", [])
        for idx, person in enumerate(persons):
            if not person.get("phone"):
                issues.append({"severity": "warning", "field": f"responsible_persons[{idx}].phone", "message": "Не указан телефон ответственного лица"})

        return {
            "passed": not any(issue["severity"] == "error" for issue in issues),
            "issue_count": len(issues),
            "issues": issues,
        }

    async def generate_test_package(self, context: dict | None = None) -> PmlaDebugPackage:
        """Generate deterministic sections and DOCX without DB writes."""
        context = context or self.reference_context()
        context_validation = self.validate_context(context)

        engine_router = create_engine_router(llm_provider=None, retriever=None)
        structure = engine_router.load_structure("pmla")
        doc_context = build_document_context(raw_context=context, calculation_results=[], scenarios=[])

        sections: dict[str, Any] = {}
        section_meta: list[dict[str, str]] = []
        for section_def in structure["sections"]:
            section_id = section_def["id"]
            result = await engine_router.generate_section(section_id, section_def, doc_context)
            title = section_def.get("title", result.title)
            sections[title] = result.blocks if result.blocks else result.content
            section_meta.append({
                "section_id": section_id,
                "title": title,
                "engine": result.engine_name,
            })

        metadata = {
            "version": "debug",
            "generated_at": datetime.now(UTC).replace(tzinfo=None).isoformat(),
            "status": "debug_generated",
            "prompt_version": "debug-no-llm",
            "template_version": "debug",
            "calculation_results": [],
            "validation_issues": [],
        }
        generator = EnhancedDocumentGenerator(
            local_llm=None,
            external_llm=None,
            retriever=None,
            document_repo=None,
            regulatory_repo=None,
        )
        docx_bytes = generator._build_docx(structure["title"], sections, metadata)

        quality = self._quality_report(context, sections, context_validation)
        package_id = datetime.now(UTC).strftime("%Y%m%d-%H%M%S") + "-" + uuid4().hex[:8]
        package_dir = self.artifacts_dir / package_id
        package_dir.mkdir(parents=True, exist_ok=True)

        context_path = package_dir / "context.json"
        rendered_path = package_dir / "rendered_sections.json"
        validation_path = package_dir / "validation_report.json"
        docx_path = package_dir / "output.docx"

        self._write_json(context_path, context)
        self._write_json(rendered_path, {
            "sections": self._serialize_sections_for_json(sections),
            "section_meta": section_meta,
        })
        self._write_json(validation_path, quality)
        docx_path.write_bytes(docx_bytes)

        return PmlaDebugPackage(
            package_id=package_id,
            artifact_dir=str(package_dir),
            context_path=str(context_path),
            rendered_sections_path=str(rendered_path),
            validation_report_path=str(validation_path),
            docx_path=str(docx_path),
            section_count=len(sections),
            engine_report=engine_router.get_engine_report(),
            quality=quality,
        )

    def _quality_report(self, context: dict, sections: dict[str, Any], context_validation: dict) -> dict:
        text_by_section = {title: self._section_to_text(value) for title, value in sections.items()}
        all_text = "\n".join(text_by_section.values()).lower()
        required_phrases = [
            "сеть газопотребления",
            "природный газ",
            "метан",
            "пасф",
            "пожар",
            "скор",
        ]
        missing_phrases = [phrase for phrase in required_phrases if phrase not in all_text]
        placeholder_markers = ["[данные не предоставлены]", "[движок не найден", "[раздел"]
        placeholders_found = [marker for marker in placeholder_markers if marker in all_text]

        non_empty_sections = [title for title, text in text_by_section.items() if text.strip()]
        short_sections = [title for title, text in text_by_section.items() if 0 < len(text.strip()) < 80]
        return {
            "generated_at": datetime.now(UTC).replace(tzinfo=None).isoformat(),
            "context_validation": context_validation,
            "summary": {
                "section_count": len(sections),
                "non_empty_section_count": len(non_empty_sections),
                "missing_required_phrase_count": len(missing_phrases),
                "placeholder_marker_count": len(placeholders_found),
                "short_section_count": len(short_sections),
            },
            "passed": (
                context_validation["passed"]
                and len(non_empty_sections) == len(sections)
                and len(missing_phrases) == 0
                and len(placeholders_found) == 0
            ),
            "missing_required_phrases": missing_phrases,
            "placeholders_found": placeholders_found,
            "short_sections": short_sections,
            "facility": context.get("facility", {}),
        }

    def _serialize_sections_for_json(self, sections: dict[str, Any]) -> dict[str, Any]:
        serializable = {}
        for title, value in sections.items():
            if isinstance(value, list):
                serializable[title] = {"__blocks__": True, "data": serialize_blocks(value)}
            else:
                serializable[title] = {"__blocks__": False, "data": value}
        return serializable

    def _section_to_text(self, value: Any) -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            lines: list[str] = []
            for block in value:
                if hasattr(block, "text"):
                    lines.append(str(block.text))
                elif hasattr(block, "headers"):
                    lines.extend(str(header) for header in block.headers)
                    for row in getattr(block, "rows", []):
                        lines.append(" ".join(str(cell) for cell in row))
            return "\n".join(lines)
        return ""

    def _write_json(self, path: Path, payload: Any) -> None:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
