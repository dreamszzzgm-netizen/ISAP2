"""Agent C: Parameterize material reserve table (13).

Tables modified:
- Table 13: material_reserve (СИЗ, инструмент, оборудование с группировкой)
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from agent_utils import (
    load_template_copy, save_agent_result, remove_rows,
    insert_loop_rows, check_sectpr, load_baseline
)

AGENT_NAME = "agent_c_resources"


def modify_table_13(doc):
    """Table 13: material_reserve with group headers."""
    table = doc.tables[13]
    print(f"  Table 13: {len(table.rows)} rows")
    remove_rows(table, 1, 21)  # 21 data rows (groups + items)
    insert_loop_rows(table, 0,
        for_tag="{%tr for item in material_reserve %}",
        field_tags=[
            "{{ loop.index if not item.is_group_header else '' }}",
            "{{ item.group_name if item.is_group_header else item.name }}",
            "{{ '' if item.is_group_header else item.quantity }}",
            "{{ '' if item.is_group_header else item.location }}",
        ],
        endfor_tag="{%tr endfor %}")
    print(f"  -> Table 13: {len(table.rows)} rows after")


def main():
    baseline = load_baseline()
    print(f"=== {AGENT_NAME} ===")

    doc = load_template_copy(AGENT_NAME)
    print(f"Loaded: {len(doc.tables)} tables")

    modify_table_13(doc)

    assert check_sectpr(doc, baseline), "FAIL: sectPr changed!"
    print("sectPr: OK")

    out = save_agent_result(doc, AGENT_NAME)
    print(f"Saved: {out}")
    print("DONE")


if __name__ == "__main__":
    main()
