# Ferrari13 cockpit-mode launch hotfix — 2026-11-19 KST

## User-reported failure and root cause

The private 600 MB Ferrari13 package bundled **the correct integrated V4 dinput8.dll and Quest V2 outrun-vr-host.exe**, but its entrypoint named `INSTALL_FERRARI13.cmd` intentionally **only installed files**, and its option `-Launch` was only available from `INSTALL_FERRARI13.ps1` when invoked explicitly. This was incorrectly presented as a ready-to-run test pack, which could leave users launching the ordinary game with cockpit disabled.

The supplied default `OutRun2006Tweaks.ini` also has `[VR] QuestCockpitV2Enabled=false` (safety default). If a user runs the original EXE without the cockpit-specific CLI overrides, cockpit mode can remain OFF. The prior known-good `Run-OutRunVRTest.ps1` source documents that release DllMain also requires `OUTRUN_VR_LAUNCH=1`, and adds `-VR.Enabled=true`, `-VR.AutoLaunchHost=true` plus the cockpit activation flags.

Two user-provided host and watchdog logs showed host v3 readiness, eventually direct sharing ready, stereo frame counter reaching **6518**, and `failure=0`, but **do not expose actual cockpit-view selection or native cockpit camera draw**. A 5-second direct GPU warning with later direct-ready is not proof of host failure. Do not claim the user has tested the patched launcher.

## Remediation delivered

- Added `tools/car_importer/ferrari16_hq_batch/tools/run_ferrari13_cockpit.ps1` and CMD entrypoint `run_ferrari13_cockpit.cmd`, plus `verify_ferrari13_cockpit.cmd` for a no-launch check.
- Safe prereqs: original `OR2006C2C.EXE` present, integrated `dinput8.dll` SHA-256 `313d9925b48fab98dbe2445201cfc54a1e2a05ab34fb940b6bc3761c94e97a4e` and Quest V2 `outrun-vr-host.exe` SHA-256 `e12a136cba5110216180b68ee2c20cadac1e0fe365bc0a58c4d42003360b5e40` match the previously delivered private pack; all thirteen OVC bodies and thirteen overlay files are present. Fail closed for missing/mismatched files or already running game/host.
- Launch flag entrypoint forces `-VR.Enabled=true -VR.Stereo=true -VR.AutoLaunchHost=true -VR.QuestCockpitV2Enabled=true -VR.F50ExternalModel=true -VR.ExternalFerrariTest=true` with full-car, native-seat, original Quest camera, no double-LOD, no per-frame telemetry; sets `OUTRUN_VR_LAUNCH=1` while calling Start-Process, then restores the parent environment. Overrides default OFF INI **without mutating user config**.
- Only intended cockpit rendering in in-game camera mode 1 and active gameplay. Menus and third-person camera won't show the cockpit geometry.
- Small hotfix archive `FERRARI13_COCKPIT_LAUNCH_HOTFIX_20261119.zip`, **3,844 bytes**, SHA-256 `98a2331fc17eddadcc65094b2dab0ef328c1721444d8de0108917c44bc82f4c9` — only three launcher scripts and README. Uploaded to private owner-only Drive, not third-party mesh data.
- Windows CI `Ferrari13 cockpit launcher activation smoke` **run 44353494412 SUCCESS**, commit `6f9a09c4b9d4609bb0902c20a1ed95916d97790d`: PowerShell 5.1 syntax, release activation flag and environment policy, CMD references, fake game EXE + missing DLL fail-closed (original EXE untouched and no dummy process). No full VR game test.

## User install

1. Keep existing Ferrari13 600 MB test package installed. **Do not re-download assets.**
2. Extract the tiny hotfix *into the game directory*, beside `OR2006C2C.EXE`.
3. Run `VERIFY_FERRARI13_COCKPIT.cmd` first. If hash checks fail, reinstall the matching Ferrari13 private pack from its original installer rather than mixing old DLL/host variants.
4. Run `RUN_FERRARI13_COCKPIT.cmd`; start a driving stage and select camera 1 (in-cabin).
5. If it still fails, obtain a fresh `OutRun2006Tweaks*.log` or VR settings screenshot from **this exact launched session**, rather than relying only on watchdog/host shadow transport logs.

**No game EXE, PMT, vehicle model, registry or INI was edited by this hotfix.** No Quest3 headset playtest has occurred. Any report of this same hotfix or another launch verification is +0 points (not a second achievement).
