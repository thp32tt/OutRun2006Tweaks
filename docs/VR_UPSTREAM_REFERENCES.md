# VR Upstream References

Catalog date: 2026-09-21 Asia/Seoul

This is a curated GitHub-wide discovery catalog, not an exhaustive scan of every repository. References are evidence only; no code is imported without local applicability and license review.

## tomreason/nfsheatvr
- URL: https://github.com/tomreason/nfsheatvr
- Discovery date: 2026-09-21
- Relevant identity: 0e552782fc86cea04e255c2bc7e7c14f7874f7af (2026-09-06)
- License: MIT
- Technique: game-specific VR injection/reference-stack work; useful for HUD stereo transforms, runtime sizing and VR rendering integration comparisons.
- Local mapping: HUD/stereo classification, host/runtime sizing, optional performance experiments.
- Risk: different game/API architecture; transfer concepts only.
- Provenance confidence: high.

## letsgosportsteam/mirrors-edge-vr-mod
- URL: https://github.com/letsgosportsteam/mirrors-edge-vr-mod
- Discovery date: 2026-09-21
- License: MIT
- Technique: modern game-specific VR mod architecture and camera/render integration.
- Local mapping: camera/reference-space and overlay/world classification comparisons.
- Risk: engine/API mismatch.
- Provenance confidence: high for repository/license; technique requires per-file follow-up.

## farmerarmor/ThiefVR
- URL: https://github.com/farmerarmor/ThiefVR
- Discovery date: 2026-09-21
- License: LGPL-2.1
- Technique: game-specific VR injection/reference handling.
- Local mapping: camera/recenter and renderer interception architecture.
- Risk: LGPL provenance obligations plus engine mismatch; do not copy blindly.
- Provenance confidence: high for repository/license; technique requires per-file follow-up.

## NotLooky/BannerlordVR
- URL: https://github.com/NotLooky/BannerlordVR
- Discovery date: 2026-09-21
- License: MIT
- Technique: game-specific VR mod integration and rendering/camera adaptation.
- Local mapping: world/HUD classification and camera lifecycle comparisons.
- Risk: engine/API mismatch.
- Provenance confidence: high for repository/license; technique requires per-file follow-up.

## DR-89/fear-vr
- URL: https://github.com/DR-89/fear-vr
- Discovery date: 2026-09-21
- Relevant identity observed by code search: 85b3af161f7f33e4d71fa4881e99699fa7ce9ecb, docs/M2-D3D9-BRIDGE.md
- License: not yet verified; no code intake permitted until verified.
- Technique: D3D9 bridge explicitly hooks Direct3DCreate9[Ex], CreateDevice[Ex], Reset and Present, closely matching the OutRun reference API boundary.
- Local mapping: D3D9/D3D9Ex wrapper lifecycle, Reset/Present interception, stereo bridge architecture.
- Risk: license pending and independent implementation details.
- Provenance confidence: medium-high.

## jiink/TrackManiaForeverOpenXR
- URL: https://github.com/jiink/TrackManiaForeverOpenXR
- Discovery date: 2026-09-21
- Relevant identity observed by code search: 57e449c002d79e4174c0f3398dc4dd97c535f00f, src/d3d9_proxy.cpp
- License: not yet verified; no code intake permitted until verified.
- Technique: D3D9 proxy tracks stereo color targets and packed per-eye rendering.
- Local mapping: D3D9 proxy, stereo target classification, eye routing.
- Risk: packed-target design differs from OutRun shared-eye/host pipeline.
- Provenance confidence: medium-high.

## ValveSoftware/openvr
- URL: https://github.com/ValveSoftware/openvr
- Discovery date: 2026-09-21
- Relevant identity observed by code search: 0924064316de3effbcd1acf1e309182a2deb1c05, headers/openvr.h
- License: upstream repository license must be checked before any code reuse; treated here as API/telemetry reference only.
- Technique: frame timing telemetry distinguishes Present blocking and wait-for-present CPU time.
- Local mapping: cadence telemetry and producer/consumer wait diagnostics.
- Risk: OpenVR rather than OpenXR; concepts only.
- Provenance confidence: high for API reference.

## fholger/openvr_fsr
- URL: https://github.com/fholger/openvr_fsr
- Discovery date: 2026-09-21
- Relevant identity observed by code search: 6fcf691fc291def968d14b3c4bcf385f42bee94e
- License: not re-verified in this pass; no code intake permitted until verified.
- Technique: VR render scaling/upscaling integration reference.
- Local mapping: optional PERFORMANCE-only scaling experiments; never alter correctness defaults.
- Risk: OpenVR wrapper architecture differs from x64 D3D11 OpenXR host.
- Provenance confidence: medium.

## Discovery notes
Query families included OpenXR/OpenVR, D3D9/D3D9Ex CreateDevice/Reset/Present hooks, stereo targets, injection/proxy architecture, frame pacing/waits and VR render scaling. Additional daily passes should extend shared-texture/generation ACK, recenter/reference-space, HUD/world-space and x86-game/x64-host bridge families and update identities idempotently.
