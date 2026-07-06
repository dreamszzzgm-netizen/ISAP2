from typing import Any, Callable

from src.application.services.calculations.types import CalculationResult


class CalculationRegistry:
    """Реестр расчётных методик. Привязка method_id → функция."""

    _methods: dict[str, dict[str, Any]] = {}

    @classmethod
    def register(
        cls,
        method_id: str,
        func: Callable,
        title: str,
        regulatory_doc_id: str | None = None,
    ):
        cls._methods[method_id] = {
            "func": func,
            "title": title,
            "regulatory_doc_id": regulatory_doc_id,
        }

    @classmethod
    def calculate(cls, method_id: str, params: Any) -> CalculationResult:
        if method_id not in cls._methods:
            raise ValueError(
                f"Методика '{method_id}' не зарегистрирована. "
                f"Доступные: {list(cls._methods.keys())}"
            )

        method = cls._methods[method_id]
        func = method["func"]
        result = func(params)

        return CalculationResult(
            method_id=method_id,
            input_params=_to_dict(params),
            results=_to_dict(result),
            validation_status="valid",
            warnings=getattr(result, "warnings", []),
        )

    @classmethod
    def get_method_info(cls, method_id: str) -> dict[str, Any] | None:
        if method_id not in cls._methods:
            return None
        method = cls._methods[method_id]
        return {
            "method_id": method_id,
            "title": method["title"],
            "regulatory_doc_id": method["regulatory_doc_id"],
        }

    @classmethod
    def list_methods(cls) -> list[dict[str, Any]]:
        return [
            {
                "method_id": mid,
                "title": m["title"],
                "regulatory_doc_id": m["regulatory_doc_id"],
            }
            for mid, m in cls._methods.items()
        ]


def _to_dict(obj: Any) -> dict:
    """Конвертирует dataclass в dict."""
    if hasattr(obj, "__dataclass_fields__"):
        return {k: getattr(obj, k) for k in obj.__dataclass_fields__}
    if isinstance(obj, dict):
        return obj
    return {"value": obj}
