"""Расчёт зоны поражения при взрыве.

Метод: эквивалент по ТНТ (РД 03-409-01, ГОСТ Р 12.3.047-98).
"""

from src.application.services.calculations.base import BaseCalculation
from src.application.services.calculations.registry import CalculationRegistry
from src.application.services.calculations.types import ExplosionParams, ExplosionResult


class ExplosionZoneCalculation(BaseCalculation):
    """Расчёт зон поражения при взрыве."""

    # Конвертация энергии: 1 кг ТНТ = 4.184 МДж
    TNT_ENERGY_MJ_PER_KG = 4.184

    # Радиусы поражения (м) на 1 кг ТНТ (нормированные)
    # Формула: R = K * (W_TNT)^(1/3), где K - нормированный радиус
    K_LETHAL = 0.28      # Зона смертельного поражения
    K_SEVERE = 0.44       # Зона среднего поражения
    K_MODERATE = 0.67     # Зона лёгкого поражения
    K_MINOR = 1.0         # Зона минимального воздействия

    @staticmethod
    def calculate(params: ExplosionParams) -> ExplosionResult:
        warnings = []

        # Валидация
        err = BaseCalculation.validate_positive(params.quantity_kg, "Масса вещества")
        if err:
            warnings.append(err)

        err = BaseCalculation.validate_positive(params.explosion_energy_mj, "Энергия взрыва")
        if err:
            warnings.append(err)

        if params.physical_state not in ("газ", "жидкость", "твёрдое"):
            warnings.append(f"Неизвестное агрегатное состояние: {params.physical_state}")

        # Эквивалент по ТНТ
        w_tnt = params.explosion_energy_mj / ExplosionZoneCalculation.TNT_ENERGY_MJ_PER_KG

        # Коэффициент для замкнутого объёма (взрыв в помещении усиливается)
        confinement_factor = 1.5 if params.confined else 1.0

        # Расчёт радиусов
        r_lethal = ExplosionZoneCalculation.K_LETHAL * (w_tnt ** (1 / 3)) * confinement_factor
        r_moderate = ExplosionZoneCalculation.K_MODERATE * (w_tnt ** (1 / 3)) * confinement_factor

        # Определяем максимальную зону (смертельного поражения)
        zone_radius = round(r_lethal, 1)
        zone_type = "зона смертельного поражения"

        if zone_radius < 1:
            zone_type = "зона минимального воздействия"
            zone_radius = round(r_moderate, 1)

        if params.confined:
            warnings.append("Учтён коэффициент для замкнутого объёма (1.5)")

        return ExplosionResult(
            zone_radius_m=zone_radius,
            zone_type=zone_type,
            method_id="tnt_equivalent_v1",
            method_title="Метод эквивалента по ТНТ (РД 03-409-01)",
            warnings=warnings,
        )


# Регистрация методики
CalculationRegistry.register(
    method_id="tnt_equivalent_v1",
    func=ExplosionZoneCalculation.calculate,
    title="Метод эквивалента по ТНТ (РД 03-409-01)",
    regulatory_doc_id=None,  # Ссылка на regulatory_documents.id
)
