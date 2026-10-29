#!/usr/bin/env python3
"""Use idle producer B as the C2 GPT-vision OCR lane.

B always keeps producer priority. Only when its ROI queue is empty/finished does
the existing B browser tab help the chat-vision OCR backlog. C1 selects odd Q
sources; idle B/C2 selects even Q sources. Both lanes share the existing single
active lease, so they cannot submit two conflicting OCR tasks at once.
"""
from __future__ import annotations
import argparse, ast
from pathlib import Path

MARKER = "# OUTRUN_B_IDLE_GPT_OCR_V1"

def replace_once(s, old, new, label):
    n=s.count(old)
    if n!=1:
        raise ValueError(f"{label}: expected one anchor, observed {n}")
    return s.replace(old,new,1)

def patch(source):
    if MARKER in source:
        return source
    if "# OUTRUN_GPT_CHAT_OCR_V1" not in source:
        raise ValueError("B idle OCR patch must run after GPT OCR patch")
    s=source

    # C1 explicitly claims odd-Q work. This preserves old behavior when no lane
    # argument is supplied elsewhere.
    s=replace_once(
        s,
        "        gpt_binding, gpt_reason = gpt_ocr_next_binding()",
        "        gpt_binding, gpt_reason = gpt_ocr_next_binding(\"C1\")",
        "c1-lane",
    )

    helper=r'''
async def _outrun_b_idle_gpt_ocr(page: Page, slot: Slot, reg: Registry):
    """Run one C2 OCR collect/send cycle on B only while B producer queue is idle."""
    gpt_active = gpt_ocr_active_task()
    if gpt_active and gpt_active.get("status") == "SENT_AWAITING_RESPONSE":
        expected_url = gpt_active.get("chat_url")
        if expected_url and page.url.rstrip("/") != expected_url.rstrip("/"):
            try:
                await page.goto(expected_url, wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(700)
            except Exception:
                slot.last_result = "B_C2_GPT_OCR_CHAT_REOPEN_FAILED"
                save_registry(reg)
                write_runtime(status="gpt_ocr_hold", last_action="B/C2 OCR: saved chat reopen failed")
                return "handled"
        if await detect_busy(page):
            slot.last_result = "B_C2_GPT_OCR_RESPONSE_BUSY"
            save_registry(reg)
            write_runtime(status="gpt_ocr_busy", last_action="B/C2 OCR: response still generating")
            return "handled"
        task_token = str(gpt_active.get("task_id") or "")
        source_token = str(gpt_active.get("source_png") or "")
        answer = await last_assistant_text(page)
        if answer and not (task_token in answer and source_token in answer and '"detections"' in answer):
            answer = ""
        if not answer:
            try:
                answer = await page.evaluate(
                    """({task, source}) => {
                      const role = el => {
                        const key = el.getAttribute('data-chatgpt-search-unit-key') ||
                                    el.getAttribute('data-content-search-unit-key') || '';
                        const m = key.match(/:(user|assistant)$/);
                        return m ? m[1] : '';
                      };
                      const raw = [...document.querySelectorAll(
                        '[data-chatgpt-search-unit-key],[data-content-search-unit-key]')];
                      const units = raw.filter((el, i) => raw.indexOf(el) === i);
                      let userIndex = -1;
                      const marker = 'UPLOAD_TASK_ID=' + task;
                      for (let i = units.length - 1; i >= 0; i--) {
                        const txt = units[i].innerText || units[i].textContent || '';
                        if (role(units[i]) === 'user' && txt.includes(marker)) {
                          userIndex = i;
                          break;
                        }
                      }
                      if (userIndex >= 0) {
                        for (let i = userIndex + 1; i < units.length; i++) {
                          if (role(units[i]) !== 'assistant') continue;
                          const txt = (units[i].innerText || units[i].textContent || '').trim();
                          if (txt.includes(task) && txt.includes(source) &&
                              txt.includes('"detections"')) return txt;
                        }
                      }
                      const bodies = [...document.querySelectorAll(
                        '[data-markdown-text-style="assistant-message"],' +
                        '[data-chatgpt-selection-message-id]')];
                      for (let i = bodies.length - 1; i >= 0; i--) {
                        const txt = (bodies[i].innerText || bodies[i].textContent || '').trim();
                        if (txt.includes(task) && txt.includes(source) &&
                            txt.includes('"detections"')) return txt;
                      }
                      return '';
                    }""",
                    {"task": task_token, "source": source_token})
            except Exception:
                answer = ""
        if not answer:
            stale = gpt_ocr_recover_stale_active()
            if not stale.get("recovered"):
                slot.last_result = "B_C2_GPT_OCR_RESPONSE_NOT_READY"
                save_registry(reg)
                write_runtime(status="gpt_ocr_waiting", last_action="B/C2 OCR: assistant response not visible yet")
                return "handled"
            write_runtime(
                status="gpt_ocr_auto_recovered",
                last_action="B/C2 OCR auto-recovered stale response wait",
                gpt_ocr_recovery=stale,
                gpt_ocr_summary=gpt_ocr_summary(),
            )
        else:
            applied = gpt_ocr_apply_response(gpt_active["task_id"], answer)
            write_runtime(
                status="gpt_ocr_response_applied",
                last_action="B/C2 OCR queued " + str(applied.get("applied", 0)) + " direct target(s)",
                gpt_ocr_result=applied,
                gpt_ocr_summary=gpt_ocr_summary(),
            )

    gpt_binding, gpt_reason = gpt_ocr_next_binding("C2")
    if gpt_binding is None:
        if gpt_reason in ("GPT_CHAT_OCR_QUEUE_EMPTY_OR_EXHAUSTED", "GPT_CHAT_OCR_DISABLED"):
            slot.last_result = "B_IDLE_C2_OCR_QUEUE_EMPTY"
            save_registry(reg)
            write_runtime(status="idle", last_action="B producer empty; C2 OCR has no retryable even-Q work",
                          gpt_ocr_summary=gpt_ocr_summary())
            return "handled"
        slot.last_result = "B_C2_GPT_OCR_HOLD:" + str(gpt_reason)
        save_registry(reg)
        write_runtime(status="gpt_ocr_hold", last_action="B/C2 OCR: " + str(gpt_reason))
        return "handled"

    project_name = _outrun_smoke_os.environ.get("OUTRUN_AB_PROJECT_NAME", "").strip()
    if not project_name:
        slot.last_result = "B_C2_GPT_OCR_PROJECT_NOT_CONFIGURED"
        save_registry(reg)
        write_runtime(status="gpt_ocr_hold", last_action="B/C2 OCR: no verified project name")
        return "handled"
    target_status = await prepare_a_project_target(page, project_name, allow_saved_chat=False)
    if target_status != "A_PROJECT_COMPOSER_READY":
        slot.last_result = "B_C2_GPT_OCR_PROJECT_TARGET_BLOCKED:" + target_status
        save_registry(reg)
        write_runtime(status="gpt_ocr_hold", last_action="B/C2 OCR: " + target_status)
        return "handled"
    start_status = gpt_ocr_stage_submission(gpt_binding["task_id"])
    if start_status != "SUBMITTING":
        slot.last_result = "B_C2_GPT_OCR_SUBMISSION_BLOCKED:" + start_status
        save_registry(reg)
        write_runtime(status="gpt_ocr_hold", last_action="B/C2 OCR: " + start_status)
        return "handled"

    send_result = await send_analysis_message_with_attachment(page, gpt_binding)
    if send_result != "sent":
        if (send_result == "SEND_UNVERIFIED" or
            send_result.startswith("SOURCE_REFERENCE_NOT_BOUND:") or
            send_result.startswith("ANALYSIS_")):
            rb = gpt_ocr_rollback_submission(gpt_binding["task_id"], send_result)
            if rb != "ROLLED_BACK_TO_STAGED":
                send_result += ":ROLLBACK_FAILED:" + rb
        slot.last_result = "B_C2_GPT_OCR_SEND_FAILED:" + send_result
        save_registry(reg)
        write_runtime(status="gpt_ocr_hold", last_action="B/C2 OCR send failed: " + send_result)
        return "handled"

    new_url = await wait_for_chat_url(page, timeout_sec=12)
    if not new_url:
        gpt_ocr_rollback_submission(gpt_binding["task_id"], "GPT_OCR_CHAT_URL_NOT_PERSISTED")
        slot.last_result = "B_C2_GPT_OCR_CHAT_URL_NOT_PERSISTED"
        save_registry(reg)
        write_runtime(status="gpt_ocr_hold", last_action="B/C2 OCR chat URL not persisted")
        return "handled"
    url_status = gpt_ocr_record_chat_url(gpt_binding["task_id"], new_url)
    if url_status != "URL_RECORDED":
        slot.last_result = "B_C2_GPT_OCR_CHAT_URL_NOT_RECORDED:" + url_status
        save_registry(reg)
        write_runtime(status="gpt_ocr_hold", last_action="B/C2 OCR URL record failed: " + url_status)
        return "handled"

    slot.url = new_url
    slot.last_result = "B_IDLE_C2_OCR_SENT"
    save_registry(reg)
    write_runtime(
        status="sent",
        last_action="B producer empty; sent C2 OCR task " + gpt_binding["task_id"],
        active_slot=slot.name,
        active_url=new_url,
        gpt_ocr_summary=gpt_ocr_summary(),
    )
    return "sent"
'''

    s=replace_once(
        s,
        "\nasync def run_cycle(context: BrowserContext, pages: dict[str, Page], scheduled_minute: Optional[int] = None):",
        helper+"\nasync def run_cycle(context: BrowserContext, pages: dict[str, Page], scheduled_minute: Optional[int] = None):",
        "helper",
    )

    old='''        elif png_binding is not None and (
                send_result.startswith("IMAGE_TOOL_NOT_SELECTED:") or
                send_result.startswith("SOURCE_REFERENCE_NOT_BOUND:")):
            rollback_status = rollback_submission(
                slot.name, png_binding["task_id"], send_result)
            if rollback_status != "ROLLED_BACK_TO_STAGED":
                send_result += ":ROLLBACK_FAILED:" + rollback_status
    elif CONTROLLER_MODE == "localization" and slot.name == "C1":'''
    new='''        elif png_binding is not None and (
                send_result.startswith("IMAGE_TOOL_NOT_SELECTED:") or
                send_result.startswith("SOURCE_REFERENCE_NOT_BOUND:")):
            rollback_status = rollback_submission(
                slot.name, png_binding["task_id"], send_result)
            if rollback_status != "ROLLED_BACK_TO_STAGED":
                send_result += ":ROLLBACK_FAILED:" + rollback_status
        if slot.name == "B" and send_result == "SOURCE_REFERENCE_NOT_BOUND:ROI_ROLE_QUEUE_EMPTY_OR_FINISHED":
            b_ocr = await _outrun_b_idle_gpt_ocr(page, slot, reg)
            if b_ocr == "handled":
                return
            send_result = b_ocr
    elif CONTROLLER_MODE == "localization" and slot.name == "C1":'''
    s=replace_once(s,old,new,"b-idle-fallback")
    s=MARKER+"\n"+s
    ast.parse(s)
    return s

def main():
    ap=argparse.ArgumentParser();ap.add_argument("controller",type=Path);args=ap.parse_args()
    old=args.controller.read_text(encoding="utf-8");new=patch(old)
    if new!=old:args.controller.write_text(new,encoding="utf-8")
    print("OUTRUN_B_IDLE_GPT_OCR_V1_PATCHED" if new!=old else "OUTRUN_B_IDLE_GPT_OCR_V1_ALREADY_PATCHED")

if __name__=="__main__":main()