from dataclasses import dataclass, field


@dataclass
class ExplosionParams:
    """Параметры для расчёта зоны взрыва."""

    substance_name: str
    quantity_kg: float
    explosion_energy_mj: float  # Энергия взрыва в МДж
    physical_state: str = "газ"  # газ | жидкость | твёрдое
    confined: bool = False  # В замкнутом объёме?


@dataclass
class ExplosionResult:
    """Результат расчёта зоны взрыва.

    Согласно РД 03-409-01 определяются 4 зоны поражения по избыточному давлению:
    смертельная (в эпицентре, наименьший радиус) → тяжёлых травм → среднего →
    минимального воздействия (внешняя, наибольший радиус).

    ``zone_radius_m`` — радиус внешней зоны возможного поражения (максимальной
    по площади), сохранён для обратной совместимости. Детальные радиусы каждой
    зоны (от тяжёлой к лёгкой) — в поле ``zones``.
    """

    zone_radius_m: float
    zone_type: str  # зона смертельного поражения | зона среднего поражения | зона лёгкого поражения
    method_id: str
    method_title: str
    warnings: list[str] = field(default_factory=list)
    # Радиусы всех зон поражения (м), от наиболее тяжёлой к лёгкой.
    zones: dict[str, float] = field(default_factory=dict)


@dataclass
class ThermalParams:
    """Параметры для расчёта теплового излучения."""

    substance_name: str
    quantity_kg: float
    combustion_energy_mj_kg: float  # Энергия сгорания МДж/кг
    burn_duration_s: float = 60  # Длительность горения
    flame_temperature_k: float = 1200  # Температура пламени


@dataclass
class ThermalResult:
    """Результат расчёта зоны теплового излучения."""

    radiation_zone_m: float  # Радиус зоны теплового излучения
    heat_flux_kw_m2: float  # Плотность теплового потока на границе
    method_id: str
    method_title: str
    warnings: list[str] = field(default_factory=list)


@dataclass
class ToxicParams:
    """Параметры для расчёта зоны токсического поражения."""

    substance_name: str
    quantity_kg: float
    mac_mg_m3: float  # ПДК мг/м³
    lc50_mg_m3: float | None = None  # КЦ50 (при наличии)
    physical_state: str = "газ"
    ventilation_factor: float = 1.0  # Коэффициент вентиляции


@dataclass
class ToxicResult:
    """Результат расчёта зоны токсического поражения."""

    toxic_zone_m: float  # Радиус зоны токсического поражения
    concentration_at_boundary: float  # Концентрация на границе
    method_id: str
    method_title: str
    warnings: list[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    """Результат валидации входных параметров."""

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    applicable_method_id: str | None = None


@dataclass
class CalculationResult:
    """Общий результат расчёта."""

    method_id: str
    input_params: dict
    results: dict
    validation_status: str  # valid | invalid | warning
    warnings: list[str] = field(default_factory=list)
