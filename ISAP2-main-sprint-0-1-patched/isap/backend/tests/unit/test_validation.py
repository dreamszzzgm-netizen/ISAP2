"""Unit-тесты валидации параметров расчёта."""
import pytest

from src.application.services.calculations.validation import CalculationValidator
from src.application.services.calculations.types import (
    ExplosionParams, ThermalParams, ToxicParams,
)


@pytest.fixture
def validator():
    return CalculationValidator()


# ── Explosion validation ─────────────────────────────────────────────────────

class TestExplosionValidation:
    def test_valid_params(self, validator):
        params = ExplosionParams(substance_name="Метан", quantity_kg=1000, explosion_energy_mj=500)
        result = validator.validate_explosion(params)
        assert result.is_valid
        assert result.applicable_method_id == "tnt_equivalent_v1"

    def test_mass_too_low(self, validator):
        params = ExplosionParams(substance_name="X", quantity_kg=0.01, explosion_energy_mj=100)
        result = validator.validate_explosion(params)
        assert not result.is_valid
        assert any("Масса" in e for e in result.errors)

    def test_mass_too_high(self, validator):
        params = ExplosionParams(substance_name="X", quantity_kg=200000, explosion_energy_mj=100)
        result = validator.validate_explosion(params)
        assert not result.is_valid

    def test_energy_out_of_range(self, validator):
        params = ExplosionParams(substance_name="X", quantity_kg=100, explosion_energy_mj=0.001)
        result = validator.validate_explosion(params)
        assert not result.is_valid

    def test_unknown_physical_state(self, validator):
        params = ExplosionParams(substance_name="X", quantity_kg=100, explosion_energy_mj=50, physical_state="плазма")
        result = validator.validate_explosion(params)
        assert not result.is_valid
        assert any("состояние" in e for e in result.errors)

    def test_solid_gives_warning(self, validator):
        params = ExplosionParams(substance_name="X", quantity_kg=100, explosion_energy_mj=50, physical_state="твёрдое")
        result = validator.validate_explosion(params)
        assert result.is_valid
        assert any("твёрдых" in w for w in result.warnings)

    def test_large_mass_warning(self, validator):
        params = ExplosionParams(substance_name="X", quantity_kg=50000, explosion_energy_mj=10000)
        result = validator.validate_explosion(params)
        assert any("Большое количество" in w for w in result.warnings)


# ── Thermal validation ───────────────────────────────────────────────────────

class TestThermalValidation:
    def test_valid_params(self, validator):
        params = ThermalParams(substance_name="Газ", quantity_kg=5000, combustion_energy_mj_kg=50)
        result = validator.validate_thermal(params)
        assert result.is_valid
        assert result.applicable_method_id == "thermal_radiation_v1"

    def test_mass_out_of_range(self, validator):
        params = ThermalParams(substance_name="X", quantity_kg=0.1, combustion_energy_mj_kg=50)
        result = validator.validate_thermal(params)
        assert not result.is_valid

    def test_energy_out_of_range(self, validator):
        params = ThermalParams(substance_name="X", quantity_kg=100, combustion_energy_mj_kg=200)
        result = validator.validate_thermal(params)
        assert not result.is_valid

    def test_zero_duration_error(self, validator):
        params = ThermalParams(substance_name="X", quantity_kg=100, combustion_energy_mj_kg=50, burn_duration_s=0)
        result = validator.validate_thermal(params)
        assert not result.is_valid

    def test_long_duration_warning(self, validator):
        params = ThermalParams(substance_name="X", quantity_kg=100, combustion_energy_mj_kg=50, burn_duration_s=7200)
        result = validator.validate_thermal(params)
        assert result.is_valid
        assert any("> 1 часа" in w for w in result.warnings)


# ── Toxic validation ─────────────────────────────────────────────────────────

class TestToxicValidation:
    def test_valid_params(self, validator):
        params = ToxicParams(substance_name="Хлор", quantity_kg=500, mac_mg_m3=0.1)
        result = validator.validate_toxic(params)
        assert result.is_valid
        assert result.applicable_method_id == "toxic_dispersion_v1"

    def test_mass_out_of_range(self, validator):
        params = ToxicParams(substance_name="X", quantity_kg=0, mac_mg_m3=0.1)
        result = validator.validate_toxic(params)
        assert not result.is_valid

    def test_mac_out_of_range(self, validator):
        params = ToxicParams(substance_name="X", quantity_kg=100, mac_mg_m3=5000)
        result = validator.validate_toxic(params)
        assert not result.is_valid

    def test_unknown_state(self, validator):
        params = ToxicParams(substance_name="X", quantity_kg=100, mac_mg_m3=0.1, physical_state="плазма")
        result = validator.validate_toxic(params)
        assert not result.is_valid

    def test_non_gas_warning(self, validator):
        params = ToxicParams(substance_name="X", quantity_kg=100, mac_mg_m3=0.1, physical_state="жидкость")
        result = validator.validate_toxic(params)
        assert result.is_valid
        assert any("газообразных" in w for w in result.warnings)

    def test_low_ventilation_warning(self, validator):
        params = ToxicParams(substance_name="X", quantity_kg=100, mac_mg_m3=0.1, ventilation_factor=0.3)
        result = validator.validate_toxic(params)
        assert any("вентиляции" in w for w in result.warnings)
