# Ferrari13 white-screen incident and game-root folder-ready diagnostic release — 2026-11-19 KST

## Fresh uploaded evidence, distinguished from the earlier successful sequence

User-provided `outrun-vr-watchdog(9).log` and `outrun-vr-host-v3(9).log` on 2026-11-19 KST show a later set of failing sessions:

- 2026-11-18 **17:00:53–17:01:39 UTC**: client PID 22328, watchdog heartbeat increasing, host pose eventually active; `stereoFrame=0` all along.
- 2026-11-18 **17:01:51–17:02:31 UTC**: client PID 18152, watchdog `game_client_missing` at 17:02:02, `stereo_frame_missing` at 17:02:03, `stereoFrame=0` and `direct=0` until stop.
- Host v3 shadow reports `directSupported=1` but `directReady=0`, `frameOk=0`, `ackPub=0`; log says Desktop Duplication fallback remains active. `failure=0` in the shadow channel **does not** prove successful game rendering.
- The earlier **16:47–16:49 UTC** session achieved 6518 stereo frames and is **NOT** evidence that these two later white-screen sessions were working.
- The log evidence cannot isolate DLL injection failure, frozen game rendering, invalid eye shared-surface, incorrect camera state or wrong game instance. Do **not** claim white screen has been fixed without fresh physical test.

## Remediation: one ZIP, game-root extraction, one-click start

- New private **`FERRARI13_VR_FOLDER_READY_DIAG_20261119.zip`**: **600,302,973 bytes**, SHA256 `3d5e0767da15803ade347724f12a7a07a01baab5d6e2d2786ee14d3b64acc04a`. Private owner-only Drive ID `10ri2w9mJcgCNsyX5YXfwn0p_DkOTQBEI`, not public redistribution.
- 45 ZIP entries; 39 original Ferrari13 source-pack files remapped verbatim under `FERRARI13_PAYLOAD/` (same hashes/content) plus six new root scripts and readme; all 45 CRC PASS. Exactly 30 installed assets governed by preserved manifest, including 13 exact-body OVCs, 13 dashboard OVCs, integrated V4 `dinput8.dll` SHA256 `313d9925b48fab98dbe2445201cfc54a1e2a05ab34fb940b6bc3761c94e97a4e` and VR host SHA256 `e12a136cba5110216180b68ee2c20cadac1e0fe365bc0a58c4d42003360b5e40`, two optional default configs.
- ZIP top-level `START-FERRARI13-VR.cmd`, `VERIFY-FERRARI13-VR.cmd`, `COLLECT-FERRARI13-LOGS.cmd`, `FERRARI13_RUN.ps1`, `FERRARI13_COLLECT.ps1`, `README_FIRST_KO.txt`. **Extract directly into the legally owned game folder containing `OR2006C2C.EXE`.** No need to download previous 600 MB ZIP or small launcher hotfix separately.
- Start script verifies source ZIP manifest, then compares currently installed hashes to manifest. On first start or if files differ, invokes SHA256-gated previous installer to **back up and install** the matching assets. On subsequent matching launches it avoids reinstallation and unnecessary backup copies. Original retail EXE/PMT and existing user INI remain untouched.
- One-click launch uses `OUTRUN_VR_LAUNCH=1` release gate, `OUTRUN_VR_FILE_LOG=1` logger, `-FileLogging=true -VR.Enabled=true -VR.Stereo=true -VR.AutoLaunchHost=true -VR.QuestCockpitV2Enabled=true -VR.F50ExternalModel=true -VR.ExternalFerrariTest=true` and native-seat camera flags.
- Diagnostic conservative transport: `-VR.DirectGpuOnly=false`, `-VR.PreferD3D9Ex=true`, `-VR.DisableDesktopDuplication=false` so a missing DirectGPU share doesn't force a direct-only path. Bounded `-VR.CockpitFrameProbe=true`, `-VR.Telemetry=false` to avoid the prior huge per-draw telemetry. This is an **A/B fallback candidate, not a proven white-screen fix**.
- `COLLECT-FERRARI13-LOGS.cmd` works while game is hung; packages up to last 4 MiB per matching log, 24 MiB aggregate, along with PID, hashes, missing files and a launch trace into `FERRARI13_DIAG/FERRARI13_LOGS_<utc>.zip`. Existing dumps are noted, not silently collected because they can be large.
- Windows PowerShell 5.1 syntax, CLI requirements, actual synthetic log file copy and ZIP creation, and fail-closed without payload **GitHub Actions run 44356282895 SUCCESS**, commit `595a29ec85b376871af815d2a1148fcb50d354bb`. This is *not* a real GPU or Quest3 end-to-end test.

## Current verification boundary and feedback requested

User launches `START-FERRARI13-VR.cmd` after extraction. If still white, immediately runs `COLLECT-FERRARI13-LOGS.cmd` in another window, shares the resulting `FERRARI13_LOGS_*.zip`, and can end hung game with Task Manager. This must include game-level `OutRun2006Tweaks.log`; host-only/watchdog-only captures can't identify why the scene is white. If game-level file is absent even with inherited file logging enabled, investigate DLL not loaded, release gate and original EXE identity.

This is the third phase of the **same** Ferrari13 cockpit launch correctness task (installer-only → launcher hotfix → one-click diagnosable bundle), **not an extra independent completed VR gameplay achievement**. Score unchanged pending actual physical validation.
