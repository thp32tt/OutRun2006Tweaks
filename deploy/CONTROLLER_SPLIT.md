# Controller deployment split

Deploy localization and VR as independent Compose projects.

Localization:
`docker compose -f deploy/localization/compose.yml down --remove-orphans`
`docker compose -f deploy/localization/compose.yml build --no-cache`
`docker compose -f deploy/localization/compose.yml up -d`

The VR controller must live in a separate Compose project, use a different state volume/network/container name, and must not mount localization controller state. This branch does not define VR workflow logic because `korean-localization-clean` is localization-only.

The Compose file is an isolation/deployment contract. The N100 controller implementation/Dockerfile is intentionally not fabricated in this repository when its runtime source is not present here.
