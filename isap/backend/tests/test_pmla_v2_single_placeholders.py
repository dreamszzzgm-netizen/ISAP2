"""Stage 1: scalar placeholder mapping for the PMLA v2 template."""
from __future__ import annotations

from src.application.services.pmla_generation_context import PmlaGenerationContext
from src.application.services.pmla_context_builder import PmlaContextBuilder
from src.application.services.pmla_v2_context_mapper import map_to_v2_context


def _source(**overrides) -> dict:
    base = {
        "organization": {"name": "ООО Тест", "short_name": "ООО Тест"},
        "facility": {"name": "ОПО", "address": "г. Тест", "hazard_class": 3},
        "responsible_persons": [],
        "pasf": {},
        "emergency_services": [],
        "questionnaire": {},
        "appendices_manifest": [{"name": "Приложение"}],
    }
    base.update(overrides)
    return base


def test_director_position_and_name_are_separate() -> None:
    result = map_to_v2_context(_source(responsible_persons=[{
        "role": "director",
        "position": "Генеральный директор",
        "full_name": "Иванов Иван Иванович",
        "phone": "+7 900 100-20-30",
    }]))

    assert result["director_position"] == "Генеральный директор"
    assert result["director_full_name"] == "Иванов Иван Иванович"
    assert result["director_initials_surname"] == "И.И. Иванов"
    assert result["director_phone"] == "+7 900 100-20-30"
    assert result["director_position_fullname"] == "Генеральный директор Иванов Иван Иванович"
    assert result["director_initials_surname_full"] == "Иванов Иван Иванович"


def test_pasf_director_position_and_name_are_separate() -> None:
    result = map_to_v2_context(_source(pasf={
        "director_position": "Директор ПАСФ",
        "director_name": "Петров Пётр Петрович",
    }))

    assert result["contractor_director_position"] == "Директор ПАСФ"
    assert result["contractor_director_full_name"] == "Петров Пётр Петрович"
    assert result["contractor_director_initials_surname"] == "П.П. Петров"


def test_pasf_phone_and_address_share_alias_sources() -> None:
    result = map_to_v2_context(_source(pasf={
        "actual_address": "ул. Спасателей, 1",
        "dispatch_phone": "+7 900 111-22-33",
    }))

    assert result["contractor_dispatch_address"] == "ул. Спасателей, 1"
    assert result["dislocation_address"] == result["contractor_dispatch_address"]
    assert result["contractor_phone"] == "+7 900 111-22-33"
    assert result["notification_pasf_phone"] == result["contractor_phone"]


def test_fire_department_full_and_short_names() -> None:
    result = map_to_v2_context(_source(emergency_services=[{
        "service_type": "fire",
        "name": "Пожарно-спасательная часть № 1",
        "short_name": "ПСЧ-1",
        "address": "ул. Пожарная, 1",
        "dispatcher_phone": "101",
    }]))

    assert result["fire_department_name"] == "Пожарно-спасательная часть № 1"
    assert result["fire_department_short_name"] == "ПСЧ-1"
    assert result["fire_department_address"] == "ул. Пожарная, 1"
    assert result["notification_fire_phone"] == "101"


def test_medical_service_type_is_supported() -> None:
    result = map_to_v2_context(_source(emergency_services=[{
        "service_type": "medical",
        "name": "Станция скорой помощи",
        "hospital_name": "Городская больница",
        "hospital_address": "ул. Медицинская, 2",
        "phone": "103",
    }]))

    assert result["ambulance_service_name"] == "Станция скорой помощи"
    assert result["hospital_name"] == "Городская больница"
    assert result["hospital_address"] == "ул. Медицинская, 2"
    assert result["notification_ambulance_phone"] == "103"


def test_hospital_service_type_is_supported() -> None:
    result = map_to_v2_context(_source(emergency_services=[{
        "service_type": "hospital", "name": "Районная больница", "phone": "103",
    }]))
    assert result["ambulance_service_name"] == "Районная больница"


def test_gas_service_and_legacy_supplier_alias() -> None:
    result = map_to_v2_context(_source(emergency_services=[{
        "service_type": "gas", "name": "Газовая АДС", "address": "ул. Газовая, 3", "phone": "104",
    }]))
    assert result["gas_service_name"] == "Газовая АДС"
    assert result["gas_service_address"] == "ул. Газовая, 3"
    assert result["gas_supplier_name"] == result["gas_service_name"]
    assert result["notification_gas_phone"] == "104"


def test_electric_network_fields_and_alias() -> None:
    result = map_to_v2_context(_source(emergency_services=[{
        "service_type": "electric", "name": "Электросети", "short_name": "РЭС",
        "address": "ул. Энергетиков, 4", "dispatcher_phone": "105",
    }]))
    assert result["electric_network_name"] == "Электросети"
    assert result["electric_network_short_name"] == "РЭС"
    assert result["electric_network_address"] == "ул. Энергетиков, 4"
    assert result["electric_company"] == result["electric_network_name"]
    assert result["notification_electric_phone"] == "105"


def test_edds_fields() -> None:
    result = map_to_v2_context(_source(emergency_services=[{
        "service_type": "edds", "name": "ЕДДС района", "short_name": "ЕДДС",
        "address": "ул. Центральная, 5", "dispatcher_phone": "112", "additional_phone": "8-800-1",
    }]))
    assert result["edds_name"] == "ЕДДС района"
    assert result["edds_short_name"] == "ЕДДС"
    assert result["edds_address"] == "ул. Центральная, 5"
    assert result["notification_edds_phone"] == "112"
    assert result["edds_additional_phone"] == "8-800-1"


def test_mchs_fields() -> None:
    result = map_to_v2_context(_source(emergency_services=[{
        "service_type": "mchs", "name": "Главное управление МЧС", "short_name": "ГУ МЧС",
        "address": "ул. МЧС, 6", "phone": "101",
    }]))
    assert result["mchs_department_name"] == "Главное управление МЧС"
    assert result["mchs_department_short_name"] == "ГУ МЧС"
    assert result["mchs_department_address"] == "ул. МЧС, 6"
    assert result["notification_mchs_phone"] == "101"


def test_rostechnadzor_fields() -> None:
    result = map_to_v2_context(_source(emergency_services=[{
        "service_type": "rostechnadzor", "name": "Управление Ростехнадзора",
        "short_name": "Ростехнадзор", "address": "ул. Надзорная, 7", "phone": "8-800-2",
    }]))
    assert result["rostechnadzor_department_name"] == "Управление Ростехнадзора"
    assert result["rostechnadzor_department_short_name"] == "Ростехнадзор"
    assert result["rostechnadzor_department_address"] == "ул. Надзорная, 7"
    assert result["notification_rostechnadzor_phone"] == "8-800-2"


def test_local_administration_fields_and_aliases() -> None:
    result = map_to_v2_context(_source(emergency_services=[{
        "service_type": "administration", "name": "Администрация района", "short_name": "Администрация",
        "address": "ул. Советская, 8", "phone": "8-800-3", "additional_phone": "8-800-4",
    }]))
    assert result["local_administration_name"] == "Администрация района"
    assert result["local_administration_short_name"] == "Администрация"
    assert result["local_administration_address"] == "ул. Советская, 8"
    assert result["notification_administration_phone"] == "8-800-3"
    assert result["local_administration_additional_phone"] == "8-800-4"
    assert result["local_admin"] == result["local_administration_name"]
    assert result["notification_admin_phone"] == result["notification_administration_phone"]


def test_opo_insurance_is_separate() -> None:
    result = map_to_v2_context(_source(insurance={
        "company": "АО Страхование", "company_short_name": "АО С",
        "contract_number": "ОПО-1", "contract_date": "2025-01-10",
        "valid_from": "2025-01-11", "valid_until": "2026-01-10", "insured_amount": "1000000",
    }))
    assert result["opo_insurance_company_name"] == "АО Страхование"
    assert result["opo_insurance_company_short_name"] == "АО С"
    assert result["opo_insurance_policy_number"] == "ОПО-1"
    assert result["opo_insurance_policy_date"] == "10.01.2025"
    assert result["opo_insurance_valid_from"] == "11.01.2025"
    assert result["opo_insurance_valid_until"] == "10.01.2026"
    assert result["opo_insurance_amount"] == "1000000"
    assert result["insurance_amount"] == "1000000"  # falls back to opo_insurance_amount


def test_financial_reserve_order_and_details() -> None:
    result = map_to_v2_context(_source(financial_reserve={
        "order_number": "ФР-1", "order_date": "2025-02-01", "amount": "500000",
        "source": "Собственные средства", "purpose": "Ликвидация аварий",
    }))
    assert result["financial_reserve_order_number"] == "ФР-1"
    assert result["financial_reserve_order_date"] == "01.02.2025"
    assert result["financial_reserve_amount"] == "500000"
    assert result["financial_reserve_source"] == "Собственные средства"
    assert result["financial_reserve_purpose"] == "Ликвидация аварий"


def test_financial_reserve_insurance_is_separate() -> None:
    result = map_to_v2_context(_source(financial_reserve_insurance={
        "company": "АО Резерв", "company_short_name": "АО Р",
        "policy_number": "РЕЗ-1", "policy_date": "2025-03-01",
        "valid_from": "2025-03-02", "valid_until": "2026-03-01", "insured_amount": "750000",
    }))
    assert result["financial_reserve_insurance_company_name"] == "АО Резерв"
    assert result["financial_reserve_insurance_company_short_name"] == "АО Р"
    assert result["financial_reserve_insurance_policy_number"] == "РЕЗ-1"
    assert result["financial_reserve_insurance_policy_date"] == "01.03.2025"
    assert result["financial_reserve_insurance_valid_from"] == "02.03.2025"
    assert result["financial_reserve_insurance_valid_until"] == "01.03.2026"
    assert result["financial_reserve_insurance_amount"] == "750000"
    assert result["opo_insurance_amount"] == ""


def test_missing_sources_remain_empty_and_are_not_invented() -> None:
    result = map_to_v2_context(_source())
    keys = (
        "contractor_director_full_name", "contractor_phone", "fire_department_name",
        "ambulance_service_name", "electric_network_short_name", "edds_address",
        "mchs_department_name", "rostechnadzor_department_name", "local_administration_name",
        "opo_insurance_company_name", "opo_insurance_amount", "financial_reserve_amount",
        "financial_reserve_insurance_company_name", "financial_reserve_insurance_amount",
        "insurance_amount",
    )
    assert all(result[key] == "" for key in keys)


def test_generation_context_keeps_reserve_insurance_separate() -> None:
    context = PmlaGenerationContext(
        insurance={"insured_amount": "100"},
        financial_reserve={"amount": "200"},
        financial_reserve_insurance={"insured_amount": "300"},
    )
    data = context.to_dict()
    assert data["insurance"]["insured_amount"] == "100"
    assert data["financial_reserve"]["amount"] == "200"
    assert data["financial_reserve_insurance"]["insured_amount"] == "300"


def test_context_builder_preserves_three_separate_financial_blocks() -> None:
    raw = _source(
        insurance={"insured_amount": "100"},
        financial_reserve={"amount": "200"},
        financial_reserve_insurance={"insured_amount": "300"},
    )
    context = PmlaContextBuilder(session=None)._from_raw_context(raw)
    assert context.insurance == {"insured_amount": "100"}
    assert context.financial_reserve == {"amount": "200"}
    assert context.financial_reserve_insurance == {"insured_amount": "300"}
