# Portainer deployment

Current controller version: v0.5.

Use branch chat-controller-downloads and one compose path:

- Localization: tools/chat-controller/v0.5/docker-compose.portainer-localization.yml
- DX11/DXVK: tools/chat-controller/v0.5/docker-compose.portainer-vr.yml

The v0.5 compose files intentionally reuse the existing v0.4 Docker volume names so the authenticated Chrome profile survives migration. v0.5 uses new state filenames (controller_v05.json/runtime_v05.json), therefore old queue_state.json/chat_registry.json files are ignored.

Required stack variables:
- GITHUB_TOKEN
- LOCALIZATION_PROJECT_URL for localization, or VR_PROJECT_URL for conversion
- VNC_PASSWORD

Existing Portainer stacks that still point at the v0.4 compose files are supported by compatibility compose wrappers on this branch; after redeploy they build the v0.5 source tree.
