# DX9Ex HMD reference: user acceptance checkpoint 2026-10-20 (KST)

**Immutable game/host binary baseline**: PC Fast package matrix `PC-FAST-20261020-012805-0cff83cf509c`, artifact source/identity SHA `0cff83cf509c2acd6f3391b3a46c4dec1403a0d9`. Backed by user HMD screenshots (vehicle selector, gameplay, selector) and session analyze ZIP `OutRun2_VR_ANALYZE_PC-FAST-20261020-012805-0cff83cf509c_CURRENT_FOCUS_CORRECTNESS_20261019T164455579Z-3df63e8e.zip`. **Do not confuse this compiled binary baseline with later GitHub script/document HEAD or the DX9Ex R84 hosted-release configuration.** Latest scripts may differ while retaining the verified compiled game/host bytes.

## User-confirmed improved / do not regress
- Game boots on Quest3 VDXR after PC Fast launcher repair.
- Main menu and ESC selection *functionally* stable; menu remains vertically squashed visually.
- Sky/background no longer doubled/headlocked as before.
- +TIME, goal-progress % and goal-time now visible in **both** eyes; spatially head-locked remains unresolved.
- Car textures/sky/track draw as shown in three screenshots; 3D gameplay visually substantially more stable.

## Unresolved, release-blocking
1. Main/vehicle selector portrait 2496x2688 source-to-ultrawide mirror and HMD menu *aspect* must be measured; do not regress readable selection or crop car.
2. F11 shell is small/up-right in HMD; preserve external ImGui source ownership, repair binocular placement/size independently.
3. VR PMT culling still clips stage objects at headset margins; diagnostic source shows `scopedWide` active with margin 4.0; do not revert culling to mono or disable globally.
4. Vehicle 1st–5th rank follows wrong 2D plane; `HUD_RANK_PROJECTED_PATH_ZERO` and `projectedMarkerSemanticCount=0`. Exact Calc3D2D anchor unobserved; do not invent a depth from a screen-coordinate alone. Preserve original rival hooks / world effects.
5. +TIME/GOAL/progress/time are bilateral but remain head-locked; require real 2D optical-plane placement or world-owned depth per producer.
6. Central lens flare duplicated/headlocked; exact C993 `objectId=0x570002` may be hidden **only in VR** while preserving C A B E outer rings, unrelated sun/sky and desktop.
7. Logs collector `gameDllSha256` optional key under PowerShell StrictMode failed; cannot assume a missing key implies invalid installation.

## Observed diagnostic details
- XR eyes: 2496x2688; VR UNIFIED SOURCE selected 2496x2688; mirror window 3440x1440.
- VR PMT CULL `scopedWide` >16 million and `failOpen` >1 million (cumulative); indicates path executing, **not** FOV coverage proof.
- `WORLD_RIVAL_MARKER` observed through original `sub_4BAD20` while `HUD_RANK` labeled SCREEN_HUD; full 3D anchor mapping still missing.
- Auto summary `directFrames=25992`, `directFallbacks=2`, `projectedMarkerSemanticCount=0`.
- CI/compile only establishes static and build contracts; **HMD acceptance remains user-reported for the exact binary snapshot**, never inferred for future commits.

## Change policy
Preserve this exact compiled baseline for A/B comparison. Apply fixes by isolated source owners, required Windows builds and final per-eye HMD regression checks. Never treat unverified fixes as acceptance, and do not alter DX11/DXVK lanes.
