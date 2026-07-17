"""Agent A: Parameterize scenario-related tables (6, 7, 9, 18).

Tables modified:
- Table 6: substance_params (Параметр | Значение)
- Table 7: equipment_scenario_links (equipment → scenario mapping)
- Table 9: accident_scenarios (С-1…С-6)
- Table 18: countermeasures (ПАЗ по сценариям)
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from agent_utils import (
    load_template_copy, save_agent_result, remove_rows,
    insert_loop_rows, check_sectpr, load_baseline, get_cell_text
)

AGENT_NAME = "agent_a_scenarios"


def modify_table_6(doc):
    """Table 6: substance_params — Параметр | Значение."""
    table = doc.tables[6]
    print(f"  Table 6: {len(table.rows)} rows")
    assert get_cell_text(table.rows[0].cells[0]).strip() == "Параметр", f"Unexpected header: {get_cell_text(table.rows[0].cells[0])}"
    remove_rows(table, 1, 8)  # 8 hardcoded params
    insert_loop_rows(table, 0,
        for_tag="{%tr for param in substance_params %}",
        field_tags=["{{ param.parameter }}", "{{ param.value }}"],
        endfor_tag="{%tr endfor %}")
    print(f"  -> Table 6: {len(table.rows)} rows after")


def modify_table_7(doc):
    """Table 7: equipment_scenario_links."""
    table = doc.tables[7]
    print(f"  Table 7: {len(table.rows)} rows")
    remove_rows(table, 1, 3)  # 3 hardcoded links
    insert_loop_rows(table, 0,
        for_tag="{%tr for link in equipment_scenario_links %}",
        field_tags=[
            "{{ loop.index }}",
            "{{ link.equipment_name }}",
            "{{ link.scenario_codes }}",
            "{{ link.description }}",
            "{{ link.damaging_factors }}",
        ],
        endfor_tag="{%tr endfor %}")
    print(f"  -> Table 7: {len(table.rows)} rows after")


def modify_table_9(doc):
    """Table 9: accident_scenarios — С-1…С-6."""
    table = doc.tables[9]
    print(f"  Table 9: {len(table.rows)} rows")
    remove_rows(table, 1, 6)  # 6 scenarios
    insert_loop_rows(table, 0,
        for_tag="{%tr for scenario in accident_scenarios %}",
        field_tags=[
            "{{ scenario.code }}",
            "{{ scenario.name }}",
            "{{ scenario.source }}",
            "{{ scenario.preconditions }}",
            "{{ scenario.signs }}",
            "{{ scenario.damaging_factors }}",
        ],
        endfor_tag="{%tr endfor %}")
    print(f"  -> Table 9: {len(table.rows)} rows after")


def modify_table_18(doc):
    """Table 18: countermeasures."""
    table = doc.tables[18]
    print(f"  Table 18: {len(table.rows)} rows")
    remove_rows(table, 1, 5)  # 5 scenario measures
    insert_loop_rows(table, 0,
        for_tag="{%tr for cm in countermeasures %}",
        field_tags=[
            "{{ cm.scenario_label }}",
            "{{ cm.signs }}",
            "{{ cm.protection }}",
            "{{ cm.technical_means }}",
            "{{ cm.executors }}",
        ],
        endfor_tag="{%tr endfor %}")
    print(f"  -> Table 18: {len(table.rows)} rows after")


def main():
    baseline = load_baseline()
    print(f"=== {AGENT_NAME} ===")
    print(f"Baseline: {baseline['total_sections']} sections, orientations: {baseline['orientations']}")

    doc = load_template_copy(AGENT_NAME)
    print(f"Loaded template: {len(doc.tables)} tables")

    modify_table_6(doc)
    modify_table_7(doc)
    modify_table_9(doc)
    modify_table_18(doc)

    # Verify sectPr
    assert check_sectpr(doc, baseline), "FAIL: sectPr baseline changed!"
    print("sectPr baseline: OK")

    out = save_agent_result(doc, AGENT_NAME)
    print(f"Saved: {out}")

    # Quick Jinja check
    jinja = 0
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                if "{{" in cell.text or "{%" in cell.text:
                    jinja += 1
    print(f"Jinja cells: {jinja}")
    print("DONE")


if __name__ == "__main__":
    main()
