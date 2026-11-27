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


async def selected_image_tool(page):
    """Prove an active composer selection, never a menu option or sidebar image.

    ChatGPT has used picture_v2 hint pills and newer labelled selection chips.
    The latter count ONLY when they are a selected composer chip, not when
    ordinary text or an Images menu item happens to be visible.
    """
    labels = frozenset(("create image", "images", "이미지 만들기",
                        "이미지 생성", "이미지"))
    for css in (
        '[data-inline-selection-pill]',
        '[data-testid="composer-tool-chip"]',
        '[data-testid="tool-selection-pill"]',
    ):
        loc = page.locator(css)
        try:
            count = min(await loc.count(), 12)
        except Exception:
            continue
        for i in range(count):
            item = loc.nth(i)
            try:
                if not await item.is_visible():
                    continue
                hint = await item.get_attribute("data-system-hint-type")
                if hint == "picture_v2":
                    return True
                text = (await item.inner_text()).strip().casefold()
                if text in labels:
                    return True
            except Exception:
                continue
    # Current UI revisions can render the active tool as a pressed/stateful
    # composer button instead of a dedicated selection pill. Restrict this
    # fallback to the active composer form and exact image-tool labels.
    try:
        active = await page.evaluate(
            r"""labels => {
              const visible=e=>!!(e&&e.getClientRects&&e.getClientRects().length);
              const box=[...document.querySelectorAll(
                '[role="textbox"][contenteditable="true"]')].find(visible);
              if(!box)return false;
              const scope=box.closest('form')||box.parentElement?.parentElement;
              if(!scope)return false;
              const normalized=x=>(x||'').replace(/\s+/g,' ').trim().toLowerCase();
              return [...scope.querySelectorAll(
                'button[aria-pressed="true"],button[data-state="on"],'+
                'button[data-state="active"],[aria-selected="true"]'
              )].some(e=>{
                if(!visible(e))return false;
                const text=normalized(
                  e.getAttribute('aria-label')||e.getAttribute('title')||
                  e.innerText||e.textContent);
                return labels.includes(text);
              });
            }""",
            ["create image","images","이미지 만들기","이미지 생성","이미지"],
        )
        if active:
            return True
    except Exception:
        pass
    return False


async def ensure_image_tool(page):
    """Select Images/이미지 in *current* More menu; verify active composer chip.

    Never send an ImageGen message merely because a menu item was clicked.
    If selection is absent the caller records a pre-send retry, not a send.
    The official UI currently documents More -> Images, while older pages
    used Add files and more -> Create image.
    """
    async def first_visible(locator, limit=10):
        try:
            count=min(await locator.count(), limit)
        except Exception:
            return None
        for i in range(count):
            item=locator.nth(i)
            try:
                if await item.is_visible():
                    return item
            except Exception:
                continue
        return None

    try:
        if await selected_image_tool(page):
            return "CREATE_IMAGE_TOOL_SELECTED"

        menus=[
            page.locator('button[data-testid="composer-plus-btn"]'),
            page.locator('button[data-testid="composer-tools-button"]'),
            page.get_by_role("button",name="More",exact=True),
            page.get_by_role("button",name="더보기",exact=True),
            page.get_by_role("button",name="더 보기",exact=True),
            page.get_by_role("button",name="Add files and more",exact=True),
            page.get_by_role("button",name="파일 및 기타 추가",exact=True),
            page.get_by_role("button",name="Tools",exact=True),
            page.get_by_role("button",name="도구",exact=True),
            page.locator('button[aria-label="More"]'),
            page.locator('button[aria-label*="Add files"]'),
            page.locator('button[aria-label*="파일"]'),
        ]
        opened=False
        option_seen=False
        for candidate in menus:
            menu=await first_visible(candidate)
            if menu is None:
                continue
            try:
                await menu.click(timeout=6000)
                opened=True
            except Exception:
                continue
            # On a loaded N100 renderer the tool popover can hydrate well after
            # the button click. Do not diagnose a missing Images option from the
            # same event-loop tick. Poll bounded visible interactive controls.
            option=None
            for _ in range(12):  # <= 3.6s, no extra queue/ImageGen polling
                options=[
                    page.get_by_role("menuitem",name="Images",exact=True),
                    page.get_by_role("menuitem",name="이미지",exact=True),
                    page.get_by_role("menuitem",name="Create image",exact=True),
                    page.get_by_role("menuitem",name="Create an image",exact=True),
                    page.get_by_role("menuitem",name="이미지 만들기",exact=True),
                    page.get_by_role("menuitem",name="이미지 생성",exact=True),
                    page.get_by_role("menuitemradio",name="Images",exact=True),
                    page.get_by_role("menuitemradio",name="이미지",exact=True),
                    page.get_by_role("menuitemradio",name="Create image",exact=True),
                    page.locator('[role="menu"] button').filter(has_text="Images"),
                    page.locator('[role="menu"] button').filter(has_text="이미지"),
                    page.locator('[data-testid*="create-image"]'),
                ]
                for loc in options:
                    option=await first_visible(loc)
                    if option is not None:
                        break
                if option is None:
                    # UI labels/testids move frequently. Search only visible
                    # interactive controls inside an open menu/popover/dialog,
                    # using an exact allow-list; never click arbitrary text.
                    try:
                        handle=await page.evaluate_handle(
                            r"""labels => {
                              const visible=e=>!!(e&&e.getClientRects&&e.getClientRects().length);
                              const norm=x=>(x||'').replace(/\s+/g,' ').trim().toLowerCase();
                              const roots=[...document.querySelectorAll(
                                '[role="menu"],[role="listbox"],[role="dialog"],'+
                                '[data-radix-menu-content],[data-radix-popper-content-wrapper]'
                              )].filter(visible);
                              for(const root of roots){
                                for(const e of root.querySelectorAll(
                                  'button,[role="menuitem"],[role="menuitemradio"],'+
                                  '[role="option"],[tabindex="0"]')){
                                  if(!visible(e))continue;
                                  const label=norm(e.getAttribute('aria-label')||
                                    e.getAttribute('title')||e.innerText||e.textContent);
                                  if(labels.includes(label))return e;
                                }
                              }
                              return null;
                            }""",
                            ["images","create image","create an image",
                             "이미지","이미지 만들기","이미지 생성"],
                        )
                        element=handle.as_element()
                        if element is not None:
                            option=element
                    except Exception:
                        option=None
                if option is not None:
                    break
                await page.wait_for_timeout(300)
            if option is None:
                try:
                    await page.keyboard.press("Escape")
                except Exception:
                    pass
                continue
            option_seen=True
            await option.click(timeout=7000)
            for _ in range(12):
                if await selected_image_tool(page):
                    return "CREATE_IMAGE_TOOL_SELECTED"
                await page.wait_for_timeout(250)
            # Selection was clicked but not independently verified: fail closed.
            return "CREATE_IMAGE_PILL_NOT_VISIBLE"
        return ("CREATE_IMAGE_OPTION_MISSING" if opened else
                "IMAGE_TOOL_MENU_MISSING")
    except Exception as exc:
        return "CREATE_IMAGE_TOOL_NOT_VERIFIED:"+type(exc).__name__


async def _attachment_input(page):
    """Return the composer file input across current ChatGPT label variants."""
    selectors = (
        'input[type="file"][aria-label="Attach files"]',
        'input[type="file"][aria-label="Attach photos or videos"]',
        'input[type="file"][aria-label="Attach photos"]',
        'input[type="file"][accept*="image"]',
    )
    for selector in selectors:
        loc = page.locator(selector)
        count = await loc.count()
        if count == 1:
            return loc
        if count > 1:
            # Hidden file inputs are expected. Prefer the last hydrated composer
            # input instead of failing merely because responsive duplicates exist.
            return loc.last
    return None


async def _attachment_snapshot(page):
    """Count completed attachment witnesses inside the active composer only."""
    return await page.evaluate(
        r"""() => {
          const visible=e=>!!(e && e.getClientRects && e.getClientRects().length);
          const box=[...document.querySelectorAll('[role="textbox"][contenteditable="true"]')]
            .find(visible);
          if(!box)return {ready:0,loading:0};
          const scope=box.closest('form') || box.parentElement?.parentElement || document;
          const images=[...scope.querySelectorAll(
            'img[src^="blob:"], img[alt="User attachment"], '+
            '[data-testid*="attachment"] img, [data-testid*="upload-preview"] img, '+
            '[data-testid*="file-upload"] img'
          )].filter(e=>visible(e) && e.complete && e.naturalWidth>0 && e.naturalHeight>0);
          const removers=[...scope.querySelectorAll('button[aria-label]')].filter(e=>{
            if(!visible(e))return false;
            const a=(e.getAttribute('aria-label')||'').toLowerCase();
            return a.includes('remove attachment') || a.includes('remove file') ||
                   a.includes('remove image') ||
                   (a.startsWith('remove ') && a.includes('.png')) ||
                   (a.includes('첨부') && a.includes('제거'));
          });
          const loading=[...scope.querySelectorAll(
            '[aria-label*="Uploading"], [aria-label*="uploading"], '+
            '[data-testid*="uploading"], [data-testid*="upload-progress"], [role="progressbar"]'
          )].filter(visible);
          return {ready:Math.max(images.length,removers.length),loading:loading.length};
        }"""
    )


async def clear_attachment_previews(page):
    """Remove stale composer file previews before selecting the ImageGen tool."""
    try:
        await page.locator('[role="textbox"][contenteditable="true"]').first.wait_for(
            state="visible", timeout=12000)
        for _ in range(8):
            removed = await page.evaluate(
                r"""() => {
                  const visible=e=>!!(e && e.getClientRects && e.getClientRects().length);
                  const box=[...document.querySelectorAll('[role="textbox"][contenteditable="true"]')]
                    .find(visible);
                  if(!box)return -1;
                  const scope=box.closest('form') || box.parentElement?.parentElement || document;
                  const buttons=[...scope.querySelectorAll('button[aria-label]')].filter(e=>{
                    if(!visible(e))return false;
                    const a=(e.getAttribute('aria-label')||'').toLowerCase();
                    return a.includes('remove attachment') || a.includes('remove file') ||
                           a.includes('remove image') ||
                           (a.startsWith('remove ') && a.includes('.png')) ||
                           (a.includes('첨부') && a.includes('제거'));
                  });
                  buttons.forEach(e=>e.click());
                  return buttons.length;
                }"""
            )
            if removed < 0:
                return "COMPOSER_ATTACHMENT_CLEAR_UNVERIFIED"
            if removed == 0:
                snapshot = await _attachment_snapshot(page)
                if snapshot.get("ready", 0) == 0 and snapshot.get("loading", 0) == 0:
                    return "COMPOSER_ATTACHMENTS_CLEAR"
                return "COMPOSER_ATTACHMENT_CLEAR_UNVERIFIED"
            await page.wait_for_timeout(300)
        snapshot = await _attachment_snapshot(page)
        if snapshot.get("ready", 0) == 0 and snapshot.get("loading", 0) == 0:
            return "COMPOSER_ATTACHMENTS_CLEAR"
        return "COMPOSER_ATTACHMENT_CLEAR_UNVERIFIED"
    except Exception:
        return "COMPOSER_ATTACHMENT_CLEAR_UNVERIFIED"


async def _wait_attachment_ready(page, filenames, baseline, timeout):
    """Accept either legacy filename proof or a new modern composer preview."""
    await page.wait_for_function(
        r"""({files,baseline})=>{
          const visible=e=>!!(e && e.getClientRects && e.getClientRects().length);
          const box=[...document.querySelectorAll('[role="textbox"][contenteditable="true"]')]
            .find(visible);
          if(!box)return false;
          const scope=box.closest('form') || box.parentElement?.parentElement || document;
          const images=[...scope.querySelectorAll('img[alt]')].filter(e=>
            visible(e)&&e.complete&&e.naturalWidth>0&&e.naturalHeight>0);
          const buttons=[...scope.querySelectorAll('button[aria-label]')].filter(visible);
          const uploading=[...scope.querySelectorAll(
            '[aria-label*="Uploading"], [aria-label*="uploading"], '+
            '[data-testid*="uploading"], [data-testid*="upload-progress"], [role="progressbar"]'
          )].filter(visible);
          if(uploading.length)return false;

          const named=files.every(name=>{
            const stem=name.replace(/\.png$/i,'');
            const same=x=>x===name ||
              (x.startsWith(stem+'(')&&x.endsWith(').png') &&
               /^[0-9]+$/.test(x.slice(stem.length+1,-5)));
            return images.some(e=>same(e.alt||'')) &&
              buttons.some(e=>{
                const a=e.getAttribute('aria-label')||'';
                return same(a.replace(/^Remove /,''));
              });
          });
          if(named)return true;

          // Current ChatGPT composer no longer guarantees filename-bearing
          // alt/remove labels. Count only attachment-like preview witnesses in
          // the active composer and require a delta caused by this upload.
          const modernImages=[...scope.querySelectorAll(
            'img[src^="blob:"], img[alt="User attachment"], '+
            '[data-testid*="attachment"] img, [data-testid*="upload-preview"] img, '+
            '[data-testid*="file-upload"] img'
          )].filter(e=>visible(e)&&e.complete&&e.naturalWidth>0&&e.naturalHeight>0);
          const removers=buttons.filter(e=>{
            const a=(e.getAttribute('aria-label')||'').toLowerCase();
            return a.includes('remove attachment') || a.includes('remove file') ||
                   a.includes('remove image') ||
                   (a.startsWith('remove ') && a.includes('.png')) ||
                   (a.includes('첨부') && a.includes('제거'));
          });
          const ready=Math.max(modernImages.length,removers.length);
          return ready >= baseline + files.length;
        }""",
        arg={"files":filenames,"baseline":int(baseline)},
        timeout=timeout,
    )


async def attach_batch_pngs(page, binding):
    """Upload 2-5 individual files and prove completed composer attachments."""
    paths = binding["paths"]
    expected = [Path(s).name for s in paths]
    if not (2 <= len(paths) <= 5) or len(set(expected)) != len(paths):
        return "BATCH_MUST_HAVE_TWO_TO_FIVE_DISTINCT_PNG"
    try:
        if not page.url.startswith("https://chatgpt.com/"):
            return "TARGET_ORIGIN_NOT_CHATGPT"
        await page.locator('[role="textbox"][contenteditable="true"]').first.wait_for(
            state="visible", timeout=12000)
        inp = await _attachment_input(page)
        if inp is None:
            return "ATTACH_FILES_INPUT_NOT_FOUND"
        before = await _attachment_snapshot(page)
        await inp.set_input_files(paths, timeout=40000)
        await _wait_attachment_ready(page, expected, before.get("ready", 0), 120000)
        return "ATTACHMENT_UPLOAD_COMPLETED"
    except Exception:
        return "ATTACHMENT_UPLOAD_NOT_VERIFIED"


async def attach_png(page,binding):
    """Upload one PNG and prove a completed attachment without filename-only DOM assumptions."""
    if len(binding.get("paths", [])) > 1:
        return await attach_batch_pngs(page, binding)
    filename=Path(binding["path"]).name
    try:
        await page.locator('[role="textbox"][contenteditable="true"]').first.wait_for(
            state="visible",timeout=12000)
        if not page.url.startswith("https://chatgpt.com/"):
            return "TARGET_ORIGIN_NOT_CHATGPT"

        # Best-effort removal of a stale legacy filename-bearing preview.
        previous=page.locator('button[aria-label^="Remove '+filename[:-4]+'"]')
        for _ in range(8):
            if not await previous.count():
                break
            await previous.first.dispatch_event("click")
            await page.wait_for_timeout(350)

        inp=await _attachment_input(page)
        if inp is None:
            return "ATTACH_FILES_INPUT_NOT_FOUND"
        before=await _attachment_snapshot(page)
        await inp.set_input_files(binding["path"],timeout=25000)
        await _wait_attachment_ready(page,[filename],before.get("ready",0),90000)
        return "ATTACHMENT_UPLOAD_COMPLETED"
    except Exception:
        return "ATTACHMENT_UPLOAD_NOT_VERIFIED"


async def verify_submission_receipt(page, task_id, filename, *, timeout_ms=45000):
    """Verify exact persisted user marker and loaded attachment count, never composer."""
    filenames = filename if isinstance(filename, list) else [filename]
    count = len(filenames)
    try:
        await page.wait_for_function(
            r"""({task,count}) => {
                if(location.hostname!=='chatgpt.com' ||
                   !location.pathname.includes('/c/') ||
                   location.href.includes('local-chatgpt'))return false;
                const marker='UPLOAD_TASK_ID='+task;
                const candidates=document.querySelectorAll(
                  '[data-markdown-text-tone="user-message"],[data-message-author-role="user"],[data-testid="conversation-turn-user"]');
                for(const target of candidates){
                  if(!(target.textContent||'').split(/\\s+/).includes(marker))continue;
                  const roots=[target,
                    target.closest('[data-message-author-role="user"]'),
                    target.closest('[data-testid="conversation-turn-user"]'),
                    target.closest('[data-chatgpt-search-unit-key]'),
                    target.closest('[data-content-search-unit-key]')];
                  for(const user of roots){
                    if(!user || user.closest('[contenteditable="true"]') ||
                       user.querySelector('[data-message-author-role="assistant"],[data-markdown-text-tone="assistant"]'))continue;
                    const thumbs=[...user.querySelectorAll('img[alt="User attachment"]')]
                      .filter(img=>img.complete && img.naturalWidth>0 && img.naturalHeight>0 &&
                        !!(img.currentSrc||img.src));
                    if(thumbs.length===count)return true;
                  }
                }
                return false;
            }""", arg={"task":task_id,"count":count}, timeout=timeout_ms, polling=1000)
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