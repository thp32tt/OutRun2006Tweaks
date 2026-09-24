# Standalone Wheel FFB Branch

Branch: `ffb-arcade-dd-research`

## Base

This branch is intentionally based on the standalone Wheel FFB v0.1.1 lineage, whose upstream base is `emoose/OutRun2006Tweaks` master (`08e5efb4deea4066c440307ec009c868a30562d3`).

Standalone FFB baseline commit: `42699d0923cfd31682392fa21d47b3d107e22e0f`.

## Scope

Only wheel/input/DirectInput FFB changes, FFB diagnostics, FFB documentation, and FFB reverse-engineering references belong here.

The branch must not contain or depend on:

- `src/vr/**`
- `vrhost/**`
- OpenXR/D3D9Ex/DXVK/DX12 VR backends
- VR automation/review state
- VR test/packaging scripts
- 3Dmigoto VR shader reuse
- VR-specific settings or input actions

Scheduled VR A/N100/B/C/D work must not target this branch.

## Distribution

This branch is a standalone non-VR distribution line. Its normal Win32 build produces the original-mod-based `dinput8.dll` plus the Wheel FFB/input changes. VR binaries and VR host components are not part of its source graph or package.

Any future merge with the VR line must be explicit and selective; FFB development does not automatically merge into `vr-d3d9ex-focus`.

## Current research additions

- read-only Xbox C2C vibration witness telemetry for correlation only
- Lindbergh/FFBArcadePlugin event-semantics map
- PS2 OutRun 2 SP Logitech/liblgdev FFB map and compact query tooling

These reverse-engineering signals are evidence only. Physics SAT/mechanical trail/damper remains the modern DD-wheel steering backbone until hardware evidence supports a bounded change.
