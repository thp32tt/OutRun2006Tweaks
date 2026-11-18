# FERRARI13 Quest3 white-screen 2026-11-19 — real uploaded game log + matched host/classic recovery

## Observed, NOT assumed

Attached user diagnostic ZIP `FERRARI13_LOGS_20261118T172831013Z.zip` contains seven entries, including actual `OutRun2006Tweaks.log` (77,096 bytes), pipeline log, host v3 and watchdog:

- Game process PID **3896**, original EXE **3,674,112 bytes**.
- **dinput8.dll actually loaded** at `I:\game\OutRun_vr_1\DINPUT8.dll`; SHA256 `313d9925b48fab98dbe2445201cfc54a1e2a05ab34fb940b6bc3761c94e97a4e`.
- User session launches with `VR.Enabled=true VR.Stereo=true VR.QuestCockpitV2Enabled=true VR.ExternalFerrariTest=true` confirmed by game log. Previous launcher/setting-gate concern is resolved and cannot explain THIS attempt.
- DX9Ex CreateDeviceEx was promoted; physical backbuffer **2248×2432** vs logical game/menu **1920×1080**, scale x1.17/y2.25; game renderer hooks installed.
- Engine Present executed repeatedly, e.g. `VR COCKPIT V2 CORRELATION present=1024 worldCam=9 effectCam=9 playerCar=0 nativePlayerCar=0`. This is **menu state**, not driving or camera mode1. Actual car-body sidecar drawing is not reached.
- `VR v3 shadow summary ... framePub=0 ... direct=0 directReady=0` for the entire attempt. Host pipeline: `gameFrameId=0`, no accepted stereo candidates, but menu `menu-local-fixed-quad-fresh` repeatedly submitted; OpenXR 90Hz host active. Watchdog stereoFrame=0 after 12s. Thus the complaint is at **menu game pixels/desktop capture/VR compositor handoff**, not yet proof of external cockpit model geometry defect.
- Old x64 host `outrun-vr-host.exe` SHA256 `e12a136cba5110216180b68ee2c20cadac1e0fe365bc0a58c4d42003360b5e40` identifies host build **2f69840b**, while actual game DLL was built from integrated V4 source **d140f6c0**. This is a version mismatch (not yet causal proof).
- The log's other hook validation failures are not demonstrated to be causally relevant to white video. `failure=0` on shadow does not imply a visible image.

## Changes, test candidates only

1. Built **new x64 OpenXR host** from current integration branch source at GitHub commit `f8f437e68429a3809605c73dca4b711188f5cb8b`. GitHub Actions `44360965222` SUCCESS; produced valid AMD64 PE, SHA256 **`9ecc80a902985506a66b93446f38d724190d622eba09a0f2683891714579460c`**, exact 1,046,528 bytes. Actual GitHub artifact **14455020556** was securely fetched and independently SHA-verified prior to package assembly.
2. Alternative **conservative D3D9 compatibility startup** using `-VR.PreferD3D9Ex=false -VR.DirectGpuOnly=false -VR.AutoRenderResolution=false -VR.FollowGameResolution=true -VR.FrameCadenceMode=0 -VR.DisableDesktopDuplication=false`, leaving QuestCockpitV2 + Ferrari13 body loader enabled and preserving driver camera. This avoids physical OpenXR portrait render target while in original 1080p menu, retaining supported SBS/Desktop Duplication fallback. Underlying white-screen cause **not proven**, so treat as A/B recovery.
3. Diagnostic `OUTRUN_VR_FILE_LOG=1`, `OUTRUN_VR_R23_PIXEL_PROBE=1` and existing bounded cockpit probe true, **per-draw telemetry false**; collect user log archive if still white. User `OutRun2006Tweaks.ini` and EXE remain untouched.
4. Optional `CHECK-FERRARI13-2D.cmd` can isolate a white screen occurring when VR is turned **off**, distinguishing original game rendering/EXE from VR host capture failure.
5. Both Win host build **44360965222 SUCCESS**, Win recovery launcher PowerShell smoke **44361193786 SUCCESS**, Win synthetic 1MiB host apply/backup/idempotency smoke **44363115775 SUCCESS**. **No Quest3 hardware frame visual test** done.

## Private deliverables and choices

- **Full, game-folder direct-extract ZIP:** `FERRARI13_VR_RECOVERY_MATCHED_HOST_20261119.zip`, **599,715,065 bytes** SHA256 **`1d3c7cb394392615a461bc315fcd8aeac274ad581bcb32cd29ea1be6260d8d3e`**, 48/48 ZIP entries CRC PASS, 13 body + 13 dashboard OVC bytes unchanged, integrated DLL SHA unchanged, new host SHA updated in `FERRARI13_PAYLOAD/manifest.json` (30 SHA-gated files), new one-click VR launcher and optional 2D A/B included. Private Google Drive file ID `1jujXr2sW1F019_C81OZBwXBQgn_qC8xY`.
- **Small, recommended patch if user already installed 600MB Ferrari13:** `FERRARI13_VR_RECOVERY_SMALL_HOTFIX_20261119.zip`, **461,345 bytes**, SHA256 **`ee1591fe4646a98eddbbc62a3858acb0ab97832a2e61d0303f26295ffd355d92`**, 9/9 ZIP CRC PASS, NO third-party models. Private Google Drive ID `1r4l86UxB-YKpMfgzCtWxrYAsYZ4GSGZK`.
- Small patch extracted in game root overwrites **payload copy of host + manifest + root game launcher**, adds `APPLY-AND-START-FERRARI13-RECOVERY.cmd`; first application verifies existing old host SHA, expected new host SHA and integrated DLL SHA; backs up old installed host and copies new host; second application idempotent. Notably 13 car models do **not** get recopied or rebacked-up. `START-FERRARI13-VR.cmd` from original installed full ZIP is reused. If existing host unexpected SHA or assets missing, reject and use full ZIP instead.
- All private model files remain owner-only on Drive; third-party asset redistribution not authorized.
- No claim that white screen is fixed until actual Quest3 HMD test.

## Score policy

This is a follow-up of the same previously-scored Ferrari13 launch-gate stability task, **+0**. Previously confirmed AI2 score **2867**, unchanged; no additional point for re-tests or re-reporting.
