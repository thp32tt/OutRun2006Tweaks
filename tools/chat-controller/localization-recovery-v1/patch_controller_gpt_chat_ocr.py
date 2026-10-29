#!/usr/bin/env python3
"""Patch C1 to use normal ChatGPT image attachments as OCR fallback first.

A/B remain ImageGen producer lanes. C remains the local native-crop worker.
C1 first consumes one exhausted local-OCR source through the normal ChatGPT
composer (no Create-image tool, no API); when no GPT OCR work exists it falls
back to the existing independent lightweight QA prompt.
"""
from __future__ import annotations
import argparse, ast
from pathlib import Path

MARKER="# OUTRUN_GPT_CHAT_OCR_V1"

def replace_once(s,old,new,label):
    n=s.count(old)
    if n!=1: raise ValueError(f"{label}: expected one anchor, observed {n}")
    return s.replace(old,new,1)

def patch(source):
    if MARKER in source:return source
    if "# OUTRUN_C1_SLOT_V2" not in source:raise ValueError("GPT OCR patch must run after C1 patch")
    s=source
    old_import='from app.controller_png_attach import load_binding, attach_png, mark_sent, prepare_a_project_target, verify_submission_receipt, ensure_image_tool, clear_attachment_previews\n'
    new_import=(
      'from app.controller_png_attach import load_binding, attach_png, mark_sent, prepare_a_project_target, verify_submission_receipt, ensure_image_tool, clear_attachment_previews, send_analysis_message_with_attachment\n'
      'from app.gpt_vision_chat_ocr import next_binding as gpt_ocr_next_binding, stage_submission as gpt_ocr_stage_submission, rollback_submission as gpt_ocr_rollback_submission, record_chat_url as gpt_ocr_record_chat_url, active_task as gpt_ocr_active_task, apply_response as gpt_ocr_apply_response, summary as gpt_ocr_summary, recover_stale_active as gpt_ocr_recover_stale_active\n'
    )
    s=replace_once(s,old_import,new_import,"imports")
    old='''    elif CONTROLLER_MODE == "localization" and slot.name == "C1":
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
'''
    new='''    elif CONTROLLER_MODE == "localization" and slot.name == "C1":
        # GPT vision OCR fallback uses the EXISTING ChatGPT browser session only.
        # No API is called and the Create-image tool is deliberately not selected.
        gpt_active = gpt_ocr_active_task()
        # B/C2 OCR is owned by the B tab; C1 must not hijack that chat.
        if gpt_active and gpt_active.get("ocr_lane") == "C2":
            slot.last_result = "C1_OCR_C2_LEASE_ACTIVE"
            save_registry(reg)
            return
        if gpt_active and gpt_active.get("status") == "SENT_AWAITING_RESPONSE":
            expected_url = gpt_active.get("chat_url")
            if expected_url and page.url.rstrip("/") != expected_url.rstrip("/"):
                try:
                    await page.goto(expected_url, wait_until="domcontentloaded", timeout=60000)
                    await page.wait_for_timeout(700)
                except Exception:
                    slot.last_result = "GPT_OCR_CHAT_REOPEN_FAILED"
                    save_registry(reg)
                    write_runtime(status="gpt_ocr_hold", last_action="C1 OCR: saved chat reopen failed")
                    return
            if await detect_busy(page):
                slot.last_result = "GPT_OCR_RESPONSE_BUSY"
                save_registry(reg)
                write_runtime(status="gpt_ocr_busy", last_action="C1 OCR: response still generating")
                return
            task_token = str(gpt_active.get("task_id") or "")
            source_token = str(gpt_active.get("source_png") or "")
            answer = await last_assistant_text(page)
            # Never consume an unrelated prior assistant turn.
            if answer and not (task_token in answer and source_token in answer and '"detections"' in answer):
                answer = ""
            if not answer:
                # 2026 ChatGPT thread redesign: role is encoded in the final
                # component of data-*-search-unit-key (e.g. :user/:assistant).
                # Anchor on THIS task's uploaded user turn, then inspect only
                # later assistant units. This avoids mistaking the JSON example
                # embedded in the user prompt for the assistant response.
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
                          // Some hydrated layouts expose only the assistant body.
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
                    slot.last_result = "GPT_OCR_RESPONSE_NOT_READY"
                    save_registry(reg)
                    write_runtime(status="gpt_ocr_waiting", last_action="C1 OCR: assistant response not visible yet")
                    return
                slot.last_result = "GPT_OCR_AUTO_RECOVERED:" + str(stale.get("status"))
                save_registry(reg)
                write_runtime(
                    status="gpt_ocr_auto_recovered",
                    last_action="C1 OCR auto-recovered stale response wait",
                    gpt_ocr_recovery=stale,
                    gpt_ocr_summary=gpt_ocr_summary(),
                )
            else:
                # The exact saved GPT-OCR chat is open, so a completed malformed
                # answer is consumed as a failed attempt instead of stalling forever.
                # apply_response still requires exact task_id/source_png binding.
                applied = gpt_ocr_apply_response(gpt_active["task_id"], answer)
                write_runtime(
                    status="gpt_ocr_response_applied",
                    last_action="C1 OCR queued " + str(applied.get("applied", 0)) + " direct target(s)",
                    gpt_ocr_result=applied,
                    gpt_ocr_summary=gpt_ocr_summary(),
                )

        gpt_binding, gpt_reason = gpt_ocr_next_binding()
        if gpt_binding is not None:
            project_name = _outrun_smoke_os.environ.get("OUTRUN_AB_PROJECT_NAME", "").strip()
            if not project_name:
                slot.last_result = "GPT_OCR_PROJECT_NOT_CONFIGURED"
                save_registry(reg)
                write_runtime(status="gpt_ocr_hold", last_action="C1 OCR: no verified project name")
                return
            target_status = await prepare_a_project_target(page, project_name, allow_saved_chat=False)
            if target_status != "A_PROJECT_COMPOSER_READY":
                slot.last_result = "GPT_OCR_PROJECT_TARGET_BLOCKED:" + target_status
                save_registry(reg)
                write_runtime(status="gpt_ocr_hold", last_action="C1 OCR: " + target_status)
                return
            start_status = gpt_ocr_stage_submission(gpt_binding["task_id"])
            if start_status != "SUBMITTING":
                send_result = "GPT_OCR_SUBMISSION_BLOCKED:" + start_status
            else:
                send_result = await send_analysis_message_with_attachment(page, gpt_binding)
            if send_result == "sent":
                new_url = await wait_for_chat_url(page, timeout_sec=12)
                if not new_url:
                    send_result = "GPT_OCR_CHAT_URL_NOT_PERSISTED"
                else:
                    url_status = gpt_ocr_record_chat_url(gpt_binding["task_id"], new_url)
                    if url_status != "URL_RECORDED":
                        send_result = "GPT_OCR_CHAT_URL_NOT_RECORDED:" + url_status
                    else:
                        slot.url = new_url
                        save_registry(reg)
            elif (send_result == "SEND_UNVERIFIED" or
                  send_result.startswith("SOURCE_REFERENCE_NOT_BOUND:") or
                  send_result.startswith("ANALYSIS_")):
                rb = gpt_ocr_rollback_submission(gpt_binding["task_id"], send_result)
                if rb != "ROLLED_BACK_TO_STAGED":
                    send_result += ":ROLLBACK_FAILED:" + rb
            png_binding = None
        elif gpt_reason in ("GPT_CHAT_OCR_QUEUE_EMPTY_OR_EXHAUSTED", "GPT_CHAT_OCR_DISABLED"):
            # No vision-OCR backlog: retain the existing independent C1 QA use.
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
            png_binding = None
            send_result = await send_message(page, prompt)
        else:
            slot.last_result = "GPT_OCR_HOLD:" + str(gpt_reason)
            save_registry(reg)
            write_runtime(status="gpt_ocr_hold", last_action="C1 OCR: " + str(gpt_reason))
            return
'''
    s=replace_once(s,old,new,"c1-gpt-ocr")
    s=MARKER+"\n"+s
    ast.parse(s)
    return s

def main():
    ap=argparse.ArgumentParser();ap.add_argument("controller",type=Path);args=ap.parse_args()
    old=args.controller.read_text(encoding="utf-8");new=patch(old)
    if new!=old:args.controller.write_text(new,encoding="utf-8")
    print("OUTRUN_GPT_CHAT_OCR_V1_PATCHED" if new!=old else "OUTRUN_GPT_CHAT_OCR_V1_ALREADY_PATCHED")

if __name__=="__main__":main()