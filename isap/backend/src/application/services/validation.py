"""Автоматическая валидация ПМЛА."""
import re
from uuid import UUID

from src.application.services.types import Issue, ValidationResult
from src.infrastructure.repositories.regulatory_repo import RegulatoryRepository


def _section_to_text(value) -> str:
    """Конвертирует значение секции (str или list[Block]) в текст для валидации."""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        lines = []
        for b in value:
            if hasattr(b, "text"):
                lines.append(b.text)
            elif hasattr(b, "headers"):
                lines.append(" ".join(b.headers))
                for row in b.rows:
                    lines.append(" ".join(str(c) for c in row))
        return "\n".join(lines)
    return ""


class DocumentValidator:
    """Автоматическая валидация ПМЛА перед отправкой на ревью."""

    def __init__(self, regulatory_repo: RegulatoryRepository):
        self.regulatory_repo = regulatory_repo

    async def validate(
        self,
        rendered_sections: dict[str, str | list],
        context: dict,
        calculation_results: list[dict] | None = None,
    ) -> ValidationResult:
        """Полная валидация документа."""
        issues: list[Issue] = []

        # 1. Все обязательные разделы заполнены
        issues += self._check_mandatory_sections(rendered_sections)

        # 2. Числа в тексте совпадают с расчётами
        if calculation_results:
            issues += self._check_numbers_match(rendered_sections, calculation_results)

        # 3. Контакты не пустые
        issues += self._check_contacts(context)

        # 4. Ссылки на нормативы проверены с реестром
        issues += await self._check_regulatory_references(rendered_sections)

        has_errors = any(i.severity == "error" for i in issues)
        return ValidationResult(
            passed=not has_errors,
            issues=issues,
        )

    def _check_mandatory_sections(
        self, sections: dict[str, str | list]
    ) -> list[Issue]:
        """Проверка заполненности обязательных разделов."""
        issues = []
        mandatory_sections = [
            ("характеристика объекта", ["характеристика"], "error"),
            ("сценарии аварий", ["сценари"], "error"),
            ("действия при авариях", ["действия", "аварий"], "warning"),
        ]

        for section_name, keywords, severity in mandatory_sections:
            found = False
            for title, value in sections.items():
                title_lower = title.lower()
                if any(kw in title_lower for kw in keywords):
                    found = True
                    text = _section_to_text(value)
                    if not text or text.strip() == "":
                        issues.append(
                            Issue(
                                section=title,
                                reason=f"Обязательный раздел '{title}' не заполнен",
                                severity="error",
                            )
                        )
                    elif "[Данные не所提供之]" in text or "[Данные не предоставлены]" in text:
                        issues.append(
                            Issue(
                                section=title,
                                reason=f"Раздел '{title}' содержит незаполненные плейсхолдеры",
                                severity="warning",
                            )
                        )
                    break
            if not found:
                issues.append(
                    Issue(
                        section=section_name,
                        reason=f"Обязательный раздел '{section_name}' не найден",
                        severity=severity,
                    )
                )

        return issues

    def _check_numbers_match(
        self,
        sections: dict[str, str | list],
        calculation_results: list[dict],
    ) -> list[Issue]:
        """Проверка соответствия чисел в тексте результатам расчётов."""
        issues = []

        for calc in calculation_results:
            method_id = calc.get("method_id", "")
            results = calc.get("results", {})

            for key, expected_value in results.items():
                if isinstance(expected_value, (int, float)):
                    pattern = rf"\b{re.escape(str(expected_value))}\b"
                    found_in_any = False
                    for section_title, value in sections.items():
                        text = _section_to_text(value)
                        if re.search(pattern, text):
                            found_in_any = True
                            break

                    if not found_in_any and expected_value > 0:
                        issues.append(
                            Issue(
                                section="Расчётный блок",
                                reason=(
                                    f"Расчётное значение {key}={expected_value} "
                                    f"(метод {method_id}) не найдено в тексте документа"
                                ),
                                severity="warning",
                            )
                        )

        return issues

    def _check_contacts(self, context: dict) -> list[Issue]:
        """Проверка наличия контактов."""
        issues = []
        responsible = context.get("responsible_persons", [])

        if not responsible:
            issues.append(
                Issue(
                    section="Контакты",
                    reason="Не указаны ответственные лица",
                    severity="error",
                )
            )
        else:
            for person in responsible:
                phone = person.get("phone", "")
                if not phone or phone.strip() == "":
                    issues.append(
                        Issue(
                            section="Контакты",
                            reason=f"У {person.get('full_name', '—')} не указан телефон",
                            severity="warning",
                        )
                    )

        return issues

    async def _check_regulatory_references(
        self, sections: dict[str, str | list]
    ) -> list[Issue]:
        """Проверка ссылок на нормативные документы."""
        issues = []
        active_docs = await self.regulatory_repo.get_active_documents()
        active_titles = {d.title.lower() for d in active_docs}

        all_text = "\n".join(_section_to_text(v) for v in sections.values())

        # Извлекаем ссылки на нормативы (Постановление, Приказ, РД, ГОСТ и т.д.)
        reference_patterns = [
            r"Постановление\s+Правительства\s+РФ\s+№\d+",
            r"Приказ\s+Ростехнадзора\s+№\d+",
            r"РД\s+\d+-\d+-\d+",
            r"ГОСТ\s+Р\s+\d+[\.\d]*-\d+",
            r"ФЗ\s+№\d+-ФЗ",
        ]

        for pattern in reference_patterns:
            matches = re.findall(pattern, all_text, re.IGNORECASE)
            for match in matches:
                # Проверяем, есть ли такой документ в реестре
                found = False
                for title in active_titles:
                    if match.lower() in title:
                        found = True
                        break

                if not found:
                    issues.append(
                        Issue(
                            section="Нормативные ссылки",
                            reason=(
                                f"Ссылка '{match}' не найдена в реестре "
                                "или имеет неактуальный статус"
                            ),
                            severity="warning",
                            requires_regulatory_review=True,
                        )
                    )

        return issues
