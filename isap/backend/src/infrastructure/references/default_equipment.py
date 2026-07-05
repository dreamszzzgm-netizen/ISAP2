"""Подбор базового перечня СИЗ/инструментов/материалов."""
import json
from pathlib import Path

from src.infrastructure.references.types import EquipmentItem, EquipmentList

DATA_FILE = Path(__file__).parent / "data" / "equipment.json"


class EquipmentListProvider:
    """Подбор базового перечня СИЗ/инструментов/материалов."""

    def __init__(self):
        self._lists: dict[str, EquipmentList] = {}
        self._load_data()

    def _load_data(self):
        if DATA_FILE.exists():
            data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
            for item in data:
                key = f"{item['facility_type']}_{item['hazard_class']}"
                items = [EquipmentItem(**i) for i in item.get("items", [])]
                self._lists[key] = EquipmentList(
                    facility_type=item["facility_type"],
                    hazard_class=item["hazard_class"],
                    items=items,
                )

    def get_defaults(
        self,
        facility_type: str,
        hazard_class: int,
    ) -> EquipmentList:
        """
        Получение перечня по умолчанию для типа ОПО и класса опасности.
        Если точное совпадение не найдено — ищем по типу объекта.
        """
        key = f"{facility_type}_{hazard_class}"
        if key in self._lists:
            return self._lists[key]

        # Ищем по типу объекта (любой класс опасности)
        for k, v in self._lists.items():
            if v.facility_type == facility_type:
                return v

        # Возвращаем общий перечень
        return EquipmentList(
            facility_type=facility_type,
            hazard_class=hazard_class,
            items=[
                EquipmentItem(name="Огнетушитель углекислотный ОУ-5", category="СИЗ", quantity=2),
                EquipmentItem(name="Аптечка первичной помощи", category="СИЗ", quantity=1),
                EquipmentItem(name="Средства связи (рация)", category="инструмент", quantity=2),
                EquipmentItem(name="Противогаз фильтрующий", category="СИЗ", quantity=5),
            ],
        )
