# OutRun 2006 C slot assignment — 2026-10-17 (KST)

**Current C = existing N100 independent Docker container `outrun-c-original-english-crop`.** It is **not** a third ChatGPT browser tab and is **not** the retired `outrun-c-salvage-offline` image-recomposition job.

- GitHub canonical C Compose: [`docker/c-original-english-crop/compose.yaml`](https://github.com/thp32tt/OutRun2006Tweaks/blob/korean-localization-recovery-20260928/docker/c-original-english-crop/compose.yaml) (asset branch `korean-localization-recovery-20260928`).
- C role SSOT: `localization/controller_roles.json` on the same asset branch; its `lanes.C` maps to this container.
- Docker Compose project `outrun-c-original-english-crop`, service `c-english-original-crop`, container `outrun-c-original-english-crop`.
- N100 host local Compose path: `/home/chatgpt-runner2/work/c_salvage_text_roi/c_original_hd_crop_only/docker/compose.yaml`. Docker's actual `com.docker.compose.project.config_files` label matched this path on 2026-10-17 01:00 KST. The container was already running; **do not start a duplicate**.
- C scope: verified complete English source HD native-pixel crop **only**, 60-second poll, at most 10 verified queue specs per cycle. Source RO; 255 archived native crops remain immutable. No alpha removal, upscaling, ImageGen, Korean, CLEAN, DDS writer or in-game application.
- Current queue has exactly one already-produced item (Q060 Target); recent live result `completed=0, skipped_existing=1, queued=1`. **No automated text detection or ROI discovery exists**. More original-source verification and manually reviewed new queue specs are needed before throughput begins.
- Existing Portainer stack `outrun-kor` is separate. Its browser controller stays **PAUSED** (`AUTO_SEND=false`, `SCHEDULE_MINUTES=""`), C browser dispatch is not authorized; the source Compose now specifies `CHAT_SLOTS=2` for any **future manual** redeployment only. Current running Portainer container will not change merely because GitHub changed.
- C runs as the **standalone offline Docker slot**. Do not migrate it into Portainer or restart the A/B browser controller automatically. Existing C-SALVAGE historical profile remains disabled.
- Re-check: `docker ps --filter name=outrun-c-original-english-crop`; `docker logs --tail 30 outrun-c-original-english-crop`; `docker inspect ...` for Compose labels.
- No game test has run: `RUNTIME_VALIDATION=UNTESTED`; new outputs stay `CROP_TEST_ONLY_REVIEW_REQUIRED`.
