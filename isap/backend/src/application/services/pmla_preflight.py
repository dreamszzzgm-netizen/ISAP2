"""PmlaPreflight — preflight validation for PMLA generation context.

Provides validation rules for factual data completeness and consistency
before PMLA generation proceeds. Supports draft and final generation modes.

Severity levels:
    BLOCKER — generation must stop in "final" mode
    WARNING — issue to highlight, generation allowed in both modes
    INFO — informational note
"""
from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from src.application.services.pmla_generation_context import PmlaGenerationContext
from src.core.settings import settings

logger = logging.getLogger(__name__)

PASF_UPLOAD_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", settings.upload_root)
)


def _resolve_pasf_document_file_path(file_path: str) -> str | None:
    """Resolve stored PASF file paths, including relative upload storage keys."""
    raw_path = str(file_path or "").strip()
    if not raw_path:
        return None
    if os.path.isabs(raw_path):
        resolved = os.path.normpath(raw_path)
    else:
        resolved = os.path.normpath(os.path.join(PASF_UPLOAD_ROOT, raw_path))
    try:
        inside_upload_root = os.path.commonpath([PASF_UPLOAD_ROOT, resolved]) == PASF_UPLOAD_ROOT
    except ValueError:
        inside_upload_root = False
    return resolved if inside_upload_root else None


# ---------------------------------------------------------------------------
# Issue model
# ---------------------------------------------------------------------------


@dataclass
class PreflightIssue:
    """Single preflight issue."""
    code: str
    field: str
    message: str
    severity: str  # BLOCKER | WARNING | INFO
    source: str | None = None
    recommended_action: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "field": self.field,
            "message": self.message,
            "severity": self.severity,
            "source": self.source,
            "recommended_action": self.recommended_action,
        }


# ---------------------------------------------------------------------------
# Preflight report
# ---------------------------------------------------------------------------


@dataclass
class PmlaPreflightReport:
    """Report from preflight validation.

    Attributes:
        status: Overall status — 'passed', 'has_warnings', 'has_blockers'
        errors: List of BLOCKER issues
        warnings: List of WARNING issues
        info: List of INFO issues
        missing_fields: Simplified list of missing/suggested field paths
        expired_documents: Documents (PASF, etc.) with expired validity
        source_conflicts: Conflicting data between different sources
    """
    status: str = "passed"
    errors: list[PreflightIssue] = field(default_factory=list)
    warnings: list[PreflightIssue] = field(default_factory=list)
    info: list[PreflightIssue] = field(default_factory=list)
    missing_fields: list[str] = field(default_factory=list)
    expired_documents: list[dict[str, Any]] = field(default_factory=list)
    source_conflicts: list[dict[str, Any]] = field(default_factory=list)

    def add_issue(self, code: str, field: str, message: str,
                  severity: str, source: str | None = None,
                  recommended_action: str | None = None) -> None:
        issue = PreflightIssue(
            code=code,
            field=field,
            message=message,
            severity=severity,
            source=source,
            recommended_action=recommended_action,
        )
        if severity == "BLOCKER":
            self.errors.append(issue)
            self.status = "has_blockers"
        elif severity == "WARNING":
            self.warnings.append(issue)
            if self.status != "has_blockers":
                self.status = "has_warnings"
        else:
            self.info.append(issue)

    def add_missing_field(self, field_path: str) -> None:
        if field_path not in self.missing_fields:
            self.missing_fields.append(field_path)

    def add_expired_document(self, doc_type: str, name: str,
                             valid_until: str | None) -> None:
        self.expired_documents.append({
            "type": doc_type,
            "name": name,
            "valid_until": valid_until or "не указана",
        })

    def add_source_conflict(self, field: str, source_a: str,
                            source_b: str, value_a: Any, value_b: Any) -> None:
        self.source_conflicts.append({
            "field": field,
            "source_a": source_a,
            "source_b": source_b,
            "value_a": str(value_a),
            "value_b": str(value_b),
        })

    @property
    def has_blockers(self) -> bool:
        return self.status == "has_blockers"

    @property
    def has_warnings(self) -> bool:
        return self.status in ("has_warnings", "has_blockers")

    @property
    def passed(self) -> bool:
        return self.status == "passed"

    def raise_if_blocked(self, generation_mode: str = "final") -> None:
        """Raise ValueError if generation should be blocked."""
        if self.has_blockers and generation_mode == "final":
            error_summary = "; ".join(e.message for e in self.errors[:10])
            raise ValueError(
                f"Preflight validation failed ({len(self.errors)} blockers): "
                f"{error_summary}"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": [e.to_dict() for e in self.warnings],
            "info": [e.to_dict() for e in self.info],
            "missing_fields": self.missing_fields,
            "expired_documents": self.expired_documents,
            "source_conflicts": self.source_conflicts,
        }


# ---------------------------------------------------------------------------
# Validation logic
# ---------------------------------------------------------------------------


def _is_empty(value: Any) -> bool:
    """Check if a value is empty (None, empty string, empty list/dict, or placeholder)."""
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip() or value.strip() in ("—", "", "—", "н/д", "н/о")
    if isinstance(value, (list, dict)):
        return len(value) == 0
    return False


def _check_date_expired(date_str: str | None) -> bool:
    """Check if a date string (YYYY-MM-DD or DD.MM.YYYY format) is in the past."""
    if not date_str:
        return False  # Can't check if unknown
    try:
        for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d.%m.%y"):
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return dt < datetime.now()
            except ValueError:
                continue
    except Exception:
        pass
    return False


def run_preflight(context: PmlaGenerationContext,
                  generation_mode: str = "final") -> PmlaPreflightReport:
    """Run all preflight checks on the generation context.

    Args:
        context: The PmlaGenerationContext to validate.
        generation_mode: "draft" or "final" — affects severity of some checks.

    Returns:
        PmlaPreflightReport with all found issues.
    """
    report = PmlaPreflightReport()

    # ── Organization checks ──────────────────────────────────────────
    org = context.organization or {}

    if _is_empty(org.get("name")):
        report.add_issue(
            code="ORG_MISSING_NAME",
            field="organization.name",
            message="Не указано полное наименование организации",
            severity="BLOCKER",
            source=context.provenance.get("organization.name", None),
            recommended_action="Заполните наименование организации в карточке организации",
        )
        report.add_missing_field("organization.name")

    # Check that organization name is not mixed with facility name
    fac = context.facility or {}
    org_name = (org.get("name") or "").strip().lower()
    fac_name = (fac.get("name") or "").strip().lower()
    if org_name and fac_name and org_name == fac_name:
        report.add_issue(
            code="ORG_FACILITY_NAME_MIX",
            field="organization.name",
            message="Наименование организации и ОПО совпадают — возможно смешивание данных",
            severity="WARNING",
            recommended_action="Проверьте, что наименование организации и ОПО не дублируются",
        )

    # ── Facility / OPO checks ────────────────────────────────────────

    if _is_empty(fac.get("name")):
        report.add_issue(
            code="FAC_MISSING_NAME",
            field="facility.name",
            message="Не указано наименование ОПО",
            severity="BLOCKER",
            recommended_action="Заполните наименование ОПО в карточке объекта",
        )
        report.add_missing_field("facility.name")

    if _is_empty(fac.get("address")):
        report.add_issue(
            code="FAC_MISSING_ADDRESS",
            field="facility.address",
            message="Не указан адрес ОПО",
            severity="WARNING",
            recommended_action="Заполните адрес ОПО",
        )
        report.add_missing_field("facility.address")

    if _is_empty(fac.get("hazard_class")):
        report.add_issue(
            code="FAC_MISSING_HAZARD_CLASS",
            field="facility.hazard_class",
            message="Не указан класс опасности ОПО",
            severity="BLOCKER",
            recommended_action="Укажите класс опасности ОПО (I-IV)",
        )
        report.add_missing_field("facility.hazard_class")

    if _is_empty(fac.get("reg_number")):
        reg_severity = "BLOCKER" if generation_mode == "final" else "WARNING"
        report.add_issue(
            code="FAC_MISSING_REG_NUMBER",
            field="facility.reg_number",
            message="Не указан регистрационный номер ОПО",
            severity=reg_severity,
            recommended_action="Укажите регистрационный номер ОПО в Ростехнадзоре",
        )
        report.add_missing_field("facility.reg_number")

    # ── Equipment checks ─────────────────────────────────────────────
    equipment = context.equipment or []
    if not equipment:
        report.add_issue(
            code="EQ_EMPTY_LIST",
            field="equipment",
            message="Список оборудования пуст",
            severity="BLOCKER",
            recommended_action="Добавьте оборудование в карточку ОПО",
        )
        report.add_missing_field("equipment")
    else:
        # Check for equipment model consistency
        for i, eq in enumerate(equipment):
            eq_name = eq.get("name", "")
            if isinstance(eq_name, str) and "РДГК" in eq_name:
                # Ensure 'РДГК-10М' is not replaced — this is a regression check
                # The actual protection is in the mapper, but we flag it here
                pass  # Check will be in mapper integrity tests

    # ── PASF checks ──────────────────────────────────────────────────
    pasf = context.pasf or {}
    if not pasf or _is_empty(pasf.get("name")):
        report.add_issue(
            code="PASF_MISSING",
            field="pasf.name",
            message="Не выбран ПАСФ / АСФ",
            severity="BLOCKER",
            recommended_action="Выберите ПАСФ / АСФ в анкете",
        )
        report.add_missing_field("pasf")
    else:
        # PASF is_active check
        pasf_active = pasf.get("is_active")
        if pasf_active is False or (isinstance(pasf_active, int) and pasf_active == 0):
            report.add_issue(
                code="PASF_DISABLED",
                field="pasf.is_active",
                message=f"ПАСФ '{pasf.get('name', '')}' отключён — выберите активный ПАСФ",
                severity="BLOCKER",
                recommended_action="Выберите активный ПАСФ из справочника",
            )
        # PASF certificate must exist
        cert_number = pasf.get("certificate_number")
        if _is_empty(cert_number):
            report.add_issue(
                code="PASF_MISSING_CERTIFICATE",
                field="pasf.certificate_number",
                message=f"У ПАСФ '{pasf.get('name', '')}' отсутствует свидетельство",
                severity="BLOCKER",
                recommended_action="Заполните номер свидетельства ПАСФ",
            )
        if _is_empty(pasf.get("dispatch_phone")):
            report.add_issue(
                code="PASF_MISSING_PHONE",
                field="pasf.dispatch_phone",
                message="Не указан телефон диспетчера ПАСФ",
                severity="WARNING",
                recommended_action="Укажите контактный телефон ПАСФ",
            )
        # PASF certificate expiry
        cert_until = pasf.get("certificate_valid_until")
        if cert_until and _check_date_expired(str(cert_until)):
            cert_severity = "BLOCKER" if generation_mode == "final" else "WARNING"
            report.add_issue(
                code="PASF_CERT_EXPIRED",
                field="pasf.certificate_valid_until",
                message=f"Срок действия свидетельства ПАСФ истёк: {cert_until}",
                severity=cert_severity,
                recommended_action="Обновите свидетельство ПАСФ",
            )
            report.add_expired_document("certificate", pasf.get("name", ""), str(cert_until))

    # ── PASF document checks ───────────────────────────────────────
    pasf_documents = context.attachments or []
    pasf_id = context.pasf.get("id") if context.pasf else None
    for doc in pasf_documents:
        doc_id = doc.get("id", "")
        doc_type = doc.get("document_type", "unknown")
        doc_status = doc.get("status", "active")
        doc_title = doc.get("title") or doc.get("file_name") or doc_id
        doc_pasf_id = doc.get("pasf_id")

        # Document must belong to the selected PASF
        if pasf_id and doc_pasf_id and doc_pasf_id != pasf_id:
            report.add_issue(
                code="PASF_DOCUMENT_WRONG_OWNER",
                field=f"pasf_documents.{doc_id}",
                message=f"Документ '{doc_title}' принадлежит другому ПАСФ",
                severity="BLOCKER",
                recommended_action="Выберите документы текущего ПАСФ",
            )

        # Revoked/archived document check
        if doc_status in ("revoked", "archived"):
            report.add_issue(
                code="PASF_DOCUMENT_REVOKED",
                field=f"pasf_documents.{doc_id}",
                message=f"Документ '{doc_title}' имеет статус '{doc_status}'",
                severity="BLOCKER",
                recommended_action="Выберите действующий документ",
            )

        # File existence check
        doc_file_path = doc.get("file_path")
        if doc_file_path:
            resolved_doc_file_path = _resolve_pasf_document_file_path(str(doc_file_path))
            if not resolved_doc_file_path or not os.path.exists(resolved_doc_file_path):
                report.add_issue(
                    code="PASF_FILE_NOT_FOUND",
                    field=f"pasf_documents.{doc_id}",
                    message=f"Файл документа '{doc_title}' не найден на диске",
                    severity="BLOCKER",
                    recommended_action="Перезагрузите файл документа",
                )
            else:
                # File unreadable check
                try:
                    with open(resolved_doc_file_path, "rb") as f:
                        content = f.read()
                    # Checksum verification
                    saved_checksum = doc.get("checksum_sha256")
                    if saved_checksum:
                        actual_checksum = hashlib.sha256(content).hexdigest()
                        if actual_checksum != saved_checksum:
                            report.add_issue(
                                code="PASF_FILE_CHECKSUM_MISMATCH",
                                field=f"pasf_documents.{doc_id}",
                                message=f"Контрольная сумма документа '{doc_title}' не совпадает — файл был изменён",
                                severity="BLOCKER",
                                recommended_action="Перезагрузите файл документа",
                            )
                except (OSError, IOError):
                    report.add_issue(
                        code="PASF_FILE_UNREADABLE",
                        field=f"pasf_documents.{doc_id}",
                        message=f"Файл документа '{doc_title}' не может быть прочитан",
                        severity="BLOCKER",
                        recommended_action="Проверьте целостность файла",
                    )

        # Expired document check
        valid_until = doc.get("valid_until")
        if valid_until:
            try:
                if isinstance(valid_until, str):
                    expiry = date.fromisoformat(valid_until)
                else:
                    expiry = valid_until
                if expiry < date.today():
                    doc_severity = "BLOCKER" if generation_mode == "final" else "WARNING"
                    report.add_issue(
                        code="PASF_DOCUMENT_EXPIRED",
                        field=f"pasf_documents.{doc_id}",
                        message=f"Срок действия документа '{doc_title}' истёк: {valid_until}",
                        severity=doc_severity,
                        recommended_action="Обновите документ",
                    )
                    report.add_expired_document(doc_type, doc_title, str(valid_until))
            except (ValueError, TypeError):
                pass

        # Unknown MIME type warning
        mime = doc.get("mime_type", "")
        if mime and mime not in ("application/pdf", "image/jpeg", "image/png"):
            report.add_issue(
                code="PASF_DOCUMENT_UNKNOWN_MIME",
                field=f"pasf_documents.{doc_id}",
                message=f"Документ '{doc_title}' имеет неподдерживаемый MIME тип: {mime}",
                severity="WARNING",
            )

    # Required document types (certificate must exist for selected PASF)
    if pasf_id and pasf_documents:
        selected_types = {d.get("document_type") for d in pasf_documents}
        if "certificate" not in selected_types:
            cert_severity = "BLOCKER" if generation_mode == "final" else "WARNING"
            report.add_issue(
                code="PASF_DOCUMENT_REQUIRED_MISSING",
                field="pasf_documents",
                message="Не выбрано свидетельство ПАСФ (certificate)",
                severity=cert_severity,
                recommended_action="Выберите свидетельство ПАСФ для включения в приложения",
            )

    # ── Emergency services checks ────────────────────────────────────
    services = context.emergency_services or []
    if not services:
        svc_severity = "BLOCKER" if generation_mode == "final" else "WARNING"
        report.add_issue(
            code="SVC_EMPTY_LIST",
            field="emergency_services",
            message="Не выбраны аварийные службы",
            severity=svc_severity,
            recommended_action="Выберите аварийные службы в анкете",
        )
        report.add_missing_field("emergency_services")
    else:
        for svc in services:
            svc_name = svc.get("name", "")
            svc_phone = svc.get("phone") or svc.get("dispatcher_phone") or ""
            # Service is_active check
            svc_active = svc.get("is_active")
            if svc_active is False or (isinstance(svc_active, int) and svc_active == 0):
                report.add_issue(
                    code="SVC_DISABLED",
                    field=f"emergency_services.{services.index(svc)}.is_active",
                    message=f"Служба '{svc_name}' отключена",
                    severity="BLOCKER",
                    recommended_action="Выберите активную аварийную службу",
                )
            if _is_empty(svc_name):
                report.add_issue(
                    code="SVC_MISSING_NAME",
                    field=f"emergency_services.{services.index(svc)}.name",
                    message="У одной из аварийных служб не указано наименование",
                    severity="WARNING",
                )
            if _is_empty(svc_phone):
                report.add_issue(
                    code="SVC_MISSING_PHONE",
                    field=f"emergency_services.{services.index(svc)}.phone",
                    message=f"У службы '{svc_name}' не указан контактный телефон",
                    severity="WARNING",
                )

    # ── Financial reserve checks ─────────────────────────────────────
    financial = context.financial_reserve or {}
    insurance = context.insurance or {}
    fin_created = financial.get("created")
    ins_has = insurance.get("has_contract")
    if fin_created is None and ins_has is None:
        # Not filled — not a blocker, but warn if not explicitly marked as not_provided
        if fin_created is None and financial.get("explicitly_not_provided") is not True:
            report.add_issue(
                code="FIN_NOT_FILLED",
                field="financial_reserve",
                message="Сведения о финансовом обеспечении не заполнены",
                severity="WARNING",
                recommended_action="Заполните сведения о финансовом резерве или явно укажите, что сведения не предоставлены",
            )

    # Check for fake financial values
    fin_amount = financial.get("amount")
    if fin_amount and _is_fake_value(str(fin_amount)):
        report.add_issue(
            code="FIN_FAKE_AMOUNT",
            field="financial_reserve.amount",
            message=f"Сумма финансового резерва выглядит как вымышленная: {fin_amount}",
            severity="BLOCKER",
            recommended_action="Укажите фактическую сумму приказа о финансовом резерве",
        )

    # ── Forces and means ─────────────────────────────────────────────
    resources = context.organization_resources or {}
    actual = resources.get("actual_items") if isinstance(resources, dict) else []
    if not actual:
        report.add_issue(
            code="RES_MISSING_ACTUAL_ITEMS",
            field="organization_resources.actual_items",
            message="Не указаны фактические силы и средства организации",
            severity="WARNING",
            recommended_action="Заполните перечень сил и средств в анкете",
        )
        report.add_missing_field("organization_resources.actual_items")

    # ── Source conflicts ─────────────────────────────────────────────
    _check_source_conflicts(context, report)

    return report


def _check_source_conflicts(context: PmlaGenerationContext,
                            report: PmlaPreflightReport) -> None:
    """Detect conflicts between different data sources using provenance."""
    # If provenance has entries for same field from different source_types,
    # that's expected (DB + graph). We only flag if values differ.
    # This is a placeholder for the actual conflict detection logic.
    pass


def _is_fake_value(value: str) -> bool:
    """Heuristic to detect obviously fake/fabricated values.

    Rules:
    - All zeros (000000, 0.00)
    - Repeated patterns (123456, 999999)
    - Placeholder text
    """
    if not value:
        return False
    cleaned = value.replace(" ", "").replace(",", "").replace(".", "")
    if not cleaned:
        return False
    # All same digit
    if all(ch == cleaned[0] for ch in cleaned):
        return True
    # Sequential digits
    sequential = {"123456", "1234567", "12345678"}
    if cleaned in sequential:
        return True
    # Placeholders
    placeholders = {"ххх", "хх", "***", "тест", "test", "н/д", "нет"}
    if cleaned.lower() in placeholders:
        return True
    return False
