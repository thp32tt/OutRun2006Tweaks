# Localization Recovery Controller v1

Purpose: run the compact 2026-09-28 localization workflow on a fresh ChatGPT account/project without importing later accumulated controller requirements.

## Frozen sources

- Controller code snapshot: `3629be2bc7dd6286e69eb400fab06ca3822270da` (2026-09-28 11:20 KST)
- Localization branch: `korean-localization-recovery-20260928`
- Localization baseline: `11631c5f12037bcd01cda1af57ec9bc564af4bcf`

The controller started from the stable historical snapshot. Recovery-specific changes are kept minimal: isolated packaging/prompts plus deterministic A/B/C1/C2 schedule mapping; no queue or state-machine expansion is added.

## Schedule

- :00 — A production/self-QA
- :10 / :40 — C1 independent final QA (odd queue indexes and unindexed special C work)
- :20 / :50 — C2 independent final QA (even queue indexes)
- :30 — B production/self-QA

The six-launch-per-hour mapping follows the latest recovery localization contract. Four independent tabs (A/B/C1/C2) are persisted; prior C history is migrated to C1 without clearing its URL or counts. A/B use the original production prompts; C1/C2 share C quality requirements but never review each other's parity shard. Each slot starts a new ChatGPT conversation after 5 successful sends, deferred while busy. The original task/event-ID and queue engines are **not** imported. The scheduled-send watchdog remains OFF by default; AUTO_SEND remains OFF by default until the user enables it.

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

## First deployment rule

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

- Every 30 seconds, inspect each of the four tabs independently for closed/missing tabs, renderer crash, Chromium error screen (two checks), or an unresponsive page (three failed probes). Replace only the affected tab and reopen its saved project/chat URL. Never auto-send a duplicate task.
- Every 120 minutes, recycle the **whole Chrome/controller container**. If ChatGPT is responding, defer up to 30 extra minutes; after the maximum deadline a running answer may be interrupted, but its saved URL/slot state is kept. The previous Chrome instance is fully stopped before profile cache maintenance.
- Delete only disposable Chrome disk/code/GPU/shader caches. Preserve profile Cookies, Network/Cookies, Local Storage, IndexedDB, Login Data, Session Storage, Sessions and Service Worker data. **No automatic logout or profile volume removal.** ChatGPT server-side session expiry may nevertheless require manual login.
- Existing separate data and log volumes, Portainer VNC/status ports (6082/8788), role schedules, High preference and restart policy are retained.
- Memory limit: 4 GiB; /dev/shm: 1 GiB. A prior Chrome crash can be due to many causes; inspect Docker OOMKilled, /logs/chrome.log and /logs/ui-watchdog.log rather than assuming every error is OOM.
- Maintenance logs/state: /logs/chrome-recycle.log, /logs/controller.log, /logs/tab-recovery/, /data/state/chrome_recycle.json and status page. Chrome recycle does not consume a new task number.
- Migration: an existing A/B/C registry is converted to A/B/C1/C2 without discarding A/B/C chat history. On daily logical-date change, archive the checkpoint and keep the same saved URLs and counts.
- Regression scripts: `python tools/chat-controller/localization-recovery-v1/tests/test_recovery_maintenance.py` and `bash tools/chat-controller/localization-recovery-v1/tests/test_chrome_cache_clean.sh`.

**Portainer:** after the CI check, rebuild/redeploy the original `localization-controller-recovery-20260928` branch / `tools/chat-controller/localization-recovery-v1/docker-compose.yml` stack, preserving named volumes. Do NOT deploy `chat-controller-downloads` / `v0.4-localization-v2` for this restored workflow. A commit to GitHub alone does not update running Docker containers.
