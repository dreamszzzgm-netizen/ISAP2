"""Расчёт зоны теплового излучения при горении.

Метод: модель теплового излучения от источника (ГОСТ Р 12.3.047-98).
"""
import math

from src.application.services.calculations.base import BaseCalculation
from src.application.services.calculations.registry import CalculationRegistry
from src.application.services.calculations.types import ThermalParams, ThermalResult


class ThermalRadiationCalculation(BaseCalculation):
    """Расчёт зон теплового излучения."""

    # Пороговые значения плотности теплового потока (кВт/м²)
    THRESHOLD_FLEE = 1.5    # Порог для экстренной эвакуации
    THRESHOLD_PAIN = 4.7    # Порог болевого ощущения
    THRESHOLD_BURN_1 = 12.5  # Ожоги I степени
    THRESHOLD_BURN_2 = 18.8  # Ожоги II степени
    THRESHOLD_LETHAL = 37.5  # Летальный исход

    @staticmethod
    def calculate(params: ThermalParams) -> ThermalResult:
        warnings = []

        # Валидация
        err = BaseCalculation.validate_positive(params.quantity_kg, "Масса вещества")
        if err:
            warnings.append(err)

        err = BaseCalculation.validate_positive(
            params.combustion_energy_mj_kg, "Энергия сгорания"
        )
        if err:
            warnings.append(err)

        # Полная энергия горения
        total_energy_mj = params.quantity_kg * params.combustion_energy_mj_kg
        total_energy_j = total_energy_mj * 1e6

        # Мощность излучения (предполагаем сферический источник)
        # Q = E / t (Вт)
        power_w = total_energy_j / params.burn_duration_s

        # Плотность теплового потока на расстоянии R:
        # q(R) = Q / (4 * π * R²) * τ
        # τ - коэффициент прозрачности атмосферы (принимаем 1.0 для MVP)
        # Решаем для q = THRESHOLD_BURN_1:
        # R = sqrt(Q / (4 * π * q))

        q_threshold = ThermalRadiationCalculation.THRESHOLD_BURN_1  # 12.5 кВт/м²
        q_threshold_w = q_threshold * 1000  # Конвертация в Вт/м²

        radiation_zone = math.sqrt(power_w / (4 * math.pi * q_threshold_w))

        # Плотность потока на границе зоны
        heat_flux = round(q_threshold, 2)

        if radiation_zone > 500:
            warnings.append(
                f"Большой радиус зоны ({radiation_zone:.0f} м). "
                "Рекомендуется уточнить параметры горения."
            )

        return ThermalResult(
            radiation_zone_m=round(radiation_zone, 1),
            heat_flux_kw_m2=heat_flux,
            method_id="thermal_radiation_v1",
            method_title="Модель теплового излучения (ГОСТ Р 12.3.047-98)",
            warnings=warnings,
        )


# Регистрация методики
CalculationRegistry.register(
    method_id="thermal_radiation_v1",
    func=ThermalRadiationCalculation.calculate,
    title="Модель теплового излучения (ГОСТ Р 12.3.047-98)",
    regulatory_doc_id=None,
)
