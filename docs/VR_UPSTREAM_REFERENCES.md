# VR Upstream References

Catalog updated: 2026-10-05 Asia/Seoul

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


## 2026-10-05 recent flat-to-VR implementation review

This pass intentionally records transferable design evidence only. No upstream source is imported by this entry.

### dariulone/cyberpunk-vr-port
- URL: https://github.com/dariulone/cyberpunk-vr-port
- Discovery/review date: 2026-10-05
- Relevant releases: v0.1.6 (2026-09-01), v0.1.7 (2026-09-29).
- Technique retained:
  - the second eye owns a real engine view instead of receiving copied/reprojected bytes;
  - both eyes are tied to one frame/base/head-sample/pose identity;
  - shared temporal/effect state must not be regenerated independently when the engine expects one authoritative producer;
  - HUD/world-marker families are treated separately instead of forcing one global stereo policy;
  - stale or mismatched view/frame state is rejected/fixed at the ownership boundary rather than hidden by later reprojection.
- Local mapping:
  - use as a root-cause model for OutRun lens-flare/SkyGlow/shadow-like state: distinguish frame-level producer state from per-eye projection/draw;
  - preserve R33 as the final physical stereo owner; do not move unrelated effect production into R33;
  - extend diagnostics around frame/pose/generation identity before changing rendering authority.
- Explicit non-transfer:
  - native frame generation, optical-flow paths and single-pass research are not candidates for the current OutRun correctness baseline.
- Risk:
  - REDengine/D3D12 architecture is substantially different; concepts only.
  - no source-code reuse is authorized by this ledger entry.
- Provenance confidence: high for release behavior and first-party release notes.

### kwstasg/Unreal-Revived
- URL: https://github.com/kwstasg/Unreal-Revived
- Discovery/review date: 2026-10-05
- Relevant current activity: 0.9.0 publication line, September 2026 OpenXR VR work.
- Technique retained:
  - independently culled per-eye world cameras use runtime IPD and asymmetric OpenXR FOV;
  - existing 2D HUD/menu content is presented as a stable shared spatial panel instead of being blindly duplicated as world stereo;
  - flat and VR paths remain separable, making VR composition an explicit opt-in presentation concern.
- Local mapping:
  - strong reference for a future OutRun screen-HUD-to-texture/OpenXR composition-layer experiment;
  - WORLD_RIVAL_MARKER/WORLD_HEART and other world-attached semantics must remain true stereo and must not be absorbed into a shared HUD layer;
  - implementation should live at compositor/layer ownership, not in R33 draw ownership.
- Gate:
  - do not promote this from reference to production work until the current DX9Ex correctness/HMD baseline is accepted or the active HUD runtime evidence specifically justifies it.
- Risk:
  - UE1/D3D12 renderer differs from OutRun D3D9Ex; architectural pattern only.
  - no source-code reuse is authorized by this ledger entry.
- Provenance confidence: high for repository activity and documented behavior.

### praydog/UEVR / UEVR-nightly
- URLs:
  - https://github.com/praydog/UEVR
  - https://github.com/praydog/UEVR-nightly
- Discovery/review date: 2026-10-05
- Relevant current artifact: UEVR Nightly 01143 published 2026-08-30.
- Technique retained:
  - runtime/backend/overlay/submission responsibilities remain separable;
  - eye/FOV/frame identity must be explicit and robust to unusual engine frame-number behavior;
  - UI handling is a separate VR concern from world stereo generation.
- Local mapping:
  - reinforces the existing OutRun architecture split rather than replacing it;
  - prefer a deterministic stereo-pair identity check at final submission over adding more heuristic eye classification.
- Risk: Unreal-specific internals; concepts only.
- Provenance confidence: high for project architecture/release provenance.

### doitsujin/dxvk v3.1
- URL: https://github.com/doitsujin/dxvk/releases/tag/v3.1
- Published: 2026-08-28
- Technique/evidence retained:
  - DXGI incremental-present support can forward dirty rectangles through `VK_KHR_incremental_present` when supported;
  - compatibility with external DXGI overlay hooks was improved;
  - D3D9 compatibility fixes remain active in current releases.
- Local mapping:
  - use only for controlled DXVK backend benchmarking/compatibility comparisons;
  - current OutRun DXVK lane remains downstream and must not replace the DX9Ex reference without measured Quest3/VDXR parity.
- Provenance confidence: high; first-party release notes.

### Development decisions retained from this review

1. **HUD composition-layer candidate:** keep screen HUD/menu as common-binocular content and consider one host/compositor-owned OpenXR UI layer; never flatten world markers into it.
2. **Effect producer ownership candidate:** for flare/SkyGlow/shadow-like defects, trace producer state -> accumulated frame state -> per-eye projection -> draw. Prefer one authoritative frame-state producer where evidence proves the original effect is frame-global.
3. **Stereo-pair freshness candidate:** strengthen final-submit diagnostics around `{frameId, poseSequence, transportGeneration}`; reject mismatched/stale pairs fail-closed.
4. **Backend measurement, not promotion:** compare DX9Ex/DX11/DXVK using the same scene and timing fields before changing backend priority.
5. **Deferred ideas:** frame generation, optical-flow synthesis, single-pass stereo and aggressive FOV/FFR work stay out of the correctness path until baseline stereo/HUD/frame pacing is runtime-verified.
