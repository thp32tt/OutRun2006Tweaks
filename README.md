# Korean localization controller rollback (2026-10-12)

This minimal GitHub branch is a **GitOps deployment definition**, not a new build. It restores the existing Korean localization controller Docker image built yesterday.

* Source commit in original repository: [`68e8a437cadd`](https://github.com/thp32tt/OutRun2006Tweaks/commit/68e8a437cadd429e30db25e14f8978a88d977b29).
* Exact image tag found on the Portainer host: `outrun-kor-plate-engine:68e8a437cadd`.
* Only one service: `controller-a`; no separate QA container.
* Host port `6082` maps to container noVNC `6080`. Status host port: `8788`.
* Persistent legacy browser/data directory on the host: `/home/chatgpt-runner2/work/outrun-imagegen-a/legacy-data`.
* The new A-slot Python controller is **not** executed. The old image's embedded `/opt/outrun/entrypoint.sh` starts the old browser/controller.

## Portainer

Update **Git-managed stack** settings:
- Repository: `https://github.com/thp32tt/OutRun2006Tweaks.git`
- Reference: `refs/heads/deploy/rollback-localization-20261012-68e8`
- Compose path: `docker-compose.yml`
- Environment `VNC_PASSWORD`: use the password already configured in Portainer
- Environment `LOCALIZATION_PROJECT_URL`: the existing Korean localization ChatGPT Project URL (required for automatic sending)
- Optionally `AUTO_SEND=false` for a login-only first run.

Then press **Pull and redeploy**. Access `http://192.168.0.48:6082/vnc.html`.
Do not delete other stacks or volumes.
Use the same Docker host that contains the image. Because `pull_policy: never` is set, a missing image will fail explicitly instead of unexpectedly downloading/building a different version.

## Limits

This is an exact Docker image rollback to the Oct 12 image, **not a claim that its ImageGen upload logic works**.
Browser login may be needed again because the old controller uses `/data/browser-profile` while the new controller used `/profile`.
Runtime and Portainer deployment remain UNTESTED until manually redeployed.
