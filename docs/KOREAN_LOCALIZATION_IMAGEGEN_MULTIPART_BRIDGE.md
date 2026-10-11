# B/C1 canonical English PNG → actual image edit multipart bridge — 2026-10-12

## Limitation verified in the ChatGPT tool

A GitHub `fetch_file` or other tool result rendered as an image is visible to this ChatGPT assistant but is **not automatically passed to the native `image_gen.text2im` generation model**. A controlled invocation explicitly returned **"Image generation has not started: the image generation model cannot see the tool results."** Therefore previous claims based only on tool-rendered screenshots, raw GitHub URLs or `edit_op=null` are invalid. Do **not** claim native ChatGPT image attachment or generate without a real reference.

## Implemented alternate real-model attachment

`tools/localization/imagegen_source_edit_bridge.py` uses the **OpenAI Images Edit API** (`client.images.with_raw_response.edit`) to send the verified source PNG as the actual binary `image=<opened file>` multipart field. This is an **API-based GPT image edit**, **not** the native ChatGPT `image_gen.text2im` tool. It requires a separately authorized and billed OpenAI API key. A successful server response must expose `x-request-id` and a genuine base64 PNG; only then is `media_attached=true` recorded. Source SHA, output SHA and API request ID are recorded in immutable raw output/receipt files. The bridge never creates approved DDS or closes actual-game defects.

Exact prepared source requests already in the repo:

- C1 q102 `imagegen_requests/q102_C1_OPENAI_EDIT_SOURCE_REQUEST.json` → canonical English-only native DDS-derived `Time Attack Mode`, SHA256 `affc027f5d9dd73b5a095cbd59f28945ba8aa999bb2f8d22e6f8a148483fcc7d`. Exact Korean: 타임 어택 모드.
- B q092 `imagegen_requests/q092_B_OPENAI_EDIT_SOURCE_REQUEST.json` → English-only PSD-composite `OutRun Mode`, SHA256 `99a9c4b7d123ccec77ed03491b4a0ca1d23e27bd9b4976563b0cab3a0b8987ba`. Exact Korean: 아웃런 모드. PSD style reference **is not yet pixel-exact C2-certified canonical DDS/CLEAN**, so resulting Korean artwork must not be promoted automatically.

The bridge enforces role/index parity, repo-confined paths, source PNG true alpha, exact PNG SHA, fixed model, exact target text, output lane, and no same-key duplicate billable invocation. No `OPENAI_API_KEY` ⇒ `SOURCE_ATTACHMENT_API_CREDENTIAL_MISSING`, generation 0, DDS 0. A synthetically mocked SDK response is **unit testing only**, not actual network binding. The actual `x-request-id` and PNG only arise from the remote editing endpoint.

## Run and verify in GitHub's virtual machine first

GitHub Actions: **Localization Real Image Edit Binding**,
`.github/workflows/localization-real-image-edit-binding.yml`.

Pushes run read-only preflight and synthetic transport/PNG→DDS regressions with no API key and no generation charges. For a real pilot, set an encrypted **repository Actions secret named `OPENAI_API_KEY`**, then use **Run workflow** with `pilot=C1_q102` or `pilot=B_q092`. Never paste an API secret into ChatGPT, GitHub source files, a log, a prompt or a script.

Live job checks the secret before a call, submits the on-disk English PNG as the real image file, requires the API request ID and nonopaque transparent RGBA PNG response, uploads unapproved RAW PNG and receipt as a workflow artifact, and (if permitted) pushes the new RAW-only evidence files to the existing branch. No unapproved image is inserted into hd_candidates or export.

After success:
1. Read the exact `RAW_UNREVIEWED.png`, `TOOL_INPUT_RECEIPT.json` and `OUTPUT_MANIFEST.json`; compare SHA for source/output and the GitHub Actions successful provider request.
2. Producer verifies visually exact Hangul and one isolated transparent letter layer. Any wrong text, vehicles/menu/UI or dirty alpha remains REWORK.
3. Independently obtain C2-approved exact canonical SOURCE/CLEAN/removal mask and every atlas region. Reuse prior PLATE_PASS only when exact SHA matches.
4. Convert with `tools/localization/imagegen_b_pipeline.py` using `generator.provider=openai-images-edit` and its **SHA-bound receipt + generated PNG**, then perform producer DDS QA (native/75/50, RAW/FLIPY, all protected pixels, unchanged BC3 blocks).
5. C2 independently inspects full exact saved DDS; C3 and actual user game retest remain separate. `RUNTIME_VALIDATION=UNTESTED` until run.

**Hard stop:** If the API key is not available, the OpenAI account lacks Images Edit access, or the server rejects the image, **do not assert generator input binding success**. The bridge being committed is not evidence of a successful live edit.

This method is an explicit alternative to the ChatGPT-only ImageGen lane. It must be approved as the B/C1 generation provider before treating outputs as normal B/C1 production; otherwise keep it as experimental reference-generation evidence and preserve the previous policy.
