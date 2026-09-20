# OutRun 2006 VR Unified Backend Test Scenario

Branch: `vr-unified-backends`

This package is a test integration harness for three renderer paths. It intentionally switches complete backend payloads before game launch instead of stacking mutually exclusive D3D9 hooks in one process.

## Backend activation

From the game directory:

```bat
Select-OutRunVRBackend.cmd d3d9
Select-OutRunVRBackend.cmd dxvk
Select-OutRunVRBackend.cmd dx12
```

Always exit the game and `outrun-vr-host.exe` before switching.

Selecting a mode now creates a unique session identity and a config snapshot **before game launch**. After each test, run `Collect-OutRunVRLogs.cmd`; only logs modified during that session are collected. Run `Collect-OutRunVRLogs.cmd -All` once at the end to create the matrix ZIP.

## Recommended short evening test order

Use 2D ORIGINAL only as a quick no-VR overhead smoke check. Then compare D3D9 control first, followed by DXVK SAFE. Test DXVK MULTIVIEW or DX12 STRICT only if the earlier modes start cleanly. A full A-F sequence is not required; this package contains no fabricated B/C/D variants.

### A. D3D9 safe baseline
1. Run `Select-OutRunVRBackend.cmd d3d9`.
2. Confirm no local `d3d9.dll` remains.
3. Start Virtual Desktop / VDXR first, then OutRun.
4. Menu: recenter once, rotate and translate head, enter car selection.
5. Gameplay: run a short Mission and then OutRun mode.
6. Check: world stereo, HUD alignment, white rank/score text, sky/cloud head-lock behavior, smoke/skid placement, opponent rank labels, 6th/6 position, Yes/No dialog.
7. Record HMD refresh rate and FPS.
8. Save `OutRun2006Tweaks.log`, `outrun-vr-host-v3*.log`, `outrun-vr-host-pipeline*.log`, and watchdog log.

### E1. DXVK safe
1. Exit all OutRun/host processes.
2. Run `Select-OutRunVRBackend.cmd dxvk-safe`.
3. Confirm root contains `d3d9.dll` but not `multiviewpatcher.dll`.
4. Repeat the exact A scenario and collect the session ZIP.

### E2. DXVK multiview
1. Exit all OutRun/host processes.
2. Run `Select-OutRunVRBackend.cmd dxvk`.
3. Confirm root contains `d3d9.dll` and `multiviewpatcher.dll`.
4. Repeat the exact A scenario.
5. Confirm log contains `VR DXVK PROBE:`, `VR DXVK MULTIVIEW:`, and when eligible `TRUE MULTIVIEW world rendering active`.
6. Compare HMD smoothness and frame time against A. Do not judge only by monitor output.

### F. DX12 strict D3D9On12
1. Exit all OutRun/host processes.
2. Run `Select-OutRunVRBackend.cmd dx12`.
3. Confirm root `d3d9.dll` is absent.
4. Start VDXR then OutRun.
5. If startup fails, stop there and keep the log; strict mode intentionally does not silently fall back to D3D9/DXVK.
6. If it starts, repeat A and verify DX12 log markers including D3D9On12 / D3D12 host initialization.

## Pass/fail sheet

Record for each backend:
- game reaches menu
- menu recenter works
- car-selection model intact
- gameplay reaches first stage
- left/right world geometry agrees
- HUD not split
- white score/rank/Yes-No not split
- sky/cloud stays world-fixed
- smoke/skid placement correct
- opponent rank labels follow cars
- 6th/6 moves to intended VR HUD placement
- no black/loading-screen recenter regression
- headset FPS / refresh
- subjective stutter: none / mild / severe
- monitor mirror mode
- final log filenames

Do not switch backends while either the game or host is running.
