"""Browser-only maintenance for the compact recovery-v1 controller.

Never submits prompts, changes role assignments, or deletes authentication data.
No v0.4 queue/event/task engine dependencies.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from datetime import datetime
from pathlib import Path

log = logging.getLogger("outrun-controller.chrome")
CACHE_PROFILE = Path("/data/browser-profile")
CHROME_RECYCLE_FILE = Path("/data/state/chrome_recycle.json")
TAB_HEALTH_CHECK_SECONDS = max(10, int(os.getenv("TAB_HEALTH_CHECK_SECONDS", "30")))
TAB_HEALTH_PROBE_TIMEOUT_SECONDS = max(2, int(os.getenv("TAB_HEALTH_PROBE_TIMEOUT_SECONDS", "6")))
TAB_HEALTH_FAILURE_THRESHOLD = max(2, int(os.getenv("TAB_HEALTH_FAILURE_THRESHOLD", "3")))
TAB_ERROR_FAILURE_THRESHOLD = max(2, int(os.getenv("TAB_ERROR_FAILURE_THRESHOLD", "2")))
TAB_RECOVERY_COOLDOWN_SECONDS = max(10, int(os.getenv("TAB_RECOVERY_COOLDOWN_SECONDS", "60")))
CHROME_RECYCLE_ENABLED = os.getenv("CHROME_RECYCLE_ENABLED", "false").lower() == "true"
CHROME_RECYCLE_INTERVAL_SECONDS = max(1800, int(os.getenv("CHROME_RECYCLE_INTERVAL_MINUTES", "120")) * 60)
CHROME_RECYCLE_BUSY_GRACE_SECONDS = max(0, int(os.getenv("CHROME_RECYCLE_BUSY_GRACE_MINUTES", "30")) * 60)
CHROME_RECYCLE_BUSY_PROBE_SECONDS = max(2, int(os.getenv("CHROME_RECYCLE_BUSY_PROBE_SECONDS", "8")))

ERROR_PAGE = re.compile(
    r"(?:aw[, ]*snap|this site can.t be reached|chrome.*(?:crash|error)|"
    r"page (?:unresponsive|crashed)|페이지를 (?:표시할 수 없|로드할 수 없)|"
    r"앗[,! ]*이런|사이트에 연결할 수 없|페이지가 응답하지 않)",
    re.IGNORECASE,
)


def is_chrome_error(probe: dict) -> bool:
    url = str(probe.get("url") or "").lower()
    if url.startswith(("chrome-error://", "chrome://crash", "chrome://kill")):
        return True
    if probe.get("composer"):
        return False
    return bool(ERROR_PAGE.search(str(probe.get("title") or "")[:250] +
                                  "\n" + str(probe.get("body") or "")[:750]))


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    with temp.open("w", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)


async def scan_slot_tabs(context, pages, slots, state: dict, protected: set[str],
                         base_url: str, write_runtime, is_saved_url) -> None:
    """Repair one failed renderer at a time; retain slot URL/runs/results."""
    seen = state.setdefault("seen", {})
    crash = state.setdefault("crash", set())
    failures = state.setdefault("failures", {})
    errors = state.setdefault("errors", {})
    last_fixed = state.setdefault("last_fixed", {})
    for slot in slots:
        name = slot.name
        if name in protected:
            continue
        page = pages.get(name)
        if page is not None and seen.get(name) is not page:
            seen[name] = page
            failures[name] = errors[name] = 0
            try:
                page.on("crash", lambda *_, n=name: crash.add(n))
            except Exception:
                log.warning("Could not attach crash listener to %s", name)
        reason = None
        if page is None or page.is_closed():
            reason = "missing_or_closed"
        elif name in crash:
            reason = "renderer_crash"
        else:
            try:
                probe = await asyncio.wait_for(page.evaluate("""() => ({
                  url: location.href, title: document.title,
                  body: (document.body?.innerText || '').slice(0, 900),
                  composer: !!document.querySelector(
                    '#prompt-textarea, [data-testid="prompt-textarea"], [contenteditable="true"][data-lexical-editor="true"]')
                })"""), timeout=TAB_HEALTH_PROBE_TIMEOUT_SECONDS)
                failures[name] = 0
                if is_chrome_error(probe):
                    errors[name] = errors.get(name, 0) + 1
                    if errors[name] >= TAB_ERROR_FAILURE_THRESHOLD:
                        reason = "chrome_error_screen"
                else:
                    errors[name] = 0
            except Exception as exc:
                failures[name] = failures.get(name, 0) + 1
                if failures[name] >= TAB_HEALTH_FAILURE_THRESHOLD:
                    reason = "unresponsive_renderer"
                log.warning("tab health probe slot=%s failure=%d: %s", name, failures[name], type(exc).__name__)
        if reason is None:
            continue
        now = time.monotonic()
        if now - last_fixed.get(name, float("-inf")) < TAB_RECOVERY_COOLDOWN_SECONDS:
            continue
        # A lane may be sent by the scheduler between probe and repair.
        if name in protected or pages.get(name) is not page:
            continue
        last_fixed[name] = now
        target = slot.url if slot.url and is_saved_url(slot.url) else base_url
        log.warning("tab recover slot=%s reason=%s URL preserved=%s", name, reason, bool(slot.url))
        try:
            if page is not None and not page.is_closed():
                try:
                    if reason != "unresponsive_renderer":
                        snapshot = Path("/logs/tab-recovery") / (
                            datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + name + ".png")
                        snapshot.parent.mkdir(parents=True, exist_ok=True)
                        await asyncio.wait_for(page.screenshot(path=str(snapshot)),
                                               timeout=TAB_HEALTH_PROBE_TIMEOUT_SECONDS)
                except Exception:
                    pass
                try:
                    await asyncio.wait_for(page.close(), timeout=TAB_HEALTH_PROBE_TIMEOUT_SECONDS)
                except Exception:
                    pass
            replacement = await context.new_page()
            pages[name] = replacement
            seen[name] = replacement
            crash.discard(name)
            failures[name] = errors[name] = 0
            replacement.on("crash", lambda *_, n=name: crash.add(n))
            await replacement.goto(target, wait_until="domcontentloaded", timeout=45000)
            count = state.get("recovery_count", 0) + 1
            state["recovery_count"] = count
            write_runtime(tab_recovery_count=count,
                          tab_recovery_last_slot=name, tab_recovery_last_reason=reason,
                          tab_recovery_last_at=datetime.now().isoformat(),
                          tab_recovery_error=None,
                          slot_tabs={key: value.url for key, value in pages.items()
                                     if not value.is_closed()})
        except Exception as exc:
            # The next pass retries after cooldown without losing the saved chat.
            write_runtime(tab_recovery_error=name + ":" + type(exc).__name__,
                          tab_recovery_last_reason=reason)
            log.exception("tab recovery failed slot=%s; previous task state preserved", name)
            if context.browser is not None and not context.browser.is_connected():
                raise RuntimeError("Chrome CDP disconnected") from exc


async def periodic_tab_health(context, pages, get_slots, state, protected,
                              base_url, write_runtime, is_saved_url):
    while True:
        await scan_slot_tabs(context, pages, get_slots(), state, protected,
                             base_url, write_runtime, is_saved_url)
        await asyncio.sleep(TAB_HEALTH_CHECK_SECONDS)


async def request_periodic_recycle(pages, protected: set[str], elapsed: float,
                                   detect_busy, write_runtime, save_checkpoint) -> bool:
    """Signal an intentional Docker restart only after the durable v1 checkpoint."""
    if not CHROME_RECYCLE_ENABLED or elapsed < CHROME_RECYCLE_INTERVAL_SECONDS:
        return False
    busy = list(protected)
    for name, page in pages.items():
        if name in protected:
            continue
        try:
            if not page.is_closed() and await asyncio.wait_for(
                    detect_busy(page), timeout=CHROME_RECYCLE_BUSY_PROBE_SECONDS):
                busy.append(name)
        except Exception:
            busy.append(name)
    overdue = elapsed - CHROME_RECYCLE_INTERVAL_SECONDS
    if busy and overdue < CHROME_RECYCLE_BUSY_GRACE_SECONDS:
        write_runtime(chrome_recycle_status="deferred_busy",
                      chrome_recycle_deferred_slots=sorted(set(busy)),
                      chrome_recycle_overdue_seconds=int(overdue))
        return False
    save_checkpoint()
    try:
        previous = json.loads(CHROME_RECYCLE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        previous = {}
    record = {
        "count": int(previous.get("count", 0)) + 1,
        "requested_at": datetime.now().isoformat(),
        "busy_slots_at_request": sorted(set(busy)),
        "reason": "periodic_auth_preserving_recycle",
        "interval_minutes": CHROME_RECYCLE_INTERVAL_SECONDS // 60,
    }
    atomic_json(CHROME_RECYCLE_FILE, record)
    write_runtime(status="chrome_recycle_requested",
                  chrome_recycle_status="restarting",
                  chrome_recycle_count=record["count"],
                  chrome_recycle_last_at=record["requested_at"],
                  last_action="Saved v1 registry; restarting Chrome without deleting credentials")
    return True
