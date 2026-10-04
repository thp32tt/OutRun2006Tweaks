# Localization Recovery Controller v1

Purpose: run the compact 2026-09-28 localization workflow on a fresh ChatGPT account/project without importing later accumulated controller requirements.

## Frozen sources

- Controller code snapshot: `3629be2bc7dd6286e69eb400fab06ca3822270da` (2026-09-28 11:20 KST)
- Localization branch: `korean-localization-recovery-20260928`
- Localization baseline: `11631c5f12037bcd01cda1af57ec9bc564af4bcf`

The controller started from the stable historical snapshot. Recovery-specific changes are kept minimal: isolated packaging/prompts plus deterministic A/B/C schedule mapping; no queue or state-machine expansion is added.

## Schedule

- :00 / :30 — A production/self-QA
- :10 / :40 — B production/self-QA
- :20 / :50 — C cross-lane final QA

Each lane runs every 30 minutes, staggered by 10 minutes. The minute-to-lane mapping is deterministic, so a skipped or failed send does not rotate the later lanes out of phase. Three role-specific chat slots are used. Each slot is recycled into a fresh ChatGPT conversation after 5 successful scheduled sends; if the fifth response is still generating at the next slot time, recycling is deferred rather than interrupting it. Watchdog is OFF by default. AUTO_SEND is OFF by default.

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
