"""PMLA Quality Review service.

Provides a structured quality report after PMLA generation so an engineer
can review completeness before issuing the document to a client.

This service does NOT certify legal compliance — it is an aid for human review.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CheckResult:
    code: str
    title: str
    status: str  # "ok" | "warning" | "critical"
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class QualityReviewReport:
    overall_status: str  # "ok" | "warning" | "critical"
    score: int
    checks: list[CheckResult]
    missing_required_data: list[str]
    manual_review_required: list[str]
    recommendations: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_status": self.overall_status,
            "score": self.score,
            "checks": [
                {
                    "code": c.code,
                    "title": c.title,
                    "status": c.status,
                    "message": c.message,
                    "details": c.details,
                }
                for c in self.checks
            ],
            "missing_required_data": self.missing_required_data,
            "manual_review_required": self.manual_review_required,
            "recommendations": self.recommendations,
        }


class PmlaQualityReviewService:
    """Runs quality checks on questionnaire context and generation metadata."""

    REQUIRED_ATTACHMENTS = [
        "схема расположения ОПО",
        "схема оповещения",
        "договор с ПАСФ",
        "страховой полис",
    ]

    # Flexible key mapping: accept both canonical and demo-data keys
    NOTIFICATION_KEY_ROLES = ["first_receiver", "incident_commander", "pasf_caller", "fire_caller"]
    NOTIFICATION_KEY_ALIASES = {
        "incident_commander": ["responsible_manager", "incident_commander"],
        "pasf_caller": ["calls_pasf", "pasf_caller"],
        "fire_caller": ["calls_fire", "fire_caller"],
        "first_receiver": ["first_receiver"],
    }

    # Локальная карта нормализации типов аварийных служб.
    # Не импортируется из smart_import — самодостаточна в этом файле.
    EMERGENCY_SERVICE_ALIASES = {
        "ambulance": "medical",
        "скорая": "medical",
        "скорая помощь": "medical",
        "медицинская помощь": "medical",
        "medical": "medical",
        "fire": "fire",
        "пожарная": "fire",
        "пожарные": "fire",
        "мчс": "fire",
    }

    def review(
        self,
        questionnaire_context: dict[str, Any],
        generation_meta: dict[str, Any] | None = None,
        docx_path: str | None = None,
        content_docx: bytes | None = None,
    ) -> QualityReviewReport:
        checks: list[CheckResult] = []

        checks.append(self._check_incident_history(questionnaire_context))
        checks.append(self._check_scenarios(questionnaire_context))
        checks.append(self._check_pasf(questionnaire_context))
        checks.append(self._check_emergency_services(questionnaire_context))
        checks.append(self._check_organization_resources(questionnaire_context))
        checks.append(self._check_notification_scheme(questionnaire_context))
        checks.append(self._check_financial_reserve(questionnaire_context))
        checks.append(self._check_insurance(questionnaire_context))
        checks.append(self._check_attachments_checklist(questionnaire_context))
        checks.append(self._check_docx_created(docx_path, content_docx))

        missing = [c.message for c in checks if c.status == "critical"]
        manual = []
        recommendations = []

        for c in checks:
            if c.status == "warning":
                manual.append(f"{c.title}: {c.message}")
            if c.code == "incident_history" and c.status == "warning":
                recommendations.append("Уточните сведения об авариях и инцидентах перед выдачей документа")
            if c.code == "pasf" and c.status == "warning":
                recommendations.append("Выберите ПАСФ или заполните данные вручную")
            if c.code == "emergency_services" and c.status != "ok":
                recommendations.append("Убедитесь, что аварийные службы указаны корректно")
            if c.code == "notification_scheme" and c.status != "ok":
                recommendations.append("Проверьте схему оповещения — укажите ключевые роли")
            if c.code == "financial_reserve" and c.status == "warning":
                recommendations.append("Укажите номер приказа и сумму финансового резерва")
            if c.code == "insurance" and c.status == "warning":
                recommendations.append("Укажите реквизиты договора страхования")
            if c.code == "attachments_checklist" and c.status == "warning":
                recommendations.append("Отметьте недостающие приложения перед выдачей документа")

        if not missing:
            recommendations.append("Рекомендуется проверить текст документа перед выдачей клиенту")

        score = self._calculate_score(checks)
        overall = self._determine_overall(checks)

        return QualityReviewReport(
            overall_status=overall,
            score=score,
            checks=checks,
            missing_required_data=missing,
            manual_review_required=manual,
            recommendations=recommendations,
        )

    def _check_incident_history(self, ctx: dict[str, Any]) -> CheckResult:
        questionnaire = ctx.get("questionnaire") or {}
        incident = questionnaire.get("incident_history") or ctx.get("incident_history") or {}
        has_incidents = incident.get("has_incidents")
        items = incident.get("items") or []

        if has_incidents is None:
            return CheckResult(
                code="incident_history",
                title="Сведения об авариях и инцидентах",
                status="warning",
                message="Блок аварий/инцидентов не заполнен",
            )
        has_incidents_str = str(has_incidents).lower()
        if has_incidents_str in {"true", "да", "yes", "1"}:
            if not items:
                return CheckResult(
                    code="incident_history",
                    title="Сведения об авариях и инцидентах",
                    status="critical",
                    message="Указано наличие аварий, но список событий пуст",
                )
            return CheckResult(
                code="incident_history",
                title="Сведения об авариях и инцидентах",
                status="ok",
                message=f"Заполнено: {len(items)} событий",
                details={"item_count": len(items)},
            )
        return CheckResult(
            code="incident_history",
            title="Сведения об авариях и инцидентах",
            status="ok",
            message="Указано, что аварий/инцидентов не было",
        )

    def _check_scenarios(self, ctx: dict[str, Any]) -> CheckResult:
        selected = ctx.get("selected_scenarios") or []
        custom = ctx.get("custom_scenarios") or []
        total = len(selected) + len(custom)
        if total > 0:
            return CheckResult(
                code="scenarios",
                title="Сценарии аварий",
                status="ok",
                message=f"Выбрано сценариев: {total}",
                details={"selected": len(selected), "custom": len(custom)},
            )
        return CheckResult(
            code="scenarios",
            title="Сценарии аварий",
            status="warning",
            message="Сценарии аварий не выбраны",
        )

    def _check_pasf(self, ctx: dict[str, Any]) -> CheckResult:
        pasf = ctx.get("pasf")
        questionnaire = ctx.get("questionnaire") or {}
        pasf_manual = questionnaire.get("pasf_manual") or {}
        if pasf and (pasf.get("name") or pasf.get("certificate_number")):
            return CheckResult(
                code="pasf",
                title="ПАСФ / АСФ",
                status="ok",
                message=f"ПАСФ выбран: {pasf.get('name', '—')}",
            )
        if pasf_manual.get("name") or pasf_manual.get("certificate_number"):
            return CheckResult(
                code="pasf",
                title="ПАСФ / АСФ",
                status="ok",
                message="ПАСФ заполнен вручную",
            )
        return CheckResult(
            code="pasf",
            title="ПАСФ / АСФ",
            status="warning",
            message="ПАСФ не выбран и не заполнен",
        )

    def _check_emergency_services(self, ctx: dict[str, Any]) -> CheckResult:
        services = ctx.get("emergency_services") or []
        if not services:
            return CheckResult(
                code="emergency_services",
                title="Аварийные службы",
                status="critical",
                message="Аварийные службы полностью отсутствуют",
            )

        def _normalize_service_type(raw: Any) -> str:
            key = str(raw or "").strip().lower()
            return self.EMERGENCY_SERVICE_ALIASES.get(key, key)

        types = {
            _normalize_service_type(s.get("service_type"))
            for s in services
            if isinstance(s, dict)
        }
        required = {"fire", "medical"}
        missing_types = required - types
        if missing_types:
            labels = {"fire": "пожарная охрана", "medical": "медицинская помощь"}
            missing_labels = [labels.get(t, t) for t in missing_types]
            return CheckResult(
                code="emergency_services",
                title="Аварийные службы",
                status="warning",
                message=f"Отсутствуют: {', '.join(missing_labels)}",
                details={"present": sorted(types), "missing": sorted(missing_types)},
            )
        return CheckResult(
            code="emergency_services",
            title="Аварийные службы",
            status="ok",
            message=f"Указано служб: {len(services)}",
            details={"types": sorted(types)},
        )

    def _check_organization_resources(self, ctx: dict[str, Any]) -> CheckResult:
        resources = ctx.get("organization_resources") or {}
        if not isinstance(resources, dict):
            resources = {}
        # Блок считается заполненным, если хотя бы один из ключей несёт
        # значимые данные (поддержка канонических и расширенных имён полей).
        resource_keys = (
            "actual_items",
            "recommended_items",
            "user_notes",
            "ppe",
            "fire_fighting",
            "monitoring",
            "communication",
            "instruments",
            "personnel",
        )
        filled: dict[str, int] = {}
        for key in resource_keys:
            value = resources.get(key)
            if isinstance(value, (list, tuple, dict, str)):
                if len(value) > 0:
                    filled[key] = len(value)
            elif value:
                filled[key] = 1
        if filled:
            return CheckResult(
                code="organization_resources",
                title="Силы и средства организации",
                status="ok",
                message=f"Заполнено разделов: {len(filled)}",
                details={"filled_sections": sorted(filled.keys())},
            )
        return CheckResult(
            code="organization_resources",
            title="Силы и средства организации",
            status="warning",
            message="Блок сил и средств пуст",
        )

    def _check_notification_scheme(self, ctx: dict[str, Any]) -> CheckResult:
        scheme = ctx.get("notification_scheme") or {}
        if not scheme:
            return CheckResult(
                code="notification_scheme",
                title="Схема оповещения",
                status="critical",
                message="Схема оповещения отсутствует",
            )
        # Check each role using aliases (accept both canonical and demo keys)
        filled_roles = []
        missing_roles = []
        for role in self.NOTIFICATION_KEY_ROLES:
            aliases = self.NOTIFICATION_KEY_ALIASES.get(role, [role])
            found = any(scheme.get(alias) for alias in aliases)
            if found:
                filled_roles.append(role)
            else:
                missing_roles.append(role)
        if not filled_roles:
            return CheckResult(
                code="notification_scheme",
                title="Схема оповещения",
                status="critical",
                message="Схема оповещения пуста — ни одна роль не заполнена",
            )
        if missing_roles:
            labels = {
                "first_receiver": "первое сообщение",
                "incident_commander": "руководитель реагирования",
                "pasf_caller": "вызов ПАСФ",
                "fire_caller": "вызов пожарной охраны",
            }
            missing_labels = [labels.get(r, r) for r in missing_roles]
            return CheckResult(
                code="notification_scheme",
                title="Схема оповещения",
                status="warning",
                message=f"Отсутствуют роли: {', '.join(missing_labels)}",
                details={"filled": filled_roles, "missing": missing_roles},
            )
        return CheckResult(
            code="notification_scheme",
            title="Схема оповещения",
            status="ok",
            message="Все ключевые роли заполнены",
        )

    def _check_financial_reserve(self, ctx: dict[str, Any]) -> CheckResult:
        questionnaire = ctx.get("questionnaire") or {}
        financial = questionnaire.get("financial_reserve") or {}
        created = financial.get("created")
        order_number = financial.get("order_number") or ""
        amount = financial.get("amount") or ""
        if created and order_number and amount:
            return CheckResult(
                code="financial_reserve",
                title="Финансовый резерв",
                status="ok",
                message=f"Приказ {order_number}, сумма {amount}",
            )
        if created and (order_number or amount):
            return CheckResult(
                code="financial_reserve",
                title="Финансовый резерв",
                status="warning",
                message="Резерв создан, но не заполнены реквизиты (номер приказа / сумма)",
            )
        if created:
            return CheckResult(
                code="financial_reserve",
                title="Финансовый резерв",
                status="warning",
                message="Резерв создан, но реквизиты отсутствуют",
            )
        return CheckResult(
            code="financial_reserve",
            title="Финансовый резерв",
            status="warning",
            message="Финансовый резерв не заполнен",
        )

    def _check_insurance(self, ctx: dict[str, Any]) -> CheckResult:
        questionnaire = ctx.get("questionnaire") or {}
        insurance = questionnaire.get("insurance") or {}
        has_contract = insurance.get("has_contract")
        company = insurance.get("company") or ""
        contract_number = insurance.get("contract_number") or ""
        if has_contract and company and contract_number:
            return CheckResult(
                code="insurance",
                title="Страхование",
                status="ok",
                message=f"Договор {contract_number}, компания {company}",
            )
        if has_contract and (company or contract_number):
            return CheckResult(
                code="insurance",
                title="Страхование",
                status="warning",
                message="Договор есть, но заполнены не все реквизиты",
            )
        return CheckResult(
            code="insurance",
            title="Страхование",
            status="warning",
            message="Договор страхования не заполнен",
        )

    def _check_attachments_checklist(self, ctx: dict[str, Any]) -> CheckResult:
        checklist = ctx.get("attachments_checklist") or []
        if isinstance(checklist, str):
            checklist = [checklist]
        # Normalize: extract names from both strings and dicts
        selected_lower = set()
        for item in checklist:
            if isinstance(item, str):
                selected_lower.add(item.lower().strip())
            elif isinstance(item, dict):
                name = item.get("name", "")
                if name:
                    selected_lower.add(name.lower().strip())
        missing = [a for a in self.REQUIRED_ATTACHMENTS if a.lower() not in selected_lower]
        if not missing:
            return CheckResult(
                code="attachments_checklist",
                title="Приложения",
                status="ok",
                message="Все ключевые приложения отмечены",
            )
        return CheckResult(
            code="attachments_checklist",
            title="Приложения",
            status="warning",
            message=f"Отсутствуют: {', '.join(missing)}",
            details={"missing": missing},
        )

    def _check_docx_created(
        self,
        docx_path: str | None,
        content_docx: bytes | None = None,
    ) -> CheckResult:
        # Байты DOCX в DocumentModel.content_docx — источник истины;
        # файл в debug-директории может быть ещё не записан на момент review().
        if content_docx:
            return CheckResult(
                code="docx_created",
                title="DOCX файл",
                status="ok",
                message="DOCX сгенерирован",
                details={"size_bytes": len(content_docx)},
            )
        if docx_path is None:
            return CheckResult(
                code="docx_created",
                title="DOCX файл",
                status="warning",
                message="Путь к DOCX не передан",
            )
        if os.path.isfile(docx_path):
            return CheckResult(
                code="docx_created",
                title="DOCX файл",
                status="ok",
                message="DOCX файл найден",
            )
        return CheckResult(
            code="docx_created",
            title="DOCX файл",
            status="critical",
            message="DOCX файл не найден по указанному пути",
        )

    @staticmethod
    def _calculate_score(checks: list[CheckResult]) -> int:
        score = 100
        for c in checks:
            if c.status == "critical":
                score -= 20
            elif c.status == "warning":
                score -= 8
        return max(0, score)

    @staticmethod
    def _determine_overall(checks: list[CheckResult]) -> str:
        statuses = {c.status for c in checks}
        if "critical" in statuses:
            return "critical"
        if "warning" in statuses:
            return "warning"
        return "ok"
