"""
Тесты для проверки, что персональные данные не уходят во внешний LLM.

Запуск: pytest test_document_generator.py -v
Зависимости: pip install pytest pytest-asyncio --break-system-packages
"""
import re
import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from document_generator import (
    DocumentGenerator,
    strip_pii,
    PiiRoutingError,
)


# ---------------------------------------------------------------------------
# Уровень 1: unit-тесты strip_pii по именам полей (быстрые, но не панацея —
# см. TestContentLeakByPattern ниже, это более надёжная проверка)
# ---------------------------------------------------------------------------

class Person:
    def __init__(self, full_name, phone, position):
        self.full_name = full_name
        self.phone = phone
        self.position = position


def test_strip_pii_removes_known_fields_from_dict():
    data = {"full_name": "Иванов Иван Иванович", "phone": "+79001234567", "position": "Председатель"}
    cleaned = strip_pii(data)
    assert cleaned["full_name"] == "[скрыто]"
    assert cleaned["phone"] == "[скрыто]"
    assert cleaned["position"] == "Председатель"  # бизнес-поле остаётся


def test_strip_pii_removes_known_fields_from_object():
    p = Person("Петров Пётр Петрович", "+79007654321", "Инженер")
    cleaned = strip_pii(p)
    assert cleaned["full_name"] == "[скрыто]"
    assert cleaned["phone"] == "[скрыто]"


def test_strip_pii_handles_nested_lists():
    context = {"responsible_persons": [Person("Сидоров С.С.", "89001112233", "Диспетчер")]}
    cleaned = strip_pii(context)
    assert cleaned["responsible_persons"][0]["full_name"] == "[скрыто]"


def test_strip_pii_does_not_mutate_original():
    original = {"full_name": "Иванов Иван Иванович"}
    strip_pii(original)
    assert original["full_name"] == "Иванов Иван Иванович"  # исходный context не тронут


# ---------------------------------------------------------------------------
# Уровень 2 (ГЛАВНЫЙ): проверка по содержимому, а не по имени поля.
# Ловит утечку, даже если реальное поле в вашей БД называется не так,
# как в захардкоженном PII_FIELD_NAMES.
# ---------------------------------------------------------------------------

PHONE_RE = re.compile(r"(\+7|8)[\s\-\(]?\d{3}[\s\-\)]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}")
# Простой эвристический паттерн ФИО: три слова с заглавной буквы подряд
FIO_RE = re.compile(r"\b[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+\b")


def assert_no_pii_leak(payload: dict | str, forbidden_values: list[str]):
    """
    payload — то, что реально было бы отправлено во внешний LLM (например,
    аргументы вызова provider.complete(...)).
    forbidden_values — реальные ФИО/телефоны из тестовых данных, которые
    НЕ должны встретиться в payload ни в каком виде.
    """
    text = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)

    for value in forbidden_values:
        assert value not in text, f"Утечка персональных данных: '{value}' найдено в промпте внешнего LLM"

    phone_matches = PHONE_RE.findall(text)
    assert not phone_matches, f"В промпте внешнего LLM найден номер телефона: {phone_matches}"

    fio_matches = FIO_RE.findall(text)
    assert not fio_matches, f"В промпте внешнего LLM найдено похожее на ФИО значение: {fio_matches}"


@pytest.mark.asyncio
async def test_pii_section_never_reaches_external_llm():
    """
    Главный тест: гоняем DocumentGenerator целиком (с моками) на секции
    pii=true и проверяем, что local_llm получил запрос, а external_llm —
    вообще не вызывался.
    """
    local_llm = AsyncMock()
    local_llm.complete.return_value = MagicMock(content="Текст раздела с ФИО")

    external_llm = AsyncMock()  # не должен быть вызван вообще

    retriever = AsyncMock()
    retriever.retrieve.return_value = []

    generator = DocumentGenerator(local_llm=local_llm, external_llm=external_llm, retriever=retriever)

    # Подменяем загрузку structure.json на одну pii-секцию
    generator._load_structure = MagicMock(return_value={
        "title": "Тест",
        "sections": [{
            "title": "Список оповещения",
            "template": "dummy.j2",  # см. примечание ниже про jinja_env в реальном тесте
            "content_type": "llm",
            "pii": True,
            "rag_query": "",
        }],
    })

    context = {
        "responsible_persons": [Person("Иванов Иван Иванович", "+79991234567", "Председатель")],
        "facility": {"facility_type": "Сеть газопотребления", "hazard_class": "III"},
        "organization": {"name": "СПК ААА"},
        "substances": [], "equipment": [],
    }

    # _render_template и _build_docx не критичны для этого теста — мокаем,
    # чтобы не тянуть реальные jinja-шаблоны
    generator._render_template = MagicMock(return_value="ok")
    generator._build_docx = MagicMock(return_value=b"docx-bytes")

    await generator.generate("pmla", context)

    local_llm.complete.assert_called_once()
    external_llm.complete.assert_not_called()

    # И главное — смотрим, что реально было в промпте, отправленном в local_llm
    sent_messages = local_llm.complete.call_args.kwargs["messages"]
    sent_text = " ".join(m.content for m in sent_messages)
    # для local_llm ФИО и телефон МОГУТ быть — это ожидаемо и безопасно (не покидает сеть)
    assert "СПК ААА" in sent_text


@pytest.mark.asyncio
async def test_non_pii_section_scrubs_context_before_external_llm():
    """
    Секция без pii=true должна идти в external_llm, но с уже вычищенным
    контекстом — реальные ФИО/телефон не должны попасть в промпт.
    """
    local_llm = AsyncMock()  # не должен быть вызван
    external_llm = AsyncMock()
    external_llm.complete.return_value = MagicMock(content="Общий текст раздела")

    retriever = AsyncMock()
    retriever.retrieve.return_value = []

    generator = DocumentGenerator(local_llm=local_llm, external_llm=external_llm, retriever=retriever)

    generator._load_structure = MagicMock(return_value={
        "title": "Тест",
        "sections": [{
            "title": "Характеристика объекта",
            "template": "dummy.j2",
            "content_type": "llm",
            "pii": False,
            "rag_query": "",
        }],
    })

    real_fio = "Иванов Иван Иванович"
    real_phone = "+79991234567"
    context = {
        "responsible_persons": [Person(real_fio, real_phone, "Председатель")],
        "facility": {"facility_type": "Сеть газопотребления", "hazard_class": "III"},
        "organization": {"name": "СПК ААА"},
        "substances": [], "equipment": [],
    }

    generator._render_template = MagicMock(return_value="ok")
    generator._build_docx = MagicMock(return_value=b"docx-bytes")

    await generator.generate("pmla", context)

    external_llm.complete.assert_called_once()
    local_llm.complete.assert_not_called()

    sent_messages = external_llm.complete.call_args.kwargs["messages"]
    sent_payload = {"messages": [m.content for m in sent_messages]}

    # бизнес-данные должны остаться (иначе LLM не сможет писать текст по делу)
    assert "СПК ААА" in json.dumps(sent_payload, ensure_ascii=False)
    # а вот персональные — не должны
    assert_no_pii_leak(sent_payload, forbidden_values=[real_fio, real_phone])


def test_pii_section_without_local_llm_raises_instead_of_silent_fallback():
    """
    Если pii=true, а local_llm не настроен (None) — должна быть явная ошибка,
    а не тихий уход в external_llm.
    """
    import asyncio

    generator = DocumentGenerator(local_llm=None, external_llm=AsyncMock(), retriever=AsyncMock())
    generator._load_structure = MagicMock(return_value={
        "title": "Тест",
        "sections": [{"title": "Оповещение", "template": "x.j2", "content_type": "llm", "pii": True, "rag_query": ""}],
    })

    with pytest.raises(PiiRoutingError):
        asyncio.run(generator.generate("pmla", {"facility": {}, "organization": {}}))