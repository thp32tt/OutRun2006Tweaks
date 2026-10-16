# OutRun 2006 KR v2 — Docker automatic execution policy (2026-10-16)

Basis: user-approved Astra v2 planning review TASK_ID OUTRUN-KR-PLAN-REVIEW-20261016-094508; active OutRun asset policy dated 2026-10-16.

## Current actual status: PAUSED / no dispatch

This change applies only to GitHub source. It does NOT deploy Portainer, restart any live process, start Chrome, submit an image, compose DDS, or edit game files.

- Docker Compose sets AUTO_SEND=false; empty SCHEDULE_MINUTES, and restart=no for both OutRun services.
- Legacy tile, ROI producer, auto imagegen/compose/deploy flags all remain false.
- v2 batch sheet producer is NOT implemented. Therefore v2_automation_policy.py rejects AUTO_SEND=true on container startup even if a human sets a later phase or drops a purported PASS evidence JSON. It also rejects activation of any legacy, one-shot, or new one-phrase ROI queue. The guard runs in entrypoint.sh before Chrome/VNC/controller.
- The historical optional C-SALVAGE container is inert: retired profile, explicit entrypoint failure, no --loop, no automatic restart. C stays original N100 HD full PNG native English crop only.
- Existing browser named volumes, source mounts, service name, status port 8788 and VNC 6082 are kept unchanged; VR/FFB/DX11/DXVK are out of scope.
- Both old 986 tiles and their logs remain immutable historical evidence, NOT new production inputs.

## Phase progression is NOT permission to send images

F0: Verify one original Q051 native DDS decode/no-op/save/redecode/real-game baseline and source-derived CLEAN with masks and protected pixels intact.
F1: One correctly mapped Korean phrase from the five-label sheet; persisted DDS, full alpha/scale/CLEAN QA, actual in-game display and rollback.
F2: All five Q051 phrases pass exact semantic mapping, one DDS writer, all mips and all live in-game screens. No hard errors.
F3: Two further style families, 15 phrases total; first-pass efficiency target >=12/15 is NOT final release approval, and each released phrase must pass.
F4: Try 6–8 phrase sheets only when time and attempts per final in-game PASS phrase improve.
Parallel release requirement: real text ID UTF-16LE to Unicode glyph layout in game, later all 1,355 non-null IDs validated. It is NOT replaced by raster-generated words.

Manual phase advancement accepts only prior-stage evidence containing a concrete artifact path and SHA-256 verified against real file bytes. This is integrity checking, NOT human review verification. User/QA screenshots and code-level DDS checks still required.

The JSON policy also requires original HD full source only, exact phrase maps/alphas, natural source anchors, safe mask and protected pixels, single final DDS writer, mip/orientation and C1/C3 vs actual-game approval separation.

## Future production (out of current scope)

When a separately approved and tested v2 batch-sheet queue exists, attach 4–6 original English phrase crops grouped by type in ONE actual reference image, request transparent alpha Korean graphics, then save output intact, independently match every complete Korean phrase to image regions, and only then perform alpha-aware proportional downsizing into real UI safe masks. A source layout is not reliable output coordinates. Generate clean plates from original source/PSD, not painted boxes. Re-encode DDS preserving header/layout/mips; protected pixels outside allowed regions must not change, and in-game failure is never auto-closed.

This controller currently has only a historical one-phrase ROI queue, not an Astra v2 batch-sheet dispatcher. Do not turn it on or call it v2. Build a separate versioned production queue and QA consumer mapping before requesting another explicit restart/redeployment authorization.

## Offline verification and sample

From tools/chat-controller/localization-recovery-v1:
  python3 -m unittest discover -s tests -p 'test_v2_automation_policy.py' -v

At Docker startup (but not deployed by this change):
  python /opt/outrun/app/v2_automation_policy.py --policy /opt/outrun/v2_docker_policy.json --evidence-root /data/imagegen/korean_v2/stage_evidence

Expected with current environment: PAUSED_NO_SEND_NO_QUEUE.
AUTO_SEND=true fails with V2_BATCH_SHEET_DISPATCH_NOT_IMPLEMENTED_AUTOSEND_FORBIDDEN.

Do not mistake GitHub changes for actual Portainer deployment. Only the user may manually pull and redeploy after a separately specified approved live change.