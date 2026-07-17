"""Agent B: Parameterize incident history tables (10, 11).

Tables modified:
- Table 10: injury_history (Характеристика травматизма)
- Table 11: accident_history (Происшедшие аварии)
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from agent_utils import (
    load_template_copy, save_agent_result, remove_rows,
    insert_loop_rows, check_sectpr, load_baseline
)

AGENT_NAME = "agent_b_incidents"


def modify_table_10(doc):
    """Table 10: injury_history."""
    table = doc.tables[10]
    print(f"  Table 10: {len(table.rows)} rows")
    remove_rows(table, 1, 5)  # 5 year rows (2022-2026)
    insert_loop_rows(table, 0,
        for_tag="{%tr for injury in injury_history %}",
        field_tags=[
            "{{ injury.year }}",
            "{{ injury.incident_number }}",
            "{{ injury.date }}",
            "{{ injury.character }}",
            "{{ injury.trauma }}",
            "{{ injury.consequences }}",
            "{{ injury.measures_percent }}",
        ],
        endfor_tag="{%tr endfor %}")
    print(f"  -> Table 10: {len(table.rows)} rows after")


def modify_table_11(doc):
    """Table 11: accident_history."""
    table = doc.tables[11]
    print(f"  Table 11: {len(table.rows)} rows")
    remove_rows(table, 1, 5)  # 5 year rows
    insert_loop_rows(table, 0,
        for_tag="{%tr for accident in accident_history %}",
        field_tags=[
            "{{ accident.year }}",
            "{{ accident.incident_number }}",
            "{{ accident.date }}",
            "{{ accident.character }}",
            "{{ accident.trauma }}",
            "{{ accident.consequences }}",
            "{{ accident.measures_percent }}",
        ],
        endfor_tag="{%tr endfor %}")
    print(f"  -> Table 11: {len(table.rows)} rows after")


def main():
    baseline = load_baseline()
    print(f"=== {AGENT_NAME} ===")

    doc = load_template_copy(AGENT_NAME)
    print(f"Loaded: {len(doc.tables)} tables")

    modify_table_10(doc)
    modify_table_11(doc)

    assert check_sectpr(doc, baseline), "FAIL: sectPr changed!"
    print("sectPr: OK")

    out = save_agent_result(doc, AGENT_NAME)
    print(f"Saved: {out}")
    print("DONE")


if __name__ == "__main__":
    main()
