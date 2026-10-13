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
        'LOCALIZATION_SLOT_NAMES = ("A", "B", "C1")',
        "role-tab-list",
    )
    source = replace_once(
        source,
        'if CONTROLLER_MODE == "localization" and CHAT_SLOTS != 4:\n'
        '    raise ValueError("Recovery localization requires CHAT_SLOTS=4 (A/B/C1/C2)")',
        'if CONTROLLER_MODE == "localization" and CHAT_SLOTS != 3:\n'
        '    raise ValueError("Recovery localization requires CHAT_SLOTS=3 (A/B/C1)")',
        "slot-count",
    )
    source = replace_once(
        source,
        'SCHEDULED_LOCALIZATION_LANES = {0: "A", 10: "C1", 20: "C2",\n'
        '                                30: "B", 40: "C1", 50: "C2"}',
        '''SCHEDULED_LOCALIZATION_LANES = {0: "A", 10: "C1", 30: "B", 40: "C1"}
# OUTRUN_SINGLE_A_SMOKE_V1: a single authorized A task, no B/C1 dispatch.
OUTRUN_A_SINGLE_SMOKE_TASK_ID = _outrun_smoke_os.environ.get("OUTRUN_A_SINGLE_SMOKE_TASK_ID", "").strip()
if OUTRUN_A_SINGLE_SMOKE_TASK_ID:
    SCHEDULED_LOCALIZATION_LANES = {0: "A"}''',
        "minute-role-schedule",
    )
    source = replace_once(
        source,
        '        unexpected = set(existing) - set(LOCALIZATION_SLOT_NAMES)',
        '''        # Preserve retired C2's exact checkpoint without re-opening a C2 tab.
        if "C2" in existing:
            retired = STATE_DIR / "retired_C2_slot_before_png_upload_v1.json"
            if not retired.exists():
                retired.write_text(json.dumps(asdict(existing["C2"]), ensure_ascii=False, indent=2), encoding="utf-8")
            del existing["C2"]
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
        status = await attach_png(page, png_binding)
        if status != "ATTACHED_PREVIEW_CONFIRMED":
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
        if CONTROLLER_MODE == "localization" and (slot.name in ("A", "B") or OUTRUN_A_SINGLE_SMOKE_TASK_ID):
            continue
        prompt = prompt_for_slot(slot, "watchdog")''',
        "producer-watchdog",
    )
    source = replace_once(
        source,
        '    send_result = await send_message(page, prompt)\n'
        '    if send_result != "sent":',
        '''    # OUTRUN_PNG_UPLOAD_V1: per-role SHA-pinned source manifest, fail closed.
    # Suppress every scheduled non-A lane in one-A pilot mode.
    if OUTRUN_A_SINGLE_SMOKE_TASK_ID and slot.name != "A":
        return
    png_binding = None
    if CONTROLLER_MODE == "localization" and slot.name in ("A", "B"):
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
            # Do not mistake a preview + Enter keypress for server receipt.
            try:
                await page.wait_for_function(
                    """task_id => {
                      const draft = document.querySelector('#prompt-textarea');
                      const draft_text = (draft?.innerText || draft?.textContent || '');
                      const body_text = document.body?.innerText || '';
                      return body_text.includes(task_id) && !draft_text.includes(task_id);
                    }""",
                    arg=png_binding["task_id"],
                    timeout=30000,
                )
            except Exception:
                return "SEND_UNVERIFIED"
        return "sent"''',
        "post-send-confirmation",
    )
    # The import must be part of controller code itself; no executable startup
    # shell monkey-patching and no separate daemon.
    import_line = 'from app.controller_png_attach import load_binding, attach_png, mark_sent\nimport os as _outrun_smoke_os\n'
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
