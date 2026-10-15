#!/usr/bin/env python3
"""Enable C-SALVAGE as a third ChatGPT tab IN THE EXISTING A/B controller image.

Runs only at Docker build time *after* patch_controller_png_upload.py.
Keeps A/B queues, existing checkpoint URLs and ImageGen attachments unchanged.
C is a text-only worker in the same existing Korean localization ChatGPT project.
No new Docker service and no runtime hot patch.
"""
from __future__ import annotations
import argparse
import ast
from pathlib import Path

MARKER = "# OUTRUN_C_SLOT_V1"

def replace_once(s, original, new, what):
    n = s.count(original)
    if n != 1:
        raise ValueError(f"{what}: expected one exact anchor, observed {n}; abort build")
    return s.replace(original,new,1)

def patch(source):
    if MARKER in source:
        return source
    if "# OUTRUN_PNG_UPLOAD_V1" not in source:
        raise ValueError("C patch must run AFTER existing pinned A/B PNG upload patch")
    s=source
    s=replace_once(s,
        'LOCALIZATION_SLOT_NAMES = ("A", "B")',
        'LOCALIZATION_SLOT_NAMES = ("A", "B", "C")',
        "active-tab-list")
    s=replace_once(s,
        'if CONTROLLER_MODE == "localization" and CHAT_SLOTS != 2:\n'
        '    raise ValueError("Recovery A/B mode requires CHAT_SLOTS=2")',
        'if CONTROLLER_MODE == "localization" and CHAT_SLOTS != 3:\n'
        '    raise ValueError("Recovery A/B/C mode requires CHAT_SLOTS=3")',
        "tab-count-guard")
    s=replace_once(s,
        'SCHEDULED_LOCALIZATION_LANES = {minute: ("A" if minute % 10 == 0 else "B") for minute in range(0, 60, 5)}',
        '''# OUTRUN_C_SLOT_V1: preserve all twelve previous A/B time slots.
SCHEDULED_LOCALIZATION_LANES = {minute: ("A" if minute % 10 == 0 else "B") for minute in range(0, 60, 5)}
SCHEDULED_LOCALIZATION_LANES.update({3: "C", 33: "C"})''',
        "minute-to-role")
    s=replace_once(s,
        '''        if "C" in existing:
            if "C1" in existing:
                raise ValueError("Conflicting legacy C and C1 checkpoint: preserve for manual review")
            existing["C"].name = "C1"
            existing["C1"] = existing.pop("C")
            changed = True
''',
        '''        # In A/B/C mode C is a live producer tab, not the old C1 reviewer.
        # Existing A/B URLs remain intact. Legacy C1/C2 are archived by the
        # existing migration block below, never silently sent as C.
''',
        "c-is-not-retired-c1")
    s=replace_once(s,
        'if CONTROLLER_MODE == "localization" and _outrun_smoke_os.environ.get("OUTRUN_AB_BATCH_QUEUE", "").lower() == "true":',
        'if CONTROLLER_MODE == "localization" and slot.name in ("A", "B") and _outrun_smoke_os.environ.get("OUTRUN_AB_BATCH_QUEUE", "").lower() == "true":',
        "ab-library-result-gate-only-ab")
    s=replace_once(s,
        '    if CONTROLLER_MODE == "localization" and slot.name not in ("A", "B"):\n'
        '        return\n'
        '    if CONTROLLER_MODE == "localization":\n'
        '        project_name = _outrun_smoke_os.environ.get("OUTRUN_AB_PROJECT_NAME", "").strip()',
        '    if CONTROLLER_MODE == "localization" and slot.name not in ("A", "B", "C"):\n'
        '        return\n'
        '    if CONTROLLER_MODE == "localization" and slot.name in ("A", "B"):\n'
        '        project_name = _outrun_smoke_os.environ.get("OUTRUN_AB_PROJECT_NAME", "").strip()',
        "source-bound-ab-producers-preserved")
    s=replace_once(s,
        '''    else:
        png_binding = None
        send_result = await send_message(page, prompt)
    if send_result != "sent":''',
        '''    elif CONTROLLER_MODE == "localization" and slot.name == "C":
        # The existing Korean localization project is the destination.
        # Never use VR_PROJECT_URL or choose an unverified different project.
        project_name = _outrun_smoke_os.environ.get("OUTRUN_AB_PROJECT_NAME", "").strip()
        if not project_name:
            slot.last_result = "C_PROJECT_NOT_CONFIGURED"
            save_registry(reg)
            write_runtime(status="c_project_hold", last_action="C: no verified Korean project name")
            return
        target_status = await prepare_a_project_target(page, project_name, allow_saved_chat=False)
        if target_status != "A_PROJECT_COMPOSER_READY":
            slot.last_result = "C_PROJECT_TARGET_BLOCKED:" + target_status
            save_registry(reg)
            write_runtime(status="c_project_hold",last_action="C: " + target_status)
            return
        # Text-only C-SALVAGE. No Create image pill, PNG upload, ImageGen
        # batch state transition, C1 auto-PASS, or independent approval.
        png_binding = None
        send_result = await send_message(page, prompt)
    else:
        png_binding = None
        send_result = await send_message(page, prompt)
    if send_result != "sent":''',
        "c-text-only-same-project")
    ast.parse(s)
    return s

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("controller",type=Path)
    args=parser.parse_args()
    old=args.controller.read_text(encoding="utf-8")
    new=patch(old)
    if new!=old:
        args.controller.write_text(new,encoding="utf-8")
    print("OUTRUN_C_SLOT_V1_PATCHED" if new!=old else "OUTRUN_C_SLOT_V1_ALREADY_PATCHED")

if __name__=="__main__":
    main()