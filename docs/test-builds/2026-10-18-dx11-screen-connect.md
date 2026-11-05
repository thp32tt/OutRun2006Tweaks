# DX11 screen connection HMD test / 2026-10-18

Branch: `vr-dx11-native-r71`.
Purpose: exercise **actual game screen → x64 D3D11 OpenXR host → Quest 3/VDXR display**, not claim a completed native DX11 game renderer.

## What this test actually does

- Keep the original game-owned x86 D3D9/D3D9Ex draws and inputs intact.
- Prefer established shared DirectGPU OpenXR transport where admitted by live GPU/ACK validation.
- In the isolated `-ScreenConnectionTest` launch, set `DirectGpuOnly=false` and keep `DisableDesktopDuplication=false`, permitting live SBS/Desktop Duplication fallback if shared DirectGPU is unavailable.
- Observe the actual host transport selection in logs and enable the passive DX11 draw/state census.
- Do not activate dormant native D3D11 game draw or certify its native stereo conversion. No simulated/HMD proof is substituted for a real Quest test.

## Install and run

1. Shut down OutRun and the existing OpenXR host.
2. Back up the existing game folder and extract the built ZIP contents **into the installed OutRun 2006 Coast 2 Coast game directory**, the folder that contains your legitimate `OR2006C2C.EXE`. The executable/game assets are not bundled.
3. Select Virtual Desktop's VDXR OpenXR runtime and connect Quest 3.
4. Run only `START_HERE_VR_TEST.cmd` from the game directory. The preflight validates x86 game DLL, x64 host, and exact build SHA.
5. Check menu, race, per-eye image, HUD, shadow, recenter, and the transport used; exit normally.
6. Submit `OutRun2_VR_ANALYZE_*.zip` from the game directory. Logs must show whether DirectGPU or Desktop Duplication was active.

## Interpretation

A visible VR image proves a real game-screen-to-D3D11-OpenXR-host connection **only**. It does not prove that game draw calls were converted to native D3D11 or that native left/right GPU game frames were published. Source-level DX11 stereo is still dormant until its complete renderer activation and real Quest HMD tests pass. RUNTIME_VALIDATION=UNTESTED before a human run.

Normal developer `Invoke-OutRunVROneClick.ps1` invocations without the switch retain strict DX11 `DirectGpuOnly=true` behavior. Do not treat fallback-success as native-DX11-success.
