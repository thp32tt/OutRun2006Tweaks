# DX11 output binding contract probe R132

## Purpose

Static evidence artifact for the DX11 conversion lane. This probe documents the expected output-binding invariants before any NativeDrawPath activation is considered.

## Contract

- The DX11 path must keep NativeDrawPathActive disabled until exhaustive draw census evidence exists.
- Output state translation must preserve the distinction between:
  - source D3D9 render target identity;
  - mirrored DX11 resource identity;
  - current output binding state.
- A missing mirror/resource mapping is a fail-closed condition, not a request to activate a fallback draw path.
- Binding validation must be deterministic from captured state descriptions and must not depend on Quest 3/VDXR runtime availability.

## Static validation cases

| Case | Expected result |
| --- | --- |
| Known output binding with matching mirror identity | PASS |
| Known output binding without mirror identity | FAIL_CLOSED |
| Stale generation identifier | FAIL_CLOSED |
| Runtime-only visual validation unavailable | RUNTIME_VALIDATION=UNTESTED |

## Scope

This artifact is limited to DX11 conversion evidence. It does not modify DXVK, DX9Ex, localization, or runtime activation behavior.
