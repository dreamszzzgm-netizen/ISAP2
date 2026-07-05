"""Базовый класс для расчётных методик."""
from abc import ABC, abstractmethod
from typing import Any


class BaseCalculation(ABC):
    """Базовый класс для всех расчётных методик."""

    @staticmethod
    @abstractmethod
    def calculate(params: Any) -> Any:
        """Выполнить расчёт."""
        pass

    @staticmethod
    def validate_range(value: float, min_val: float, max_val: float, name: str) -> str | None:
        """Проверка диапазона значения. Возвращает ошибку или None."""
        if value < min_val or value > max_val:
            return f"{name} = {value} вне диапазона [{min_val}, {max_val}]"
        return None

    @staticmethod
    def validate_positive(value: float, name: str) -> str | None:
        """Проверка положительного значения."""
        if value <= 0:
            return f"{name} должен быть положительным, получено: {value}"
        return None
