"""Agent D: Parameterize notification list phones (Table 17).

Tables modified:
- Table 17: notification phones (scalar placeholders for merged-cell table)
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from agent_utils import (
    load_template_copy, save_agent_result, check_sectpr, load_baseline
)

AGENT_NAME = "agent_d_forces"

# Phone number replacements: old hardcoded -> Jinja2 placeholder
PHONE_MAP = {
    "+7 928 709-95-15": "{{ notification_chairman_phone | default('', true) }}",
    "+ 7 906 881-07-07": "{{ notification_deputy_phone | default('', true) }}",
    "112 | +7 (86630) 4-00-06": "{{ notification_edds_phone | default('112', true) }}",
    "+7 (903) 495-75-57 | +7 (903) 491-85-75": "{{ notification_pasf_phone | default('', true) }}",
    "+7(8663) 04-14-91": "{{ notification_fire_phone | default('', true) }}",
    "112/03/103": "{{ notification_ambulance_phone | default('112/03/103', true) }}",
    "+7 (86630) 4-18-68; | 4-18-53": "{{ notification_gas_phone | default('', true) }}",
    "+7  (86630) 4-27-70": "{{ notification_electric_phone | default('', true) }}",
    "+7 (8662) 39-99-99": "{{ notification_mchs_phone | default('', true) }}",
    "+7 (928) 307-04-62 | +7 (8793)-34-64-24 | +7 (8662) 91-99-33": "{{ notification_rostechnadzor_phone | default('', true) }}",
    "+7 (86630) 7-63-99": "{{ notification_admin_phone | default('', true) }}",
}


def modify_table_17(doc):
    """Table 17: Replace hardcoded phone numbers with placeholders."""
    table = doc.tables[17]
    print(f"  Table 17: {len(table.rows)} rows")

    replaced = 0
    for row in table.rows:
        for cell in row.cells:
            for para in cell.paragraphs:
                for run in list(para.runs):
                    original = run.text
                    modified = original
                    for old, new in PHONE_MAP.items():
                        if old in modified:
                            modified = modified.replace(old, new)
                    if modified != original:
                        run.text = modified
                        replaced += 1

    print(f"  -> Replaced {replaced} phone entries")


def main():
    baseline = load_baseline()
    print(f"=== {AGENT_NAME} ===")

    doc = load_template_copy(AGENT_NAME)
    print(f"Loaded: {len(doc.tables)} tables")

    modify_table_17(doc)

    assert check_sectpr(doc, baseline), "FAIL: sectPr changed!"
    print("sectPr: OK")

    out = save_agent_result(doc, AGENT_NAME)
    print(f"Saved: {out}")
    print("DONE")


if __name__ == "__main__":
    main()
