"""File parsers for Smart Import Center."""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ParsedTable:
    headers: list[str]
    rows: list[dict[str, Any]]


class SmartImportParser:
    """Parse Excel/CSV files into a flat table."""

    def parse_bytes(self, filename: str, content: bytes) -> ParsedTable:
        suffix = Path(filename).suffix.lower()
        if suffix in {".xlsx", ".xlsm"}:
            return self._parse_xlsx(content)
        if suffix in {".csv", ".txt"}:
            return self._parse_csv(content)
        raise ValueError("Поддерживаются только .xlsx, .xlsm, .csv, .txt")

    def _parse_csv(self, content: bytes) -> ParsedTable:
        text = content.decode("utf-8-sig")
        sample = text[:4096]
        dialect = csv.Sniffer().sniff(sample, delimiters=";,\t,") if sample.strip() else csv.excel
        reader = csv.DictReader(io.StringIO(text), dialect=dialect)
        headers = [str(header or "").strip() for header in (reader.fieldnames or [])]
        rows = [self._clean_row(row) for row in reader]
        return ParsedTable(headers=headers, rows=rows)

    def _parse_xlsx(self, content: bytes) -> ParsedTable:
        try:
            from openpyxl import load_workbook
        except ModuleNotFoundError as exc:
            raise RuntimeError("Для импорта Excel требуется openpyxl") from exc

        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        sheet = workbook.active
        rows_iter = sheet.iter_rows(values_only=True)
        header_values = next(rows_iter, None)
        if not header_values:
            return ParsedTable(headers=[], rows=[])
        headers = [str(value or "").strip() for value in header_values]
        rows: list[dict[str, Any]] = []
        for values in rows_iter:
            raw = {headers[i]: values[i] if i < len(values) else None for i in range(len(headers))}
            if any(value not in (None, "") for value in raw.values()):
                rows.append(self._clean_row(raw))
        return ParsedTable(headers=headers, rows=rows)

    @staticmethod
    def _clean_row(row: dict[str, Any]) -> dict[str, Any]:
        cleaned: dict[str, Any] = {}
        for key, value in row.items():
            if key is None:
                continue
            header = str(key).strip()
            if not header:
                continue
            cleaned[header] = value
        return cleaned
