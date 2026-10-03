from __future__ import annotations

import argparse
import asyncio
import hashlib
import html
import json
import logging
import os
import re
import threading
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, asdict
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

from playwright.async_api import async_playwright, BrowserContext, Page

TZ = ZoneInfo(os.getenv("TZ", "Asia/Seoul"))
REPO = os.getenv("GITHUB_REPO", "thp32tt/OutRun2006Tweaks").strip()
BRANCH = os.getenv("TARGET_BRANCH", "korean-localization-20260928-clean-v1").strip()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "").strip()
PROJECT_URL = os.getenv("LOCALIZATION_PROJECT_URL", "").strip()
AUTO_SEND = os.getenv("AUTO_SEND", "false").lower() == "true"
POLL_SECONDS = max(10, int(os.getenv("POLL_SECONDS", "15")))
STABLE_SECONDS = max(10, int(os.getenv("STABLE_SECONDS", "30")))
NUDGE_SECONDS = max(60, int(os.getenv("NUDGE_SECONDS", "180")))
RECOVERY_SECONDS = max(600, int(os.getenv("RECOVERY_SECONDS", "1200")))
MAX_NUDGES = max(1, int(os.getenv("MAX_NUDGES", "4")))
STATUS_PORT = int(os.getenv("STATUS_PORT", "8787"))
STATE_FILE = Path("/data/state/localization-clean-v1.json")
LOG_FILE = Path("/logs/controller.log")

LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(LOG_FILE)],
)
log = logging.getLogger("localization-clean-v1")

INPUT_SELECTORS = [
    "#prompt-textarea",
    "div#prompt-textarea",
    "[data-testid='prompt-textarea']",
    "[data-testid='composer'] textarea",
    "[data-testid='composer'] [contenteditable='true']",
    "textarea[placeholder*='Message' i]",
    "textarea[placeholder*='Ask ChatGPT' i]",
    "textarea[placeholder*='메시지']",
    "[contenteditable='true'][data-lexical-editor='true']",
    "div.ProseMirror[contenteditable='true']",
    "[role='textbox'][contenteditable='true']",
]
BUSY_SELECTORS = [
    "button[data-testid='stop-button']",
    "button:has-text('Stop generating')",
    "button:has-text('Stop streaming')",
    "button:has-text('생성 중지')",
    "button:has-text('응답 중지')",
]
CONTINUE_SELECTORS = [
    "button:has-text('Continue generating')",
    "button:has-text('계속 생성')",
    "button:has-text('계속해서 생성')",
]
ASSISTANT_SELECTOR = "[data-message-author-role='assistant']"
CONVERSATION_LIMIT_RE = re.compile(
    r"maximum (conversation|chat) length|conversation.{0,30}too long|새 (채팅|대화).{0,20}(시작|계속)|대화.{0,20}(한도|최대 길이)",
    re.I | re.S,
)

state_lock = threading.RLock()
runtime = {
    "started_at": datetime.now(TZ).isoformat(),
    "status": "starting",
    "repo": REPO,
    "branch": BRANCH,
    "auto_send": AUTO_SEND,
}


@dataclass
class Lane:
    role: str
    status: str = "IDLE"
    task_id: str = ""
    base_sha: str = ""
    result_sha: str = ""
    chat_url: str = ""
    sent_at: str = ""
    last_nudge_at: str = ""
    nudges: int = 0
    recoveries: int = 0
    assistant_hash: str = ""
    assistant_changed_at: str = ""


@dataclass
class ControllerState:
    schema: int
    wave: int
    phase: str
    lanes: dict[str, Lane]


def new_state() -> ControllerState:
    return ControllerState(schema=1, wave=1, phase="PRODUCE", lanes={r: Lane(r) for r in "ABC"})


def _state_to_json(s: ControllerState) -> dict:
    return {
        "schema": s.schema,
        "wave": s.wave,
        "phase": s.phase,
        "lanes": {k: asdict(v) for k, v in s.lanes.items()},
    }


def save_state(s: ControllerState) -> None:
    with state_lock:
        tmp = STATE_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(_state_to_json(s), ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(STATE_FILE)


def load_state() -> ControllerState:
    if not STATE_FILE.exists():
        return new_state()
    raw = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    if raw.get("schema") != 1:
        raise RuntimeError("Unsupported controller state schema")
    lanes = {k: Lane(**v) for k, v in raw["lanes"].items()}
    return ControllerState(schema=1, wave=int(raw["wave"]), phase=raw["phase"], lanes=lanes)


def set_runtime(**updates) -> None:
    with state_lock:
        runtime.update(updates)


def github_json(path: str):
    url = "https://api.github.com" + path
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "outrun-localization-clean-v1",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def github_commits(limit: int = 100) -> list[dict]:
    q = urllib.parse.urlencode({"sha": BRANCH, "per_page": str(min(100, limit))})
    return github_json(f"/repos/{REPO}/commits?{q}")


def github_head() -> str:
    commits = github_commits(1)
    if not commits:
        raise RuntimeError(f"No commits found for {REPO}:{BRANCH}")
    return commits[0]["sha"]


def marker_commit(task_id: str) -> Optional[dict]:
    if not task_id:
        return None
    marker = f"[AUTO:{task_id}]"
    for item in github_commits(100):
        message = item.get("commit", {}).get("message", "")
        if marker in message:
            return {"sha": item["sha"], "message": message}
    return None


def task_id(role: str, wave: int) -> str:
    return f"LOCALIZATION-{role}-W{wave:05d}"


def task_prompt(role: str, lane: Lane, a_sha: str = "", b_sha: str = "") -> str:
    lines = [
        f"OutRun 한글화 {role} 실행",
        f"TASK_ID={lane.task_id}",
        f"TARGET_BRANCH={BRANCH}",
        "GitHub의 대상 브랜치를 SSOT로 사용하고 docs/KOREAN_LOCALIZATION_AUTOMATION_CONTRACT.md를 먼저 읽어.",
    ]
    if role in {"A", "B"}:
        lines += [
            "검토만 하고 끝내지 말고, 실행 가능한 작업이 있으면 실제 DDS/근거/소스 변경까지 진행해.",
            "한 번 실행에서 가능한 범위의 여러 독립 작업을 계속 처리한 뒤 durable Git 결과를 남겨.",
        ]
    else:
        lines += [
            f"A_RESULT_SHA={a_sha}",
            f"B_RESULT_SHA={b_sha}",
            "A/B 두 결과를 최신 HEAD에서 보존한 채 cross-lane 최종 QA와 shared-state reconciliation을 수행해.",
        ]
    lines += [
        f"완료 또는 실제 blocker는 반드시 실제 변경/근거를 Git에 남기고 커밋 메시지에 정확히 [AUTO:{lane.task_id}] 를 포함해.",
        "실기 게임 테스트를 하지 않았다면 RUNTIME_VALIDATION=UNTESTED로 유지해.",
        "최종 답변 마지막에 RESULT_SHA=<40자리 커밋 SHA>를 출력해.",
    ]
    return "\n".join(lines)


def resume_prompt(lane: Lane) -> str:
    return "\n".join([
        f"같은 작업을 계속 실행해. TASK_ID={lane.task_id}",
        f"TARGET_BRANCH={BRANCH}",
        "설명/검토만으로 종료하지 말고 아직 실행 가능한 한글화 작업을 계속 처리해.",
        f"durable 결과 커밋에 정확히 [AUTO:{lane.task_id}] 를 포함하고 RESULT_SHA를 출력해.",
        "이미 완료한 작업은 반복하지 말고 Git 최신 HEAD에서 이어서 진행해.",
    ])


def stable_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


async def composer(page: Page):
    for sel in INPUT_SELECTORS:
        try:
            loc = page.locator(sel).first
            if await loc.count() and await loc.is_visible():
                return loc
        except Exception:
            continue
    return None


async def ensure_project(page: Page) -> bool:
    if not PROJECT_URL:
        set_runtime(status="project_url_required")
        return False
    if not page.url.startswith(PROJECT_URL):
        try:
            await page.goto(PROJECT_URL, wait_until="domcontentloaded", timeout=60000)
        except Exception as exc:
            log.warning("project navigation failed: %r", exc)
    for _ in range(30):
        if await composer(page):
            return True
        await asyncio.sleep(1)
    set_runtime(status="login_or_project_required")
    return False


async def is_busy(page: Page) -> bool:
    for sel in BUSY_SELECTORS:
        try:
            loc = page.locator(sel).first
            if await loc.count() and await loc.is_visible():
                return True
        except Exception:
            continue
    return False


async def click_continue(page: Page) -> bool:
    for sel in CONTINUE_SELECTORS:
        try:
            loc = page.locator(sel).first
            if await loc.count() and await loc.is_visible():
                await loc.click()
                return True
        except Exception:
            continue
    return False


async def last_assistant_text(page: Page) -> str:
    try:
        loc = page.locator(ASSISTANT_SELECTOR)
        n = await loc.count()
        if n:
            return (await loc.nth(n - 1).inner_text()).strip()
    except Exception:
        pass
    return ""


async def has_conversation_limit(page: Page) -> bool:
    text = await last_assistant_text(page)
    return bool(text and CONVERSATION_LIMIT_RE.search(text))


async def send(page: Page, message: str) -> bool:
    box = await composer(page)
    if box is None:
        return False
    try:
        tag = await box.evaluate("el => el.tagName.toLowerCase()")
        if tag == "textarea":
            await box.fill(message)
        else:
            await box.click()
            await page.keyboard.press("Control+A")
            await page.keyboard.type(message)
        await page.keyboard.press("Enter")
        return True
    except Exception as exc:
        log.warning("send failed: %r", exc)
        return False


async def fresh_page(context: BrowserContext, old: Optional[Page]) -> Page:
    page = await context.new_page()
    await page.goto(PROJECT_URL, wait_until="domcontentloaded", timeout=60000)
    if old is not None and not old.is_closed():
        try:
            await old.close()
        except Exception:
            pass
    return page


async def restore_pages(context: BrowserContext, s: ControllerState) -> dict[str, Page]:
    pages: dict[str, Page] = {}
    existing = [p for p in context.pages if not p.is_closed()]
    for role in "ABC":
        lane = s.lanes[role]
        page = await context.new_page()
        url = lane.chat_url or PROJECT_URL
        if url:
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            except Exception:
                pass
        pages[role] = page
    for p in existing:
        if p not in pages.values():
            try:
                await p.close()
            except Exception:
                pass
    return pages


async def dispatch(context: BrowserContext, pages: dict[str, Page], s: ControllerState, role: str) -> None:
    lane = s.lanes[role]
    lane.task_id = task_id(role, s.wave)
    lane.base_sha = await asyncio.to_thread(github_head)
    lane.result_sha = ""
    lane.status = "ACTIVE"
    lane.nudges = 0
    lane.recoveries = 0
    lane.last_nudge_at = ""
    lane.assistant_hash = ""
    lane.assistant_changed_at = datetime.now(TZ).isoformat()
    page = await fresh_page(context, pages.get(role))
    pages[role] = page
    if not await ensure_project(page):
        lane.status = "IDLE"
        save_state(s)
        return
    prompt = task_prompt(
        role,
        lane,
        s.lanes["A"].result_sha if role == "C" else "",
        s.lanes["B"].result_sha if role == "C" else "",
    )
    if not await send(page, prompt):
        lane.status = "IDLE"
        save_state(s)
        return
    lane.sent_at = datetime.now(TZ).isoformat()
    await asyncio.sleep(2)
    lane.chat_url = page.url
    save_state(s)
    log.info("dispatched role=%s task=%s base=%s", role, lane.task_id, lane.base_sha)


async def reconcile_lane(s: ControllerState, role: str) -> bool:
    lane = s.lanes[role]
    if lane.status != "ACTIVE":
        return False
    found = await asyncio.to_thread(marker_commit, lane.task_id)
    if not found:
        return False
    lane.status = "DONE"
    lane.result_sha = found["sha"]
    save_state(s)
    log.info("completed role=%s task=%s sha=%s", role, lane.task_id, lane.result_sha)
    return True


async def recover_same_task(context: BrowserContext, pages: dict[str, Page], s: ControllerState, role: str) -> None:
    lane = s.lanes[role]
    page = await fresh_page(context, pages.get(role))
    pages[role] = page
    if not await ensure_project(page):
        return
    if await send(page, resume_prompt(lane)):
        lane.recoveries += 1
        lane.nudges = 0
        lane.sent_at = datetime.now(TZ).isoformat()
        lane.last_nudge_at = ""
        lane.chat_url = page.url
        lane.assistant_hash = ""
        lane.assistant_changed_at = lane.sent_at
        save_state(s)
        log.warning("recovered same task role=%s task=%s recovery=%s", role, lane.task_id, lane.recoveries)


async def observe_active(context: BrowserContext, pages: dict[str, Page], s: ControllerState, role: str) -> None:
    lane = s.lanes[role]
    if lane.status != "ACTIVE":
        return
    if await reconcile_lane(s, role):
        return
    page = pages[role]
    if page.is_closed():
        await recover_same_task(context, pages, s, role)
        return
    if await is_busy(page):
        return
    if await click_continue(page):
        return
    now = datetime.now(TZ)
    text = await last_assistant_text(page)
    digest = stable_hash(text) if text else ""
    if digest != lane.assistant_hash:
        lane.assistant_hash = digest
        lane.assistant_changed_at = now.isoformat()
        save_state(s)
        return
    changed_at = datetime.fromisoformat(lane.assistant_changed_at or lane.sent_at)
    sent_at = datetime.fromisoformat(lane.sent_at)
    if await has_conversation_limit(page) or (now - sent_at).total_seconds() >= RECOVERY_SECONDS:
        await recover_same_task(context, pages, s, role)
        return
    if (now - changed_at).total_seconds() < STABLE_SECONDS:
        return
    last_nudge = datetime.fromisoformat(lane.last_nudge_at) if lane.last_nudge_at else sent_at
    if lane.nudges < MAX_NUDGES and (now - last_nudge).total_seconds() >= NUDGE_SECONDS:
        if await send(page, resume_prompt(lane)):
            lane.nudges += 1
            lane.last_nudge_at = now.isoformat()
            lane.assistant_changed_at = now.isoformat()
            save_state(s)
            log.info("nudged role=%s task=%s nudge=%s", role, lane.task_id, lane.nudges)


async def cycle(context: BrowserContext, pages: dict[str, Page], s: ControllerState) -> None:
    head = await asyncio.to_thread(github_head)
    set_runtime(status="running" if AUTO_SEND else "manual", wave=s.wave, phase=s.phase, head=head)

    for role in "ABC":
        await observe_active(context, pages, s, role)

    if not AUTO_SEND:
        return

    if s.phase == "PRODUCE":
        for role in "AB":
            if s.lanes[role].status == "IDLE":
                await dispatch(context, pages, s, role)
        if s.lanes["A"].status == "DONE" and s.lanes["B"].status == "DONE":
            s.phase = "QA"
            s.lanes["C"] = Lane("C")
            save_state(s)

    if s.phase == "QA":
        if s.lanes["C"].status == "IDLE":
            await dispatch(context, pages, s, "C")
        if s.lanes["C"].status == "DONE":
            log.info("wave complete wave=%s A=%s B=%s C=%s",
                     s.wave, s.lanes["A"].result_sha, s.lanes["B"].result_sha, s.lanes["C"].result_sha)
            s.wave += 1
            s.phase = "PRODUCE"
            s.lanes = {r: Lane(r) for r in "ABC"}
            save_state(s)


class StatusHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def do_GET(self):
        if self.path not in {"/", "/status"}:
            self.send_response(404)
            self.end_headers()
            return
        with state_lock:
            s = json.loads(STATE_FILE.read_text(encoding="utf-8")) if STATE_FILE.exists() else _state_to_json(new_state())
            payload = {"runtime": dict(runtime), "state": s}
        body = ("<!doctype html><html><head><meta charset='utf-8'><title>Localization clean v1</title></head>"
                "<body><h1>OutRun Korean Localization clean-v1</h1><pre>" +
                html.escape(json.dumps(payload, ensure_ascii=False, indent=2)) + "</pre></body></html>").encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def start_status_server():
    server = ThreadingHTTPServer(("0.0.0.0", STATUS_PORT), StatusHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()


async def main_async(once: bool):
    start_status_server()
    if not PROJECT_URL:
        set_runtime(status="project_url_required")
    s = load_state()
    async with async_playwright() as p:
        browser = None
        for _ in range(60):
            try:
                browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
                break
            except Exception:
                await asyncio.sleep(1)
        if browser is None:
            raise RuntimeError("Chrome CDP 9222 unavailable")
        context = browser.contexts[0] if browser.contexts else await browser.new_context()
        pages = await restore_pages(context, s)
        while True:
            try:
                await cycle(context, pages, s)
            except urllib.error.HTTPError as exc:
                log.exception("GitHub HTTP error; state preserved")
                set_runtime(status="github_error", last_error=f"HTTP {exc.code}")
            except Exception as exc:
                log.exception("cycle failed; state preserved")
                set_runtime(status="error", last_error=repr(exc))
            if once:
                return
            await asyncio.sleep(POLL_SECONDS)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    try:
        asyncio.run(main_async(args.once))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
