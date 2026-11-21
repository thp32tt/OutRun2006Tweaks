# Ferrari14 clean v0.03 test-copy deployment

**Do not execute installer against the existing working release.** Prepare a separately named `OutRun-Ferrari14-Test` directory from an *exact* v0.03 release directory first.

1. Ensure `OR2006C2C.EXE`, `OutRun2006Tweaks.ini`, `dinput8.dll` and `outrun-vr-host.exe` in the release folder match the official hashes. Customized INIs must be backed up separately; use a fresh v0.03 INI for strict parity.
2. From the extracted package, run `powershell -NoProfile -ExecutionPolicy Bypass -File .\PREPARE-FERRARI14-V003-TEST-COPY.ps1 -ReleaseRoot "C:\OutRun-Working" -TestRoot "C:\OutRun-Ferrari14-Test"` to verify. Re-run adding `-Create` to copy the full licensed game.
3. The preparation script records an isolated copy marker. The next installer **refuses** paths without that marker, source/target overlap, unknown EXE/INI, unknown runtime or unexpected optional 575 model.
4. Without `-Install`, `APPLY-FERRARI14-V003-CLEAN.ps1 -GameRoot "C:\OutRun-Ferrari14-Test"` only validates. Run adding `-Install` after both game and host exit.
5. Test the original release first before installing, then patched `RUN-FERRARI14-V003-MODEL-OFF.cmd vr`, then `RUN-FERRARI14-V003-575-ON.cmd vr`. The ON path explicitly accepts **experimental complete native player callback replacement** and fixed-function stereo; it is not a production release.
6. A private original/hybrid/diagnostic 575 file may be placed in `ExternalCars\car_id_05.ovc` only on the TEST copy; if absent, the patched DLL falls back to the original game car.
7. If model ON produces black panels, bad eye depth or low FPS, run short `RUN-FERRARI14-V003-575-TRACE.cmd vr`, save game and VR host logs and restore using `RESTORE-FERRARI14-V003-CLEAN.ps1`.

**Important unresolved:** original native callback contains queue/effect ownership not yet surgically extracted; generic external replacement is opt-in and may skip original native subdraws. PBR shader c0/c4/c8 is not stereo-certified; fixed-function diagnostic does not offer finished PBR normal maps. No headset run has accepted the camera, asset, FPS or stereo quality. The official release branch is never modified.

Official pinned hashes:
- EXE 68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3
- INI 630fc782a7b99666bc6f62ee0c791f160bddb6b1a879ef97f39f38763ac77358
- DLL 5d3c4fa550f3589323d1bddf65f475915f97b1bcdd3904ba50df865e002b7443
- Host 8c7e574214eb39a11db906e97465da77e69402bc7aeaeb835bc8e732ad3d661f
