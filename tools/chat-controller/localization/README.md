# Standalone Korean Localization Controller

This directory is the independent Korean-localization runtime.

- hard-locked to localization mode;
- exactly three slots: A, B, C;
- image contains only localization A/B/C prompts;
- no VR/DX11/DXVK prompt is packaged;
- VR keeps its own existing controller/compose;
- stale D/E runtime records from an older shared controller are archived, not executed;
- persistent Generic Retry and missing-composer WAIT_CHAT states roll over to a fresh localization-project chat under the same TASK_ID.

Portainer:
- branch: `chat-controller-downloads`
- compose: `tools/chat-controller/localization/docker-compose.portainer.yml`

Set `LOCALIZATION_PROJECT_URL`, `VNC_PASSWORD`, and optionally `GITHUB_TOKEN`. This stack defaults `AUTO_SEND=true`.
