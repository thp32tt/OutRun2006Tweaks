from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Optional
from zoneinfo import ZoneInfo

from playwright.async_api import BrowserContext, Page, async_playwright

from .core import (
    consume_qa_inputs,
    enqueue_qa,
    make_job,
    material_commit_ok,
    now_iso,
    prepare_outgoing_message,
    GITHUB_TOOL_RECOVERY_MESSAGE,
    LOCALIZATION_QUEUE_RECOVERY_MESSAGE,
    github_tool_unavailable_response,
    github_read_limit_response,
    retry_surface_has_platform_error,
    reconcile_state,
    record_completed,
    select_qa_batch,
)

TZ = ZoneInfo(os.getenv("TZ", "Asia/Seoul"))
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = Path(os.getenv("CONTROLLER_CONFIG_FILE", str(BASE_DIR / "config.json")))
PROMPTS_DIR = Path(os.getenv("PROMPTS_DIR", str(BASE_DIR / "prompts")))
STATE_DIR = Path(os.getenv("STATE_DIR", "/data/state"))
STATE_FILE = STATE_DIR / "controller_v05.json"
STATE_BACKUP_FILE = STATE_DIR / "controller_v05.json.bak"
RUNTIME_FILE = STATE_DIR / "runtime_v05.json"
LOG_FILE = Path(os.getenv("LOG_FILE", "/logs/controller-v05.log"))

CONTROLLER_MODE = os.getenv("CONTROLLER_MODE", "localization").strip().lower()
AUTO_SEND = os.getenv("AUTO_SEND", "true").lower() == "true"
GITHUB_REPO = os.getenv("GITHUB_REPO", "thp32tt/OutRun2006Tweaks").strip()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "").strip()
CHATGPT_PROJECT_URL = os.getenv("CHATGPT_PROJECT_URL", "").strip()
REQUIRE_PROJECT_URL = os.getenv("REQUIRE_PROJECT_URL", "true").lower() == "true"
PREFERRED_THINKING_LEVEL = os.getenv("PREFERRED_THINKING_LEVEL", "High").strip() or "High"

TICK_SECONDS = max(5, int(os.getenv("TICK_SECONDS", "15")))
SEND_GAP_SECONDS = max(5, int(os.getenv("SEND_GAP_SECONDS", "30")))
SAME_CHAT_CONTINUATION_GAP_SECONDS = max(
    5, int(os.getenv("SAME_CHAT_CONTINUATION_GAP_SECONDS", "20"))
)
TURN_IDLE_GRACE_SECONDS = max(3, int(os.getenv("TURN_IDLE_GRACE_SECONDS", "8")))
COMMIT_DISCOVERY_GRACE_SECONDS = max(
    10, int(os.getenv("COMMIT_DISCOVERY_GRACE_SECONDS", "30"))
)
RESPONSE_TIMEOUT_SECONDS = max(300, int(os.getenv("RESPONSE_TIMEOUT_SECONDS", "1200")))
NO_WORK_RETRY_SECONDS = max(60, int(os.getenv("NO_WORK_RETRY_SECONDS", "600")))
QA_BATCH_SIZE = max(1, int(os.getenv("QA_BATCH_SIZE", "4")))
CHAT_REUSE_MAX_JOBS = max(2, int(os.getenv("CHAT_REUSE_MAX_JOBS", "12")))
CHAT_REUSE_MAX_AGE_MINUTES = max(
    30, int(os.getenv("CHAT_REUSE_MAX_AGE_MINUTES", "240"))
)
STATUS_PORT = int(os.getenv("STATUS_PORT", "8787"))
RATE_LIMIT_BACKOFF_SECONDS = [
    max(30, int(x.strip()))
    for x in os.getenv("RATE_LIMIT_BACKOFF_SECONDS", "90,180,300,600").split(",")
    if x.strip()
]
GITHUB_SCAN_LIMIT = max(30, min(100, int(os.getenv("GITHUB_SCAN_LIMIT", "100"))))

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
    "form textarea",
    "form [contenteditable='true']",
]

BUSY_SELECTORS = [
    "button[data-testid='stop-button']",
    "button:has-text('Stop generating')",
    "button:has-text('Stop streaming')",
    "button:has-text('생성 중지')",
    "button:has-text('응답 중지')",
]
RETRY_SELECTORS = [
    "button:has-text('Retry')",
    "button:has-text('Try again')",
    "button:has-text('다시 시도')",
    "button:has-text('재시도')",
]
ASSISTANT_MESSAGE_SELECTOR = "[data-message-author-role='assistant']"
CONVERSATION_LIMIT_PATTERNS = [
    r"maximum (?:conversation|chat) length",
    r"(?:conversation|chat).{0,50}(?:too long|maximum length|length limit|limit reached)",
    r"start (?:a )?new (?:chat|conversation).{0,60}(?:continue|limit|length)",
    r"이 대화.{0,40}(?:최대|한도|길이)",
    r"새 (?:채팅|대화).{0,50}(?:시작|계속|이어)",
]
RATE_LIMIT_PATTERNS = [
    r"too many requests",
    r"\b429\b.{0,80}(request|rate|limit)",
    r"rate limit",
    r"너무 많은 요청",
    r"요청.{0,16}(한도|제한)",
]

LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
STATE_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(LOG_FILE)],
)
log = logging.getLogger("outrun-controller-v05")

CONFIG = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
if CONTROLLER_MODE not in CONFIG["modes"]:
    raise ValueError(f"Unsupported CONTROLLER_MODE={CONTROLLER_MODE!r}")
MODE_CONFIG = CONFIG["modes"][CONTROLLER_MODE]
LANE_SPECS = MODE_CONFIG["lanes"]

runtime: dict[str, Any] = {
    "version": "0.5",
    "started_at": now_iso(),
    "mode": CONTROLLER_MODE,
    "auto_send": AUTO_SEND,
    "repository": GITHUB_REPO,
    "project_url_configured": bool(CHATGPT_PROJECT_URL),
    "github_token_configured": bool(GITHUB_TOKEN),
    "status": "starting",
    "last_tick": None,
    "last_action": None,
    "last_error": None,
}


def write_runtime(**updates: Any) -> None:
    runtime.update(updates)
    runtime["last_tick"] = now_iso()
    tmp = RUNTIME_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(runtime, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(RUNTIME_FILE)


def _safe_json_load(path: Path) -> Optional[dict[str, Any]]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def load_state() -> dict[str, Any]:
    raw = _safe_json_load(STATE_FILE)
    if raw is None:
        raw = _safe_json_load(STATE_BACKUP_FILE)
    state = reconcile_state(raw, CONTROLLER_MODE, LANE_SPECS)
    save_state(state)
    return state


def save_state(state: dict[str, Any]) -> None:
    state["updated_at"] = now_iso()
    encoded = json.dumps(state, ensure_ascii=False, indent=2)
    if STATE_FILE.exists():
        current = _safe_json_load(STATE_FILE)
        if current is not None:
            tmp_bak = STATE_BACKUP_FILE.with_suffix(".tmp")
            tmp_bak.write_text(
                json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            tmp_bak.replace(STATE_BACKUP_FILE)
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(encoded, encoding="utf-8")
    tmp.replace(STATE_FILE)
    tmp_bak = STATE_BACKUP_FILE.with_suffix(".tmp")
    tmp_bak.write_text(encoded, encoding="utf-8")
    tmp_bak.replace(STATE_BACKUP_FILE)


def parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=TZ)
        return dt.astimezone(TZ)
    except Exception:
        return None


def stable_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def project_id_from_url(url: str) -> Optional[str]:
    try:
        m = re.search(r"/g/(g-p-[A-Za-z0-9]+)", urllib.parse.urlparse(url).path)
        return m.group(1) if m else None
    except Exception:
        return None


PROJECT_ID = project_id_from_url(CHATGPT_PROJECT_URL)


def is_project_url(url: str) -> bool:
    if not REQUIRE_PROJECT_URL:
        return True
    if not CHATGPT_PROJECT_URL or not PROJECT_ID:
        return False
    try:
        parsed = urllib.parse.urlparse(url)
        return parsed.netloc.lower() in {"chatgpt.com", "www.chatgpt.com"} and (
            parsed.path.startswith(f"/g/{PROJECT_ID}")
        )
    except Exception:
        return False


def is_chat_url(url: str) -> bool:
    return is_project_url(url) and "/c/" in url and "local-chatgpt" not in url.lower()


def github_api(path: str) -> Any:
    url = f"https://api.github.com/repos/{GITHUB_REPO}/{path.lstrip('/')}"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "outrun-chat-controller-v05",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    request = urllib.request.Request(url, headers=headers)
    last_error: Optional[Exception] = None
    for delay in (0, 2, 5, 10):
        if delay:
            time.sleep(delay)
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code in {403, 429, 500, 502, 503, 504}:
                continue
            raise
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            continue
    raise RuntimeError(f"GitHub API failed for {path}: {last_error!r}")


def github_branch_head(branch: str) -> str:
    data = github_api(f"branches/{urllib.parse.quote(branch, safe='')}")
    return str(data["commit"]["sha"])


def github_recent_commits(branch: str) -> list[dict[str, Any]]:
    query = urllib.parse.urlencode({"sha": branch, "per_page": GITHUB_SCAN_LIMIT})
    data = github_api(f"commits?{query}")
    return data if isinstance(data, list) else []


def github_commit_detail(sha: str) -> dict[str, Any]:
    data = github_api(f"commits/{sha}")
    return data if isinstance(data, dict) else {}


def commit_paths(detail: dict[str, Any]) -> list[str]:
    result = []
    for item in detail.get("files") or []:
        if isinstance(item, dict) and item.get("filename"):
            result.append(str(item["filename"]))
    return result


def find_material_marker_commit(
    branch: str, job_id: str, role: str
) -> tuple[Optional[dict[str, Any]], Optional[dict[str, Any]]]:
    marker = f"[AUTO:{job_id}]"
    first_nonmaterial = None
    for row in github_recent_commits(branch):
        message = str(((row.get("commit") or {}).get("message") or ""))
        if marker not in message:
            continue
        sha = str(row.get("sha") or "")
        if not sha:
            continue
        detail = github_commit_detail(sha)
        paths = commit_paths(detail)
        if material_commit_ok(role, paths):
            return {
                "sha": sha,
                "message": message,
                "paths": paths,
            }, first_nonmaterial
        if first_nonmaterial is None:
            first_nonmaterial = {
                "sha": sha,
                "message": message,
                "paths": paths,
            }
    return None, first_nonmaterial


def read_prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8").strip()


BASE_PROMPT = read_prompt("base.md")
LOCALIZATION_PRODUCER_PROMPT = read_prompt("localization_producer.md")
LOCALIZATION_QA_PROMPT = read_prompt("localization_qa.md")
CONVERSION_PROMPT = read_prompt("conversion.md")


def render_full_prompt(lane: dict[str, Any], job: dict[str, Any]) -> str:
    base = BASE_PROMPT.format(
        repo=GITHUB_REPO,
        branch=lane["branch"],
        job_id=job["job_id"],
    )
    if lane["role"] == "localization_producer":
        role = LOCALIZATION_PRODUCER_PROMPT.format(
            lane=lane["name"], shard=lane["shard"]
        )
    elif lane["role"] == "localization_qa":
        inputs = job.get("qa_inputs") or []
        if inputs:
            qa_text = "\n".join(
                f"- {item['job_id']}@{item['sha']} (producer {item['lane']})"
                for item in inputs
            )
        else:
            qa_text = (
                "- Controller queue is empty. Scan current localization state for up to "
                "4 existing QA_PENDING/current-candidate items left by earlier runs. "
                "If none exist, return CONTROLLER_IDLE=NO_RUNNABLE_WORK without a commit."
            )
        role = LOCALIZATION_QA_PROMPT.format(qa_inputs=qa_text)
    else:
        role = CONVERSION_PROMPT.format(backend=lane["backend"])
    return base + "\n\n" + role


def render_continuation_prompt(
    lane: dict[str, Any],
    job: dict[str, Any],
    reason: str,
) -> str:
    transport_hint = ""
    if lane["role"] == "localization_producer":
        transport_hint = (
            " If DDS upload is too large for one GitHub connector call, do not stop: use "
            ".github/workflows/localization-binary-import-v05.yml via "
            "localization/graphics/binary_staging/v05/<JOB_ID>/ chunk files and manifest.json; "
            "the importer creates the material [AUTO:<JOB_ID>] DDS commit."
        )
    return (
        f"CONTINUE JOB_ID={job['job_id']} on {lane['branch']}.\n"
        f"{reason}\n"
        "This is the same atomic job, not a new task. Do not recap or re-plan. "
        "Resume from the current Git state and finish the assigned material work, validation, "
        f"and commit with [AUTO:{job['job_id']}]."
        f"{transport_hint} "
        "If no runnable work truly remains, use CONTROLLER_IDLE=NO_RUNNABLE_WORK."
    )


async def first_visible(page: Page, selectors: list[str], wait_ms: int = 3000):
    deadline = time.time() + wait_ms / 1000.0
    while time.time() < deadline:
        for frame in page.frames:
            for selector in selectors:
                try:
                    loc = frame.locator(selector).first
                    if await loc.count() and await loc.is_visible(timeout=150):
                        return loc
                except Exception:
                    pass
        await page.wait_for_timeout(200)
    return None


async def detect_busy(page: Page) -> bool:
    return (await first_visible(page, BUSY_SELECTORS, wait_ms=250)) is not None


async def last_assistant_text(page: Page) -> str:
    try:
        loc = page.locator(ASSISTANT_MESSAGE_SELECTOR)
        count = await loc.count()
        if count:
            return (await loc.nth(count - 1).inner_text(timeout=1500)).strip()
    except Exception:
        pass
    return ""


async def visible_surface_text(page: Page) -> str:
    chunks: list[str] = []
    for selector in (
        "[role='alert']",
        "[role='status']",
        "[data-sonner-toast]",
        "[data-testid*='error']",
        "dialog",
        "[role='dialog']",
    ):
        try:
            loc = page.locator(selector)
            for i in range(min(await loc.count(), 12)):
                item = loc.nth(i)
                if await item.is_visible(timeout=100):
                    text = (await item.inner_text(timeout=300)).strip()
                    if text:
                        chunks.append(text)
        except Exception:
            pass
    return "\n".join(chunks).lower()


async def detect_rate_limit(page: Page) -> bool:
    text = await visible_surface_text(page)
    return any(re.search(p, text, flags=re.I | re.S) for p in RATE_LIMIT_PATTERNS)


async def detect_conversation_limit(page: Page) -> bool:
    text = await visible_surface_text(page)
    if any(re.search(p, text, flags=re.I | re.S) for p in CONVERSATION_LIMIT_PATTERNS):
        return True
    composer = await first_visible(page, INPUT_SELECTORS, wait_ms=300)
    if composer is None:
        try:
            body = (await page.locator("body").inner_text(timeout=1200)).lower()
        except Exception:
            body = ""
        return any(
            re.search(p, body, flags=re.I | re.S)
            for p in CONVERSATION_LIMIT_PATTERNS
        )
    return False


async def ensure_logged_in(page: Page) -> bool:
    if not page.url or page.url == "about:blank":
        if CHATGPT_PROJECT_URL:
            await page.goto(CHATGPT_PROJECT_URL, wait_until="domcontentloaded", timeout=60000)
    if REQUIRE_PROJECT_URL and not is_project_url(page.url):
        await page.goto(CHATGPT_PROJECT_URL, wait_until="domcontentloaded", timeout=60000)
    composer = await first_visible(page, INPUT_SELECTORS, wait_ms=15000)
    if composer is not None:
        return True
    return False


async def ensure_thinking_high(page: Page) -> bool:
    if PREFERRED_THINKING_LEVEL.lower() != "high":
        return True

    selectors = [
        "button[aria-label='ChatGPT 모델 선택']",
        "button[aria-label='Select ChatGPT model']",
        "button[aria-label*='모델 선택']",
        "button[data-testid='model-switcher-dropdown-button']",
        "form button[aria-haspopup='menu']",
        "form button[aria-haspopup='listbox']",
    ]
    explicit_non_high = False
    candidates = []
    for selector in selectors:
        try:
            loc = page.locator(selector)
            for i in range(min(await loc.count(), 12)):
                item = loc.nth(i)
                if not await item.is_visible(timeout=100):
                    continue
                text = ((await item.inner_text(timeout=300)) or "").strip()
                aria = ((await item.get_attribute("aria-label")) or "").strip()
                combined = f"{text} {aria}".lower()
                if "high" in combined or "높음" in combined:
                    return True
                if any(x in combined for x in ("instant", "medium", "즉시", "중간")):
                    explicit_non_high = True
                candidates.append(item)
        except Exception:
            pass

    for item in candidates[:12]:
        try:
            await item.click(force=True, timeout=1500)
            await page.wait_for_timeout(250)
            options = [
                page.get_by_role("menuitemradio", name="High", exact=True),
                page.get_by_role("menuitem", name="High", exact=True),
                page.get_by_role("option", name="High", exact=True),
                page.get_by_text("High", exact=True),
                page.get_by_text("높음", exact=True),
            ]
            for option in options:
                try:
                    if await option.count() and await option.first.is_visible(timeout=150):
                        await option.first.click(force=True, timeout=1500)
                        await page.wait_for_timeout(300)
                        return True
                except Exception:
                    pass
            await page.keyboard.press("Escape")
        except Exception:
            try:
                await page.keyboard.press("Escape")
            except Exception:
                pass

    if explicit_non_high:
        log.warning("High reasoning was explicitly not selected and could not be changed")
        return False
    log.info("High reasoning control not discoverable; allowing send without false UI block")
    return True


async def composer_text(box) -> str:
    try:
        tag = (await box.evaluate("el => el.tagName")).lower()
        if tag in {"textarea", "input"}:
            return await box.input_value()
        return await box.evaluate("el => (el.innerText ?? el.textContent ?? '')")
    except Exception:
        return ""


async def send_message(page: Page, message: str) -> str:
    message = prepare_outgoing_message(message)
    if REQUIRE_PROJECT_URL and not is_project_url(page.url):
        return "wrong_project"
    box = await first_visible(page, INPUT_SELECTORS, wait_ms=8000)
    if box is None:
        return "composer_missing"
    try:
        try:
            await box.fill(message, timeout=12000)
        except Exception:
            await box.click(timeout=2000)
            await page.keyboard.press("Control+A")
            await page.keyboard.insert_text(message)

        actual = (await composer_text(box)).replace("\r\n", "\n").replace("\r", "\n")
        expected = message.replace("\r\n", "\n").replace("\r", "\n")
        if not actual.strip():
            return "composer_empty"
        ratio = len(actual) / max(1, len(expected))
        if ratio < 0.88 or ratio > 1.12:
            return "composer_verify_failed"
        await box.press("Enter", timeout=4000)
        await page.wait_for_timeout(1200)
        return "sent"
    except Exception:
        log.exception("send_message failed")
        return "send_failed"


async def wait_for_chat_url(page: Page, timeout_seconds: int = 10) -> Optional[str]:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if is_chat_url(page.url):
            return page.url
        await page.wait_for_timeout(300)
    return page.url if is_chat_url(page.url) else None


def should_recycle_completed_chat(lane: dict[str, Any]) -> bool:
    if lane.get("job"):
        return False
    if int(lane.get("chat_jobs", 0) or 0) >= CHAT_REUSE_MAX_JOBS:
        return True
    started = parse_iso(lane.get("chat_started_at"))
    if started and datetime.now(TZ) - started >= timedelta(minutes=CHAT_REUSE_MAX_AGE_MINUTES):
        return True
    return False


class StatusHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/healthz":
            last_tick = parse_iso(runtime.get("last_tick"))
            healthy = bool(last_tick and datetime.now(TZ) - last_tick < timedelta(seconds=max(90, TICK_SECONDS * 6)))
            body = b"ok\n" if healthy else b"stale\n"
            self.send_response(200 if healthy else 503)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        state = _safe_json_load(STATE_FILE) or {}
        payload = json.dumps(
            {"runtime": runtime, "state": state},
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        return


def start_status_server() -> None:
    def serve():
        server = ThreadingHTTPServer(("0.0.0.0", STATUS_PORT), StatusHandler)
        server.serve_forever()

    threading.Thread(target=serve, daemon=True).start()


class Controller:
    def __init__(self, context: BrowserContext, state: dict[str, Any]):
        self.context = context
        self.state = state
        self.pages: dict[str, Page] = {}

    async def get_page(self, lane: dict[str, Any]) -> Page:
        name = lane["name"]
        target = lane.get("chat_url")
        page = self.pages.get(name)
        if page and not page.is_closed():
            if target and page.url == target:
                return page
            if not target and CHATGPT_PROJECT_URL:
                await page.goto(CHATGPT_PROJECT_URL, wait_until="domcontentloaded", timeout=60000)
                return page

        if target:
            for existing in self.context.pages:
                if existing.url == target and not existing.is_closed():
                    self.pages[name] = existing
                    return existing

        page = await self.context.new_page()
        if target:
            try:
                await page.goto(target, wait_until="domcontentloaded", timeout=60000)
            except Exception:
                lane["chat_url"] = None
        if not lane.get("chat_url") and CHATGPT_PROJECT_URL:
            await page.goto(CHATGPT_PROJECT_URL, wait_until="domcontentloaded", timeout=60000)
        self.pages[name] = page
        return page

    async def recycle_chat(self, lane: dict[str, Any], reason: str) -> None:
        page = self.pages.get(lane["name"])
        if page and not page.is_closed():
            try:
                await page.close()
            except Exception:
                pass
        self.pages.pop(lane["name"], None)
        lane["chat_url"] = None
        lane["chat_started_at"] = None
        lane["chat_jobs"] = 0
        lane["retry_clicked_at"] = None
        lane["recycle_reason"] = reason
        job = lane.get("job")
        if isinstance(job, dict):
            job["status"] = "READY"
            job["force_full_prompt"] = True
            job["next_send_at"] = now_iso()
            job["baseline_assistant_hash"] = None
            job["response_hash"] = None
            job["response_last_changed_at"] = None
            job["verify_started_at"] = None
        save_state(self.state)
        write_runtime(status="chat_recycled", last_action=f"{lane['name']}: {reason}")

    def global_send_ready(self, lane: dict[str, Any], continuation: bool) -> bool:
        now = datetime.now(TZ)
        rate_until = parse_iso(self.state.get("rate_limit_until"))
        if rate_until and now < rate_until:
            return False

        last_global = parse_iso(self.state.get("last_global_send_at"))
        gap = SAME_CHAT_CONTINUATION_GAP_SECONDS if continuation else SEND_GAP_SECONDS
        if last_global and (now - last_global).total_seconds() < gap:
            return False

        last_lane = parse_iso(lane.get("last_send_at"))
        if last_lane and (now - last_lane).total_seconds() < gap:
            return False
        return True

    def mark_rate_limit(self) -> None:
        attempts = int(self.state.get("rate_limit_attempts", 0) or 0) + 1
        self.state["rate_limit_attempts"] = attempts
        delay = RATE_LIMIT_BACKOFF_SECONDS[min(attempts - 1, len(RATE_LIMIT_BACKOFF_SECONDS) - 1)]
        self.state["rate_limit_until"] = (
            datetime.now(TZ) + timedelta(seconds=delay)
        ).isoformat()
        save_state(self.state)
        write_runtime(
            status="rate_limited",
            last_action=f"global backoff {delay}s",
            rate_limit_until=self.state["rate_limit_until"],
        )

    def clear_rate_limit(self) -> None:
        if self.state.get("rate_limit_attempts") or self.state.get("rate_limit_until"):
            self.state["rate_limit_attempts"] = 0
            self.state["rate_limit_until"] = None
            save_state(self.state)

    def create_job_if_needed(self, lane: dict[str, Any]) -> None:
        if lane.get("job"):
            return
        idle_until = parse_iso(lane.get("idle_until"))
        if idle_until and datetime.now(TZ) < idle_until:
            return
        lane["idle_until"] = None

        if should_recycle_completed_chat(lane):
            lane["recycle_reason"] = "completed_chat_reuse_budget"
            lane["chat_url"] = None
            lane["chat_started_at"] = None
            lane["chat_jobs"] = 0

        if lane["role"] == "localization_qa":
            batch_size = int(lane.get("qa_batch_size") or QA_BATCH_SIZE)
            inputs = select_qa_batch(self.state, batch_size)
        else:
            inputs = []

        try:
            base_sha = github_branch_head(lane["branch"])
        except Exception as exc:
            lane["last_result"] = f"github_head_error:{exc!r}"
            return

        lane["job"] = make_job(self.state, lane, base_sha, qa_inputs=inputs)
        lane["last_result"] = "job_created"
        save_state(self.state)

    async def send_job(self, lane: dict[str, Any], page: Page) -> None:
        job = lane["job"]
        continuation = not bool(job.get("force_full_prompt", True))
        if not self.global_send_ready(lane, continuation):
            return

        next_send_at = parse_iso(job.get("next_send_at"))
        if next_send_at and datetime.now(TZ) < next_send_at:
            return

        if not await ensure_logged_in(page):
            lane["last_result"] = "login_required"
            write_runtime(status="login_required", last_action=f"{lane['name']} login/composer unavailable")
            return

        if await detect_rate_limit(page):
            self.mark_rate_limit()
            return

        if await detect_conversation_limit(page):
            await self.recycle_chat(lane, "conversation_length_limit")
            return

        if not await ensure_thinking_high(page):
            lane["last_result"] = "high_not_selected"
            job["next_send_at"] = (datetime.now(TZ) + timedelta(seconds=60)).isoformat()
            save_state(self.state)
            return

        baseline = stable_hash(await last_assistant_text(page))
        if job.get("github_read_limit_retry_same_chat"):
            prompt = LOCALIZATION_QUEUE_RECOVERY_MESSAGE
        elif job.get("github_tool_retry_same_chat"):
            prompt = GITHUB_TOOL_RECOVERY_MESSAGE
        elif job.get("force_full_prompt", True):
            prompt = render_full_prompt(lane, job)
        else:
            reason = "No valid material AUTO commit was found for the previous turn."
            if job.get("last_nonmaterial_sha"):
                paths = ", ".join((job.get("last_nonmaterial_paths") or [])[:6])
                reason = (
                    f"Commit {job['last_nonmaterial_sha'][:12]} had the marker but was non-material "
                    f"for this role. Changed paths: {paths or '(none)'}."
                )
            prompt = render_continuation_prompt(lane, job, reason)

        result = await send_message(page, prompt)
        if result != "sent":
            lane["last_result"] = f"send_{result}"
            if result in {"composer_missing", "wrong_project"}:
                await self.recycle_chat(lane, f"send_surface:{result}")
            else:
                job["next_send_at"] = (
                    datetime.now(TZ) + timedelta(seconds=30)
                ).isoformat()
                save_state(self.state)
            return

        now = datetime.now(TZ)
        self.state["last_global_send_at"] = now.isoformat()
        lane["last_send_at"] = now.isoformat()
        lane["last_result"] = "sent"
        job["status"] = "WAIT_RESPONSE"
        job["sent_at"] = now.isoformat()
        job["turn_count"] = int(job.get("turn_count", 0) or 0) + 1
        job["baseline_assistant_hash"] = baseline
        job["response_hash"] = None
        job["response_last_changed_at"] = None
        job["verify_started_at"] = None
        job["next_send_at"] = None
        job["force_full_prompt"] = False
        job["github_tool_retry_same_chat"] = False
        job["github_read_limit_retry_same_chat"] = False

        chat_url = await wait_for_chat_url(page)
        if chat_url:
            lane["chat_url"] = chat_url
            if not lane.get("chat_started_at"):
                lane["chat_started_at"] = now.isoformat()
        save_state(self.state)
        write_runtime(status="sent", last_action=f"{lane['name']} {job['job_id']} turn {job['turn_count']}")

    async def recover_retry_surface(self, lane: dict[str, Any], page: Page) -> bool:
        retry = await first_visible(page, RETRY_SELECTORS, wait_ms=250)
        if retry is None or await detect_busy(page):
            lane["retry_clicked_at"] = None
            return False

        # Old Retry/Try again controls can remain visible in message history.
        # Only act when the current page also shows a real generation/network error.
        surface = await visible_surface_text(page)
        if not retry_surface_has_platform_error(surface):
            lane["retry_clicked_at"] = None
            return False

        clicked_at = parse_iso(lane.get("retry_clicked_at"))
        if clicked_at is not None and datetime.now(TZ) - clicked_at < timedelta(seconds=45):
            return True

        try:
            await retry.click(force=True, timeout=1500)
            lane["retry_clicked_at"] = now_iso()
            save_state(self.state)
            write_runtime(status="retry_clicked", last_action=f"{lane['name']} platform retry")
            return True
        except Exception:
            # A stale control must never cause chat churn.
            lane["retry_clicked_at"] = now_iso()
            save_state(self.state)
            return True

    async def observe_response(self, lane: dict[str, Any], page: Page) -> None:
        job = lane["job"]
        if await self.recover_retry_surface(lane, page):
            return
        if await detect_rate_limit(page):
            self.mark_rate_limit()
            return
        if await detect_conversation_limit(page):
            await self.recycle_chat(lane, "conversation_length_limit")
            return
        if await detect_busy(page):
            lane["last_result"] = "generating"
            return

        sent_at = parse_iso(job.get("sent_at"))
        if sent_at and datetime.now(TZ) - sent_at > timedelta(seconds=RESPONSE_TIMEOUT_SECONDS):
            await self.recycle_chat(lane, "response_timeout")
            return

        text = await last_assistant_text(page)
        if not text:
            return
        response_hash = stable_hash(text)
        if response_hash == job.get("baseline_assistant_hash"):
            return

        if response_hash != job.get("response_hash"):
            job["response_hash"] = response_hash
            job["response_last_changed_at"] = now_iso()
            save_state(self.state)
            return

        changed_at = parse_iso(job.get("response_last_changed_at"))
        if not changed_at:
            job["response_last_changed_at"] = now_iso()
            save_state(self.state)
            return
        if datetime.now(TZ) - changed_at < timedelta(seconds=TURN_IDLE_GRACE_SECONDS):
            return

        github_unavailable = github_tool_unavailable_response(text)
        github_read_limited = github_read_limit_response(text)

        if github_read_limited and lane["role"] == "localization_producer":
            attempts = int(job.get("github_read_limit_recovery_attempts", 0) or 0) + 1
            job["github_read_limit_recovery_attempts"] = attempts
            job["github_read_limit_retry_same_chat"] = True
            job["status"] = "READY"
            job["next_send_at"] = (
                datetime.now(TZ) + timedelta(seconds=SAME_CHAT_CONTINUATION_GAP_SECONDS)
            ).isoformat()
            job["baseline_assistant_hash"] = None
            job["response_hash"] = None
            job["response_last_changed_at"] = None
            job["verify_started_at"] = None
            lane["last_result"] = f"github_read_limit_ranged_retry:{attempts}"
            save_state(self.state)
            write_runtime(
                status="github_read_recovery",
                last_action=(
                    f"{lane['name']} {job['job_id']} read-limit attempt {attempts}; "
                    "retry same chat with ranged queue instruction"
                ),
            )
            return

        if github_unavailable or github_read_limited:
            attempts = int(job.get("github_tool_recovery_attempts", 0) or 0) + 1
            job["github_tool_recovery_attempts"] = attempts
            job["github_tool_retry_same_chat"] = True
            job["status"] = "READY"
            job["next_send_at"] = (
                datetime.now(TZ) + timedelta(seconds=SAME_CHAT_CONTINUATION_GAP_SECONDS)
            ).isoformat()
            job["baseline_assistant_hash"] = None
            job["response_hash"] = None
            job["response_last_changed_at"] = None
            job["verify_started_at"] = None
            reason = "connector_unavailable" if github_unavailable else "github_read_limit"
            lane["last_result"] = f"{reason}_same_chat_retry:{attempts}"
            save_state(self.state)
            write_runtime(
                status="github_tool_recovery",
                last_action=(
                    f"{lane['name']} {job['job_id']} {reason} attempt {attempts}; "
                    "retry same chat with 진행해"
                ),
            )
            return

        job["github_tool_recovery_attempts"] = 0
        job["status"] = "VERIFY_GIT"
        job["verify_started_at"] = now_iso()
        job["last_response_excerpt"] = text[-1200:]
        save_state(self.state)

    async def verify_job(self, lane: dict[str, Any]) -> None:
        job = lane["job"]
        try:
            valid, nonmaterial = find_material_marker_commit(
                lane["branch"], job["job_id"], lane["role"]
            )
        except Exception as exc:
            lane["last_result"] = f"github_verify_error:{exc!r}"
            write_runtime(status="github_error", last_action=f"{lane['name']} verify", last_error=repr(exc))
            return

        if valid:
            self.clear_rate_limit()
            sha = valid["sha"]
            lane["last_commit_sha"] = sha
            lane["last_result"] = f"commit:{sha[:12]}"
            lane["chat_jobs"] = int(lane.get("chat_jobs", 0) or 0) + 1

            if lane["role"] == "localization_producer":
                enqueue_qa(
                    self.state,
                    producer_job_id=job["job_id"],
                    sha=sha,
                    lane=lane["name"],
                    branch=lane["branch"],
                )
            elif lane["role"] == "localization_qa":
                consume_qa_inputs(self.state, job.get("qa_inputs") or [])

            record_completed(self.state, lane, job, sha, "COMMIT")
            lane["job"] = None
            lane["idle_until"] = None
            save_state(self.state)
            write_runtime(status="job_complete", last_action=f"{lane['name']} {job['job_id']} -> {sha[:12]}")
            return

        verify_started = parse_iso(job.get("verify_started_at")) or datetime.now(TZ)
        if datetime.now(TZ) - verify_started < timedelta(seconds=COMMIT_DISCOVERY_GRACE_SECONDS):
            return

        response_text = str(job.get("last_response_excerpt") or "")
        if "CONTROLLER_IDLE=NO_RUNNABLE_WORK" in response_text:
            lane["last_result"] = "idle_no_runnable_work"
            lane["idle_until"] = (
                datetime.now(TZ) + timedelta(seconds=NO_WORK_RETRY_SECONDS)
            ).isoformat()
            record_completed(self.state, lane, job, None, "IDLE_NO_WORK")
            lane["job"] = None
            save_state(self.state)
            write_runtime(
                status="lane_idle",
                last_action=f"{lane['name']} no runnable work; retry later",
            )
            return

        if nonmaterial:
            job["last_nonmaterial_sha"] = nonmaterial["sha"]
            job["last_nonmaterial_paths"] = nonmaterial["paths"]
            lane["last_result"] = f"nonmaterial_marker:{nonmaterial['sha'][:12]}"
        else:
            lane["last_result"] = "response_without_commit"

        job["status"] = "READY"
        job["force_full_prompt"] = False
        job["next_send_at"] = (
            datetime.now(TZ) + timedelta(seconds=SAME_CHAT_CONTINUATION_GAP_SECONDS)
        ).isoformat()
        job["baseline_assistant_hash"] = None
        job["response_hash"] = None
        job["response_last_changed_at"] = None
        job["verify_started_at"] = None
        save_state(self.state)
        write_runtime(
            status="job_continue",
            last_action=f"{lane['name']} {job['job_id']} continues after turn {job['turn_count']}",
        )

    async def tick_lane(self, lane: dict[str, Any]) -> None:
        self.create_job_if_needed(lane)
        job = lane.get("job")
        if not isinstance(job, dict):
            return

        page = await self.get_page(lane)
        status = job.get("status")
        if status == "READY":
            await self.send_job(lane, page)
        elif status == "WAIT_RESPONSE":
            await self.observe_response(lane, page)
        elif status == "VERIFY_GIT":
            await self.verify_job(lane)
        else:
            job["status"] = "READY"
            job["force_full_prompt"] = True
            save_state(self.state)

    async def tick(self) -> None:
        write_runtime(
            status="running",
            last_action="tick",
            queue_summary={
                "qa_pending": len(self.state.get("qa_pending") or []),
                "lanes": {
                    name: {
                        "job_id": (lane.get("job") or {}).get("job_id"),
                        "job_status": (lane.get("job") or {}).get("status"),
                        "last_result": lane.get("last_result"),
                        "chat_jobs": lane.get("chat_jobs"),
                    }
                    for name, lane in self.state.get("lanes", {}).items()
                },
            },
        )

        if REQUIRE_PROJECT_URL and not CHATGPT_PROJECT_URL:
            write_runtime(status="project_url_missing", last_action="CHATGPT_PROJECT_URL is required")
            return
        if not AUTO_SEND:
            write_runtime(status="paused", last_action="AUTO_SEND=false")
            return

        for spec in LANE_SPECS:
            lane = self.state["lanes"][spec["name"]]
            try:
                await self.tick_lane(lane)
            except Exception as exc:
                log.exception("lane tick failed lane=%s", lane["name"])
                lane["last_result"] = f"lane_error:{type(exc).__name__}:{exc}"
                save_state(self.state)
                write_runtime(
                    status="lane_error",
                    last_action=f"{lane['name']} isolated failure",
                    last_error=repr(exc),
                )

    async def run(self) -> None:
        while True:
            try:
                await self.tick()
            except Exception as exc:
                log.exception("controller tick failed")
                write_runtime(status="controller_error", last_error=repr(exc))
            await asyncio.sleep(TICK_SECONDS)


async def async_main() -> None:
    start_status_server()
    state = load_state()
    write_runtime(status="connecting_browser", last_action="connect over CDP")

    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9222")
        if not browser.contexts:
            raise RuntimeError("Chrome CDP connected without a browser context")
        context = browser.contexts[0]
        controller = Controller(context, state)
        write_runtime(status="running", last_action="controller v0.5 started")
        await controller.run()


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
