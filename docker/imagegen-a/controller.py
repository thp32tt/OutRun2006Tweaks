"""One A tab, one generation, one automatic self-QA. No legacy scheduler."""
import asyncio
import fcntl
import json
import os
import re
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from playwright.async_api import async_playwright
from .qa import inspect, sha
from .fetch_source import fetch

ROOT = Path(os.getenv("DATA_ROOT", "/data"))
INPUT = Path(os.getenv("INPUT_ROOT", "/opt/outrun/input"))
TASK = os.getenv("TASK_ID", "OUTRUN-NEW-A-Q217-20261013-142553")
assert re.fullmatch(r"[A-Za-z0-9_.-]{1,96}", TASK)
OUT = ROOT / "results" / TASK
STATE = OUT / "state.json"
SOURCE_SHA = "56b3834649568383293786e862025351d0f2379ec632592cf40d78c532a50b15"
BOX = "#prompt-textarea"
SEND = "button[data-testid='send-button']"
STOP = "button[data-testid='stop-button']"
USER = "[data-message-author-role='user']"
ASSISTANT = "[data-message-author-role='assistant']"
DOWNLOAD = "button[aria-label*='Download'],button[aria-label*='다운로드'],button[title*='Download'],button[title*='다운로드']"

def read_state():
    return json.loads(STATE.read_text()) if STATE.exists() else {"phase": "READY"}

def save(phase, **extra):
    data = read_state()
    data.update(phase=phase, task_id=TASK, updated=datetime.now(timezone.utc).isoformat(), **extra)
    OUT.mkdir(parents=True, exist_ok=True)
    temp = STATE.with_suffix(".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    temp.replace(STATE)
    print(json.dumps({"task_id": TASK, "phase": phase}, ensure_ascii=False), flush=True)

async def upload(page, paths):
    # Use actual composer file inputs, not a GitHub image or a tool preview.
    inputs = page.locator("input[type=file]")
    if not await inputs.count():
        attach = page.locator("[data-testid='composer-plus-btn'],[data-testid='composer-attach-button'],button[aria-label*='Attach'],button[aria-label*='첨부']").first
        await attach.click(timeout=10000)
        menu = page.get_by_text(re.compile("Upload photos|Add photos|사진.*파일|파일.*추가", re.I)).first
        if await menu.count():
            async with page.expect_file_chooser(timeout=10000) as chooser:
                await menu.click()
            await (await chooser.value).set_files([str(p) for p in paths])
        else:
            await page.locator("input[type=file]").last.set_input_files([str(p) for p in paths])
    else:
        await inputs.last.set_input_files([str(p) for p in paths])
    # Require visible attachment controls in the composer and wait for upload to settle.
    await page.wait_for_function("""n => {
      const b=document.querySelector('#prompt-textarea');
      const c=b?.closest('form'); if(!c) return false;
      const chips=c.querySelectorAll('[data-testid*=attachment],button[aria-label*=Remove],button[aria-label*=삭제]');
      return [...chips].filter(x=>x.getClientRects().length).length>=n &&
        !c.querySelector('[role=progressbar],[aria-busy=true]');
    }""", arg=len(paths), timeout=120000)

async def submit(page, prompt, marker, phase):
    box = page.locator(BOX)
    await box.fill(prompt + "\n\n" + marker + " (추적 ID: 이미지에 표시하지 마)")
    await page.locator(SEND).wait_for(state="visible", timeout=30000)
    # Persist BEFORE click: any crash or ambiguous send must never auto-resend.
    save(phase + "_SUBMITTING", conversation_url=page.url, marker=marker)
    await page.locator(SEND).click(timeout=120000)
    await page.locator(USER).filter(has_text=marker).last.wait_for(timeout=60000)
    save(phase + "_SENT", conversation_url=page.url)

async def new_answer(page, count, timeout=1200):
    for _ in range(timeout // 2):
        answers = page.locator(ASSISTANT)
        if await answers.count() > count and not await page.locator(STOP).count():
            last = answers.last
            if (await last.inner_text()).strip() or await last.locator("img").count():
                return last
        await asyncio.sleep(2)
    raise RuntimeError("RESPONSE_TIMEOUT")

async def capture(page, count):
    # Only inspect an assistant turn created AFTER the generation prompt.
    for _ in range(600):
        answers = page.locator(ASSISTANT)
        if await answers.count() > count and not await page.locator(STOP).count():
            last = answers.last
            article = last.locator("xpath=ancestor::article[1]")
            scope = article if await article.count() else last
            pictures = scope.locator("img")
            if await pictures.count():
                await pictures.last.hover()
            buttons = scope.locator(os.getenv("IMAGE_DOWNLOAD_SELECTOR", DOWNLOAD))
            if await buttons.count():
                if await buttons.count() != 1:
                    raise RuntimeError("AMBIGUOUS_OUTPUT_DOWNLOADS")
                async with page.expect_download(timeout=60000) as event:
                    await buttons.first.click()
                download = await event.value
                candidate = OUT / "generated.png"
                await download.save_as(candidate)
                if candidate.stat().st_size > 64 * 1024 * 1024:
                    raise RuntimeError("OUTPUT_TOO_LARGE")
                return candidate
        await asyncio.sleep(2)
    raise RuntimeError("IMAGE_OUTPUT_MISSING_OR_UI_SELECTOR_CHANGED")

async def run():
    assert os.getenv("CHAT_SLOTS", "1") == "1", "A_ONLY"
    assert os.getenv("AUTO_SEND", "true").lower() == "true", "AUTO_SEND_DISABLED"
    source = fetch(INPUT / "source.json", Path(os.getenv("SOURCE_ROOT", "/sources")))
    if sha(source) != SOURCE_SHA: raise RuntimeError("SOURCE_SHA_MISMATCH")
    from PIL import Image
    with Image.open(source) as im:
        im.load()
        if im.size != (2048, 2048) or im.mode != "RGBA": raise RuntimeError("SOURCE_FORMAT")
    old = read_state()
    if old["phase"] not in ("READY", "WAITING_FOR_LOGIN"):
        # Resume is deliberately fail-closed; manual review of the existing chat first.
        print("Existing task checkpoint retained; no automatic duplicate send", flush=True)
        return
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else await context.new_page()
        if len(context.pages) != 1: raise RuntimeError("EXPECTED_ONE_A_TAB")
        url = os.getenv("CHATGPT_PROJECT_URL", "https://chatgpt.com/")
        if urlparse(url).scheme != "https" or urlparse(url).hostname != "chatgpt.com":
            raise RuntimeError("INVALID_CHATGPT_URL")
        await page.goto(url, wait_until="domcontentloaded")
        save("WAITING_FOR_LOGIN")
        await page.locator(BOX).wait_for(state="visible", timeout=3600000)
        if await page.locator(USER).count(): raise RuntimeError("FRESH_A_CHAT_REQUIRED")
        save("UPLOADING", source_sha256=SOURCE_SHA)
        await upload(page, [source])
        count = await page.locator(ASSISTANT).count()
        prompt = (INPUT / "prompt.txt").read_text()
        (OUT / "generation_prompt.txt").write_text(prompt)
        await submit(page, prompt, "GEN_" + TASK, "GENERATION")
        candidate = await capture(page, count)
        report = inspect(source, candidate, OUT)
        (OUT / "mechanical_qa.json").write_text(json.dumps(report, indent=2))
        save("OUTPUT_CAPTURED", candidate_sha256=report["candidate_sha256"], mechanical=report["mechanical"])
        # Same A tab; attach exact saved output + source so self-QA examines bytes.
        await upload(page, [source, candidate])
        qa_prompt = '''이미지를 생성하거나 수정하지 말고 QA만 해줘. 첫 첨부는 영문 원본, 두 번째는 저장된 생성 결과야.
START→출발, GOAL→골의 정확한 철자/획/가독성, 원본 전체 배치/방향/알파, 잘림/겹침, 영문 잔상, 로고/지도/경로 등 보호 아트 변경을 비교해.
번역문 전체 길이/underfill 차이 자체는 반려 사유가 아니야. native/75%/50% 가독성을 구분하고 실제로 확인 못 한 항목은 UNKNOWN으로 남겨.
JSON만 반환해: {"verdict":"PASS|REWORK|HOLD","checks":{"hangul":"PASS|FAIL|UNKNOWN","layout":"PASS|FAIL|UNKNOWN","protected_art":"PASS|FAIL|UNKNOWN","readability":"PASS|FAIL|UNKNOWN"},"defects":[{"region":"좌표 또는 위치","reason":"구체적인 근거"}]}. 이것은 생산자 자체 QA이며 독립 검수나 게임 PASS가 아니야.'''
        (OUT / "qa_prompt.txt").write_text(qa_prompt)
        count = await page.locator(ASSISTANT).count()
        await submit(page, qa_prompt, "QA_" + TASK, "QA")
        answer = await new_answer(page, count, 600)
        answer_text = await answer.inner_text()
        (OUT / "visual_self_qa.txt").write_text(answer_text)
        verdict = "HOLD"
        try:
            clean = re.sub(r"^```(?:json)?\s*|\s*```$", "", answer_text.strip())
            visual = json.loads(clean)
            checks = visual["checks"]
            if visual["verdict"] == "REWORK" or "FAIL" in checks.values(): verdict = "REWORK"
            elif visual["verdict"] == "PASS" and all(checks.get(k) == "PASS" for k in ("hangul","layout","protected_art","readability")):
                verdict = "SELF_QA_PASS_REQUIRES_INDEPENDENT_REVIEW"
        except (ValueError, KeyError, TypeError, AttributeError): pass
        if report["mechanical"] == "FAIL": verdict = "REWORK"
        save("COMPLETE", self_qa=verdict, independent_qa="NOT_RUN", RUNTIME_VALIDATION="UNTESTED", DDS="NOT_BUILT", official_promotion=False)

class Status(BaseHTTPRequestHandler):
    def do_GET(self):
        # Never serve browser profile, cookies, or conversation screenshots.
        data = json.dumps(read_state(), ensure_ascii=False).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers(); self.wfile.write(data)
    def log_message(self, *args): pass

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    lock = (ROOT / "a.lock").open("w")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    server = ThreadingHTTPServer(("0.0.0.0", 8787), Status)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try: asyncio.run(run())
    except Exception as exc:
        save("HOLD", reason=str(exc)[:500], resume_policy="NO_AUTO_RESEND")
    # Keep noVNC/status available after success/HOLD; never schedule another task.
    threading.Event().wait()

if __name__ == "__main__": main()
