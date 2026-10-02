# Portainer deployment: exact pre-E localization controller

Deploy from:

- Repository: `thp32tt/OutRun2006Tweaks`
- Branch: `recovery/localization-no-e`
- Compose path: `tools/chat-controller/v0.4/docker-compose.portainer-localization.yml`

Required Portainer environment values:

- `LOCALIZATION_PROJECT_URL`: the ChatGPT localization project URL used by this controller.
- `AUTO_SEND=true`: enables automatic task sending. The historical compose defaults to false, so set this explicitly for production.
- `VNC_PASSWORD`: set a non-default password.
- `GITHUB_TOKEN`: optional when public REST access is sufficient; set it when authenticated REST quota is desired.

After deploy, verify:

- noVNC: host port `6081`
- controller status: host port `8788`
- status page reports `Controller mode: localization`
- registry contains three chat slots A/B/C
- no `LOCALIZATION_E` task is created

The controller runtime and A/B/C input prompts are byte-equivalent to the pre-E controller baseline commit `42e3410d9582b85d74a51435188905c5bbd27feb`. The localization governance files on `korean-localization-clean` are restored forward to their pre-E baseline content without resetting historical DDS/QA/output commits.
