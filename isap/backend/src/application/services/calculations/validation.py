"""Валидация входных параметров расчёта."""
from src.application.services.calculations.base import BaseCalculation
from src.application.services.calculations.types import (
    ExplosionParams,
    ThermalParams,
    ToxicParams,
    ValidationResult,
)


class CalculationValidator:
    """Валидация входных параметров расчёта."""

    # Диапазоны применимости методик
    EXPLOSION_MASS_RANGE = (0.1, 100000)  # кг
    EXPLOSION_ENERGY_RANGE = (0.01, 1000000)  # МДж
    THERMAL_MASS_RANGE = (1, 1000000)  # кг
    THERMAL_ENERGY_RANGE = (1, 100)  # МДж/кг
    TOXIC_MASS_RANGE = (0.01, 100000)  # кг
    TOXIC_MAC_RANGE = (0.001, 1000)  # мг/м³

    def validate_explosion(self, params: ExplosionParams) -> ValidationResult:
        errors = []
        warnings = []

        # Проверка массы
        err = self._check_range(
            params.quantity_kg,
            self.EXPLOSION_MASS_RANGE[0],
            self.EXPLOSION_MASS_RANGE[1],
            "Масса вещества (кг)",
        )
        if err:
            errors.append(err)

        # Проверка энергии
        err = self._check_range(
            params.explosion_energy_mj,
            self.EXPLOSION_ENERGY_RANGE[0],
            self.EXPLOSION_ENERGY_RANGE[1],
            "Энергия взрыва (МДж)",
        )
        if err:
            errors.append(err)

        # Проверка агрегатного состояния
        if params.physical_state not in ("газ", "жидкость", "твёрдое"):
            errors.append(
                f"Неизвестное агрегатное состояние: '{params.physical_state}'. "
                "Допустимые: газ, жидкость, твёрдое"
            )

        # Предупреждения
        if params.physical_state == "твёрдое":
            warnings.append(
                "Для твёрдых веществ расчёт по ТНТ-эквиваленту приближённый. "
                "Рекомендуется уточнить параметры детонации."
            )

        if params.quantity_kg > 10000:
            warnings.append(
                "Большое количество вещества. "
                "Рекомендуется детальное моделирование с учётом рельефа."
            )

        is_valid = len(errors) == 0
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            applicable_method_id="tnt_equivalent_v1" if is_valid else None,
        )

    def validate_thermal(self, params: ThermalParams) -> ValidationResult:
        errors = []
        warnings = []

        err = self._check_range(
            params.quantity_kg,
            self.THERMAL_MASS_RANGE[0],
            self.THERMAL_MASS_RANGE[1],
            "Масса вещества (кг)",
        )
        if err:
            errors.append(err)

        err = self._check_range(
            params.combustion_energy_mj_kg,
            self.THERMAL_ENERGY_RANGE[0],
            self.THERMAL_ENERGY_RANGE[1],
            "Энергия сгорания (МДж/кг)",
        )
        if err:
            errors.append(err)

        if params.burn_duration_s <= 0:
            errors.append("Длительность горения должна быть положительной")

        if params.burn_duration_s > 3600:
            warnings.append(
                "Длительность горения > 1 часа. "
                "Рекомендуется разбить на этапы."
            )

        is_valid = len(errors) == 0
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            applicable_method_id="thermal_radiation_v1" if is_valid else None,
        )

    def validate_toxic(self, params: ToxicParams) -> ValidationResult:
        errors = []
        warnings = []

        err = self._check_range(
            params.quantity_kg,
            self.TOXIC_MASS_RANGE[0],
            self.TOXIC_MASS_RANGE[1],
            "Масса вещества (кг)",
        )
        if err:
            errors.append(err)

        err = self._check_range(
            params.mac_mg_m3,
            self.TOXIC_MAC_RANGE[0],
            self.TOXIC_MAC_RANGE[1],
            "ПДК (мг/м³)",
        )
        if err:
            errors.append(err)

        if params.physical_state not in ("газ", "жидкость", "твёрдое"):
            errors.append(
                f"Неизвестное агрегатное состояние: '{params.physical_state}'. "
                "Допустимые: газ, жидкость, твёрдое"
            )

        if params.physical_state != "газ":
            warnings.append(
                f"Методика рассчитана для газообразных веществ. "
                f"Для '{params.physical_state}' результат приближённый."
            )

        if params.ventilation_factor < 0.5:
            warnings.append(
                "Низкий коэффициент вентиляции — вещество может накапливаться."
            )

        is_valid = len(errors) == 0
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            applicable_method_id="toxic_dispersion_v1" if is_valid else None,
        )

    @staticmethod
    def _check_range(value: float, min_val: float, max_val: float, name: str) -> str | None:
        if value < min_val or value > max_val:
            return f"{name}: {value} вне диапазона [{min_val}, {max_val}]"
        return None
