# Localization Controller v2

Portainer (Docker Standalone, amd64): repository `thp32tt/OutRun2006Tweaks`, branch `chat-controller-downloads`, compose path `tools/chat-controller/v0.4-localization-v2/docker-compose.yml`.

Set `LOCALIZATION_PROJECT_URL`, `GITHUB_TOKEN` (repository read access), and `VNC_PASSWORD` in Portainer. Start with `AUTO_SEND=false`, open port 6082 and sign in to ChatGPT; after verifying the project and connected GitHub plugin, set `AUTO_SEND=true` and redeploy. Fresh browser volumes cannot inherit an authenticated session automatically. Status: port 8789. Ports can be overridden with `LOCALIZATION_VNC_PORT` and `LOCALIZATION_STATUS_PORT`.

A owns even queue indexes; B owns odd indexes. A/B produce material DDS results, then C consumes their exact SHAs. The next wave waits for C dispositions and its Actions gate. HOLD or incomplete C evidence stops dispatch. Resolve evidence, then clear `qa_hold` in preserved queue state to resume. E is not scheduled; historical E records are archived in queue state, never deleted. Existing localization artifacts and VR deployment are untouched.

TASK lookup uses exact record, TASK_ID.*, dispatch, reconcile, rollover, lane+number, number. Embedded TASK_ID must match even for broad fallbacks. Only missing paths fall through; auth errors and rate limits stay distinct. Generic Retry gets one recovery attempt per chat, then rollover with the same TASK_ID and ATTEMPT. Rate limits still respect backoff. MAX_CHAT_ROLLOVERS_PER_TASK=0 means unlimited rollovers.

Execution environment:

- N100 remote execution is supported for controller operation, Docker management, Portainer deployment, and maintenance workflows.
- GitHub remains the source of truth for code, state definitions, and tracked changes.
- Approved Google Drive canonical HD source transport may be used for original DDS acquisition when required by localization tasks.
- Drive-sourced DDS files must preserve checksum, dimensions, format, alpha, mip requirements, and localization quality gates.
- VR controller and localization controller remain separate deployments.

Build locally from repository root:

```sh
docker compose -f tools/chat-controller/v0.4-localization-v2/docker-compose.yml config
docker compose -f tools/chat-controller/v0.4-localization-v2/docker-compose.yml build
docker compose -f tools/chat-controller/v0.4-localization-v2/docker-compose.yml up -d
```

The image builds from v0.4/src; it never copies the older localization fork. It ships A/B/C prompts only and rejects conversion mode. Volumes and network are dedicated to v2. Stop the older localization controller before enabling auto-send on v2 to prevent duplicate production. Do not delete old volumes. Game runtime validation remains UNTESTED.
