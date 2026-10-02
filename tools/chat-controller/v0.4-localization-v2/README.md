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

## Localization worker model

The production controller uses independent parallel lanes:

```text
Producer A  ─────┐
                 ├── Artifact Queue ─── QA Validator C
Producer B  ─────┘
```

### Producer lanes

- A and B continuously produce DDS localization candidates.
- A and B are independent production workers.
- A/B production must not stop because unrelated assets are waiting for QA.
- Every candidate must include the required artifact evidence before entering QA.

### QA lane

- C continuously consumes completed A/B artifacts.
- C validates producer output using the required QA rules.
- C PASS/REWORK decisions apply to the affected asset only.
- A QA failure must not block unrelated production assets.

## State and source rules

- GitHub remains the SSOT for code, state definitions, and tracked changes.
- N100 remote execution is supported for controller operation, Docker management, and Portainer deployment.
- Approved Google Drive canonical HD source transport may be used for original DDS acquisition.
- Drive DDS sources must preserve checksum, dimensions, format, alpha, mip requirements, and localization quality gates.
- Existing localization artifacts and VR deployment remain separate.

## Slot model

Localization execution uses three logical workers:

```text
slot-1 = Producer A
slot-2 = Producer B
slot-3 = QA C
```

Restarting the controller must preserve this role separation.

## Queue rules

- Production queue continues while QA is processing other assets.
- Blocking is asset-scoped, not global.
- Rework only returns the affected asset to production.
- Completed assets are not reprocessed unless explicitly reopened by QA.

## Build

```sh
docker compose -f tools/chat-controller/v0.4-localization-v2/docker-compose.yml config
docker compose -f tools/chat-controller/v0.4-localization-v2/docker-compose.yml build
docker compose -f tools/chat-controller/v0.4-localization-v2/docker-compose.yml up -d
```

The image builds from `v0.4/src` and uses A/B/C localization prompts. VR controller deployment is independent. Do not delete existing volumes. Runtime game validation remains `UNTESTED` until performed.
