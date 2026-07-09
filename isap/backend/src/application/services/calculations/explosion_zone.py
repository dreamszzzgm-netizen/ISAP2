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

    # Нормированные коэффициенты радиуса: R = K * (W_TNT)^(1/3).
    # Согласно РД 03-409-01 зона тем меньше, чем тяжелее поражение:
    # смертельная зона — в эпицентре (наименьший радиус), лёгкая — внешняя.
    K_LETHAL = 0.28      # Зона смертельного поражения (≤ 100 кПа, внутр.)
    K_SEVERE = 0.44       # Зона тяжёлых травм
    K_MODERATE = 0.67     # Зона среднего (лёгкого) поражения
    K_MINOR = 1.0         # Зона минимального воздействия (внешняя)

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

        cube_root = w_tnt ** (1 / 3) if w_tnt > 0 else 0.0

        # Радиусы всех четырёх зон поражения (от тяжёлой к лёгкой).
        zones = {
            "зона смертельного поражения": round(
                ExplosionZoneCalculation.K_LETHAL * cube_root * confinement_factor, 1
            ),
            "зона тяжёлых травм": round(
                ExplosionZoneCalculation.K_SEVERE * cube_root * confinement_factor, 1
            ),
            "зона среднего поражения": round(
                ExplosionZoneCalculation.K_MODERATE * cube_root * confinement_factor, 1
            ),
            "зона минимального воздействия": round(
                ExplosionZoneCalculation.K_MINOR * cube_root * confinement_factor, 1
            ),
        }

        # ``zone_radius_m`` — радиус внешней (максимальной по площади) зоны,
        # охватывающей все степени поражения. Это сохраняет существующие
        # инварианты (большее количество → больший радиус, замкнутый объём
        # увеличивает радиус) и соответствует «зоне возможного поражения».
        zone_radius = zones["зона минимального воздействия"]
        zone_type = "зона минимального воздействия"

        if params.confined:
            warnings.append("Учтён коэффициент для замкнутого объёма (1.5)")

        return ExplosionResult(
            zone_radius_m=zone_radius,
            zone_type=zone_type,
            method_id="tnt_equivalent_v1",
            method_title="Метод эквивалента по ТНТ (РД 03-409-01)",
            warnings=warnings,
            zones=zones,
        )


# Регистрация методики
CalculationRegistry.register(
    method_id="tnt_equivalent_v1",
    func=ExplosionZoneCalculation.calculate,
    title="Метод эквивалента по ТНТ (РД 03-409-01)",
    regulatory_doc_id=None,  # Ссылка на regulatory_documents.id
)
