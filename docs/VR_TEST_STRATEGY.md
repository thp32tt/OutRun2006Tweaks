# VR runtime test minimization strategy

This branch treats Quest 3 / VDXR runtime testing as a scarce validation gate rather than a per-change development loop.

## Default loop

1. Review and implement independent issues without waiting for a headset test.
2. Classify every change into TEST_LEVEL 0..4.
3. Accumulate compatible LEVEL0/LEVEL1 changes behind configuration/feature boundaries.
4. Build and statically validate affected Win32 DX9Ex game + x64 D3D11 OpenXR host only.
5. Freeze one CORRECTNESS candidate around the evening test window when material changes exist.
6. Ask for CONTROL or PERFORMANCE only when the evidence requires an A/B comparison.
7. Preserve the frozen candidate while the user is testing it.

## Profiles

- CONTROL: conservative DX9Ex reference used only when a baseline comparison is needed.
- CORRECTNESS: default daily runtime profile and the only profile the user should normally need.
- PERFORMANCE: same binary set where possible, with isolated performance feature flags enabled only when supported.

Backend and TestProfile are separate identities. Session manifests and log archives must record both.

## Test levels

- LEVEL0: no HMD test required. Deterministic/static/build-verifiable work.
- LEVEL1: validate in the next normal CORRECTNESS test.
- LEVEL2: validate only with PERFORMANCE/A-B when needed.
- LEVEL3: backend-specific runtime validation such as D3D9Ex transport/reset/shared-resource behavior.
- LEVEL4: release-matrix validation only.

Lack of new runtime evidence is not a reason to stop work on independent LEVEL0/static investigations.

## Diagnostic capture target

F11 remains the existing Tweaks overlay key. The VR diagnostic trigger is Ctrl+F11 (or another explicitly non-conflicting bind).

The target capture bundle is low overhead and on-demand:

- bounded rolling telemetry, roughly the previous 10 seconds plus a short post-trigger window;
- backend/profile/session/source identity;
- frame/pose/presentation/fallback state;
- OpenXR refresh/recommended eye size when available;
- L/R view/projection/WVP evidence;
- draw-class counters;
- wait/acquire/render-left/render-right/copy/end timings;
- recent logs;
- optional L/R image snapshots only when a safe low-overhead path exists.

Capture file I/O should be deferred from the render hot path. Reset/session/resource generations invalidate stale capture state.

## Scheduled development split

The :00 automation is the only production writer on vr-d3d9ex-focus. It implements, validates, commits and freezes the evening CORRECTNESS candidate.

The :30 automation works independently on vr-d3d9ex-review. It performs adversarial review and may add documentation or verifier prototypes, but it must not change production runtime behavior or replace the frozen candidate.

The main job consumes only verified evidence from the review branch.


## Temporary compile-time comparison caveat

Some current renderer-chain comparisons (historical P1/P2/P3/P4) are selected by CMake source composition and cannot yet be toggled safely inside one DLL. They are retained only as regression-isolation tools. The default development policy no longer requires the user to test them sequentially. Runtime/profile differences that are already safe to isolate use CONTROL/CORRECTNESS/PERFORMANCE with one binary set; renderer-chain compile variants should be retired or feature-flagged only after the DX9Ex reference path is established.

## Scheduled support split

- :00 — production writer on `vr-d3d9ex-focus`.
- :30 — adversarial reviewer on `vr-d3d9ex-review`, no production runtime writes.
- 01:15 — once-per-day nightly gate: consolidate evidence, validate hashes/profile/session state, remove redundant test requests, and tell the 02:00 run which unchanged work can be skipped.
- 08:15 / 11:15 / 14:15 / 17:15 — support work on `vr-d3d9ex-support` when a commit is needed: reusable verifiers, profile/session/log/package validators, CI efficiency, capture-schema/ring-buffer test harnesses and TEST_LEVEL demotion work. This slot does not become a third production runtime writer.
