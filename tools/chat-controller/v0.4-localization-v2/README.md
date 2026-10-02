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

## Parallel localization flow

A/B/C are independent pipeline roles.

```
A producer  ----\
                +---- artifact queue ---- C QA validator
B producer  ----/
```

### A/B production lanes

A and B continuously produce DDS candidates.

Rules:

- Claim independent assets.
- Produce Korean DDS candidates.
- Preserve dimensions, format, alpha, mip and artwork requirements.
- Store commit/artifact evidence.
- A/B production does not stop because unrelated assets are waiting for QA.

### C validation lane

C continuously consumes completed A/B artifacts.

Rules:

- Validate exact artifact SHA.
- Perform source/output comparison.
- Record PASS or REWORK.
- Block only the affected asset.

A/B production and C validation run concurrently.

## State and source rules

- GitHub remains the SSOT for code, state definitions, and tracked changes.
- N100 remote execution is supported for controller operation, Docker management, and Portainer deployment.
- Approved Google Drive canonical HD source transport may be used for original DDS acquisition.
- Drive DDS sources must preserve checksum, dimensions, format, alpha, mip requirements, and localization quality gates.
- VR controller deployment remains independent.

## Build

```sh
docker compose -f tools/chat-controller/v0.4-localization-v2/docker-compose.yml config
docker compose -f tools/chat-controller/v0.4-localization-v2/docker-compose.yml build
docker compose -f tools/chat-controller/v0.4-localization-v2/docker-compose.yml up -d
```

The image builds from `v0.4/src` and uses A/B/C localization prompts. Do not delete existing localization artifacts or volumes. Runtime game validation remains `UNTESTED` until performed.
