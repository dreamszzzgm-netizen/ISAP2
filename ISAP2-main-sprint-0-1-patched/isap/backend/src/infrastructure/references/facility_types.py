"""Справочник типов опасных производственных объектов."""
from dataclasses import dataclass


@dataclass
class FacilityType:
    """Тип ОПО."""
    code: str
    name: str
    description: str
    hazard_class_default: int | None = None


FACILITY_TYPES: list[FacilityType] = [
    FacilityType(
        code="gas_distribution",
        name="Сеть газопотребления",
        description="Системы газоснабжения, газораспределительные сети, газопотребляющие установки",
        hazard_class_default=3,
    ),
    FacilityType(
        code="gas_processing",
        name="Компрессорная станция",
        description="Компрессорные установки для транспортировки и переработки газа",
        hazard_class_default=3,
    ),
    FacilityType(
        code="boiler",
        name="Котельная",
        description="Котельные установки паровые, водогрейные, котлы-утилизаторы",
        hazard_class_default=3,
    ),
    FacilityType(
        code="fuel_storage",
        name="Хранилище СУГ/СНГ",
        description="Хранилища сжиженных углеводородных и природных газов",
        hazard_class_default=2,
    ),
    FacilityType(
        code="gas_station",
        name="АЗС / АГНКС",
        description="Автомобильные и автомобильные газонаполнительные компрессорные станции",
        hazard_class_default=3,
    ),
    FacilityType(
        code="oil_pipeline",
        name="Магистральный нефтепровод",
        description="Трубопроводный транспорт нефти и нефтепродуктов",
        hazard_class_default=2,
    ),
    FacilityType(
        code="gas_pipeline",
        name="Магистральный газопровод",
        description="Трубопроводный транспорт природного газа высокого давления",
        hazard_class_default=1,
    ),
    FacilityType(
        code="chemical_plant",
        name="Химический комбинат",
        description="Производства по переработке химического сырья и выпуску химической продукции",
        hazard_class_default=1,
    ),
    FacilityType(
        code="petrochemical",
        name="Нефтехимический комбинат",
        description="Производства по переработке нефти и газа в нефтехимическую продукцию",
        hazard_class_default=1,
    ),
    FacilityType(
        code="oil_refinery",
        name="Нефтеперерабатывающий завод",
        description="Переработка нефти в нефтепродукты",
        hazard_class_default=1,
    ),
    FacilityType(
        code="ammonia_plant",
        name="Производство аммиака",
        description="Установки по производству и хранению аммиака",
        hazard_class_default=1,
    ),
    FacilityType(
        code="acid_plant",
        name="Производство кислот",
        description="Производства серной, азотной, соляной и других минеральных кислот",
        hazard_class_default=2,
    ),
    FacilityType(
        code="explosives",
        name="Производство взрывчатых веществ",
        description="Производства и хранение промышленных взрывчатых веществ",
        hazard_class_default=1,
    ),
    FacilityType(
        code="mining",
        name="Шахта / рудник",
        description="Подземные горные работы с выделением опасных газов и пыли",
        hazard_class_default=2,
    ),
    FacilityType(
        code="nuclear",
        name="Ядерная установка",
        description="Атомные электростанции и предприятия ядерного топливного цикла",
        hazard_class_default=1,
    ),
    FacilityType(
        code="metallurgy",
        name="Металлургический комбинат",
        description="Производство чугуна, стали, проката и сплавов",
        hazard_class_default=2,
    ),
    FacilityType(
        code="paper_mill",
        name="Бумажный комбинат",
        description="Производство целлюлозы, бумаги и картона с химическими процессами",
        hazard_class_default=3,
    ),
    FacilityType(
        code="pharmaceutical",
        name="Фармацевтическое производство",
        description="Производство лекарственных средств с химическим синтезом",
        hazard_class_default=3,
    ),
    FacilityType(
        code="food_processing",
        name="Пищевое производство",
        description="Предприятия пищевой промышленности с технологическими газами и холодильными установками",
        hazard_class_default=4,
    ),
    FacilityType(
        code="other",
        name="Другой тип ОПО",
        description="Иной опасный производственный объект",
        hazard_class_default=None,
    ),
]

# Быстрый поиск по коду
TYPES_BY_CODE: dict[str, FacilityType] = {ft.code: ft for ft in FACILITY_TYPES}


def get_facility_types() -> list[FacilityType]:
    """Получить полный список типов ОПО."""
    return FACILITY_TYPES


def get_facility_type(code: str) -> FacilityType | None:
    """Получить тип ОПО по коду."""
    return TYPES_BY_CODE.get(code)
