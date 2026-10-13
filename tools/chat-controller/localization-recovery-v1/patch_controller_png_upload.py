"""Patch the pinned Portainer base controller at Docker build time, never live.

Hard-fail when the expected older source anchors change. The backup base image
remains untouched. Running this patch twice is idempotent.
"""
import argparse
import ast
from pathlib import Path


def replace_once(source, old, new, label):
    count = source.count(old)
    if count != 1:
        raise ValueError(f"{label}: expected exactly one anchor, found {count}")
    return source.replace(old, new, 1)


def patch(source):
    if "# OUTRUN_PNG_UPLOAD_V1" in source:
        return source
    source = replace_once(
        source,
        'LOCALIZATION_SLOT_NAMES = ("A", "B", "C1", "C2")',
        'LOCALIZATION_SLOT_NAMES = ("A",)',
        "role-tab-list",
    )
    source = replace_once(
        source,
        'if CONTROLLER_MODE == "localization" and CHAT_SLOTS != 4:\n'
        '    raise ValueError("Recovery localization requires CHAT_SLOTS=4 (A/B/C1/C2)")',
        'if CONTROLLER_MODE == "localization" and CHAT_SLOTS != 1:\n'
        '    raise ValueError("Recovery A-only mode requires CHAT_SLOTS=1")',
        "slot-count",
    )
    source = replace_once(
        source,
        'SCHEDULED_LOCALIZATION_LANES = {0: "A", 10: "C1", 20: "C2",\n'
        '                                30: "B", 40: "C1", 50: "C2"}',
        '''SCHEDULED_LOCALIZATION_LANES = {minute: "A" for minute in range(0, 60, 10)}
# A-only source-folder testing: manifest selects any valid A task ID.
OUTRUN_A_SINGLE_SMOKE_TASK_ID = _outrun_smoke_os.environ.get("OUTRUN_A_SINGLE_SMOKE_TASK_ID", "").strip()''',
        "minute-role-schedule",
    )
    source = replace_once(
        source,
        '        unexpected = set(existing) - set(LOCALIZATION_SLOT_NAMES)',
        '''        # Back up all inactive lanes before dropping their live registry slots.
        # Never overwrite a different historical record without operator review.
        for retired_name in ("B", "C1", "C2"):
            if retired_name not in existing:
                continue
            retired = STATE_DIR / ("retired_" + retired_name + "_slot_before_a_only_20261013.json")
            payload = json.dumps(asdict(existing[retired_name]), ensure_ascii=False, indent=2)
            if retired.exists():
                if retired.read_text(encoding="utf-8") != payload:
                    raise ValueError("Conflicting retired slot backup: " + str(retired))
            else:
                retired.write_text(payload, encoding="utf-8")
            del existing[retired_name]
            changed = True
        unexpected = set(existing) - set(LOCALIZATION_SLOT_NAMES)''',
        "retired-c2-checkpoint",
    )
    source = replace_once(
        source,
        'async def send_message(page: Page, message: str) -> str:\n'
        '    """Insert and send a prompt, returning the exact stage result for diagnostics."""\n'
        '    box = await first_visible(page, INPUT_SELECTORS)',
        '''async def send_message(page: Page, message: str, png_binding=None) -> str:
    """Send the source PNG first; never submit a text-only ImageGen producer task."""
    if png_binding is not None:
        tool_status = await ensure_image_tool(page)
        if tool_status != "CREATE_IMAGE_TOOL_SELECTED":
            return "IMAGE_TOOL_NOT_SELECTED:" + tool_status
        status = await attach_png(page, png_binding)
        if status != "ATTACHMENT_UPLOAD_COMPLETED":
            log.error("PNG composer attachment not proven role=%s status=%s",
                      png_binding["role"], status)
            return "SOURCE_REFERENCE_NOT_BOUND:" + status
    if png_binding is not None:
        message += "\\n\\nUPLOAD_TASK_ID=" + png_binding["task_id"] + " (추적용 ID이며 이미지에 표시하지 마세요)"
    box = await first_visible(page, INPUT_SELECTORS)''',
        "composer-attachment-send",
    )
    source = replace_once(
        source,
        '        prompt = prompt_for_slot(slot, "watchdog")',
        '''        # The watchdog must never silently send a producer text-only prompt.
        # A/B are single-asset source-bound jobs; only the explicit scheduler sends.
        if CONTROLLER_MODE == "localization":
            continue
        prompt = prompt_for_slot(slot, "watchdog")''',
        "producer-watchdog",
    )
    source = replace_once(
        source,
        '    send_result = await send_message(page, prompt)\n'
        '    if send_result != "sent":',
        '''    # No automatic upload without an explicit destination.
    if CONTROLLER_MODE == "localization" and slot.name == "A":
        if not slot.url and not _outrun_smoke_os.environ.get("OUTRUN_A_PROJECT_NAME", "").strip():
            slot.last_result = "NO_TARGET_CHAT_URL"
            save_registry(reg)
            write_runtime(status="target_missing",
                          last_action="A upload blocked: no saved chat URL or project target")
            return
    # OUTRUN_PNG_UPLOAD_V1: per-role SHA-pinned source manifest, fail closed.
    if CONTROLLER_MODE == "localization" and slot.name == "A":
        target_status = await prepare_a_project_target(
            page, _outrun_smoke_os.environ.get("OUTRUN_A_PROJECT_NAME", "").strip(),
            allow_saved_chat=bool(slot.url))
        if target_status != "A_PROJECT_COMPOSER_READY":
            slot.last_result = "PROJECT_TARGET_BLOCKED:" + target_status
            save_registry(reg)
            write_runtime(status="project_target_blocked",
                          last_action="A source withheld: " + target_status)
            return
    # Any non-A task is prohibited regardless of the pilot task ID.
    if CONTROLLER_MODE == "localization" and slot.name != "A":
        return
    if CONTROLLER_MODE == "localization" and slot.name == "A" and _outrun_smoke_os.environ.get("OUTRUN_A_TILE_BATCH_QUEUE", "").lower() == "true":
        result_probe = await confirm_visible_results(page, "/data/imagegen")
        log.info("A batch result probe: %s", result_probe)
    png_binding = None
    if CONTROLLER_MODE == "localization" and slot.name == "A":
        png_binding, png_reason = load_binding(slot.name)
        if png_reason is not None:
            send_result = "SOURCE_REFERENCE_NOT_BOUND:" + png_reason
        else:
            send_result = await send_message(page, png_binding["prompt"], png_binding)
    else:
        send_result = await send_message(page, prompt)
    if send_result == "sent" and png_binding is not None:
        mark_sent(png_binding)
    elif send_result == "SEND_UNVERIFIED" and png_binding is not None:
        # Preserve uncertain turn as a hold, never automatically duplicate it.
        mark_sent(png_binding, status="SUBMISSION_UNVERIFIED_DO_NOT_AUTO_RETRY")
    if send_result != "sent":''',
        "scheduled-attachment",
    )
    source = replace_once(
        source,
        '        await page.wait_for_timeout(1500)\n        return "sent"',
        '''        await page.wait_for_timeout(1500)
        if png_binding is not None:
            proof = await verify_submission_receipt(
                page, png_binding["task_id"], [_outrun_smoke_os.path.basename(p) for p in png_binding.get("paths", [png_binding["path"]])])
            if proof != "PERSISTED_CHAT_USER_MESSAGE_WITH_IMAGE_CONFIRMED":
                return "SEND_UNVERIFIED"
        return "sent"''',
        "post-send-confirmation",
    )
    source = replace_once(
        source,
        '        try:\n'
        '            await box.fill(message, timeout=15000)\n'
        '        except Exception:',
        """        try:
            if png_binding is not None:
                # Keep the inline Create image tool pill; fill() removes it.
                await box.click(timeout=5000)
                await box.press("End", timeout=3000)
                await page.keyboard.insert_text(message)
            else:
                await box.fill(message, timeout=15000)
        except Exception:""",
        "preserve-image-tool",
    )
    source = replace_once(
        source,
        '        if ratio < 0.90 or ratio > 1.10:',
        '        if png_binding is not None and "UPLOAD_TASK_ID=" + png_binding["task_id"] not in actual:\n'
        '            return "verify_task_id_missing"\n'
        '        if png_binding is None and (ratio < 0.90 or ratio > 1.10):',
        "task-id-in-editor",
    )
    # The import must be part of controller code itself; no executable startup
    # shell monkey-patching and no separate daemon.
    import_line = 'from app.controller_png_attach import load_binding, attach_png, mark_sent, prepare_a_project_target, verify_submission_receipt, ensure_image_tool\nfrom app.tile_batch_queue import confirm_visible_results\nimport os as _outrun_smoke_os\n'
    lines = source.splitlines(keepends=True)
    future_imports = [i for i, line in enumerate(lines)
                      if line.startswith("from __future__ import ")]
    if future_imports:
        lines.insert(max(future_imports) + 1, import_line)
        source = "".join(lines)
    else:
        # With a module docstring, an import before it is valid Python too.
        source = import_line + source
    ast.parse(source)
    return source


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("controller", type=Path)
    args = parser.parse_args()
    original = args.controller.read_text(encoding="utf-8")
    updated = patch(original)
    if updated != original:
        args.controller.write_text(updated, encoding="utf-8")
    print("OUTRUN_PNG_UPLOAD_V1_PATCHED" if updated != original else "ALREADY_PATCHED")


if __name__ == "__main__":
    main()