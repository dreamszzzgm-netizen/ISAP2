"""PMLA Assembly Block Registry — классификация типов блоков для гибридной сборки.

Каждый раздел ПМЛА имеет тип блока, определяющий стратегию рендеринга:
- static_block: фиксированный текст, без переменных и LLM
- variable_block: Jinja2-шаблон с подстановкой данных из БД/анкеты
- generated_block: требует LLM для генерации описательного текста
- word_toc_block: Word TOC field с заголовками Heading 1/2
- appendix_reference: ссылка на файл в манифесте приложений
- external_file: заготовка для будущих загружаемых файлов

Реестр является единым источником истины для DOCX-сборки: front-matter
выделяется по section_id (а не по русским строкам), а манифест приложений
синтезируется из канонических записей реестра.

Поля ``title`` синхронны со ``structure.json`` — инвариант проверяется тестом
``test_registry_titles_match_structure_json``.
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
    title: str
    template: str | None = None
    description: str = ""


# ---------------------------------------------------------------------------
# Registry: section_id → SectionBlockDef
#
# Порядок записей совпадает с порядком разделов в structure.json.
# title — русское название раздела (совпадает со structure.json["title"]),
# используется как ключ dict секций в _build_docx.
# ---------------------------------------------------------------------------

ASSEMBLY_REGISTRY: dict[str, SectionBlockDef] = {
    # Front matter
    "title_page": SectionBlockDef(
        "title_page", BlockType.VARIABLE, False,
        "Титульный лист",
        "sections/00_title_page.j2",
        "Титульный лист с подписями руководства",
    ),
    "approval_sheet": SectionBlockDef(
        "approval_sheet", BlockType.VARIABLE, False,
        "Лист согласования",
        "sections/00_approval_sheet.j2",
        "Лист согласования с ролями разработал/проверил/утвердил",
    ),
    "correction_log": SectionBlockDef(
        "correction_log", BlockType.STATIC, False,
        "Журнал корректировки документа",
        description="Журнал корректировки — фиксированная DOCX-таблица",
    ),
    "toc": SectionBlockDef(
        "toc", BlockType.WORD_TOC, False,
        "Содержание",
        description="Содержание — Word TOC field с Heading стилями",
    ),
    "abbreviations": SectionBlockDef(
        "abbreviations", BlockType.STATIC, False,
        "Перечень обозначений и сокращений",
        "sections/00_abbreviations.j2",
        "Фиксированный список обозначений и сокращений",
    ),
    "terms": SectionBlockDef(
        "terms", BlockType.STATIC, False,
        "Термины и определения",
        "sections/00_terms.j2",
        "Фиксированные термины из ФЗ-116",
    ),

    # Main sections
    "introduction": SectionBlockDef(
        "introduction", BlockType.GENERATED, True,
        "Введение",
        "sections/00_introduction.j2",
        "Нормативная база — генерируется LLM",
    ),
    "section_1": SectionBlockDef(
        "section_1", BlockType.VARIABLE, False,
        "1. Характеристика опасного производственного объекта",
        "sections/01_characteristics.j2",
        "Характеристика ОПО — таблицы из данных",
    ),
    "section_2": SectionBlockDef(
        "section_2", BlockType.GENERATED, True,
        "2. Сценарии наиболее вероятных аварий на ОПО",
        "sections/02_scenarios.j2",
        "Сценарии аварий — LLM + расчёты",
    ),
    "section_3": SectionBlockDef(
        "section_3", BlockType.VARIABLE, False,
        "3. Характеристика аварийности на объекте и аналогичных объектах",
        "sections/03_accident_history.j2",
        "Аварийность — статистика из данных",
    ),
    "section_4": SectionBlockDef(
        "section_4", BlockType.VARIABLE, False,
        "4. Количество необходимых сил и средств для локализации и ликвидации аварий",
        "sections/04_forces.j2",
        "Силы и средства — таблицы из данных",
    ),
    "section_5": SectionBlockDef(
        "section_5", BlockType.GENERATED, True,
        "5. Организация взаимодействия сил и средств при локализации и ликвидации аварий",
        "sections/05_interaction.j2",
        "Взаимодействие сил — генерируется LLM",
    ),
    "section_6": SectionBlockDef(
        "section_6", BlockType.VARIABLE, False,
        "6. Состав и дислокация сил и средств, привлекаемых для локализации и ликвидации аварий",
        "sections/06_composition.j2",
        "Состав и дислокация — таблицы из данных",
    ),
    "section_7": SectionBlockDef(
        "section_7", BlockType.GENERATED, True,
        "7. Порядок обеспечения готовности сил и средств к локализации и ликвидации аварий",
        "sections/07_readiness.j2",
        "Готовность сил — генерируется LLM",
    ),
    "section_8": SectionBlockDef(
        "section_8", BlockType.VARIABLE, False,
        "8. Организация управления, связи и оповещения",
        "sections/08_management.j2",
        "Управление и оповещение — таблица из данных",
    ),
    "section_9": SectionBlockDef(
        "section_9", BlockType.GENERATED, True,
        "9. Система взаимного обмена информацией при локализации и ликвидации аварий",
        "sections/09_information_exchange.j2",
        "Обмен информацией — генерируется LLM",
    ),
    "section_10": SectionBlockDef(
        "section_10", BlockType.GENERATED, True,
        "10. Первоочередные действия по локализации и ликвидации аварий",
        "sections/10_initial_actions.j2",
        "Первоочередные действия — генерируется LLM",
    ),
    "section_11": SectionBlockDef(
        "section_11", BlockType.GENERATED, True,
        "11. Действия производственного персонала при угрозе и возникновении аварий",
        "sections/11_personnel_actions.j2",
        "Действия персонала — генерируется LLM",
    ),
    "section_12": SectionBlockDef(
        "section_12", BlockType.GENERATED, True,
        "12. Мероприятия по обеспечению безопасности населения",
        "sections/12_population_safety.j2",
        "Безопасность населения — генерируется LLM",
    ),
    "section_13": SectionBlockDef(
        "section_13", BlockType.VARIABLE, False,
        "13. Организация материально-технического обеспечения",
        "sections/13_material_support.j2",
        "Материально-техническое обеспечение — данные",
    ),
    "special_section": SectionBlockDef(
        "special_section", BlockType.GENERATED, True,
        "2. Специальный раздел плана мероприятий (оперативная часть)",
        "sections/20_special_section.j2",
        "Специальный раздел — LLM + сценарии",
    ),

    # Appendices
    "appendix_1": SectionBlockDef(
        "appendix_1", BlockType.APPENDIX_REF, False,
        "Приложение 1. Порядок изучения ПМЛА",
        "sections/30_appendix_1.j2",
        "Порядок обучения персонала",
    ),
    "appendix_2": SectionBlockDef(
        "appendix_2", BlockType.APPENDIX_REF, False,
        "Приложение 2. Форма оперативного сообщения об инциденте",
        "sections/31_appendix_2.j2",
        "Шаблон сообщения",
    ),
    "appendix_3": SectionBlockDef(
        "appendix_3", BlockType.APPENDIX_REF, False,
        "Приложение 3. Состав ПАСФ",
        "sections/32_appendix_3.j2",
        "Состав профессиональных аварийно-спасательных формирований",
    ),
    "appendix_4": SectionBlockDef(
        "appendix_4", BlockType.APPENDIX_REF, False,
        "Приложение 4. Оснащение ПАСФ",
        "sections/33_appendix_4.j2",
        "Средства индивидуальной и коллективной защиты",
    ),
    "appendix_5": SectionBlockDef(
        "appendix_5", BlockType.APPENDIX_REF, False,
        "Приложение 5. Схема оповещения",
        "sections/34_appendix_5.j2",
        "Схема оповещения при аварии",
    ),

    # Back matter
    "bibliography": SectionBlockDef(
        "bibliography", BlockType.STATIC, False,
        "Список использованной литературы",
        "sections/40_bibliography.j2",
        "Фиксированный список нормативных документов",
    ),
    "familiarization_sheet": SectionBlockDef(
        "familiarization_sheet", BlockType.VARIABLE, False,
        "Лист ознакомления с ПМЛА",
        "sections/41_familiarization_sheet.j2",
        "Лист ознакомления — таблица подписей",
    ),
}

# Section ids, составляющие front matter: рендерятся специальными
# DOCX-хелперами (титул, согласование, журнал корректировки, оглавление),
# а не общим циклом секций.
FRONT_MATTER_SECTION_IDS: list[str] = [
    "title_page",
    "approval_sheet",
    "correction_log",
    "toc",
]


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


def get_section_title(section_id: str) -> str | None:
    """Русское название раздела (совпадает со structure.json["title"])."""
    entry = ASSEMBLY_REGISTRY.get(section_id)
    return entry.title if entry else None


def get_front_matter_section_ids() -> list[str]:
    """Section ids front matter: рендерятся специальными хелперами."""
    return list(FRONT_MATTER_SECTION_IDS)


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


def get_appendix_manifest_entries() -> list[dict]:
    """Канонические записи манифеста приложений из реестра.

    Возвращает список записей вида::
        {"appendix_number": 1, "section_id": "appendix_1", "title": "Приложение 1. ..."}
    без поля ``present`` (оно выясняется в рентайме из attachments_checklist).
    Порядок совпадает с нумерацией приложений.
    """
    entries: list[dict] = []
    for sid in get_appendix_sections():
        entry = ASSEMBLY_REGISTRY[sid]
        # Номер приложения достаём из префикса "appendix_N".
        try:
            num = int(sid.split("_")[1])
        except (IndexError, ValueError):
            num = len(entries) + 1
        entries.append({
            "appendix_number": num,
            "section_id": sid,
            "title": entry.title,
        })
    return entries


def requires_llm(section_id: str) -> bool:
    """Проверяет, требует ли раздел LLM."""
    entry = ASSEMBLY_REGISTRY.get(section_id)
    return entry.requires_llm if entry else False
