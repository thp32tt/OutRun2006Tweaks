# DX9Ex test launcher shipping standard — 2026-10-15

User-confirmed failure in the f91edcf3 test: gamePid=3728, hostPid=0, hostReason=host-pid-missing, stereoAllowed=0. A functioning game EXE or host v3 shadow does not demonstrate a functioning OpenXR/Quest3 session; actual root cause of the host failure is not established.

## One-click execution

1. Back up old files; extract the *entire* DX9Ex Active test ZIP directly into the original directory containing `OR2006C2C.EXE`, not into a nested new directory.
2. Connect Quest 3 through Virtual Desktop and prepare the selected VDXR OpenXR runtime.
3. Double-click **START_DX9EX_TEST.cmd**, not the host exe. The batch checks backend payload, PowerShell/INI/game EXE and launches D3D9Ex CURRENT_FOCUS/CORRECTNESS with visible error output. The GUI selector is optional.
4. Close the game normally. If the OpenXR host never appears or disappears, inspect **OUTRUNVR_LAUNCH_ERROR.txt** and session **DX9EX_LAUNCH_HEALTH.txt** and upload the generated `OutRun2_VR_ANALYZE_*.zip`.

## Release acceptance

The ZIP MUST include direct visible `START_DX9EX_TEST.cmd`, optional GUI `OutRunVR-Slot-Selector.cmd`, all relevant PS1 helper scripts, original-mod INI and backends/d3d9/{dinput8.dll,outrun-vr-host.exe,SOURCE_SHA.txt}. Mandatory scripts must handle paths with spaces, `%~dp0` and correct working directory, nonzero error code propagation, diagnostic log preservation, and pause on failure. Ensure original EXE/hash identity, forbid injected DXVK `d3d9.dll`, and require Windows CI static and package verifiers. Do not call a ZIP usable merely because x86/x64 compilation succeeded. Quest3/VDXR runtime and stereoscopy remain **UNTESTED** until direct HMD evidence.
