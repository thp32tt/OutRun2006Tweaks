## 2026-11-09 19:52 KST — QA rework container log analysis and bounded collection retry

**Evidence:** user-supplied Portainer export `_outrun-chat-qa-rework_logs.txt` (16:37–19:40 KST; timestamps in file are UTC). 17 `CYCLE_OK` logs, repeated `WAIT_IMAGEGEN_ASSISTANT_GENERATED_IMAGE_NOT_RENDERED`, no exported candidate and no C1-ready status in the supplied segment. The initial `CHROMIUM_LOCAL_RENDER_PROBE: FAIL dom=False pixel=(255,255,255)` and an early `HOLD_CHATGPT_LOGIN_REQUIRED` were followed by a verified `AB_SENT` event, so the browser could subsequently send. This alone does not establish that ImageGen actually produced a response. Hundreds of repeated Portainer timestamps in single exported lines are exporter formatting, not the Python worker printing hundreds of separate cycles (the worker prints one JSON per cycle).

**Fixes in this branch:**
- Browser bootstrap now says `CHATGPT_BROWSER_TAB_VISIBLE_AUTH_UNVERIFIED`. Merely opening a page cannot prove logout.
- On every persisted `AB_SENT` task, try the SHA-bound assistant-image collector first. Wait *once*, for up to 1.2s, for delayed user or assistant hydration. Never resend an `AB_SENT` task.
- Do not launch the old 24-second twice-wait-and-reload path when the exact source-bound user turn has already rendered but there is no Assistant image. Run the legacy exporter only if its exact candidate selector verifies one result.
- Missing ImageGen output now emits **only bounded DOM counts**, for example `ASSISTANT_GENERATED_IMAGE_NOT_RENDERED_A0_G0_U1_L0`. `A`=assistant text turns immediately after the user; `G`=generated-image selector nodes anywhere in this page; `U`=rendered user turns; `L`=visible password login input (0/1). These are diagnostic signals, not confirmation of image generation/authentication. No user text, private chat URL, cookies, image bytes or tokens are logged.
- C1 QA, source-SHA linkage, PNG alpha/frame checks, and native DDS/game release gates remain unchanged.

**Verification:** **44 Python tests PASS** on N100; **17 JS mocked DOM tests PASS**. Browser runtime recovery **not yet verified**, so do not mark any PNG complete based only on these tests.

**Operator action:** Portainer, existing image-rework stack only (not the separate Actions light controller): Pull latest branch `localization-controller-recovery-20260928`, **Rebuild and Redeploy**, retaining login profile/volumes. Then check the first `processed` reason / GitHub `hd_imagegen_fallback/state` for `_A#_G#_U#_L#` and check `candidates` for a real new PNG. If `A0_G0` persists, inspect one matching saved ChatGPT conversation in noVNC for a generated image or generation error; do not blindly resend.

---

## 2026-11-09 15:15 KST — distinguish delivered image prompt from failed ImageGen response

**Known sent-work anchor:** `HDRW-B-322d801e17d4261db4fa`, English `Manual`, Korean `수동`, original DDS SHA-256 `7b41a04e2b0736717dd0da4d82f9e18f3aac7c469a5738848c5cfa6bf28e15b5`. GitHub `AB_SENT` is evidence of an attached **user message**, never evidence that the assistant image was generated or collected. The user's reference chat showed a generation-error response for this prompt in this project, but the running Docker's actual response/log still requires confirmation.

**Fix:** `chat_image_result_rescue.py` now classifies explicit ImageGen failure text (e.g. `Something went wrong while generating your image`) as `IMAGEGEN_FAILED_UI` in a reply *bounded after the verified task's user message and before the next user message*. It keeps failed output in `AB_SENT` with `last_result_poll_reason=IMAGEGEN_FAILED_UI`, never writes an English uploaded reference as a Korean image, never falsely advances to `C1_READY`, and **does not automatically resend** the existing `UPLOAD_TASK_ID`. A missing media result without an explicit failure is `ASSISTANT_GENERATED_IMAGE_NOT_RENDERED`, not automatically treated as generation failure. This permits precise operator recovery without violating the duplicate-send policy.

**Offline regressions:** 39 Python tests PASS and 17 mock browser-DOM tests PASS, including roleless ImageGen media, explicit failure, quoted failure in a user prompt, failure after the next user turn, original-reference exclusion and SHA-bound proof. These are not live image-success evidence.

**Operator log evidence request:** In Portainer → Containers → `outrun-chat-qa-rework` → Logs, copy **the latest 100–200 lines** including JSON keys `checked_utc`, `processed`, `status` and `error_type`. Or, on a privileged host shell, run:

```bash
docker logs --since 45m --tail 200 outrun-chat-qa-rework 2>&1
```

Remove tokens, cookies, personal chat text and authentication URLs before sharing. The connected non-root host session cannot read the Docker socket or worker's `/proc/.../fd/1`, so the user-provided logs are required to conclusively distinguish a generation failure from absent DOM/media. Avoid repeated manual resend under the same task ID. If the actual ChatGPT conversation shows a failed image, retry in the **existing conversation** only once the UI action and exact task binding are verified; do not claim an output was produced.

**Deploy:** Once logs are captured, pull latest `localization-controller-recovery-20260928`, **rebuild and redeploy** existing Portainer stack, preserving browser/data volumes. The running controller at 15:16 KST predates this source change; a simple restart would not apply it. No new host resources or paid API added.

---

## 2026-11-09 15:04 KST — ImageGen media-only assistant turn handling

**Live evidence:** browser and the existing Docker controller remain running at 15:05 KST; `Ghost Forest` and `Manual` persisted A/B tasks are still `AB_SENT` with `ASSISTANT_TURN_NOT_READY`. This status is not proof that the AI image was never generated. The running worker's Docker logs and process stdout could not be read by the authorized non-root host connection (Docker socket and `/proc/<pid>/fd/1` denied). No new PNG/C1 success claimed.

**Code fix:** `chat_image_result_rescue.py` now searches specifically generated-image UI elements in DOM order **after the exact SHA-bound user task and before the next user turn**, even when the generated image is wrapped in a media/tool-only turn without an assistant text-role element. Never capture source-upload previews, a later user's response, or multiple ambiguous generated images. Existing source-triple/provenance and independent C1/DDS gates are unchanged. Missing output is labeled `ASSISTANT_GENERATED_IMAGE_NOT_RENDERED` instead of implying that an assistant text-role was mandatory.

**Offline verification:** 37 Python regression tests PASS and 14 ImageGen DOM JS mock fixtures PASS, including media-only image output, next-user rejection, ambiguous image rejection, and upload-vs-output separation. No actual authenticated browser image retrieval has yet been demonstrated.

**For operator diagnosis (no secrets):** In Portainer, open container `outrun-chat-qa-rework` → Logs → most recent 200 lines, and share lines with `status`, `processed`, `checked_utc`, or `error_type`. Alternatively run `docker logs --since 30m --tail 200 outrun-chat-qa-rework` on a privileged host terminal. Redact secrets, cookies, tokens and private chat URLs. The worker logs one cycle JSON record every `OUTRUN_REWORK_POLL_SECONDS` (default 600). This is required to separate page DOM failures from browser reload/navigation exceptions and unexpected worker errors. After logs are examined, **Rebuild + Redeploy** this latest controller branch; ordinary container restart does not incorporate the fix.

---

## 2026-11-09 12:10 KST — current ChatGPT Project DOM recovery repair

**Issue confirmed from source:** the persisted send receipt validator uses current ChatGPT Project selectors `[data-markdown-text-tone="user-message"]` and `[data-chatgpt-search-unit-key]`, but the fallback ImageGen result collector previously only searched `[data-message-author-role]`. Its `USER_TURN_MISSING` result could therefore be misleading even if the source user message was saved. The legacy detector also depends on visible `UPLOAD_TASK_ID`, which can be absent in an older/re-rendered turn. No user-facing screenshot, log, or image success is assumed.

**Correction:**
- `chat_image_result_rescue.py` now supports both current and older user/assistant message selectors and searches only the assistant turn(s) immediately after one verified user turn.
- Preferred provenance is the exact `UPLOAD_TASK_ID=<TASK_ID>` in a user turn. If the footer is unavailable, the *same unique user turn* must contain the exact English text, Korean translation **and full source DDS SHA-256** from the GitHub task. Missing or ambiguous metadata fails closed; no generic images or user-uploaded English crops can become Korean candidates.
- Result extraction prefers the generated-image carousel selector if present (avoids double-counting a single output's thumbnail and preview). It requires exactly one valid generated image, then PNG SHA verification, unapproved state and independent C1 QA. DDS/game approvals remain unchanged.
- `github_chat_rework_controller.py` passes the SHA-bound task details to this probe and attempts this fast, strictly checked rescue *before* the legacy 12-second chat-turn wait/reload, reducing unnecessary browser reloading and N100 work.
- Simulated automated checks: **37 Python regression tests PASS**; **8 browser-JavaScript DOM fixtures PASS** on N100 (task marker, source triple, source reference separation, duplicated/ambiguous turns and image candidates). Tests do not prove success on the real authenticated ChatGPT UI.

**Deployment:** manually Pull latest `localization-controller-recovery-20260928` from GitHub, **Rebuild + Redeploy** the same Portainer stack. No new variables or extra containers; keep existing browser profile and data volumes. Confirm the new code by a state moving from `AB_SENT` to `C1_READY` or a new precise `last_result_poll_reason` such as `SOURCE_BOUND_USER_TURN_MISSING`, `CHAT_USER_TURNS_NOT_RENDERED`, or `ASSISTANT_GENERATED_IMAGE_SELECTOR_MISSING`. A previous `USER_TURN_MISSING` receipt must not cause another A/B send.

**Release:** manual C1/C3 and native DDS/in-game quality gates remain required. Never claim completion from an `AB_SENT`, PNG export or test-only success.

---

## 2026-11-09 read-only chat result collector fix (manual rebuild/redeploy)

**Verified live symptoms:** after the browser and worker were restarted around 10:55 KST, Ghost Forest continued recording `WAIT_CHATGPT_COMPOSER_OR_LOGIN` at 10:56 KST. This is a collected-page check failure, **not proof that ChatGPT logout occurred**. N100 load and memory were normal; current queue still had 0 saved PNG candidates.

**Fix:** `ChatBridge.page(..., read_only=True)` retrieves a **specific, previously saved and validated ChatGPT conversation URL** without requiring a composer. The A/B `collect_producer` and C1 `inspect_c1` paths use read-only mode. Invalid or redirected conversation URLs fail closed; `submit_producer` and `submit_c1` still require the visible composer and existing attachment/send validation. No output SHA, PNG evidence, independent C1 QA, or native DDS acceptance gate was relaxed.

**Independent checks:** 32 offline regression tests PASS on 2026-11-09, including composer-free authenticated-chat URL read, missing URL fail closed, redirect rejection, send-path composer enforcement, and previous assistant-only image result cases. Real UI collection remains unverified until the next container deployment.

**Operator action:** Portainer Git Stack (controller branch `localization-controller-recovery-20260928`): Pull latest, Rebuild image, Redeploy the **existing** stack. Preserve browser login and data volumes. A simple browser refresh/container restart without rebuilding the image does not include this code change. Confirm on GitHub `hd_imagegen_fallback/state`: `last_result_poll_reason` changes from `WAIT_CHATGPT_COMPOSER_OR_LOGIN` to a more precise image result reason, or a task advances to `C1_READY`. Do not resend an already `AB_SENT` task.

---

## 2026-11-09 ImageGen result collector repair (manual redeploy required)

**Why:** 16 observed A/B tasks reached `AB_SENT` but no candidate PNG reached GitHub/C1. Code inspection identified that only the alphabetically first three saved task files were checked each cycle, and the existing lazy ChatGPT conversation recovery helper was never invoked in `collect_producer`. The legacy result detector also depended on one older ChatGPT generated-preview DOM shape. The live failed selector cannot be confirmed without authenticated container browser logs.

**Changed:** 
- `github_chat_rework_controller.py` round-robins all persisted A/B tasks, including older batches when the GitHub staging queue rotates. It invokes `text_roi_queue._recover_task_turn()` when `USER_TURN_MISSING` occurs and keeps prior `AB_SENT` receipt evidence without sending duplicate prompts.
- New `chat_image_result_rescue.py` uses only the assistant reply immediately after an exact `UPLOAD_TASK_ID` user turn to locate a single generated image. It rejects uploaded user English reference images, unrelated generic images, multiple ambiguous images, untrusted download URLs and screenshots; image bytes are SHA-verified and stored as unapproved local PNG before publication and C1 QA.
- A/B `AB_SENT` states now expose `last_result_poll_reason` and `last_result_poll_utc` on the GitHub queue branch, throttled to once per 30 minutes per identical reason. Missing evidence stays `AB_SENT`, not `PASS`; opaque/cropped generated output becomes `HOLD` for rework. C1/DDS/game approval is unchanged.
- `Dockerfile.chat-rework` includes the module and gates build on all **27 offline tests PASS** on 2026-11-09, including modern-image simulation, 16-ticket fairness, collector integration, SHA receipt and fail-closed cases. Live browser image capture is **not yet verified**.

**Operator deployment:** Pull latest controller branch `localization-controller-recovery-20260928` and **Rebuild + Redeploy existing** Portainer stack only. Do not delete data/browser volumes or change secrets. Compose is unchanged (default fallback workqueue, 2GiB memory, noVNC 6084). After deployment inspect `localization/automation_runs/hd_imagegen_fallback/state/<TASK_ID>.json` on `korean-localization-qa-queue-20261104` and check that `last_result_poll_reason` is populated or state moves to `C1_READY`. If stalled, inspect container logs for `processed` outcomes, then use `last_result_poll_reason` to distinguish missing original user turn, missing assistant output, inaccessible image URL, and invalid alpha candidate. No auto-redeploy or image-generation success was claimed in the code-only repair.

---

## 2026-11-08 Docker ImageGen fallback deployment — operator-managed Portainer

Implementation: `github_chat_rework_controller.py`, `docker-compose.yml`, `test_github_chat_rework_controller.py`, `Dockerfile.chat-rework` on this branch. GitHub work queue: `korean-localization-qa-queue-20261104:localization/automation_runs/hd_imagegen_fallback/latest.json` (8 SHA-proved original HD PNG tasks, of which 7 exactly match preexisting `hd_rework_queue/state` `AB_SENT` receipts dated 2026-11-05; only PERFECT! has no prior send). Fallback work order is **not** proof of ImageGen output.

**Changes now staged for the next MANUAL deploy:**

- `OUTRUN_REWORK_QUEUE_NAME=${OUTRUN_REWORK_QUEUE_NAME:-hd_imagegen_fallback}`, `OUTRUN_REWORK_REUSE_ONLY=${OUTRUN_REWORK_REUSE_ONLY:-0}`. Only two queue names are accepted, and the original reuse-only state namespace remains immutable in fallback mode. A/B send requires an exact SHA-bound approved fallback queue, source PNG, active account login, verified ImageGen tool selection and actual persisted attachment receipt.
- For seven prior `AB_SENT` tasks, import the exact original task and its persisted ChatGPT Project `/g/g-p-.../c/...` conversation URL into new fallback state, **never re-submit**. Resume image output download and C1 QA in existing conversations. A conflicting or unverifiable original state becomes HOLD without resending.
- A/B can newly attach the one unsubmitted `PERFECT!` task only when verified. Output images are alpha-checked and losslessly cropped of unused transparent margins, retaining all visible pixels; GitHub candidate SHA is for the normalized bytes and retains the raw generated SHA separately. C1 attaches original + Korean candidate and records independent provisional results; no automatic final DDS/game approval.
- Browser worker now defaults to CPU 1.0 / memory 2048m / shm 512m (Portainer overrides `OUTRUN_REWORK_MEM_LIMIT` and `OUTRUN_REWORK_SHM_SIZE`). Named data, browser profile and logs volumes are preserved. No second Chromium instance. Heavy HD/DDS processing remains on GitHub.
- Offline source/PNG/recovery regression tests are included in the Docker build; any failure aborts image build. Test source can be run with `python -m unittest -v test_github_chat_rework_controller` from the controller directory when Pillow and Playwright are installed. Initial offline check on 2026-11-08 ran 18 tests PASS (synthetic browser tests; **not live ImageGen evidence**).

**Your deployment steps:**

1. Open the **existing** Portainer Git Stack (`outrun-kor`), repository `thp32tt/OutRun2006Tweaks`, branch `localization-controller-recovery-20260928`, Compose `tools/chat-controller/localization-recovery-v1/docker-compose.yml`. Do not create a second stack.
2. Preserve existing named volumes. Ensure secrets `OUTRUN_REWORK_VNC_PASSWORD` and `OUTRUN_GITHUB_CONTENTS_TOKEN` are set (token needs repository Contents Read/Write). Set `CHATGPT_PROJECT_URL` to the actual ChatGPT project URL when known; user must authenticate manually if session expired. Do not publish tokens or VNC passwords in GitHub.
3. **Pull latest → Rebuild image → Redeploy**, not a no-build redeploy. Observe `outrun-chat-qa-rework` logs and `http://N100-IP:6084/vnc.html`. Look for `NOVNC_LISTENER_STARTED`, `CHROMIUM_LOGIN_WINDOW_READY`, then `CYCLE_OK` and `RECOVERED_AB_SENT_NO_RESEND` / `C1_READY`. No live success is claimed until these receipts are observed. Browser login/status, GitHub credential availability, generated PNG and C1 result are separate gates.
4. Pause sending **without deleting any state** by Portainer env `OUTRUN_REWORK_REUSE_ONLY=1` and redeploy; with `1`, already persisted A/B/C1 outputs can continue review but no new ImageGen requests are sent. To resume, use `0` with the same queue. If errors mention `HOLD_GITHUB_CONTENTS_TOKEN_MISSING`, `HOLD_CHATGPT_LOGIN_REQUIRED`, or `HOLD_QUEUE_AUTHORITY_OR_SOURCE_PROOF`, correct credentials or source proof before sending.
5. `release_approved=false` / `runtime_validation=UNTESTED` until independent HD DDS/CLEAN and C3/actual in-game verification. Existing GPU/VR stacks unaffected.

---

## 2026-11-01 direct visual ROI non-OCR GitOps profile

Portainer branch: `localization-controller-recovery-20260928`. Existing Compose: `tools/chat-controller/localization-recovery-v1/docker-compose.yml` (same stack; rebuild + redeploy manually). A/B remain enabled for SHA-verified full-HD direct-reference ImageGen; C1 remains independent QA. OCR ChatGPT dispatch, pixel OCR review and OCR response polling are disabled, and the in-container OCR watchdog is not started. Old OCR `state.json` is retained but no longer locks QA. The ROI bridge scans only `manual_vision_outputs` and exact RGBA `cross_variant_verified` in `OUTRUN_ROI_SOURCE_MODE=direct_visual`; legacy `hd108_outputs` and `gpt_vision_chat_ocr_outputs` are **not** used as *new* inputs. Previously admitted manifest entries and A/B progress remain unchanged. New human-verified visual ROI cases must have exact original SHA, approved English/Korean translation and visual crop evidence under the shared bind-mounted `text_roi_batches/manual_visual_evidence/<crop-sha256>.png`; save `manual_visual_evidence_relative_path=<crop-sha256>.png` in the manual manifest so both N100 and Docker independently read the same crop. 25 preexisting manual evidence crops were safely mirrored to this folder, with SHA/pixel equality and per-manifest backups; unproven older manifests are held. A blind alpha split does not count as semantic proof. 1- and 2-line source layouts must remain intact. No automatic DDS edits, C3/game PASS or VR changes.

Startup policy fails closed unless `OUTRUN_GPT_CHAT_OCR_ENABLED=false`, `OUTRUN_PIXEL_OCR_REVIEW_ENABLED=false`, `OUTRUN_ROI_SOURCE_MODE=direct_visual`, A/B queue, bridge and controlled sending are enabled. Normal Portainer **Pull latest + Rebuild + Redeploy** applies this profile; never delete browser/session named volumes or start a separate container. After deployment verify `/status`: C1 QA no longer posts OCR tasks, A/B can consume only newly verified ROI records, and existing pending tasks remain; do not infer ImageGen completion from queue registration.

---

## 2026-10-18 C 슬롯 OCR 중복 작업 제거 — GitOps v2

측정: 2026-10-18 UTC 기준 기존 N100 C OCR 로그에서 원본 PNG 716회 중복 검사, 매치 1,670, 중복 1,153, 보류 517, 신규 크롭 0. 하루 전 원본 108개에서 최초 166개 TEST_ONLY 결과를 얻은 뒤에 전수 재검사를 무한 반복하는 구조를 개선했습니다.

- 소스 `c_english_crop/ocr_hd108.py`의 `POLICY_VERSION=hd108-pass-v2-20261018-reviewed-edge-crops`. 원본 HD PNG 각 파일은 이 정책 버전과 원본 SHA별 **한 번만** 검사한 뒤 `hd108_ocr/processed_v2/*.json`에 처리 기록을 남깁니다. 같은 원본/같은 정책을 또 OCR하지 않습니다. 원본·검증 정책이 바뀌면 명시적으로 새 버전으로 다시 스캔합니다.
- OCR 1회에서 원본 4개씩 순차 검사. 108개 완료 시 `HD108_PASS_COMPLETE_REVIEW_PENDING`를 기록하고, 이후 OCR 반복을 멈춥니다. 기존 50개 DDS 검사도 이미 처리한 94개 결과에 대한 반복 OCR은 중지하며, 원본·기존 큐·결과 보관은 유지합니다.
- `ALPHA_TOUCHES_CROP_BORDER_REVIEW`는 겹쳐진 불투명한 원본 배경/윤곽 때문에 생길 수 있으므로 원본 네이티브 픽셀 그대로 **검토용 크롭**을 별도 생성하고 `edge_warning` 및 `human_review_required=true`를 남깁니다. 진짜 빈 픽셀/너무 작은 후보는 HOLD합니다. 번역/합성/DDS 수정/게임 PASS 선언은 하지 않습니다.
- C CPU 쿼터 0.75 → **1.5**. A/B 서비스 및 설정은 건드리지 않습니다.
- 실제 N100 108개 원본 ZIP/매니페스트를 사용한 격리 시험에서 첫 2개/다음 2개 파일 처리, 재검사 방지, 원본 픽셀 일치 PASS. 실제 신규 생성량과 실게임 검증 여부는 **새 GitOps C 이미지가 배포된 후** 재측정해야 합니다.
- Portainer GitHub 스택 `localization-controller-recovery-20260928`, Compose `tools/chat-controller/localization-recovery-v1/docker-compose.yml`을 최신 커밋으로 **Rebuild + Redeploy**해야 적용됩니다. 독립 C Docker 재생성은 금지.

---

## 2026-10-17 GitHub/Portainer C 슬롯 — 최신 사용자 지시

- **C 영문 원본 크롭은 단독 Docker Compose 금지**. 이 GitOps 스택의 `outrun-c-english-native-crop` 서비스만 사용합니다. 배포 이름 `outrun-localization-c-english-crop` (기존 독립 컨테이너 `outrun-c-original-english-crop`와 별개).
- 고정 Git 리포지토리: `thp32tt/OutRun2006Tweaks`, 브랜치 `localization-controller-recovery-20260928`, Compose `tools/chat-controller/localization-recovery-v1/docker-compose.yml`.
- C용 Docker 빌드: `c_english_crop/Dockerfile`. Tesseract+Pillow+NumPy, GitHub에 고정한 `loop.py`, `ocr_hd108.py`, `ocr_recognize.py`, `discover.py` 및 원본 검증/크롭 모듈을 포함. Compose 서비스는 포트를 열지 않고 `network_mode:none`, `user=1002:1002`, 읽기전용 소스, 별도 기존 C 결과 폴더에만 쓰기.
- N100에서 이미 검증한 분할 전 원본 HD PNG **108/108개** 위치: `/home/chatgpt-runner2/work/c_salvage_text_roi/c_original_hd_crop_only/hd_original_108_verified`. `hd108_import_receipt.json`과 `hd108_ocr/cursor.json`, 이전 `hd108_outputs`, DDS `outputs`, `queue_specs`, 255건 아카이브를 새로 만들거나 덮어쓰지 않습니다.
- C는 108개 원본 PNG를 두 개씩 순환 검사하고, 기존 SHA/DDS 검증 원본 그룹 네 개씩을 별도 검사합니다. 공식 검토 영문 OCR 신뢰도/중복/잘림 검사 통과만 원본 네이티브 픽셀 그대로 크롭. **GAME_RUNTIME=UNTESTED**. 기존 986 타일/이미지생성 결과/한글 합성/DDS 출력/VR은 실행하지 않습니다.
- **A/B는 계속 중지**: `AUTO_SEND=false`, `SCHEDULE_MINUTES=""`, `restart=no`; C는 독립 서비스로 `restart=unless-stopped`이므로 서버 재시작 뒤에 복구됩니다. A/B의 ChatGPT 슬롯 수는 2이며 C는 웹 탭이 아닌 배포용 C 작업 서비스입니다.
- 기존 별도 컨테이너 `outrun-c-original-english-crop`는 원복하거나 켜지 말고 **새 Portainer GitOps C 배포 이전에 정지/재시작 정책 해제**합니다. 새 C는 기존 파일과 체크포인트를 사용하므로 중복 컨테이너 실행은 금지합니다.
- 이 문서/깃허브 커밋은 **실제 배포 완료 증빙이 아닙니다**. Portainer에서 같은 스택을 **Pull latest + Rebuild + Redeploy**해야 반영됩니다. C 상태는 `outrun-localization-c-english-crop` 로그와 `hd108_ocr/last_scan.json` 갱신 시각으로 확인합니다. `--no-build`로 재배포하면 C 이미지는 존재하지 않을 수 있으므로 사용하지 마세요.

---

> **2026-10-16 v2 Docker STOP/FAIL-CLOSED:** all scheduled localization sends and retired C-SALVAGE are disabled. See [V2_DOCKER_AUTOMATION_POLICY_20261016.md](V2_DOCKER_AUTOMATION_POLICY_20261016.md). The 2026-10-14 A/B 986-tile schedule below is **HISTORICAL ONLY**, not current production. No Portainer restart/deploy was performed.

> **Next deployment profile (GitHub-only until user manually redeploys Portainer; 2026-10-14):**
> **A/B image translation slots** with `CHAT_SLOTS=2`. A runs :00/:10/:20/:30/:40/:50
> on original PNG ordinals **1–500**; B runs :05/:15/:25/:35/:45/:55 on
> original ordinals **501–986**. Each accepted batch gets its **own new chat**
> and up to **five attached source images**, requesting the same number of
> **separate** ImageGen Korean results (no collage).
>
> The existing **`아웃런 한글화 신규` project Library** is the mandatory
> image-save completion gate (separate `outrun_kor` folder deprecated).
> The new browser verifier checks all generated PNG content SHA256 against
> distinct actual Library `libfile_` items. Missing / mismatched output is HOLD.
> The candidate exporter uses `_k.png` suffix on local output only and records
> original/generated sizes. Original English PNGs, DDS hashes, and orientation
> transformation remain unchanged. One corrupt PNG source stays quarantined.
>
> See **[AB_HD_IMAGEGEN_20261014.md](AB_HD_IMAGEGEN_20261014.md)** for the
> authoritative current schedule, prompt, safety checks and deployment guidance.
> A-only material in this README and older documents below is **historical**.
> The currently running N100 container is **not** changed by a GitHub commit.
>
# Localization Recovery Controller v1

Purpose: run the compact 2026-09-28 localization workflow on a fresh ChatGPT account/project without importing later accumulated controller requirements.

## Frozen sources

- Controller code snapshot: `3629be2bc7dd6286e69eb400fab06ca3822270da` (2026-09-28 11:20 KST)
- Localization branch: `korean-localization-recovery-20260928`
- Localization baseline: `11631c5f12037bcd01cda1af57ec9bc564af4bcf`

The controller started from the stable historical snapshot. Recovery-specific changes are kept minimal: isolated packaging/prompts plus deterministic A/B/C1/C2 schedule mapping; no queue or state-machine expansion is added.

## Glyph-by-glyph scale review (2026-10-11)

A/B/C1 production/self-QA, C2 independent QA and subsequent C3 strict checks all follow the GitHub branch canonical `docs/KOREAN_LOCALIZATION_GLYPH_SCALE_POLICY.md`. Translation-dependent whole-sentence width/height/aspect/glyph-count differences are not defects. Smaller legible Korean glyphs and shorter translated phrases PASS size criterion. Each glyph still needs intact strokes/counters/readability at native/75/50, and any 1px original source glyph/effect bbox growth remains FAIL; remaining independent QA, C3 and actual in-game status are not bypassed. The new Git policy takes effect on reading latest contract; use user-rebuilt Docker image only to refresh the bundled short prompts.

## Historical schedule (not current — consult AB_HD_IMAGEGEN_20261014.md)

- :00 — A production/self-QA
- :10 / :40 — C1 ChatGPT ImageGen production/self-QA (new even indexes % 4 == 2)
- :20 / :50 — C2 independent final QA (all A/B/C1 candidate indexes and unindexed special C work)
- :30 — B ChatGPT ImageGen production/self-QA (new even indexes % 4 == 0)

The six-launch-per-hour mapping follows the latest recovery localization contract. Four independent tabs (A/B/C1/C2) are persisted; prior C history is migrated to C1 without clearing its URL or counts. A retains native/manual production; B and C1 use real ChatGPT ImageGen production with separate even-index shards; C2 alone provides independent QA for all production lanes. Existing assigned/in-flight work is not overwritten. Each slot starts a new ChatGPT conversation after 5 successful sends, deferred while busy. The original task/event-ID and queue engines are **not** imported. The scheduled-send watchdog remains OFF by default; AUTO_SEND remains OFF by default until the user enables it.

## Portainer

Git repository:
`https://github.com/thp32tt/OutRun2006Tweaks.git`

Reference:
`refs/heads/localization-controller-recovery-20260928`

Compose path:
`tools/chat-controller/localization-recovery-v1/docker-compose.yml`

Required variables:

- `LOCALIZATION_PROJECT_URL=<new account's clean ChatGPT project URL>`
- `AUTO_SEND=false` initially
- `VNC_PASSWORD=<password>`

Side-by-side test ports:

- noVNC: `http://<N100-IP>:6082/vnc.html`
- status: `http://<N100-IP>:8788/`

## Historical first deployment rule (not current AB workflow)

1. Create a new ChatGPT Project on the other account.
2. Do not copy old project instructions or memories.
3. Connect GitHub with write access.
4. Set only the new project's URL in `LOCALIZATION_PROJECT_URL`.
5. Deploy with `AUTO_SEND=false`.
6. In noVNC, verify login/project and manually run one A command.
7. Confirm a real commit lands on `korean-localization-recovery-20260928`.
8. Then change `AUTO_SEND=true` and redeploy.

Do not add queue engines, Production/Event ID systems, C0-C6 state machines, VR rules, or long duplicated prompts unless a concrete failure requires one change at a time.

## Chrome stability maintenance (recovery v1 only, 2026-10-10)

The Portainer branch/reference and Compose path at the top remain unchanged.

- Every 30 seconds, inspect each configured tab independently (A/B after the new Compose deployment) for closed/missing tabs, renderer crash, Chromium error screen (two checks), or an unresponsive page (three failed probes). Replace only the affected tab and reopen its saved project/chat URL. Never auto-send a duplicate task.
- Every 120 minutes, recycle the **whole Chrome/controller container**. If ChatGPT is responding, defer up to 30 extra minutes; after the maximum deadline a running answer may be interrupted, but its saved URL/slot state is kept. The previous Chrome instance is fully stopped before profile cache maintenance.
- Delete only disposable Chrome disk/code/GPU/shader caches. Preserve profile Cookies, Network/Cookies, Local Storage, IndexedDB, Login Data, Session Storage, Sessions and Service Worker data. **No automatic logout or profile volume removal.** ChatGPT server-side session expiry may nevertheless require manual login.
- Existing separate data and log volumes, Portainer VNC/status ports (6082/8788), role schedules, High preference and restart policy are retained.
- Memory limit: 4 GiB; /dev/shm: 1 GiB. A prior Chrome crash can be due to many causes; inspect Docker OOMKilled, /logs/chrome.log and /logs/ui-watchdog.log rather than assuming every error is OOM.
- Maintenance logs/state: /logs/chrome-recycle.log, /logs/controller.log, /logs/tab-recovery/, /data/state/chrome_recycle.json and status page. Chrome recycle does not consume a new task number.
- Migration: an existing A/B/C registry is converted to A/B/C1/C2 without discarding A/B/C chat history. On daily logical-date change, archive the checkpoint and keep the same saved URLs and counts.
- Regression scripts: `python tools/chat-controller/localization-recovery-v1/tests/test_recovery_maintenance.py` and `bash tools/chat-controller/localization-recovery-v1/tests/test_chrome_cache_clean.sh`.

**Portainer:** after the CI check, rebuild/redeploy the original `localization-controller-recovery-20260928` branch / `tools/chat-controller/localization-recovery-v1/docker-compose.yml` stack, preserving named volumes. Do NOT deploy `chat-controller-downloads` / `v0.4-localization-v2` for this restored workflow. A commit to GitHub alone does not update running Docker containers.