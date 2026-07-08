"""Helpers for capturing regulatory document state."""
from __future__ import annotations

import inspect
from typing import Any

from sqlalchemy import select

from src.infrastructure.database.models import RegulatoryDocumentModel


async def _resolve(value: Any) -> Any:
    """Resolve awaitables returned by async sessions or test doubles."""
    if inspect.isawaitable(value):
        return await value
    return value


async def collect_regulatory_snapshot(session: Any) -> list[dict[str, Any]]:
    """Return a serializable snapshot of active regulatory documents."""
    if session is None or not hasattr(session, "execute"):
        return []

    try:
        result = await _resolve(
            session.execute(
                select(RegulatoryDocumentModel).where(
                    RegulatoryDocumentModel.status == "действует"
                )
            )
        )
        scalars = await _resolve(result.scalars())
        documents = await _resolve(scalars.all())
    except Exception:
        return []

    snapshot: list[dict[str, Any]] = []
    for document in documents:
        snapshot.append(
            {
                "id": str(document.id),
                "title": document.title,
                "category": document.category,
                "status": document.status,
                "replacement_id": (
                    str(document.replacement_id) if document.replacement_id else None
                ),
                "last_verified_at": (
                    document.last_verified_at.isoformat()
                    if document.last_verified_at
                    else None
                ),
            }
        )
    return snapshot
