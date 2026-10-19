#!/usr/bin/env python3
"""Enable A/B/C1 in the existing single localization browser.

A/B are source-bound ImageGen producers. C1 is text-only independent lightweight
QA. Native English C extraction remains an in-container background worker and is
not a ChatGPT browser slot.
"""
from __future__ import annotations
import argparse
import ast
from pathlib import Path

MARKER = "# OUTRUN_C1_SLOT_V2"

def replace_once(s: str, old: str, new: str, what: str) -> str:
    n = s.count(old)
    if n != 1:
        raise ValueError(f"{what}: expected one exact anchor, observed {n}")
    return s.replace(old, new, 1)

def patch(source: str) -> str:
    if MARKER in source:
        return source
    if "# OUTRUN_PNG_UPLOAD_V1" not in source:
        raise ValueError("C1 patch must run after PNG upload patch")
    s = source
    s = replace_once(
        s,
        'LOCALIZATION_SLOT_NAMES = ("A", "B")',
        'LOCALIZATION_SLOT_NAMES = ("A", "B", "C1")',
        "slot-list",
    )
    s = replace_once(
        s,
        'if CONTROLLER_MODE == "localization" and CHAT_SLOTS != 2:\n'
        '    raise ValueError("Recovery A/B mode requires CHAT_SLOTS=2")',
        'if CONTROLLER_MODE == "localization" and CHAT_SLOTS != 3:\n'
        '    raise ValueError("Recovery A/B/C1 mode requires CHAT_SLOTS=3")',
        "slot-count",
    )
    s = replace_once(
        s,
        'SCHEDULED_LOCALIZATION_LANES = {minute: ("A" if minute % 10 == 0 else "B") for minute in range(0, 60, 5)}',
        '''# OUTRUN_C1_SLOT_V2: current policy A :00, B :30, C1 :10/:40.
SCHEDULED_LOCALIZATION_LANES = {0: "A", 10: "C1", 30: "B", 40: "C1"}''',
        "schedule",
    )
    s = replace_once(
        s,
        'for retired_name in ("C1", "C2"):',
        'for retired_name in ("C2",):',
        "preserve-c1",
    )
    s = replace_once(
        s,
        'if CONTROLLER_MODE == "localization" and (_outrun_smoke_os.environ.get("OUTRUN_AB_BATCH_QUEUE", "").lower() == "true" or _outrun_smoke_os.environ.get("OUTRUN_AB_TEXT_ROI_QUEUE", "").lower() == "true"):',
        'if CONTROLLER_MODE == "localization" and slot.name in ("A", "B") and (_outrun_smoke_os.environ.get("OUTRUN_AB_BATCH_QUEUE", "").lower() == "true" or _outrun_smoke_os.environ.get("OUTRUN_AB_TEXT_ROI_QUEUE", "").lower() == "true"):',
        "ab-result-gate",
    )
    s = replace_once(
        s,
        '    if CONTROLLER_MODE == "localization" and slot.name not in ("A", "B"):\n'
        '        return\n'
        '    if CONTROLLER_MODE == "localization":\n'
        '        project_name = _outrun_smoke_os.environ.get("OUTRUN_AB_PROJECT_NAME", "").strip()',
        '    if CONTROLLER_MODE == "localization" and slot.name not in ("A", "B", "C1"):\n'
        '        return\n'
        '    if CONTROLLER_MODE == "localization" and slot.name in ("A", "B"):\n'
        '        project_name = _outrun_smoke_os.environ.get("OUTRUN_AB_PROJECT_NAME", "").strip()',
        "ab-producers",
    )
    s = replace_once(
        s,
        '''    else:
        png_binding = None
        send_result = await send_message(page, prompt)
    if send_result != "sent":''',
        '''    elif CONTROLLER_MODE == "localization" and slot.name == "C1":
        project_name = _outrun_smoke_os.environ.get("OUTRUN_AB_PROJECT_NAME", "").strip()
        if not project_name:
            slot.last_result = "C1_PROJECT_NOT_CONFIGURED"
            save_registry(reg)
            write_runtime(status="c1_project_hold", last_action="C1: no verified Korean project name")
            return
        target_status = await prepare_a_project_target(page, project_name, allow_saved_chat=False)
        if target_status != "A_PROJECT_COMPOSER_READY":
            slot.last_result = "C1_PROJECT_TARGET_BLOCKED:" + target_status
            save_registry(reg)
            write_runtime(status="c1_project_hold", last_action="C1: " + target_status)
            return
        # C1 is independent lightweight QA only. It never uploads producer
        # sources, invokes ImageGen, promotes DDS/game PASS, or consumes A/B state.
        png_binding = None
        send_result = await send_message(page, prompt)
    else:
        png_binding = None
        send_result = await send_message(page, prompt)
    if send_result != "sent":''',
        "c1-send",
    )
    s = MARKER + "\n" + s
    ast.parse(s)
    return s

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("controller", type=Path)
    args = ap.parse_args()
    old = args.controller.read_text(encoding="utf-8")
    new = patch(old)
    if new != old:
        args.controller.write_text(new, encoding="utf-8")
    print("OUTRUN_C1_SLOT_V2_PATCHED" if new != old else "OUTRUN_C1_SLOT_V2_ALREADY_PATCHED")

if __name__ == "__main__":
    main()
