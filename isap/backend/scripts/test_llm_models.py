"""
Сравнение LLM-моделей для генерации ПМЛА.

Запуск:
    cd backend
    python -m scripts.test_llm_models

Тестирует доступные модели на одном и том же промпте и выводит таблицу сравнения.
"""
import asyncio
import time

from src.infrastructure.llm.providers import (
    OllamaProvider,
    OpenAIProvider,
    LLMMessage,
)
from src.application.services.prompts import SYSTEM_PROMPT, build_section_prompt


# Тестовый контекст ОПО
TEST_FACILITY = {
    "name": "Сеть газопотребления Хлебозавода №2",
    "facility_type": "Сеть газопотребления",
    "hazard_class": 3,
    "address": "г. Якутск, ул. Очичкенко, д.17",
}

TEST_SUBSTANCES = [
    {"name": "Природный газ (метан)", "quantity_kg": 800}
]

TEST_EQUIPMENT = [
    {"name": "Подводящий газопровод высокого давления", "equipment_type": "Газопровод"},
    {"name": "Водогрейный котёл ROSSEN RSD 1000", "equipment_type": "Котёл"},
]

TEST_PERSONS = [
    {"full_name": "Иванова С.Т.", "position": "Директор", "phone": "+7 (4112) 43-33-01"}
]

TEST_CALC = {
    "tnt_equivalent_метан": "1250 кг ТНТ",
    "thermal_radiation_метан": "350 м",
}

# Модели для тестирования
MODELS = [
    ("ollama", "llama3:8b"),
    ("ollama", "qwen2.5:14b"),
]


def _build_test_prompt() -> str:
    """Собирает тестовый промпт для раздела «Сценарии аварий»."""
    return build_section_prompt(
        section_title="Сценарии аварий",
        facility_data=TEST_FACILITY,
        substances=TEST_SUBSTANCES,
        equipment=TEST_EQUIPMENT,
        rag_context="Газопровод высокого давления подвержен риску разгерметизации. "
                    "Котёл ROSSEN RSD 1000 требует постоянного контроля давления.",
        calculation_placeholders=TEST_CALC,
        responsible_persons=TEST_PERSONS,
    )


def _create_provider(provider_type: str):
    """Создаёт провайдер без fallback."""
    if provider_type == "openai":
        return OpenAIProvider()
    return OllamaProvider()


async def test_model(provider_type: str, model_name: str) -> dict:
    """Тестирует одну модель и возвращает результат."""
    provider = _create_provider(provider_type)
    user_prompt = _build_test_prompt()
    messages = [
        LLMMessage(role="system", content=SYSTEM_PROMPT),
        LLMMessage(role="user", content=user_prompt),
    ]

    print(f"\n{'='*60}")
    print(f"Тестирую: {provider_type}/{model_name}")
    print(f"{'='*60}")

    start = time.perf_counter()
    try:
        response = await provider.complete(
            messages=messages,
            temperature=0.2,
            max_tokens=2048,
        )
        elapsed = time.perf_counter() - start

        # Подсчёт статистики
        content = response.content
        word_count = len(content.split())
        has_calculated = "[CALCULATED:" in content
        has_english = any(w.isascii() and w.isalpha() and len(w) > 3 for w in content.split())

        print(f"Время: {elapsed:.1f}с")
        print(f"Токены: prompt={response.prompt_tokens}, completion={response.completion_tokens}")
        print(f"Слов: {word_count}")
        print(f"Содержит [CALCULATED:...]: {'ДА ⚠️' if has_calculated else 'нет'}")
        print(f"Английские слова >3 символов: {'ДА ⚠️' if has_english else 'нет'}")
        print(f"\n--- Фрагмент ответа (первые 500 символов) ---")
        print(content[:500])

        return {
            "model": f"{provider_type}/{model_name}",
            "status": "ok",
            "time_s": round(elapsed, 1),
            "prompt_tokens": response.prompt_tokens,
            "completion_tokens": response.completion_tokens,
            "word_count": word_count,
            "has_calculated_leak": has_calculated,
            "has_english_words": has_english,
            "sample": content[:300],
        }
    except Exception as e:
        elapsed = time.perf_counter() - start
        print(f"ОШИБКА: {e}")
        return {
            "model": f"{provider_type}/{model_name}",
            "status": "error",
            "time_s": round(elapsed, 1),
            "error": str(e),
        }


async def main():
    print("=" * 60)
    print("Сравнение LLM-моделей для генерации ПМЛА")
    print("=" * 60)

    results = []
    for provider_type, model_name in MODELS:
        result = await test_model(provider_type, model_name)
        results.append(result)

    # Итоговая таблица
    print("\n\n" + "=" * 60)
    print("ИТОГОВАЯ ТАБЛИЦА")
    print("=" * 60)
    print(f"{'Модель':<30} {'Статус':<10} {'Время':<8} {'Слов':<8} {'CALC leak':<10} {'English':<10}")
    print("-" * 76)
    for r in results:
        if r["status"] == "ok":
            print(
                f"{r['model']:<30} {'OK':<10} {r['time_s']:<8} {r['word_count']:<8} "
                f"{'⚠️ ДА' if r['has_calculated_leak'] else 'нет':<10} "
                f"{'⚠️ ДА' if r['has_english_words'] else 'нет':<10}"
            )
        else:
            print(f"{r['model']:<30} {'ОШИБКА':<10} {r['time_s']:<8} {r.get('error', '')[:30]}")


if __name__ == "__main__":
    asyncio.run(main())
