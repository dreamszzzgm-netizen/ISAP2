from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    Numeric,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def _uuid() -> uuid4:
    return uuid4()


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class OrganizationModel(Base):
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    name = Column(String(500), nullable=False)
    inn = Column(String(20), nullable=False)
    ogrn = Column(String(20))
    address = Column(String(500))
    phone = Column(String(50))
    email = Column(String(200))
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)


class HazardousFacilityModel(Base):
    __tablename__ = "hazardous_facilities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    name = Column(String(500), nullable=False)
    reg_number = Column(String(100))
    hazard_class = Column(SmallInteger)
    facility_type = Column(String(200))
    address = Column(String(500))
    latitude = Column(Numeric(10, 7))
    longitude = Column(Numeric(10, 7))
    commissioning_date = Column(Date)
    inventory_number = Column(String(100))
    properties = Column(JSONB, default=dict)
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)


class EquipmentModel(Base):
    __tablename__ = "equipment"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    hazardous_facility_id = Column(
        UUID(as_uuid=True), ForeignKey("hazardous_facilities.id"), nullable=False
    )
    name = Column(String(500), nullable=False)
    equipment_type = Column(String(100))
    serial_number = Column(String(100))
    manufacturer = Column(String(300))
    manufacture_year = Column(SmallInteger)
    specifications = Column(JSONB, default=dict)
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)


class HazardousSubstanceModel(Base):
    __tablename__ = "hazardous_substances"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    hazardous_facility_id = Column(
        UUID(as_uuid=True), ForeignKey("hazardous_facilities.id"), nullable=False
    )
    name = Column(String(500), nullable=False)
    cas_number = Column(String(20))
    quantity_kg = Column(Numeric(12, 2))
    threshold_quantity_kg = Column(Numeric(12, 2))
    hazard_properties = Column(JSONB, default=dict)
    created_at = Column(DateTime, default=_now)


class ResponsiblePersonModel(Base):
    __tablename__ = "responsible_persons"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    full_name = Column(String(300), nullable=False)
    position = Column(String(300))
    role = Column(String(100))
    phone = Column(String(50))
    email = Column(String(200))
    created_at = Column(DateTime, default=_now)


class DocumentModel(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    hazardous_facility_id = Column(
        UUID(as_uuid=True), ForeignKey("hazardous_facilities.id"), nullable=False
    )
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    document_type = Column(String(100), nullable=False)
    title = Column(String(500))
    status = Column(String(50), default="draft")
    content_docx = Column(LargeBinary)
    rendered_sections = Column(JSONB, default=dict)
    generation_meta = Column(JSONB, default=dict)
    submitted_at = Column(DateTime)
    approved_at = Column(DateTime)
    rejected_at = Column(DateTime)
    review_date = Column(DateTime)
    regeneration_count = Column(Integer, default=0)
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)
    # Review workflow fields
    review_status = Column(String(50), default="needs_review")
    review_comment = Column(String(2000))
    reviewed_by = Column(String(200))
    reviewed_at = Column(DateTime)
    issued_at = Column(DateTime)


class RegulatoryDocumentModel(Base):
    __tablename__ = "regulatory_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    title = Column(String(500), nullable=False)
    category = Column(String(50), nullable=False)  # НПА | рекомендация | методика расчёта
    status = Column(String(50), nullable=False, default="действует")
    replacement_id = Column(UUID(as_uuid=True), ForeignKey("regulatory_documents.id"))
    last_verified_at = Column(DateTime)
    verification_source = Column(String(500))
    notes = Column(Text)
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)


class DocumentVersionModel(Base):
    __tablename__ = "document_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    version_number = Column(Integer, nullable=False)
    input_data = Column(JSONB, nullable=False)
    prompt_version = Column(String(100))
    template_version = Column(String(100))
    calculation_results = Column(JSONB, default=dict)
    reviewer_id = Column(UUID(as_uuid=True))
    reviewer_decision = Column(String(50))
    reviewer_comments = Column(JSONB, default=list)
    regulatory_snapshot = Column(JSONB, default=list)
    ai_review_confidence = Column(Numeric(3, 2))
    ai_review_decision = Column(String(50))
    ai_review_items = Column(JSONB, default=list)
    ai_review_summary = Column(Text)
    content_docx = Column(LargeBinary)
    created_at = Column(DateTime, default=_now)


class CalculationResultModel(Base):
    __tablename__ = "calculation_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    method_id = Column(String(100), nullable=False)
    input_params = Column(JSONB, nullable=False)
    results = Column(JSONB, nullable=False)
    validation_status = Column(String(50))
    created_at = Column(DateTime, default=_now)


class PmlaSampleModel(Base):
    """Образцы ПМЛА для референса."""
    __tablename__ = "pmla_samples"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    title = Column(String(500), nullable=False)
    description = Column(String(2000))
    file_path = Column(String(1000), nullable=False)
    file_name = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_type = Column(String(50), default="docx")
    facility_type = Column(String(200))
    hazard_class = Column(String(50))
    is_active = Column(SmallInteger, default=1)
    is_verified = Column(SmallInteger, default=0)
    usage_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)


class ScenarioMatrixModel(Base):
    """Матрица сценариев аварий для детерминированного выбора."""
    __tablename__ = "scenario_matrix"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    facility_type = Column(String(200), nullable=False)
    hazard_class = Column(String(50), nullable=False)
    scenario_code = Column(String(50), nullable=False)
    scenario_name = Column(String(500), nullable=False)
    factor_type = Column(String(200))
    calculation_method = Column(String(100))
    probability = Column(String(50), default="средняя")
    is_active = Column(SmallInteger, default=1)
    created_at = Column(DateTime, default=_now)


class OpoDetailsModel(Base):
    """Сведения, характеризующие ОПО (обновлённая форма)."""
    __tablename__ = "opo_details"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    facility_id = Column(UUID(as_uuid=True), ForeignKey("hazardous_facilities.id"), unique=True, nullable=False)
    form_data = Column(JSONB, default=dict)
    total_amount = Column(Numeric(10, 3), default=0)
    applicant_type = Column(String(20), default="legal")
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)


class EmergencyRescueUnitModel(Base):
    """Справочник ПАСФ / АСФ."""
    __tablename__ = "emergency_rescue_units"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    name = Column(String(500), nullable=False)
    short_name = Column(String(200))
    organization_type = Column(String(100))
    director_name = Column(String(300))
    director_position = Column(String(300))
    legal_address = Column(String(500))
    actual_address = Column(String(500))
    dispatch_phone = Column(String(100))
    email = Column(String(200))
    manager_name = Column(String(300))
    certificate_number = Column(String(100))
    certificate_date = Column(String(50))
    certificate_valid_until = Column(String(50))
    permitted_work_types = Column(JSONB, default=list)
    equipment_passport = Column(JSONB, default=list)
    staff_count = Column(String(50))
    readiness_mode = Column(String(200))
    service_area = Column(String(500))
    region = Column(String(200))
    is_active = Column(SmallInteger, default=1)
    notes = Column(Text)
    source_import_job_id = Column(UUID(as_uuid=True), ForeignKey("import_jobs.id"))
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)


class PasfDocumentModel(Base):
    """Документ ПАСФ: свидетельство, паспорт АСФ, договор, лицензия."""
    __tablename__ = "pasf_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    pasf_id = Column(
        UUID(as_uuid=True),
        ForeignKey("emergency_rescue_units.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_type = Column(String(50), nullable=False, default="certificate")
    document_number = Column(String(200))
    title = Column(String(500))
    issued_at = Column(Date)
    valid_until = Column(Date, index=True)
    file_path = Column(String(1000))
    file_name = Column(String(500))
    file_size = Column(Integer)
    mime_type = Column(String(100))
    checksum_sha256 = Column(String(64))
    status = Column(String(20), default="active")
    verified_at = Column(DateTime)
    verified_by = Column(String(200))
    notes = Column(Text)
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)


class EmergencyServiceModel(Base):
    """Справочник внешних аварийных служб: пожарные, скорая, полиция, газовая, ЕДДС."""
    __tablename__ = "emergency_services"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    service_type = Column(String(50), nullable=False, default="fire")
    name = Column(String(500), nullable=False)
    address = Column(String(500))
    phone = Column(String(100))
    dispatcher_phone = Column(String(100))
    additional_phone = Column(String(100))
    municipality = Column(String(200))
    settlement = Column(String(200))
    latitude = Column(String(50))
    longitude = Column(String(50))
    service_area = Column(String(500))
    region = Column(String(200))
    is_active = Column(SmallInteger, default=1)
    verified_at = Column(String(50))
    notes = Column(Text)
    source_import_job_id = Column(UUID(as_uuid=True), ForeignKey("import_jobs.id"))
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)


class PmlaQuestionnaireModel(Base):
    """Анкета генерации ПМЛА. Основное содержимое хранится в JSONB для гибкого развития формы."""
    __tablename__ = "pmla_questionnaires"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"))
    facility_id = Column(UUID(as_uuid=True), ForeignKey("hazardous_facilities.id"))
    title = Column(String(500))
    data = Column(JSONB, default=dict)
    source_import_job_id = Column(UUID(as_uuid=True), ForeignKey("import_jobs.id"))
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)


class ImportJobModel(Base):
    """Задание умного импорта."""
    __tablename__ = "import_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    import_type = Column(String(100), nullable=False)
    filename = Column(String(500), nullable=False)
    status = Column(String(50), default="preview")
    header_mapping = Column(JSONB, default=dict)
    total_rows = Column(Integer, default=0)
    created_rows = Column(Integer, default=0)
    updated_rows = Column(Integer, default=0)
    skipped_rows = Column(Integer, default=0)
    error_rows = Column(Integer, default=0)
    warning_rows = Column(Integer, default=0)
    report = Column(JSONB, default=dict)
    created_by = Column(String(200))
    created_at = Column(DateTime, default=_now)
    finished_at = Column(DateTime)


class ImportRowModel(Base):
    """Строка импорта с raw/mapped/normalized данными и статусом."""
    __tablename__ = "import_rows"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    job_id = Column(UUID(as_uuid=True), ForeignKey("import_jobs.id"), nullable=False)
    row_number = Column(Integer, nullable=False)
    raw_data = Column(JSONB, default=dict)
    mapped_data = Column(JSONB, default=dict)
    normalized_data = Column(JSONB, default=dict)
    status = Column(String(50), default="pending")
    errors = Column(JSONB, default=list)
    warnings = Column(JSONB, default=list)
    duplicate_candidates = Column(JSONB, default=list)
    action = Column(String(50), default="create")
    created_at = Column(DateTime, default=_now)
