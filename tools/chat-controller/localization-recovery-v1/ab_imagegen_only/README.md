# OutRun 2006 A/B Korean PNG image-only automation — 2026-10-17

## Active GitOps stack (no additional Portainer stack)

- GitHub repository: `thp32tt/OutRun2006Tweaks`
- Branch: `localization-controller-recovery-20260928`
- Existing Compose: `tools/chat-controller/localization-recovery-v1/docker-compose.yml`.
- **Only newly added service**: `outrun-ab-imagegen-only`, cache image `outrun-imagegen-a-stable:20261013`.
- Existing C service `outrun-c-english-native-crop` and its code, volumes, OCR schedule are unchanged.
- Legacy `outrun-chat-controller-localization-recovery` A/B browser dispatcher remains `AUTO_SEND=false` and `SCHEDULE_MINUTES=""`, avoiding duplicate sends. Do not re-enable it.
- N100 prepared independent A/B files under `/home/chatgpt-runner2/work/outrun-ab-imagegen-only`; old C and old A_state/B_state untouched.

## Scheduler (Asia/Seoul KST)

A: at minutes **00, 20, 40**.
B: at minutes **10, 30, 50**.
Maximum 3 attempts/hour each, never duplicate a task. Empty verified queue => IDLE. A task with an uncertain ChatGPT send is held for manual review, not auto-resubmitted.

Six initial new batch sheets, all English source native HD 1:1 SHA-matched and Korean transcription from reviewed manifest (not the already manually generated F3 sheets):
- A Q054 first 6 minigame instructions; Q054 next 6; Q053 6 untouched words. **18 phrases in 3 sheets.**
- B Q060 4 untouched HUD labels; Q060 next 3; Q057 7 untouched words. **14 phrases in 3 sheets.**
- 5 Q054 source crops with `HOLD_ADJACENT_PHRASES` are excluded. Total **32 distinct new phrase inputs** (not 32 completed Korean images).

Generated file `/output/{A|B}/<task_id>_KOR_BATCH.png`, SHA and candidate-level QA record `/state/<task_id>.json`. No DDS edit, CLEAN, Korean sprite splitting, C crop changes, game patch or release status. Actual text meaning/QA still independent.

## Portainer user action required to activate

The N100 MCP user is `1002:1002` and does not have docker.sock access; `sudo -n docker` needs a password. **GitHub commit and N100 staging do not launch containers.** In Portainer, open the **existing** localization-recovery Stack whose Git repo and branch are as above, verify image tag `outrun-imagegen-a-stable:20261013` exists on N100, set `VNC_PASSWORD` as a nontrivial private secret, then select **Pull latest / Redeploy**. No new Stack. Do not restart standalone `outrun-imagegen-a` or any VR Stack.

New dedicated noVNC runs at `http://N100-IP:6083/vnc.html` (old port 6082 remains separate). Sign in to ChatGPT's **아웃런 한글화 신규** project inside the new saved Chromium profile. Project URL default was taken from N100's last bound A_state; override with `LOCALIZATION_PROJECT_URL` only if it moved. On missing login/project or changed UI selectors, tasks HOLD without sending. Only one active browser message at a time.

## Execution, logs, independent verification

N100 prepared directory: `work/outrun-ab-imagegen-only/app/`.
Source layout, source SHA and 6 distinct JSON job manifests are already validated by `preflight_queue_20261017.py`.
Four scheduler/idempotence unittests pass in N100, and YAML was parsed with 3 services and C `network_mode:none`.
After deployment, inspect container `outrun-ab-imagegen-only`, logs, `/state/audit.jsonl`, `/output/A/` and `/output/B/`; verify actual ChatGPT attachment and screenshot. Do not report live send / production PNG until confirmed in runtime logs and output hashes.

Job results with valid PNG RGBA receive `CAPTURED_QA_PENDING`; checking actual Korean glyphs and absence of background/noise remains required. Production **ENDS** with Korean image files. Final DDS composition is a separate future activity requiring a separate authorization.

## Safety

- No duplicate submits: atomic per-task state before send.
- Only reviewed original crops and official transcription strings; no inferred translations, no legacy 986 tiles, no old generated artwork reuse.
- Failing browser/UI/upload/save => HOLD, never auto-resend an uncertain request.
- C OCR branch and existing production controllers untouched except for new Compose service.
- Existing source/controller volumes never deleted, reseeded, or reset.