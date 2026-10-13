# A-only image-src mount and multiple task IDs — 2026-10-13

## Portainer Git source

- Repository URL: `https://github.com/thp32tt/OutRun2006Tweaks.git`
- Repository reference: `refs/heads/localization-controller-recovery-20260928`
- Compose path: `tools/chat-controller/localization-recovery-v1/docker-compose.yml`
- Additional paths: empty
- Existing stack only; user-controlled **Pull and redeploy**, which rebuilds via `build: .` / `pull_policy: build`.

## Runtime configuration

- A-only 3-minute schedule at :00/:03/:06/…/:57 (KST): `AUTO_SEND=true`, `SCHEDULE_MINUTES=0,3,6,9,12,15,18,21,24,27,30,33,36,39,42,45,48,51,54,57`, `WATCHDOG_ENABLED=false`. Only **one automatic submission per unique TASK_ID** is permitted; the scheduler keeps checking every 3 minutes but does not repeat the same sent task.
- `CHAT_SLOTS=1`: one ChatGPT A tab only. B, C1 and C2 **never open tabs, run watchdog tasks, or dispatch scheduled prompts**. Existing inactive slot records are preserved separately under `/data/state/retired_{B,C1,C2}_slot_before_a_only_20261013.json` if present; a conflicting backup stops startup rather than overwriting history.
- `REQUIRE_PROJECT_URL=false` prevents an empty optional Project URL from disabling `AUTO_SEND`; the controller reuses the persisted A chat URL when available.
- The role dispatcher (not only Compose) maps every 3-minute tick to A. Other roles never dispatch.
- `OUTRUN_A_SINGLE_SMOKE_TASK_ID=""` removes Q217 task-ID pinning. The next eligible A task is read from a source manifest, not hardcoded.
- Host `/home/chatgpt-runner2/work/image-src` is mounted RW as `/data/imagegen` with `create_host_path=false`. The directory exists on N100. The existing `/data` and `/logs` volumes, noVNC `6082`, status `8788` and VR controller are not changed.

## File layout (required by the current input loader)

```text
/home/chatgpt-runner2/work/image-src/
  pending_A.json          # operator supplies/updates for each task
  inputs/
    A/
      q001_READABLE.png
      q002_READABLE.png
  sent/                   # tool writes this; do not delete
```

Example `pending_A.json` for *one* source, with SHA values calculated from actual files:

```json
{
  "role": "A",
  "task_id": "OUTRUN-A-Q001-IMG-20261013",
  "png": "A/q001_READABLE.png",
  "png_sha256": "<actual lowercase 64-character SHA256 of q001_READABLE.png>",
  "source_dds_sha256": "<actual lowercase 64-character SHA256 of original DDS>",
  "prompt": "첨부한 영문 원본 PNG를 참고하여 대상 문구만 자연스러운 한글로 바꾸고 아이콘과 배경, 알파 채널을 보존하세요."
}
```

Replace the SHA placeholders with actual hex digests. `png` must resolve inside `inputs/`. A file upload happens only after validating task ID, manifest, PNG SHA, PNG CRC and dimensions. The original DDS SHA field is format-validated here; actual DDS-byte provenance still requires separate verification.

To submit the next image, stage a new PNG and **update `pending_A.json` to a new distinct task_id, PNG path, hashes and approved prompt**. `sent/A_<TASK_ID>.json` prevents a duplicate send. Do not remove the sent records. The controller does *not* discover all directory PNGs or make manifests automatically; mounting the folder alone does not cause uploads. The current A test runs at the next 3-minute minute mark only when a valid manifest is present; the same task cannot be sent twice.

After Portainer rebuild: verify mount and env values, ChatGPT authentication, actual attachment preview and post-send receipt for one A task before preparing a second. Message submission is not proof of completed ImageGen output or DDS/QA. Until directly tested: `UPLOAD_RUNTIME=UNTESTED`, `IMAGEGEN_E2E=UNTESTED`, `RUNTIME_VALIDATION=UNTESTED`.

## History

The Q217 one-shot pilot had a different host bind and a hard-coded `OUTRUN-A-Q217-IMG-SMOKE-20261013` gate. See `Q217_A_IMAGEGEN_SMOKE_DEPLOY_20261013.md` for historical evidence only; it is superseded by this operational procedure.

## False-positive fix 2026-10-14

Source upload is confirmed only after PNG thumbnail and Remove button exist and Uploading indicator disappears. A routes into the named Korean-localization project; it retains inline Create image mode while inserting text and does not mark the run as sent unless a durable chat URL, a user message with exact task ID, and a user image are all verified. Unverified submissions are held against duplicate sends. Preserve original disputed send evidence.