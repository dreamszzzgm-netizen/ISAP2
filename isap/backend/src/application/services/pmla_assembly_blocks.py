"""PMLA Assembly Block Registry — классификация типов блоков для гибридной сборки.

Каждый раздел ПМЛА имеет тип блока, определяющий стратегию рендеринга:
- static_block: фиксированный текст, без переменных и LLM
- variable_block: Jinja2-шаблон с подстановкой данных из БД/анкеты
- generated_block: требует LLM для генерации описательного текста
- word_toc_block: Word TOC field с заголовками Heading 1/2
- appendix_reference: ссылка на файл в манифесте приложений
- external_file: заготовка для будущих загружаемых файлов
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class BlockType(str, Enum):
    STATIC = "static_block"
    VARIABLE = "variable_block"
    GENERATED = "generated_block"
    WORD_TOC = "word_toc_block"
    APPENDIX_REF = "appendix_reference"
    EXTERNAL_FILE = "external_file"


@dataclass
class SectionBlockDef:
    """Определение блока для одного раздела ПМЛА."""
    section_id: str
    block_type: BlockType
    requires_llm: bool
    template: str | None = None
    description: str = ""


# ---------------------------------------------------------------------------
# Registry: section_id → SectionBlockDef
# ---------------------------------------------------------------------------

ASSEMBLY_REGISTRY: dict[str, SectionBlockDef] = {
    # Front matter
    "title_page": SectionBlockDef(
        "title_page", BlockType.VARIABLE, False,
        "sections/00_title_page.j2",
        "Титульный лист с подписями руководства",
    ),
    "approval_sheet": SectionBlockDef(
        "approval_sheet", BlockType.VARIABLE, False,
        "sections/00_approval_sheet.j2",
        "Лист согласования с ролями разработал/проверил/утвердил",
    ),
    "correction_log": SectionBlockDef(
        "correction_log", BlockType.STATIC, False,
        description="Журнал корректировки — фиксированная DOCX-таблица",
    ),
    "toc": SectionBlockDef(
        "toc", BlockType.WORD_TOC, False,
        description="Содержание — Word TOC field с Heading стилями",
    ),
    "abbreviations": SectionBlockDef(
        "abbreviations", BlockType.STATIC, False,
        "sections/00_abbreviations.j2",
        "Фиксированный список обозначений и сокращений",
    ),
    "terms": SectionBlockDef(
        "terms", BlockType.STATIC, False,
        "sections/00_terms.j2",
        "Фиксированные термины из ФЗ-116",
    ),

    # Main sections
    "introduction": SectionBlockDef(
        "introduction", BlockType.GENERATED, True,
        "sections/00_introduction.j2",
        "Нормативная база — генерируется LLM",
    ),
    "section_1": SectionBlockDef(
        "section_1", BlockType.VARIABLE, False,
        "sections/01_characteristics.j2",
        "Характеристика ОПО — таблицы из данных",
    ),
    "section_2": SectionBlockDef(
        "section_2", BlockType.GENERATED, True,
        "sections/02_scenarios.j2",
        "Сценарии аварий — LLM + расчёты",
    ),
    "section_3": SectionBlockDef(
        "section_3", BlockType.VARIABLE, False,
        "sections/03_accident_history.j2",
        "Аварийность — статистика из данных",
    ),
    "section_4": SectionBlockDef(
        "section_4", BlockType.VARIABLE, False,
        "sections/04_forces.j2",
        "Силы и средства — таблицы из данных",
    ),
    "section_5": SectionBlockDef(
        "section_5", BlockType.GENERATED, True,
        "sections/05_interaction.j2",
        "Взаимодействие сил — генерируется LLM",
    ),
    "section_6": SectionBlockDef(
        "section_6", BlockType.VARIABLE, False,
        "sections/06_composition.j2",
        "Состав и дислокация — таблицы из данных",
    ),
    "section_7": SectionBlockDef(
        "section_7", BlockType.GENERATED, True,
        "sections/07_readiness.j2",
        "Готовность сил — генерируется LLM",
    ),
    "section_8": SectionBlockDef(
        "section_8", BlockType.VARIABLE, False,
        "sections/08_management.j2",
        "Управление и оповещение — таблица из данных",
    ),
    "section_9": SectionBlockDef(
        "section_9", BlockType.GENERATED, True,
        "sections/09_information_exchange.j2",
        "Обмен информацией — генерируется LLM",
    ),
    "section_10": SectionBlockDef(
        "section_10", BlockType.GENERATED, True,
        "sections/10_initial_actions.j2",
        "Первоочередные действия — генерируется LLM",
    ),
    "section_11": SectionBlockDef(
        "section_11", BlockType.GENERATED, True,
        "sections/11_personnel_actions.j2",
        "Действия персонала — генерируется LLM",
    ),
    "section_12": SectionBlockDef(
        "section_12", BlockType.GENERATED, True,
        "sections/12_population_safety.j2",
        "Безопасность населения — генерируется LLM",
    ),
    "section_13": SectionBlockDef(
        "section_13", BlockType.VARIABLE, False,
        "sections/13_material_support.j2",
        "Материально-техническое обеспечение — данные",
    ),
    "special_section": SectionBlockDef(
        "special_section", BlockType.GENERATED, True,
        "sections/20_special_section.j2",
        "Специальный раздел — LLM + сценарии",
    ),

    # Appendices
    "appendix_1": SectionBlockDef(
        "appendix_1", BlockType.APPENDIX_REF, False,
        "sections/30_appendix_1.j2",
        "Приложение 1: Порядок изучения ПМЛА",
    ),
    "appendix_2": SectionBlockDef(
        "appendix_2", BlockType.APPENDIX_REF, False,
        "sections/31_appendix_2.j2",
        "Приложение 2: Форма оперативного сообщения",
    ),
    "appendix_3": SectionBlockDef(
        "appendix_3", BlockType.APPENDIX_REF, False,
        "sections/32_appendix_3.j2",
        "Приложение 3: Состав ПАСФ",
    ),
    "appendix_4": SectionBlockDef(
        "appendix_4", BlockType.APPENDIX_REF, False,
        "sections/33_appendix_4.j2",
        "Приложение 4: Оснащение ПАСФ",
    ),
    "appendix_5": SectionBlockDef(
        "appendix_5", BlockType.APPENDIX_REF, False,
        "sections/34_appendix_5.j2",
        "Приложение 5: Схема оповещения",
    ),

    # Back matter
    "bibliography": SectionBlockDef(
        "bibliography", BlockType.STATIC, False,
        "sections/40_bibliography.j2",
        "Фиксированный список нормативных документов",
    ),
    "familiarization_sheet": SectionBlockDef(
        "familiarization_sheet", BlockType.VARIABLE, False,
        "sections/41_familiarization_sheet.j2",
        "Лист ознакомления — таблица подписей",
    ),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_block_type(section_id: str) -> BlockType | None:
    """Возвращает тип блока для раздела или None, если раздел не найден."""
    entry = ASSEMBLY_REGISTRY.get(section_id)
    return entry.block_type if entry else None


def get_block_def(section_id: str) -> SectionBlockDef | None:
    """Возвращает полное определение блока для раздела."""
    return ASSEMBLY_REGISTRY.get(section_id)


def get_static_sections() -> list[str]:
    """Разделы с фиксированным содержимым (без переменных и LLM)."""
    return [sid for sid, d in ASSEMBLY_REGISTRY.items() if d.block_type == BlockType.STATIC]


def get_variable_sections() -> list[str]:
    """Разделы с подстановкой переменных из контекста."""
    return [sid for sid, d in ASSEMBLY_REGISTRY.items() if d.block_type == BlockType.VARIABLE]


def get_generated_sections() -> list[str]:
    """Разделы, требующие LLM-генерации."""
    return [sid for sid, d in ASSEMBLY_REGISTRY.items() if d.block_type == BlockType.GENERATED]


def get_appendix_sections() -> list[str]:
    """Приложения (ссылки на файлы/манифест)."""
    return [sid for sid, d in ASSEMBLY_REGISTRY.items() if d.block_type == BlockType.APPENDIX_REF]


def requires_llm(section_id: str) -> bool:
    """Проверяет, требует ли раздел LLM."""
    entry = ASSEMBLY_REGISTRY.get(section_id)
    return entry.requires_llm if entry else False
