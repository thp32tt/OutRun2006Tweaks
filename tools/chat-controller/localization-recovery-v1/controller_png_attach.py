"""Fail-closed, source-bound ChatGPT composer PNG uploads (localization A/B only).

Input is an operator-staged JSON manifest in /data/imagegen/pending_A.json or
pending_B.json. This module never invokes the paid Images API, starts Docker,
or marks an image as generated. UI attachment is not ImageGen completion.
"""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import zlib

ROOT = Path("/data/imagegen")
SHA = re.compile(r"[0-9a-f]{64}\Z")
TASK = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}\Z")
PREVIEW = (
    "[data-testid*='attachment'], [data-testid*='upload-preview'], "
    "[data-testid*='file-upload'], button[aria-label*='Remove file'], "
    "button[aria-label*='Remove attachment'], img[src^='blob:']"
)


def load_binding(role, root=ROOT):
    """Return (binding, reason). Missing/invalid inputs MUST NOT send text only."""
    if role not in ("A", "B"):
        return None, "NOT_A_PRODUCER"
    pilot = os.environ.get("OUTRUN_A_SINGLE_SMOKE_TASK_ID", "").strip()
    if pilot and not TASK.fullmatch(pilot):
        return None, "INVALID_PILOT_TASK_ID"
    if pilot and role != "A":
        return None, "PILOT_ROLE_BLOCKED"
    root = Path(root).resolve()
    if os.environ.get("OUTRUN_AB_TEXT_ROI_QUEUE", "false").lower() == "true":
        try:
            from app.text_roi_queue import next_binding as roi_next_binding
        except ModuleNotFoundError:
            from text_roi_queue import next_binding as roi_next_binding
        return roi_next_binding(role, root)
    if os.environ.get("OUTRUN_AB_BATCH_QUEUE", "false").lower() == "true":
        try:
            from app.ab_batch_queue import next_binding
        except ModuleNotFoundError:
            from ab_batch_queue import next_binding
        return next_binding(role, root)
    if role == "A" and os.environ.get("OUTRUN_A_TILE_BATCH_QUEUE", "false").lower() == "true":
        from app.tile_batch_queue import prepare_next_binding
        return prepare_next_binding(root)
    manifest = root / ("pending_" + role + ".json")
    if not manifest.is_file() or manifest.is_symlink():
        return None, "SOURCE_REFERENCE_NOT_BOUND"
    try:
        if manifest.stat().st_size > 256 * 1024:
            return None, "MANIFEST_TOO_LARGE"
        entry = json.loads(manifest.read_text(encoding="utf-8"))
        if not isinstance(entry, dict) or entry.get("role") != role:
            return None, "ROLE_MISMATCH"
        task = entry.get("task_id")
        digest = entry.get("png_sha256")
        source_digest = entry.get("source_dds_sha256")
        prompt = entry.get("prompt")
        rel = entry.get("png")
        if not isinstance(task, str) or not TASK.fullmatch(task):
            return None, "INVALID_TASK_ID"
        if pilot and task != pilot:
            return None, "PILOT_TASK_ID_MISMATCH"
        if not isinstance(digest, str) or not SHA.fullmatch(digest):
            return None, "INVALID_PNG_SHA"
        if not isinstance(source_digest, str) or not SHA.fullmatch(source_digest):
            return None, "INVALID_DDS_SHA"
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 25000:
            return None, "MISSING_APPROVED_PROMPT"
        if not isinstance(rel, str) or not rel.endswith(".png"):
            return None, "INVALID_PNG_PATH"
        base = (root / "inputs").resolve()
        target = (base / rel).resolve()
        if not target.is_relative_to(base) or target.is_symlink() or not target.is_file():
            return None, "INVALID_PNG_PATH"
        if target.stat().st_size > 32 * 1024 * 1024:
            return None, "PNG_TOO_LARGE"
        data = target.read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            return None, "PNG_SHA_MISMATCH"
        if len(data) < 45 or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
            return None, "INVALID_PNG"
        offset, seen_idat, seen_end = 8, False, False
        while offset + 12 <= len(data):
            size = struct.unpack_from(">I", data, offset)[0]
            end = offset + 12 + size
            if size > 32 * 1024 * 1024 or end > len(data):
                return None, "INVALID_PNG"
            kind = data[offset + 4:offset + 8]
            crc = struct.unpack_from(">I", data, end - 4)[0]
            if zlib.crc32(data[offset + 4:end - 4]) != crc:
                return None, "INVALID_PNG_CRC"
            if kind == b"IDAT":
                seen_idat = True
            if kind == b"IEND":
                seen_end = True
                if size != 0 or end != len(data):
                    return None, "INVALID_PNG"
                break
            offset = end
        if not seen_idat or not seen_end:
            return None, "INVALID_PNG"
        width, height = struct.unpack(">II", data[16:24])
        if not (1 <= width <= 8192 and 1 <= height <= 8192):
            return None, "INVALID_PNG_DIMENSIONS"
        if (root / "sent" / (role + "_" + task + ".json")).exists():
            return None, "ALREADY_SENT"
        return {
            "role": role, "task_id": task, "path": str(target),
            "png_sha256": digest, "source_dds_sha256": source_digest,
            "prompt": prompt, "dimensions": [width, height],
        }, None
    except (OSError, ValueError, UnicodeError, KeyError, TypeError, json.JSONDecodeError):
        return None, "INVALID_MANIFEST"


async def prepare_a_project_target(page, project_name, allow_saved_chat=False):
    """Find the exact ChatGPT project before starting a fresh A/B image chat.

    A new tab starts at chatgpt.com/, where the project-specific "New chat in"
    button does not exist. Resolve the configured project URL or discover the
    exact project in the sidebar, then verify BOTH its route and visible heading.
    Never fall back to a global new chat (which could send outside the project).
    """
    from urllib.parse import urljoin, urlsplit

    def _project_url(value):
        parsed = urlsplit(value)
        return (parsed.scheme == "https" and parsed.hostname == "chatgpt.com"
                and parsed.username is None and parsed.password is None
                and re.fullmatch(r"/g/[^/]+/project/?", parsed.path) is not None)

    try:
        current = urlsplit(page.url)
        if current.scheme != "https" or current.hostname != "chatgpt.com":
            return "TARGET_ORIGIN_NOT_CHATGPT"
        if allow_saved_chat and "/c/" in current.path and "local-chatgpt" not in page.url:
            await page.locator('[role="textbox"][contenteditable="true"]').first.wait_for(
                state="visible", timeout=12000)
            return "A_PROJECT_COMPOSER_READY"
        if not project_name:
            return "A_PROJECT_NAME_MISSING"

        if not _project_url(page.url):
            configured = (os.environ.get("CHATGPT_PROJECT_URL", "").strip()
                          or os.environ.get("LOCALIZATION_PROJECT_URL", "").strip())
            if configured:
                if not _project_url(configured):
                    return "A_PROJECT_URL_INVALID"
                await page.goto(configured, wait_until="domcontentloaded", timeout=30000)
            else:
                # The current ChatGPT sidebar renders project rows as DIVs
                # (role=button) with an explicit stable project ID, not an
                # anchor to the project home. Clicking the row only expands it.
                # Read the exact ID/label pair and navigate to the verified
                # project-home route; never click the global new-chat button.
                project_rows = page.locator(
                    '[data-app-action-sidebar-project-id]'
                    '[data-app-action-sidebar-project-label]')
                # The sidebar hydrates after DOMContentLoaded. A zero-count
                # immediately after navigation is not evidence of absence.
                try:
                    await project_rows.first.wait_for(
                        state="attached", timeout=12000)
                except Exception:
                    pass  # Older sidebar UI might expose links instead.
                project_matches = []
                for idx in range(min(await project_rows.count(), 100)):
                    row = project_rows.nth(idx)
                    label = await row.get_attribute(
                        'data-app-action-sidebar-project-label')
                    if label != project_name:
                        continue
                    project_id = await row.get_attribute(
                        'data-app-action-sidebar-project-id')
                    if not project_id or not re.fullmatch(
                            r'g-p-[A-Za-z0-9_-]+', project_id):
                        return "A_PROJECT_ID_INVALID"
                    project_matches.append(project_id)
                if len(project_matches) > 1:
                    return "A_PROJECT_LINK_AMBIGUOUS"
                if len(project_matches) == 1:
                    exact_project_url = (
                        "https://chatgpt.com/g/" + project_matches[0] + "/project")
                    await page.goto(exact_project_url,
                                    wait_until="domcontentloaded", timeout=30000)
                else:
                    # Compatibility with older anchor-based sidebar UI.
                    exact = page.get_by_text(project_name, exact=True)
                    try:
                        await exact.first.wait_for(state="visible", timeout=12000)
                    except Exception:
                        return "A_PROJECT_LINK_NOT_FOUND"
    
                    project_links = page.locator('a[href*="/g/"][href*="/project"]')
                    target_urls = []
                    untrusted_name_matches = 0
                    for idx in range(min(await project_links.count(), 100)):
                        link = project_links.nth(idx)
                        title = (await link.inner_text()).strip()
                        aria = (await link.get_attribute("aria-label") or "").strip()
                        if title == project_name or aria == project_name:
                            href = await link.get_attribute("href") or ""
                            target = urljoin(page.url, href)
                            if _project_url(target):
                                target_urls.append(target.split("?")[0])
                            else:
                                untrusted_name_matches += 1
                    if untrusted_name_matches:
                        return "A_PROJECT_LINK_UNTRUSTED"
                    target_urls = list(dict.fromkeys(target_urls))
                    if len(target_urls) == 1:
                        await page.goto(target_urls[0], wait_until="domcontentloaded", timeout=30000)
                    elif len(target_urls) > 1:
                        return "A_PROJECT_LINK_AMBIGUOUS"
                    else:
                        # Some ChatGPT sidebar versions use a project button/div
                        # rather than a link. A click is accepted only when the
                        # resulting URL is the project home and identity is proven.
                        candidates = (
                            page.get_by_role("button", name="New chat in " + project_name, exact=True),
                            page.get_by_role("button", name=project_name, exact=True),
                            exact,
                        )
                        clicked = False
                        for candidate in candidates:
                            if await candidate.count() == 1 and await candidate.first.is_visible():
                                await candidate.first.click(timeout=10000)
                                clicked = True
                                break
                        if not clicked:
                            return "A_PROJECT_LINK_NOT_FOUND"
                        try:
                            await page.wait_for_url("**/g/*/project", timeout=18000)
                        except Exception:
                            return "A_PROJECT_NAVIGATION_UNVERIFIED"
    
        if not _project_url(page.url):
            return "A_PROJECT_ROUTE_NOT_VERIFIED"
        try:
            await page.get_by_role("heading", name=project_name, exact=True).wait_for(
                state="visible", timeout=20000)
        except Exception:
            return "A_PROJECT_IDENTITY_NOT_VERIFIED"
        await page.locator('[role="textbox"][contenteditable="true"]').first.wait_for(
            state="visible", timeout=12000)
        return "A_PROJECT_COMPOSER_READY"
    except Exception:
        return "A_PROJECT_NAVIGATION_UNVERIFIED"


async def ensure_image_tool(page):
    """Select and prove the actual Create image tool pill in ChatGPT composer.

    ChatGPT can render duplicate responsive controls and localized labels. Only
    visible controls are eligible; identity is finally proven by picture_v2 pill.
    """
    async def first_visible(locator, limit=12):
        for i in range(min(await locator.count(),limit)):
            item=locator.nth(i)
            try:
                if await item.is_visible():
                    return item
            except Exception:
                continue
        return None

    try:
        pill=page.locator('[data-inline-selection-pill][data-system-hint-type="picture_v2"]')
        selected=await first_visible(pill)
        if selected is not None:
            return "CREATE_IMAGE_TOOL_SELECTED"

        menu_candidates=[
            page.get_by_role("button",name="Add files and more"),
            page.get_by_role("button",name="파일 및 기타 추가"),
            page.locator('button[aria-label*="Add files"]'),
            page.locator('button[aria-label*="파일"]'),
        ]
        menu=None
        for loc in menu_candidates:
            menu=await first_visible(loc)
            if menu is not None: break
        if menu is None:
            return "IMAGE_TOOL_MENU_MISSING"
        await menu.click(timeout=6000)

        option_candidates=[
            page.get_by_text("Create image",exact=True),
            page.get_by_text("이미지 만들기",exact=True),
            page.get_by_text("이미지 생성",exact=True),
            page.get_by_role("menuitem",name="Create image"),
            page.locator('[data-testid*="create-image"]'),
        ]
        option=None
        for loc in option_candidates:
            option=await first_visible(loc)
            if option is not None: break
        if option is None:
            try: await page.keyboard.press("Escape")
            except Exception: pass
            return "CREATE_IMAGE_OPTION_MISSING"
        await option.click(timeout=7000)

        # Responsive UIs may re-render the composer after selection.
        for _ in range(12):
            selected=await first_visible(pill)
            if selected is not None:
                return "CREATE_IMAGE_TOOL_SELECTED"
            await page.wait_for_timeout(250)
        return "CREATE_IMAGE_PILL_NOT_VISIBLE"
    except Exception as exc:
        return "CREATE_IMAGE_TOOL_NOT_VERIFIED:"+type(exc).__name__


async def _attachment_file_input(page):
    """Return the current ChatGPT composer file input across responsive DOM variants."""
    candidates = (
        'input[type="file"][aria-label="Attach files"]',
        'input[type="file"][aria-label="Attach photos"]',
        'input[type="file"][aria-label="Attach photos or videos"]',
        'input[type="file"][accept*="image"]',
    )
    for selector in candidates:
        loc = page.locator(selector)
        count = await loc.count()
        if count:
            return loc.first
    return None


async def _clear_composer_attachments(page):
    """Remove stale composer attachments without touching persisted chat turns."""
    try:
        box = page.locator('[role="textbox"][contenteditable="true"]').first
        scope = box.locator("xpath=ancestor::form[1]")
        if await scope.count() == 0:
            return
        remove = scope.locator(
            'button[aria-label^="Remove"], button[aria-label*="Remove file"], '
            'button[aria-label*="Remove attachment"], button[aria-label*="삭제"], '
            'button[aria-label*="제거"]'
        )
        for _ in range(8):
            visible = None
            for i in range(min(await remove.count(), 12)):
                item = remove.nth(i)
                try:
                    if await item.is_visible():
                        visible = item
                        break
                except Exception:
                    continue
            if visible is None:
                break
            await visible.click(timeout=4000)
            await page.wait_for_timeout(250)
    except Exception:
        # Fresh project composer normally has no attachment. Cleanup is best-effort;
        # upload verification below remains fail-closed.
        return


async def _wait_for_attachment_previews(page, expected_names, timeout):
    """Prove N completed composer attachments without depending on filename alt text.

    ChatGPT's 2026 composer no longer consistently exposes the original filename
    in image alt/remove aria labels. We therefore accept one of several
    attachment-card signals, but only inside the active composer form and only
    after upload/progress indicators have disappeared.
    """
    await page.wait_for_function(
        r"""({names}) => {
          const visible = e => !!(e && e.getClientRects().length);
          const box = [...document.querySelectorAll('[role="textbox"][contenteditable="true"]')]
              .find(visible);
          if (!box) return false;
          const scope = box.closest('form') || box.parentElement || document;
          const expected = names.length;

          const uploads = [...scope.querySelectorAll(
            '[aria-label*="Uploading"], [aria-label*="uploading"], ' +
            '[aria-label*="업로드 중"], [role="progressbar"], ' +
            '[data-state="loading"], [data-testid*="uploading"]'
          )].filter(visible);
          if (uploads.length) return false;

          const normalize = x => (x || '').trim();
          const sameName = (value, name) => {
            value = normalize(value);
            if (!value) return false;
            const stem = name.replace(/\.png$/i, '');
            return value === name || value.includes(name) ||
                   value === stem || value.includes(stem);
          };

          const named = new Set();
          const labelled = [...scope.querySelectorAll(
            '[aria-label], [title], [data-file-name], img[alt]'
          )];
          for (const el of labelled) {
            if (!visible(el)) continue;
            const values = [
              el.getAttribute('aria-label'), el.getAttribute('title'),
              el.getAttribute('data-file-name'), el.getAttribute('alt')
            ];
            names.forEach((name, idx) => {
              if (values.some(v => sameName(v, name))) named.add(idx);
            });
          }
          if (named.size >= expected) return true;

          const removeButtons = [...scope.querySelectorAll('button[aria-label]')]
            .filter(el => {
              if (!visible(el)) return false;
              const a = (el.getAttribute('aria-label') || '').toLowerCase();
              return a.includes('remove') || a.includes('삭제') || a.includes('제거');
            });

          const cards = [...scope.querySelectorAll(
            '[data-testid*="attachment"], [data-testid*="upload-preview"], ' +
            '[data-testid*="file-upload"], [data-testid*="composer-attachment"]'
          )].filter(visible);

          const previewImages = [...scope.querySelectorAll('img')]
            .filter(img => {
              if (!visible(img) || !img.complete ||
                  img.naturalWidth <= 0 || img.naturalHeight <= 0) return false;
              const src = img.currentSrc || img.src || '';
              if (src.startsWith('blob:') || src.startsWith('data:image')) return true;
              return !!img.closest(
                '[data-testid*="attachment"], [data-testid*="upload-preview"], ' +
                '[data-testid*="file-upload"], [data-testid*="composer-attachment"], ' +
                'button[aria-label*="Remove"], button[aria-label*="삭제"], ' +
                'button[aria-label*="제거"]'
              );
            });

          // set_input_files() can leave the selected files on one of the hidden
          // composer inputs. This is strong evidence when coupled with no
          // visible upload/progress state.
          const selectedFiles = Math.max(0, ...[...scope.querySelectorAll('input[type="file"]')]
            .map(i => i.files ? i.files.length : 0));

          return removeButtons.length >= expected ||
                 cards.length >= expected ||
                 previewImages.length >= expected ||
                 selectedFiles >= expected;
        }""",
        arg={"names": expected_names},
        timeout=timeout,
    )


async def attach_batch_pngs(page, binding):
    """Upload 2..5 independent PNGs and verify current composer preview state."""
    paths = binding["paths"]
    expected = [Path(s).name for s in paths]
    if not (2 <= len(paths) <= 5) or len(set(expected)) != len(paths):
        return "BATCH_MUST_HAVE_TWO_TO_FIVE_DISTINCT_PNG"
    try:
        if not page.url.startswith("https://chatgpt.com/"):
            return "TARGET_ORIGIN_NOT_CHATGPT"
        await page.locator('[role="textbox"][contenteditable="true"]').first.wait_for(
            state="visible", timeout=12000)
        await _clear_composer_attachments(page)
        inp = await _attachment_file_input(page)
        if inp is None:
            return "ATTACH_FILES_INPUT_NOT_FOUND"
        await inp.set_input_files(paths, timeout=40000)
        await page.wait_for_timeout(750)
        await _wait_for_attachment_previews(page, expected, 120000)
        return "ATTACHMENT_UPLOAD_COMPLETED"
    except Exception:
        return "ATTACHMENT_UPLOAD_NOT_VERIFIED"


async def attach_png(page, binding):
    """Upload one PNG and verify a completed composer attachment preview."""
    if len(binding.get("paths", [])) > 1:
        return await attach_batch_pngs(page, binding)
    filename = Path(binding["path"]).name
    try:
        await page.locator('[role="textbox"][contenteditable="true"]').first.wait_for(
            state="visible", timeout=12000)
        if not page.url.startswith("https://chatgpt.com/"):
            return "TARGET_ORIGIN_NOT_CHATGPT"
        await _clear_composer_attachments(page)
        inp = await _attachment_file_input(page)
        if inp is None:
            return "ATTACH_FILES_INPUT_NOT_FOUND"
        await inp.set_input_files(binding["path"], timeout=25000)
        await page.wait_for_timeout(750)
        await _wait_for_attachment_previews(page, [filename], 90000)
        return "ATTACHMENT_UPLOAD_COMPLETED"
    except Exception:
        return "ATTACHMENT_UPLOAD_NOT_VERIFIED"


async def verify_submission_receipt(page, task_id, filename):
    """Require an actual persisted ChatGPT user turn with N uploaded PNGs.

    Current project UI uses data-markdown-text-tone=user-message and
    data-chatgpt-search-unit-key, not the old data-message-author-role.
    Neither a typed prompt nor the composer preview is proof of submission.
    """
    filenames = filename if isinstance(filename, list) else [filename]
    count = len(filenames)
    try:
        await page.wait_for_function(
            """({task,count}) => {
                if(location.hostname!=='chatgpt.com' ||
                   !location.pathname.includes('/c/') ||
                   location.href.includes('local-chatgpt'))return false;
                const target=[...document.querySelectorAll('[data-markdown-text-tone="user-message"]')]
                    .find(n=>(n.innerText||'').includes('UPLOAD_TASK_ID='+task));
                const user=target?.closest('[data-chatgpt-search-unit-key]') ||
                           target?.closest('[data-content-search-unit-key]');
                if(!user)return false;
                const thumbs=[...user.querySelectorAll('img')]
                    .filter(img=>img.complete && img.naturalWidth>16 && img.naturalHeight>16 &&
                           !!img.getClientRects().length && !!(img.currentSrc||img.src));
                // The 2026 UI varies attachment alt text (User attachment,
                // Uploaded image, or empty) by composer surface. Because this
                // is scoped to the exact persisted user turn carrying our
                // unique UPLOAD_TASK_ID, image count is the stable proof.
                return thumbs.length===count;
            }""", arg={"task":task_id,"count":count}, timeout=45000)
        return "PERSISTED_CHAT_USER_MESSAGE_WITH_IMAGE_CONFIRMED"
    except Exception:
        return "SEND_UNVERIFIED"


def mark_sent(binding, root=ROOT, status="CHAT_MESSAGE_SENT_ATTACHMENT_UI_VERIFIED_NOT_IMAGEGEN_PASS"):
    """Prevent re-sending a stale source on later automatic schedules."""
    target = Path(root) / "sent" / (
        binding["role"] + "_" + binding["task_id"] + ".json"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "task_id": binding["task_id"], "role": binding["role"],
        "png_sha256": binding["png_sha256"],
        "source_dds_sha256": binding["source_dds_sha256"],
        "status": status,
        "submitted_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "tiles": [
            {"filename": x["filename"], "png_sha256": x["sha256"]}
            for x in binding.get("tiles", [])
        ],
    }
    with target.open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    return str(target)

async def send_analysis_message_with_attachment(page, binding):
    """Attach one original HD PNG and send an analysis-only prompt.

    Unlike A/B ImageGen production, this deliberately does NOT select the
    Create image tool. It uses the normal ChatGPT composer with one image
    attachment so the assistant can visually inspect the source.
    """
    status = await attach_png(page, binding)
    if status != "ATTACHMENT_UPLOAD_COMPLETED":
        return "SOURCE_REFERENCE_NOT_BOUND:" + status
    task_id = binding.get("task_id", "")
    message = binding.get("prompt", "")
    if not isinstance(task_id, str) or not TASK.fullmatch(task_id):
        return "ANALYSIS_TASK_ID_INVALID"
    if not isinstance(message, str) or not message.strip() or len(message) > 26000:
        return "ANALYSIS_PROMPT_INVALID"
    message += "\n\nUPLOAD_TASK_ID=" + task_id + " (분석 추적용이며 JSON task_id에도 동일하게 답하세요)"
    try:
        box = page.locator('[role="textbox"][contenteditable="true"]').first
        await box.wait_for(state="visible", timeout=12000)
        # Keep the already-uploaded attachment in the rich composer.
        await box.click(timeout=5000)
        await box.press("End", timeout=3000)
        await page.keyboard.insert_text(message)
        actual = await box.evaluate("el => (el.innerText ?? el.textContent ?? '')")
        if ("UPLOAD_TASK_ID=" + task_id) not in (actual or ""):
            return "ANALYSIS_COMPOSER_TASK_ID_MISSING"
        try:
            await box.press("Enter", timeout=5000)
        except Exception:
            await page.keyboard.press("Enter")
        await page.wait_for_timeout(1500)
        proof = await verify_submission_receipt(
            page, task_id, Path(binding["path"]).name)
        if proof != "PERSISTED_CHAT_USER_MESSAGE_WITH_IMAGE_CONFIRMED":
            body_text = await page.locator("body").inner_text(timeout=5000)
            if "/c/" not in page.url or task_id not in body_text:
                return "SEND_UNVERIFIED"
        return "sent"
    except Exception:
        return "ANALYSIS_SEND_FAILED"