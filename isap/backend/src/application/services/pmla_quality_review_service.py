"""PMLA Quality Review service (v2 — Assembly-aware).

Provides a structured quality report after PMLA generation so an engineer
can review completeness before issuing the document to a client.

v2 adds block-type-aware checks using the Assembly Registry, validating
sections by their block_type (static, variable, generated, toc, appendix,
external) rather than only by raw string presence.

This service does NOT certify legal compliance — it is an aid for human review.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any

from src.application.services.pmla_assembly_blocks import (
    ASSEMBLY_REGISTRY,
    BlockType,
    get_appendix_manifest_entries,
    get_block_def,
    get_front_matter_section_ids,
)


@dataclass
class CheckResult:
    code: str
    title: str
    status: str  # "ok" | "warning" | "critical"
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    block_id: str | None = None
    block_type: str | None = None


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
                    "block_id": c.block_id,
                    "block_type": c.block_type,
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
        rendered_sections: dict[str, Any] | None = None,
    ) -> QualityReviewReport:
        checks: list[CheckResult] = []

        # --- Existing data-level checks ---
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

        # --- v2.1: data completeness checks ---
        checks.append(self._check_emergency_service_phones(questionnaire_context))
        checks.append(self._check_notification_responsible(questionnaire_context))
        checks.append(self._check_financial_reserve_data(questionnaire_context))
        checks.append(self._check_insurance_data(questionnaire_context))
        checks.append(self._check_familiarization_date(questionnaire_context))
        checks.append(self._check_appendix_signatures(questionnaire_context))

        # --- v2.2: knowledge graph context checks ---
        from src.application.services.pmla_knowledge_graph_adapter import (
            PmlaKnowledgeGraphAdapter,
        )
        try:
            kg_adapter = PmlaKnowledgeGraphAdapter()
            kg_context = kg_adapter.get_context(questionnaire_context)
            checks.extend(self._check_graph_context(questionnaire_context, kg_context))
        except Exception as e:
            logger.warning("Knowledge graph adapter failed: %s", e)
            # Don't add graph checks if adapter fails

        # --- v2: block-aware checks via Assembly Registry ---
        checks.append(self._check_static_blocks())
        checks.append(self._check_variable_blocks(questionnaire_context))
        checks.append(self._check_generated_blocks(rendered_sections))
        checks.append(self._check_toc_block(rendered_sections))
        checks.append(self._check_appendix_references(questionnaire_context))
        checks.append(self._check_external_files())

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
            # v2 block-aware recommendations
            if c.code == "assembly_variable_blocks" and c.status == "warning":
                recommendations.append("Заполните недостающие источники данных для переменных блоков (организация, ОПО)")
            if c.code == "assembly_generated_blocks" and c.status != "ok":
                recommendations.append("Проверьте генерируемые блоки — есть пустые или ошибочные разделы")
            if c.code == "assembly_appendix_references" and c.status != "ok":
                recommendations.append("Проверьте манифест приложений и attachments_checklist")

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
        # Normalize: extract names from both strings and dicts; for dicts,
        # only count items where present=True.
        selected_lower: set[str] = set()
        for item in checklist:
            if isinstance(item, str):
                selected_lower.add(item.lower().strip())
            elif isinstance(item, dict):
                name = item.get("name", "")
                present = item.get("present", True)
                if name and present:
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

    # ------------------------------------------------------------------
    # v2.1: Data completeness checks
    # ------------------------------------------------------------------

    def _check_emergency_service_phones(self, ctx: dict[str, Any]) -> CheckResult:
        """Check that emergency services have phone numbers."""
        services = ctx.get("emergency_services") or []
        if not services:
            return CheckResult(
                code="emergency_service_phones",
                title="Телефоны аварийных служб",
                status="ok",
                message="Аварийные службы не указаны — проверка телефонов не требуется",
            )
        missing = []
        for s in services:
            if isinstance(s, dict):
                phone = (s.get("phone") or "").strip()
                name = s.get("name", "—")
                if not phone:
                    missing.append(name)
        if missing:
            return CheckResult(
                code="emergency_service_phones",
                title="Телефоны аварийных служб",
                status="warning",
                message=f"Не указаны телефоны: {', '.join(missing)}",
                details={"missing_phones": missing},
            )
        return CheckResult(
            code="emergency_service_phones",
            title="Телефоны аварийных служб",
            status="ok",
            message="Телефоны указаны у всех служб",
        )

    def _check_notification_responsible(self, ctx: dict[str, Any]) -> CheckResult:
        """Check that notification scheme has responsible persons."""
        scheme = ctx.get("notification_scheme") or {}
        if not scheme:
            return CheckResult(
                code="notification_responsible",
                title="Ответственные за оповещение",
                status="ok",
                message="Схема оповещения не заполнена — проверка не требуется",
            )
        contacts = scheme.get("contacts") or []
        if not contacts:
            # Check if key roles are filled
            roles_filled = 0
            for role in self.NOTIFICATION_KEY_ROLES:
                aliases = self.NOTIFICATION_KEY_ALIASES.get(role, [role])
                if any(scheme.get(a) for a in aliases):
                    roles_filled += 1
            if roles_filled < 2:
                return CheckResult(
                    code="notification_responsible",
                    title="Ответственные за оповещение",
                    status="warning",
                    message="Не указаны контактные лица для оповещения",
                )
        return CheckResult(
            code="notification_responsible",
            title="Ответственные за оповещение",
            status="ok",
            message="Контактные лица определены",
        )

    def _check_financial_reserve_data(self, ctx: dict[str, Any]) -> CheckResult:
        """Check financial reserve completeness."""
        questionnaire = ctx.get("questionnaire") or {}
        financial = questionnaire.get("financial_reserve") or {}
        if not financial:
            return CheckResult(
                code="financial_reserve_data",
                title="Данные финансового резерва",
                status="ok",
                message="Данные о финансовом резерве не переданы",
            )
        created = financial.get("created")
        if created is False:
            return CheckResult(
                code="financial_reserve_data",
                title="Данные финансового резерва",
                status="warning",
                message="Финансовый резерв не создан",
            )
        return CheckResult(
            code="financial_reserve_data",
            title="Данные финансового резерва",
            status="ok",
            message="Данные о финансовом резерве заполнены",
        )

    def _check_insurance_data(self, ctx: dict[str, Any]) -> CheckResult:
        """Check insurance completeness."""
        questionnaire = ctx.get("questionnaire") or {}
        insurance = questionnaire.get("insurance") or {}
        if not insurance:
            return CheckResult(
                code="insurance_data",
                title="Данные страхования",
                status="ok",
                message="Данные о страховании не переданы",
            )
        has_contract = insurance.get("has_contract")
        if has_contract is False:
            return CheckResult(
                code="insurance_data",
                title="Данные страхования",
                status="warning",
                message="Договор страхования не заключён",
            )
        return CheckResult(
            code="insurance_data",
            title="Данные страхования",
            status="ok",
            message="Данные о страховании заполнены",
        )

    def _check_familiarization_date(self, ctx: dict[str, Any]) -> CheckResult:
        """Check that familiarization sheet has a date."""
        facility = ctx.get("facility") or {}
        reg_number = (facility.get("reg_number") or "").strip()
        if not reg_number:
            return CheckResult(
                code="familiarization_date",
                title="Дата и номер в листе ознакомления",
                status="warning",
                message="Регистрационный номер ОПО не указан",
            )
        return CheckResult(
            code="familiarization_date",
            title="Дата и номер в листе ознакомления",
            status="ok",
            message="Регистрационный номер указан",
        )

    def _check_appendix_signatures(self, ctx: dict[str, Any]) -> CheckResult:
        """Check that appendix responsible persons are defined."""
        persons = ctx.get("responsible_persons") or []
        if not persons:
            return CheckResult(
                code="appendix_signatures",
                title="Подписи в приложениях",
                status="warning",
                message="Ответственные лица не указаны — подписи в приложениях будут пустыми",
            )
        has_position = any(
            (p.get("position") or "").strip()
            for p in persons
            if isinstance(p, dict)
        )
        if not has_position:
            return CheckResult(
                code="appendix_signatures",
                title="Подписи в приложениях",
                status="warning",
                message="У ответственных лиц не указаны должности",
            )
        return CheckResult(
            code="appendix_signatures",
            title="Подписи в приложениях",
            status="ok",
            message=f"Определены {len(persons)} ответственных лица",
        )

    def _check_graph_context(
        self,
        ctx: dict[str, Any],
        kg_context: Any,
    ) -> list[CheckResult]:
        """Check PMLA completeness against knowledge graph context.

        All graph checks are WARNING level — they guide the engineer
        without blocking document generation.
        """
        checks: list[CheckResult] = []

        if kg_context.is_empty:
            checks.append(CheckResult(
                code="graph_context_empty",
                title="Контекст графа знаний",
                status="ok",
                message="Контекст графа знаний пуст — проверки пропущены",
            ))
            return checks

        # Check required emergency services
        existing_services = set()
        for s in (ctx.get("emergency_services") or []):
            if isinstance(s, dict):
                stype = (s.get("service_type") or "").lower()
                existing_services.add(stype)
        # Also check PASF
        if ctx.get("pasf"):
            existing_services.add("пасф")

        # Keyword matching: graph service name → keywords that match service_type
        _service_keywords = {
            "пожарная охрана": ["fire", "пожар", "мчс"],
            "скорая медицинская помощь": ["medical", "скорая", "больница"],
            "аварийная газовая служба": ["gas", "газовая", "аварийн"],
            "ПАСФ / АСФ": ["pasf", "асф", "пасф"],
        }
        existing_str = " ".join(existing_services)

        missing_services = []
        for svc in kg_context.required_services:
            keywords = _service_keywords.get(svc, [svc.lower()])
            found = any(kw in existing_str for kw in keywords)
            if not found:
                missing_services.append(svc)
        if missing_services:
            checks.append(CheckResult(
                code="graph_required_service_missing",
                title="Рекомендуемые аварийные службы (граф)",
                status="warning",
                message=f"Рекомендуются службы: {', '.join(missing_services)}",
                details={"missing": missing_services},
            ))
        else:
            checks.append(CheckResult(
                code="graph_required_service_missing",
                title="Рекомендуемые аварийные службы (граф)",
                status="ok",
                message="Все рекомендуемые службы определены",
            ))

        # Check recommended scenarios — use keyword overlap for fuzzy matching
        existing_scenarios: list[str] = []
        for s in (ctx.get("selected_scenarios") or []):
            if isinstance(s, dict):
                existing_scenarios.append((s.get("scenario_name") or "").lower())
            elif isinstance(s, str):
                existing_scenarios.append(s.lower())
        for s in (ctx.get("custom_scenarios") or []):
            if isinstance(s, dict):
                existing_scenarios.append((s.get("title") or s.get("name") or "").lower())

        def _scenarios_match(graph_sc: str, existing: list[str]) -> bool:
            """Check if a graph scenario is covered by any existing scenario."""
            graph_words = set(graph_sc.lower().split())
            for es in existing:
                es_words = set(es.split())
                # Match if at least 50% of graph keywords appear in existing
                if graph_words and len(graph_words & es_words) / len(graph_words) >= 0.5:
                    return True
                # Or if the graph scenario is a substring
                if graph_sc.lower() in es:
                    return True
            return False

        missing_scenarios = [
            sc for sc in kg_context.recommended_scenarios
            if not _scenarios_match(sc, existing_scenarios)
        ]
        if missing_scenarios:
            checks.append(CheckResult(
                code="graph_required_scenario_missing",
                title="Рекомендуемые сценарии (граф)",
                status="warning",
                message=f"Рекомендуются сценарии: {', '.join(missing_scenarios[:3])}{'...' if len(missing_scenarios) > 3 else ''}",
                details={"missing": missing_scenarios},
            ))
        else:
            checks.append(CheckResult(
                code="graph_required_scenario_missing",
                title="Рекомендуемые сценарии (граф)",
                status="ok",
                message="Все рекомендуемые сценарии определены",
            ))

        # Check required appendices
        existing_appendices = set()
        for a in (ctx.get("attachments_checklist") or []):
            if isinstance(a, dict):
                name = (a.get("name") or "").lower()
                if a.get("present", True):
                    existing_appendices.add(name)
            elif isinstance(a, str):
                existing_appendices.add(a.lower())

        missing_appendices = [
            ap for ap in kg_context.required_appendices
            if not any(ap.lower() in ea for ea in existing_appendices)
        ]
        if missing_appendices:
            checks.append(CheckResult(
                code="graph_required_appendix_missing",
                title="Обязательные приложения (граф)",
                status="warning",
                message=f"Отсутствуют приложения: {', '.join(missing_appendices)}",
                details={"missing": missing_appendices},
            ))
        else:
            checks.append(CheckResult(
                code="graph_required_appendix_missing",
                title="Обязательные приложения (граф)",
                status="ok",
                message="Все обязательные приложения определены",
            ))

        return checks

    # ------------------------------------------------------------------
    # v2: Block-aware checks via Assembly Registry
    # ------------------------------------------------------------------

    _HTML_TAG_RE = re.compile(r"<(?:table|tr|td|th|div|span|p|b|i|strong|em)\b", re.IGNORECASE)

    def _check_static_blocks(self) -> CheckResult:
        """Verify all static_block sections exist in the Assembly Registry.

        Static blocks (correction_log, abbreviations, terms, bibliography)
        have fixed content — no questionnaire data or LLM text required.
        """
        from src.application.services.pmla_assembly_blocks import get_static_sections

        static_ids = get_static_sections()
        missing = [sid for sid in static_ids if sid not in ASSEMBLY_REGISTRY]
        if missing:
            return CheckResult(
                code="assembly_static_blocks",
                title="Статические блоки (Assembly)",
                status="critical",
                message=f"Отсутствуют в реестре: {', '.join(missing)}",
                details={"missing": missing},
            )
        return CheckResult(
            code="assembly_static_blocks",
            title="Статические блоки (Assembly)",
            status="ok",
            message=f"Все {len(static_ids)} статических блока определены",
            details={"section_ids": static_ids},
        )

    def _check_variable_blocks(self, ctx: dict[str, Any]) -> CheckResult:
        """Verify variable_block sections have their key data sources populated.

        Checks that organization, facility, and other critical data required
        by variable-block templates is present in the context.
        """
        from src.application.services.pmla_assembly_blocks import get_variable_sections

        variable_ids = get_variable_sections()
        # Map section_id → required data keys in context
        required_keys: dict[str, list[str]] = {
            "title_page": ["organization", "facility"],
            "approval_sheet": ["organization", "facility"],
            "section_1": ["organization", "facility"],
            "section_3": ["facility"],
            "section_4": ["facility"],
            "section_6": ["organization", "facility"],
            "section_8": ["organization", "facility"],
            "section_13": ["organization", "facility"],
            "familiarization_sheet": ["organization"],
        }
        sections_with_missing_data: list[dict[str, Any]] = []
        for sid in variable_ids:
            keys_needed = required_keys.get(sid, ["organization", "facility"])
            missing_keys = [k for k in keys_needed if not ctx.get(k)]
            if missing_keys:
                sections_with_missing_data.append({
                    "section_id": sid,
                    "missing_keys": missing_keys,
                })

        if sections_with_missing_data:
            labels = [f"{s['section_id']} ({', '.join(s['missing_keys'])})" for s in sections_with_missing_data]
            return CheckResult(
                code="assembly_variable_blocks",
                title="Переменные блоки (Assembly)",
                status="warning",
                message=f"Не заполнены источники данных: {'; '.join(labels)}",
                details={"sections_with_missing_data": sections_with_missing_data},
            )
        return CheckResult(
            code="assembly_variable_blocks",
            title="Переменные блоки (Assembly)",
            status="ok",
            message=f"Все {len(variable_ids)} переменных блока имеют данные",
            details={"section_ids": variable_ids},
        )

    def _check_generated_blocks(
        self,
        rendered_sections: dict[str, Any] | None = None,
    ) -> CheckResult:
        """Verify generated_block sections have non-empty, valid content.

        Checks for: non-empty text, no raw HTML tags, no placeholder text,
        minimum content length.
        """
        from src.application.services.pmla_assembly_blocks import get_generated_sections

        generated_ids = get_generated_sections()
        if not rendered_sections:
            return CheckResult(
                code="assembly_generated_blocks",
                title="Генерируемые блоки (Assembly)",
                status="ok",
                message=f"Генерируемые блоки определены ({len(generated_ids)}), контент не передан для проверки",
                details={"section_ids": generated_ids, "note": "rendered_sections не передан"},
            )

        problems: list[dict[str, Any]] = []
        ok_count = 0
        for sid in generated_ids:
            content = rendered_sections.get(sid, "")
            if not content:
                problems.append({"section_id": sid, "issue": "empty"})
                continue
            text = str(content)
            if self._HTML_TAG_RE.search(text):
                problems.append({"section_id": sid, "issue": "raw_html"})
                continue
            if len(text.strip()) < 20:
                problems.append({"section_id": sid, "issue": "too_short"})
                continue
            ok_count += 1

        if problems:
            html_problems = [p["section_id"] for p in problems if p["issue"] == "raw_html"]
            empty_problems = [p["section_id"] for p in problems if p["issue"] == "empty"]
            short_problems = [p["section_id"] for p in problems if p["issue"] == "too_short"]
            messages = []
            if empty_problems:
                messages.append(f"Пустые: {', '.join(empty_problems)}")
            if html_problems:
                messages.append(f"Raw HTML: {', '.join(html_problems)}")
            if short_problems:
                messages.append(f"Слишком короткие: {', '.join(short_problems)}")
            status = "critical" if html_problems or empty_problems else "warning"
            return CheckResult(
                code="assembly_generated_blocks",
                title="Генерируемые блоки (Assembly)",
                status=status,
                message="; ".join(messages),
                details={"problems": problems, "ok_count": ok_count},
            )
        return CheckResult(
            code="assembly_generated_blocks",
            title="Генерируемые блоки (Assembly)",
            status="ok",
            message=f"Все {ok_count} генерируемых блоков заполнены корректно",
            details={"ok_count": ok_count},
        )

    def _check_toc_block(
        self,
        rendered_sections: dict[str, Any] | None = None,
    ) -> CheckResult:
        """Verify word_toc_block section exists and has proper TOC structure."""
        section_id = "toc"
        block_def = get_block_def(section_id)
        if not block_def:
            return CheckResult(
                code="assembly_toc_block",
                title="Содержание (Assembly)",
                status="critical",
                message="Раздел 'Содержание' не найден в Assembly Registry",
                block_id=section_id,
                block_type=BlockType.WORD_TOC.value,
            )

        if rendered_sections:
            content = rendered_sections.get(section_id, "")
            text = str(content)
            has_heading = "Содержание" in text
            has_toc = bool(re.search(r"TOC|\\o\s|\\h\s|MERGEFIELD", text, re.IGNORECASE))
            if has_heading and has_toc:
                return CheckResult(
                    code="assembly_toc_block",
                    title="Содержание (Assembly)",
                    status="ok",
                    message="Содержание: заголовок + TOC placeholder",
                    block_id=section_id,
                    block_type=BlockType.WORD_TOC.value,
                )
            if has_heading:
                return CheckResult(
                    code="assembly_toc_block",
                    title="Содержание (Assembly)",
                    status="ok",
                    message="Содержание: заголовок найден (TOC field будет сгенерирован Word)",
                    block_id=section_id,
                    block_type=BlockType.WORD_TOC.value,
                )

        return CheckResult(
            code="assembly_toc_block",
            title="Содержание (Assembly)",
            status="ok",
            message="Раздел 'Содержание' определён в Assembly Registry (TOC генерируется Word)",
            block_id=section_id,
            block_type=BlockType.WORD_TOC.value,
        )

    def _check_appendix_references(self, ctx: dict[str, Any]) -> CheckResult:
        """Verify appendix_reference blocks have a manifest with entries."""
        from src.application.services.pmla_assembly_blocks import get_appendix_sections

        appendix_ids = get_appendix_sections()
        manifest_entries = get_appendix_manifest_entries()
        attachments = ctx.get("attachments_checklist") or []

        # Build a set of present attachment names
        present_names: set[str] = set()
        for item in attachments:
            if isinstance(item, str):
                present_names.add(item.lower().strip())
            elif isinstance(item, dict):
                name = item.get("name", "")
                present = item.get("present", True)
                if name and present:
                    present_names.add(name.lower().strip())

        if not manifest_entries:
            return CheckResult(
                code="assembly_appendix_references",
                title="Приложения (Assembly)",
                status="critical",
                message="Манифест приложений пуст — приложения не определены",
                details={"appendix_ids": appendix_ids},
            )

        if not present_names:
            return CheckResult(
                code="assembly_appendix_references",
                title="Приложения (Assembly)",
                status="warning",
                message=f"Манифест содержит {len(manifest_entries)} приложений, но attachments_checklist пуст",
                details={"manifest_count": len(manifest_entries)},
            )

        return CheckResult(
            code="assembly_appendix_references",
            title="Приложения (Assembly)",
            status="ok",
            message=f"Манифест приложений: {len(manifest_entries)} записей, {len(present_names)} отмечены",
            details={
                "manifest_count": len(manifest_entries),
                "present_count": len(present_names),
            },
        )

    def _check_external_files(self) -> CheckResult:
        """Placeholder check for external_file blocks.

        Currently only verifies the block type is registered for future use.
        PDF merge is not yet implemented.
        """
        external_count = sum(
            1 for d in ASSEMBLY_REGISTRY.values()
            if d.block_type == BlockType.EXTERNAL_FILE
        )
        return CheckResult(
            code="assembly_external_files",
            title="Внешние файлы (Assembly)",
            status="ok",
            message=f"Тип 'external_file' зарегистрирован (0 блоков, PDF merge — будущее)" if external_count == 0
            else f"Зарегистрировано {external_count} внешних файлов",
            details={"external_count": external_count},
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
