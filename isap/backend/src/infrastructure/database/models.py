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
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


def _uuid() -> uuid4:
    return uuid4()


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class OrganizationModel(Base):
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    # --- Базовые поля (обратная совместимость) ---
    name = Column(String(500), nullable=False)
    inn = Column(String(20), nullable=False)
    ogrn = Column(String(20))
    address = Column(String(500))
    phone = Column(String(50))
    email = Column(String(200))
    # --- Новые поля карточки организации ---
    org_type = Column(String(20), default="legal")  # legal | individual
    full_name = Column(String(1000))                  # полное наименование юрлица
    short_name = Column(String(500))                  # сокращённое наименование
    legal_address = Column(String(500))               # юридический/регистрационный адрес
    actual_address = Column(String(500))              # фактический адрес
    postal_address = Column(String(500))              # почтовый адрес
    phone_additional = Column(String(50))             # дополнительный телефон
    phone_mobile = Column(String(50))                 # мобильный телефон
    fax = Column(String(50))                          # факс
    website = Column(String(500))                     # сайт
    kpp = Column(String(20))                          # КПП (для юрлиц)
    ogrnip = Column(String(20))                       # ОГРНИП (для ИП)
    okpo = Column(String(20))                         # ОКПО
    # --- Руководитель (для юрлица) ---
    director_full_name = Column(String(300))
    director_position = Column(String(300))
    director_phone = Column(String(50))
    director_email = Column(String(200))
    # --- ИП (фамилия, имя, отчество) ---
    ip_last_name = Column(String(100))
    ip_first_name = Column(String(100))
    ip_middle_name = Column(String(100))
    # --- Связи (relationships) ---
    bank_accounts = relationship("BankAccountModel", back_populates="organization", lazy="selectin")
    okved_codes = relationship("OkvedCodeModel", back_populates="organization", lazy="selectin")
    licenses = relationship("LicenseModel", back_populates="organization", lazy="selectin")
    # --- Служебные поля ---
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)


class BankAccountModel(Base):
    """Банковские счета организации."""
    __tablename__ = "bank_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    account_number = Column(String(34), nullable=False)
    bank_name = Column(String(500))
    bank_bik = Column(String(20))
    bank_corr_account = Column(String(34))
    currency = Column(String(3), default="RUB")
    is_primary = Column(SmallInteger, default=0)
    notes = Column(String(500))
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)
    # Relationship
    organization = relationship("OrganizationModel", back_populates="bank_accounts")


class OkvedCodeModel(Base):
    """Коды ОКВЭД организации."""
    __tablename__ = "okved_codes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    code = Column(String(20), nullable=False)
    description = Column(String(1000))
    is_primary = Column(SmallInteger, default=0)
    created_at = Column(DateTime, default=_now)
    # Relationship
    organization = relationship("OrganizationModel", back_populates="okved_codes")


class LicenseModel(Base):
    """Лицензии организации.

    Согласованные поля: вид деятельности, номер, дата выдачи, статус, файл.
    Поле notes и срок действия исключены как несогласованные.
    file_path — это storage_key (относительный путь внутри upload_root/licenses),
    никогда не возвращается клиенту напрямую.

    При удалении организации лицензии удаляются каскадно (CASCADE).
    Файл на диске не удаляется — это ожидаемое поведение: orphan-файлы
    периодически зачищаются фоновой задачей.
    """
    __tablename__ = "licenses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    activity_type = Column(String(500), nullable=False)   # вид деятельности
    license_number = Column(String(100), nullable=False)  # номер лицензии
    issue_date = Column(Date)                              # дата выдачи
    status = Column(String(50), default="active")         # статус
    # Файл (storage_key — относительный путь внутри licenses/, не возвращается клиенту)
    file_path = Column(String(1000))
    file_name = Column(String(500))
    file_size = Column(Integer)
    mime_type = Column(String(100))
    checksum_sha256 = Column(String(64))
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)
    # Relationship
    organization = relationship("OrganizationModel", back_populates="licenses")


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
    # --- ОПО card fields (feature/opo-card-backend) ---
    opo_full_name = Column(String(500))           # полное наименование ОПО
    classification = Column(JSONB, default=list)   # признаки классификации 4.1–4.12
    work_processes = Column(JSONB, default=dict)   # процессы и работы 2.1–2.6
    licensed_activities = Column(JSONB, default=list)  # лицензируемые виды деятельности
    composition_structures = Column(JSONB, default=list) # здания, сооружения, площадки
    nearby_hazardous = Column(JSONB, default=list) # опасные вещества на других ОПО ближе 500м
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
    agreement_date = Column(String(50))
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
