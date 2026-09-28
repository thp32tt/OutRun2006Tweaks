# OutRun Chat Controller v0.4 — Portainer deployment

## Architecture

N100 runs only the browser/controller containers. Project work must be performed directly against GitHub by ChatGPT.

- VR SSOT: `thp32tt/OutRun2006Tweaks` / `vr-d3d9ex-focus`
- Korean localization SSOT: `thp32tt/OutRun2006Tweaks` / `korean-localization-clean`
- Do not use N100 local clones/worktrees as project workspaces.
- Each ChatGPT account must have working GitHub read/write access before AUTO_SEND is enabled.

## Portainer Git source

Repository:
`https://github.com/thp32tt/OutRun2006Tweaks.git`

Reference:
`refs/heads/chat-controller-downloads`

## VR stack

Stack name:
`outrun-chat-vr`

Compose path:
`tools/chat-controller/v0.4/docker-compose.portainer-vr.yml`

Environment variables:

- `VR_PROJECT_URL=<full ChatGPT VR project URL>`
- `AUTO_SEND=false`
- `WATCHDOG_ENABLED=false`
- `VNC_PASSWORD=<your password>`

Access:

- noVNC: `http://<N100-IP>:6080`
- status: `http://<N100-IP>:8787`

Log in with the VR ChatGPT account and verify the configured project opens.

## Localization stack

Stack name:
`outrun-chat-localization`

Compose path:
`tools/chat-controller/v0.4/docker-compose.portainer-localization.yml`

Environment variables:

- `LOCALIZATION_PROJECT_URL=<full ChatGPT localization project URL>`
- `AUTO_SEND=false`
- `WATCHDOG_ENABLED=false`
- `VNC_PASSWORD=<your password>`

Access:

- noVNC: `http://<N100-IP>:6081`
- status: `http://<N100-IP>:8788`

Log in with the localization ChatGPT account and verify the configured project opens.

## Before enabling automation

For each account:

1. Verify the correct ChatGPT account is logged in.
2. Verify the configured ChatGPT project opens from noVNC.
3. Verify GitHub read/write access is available to ChatGPT.
4. Run one manual task and confirm GitHub is used directly.
5. Confirm no N100 local clone/worktree is used for project changes.

Then change `AUTO_SEND=true` in that Portainer stack and redeploy.

`REQUIRE_PROJECT_URL=true` is built into both compose files. If the project URL is missing, AUTO_SEND is blocked even when requested.

## Isolation

VR volumes:
- `outrun_chat_vr_data`
- `outrun_chat_vr_logs`

Localization volumes:
- `outrun_chat_localization_data`
- `outrun_chat_localization_logs`

Never share `/data` between the two stacks. It contains the Chrome profile, login session, controller state, and VNC password file.

## Current resource limits

Each controller:

- memory hard limit: 3 GiB
- memory reservation: 1 GiB
- CPU limit: 1.5
- shared memory: 768 MiB

## Safety

If GitHub access is unavailable, the controller prompt instructs ChatGPT to report the failure. It must not fall back to the N100 local repository.
