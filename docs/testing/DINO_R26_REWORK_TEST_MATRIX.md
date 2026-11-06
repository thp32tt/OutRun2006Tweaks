# Dino R26 experiment gates

RUNTIME_VALIDATION=UNTESTED

| Gate | Pass criteria |
| --- | --- |
| GLB preservation | Existing validator passes. Texture-only audit allows image payload changes and verifies the remaining scene structure and buffer data. |
| OVC | Actual R26 parser accepts the candidate DDS, group, counts and CRC. Runtime package uses matching game and host build identity. |
| Native Draw ownership | Capture original-only and experiment runs at the same viewpoint. Identify and remove only the verified replaced Draw, retaining exterior and unrelated cockpit parts. |
| Cockpit fit | Observe one wheel and column, intended stalk count, clear dash-to-column junction and consistent position in both eyes. |
| Race teardown | Race, finish, return to menu and start another race. Inspect transition logs and any crash report. |
| Launcher and recovery | Verify CMD/PS1 paths and matching source SHA and payload hashes. Confirm model-off control and recovery. |
| VR performance | Compare Quest 3 frame timing under identical options and course. Target 8.33 ms frame budget at 120 Hz and at most +0.5 ms additional GPU time. |

`CallOriginalPlayerWithGlassScope` in `src/hooks_graphics.cpp` invokes the native player callback then the external FitV6 draw. The ticket snapshots player matrices before that callback and skips submission after a gameplay state change. That establishes ordering and guards, while the individual native Draw owner and crash cause still require runtime evidence.
