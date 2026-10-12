# Free ChatGPT browser attachment assistant — OutRun 2006 B/C1
**No paid API, no password, no ChatGPT automation login.** Designed for locally logged-in Chrome on Windows, not GitHub Actions.

## Install (unpacked extension)
1. Download this folder (or the published extension ZIP), extract it locally.
2. Open Chrome `chrome://extensions`, enable Developer mode, choose **Load unpacked**, and select the folder containing `manifest.json`.
3. Open your signed-in `https://chatgpt.com/` project conversation.
4. Click the extension icon, choose a SHA-verified original English glyph PNG, then **현재 ChatGPT에 첨부 시도**.
5. Verify the actual ChatGPT attachment thumbnail appears in the conversation composer. **No thumbnail = NOT BOUND**; select **PNG 복사** in the extension, click the input area, press Ctrl+V. ChatGPT officially supports pasting image files.
6. Copy the corresponding prompt with the third button, submit the image-edit request manually only after verifying the preview.
7. Save generated Korean PNG, verify exact Hangul/alpha and independently run CLEAN/plate/C2/C3/user-game gates. No status changes from this helper.

## Scope and limitations
- The extension fetches ONLY 8 hardcoded original English transparent-letter PNGs from `thp32tt/OutRun2006Tweaks`, computes SHA-256 via browser Web Crypto, refuses any changed source, and injects a local `File` into the ChatGPT page's existing file input.
- It does NOT call the paid OpenAI API, send a prompt, automate generation or read login cookies. Only `raw.githubusercontent.com` download access and temporary tab scripting access; no background web activity.
- Browser file-input DOM can change without notice. Synthetic `change` event **is not proof of upload**. If no ChatGPT preview, explicitly FAIL/HOLD and use clipboard fallback or native + file picker.
- This is a **locally user-initiated one-click helper**, not unattended agent production or verified direct `image_gen.text2im` media binding.
- q098 has a canonical image and a PSD style variant (not pixel equivalent), q092 PSD composite is not C2-approved CLEAN, q230 translations are not yet approved. Do not create q230 Korean text until target phrase verified. Existing producer owners preserved.
- File upload / image generation limits of the user's ChatGPT plan still apply. There is no way to bypass plan limits.
- Published ZIP source files are auditable; only install an unpacked extension whose source you trust. No external extensions are downloaded or installed by this tool.

## Verifying attachment
The extension message `DOM_FILE_CHANGE_DISPATCHED_NOT_UPLOAD_PROOF` **never** establishes media bound. Require an actual thumbnail in the message composer and that the uploaded image appears in the user message after sending. If it fails, user-controlled `Ctrl+V` fallback is the supported method. No source attached => `SOURCE_REFERENCE_NOT_BOUND`, no official DDS.