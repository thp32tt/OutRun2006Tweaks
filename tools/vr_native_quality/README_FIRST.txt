OutRun 2006 high-quality native D3D9Ex test - 2026-11-01

LOG-CONFIRMED ROOT CAUSE:
- Game folder d3d9.dll is a third-party D3D9 provider.
- D3D9Ex upgrade was skipped for compatibility.
- DirectGPU frames 0, Desktop Duplication SBS fallback all gameplay.
- Game eye resources were only 1920x1080.
- R9 mono shadow issued ~2.75 million extra Draw calls.
- Full-trace logs were large and may also increase overhead.

WHAT THIS PACKAGE CHANGES:
- Does NOT replace game EXE, DLL, x64 host or INI.
- Runs existing stable R26 game binaries with an explicit high-quality DX9Ex profile.
- When a local d3d9.dll exists, asks permission to move it to
  VR_NATIVE_D3D9_BACKUP ONLY for this one game session.
- Uses try/finally to automatically restore d3d9.dll after game exits, checked by SHA256.
- Requests true D3D9Ex + DirectGPU-only GAMEPLAY + XR recommended full eye resolution.
- Prevents silent SBS gameplay downgrade. Menu fallback remains enabled.
- Disables VR telemetry for the comparative performance run.
- Reports whether D3D9Ex probe and DirectGPU frame counters actually succeeded.
- Never delete the VR_NATIVE_D3D9_BACKUP folder before confirming normal restore.

INSTRUCTIONS:
1. Extract RUN_NATIVE_VR_QUALITY.cmd and Run-VRNativeD3D9Ex.ps1 into the actual
   OutRun folder containing OR2006C2C.EXE and the previously installed VR binaries.
2. Close game and VR host. Start your Quest + VDXR/OpenXR runtime.
3. Double-click RUN_NATIVE_VR_QUALITY.cmd.
4. If local d3d9.dll is found, type YES to isolate it temporarily.
5. Play a comparable stage and exit normally. Read the console transport result.
6. Upload VR_NATIVE_QUALITY_LOGS/NATIVE_D3D9EX_*/ folder if DirectGPU fails.

If DirectGPU is not supported for any other reason, gameplay can be blank
rather than low-resolution SBS. This is intentional fail-closed behavior,
and this experimental test is NOT a guaranteed visual fix.
Exit the game normally and the local third-party d3d9.dll is restored.

Do not run the VR host executable directly. Do not combine with another
VR game launcher. The initial safe R26 binary remains unchanged.

When PowerShell is forcibly terminated or Windows loses power, the finally
block cannot execute. In that case stop all game/host processes, then
manually move the d3d9.dll from VR_NATIVE_D3D9_BACKUP back into the game
folder only if no d3d9.dll exists there. Do not discard the backup.
