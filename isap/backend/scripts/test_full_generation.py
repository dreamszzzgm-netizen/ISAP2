"""Полный тест генерации ПМЛА с LLM."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


async def test_full_generation():
    print("=" * 70)
    print("ПОЛНЫЙ ТЕСТ ГЕНЕРАЦИИ ПМЛА С LLM")
    print("=" * 70)

    from src.infrastructure.rag.structural_pipeline import StructuralSampleRetriever
    from src.application.services.structural_sample_integration import StructuralSampleIntegrationService
    from src.application.services.prompts import build_section_prompt, SYSTEM_PROMPT

    # Мок sample_repo
    class MockSampleRepo:
        pass

    service = StructuralSampleIntegrationService(MockSampleRepo())

    # Тестовый контекст объекта
    facility = {
        "name": "Газораспределительная станция «Северная»",
        "facility_type": "сеть газопотребления",
        "hazard_class": "III",
        "address": "г. Нальчик, ул. Ленина, 10",
    }

    substances = [
        {"name": "Метан", "quantity_kg": 5000},
        {"name": "Конденсат газовый", "quantity_kg": 200},
    ]

    equipment = [
        {"name": "ГРУ-1000", "equipment_type": "ГРУ"},
        {"name": "КС-500", "equipment_type": "компрессорная станция"},
    ]

    # Генерируем раздел 2 (Сценарии аварий)
    section_id = "section_2"
    section_title = "2. Сценарии наиболее вероятных аварий на ОПО"

    print(f"\nГенерация раздела: {section_title}")

    # Получаем контекст из образцов
    sample_context = await service.build_sample_context(
        section_id=section_id,
        section_title=section_title,
        facility_type="сеть газопотребления",
        hazard_class="III",
    )

    rag_len = len(sample_context.get("rag_context", ""))
    fewshot_len = len(sample_context.get("few_shot_example", ""))
    print(f"\nRAG контекст: {rag_len} символов")
    print(f"Few-shot: {fewshot_len} символов")

    # Формируем промпт
    prompt = build_section_prompt(
        section_title=section_title,
        facility_data=facility,
        substances=substances,
        equipment=equipment,
        rag_context=sample_context.get("rag_context", ""),
        responsible_persons=[],
        slot_type="mixed",
        scenario_list=None,
        sample_context=sample_context,
    )

    print(f"\nПромпт: {len(prompt)} символов")
    print("\n--- ПРОМПТ (первые 800 символов) ---")
    print(prompt[:800])
    print("...")

    # Вызов LLM
    print("\n--- ВЫЗОВ LLM ---")
    try:
        from src.infrastructure.llm.providers import OllamaProvider, LLMMessage

        llm = OllamaProvider()

        response = await llm.complete([
            LLMMessage(role="system", content=SYSTEM_PROMPT),
            LLMMessage(role="user", content=prompt),
        ])

        print(f"\n--- ОТВЕТ LLM ({len(response.content)} символов) ---")
        print(response.content[:1500])

    except Exception as e:
        print(f"\nОшибка LLM: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_full_generation())
