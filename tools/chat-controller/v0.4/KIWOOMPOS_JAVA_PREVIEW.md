# KiwoomPOS Java preview in the OutRun Portainer VR stack

This preview is an **independent service**, not part of the OutRun VR game or controller.
Its purpose is to preview the public pages of `https://pos.kiwoompay.co.kr/`
without starting PHP. Do not enable it as a production customer-inquiry endpoint.

## Portainer Git deployment

- Git repository: `https://github.com/thp32tt/OutRun2006Tweaks.git`
- Git branch/reference: `refs/heads/chat-controller-downloads`
- Existing VR stack compose: `tools/chat-controller/v0.4/docker-compose.portainer-vr.yml`
- Added service: `kiwoompos-java-preview` (container `outrun-kiwoompos-preview`)
- After **Pull and redeploy**, open `http://192.168.0.48:18082/`.
- `/health` returns HTTP 200 when the Java preview process is ready.

The OutRun controller's existing `6080`/`8787` ports, volume names,
container settings, secrets, and working data were not changed.
The additional service has its own CPU/memory limits and mounts the website
files read-only. Rebuilding the OutRun image is not required by the
KiwoomPOS change itself; Portainer may nevertheless rebuild/recreate
services based on its deployment settings. Check preserved VR state after redeploy.

## Required host-side files

These paths are absolute host paths **on the N100 machine**:

- `/home/chatgpt-runner/apps/kiwoompos-java/app.jar` — Java 21 JAR
- `/home/chatgpt-runner/apps/kiwoompos-java/site/index.html`
- `/home/chatgpt-runner/apps/kiwoompos-java/site/page/*.html`
- `/home/chatgpt-runner/apps/kiwoompos-java/site/css/`, `site/js/`, `site/img/`

The files were generated on the N100 on 2026-10-22. Their directories are
world-traversable and the files world-readable for the read-only
non-root container (UID 10001); they do not contain server-side PHP source.
The `site/` snapshot is intentionally **not** uploaded to this public game
repository, to avoid republishing someone else's web assets.

If these host files are removed, the Git-based Portainer stack alone
cannot recreate them. Restore the N100 snapshot and JAR before redeploy.

## Preview limitations

- Pages are mirrors of public GET responses, not a source-code conversion of
  the original PHP application's server-side logic.
- Legacy `.php` public-page requests redirect to local `.html` pages.
- The customer-inquiry POST endpoint returns HTTP 503 intentionally:
  it does not transmit/store customer names or telephone numbers.
- No ASP/admin/PG/VAN integration is included.
- Port `18082` binds to the N100 LAN interface (192.168.0.48), not the public internet.
  Do not open an internet-facing NAT rule for this test port.
- Verify privacy requirements, copyright/brand authorization, functional QA,
  authentication and external integrations before any production migration.

## Test after deployment

```bash
curl -i http://192.168.0.48:18082/health
curl -I http://192.168.0.48:18082/
curl -I http://192.168.0.48:18082/page/pos.html
curl -I http://192.168.0.48:18082/page/cs_inquiry.html
```

Portainer **Containers** should display `outrun-kiwoompos-preview` as healthy.
The OutRun container must remain healthy independently.
