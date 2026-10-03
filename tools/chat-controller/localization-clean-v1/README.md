# OutRun Korean Localization Controller — clean-v1

This controller restores the simple 2026-09-28 workflow on an isolated branch.

- Base checkpoint: c7a7217735895473b6b8ff0326f458bb23446ec7 (2026-09-28 22:39 KST)
- Target branch: korean-localization-20260928-clean-v1
- Flow: A+B production in parallel -> C reconciliation/QA -> next wave
- Durable completion: exact Git commit marker [AUTO:<TASK_ID>]
- Browser retry/recovery keeps the same TASK_ID.
- No C0-C6 pipeline, EVENT_ID, rollover schema, per-step Actions gate, or task-latch machinery.
- Git repository state is authoritative; controller JSON is disposable orchestration state.

## Portainer

Repository:
https://github.com/thp32tt/OutRun2006Tweaks.git

Reference:
refs/heads/korean-localization-20260928-clean-v1

Compose path:
tools/chat-controller/localization-clean-v1/docker-compose.portainer.yml

Required environment:
- LOCALIZATION_PROJECT_URL=<new account's ChatGPT localization project URL>
- VNC_PASSWORD=<password>
- AUTO_SEND=false for the first login/test
- optional GITHUB_TOKEN for authenticated controller read polling

Ports:
- noVNC: 6081
- controller status: 8788

Use the new clean-v1 volumes. Do not attach the old localization controller /data volume, because it contains old queue/task/browser state.

## Runtime behavior

Each wave creates exactly three task IDs:
- LOCALIZATION-A-W00001
- LOCALIZATION-B-W00001
- LOCALIZATION-C-W00001

A/B start independently. C cannot start until both A and B have a durable marker commit. C then reconciles shared state. After C's marker commit appears, the controller increments the wave and immediately prepares the next A+B pair.

If an assistant response stops without a marker commit, the controller sends a short continuation in the same chat. Only after prolonged inactivity or an actual conversation-length condition does it open a fresh chat, preserving the same TASK_ID.
