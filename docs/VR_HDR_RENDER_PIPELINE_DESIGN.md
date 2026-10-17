# VR HDR / Floating-Point Render Pipeline Design

Status: DESIGN CONTRACT — implementation guidance, not runtime acceptance  
Scope: DXVK and native DX11 conversion lanes  
Primary runtime target: Quest 3 / VDXR SDR presentation  
Reference: https://github.com/emoose/OutRun2006Tweaks/discussions/244

## Purpose

Preserve OutRun 2006's recovered Xbox-era high-dynamic-range **lighting/exposure semantics** through the VR renderer without confusing them with modern HDR-display output.

The upstream game logic uses framebuffer alpha as exposure data for the restored HDR/SkyGlow path. That semantic must survive conversion. The target architecture therefore keeps extended-range scene/effect values in a floating-point working path where justified, then performs one controlled tone-mapping step for the actual output target.

Quest 3 is treated as an SDR presentation target. Modern HDR/scRGB output is a separate optional mirror/display feature and must never be required for HMD correctness.

## Non-negotiable principles

1. **Preserve game semantics first.** `RestoreXboxBrightness`, SkyGlow, material exposure, alpha-test/cutout behavior, and restored console lighting are source semantics. Backend conversion must preserve them before attempting wider-gamut or HDR-display output.
2. **Never globally promote every render target.** Promotion is allowlist/provenance driven. Unknown resources retain their source format.
3. **Scene/effect color is the main FP16 candidate.** Prefer 16-bit floating point for eligible extended-range intermediates; FP32 is a diagnostic escape hatch, not the default production format.
4. **Alpha is not disposable.** Format upgrades must preserve alpha exactly because the restored renderer can carry exposure/glow information there.
5. **Tone map once.** The SDR HMD path has one explicit final tone-mapping boundary. Do not tone map in both the game/backend and OpenXR host/compositor path.
6. **Color-space selection is not tone mapping.** OpenXR color-space extensions or swapchain color-space declarations must not be treated as HDR luminance conversion.
7. **Reflection/UI/depth/transport resources are deny-by-default.** They require independent evidence before any format promotion.
8. **Fail closed.** If classification or capability evidence is incomplete, keep the original format and record why promotion was rejected.
9. **No ReShade dependency.** ReShade/inverse-tone-mapping experiments are useful reference evidence only; the VR backend must own its deterministic render/tone-map path.
10. **Build success is not visual proof.** Quest 3/VDXR runtime evidence remains required for graphics, stereo, glow, cutout, pacing and final-tone-map claims.

## Rendering model

```text
OutRun material / lighting semantics
        |
        |  exposure / SkyGlow semantics preserved
        v
eligible scene/effect color intermediates
        |
        |  selective FP16 promotion only
        v
stereo world + effects composition
        |
        |  keep extended range until composition is complete
        v
single explicit output transform
        |
        +--> Quest 3 / VDXR: SDR tone map -> OpenXR submission
        |
        +--> optional future desktop mirror: independent scRGB/HDR path
```

The HMD path must not depend on an HDR monitor, Windows HDR mode, ReShade, or a modified external DXVK build.

## Resource classification contract

Every renderable resource considered for promotion must resolve to one of these classes:

- **SCENE_COLOR** — perspective world/vehicle/track color; promotion candidate after evidence.
- **EFFECT_COLOR** — SkyGlow/bloom/post-effect intermediate; promotion candidate after evidence.
- **REFLECTION_COLOR** — car/water/reflection/cubemap resources; original format by default.
- **HUD_UI_COLOR** — HUD, text, menus, screen sprites; original format by default.
- **MASK_ALPHA** — masks, cutouts, classification/coverage intermediates; original format by default.
- **DEPTH_STENCIL** — never promoted by this design.
- **COPY_RESOLVE_TEMP** — original format unless exact copy/resolve compatibility is proven.
- **READBACK_LOCKABLE** — original format.
- **XR_IPC_TRANSPORT** — format is governed by transport/OpenXR interoperability, not scene-HDR policy.
- **UNKNOWN** — original format, telemetry required if encountered in a promotion-relevant path.

Classification should prefer resource creation callsite/provenance, producer scope, use flags, known effect lifecycle, dimensions and source format. Dimensions or format alone are never sufficient evidence.

## Promotion policy

A resource may be promoted only when all are true:

- it is classified `SCENE_COLOR` or `EFFECT_COLOR`;
- its producer/consumer chain is understood;
- required render/sample/copy/resolve operations are supported;
- shader/fixed-function expectations remain valid;
- alpha meaning is preserved;
- reset/recreate lifetime is handled;
- memory/bandwidth cost fits the active performance profile;
- deterministic tests cover both promotion and fallback.

Promotion must be per-resource or per-provenance family. A backend-wide "upgrade all matching formats" switch is not an acceptable production design.

## Explicit deny-by-default surfaces

Do not automatically upgrade:

- water or car reflection targets;
- cubemaps/environment maps;
- HUD/menu/text/rank-marker targets;
- stencil/depth surfaces;
- alpha/cutout/mask intermediates;
- lockable/readback textures;
- resource-copy staging surfaces;
- swapchain/OpenXR/DirectGPU shared surfaces;
- unknown render targets.

The reflection restriction is intentional: broad FP render-target upgrades have publicly shown reflection/water regressions in OutRun experiments. Any future exception needs its own proof and regression test.

## Tone-mapping boundary

For Quest 3 / VDXR:

1. keep eligible scene/effect data in linear extended range through stereo composition;
2. combine SkyGlow/bloom while the working range is still floating point;
3. apply one deterministic SDR tone mapper after scene/effect composition and before the final HMD submission surface;
4. keep HUD/UI composition policy explicit:
   - if UI is authored in display-referred SDR, composite it after scene tone mapping where practical;
   - if an existing backend architecture requires UI before the output transform, protect UI from unintended exposure/bloom and validate text/white levels separately;
5. clamp/encode only at the final target boundary.

Do not use `XR_FB_color_space` or an equivalent color-space declaration as a replacement for luminance mapping.

## HDR desktop mirror is a separate feature

A future desktop mirror may expose scRGB/HDR independently from the Quest SDR path. If implemented:

- it gets a distinct output transform and capability gate;
- HMD and mirror outputs must not share an implicit tone-map assumption;
- turning Windows HDR on/off must not alter HMD rendering;
- mirror HDR failure must not disable VR.

This is lower priority than correct Quest 3 stereo, HUD, effects and pacing.


## Native DX11 lane rules

The native DX11 lane may use `DXGI_FORMAT_R16G16B16A16_FLOAT` for **explicitly proven scene-color/effect resources** after the source draw/resource translation proves compatibility.

Before promotion, verify:
- RTV/SRV/Copy/Resolve behavior remains compatible with the translated resource contract;
- source alpha is preserved as data, including OutRun exposure/glow semantics;
- the resource is not a reflection/cubemap, UI/HUD surface, mask, depth/stencil surface, readback surface, or OpenXR/IPC transport surface unless separately proven safe;
- the resource-lifetime and format mapping survives reset/recreate paths.

This document does **not** authorize native D3D11 Draw* routing. Existing census/activation proof gates remain authoritative; format work must remain fail-closed until those gates permit the corresponding resource/draw path.


## Performance budget

FP16 roughly doubles color storage/bandwidth versus common 8-bit RGBA resources. Therefore:

- promote the smallest proven set of resources;
- keep FP32 out of normal production profiles;
- include allocation count, promoted bytes, copy/blit count and fallback reason telemetry;
- measure frame-time impact separately from visual correctness;
- retain the project goal of stable 72 Hz operation on hardware below the development RTX 4070 where practical.

A visual improvement that materially destabilizes frame pacing is not automatically accepted.

## Implementation sequence

### H0 — provenance/telemetry only
- enumerate render-target/resource creation and lifecycle;
- classify resources without changing formats;
- record candidate class, original format, dimensions, usage, producer and reject reason.

### H1 — isolated FP16 experiment
- promote one proven SCENE_COLOR or EFFECT_COLOR family;
- preserve original-format fallback;
- add deterministic capability and lifetime guards;
- do not change unrelated reflection/UI/transport resources.

### H2 — effect-range preservation
- verify Xbox brightness/exposure and SkyGlow values survive the promoted path;
- verify alpha/cutouts, particles, translucent scenery and bloom thresholds.

### H3 — final SDR tone map
- add one backend-owned tone-map boundary for Quest output;
- protect HUD/menu/text white levels and avoid double tone mapping.

### H4 — stereo/performance runtime gate
- Quest 3/VDXR same-scene checks for left/right parity, world stereo, SkyGlow/bloom, reflections, water, HUD/menu/text, rank markers, cutouts and frame pacing.

### H5 — optional desktop HDR mirror
- only after the Quest SDR path is stable and protected.

## Required regression coverage

Any implementation of this design must specifically check:

- restored Xbox brightness remains neither lost nor doubled;
- SkyGlow threshold/intensity is preserved;
- water/car reflections are unchanged unless intentionally promoted;
- alpha-tested foliage/fences/road-edge materials retain cutout behavior;
- transparent particles and blended materials do not inherit exposure alpha incorrectly;
- HUD/menu/white text remain stable and readable;
- vehicle/world rank markers keep their correct spatial semantics;
- no left/right exposure or tone-map mismatch is introduced;
- reset/device recreation does not silently revert or over-promote formats;
- original-format fallback produces a usable frame;
- frame pacing/copy bandwidth does not regress beyond the accepted profile.

## Acceptance rule

This document is architectural guidance. It does not by itself advance any conversion gate.

A backend may claim:
- **STATICALLY VERIFIED** after classification/capability/lifetime tests pass;
- **BUILD VERIFIED** after exact-SHA CI passes;
- **RUNTIME VERIFIED** only after matching Quest 3/VDXR evidence.

Until runtime evidence exists, keep `RUNTIME_VALIDATION=UNTESTED`.
