"""Unit-тесты расчётных методик."""
import math
import pytest

from src.application.services.calculations.base import BaseCalculation
from src.application.services.calculations.types import (
    ExplosionParams, ExplosionResult,
    ThermalParams, ThermalResult,
    ToxicParams, ToxicResult,
)
from src.application.services.calculations.explosion_zone import ExplosionZoneCalculation
from src.application.services.calculations.thermal_radiation import ThermalRadiationCalculation
from src.application.services.calculations.toxic_exposure import ToxicExposureCalculation
from src.application.services.calculations.registry import CalculationRegistry


# ── BaseCalculation ──────────────────────────────────────────────────────────

class TestBaseCalculation:
    def test_validate_range_in_range(self):
        assert BaseCalculation.validate_range(5, 1, 10, "x") is None

    def test_validate_range_below(self):
        err = BaseCalculation.validate_range(0, 1, 10, "x")
        assert err is not None and "вне диапазона" in err

    def test_validate_range_above(self):
        err = BaseCalculation.validate_range(15, 1, 10, "x")
        assert err is not None

    def test_validate_positive_ok(self):
        assert BaseCalculation.validate_positive(1.0, "x") is None

    def test_validate_positive_zero(self):
        err = BaseCalculation.validate_positive(0, "x")
        assert err is not None and "положительным" in err

    def test_validate_positive_negative(self):
        assert BaseCalculation.validate_positive(-5, "x") is not None


# ── ExplosionZoneCalculation ─────────────────────────────────────────────────

class TestExplosionZone:
    def test_basic_calculation(self):
        params = ExplosionParams(
            substance_name="Метан",
            quantity_kg=50000,
            explosion_energy_mj=1000,
            physical_state="газ",
        )
        result = ExplosionZoneCalculation.calculate(params)
        assert isinstance(result, ExplosionResult)
        assert result.zone_radius_m > 0
        assert result.method_id == "tnt_equivalent_v1"

    def test_confined_increases_radius(self):
        params_open = ExplosionParams(
            substance_name="Газ", quantity_kg=1000,
            explosion_energy_mj=500, physical_state="газ", confined=False,
        )
        params_closed = ExplosionParams(
            substance_name="Газ", quantity_kg=1000,
            explosion_energy_mj=500, physical_state="газ", confined=True,
        )
        r_open = ExplosionZoneCalculation.calculate(params_open).zone_radius_m
        r_closed = ExplosionZoneCalculation.calculate(params_closed).zone_radius_m
        assert r_closed > r_open

    def test_larger_quantity_larger_zone(self):
        small = ExplosionParams(substance_name="X", quantity_kg=100, explosion_energy_mj=50)
        large = ExplosionParams(substance_name="X", quantity_kg=10000, explosion_energy_mj=5000)
        assert ExplosionZoneCalculation.calculate(large).zone_radius_m > ExplosionZoneCalculation.calculate(small).zone_radius_m

    def test_negative_mass_warns(self):
        params = ExplosionParams(substance_name="X", quantity_kg=-10, explosion_energy_mj=100)
        result = ExplosionZoneCalculation.calculate(params)
        assert any("положительным" in w for w in result.warnings)

    def test_tnt_conversion(self):
        energy_mj = 4184
        expected_tnt = energy_mj / ExplosionZoneCalculation.TNT_ENERGY_MJ_PER_KG
        assert abs(expected_tnt - 1000) < 0.01

    def test_all_four_zones_present_and_ordered(self):
        """Согласно РД 03-409-01 определяются 4 зоны; смертельная зона —
        наименьшая (в эпицентре), зона минимального воздействия — внешняя,
        наибольшая по радиусу."""
        params = ExplosionParams(
            substance_name="Метан", quantity_kg=50000,
            explosion_energy_mj=1000, physical_state="газ",
        )
        result = ExplosionZoneCalculation.calculate(params)
        assert len(result.zones) == 4
        r_lethal = result.zones["зона смертельного поражения"]
        r_severe = result.zones["зона тяжёлых травм"]
        r_moderate = result.zones["зона среднего поражения"]
        r_minor = result.zones["зона минимального воздействия"]
        # Радиусы возрастают от тяжёлой зоны к лёгкой.
        assert 0 < r_lethal < r_severe < r_moderate < r_minor
        # zone_radius_m — радиус внешней зоны (всей зоны возможного поражения).
        assert result.zone_radius_m == r_minor


# ── ThermalRadiationCalculation ──────────────────────────────────────────────

class TestThermalRadiation:
    def test_basic_calculation(self):
        params = ThermalParams(
            substance_name="Метан",
            quantity_kg=5000,
            combustion_energy_mj_kg=50,
            burn_duration_s=300,
        )
        result = ThermalRadiationCalculation.calculate(params)
        assert isinstance(result, ThermalResult)
        assert result.radiation_zone_m > 0
        assert result.heat_flux_kw_m2 == 12.5  # порог ожогов I степени

    def test_larger_fire_bigger_zone(self):
        small = ThermalParams(substance_name="X", quantity_kg=100, combustion_energy_mj_kg=40, burn_duration_s=60)
        large = ThermalParams(substance_name="X", quantity_kg=10000, combustion_energy_mj_kg=40, burn_duration_s=60)
        assert ThermalRadiationCalculation.calculate(large).radiation_zone_m > ThermalRadiationCalculation.calculate(small).radiation_zone_m

    def test_longer_burn_smaller_zone(self):
        short = ThermalParams(substance_name="X", quantity_kg=1000, combustion_energy_mj_kg=50, burn_duration_s=60)
        long = ThermalParams(substance_name="X", quantity_kg=1000, combustion_energy_mj_kg=50, burn_duration_s=600)
        # Longer burn → lower power → smaller zone
        assert ThermalRadiationCalculation.calculate(long).radiation_zone_m < ThermalRadiationCalculation.calculate(short).radiation_zone_m

    def test_negative_quantity_causes_error(self):
        """Отрицательная масса вызывает ошибку в расчёте (нужна валидация перед расчётом)."""
        from src.application.services.calculations.validation import CalculationValidator
        params = ThermalParams(substance_name="X", quantity_kg=-100, combustion_energy_mj_kg=50)
        v = CalculationValidator()
        result = v.validate_thermal(params)
        assert not result.is_valid


# ── ToxicExposureCalculation ─────────────────────────────────────────────────

class TestToxicExposure:
    def test_basic_calculation(self):
        params = ToxicParams(
            substance_name="Хлор", quantity_kg=500, mac_mg_m3=0.1, physical_state="газ",
        )
        result = ToxicExposureCalculation.calculate(params)
        assert isinstance(result, ToxicResult)
        assert result.toxic_zone_m > 0
        assert result.method_id == "toxic_dispersion_v1"

    def test_higher_mac_smaller_zone(self):
        low_mac = ToxicParams(substance_name="X", quantity_kg=100, mac_mg_m3=0.01)
        high_mac = ToxicParams(substance_name="X", quantity_kg=100, mac_mg_m3=1.0)
        assert ToxicExposureCalculation.calculate(low_mac).toxic_zone_m > ToxicExposureCalculation.calculate(high_mac).toxic_zone_m

    def test_non_gas_warns(self):
        params = ToxicParams(substance_name="X", quantity_kg=100, mac_mg_m3=0.1, physical_state="жидкость")
        result = ToxicExposureCalculation.calculate(params)
        assert any("приближённый" in w for w in result.warnings)

    def test_low_ventilation_warns(self):
        params = ToxicParams(substance_name="X", quantity_kg=100, mac_mg_m3=0.1, ventilation_factor=0.3)
        result = ToxicExposureCalculation.calculate(params)
        assert len(result.warnings) > 0


# ── CalculationRegistry ──────────────────────────────────────────────────────

class TestCalculationRegistry:
    def test_list_methods_not_empty(self):
        methods = CalculationRegistry.list_methods()
        assert len(methods) >= 3

    def test_get_method_info(self):
        info = CalculationRegistry.get_method_info("tnt_equivalent_v1")
        assert info is not None
        assert info["method_id"] == "tnt_equivalent_v1"

    def test_get_unknown_method(self):
        assert CalculationRegistry.get_method_info("nonexistent") is None

    def test_calculate_via_registry(self):
        params = ExplosionParams(substance_name="X", quantity_kg=1000, explosion_energy_mj=200)
        result = CalculationRegistry.calculate("tnt_equivalent_v1", params)
        assert result.method_id == "tnt_equivalent_v1"
        assert result.validation_status == "valid"

    def test_calculate_unknown_raises(self):
        with pytest.raises(ValueError, match="не зарегистрирована"):
            CalculationRegistry.calculate("unknown_method", None)
