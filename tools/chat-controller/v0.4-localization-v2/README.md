# Localization Controller v2

## Production deployment entrypoint

Use only this controller for Korean localization production:

- Repository: `thp32tt/OutRun2006Tweaks`
- Branch: `chat-controller-downloads`
- Compose:
  `tools/chat-controller/v0.4-localization-v2/docker-compose.yml`

Do not deploy the older controller folders directly:

- `tools/chat-controller/v0.4` = legacy/reference
- `tools/chat-controller/localization` = previous localization fork/reference
- `tools/chat-controller/v0.5` = development/reference unless explicitly promoted

## Runtime

Portainer (Docker Standalone, amd64): configure:

- `LOCALIZATION_PROJECT_URL`
- `GITHUB_TOKEN`
- `VNC_PASSWORD`

Start with `AUTO_SEND=false`, verify ChatGPT project and GitHub connection, then enable `AUTO_SEND=true` and redeploy.

## Localization flow

- A/B produce material DDS candidates.
- C consumes exact producer SHAs and performs QA disposition.
- E is not scheduled.
- Existing localization artifacts and VR deployment remain separate.

## State and source rules

- GitHub remains the SSOT for code, state definitions, and tracked changes.
- N100 remote execution is supported for controller operation, Docker management, and Portainer deployment.
- Approved Google Drive canonical HD source transport may be used for original DDS acquisition.
- Drive DDS sources must preserve checksum, dimensions, format, alpha, mip requirements, and localization quality gates.

## Build

```sh
docker compose -f tools/chat-controller/v0.4-localization-v2/docker-compose.yml config
docker compose -f tools/chat-controller/v0.4-localization-v2/docker-compose.yml build
docker compose -f tools/chat-controller/v0.4-localization-v2/docker-compose.yml up -d
```

The image builds from `v0.4/src` and uses A/B/C localization prompts. VR controller deployment is independent. Do not delete existing volumes. Runtime game validation remains `UNTESTED` until performed.
