"""Расчёт зоны токсического поражения.

Метод: моделирование рассеивания газообразного вещества.
"""
import math

from src.application.services.calculations.base import BaseCalculation
from src.application.services.calculations.registry import CalculationRegistry
from src.application.services.calculations.types import ToxicParams, ToxicResult


class ToxicExposureCalculation(BaseCalculation):
    """Расчёт зон токсического поражения."""

    # Стандартные условия
    STANDARD_PRESSURE_PA = 101325  # Давление, Па
    STANDARD_TEMPERATURE_K = 293  # Температура, К (20°C)
    GAS_CONSTANT = 8.314  # Универсальная газовая постоянная, Дж/(моль·К)

    @staticmethod
    def calculate(params: ToxicParams) -> ToxicResult:
        warnings = []

        # Валидация
        err = BaseCalculation.validate_positive(params.quantity_kg, "Масса вещества")
        if err:
            warnings.append(err)

        err = BaseCalculation.validate_positive(params.mac_mg_m3, "ПДК")
        if err:
            warnings.append(err)

        if params.physical_state != "газ":
            warnings.append(
                f"Расчёт для агрегатного состояния '{params.physical_state}' "
                "приближённый. Рекомендуется использовать методику для жидкостей/твёрдых тел."
            )

        # Модель пассивного облака (упрощённая)
        # Концентрация на расстоянии R: C(R) = M / (π/2 * σ_y * σ_z * R)
        # где σ_y, σ_z - стандартные отклонения рассеивания
        # Для пассивного облака: σ = a * R^b (коэффициенты зависят от класса нестабильности)

        # Принимаем класс нестабильности С (нейтральная стратификация)
        a_y, b_y = 0.22, 0.78
        a_z, b_z = 0.20, 0.75

        # Конвертация ПДК в кг/м³
        mac_kg_m3 = params.mac_mg_m3 / 1e6

        # Итеративный расчёт радиуса, где концентрация = ПДК
        # C(R) = M / (π/2 * a_y*R^b_y * a_z*R^b_z * R)
        # C(R) = 2M / (π * a_y * a_z * R^(b_y + b_z + 1))

        m_kg = params.quantity_kg
        ventilation = params.ventilation_factor

        # Решаем: 2M / (π * a_y * a_z * R^(b_y+b_z+1)) = MAC
        # R^(b_y+b_z+1) = 2M / (π * a_y * a_z * MAC)
        exponent = b_y + b_z + 1
        r_value = (
            (2 * m_kg)
            / (math.pi * a_y * a_z * mac_kg_m3 * ventilation)
        ) ** (1 / exponent)

        # Концентрация на границе зоны
        concentration_at_boundary = params.mac_mg_m3

        if r_value > 1000:
            warnings.append(
                f"Большой радиус зоны ({r_value:.0f} м). "
                "Возможно, вещество highly toxic или большое количество."
            )

        if params.lc50_mg_m3 and params.lc50_mg_m3 < params.mac_mg_m3 * 10:
            warnings.append(
                "КЦ50 близка к ПДК — высокая токсичность. "
                "Рекомендуется дополнительная верификация."
            )

        return ToxicResult(
            toxic_zone_m=round(r_value, 1),
            concentration_at_boundary=concentration_at_boundary,
            method_id="toxic_dispersion_v1",
            method_title="Модель рассеивания токсичных веществ (атмосферная дисперсия)",
            warnings=warnings,
        )


# Регистрация методики
CalculationRegistry.register(
    method_id="toxic_dispersion_v1",
    func=ToxicExposureCalculation.calculate,
    title="Модель рассеивания токсичных веществ (атмосферная дисперсия)",
    regulatory_doc_id=None,
)
