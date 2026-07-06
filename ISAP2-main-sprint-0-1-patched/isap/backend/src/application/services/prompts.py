"""Промпты для LLM генерации — v2 с разделением FACT/TEXT."""

CURRENT_PROMPT_VERSION = "2.0.0"

SYSTEM_PROMPT = (
    "Ты — эксперт по промышленной безопасности с 10-летним стажем. "
    "Твоя задача — разработать раздел Плана мероприятий по локализации "
    "и ликвидации последствий аварий (ПМЛА) в строгом соответствии с "
    "Постановлением Правительства РФ №1437 от 15.09.2020 и ФЗ №116-ФЗ.\n\n"
    "КРИТИЧЕСКИЕ ТРЕБОВАНИЯ:\n"
    "1. Пиши ТОЛЬКО на русском языке в официально-деловом стиле\n"
    "2. Используй формулировки из НПА: «в соответствии с», «на основании», «согласно»\n"
    "3. НЕ используй канцелярские шаблоны — пиши конкретно для данного ОПО\n"
    "4. Ссылайся на конкретное оборудование и вещества из входных данных\n"
    "5. НЕ указывай конкретные числа, расстояния, радиусы — они подставляются системой\n\n"
    "ЗАПРЕЩЕНО:\n"
    "- Использовать английские слова или конструкции\n"
    "- Указывать числовые значения (расстояния, радиусы, количество) — это делает система\n"
    "- Генерировать общие фразы без привязки к конкретному ОПО\n"
    "- Использовать маркированные списки (**) — только проза\n\n"
    "Если данных недостаточно — укажи [Данные не предоставлены], но НЕ выдумывай."
)

TEXT_ONLY_PROMPT = (
    "\n--- ВАЖНО ---\n"
    "Ты генерируешь ТОЛЬКО описательный текст. Числовые данные (радиусы, расстояния, "
    "количество, ФИО, телефоны) подставляются системой отдельно.\n"
    "НЕ пиши конкретные цифры — описывай ХАРАКТЕР последствий без чисел.\n"
    "Примеры:\n"
    "- ПРАВИЛЬНО: «В зоне поражения возможны травмы персонала»\n"
    "- НЕПРАВИЛЬНО: «В радиусе 50 метров возможны травмы»\n"
)

SCENARIOS_TEXT_PROMPT = (
    "\n--- ОГРАНИЧЕНИЯ ---\n"
    "Опиши КАЖДЫЙ сценарий из списка выше. Для каждого сценария укажи:\n"
    "- Причину возникновения\n"
    "- Механизм развития аварии\n"
    "- Характер возможных последствий (БЕЗ чисел)\n"
    "- Методы локализации и ликвидации\n\n"
    "НЕ указывай радиусы, расстояния, количество пострадавших — это подставится системой.\n"
)

ACTIONS_TEXT_PROMPT = (
    "\n--- ОГРАНИЧЕНИЯ ---\n"
    "Опиши порядок действий при аварии. Для каждого действия укажи:\n"
    "- Конкретное действие\n"
    "- Кто отвечает (должность, не ФИО)\n"
    "- Сроки выполнения (если применимо)\n\n"
    "НЕ указывай телефоны, ФИО, адреса — это подставится системой из справочника.\n"
)


def build_section_prompt(
    section_title: str,
    facility_data: dict,
    substances: list[dict],
    equipment: list[dict],
    rag_context: str,
    responsible_persons: list[dict] | None = None,
    slot_type: str = "text",
    scenario_list: list[dict] | None = None,
    sample_context: dict | None = None,
) -> str:
    """
    Формирует промпт для генерации раздела.

    v2: Не передаёт расчётные данные в промпт.
    FACT-слоты заполняются кодом, LLM генерирует только текст.
    """

    substances_text = _format_list(substances, ["name", "quantity_kg"])
    equipment_text = _format_list(equipment, ["name", "equipment_type"])

    # Формируем список сценариев для промпта
    scenarios_text = ""
    if scenario_list:
        scenarios_text = "\n--- ВЫБРАННЫЕ СЦЕНАРИИ АВАРИЙ (из матрицы) ---\n"
        for s in scenario_list:
            scenarios_text += f"- {s['id']}: {s['name']} (тип фактора: {s['factor_type']}, вероятность: {s['probability']})\n"
        scenarios_text += "\nОпиши КАЖДЫЙ сценарий из списка выше.\n"

    # Добавляем ограничения в зависимости от раздела
    constraints = ""
    if "сценари" in section_title.lower():
        constraints = SCENARIOS_TEXT_PROMPT
    elif "действи" in section_title.lower() or "порядок" in section_title.lower():
        constraints = ACTIONS_TEXT_PROMPT

    # Формируем контекст из образцов
    sample_rag = ""
    few_shot = ""
    if sample_context:
        if sample_context.get("rag_context"):
            sample_rag = (
                "\n--- ФРАГМЕНТЫ ИЗ ОБРАЗЦОВ ПМЛА (для данного типа ОПО) ---\n"
                + sample_context["rag_context"]
                + "\n"
            )
        if sample_context.get("few_shot_example"):
            few_shot = (
                "\n--- ПРИМЕР ИЗ РЕАЛЬНОГО ПМЛА (для данного типа ОПО) ---\n"
                + sample_context["few_shot_example"]
                + "\nИспользуй этот пример как ориентир по стилю и содержанию, но не копируй дословно.\n"
            )

    return f"""
Раздел: {section_title}

--- ДАННЫЕ ОБ ОПО ---
Объект: {facility_data.get('name', '—')}
Тип: {facility_data.get('facility_type', '—')}
Класс опасности: {facility_data.get('hazard_class', '—')}
Адрес: {facility_data.get('address', '—')}

Опасные вещества:
{substances_text}

Оборудование:
{equipment_text}
{scenarios_text}

--- ФРАГМЕНТЫ ИЗ НОРМАТИВНОЙ БАЗЫ ---
{rag_context if rag_context else "Нормативные фрагменты не найдены."}
{sample_rag}
--- ЗАДАНИЕ ---
Напиши текст раздела «{section_title}» для данного ОПО.
Текст должен быть конкретным, ссылаться на указанное оборудование и вещества.
{TEXT_ONLY_PROMPT}
{constraints}
{few_shot}
"""


def build_scenario_list_prompt(
    facility_data: dict,
    substances: list[dict],
    equipment: list[dict],
) -> str:
    """
    Промпт для выбора сценариев из матрицы.
    Возвращает JSON со списком сценариев.
    """
    substances_text = _format_list(substances, ["name", "quantity_kg"])
    equipment_text = _format_list(equipment, ["name", "equipment_type"])

    return f"""
На основании характеристик объекта ОПО выбери подходящие сценарии аварий.

Объект: {facility_data.get('name', '—')}
Тип: {facility_data.get('facility_type', '—')}
Класс опасности: {facility_data.get('hazard_class', '—')}

Опасные вещества:
{substances_text}

Оборудование:
{equipment_text}

Верни JSON со списком подходящих сценариев:
[
  {{"id": "С-1", "name": "Название сценария", "factor_type": "Тип поражающего фактора", "probability": "высокая/средняя/низкая"}},
  ...
]

Максимум 5 сценариев. Выбирай наиболее вероятные для данного типа объекта.
"""


def _format_list(items: list[dict], fields: list[str]) -> str:
    """Форматирование списка объектов для промпта."""
    lines = []
    for item in items:
        parts = [str(item.get(f, "—")) for f in fields]
        lines.append(f"- {', '.join(parts)}")
    return "\n".join(lines) if lines else "Не указано"