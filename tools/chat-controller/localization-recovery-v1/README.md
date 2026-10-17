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