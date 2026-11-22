# Ferrari16 external vehicle loader: correction plan and verification

Date: 2026-11-22 (KST)
Branch: `fix/ferrari16-stereo-loader-guard-20261122`
Input: `vr-ferrari16-v003-multicar-debug-20261122@929ba1e60ef94904c99d9a1337849bcc57a69a8a`
Known-good comparison: v0.03 `2446269aa33bc3c90a2a57f36a650cdd4d4fd5d7`

## Implementation and priorities

| Priority | Issue | Current state | Proof required before merge |
| --- | --- | --- | --- |
| P0 | Left-only HRESULT masquerades as bilateral success | **Implemented, CI regression**: per-DIP `ExternalStereoMeshReceipt` from R7, R30, R33; pose check, both eye outcome, state restoration, exact once report | Windows Build, Quest 3 L/R and failure injection, all 16 installed cars |
| P0 | Original player callback is skipped after external body replacement | **Not implemented: unsafe to change without exact native car-leaf suppression** | Native 46BD30 / 469600 opcode+ABI verification, no duplicate body, original update/occupant/shadow preserved |
| P1 | External vehicle consumes pending game HUD semantic | **Implemented, regression:** `ScopedExternalVehicleSemantic` retains `NextDrawScope` while external DIP routes through R33 `ConsumeForDraw()` | Runtime HUD, F11, rank/rival, goal/lens, menu/sky comparison |
| P1 | File CRC/parse and whole-GPU upload block draw callback | **Implemented, Windows Build pending:** `std::async` CPU IO/CRC/parse, atomic CPU result adoption, 1 albedo or 1 VB/IB mesh GPU upload per callback; native fallback until full ready | First-enter/selection/reset stalls, GPU device-loss, missing/corrupt OVC, 16 cars sequentially |
| P1 | Legacy F50 bypasses fixed-function stereo probe | **Implemented:** same opt-in acknowledgement and fixed-function diagnostic gate for F50 and generic cars | Verify F50 launch flags with operator and A/B graphics |
| P2 | Mirrored-UV derivative tangent incorrectly omits determinant | **Implemented:** divide both tangent derivatives by UV determinant, compute bitangent handedness | Shader compile and mirrored normal-map reference images |
| P2 | Transparency inferred from mesh name | **Deferred (asset format change)**: current OVC V4 has no material alpha mode; changing D3D9 transparency by guessed name or alpha texture alone is unsafe | Extend OVC schema/packer/parser with validated alpha mode and sample assets |
| P2 | Only minimum local Y used for ground validation | **Deferred (per-car source contract)**: scale/axes/pivot/wheel coordinates should accompany each source asset | All-car axle/wheelbase, orientation and ground QA |

## Native original callback: why suppression must be selective

PC retail reference decomp `r4dius/outrun2-decomp` describes `0x46BD30` as
`vehicle_race_display_46bd30` which updates render-environment lighting and
race-display phase state; its `0x469600` model child updates car flags,
convertible-roof state and queues draw calls. It additionally issues native
shadow/queue and wheel draw leaves. Thus the current `PlayerCallbackHook.ccall`
early return is **not** a proven body-only replacement. Blindly calling the
original after external DIP overlays full original car triangles: not safe.
Blindly skipping `0x469600` can drop game field updates: also not safe.

Proposed next isolatable change (do **not** enable without runtime/ABI proof):
exact validated `0x405360`/alternate `0x4056D0` native **car-body leaf**
suppression only inside verified `0x469600` player scope, preserving
`0x46BD30` and `0x469600` state mutations, shade, passenger, native shadows,
and queue lifecycle. Prove signatures and entrypoint ABI from supported EXE,
then stage external DIP only after stock leaf suppression is active and validated.
Reject unknown leaf/scope entirely instead of applying global mesh suppression.

## Deployment and QA contract

* Only modify the above opt-in 16-car branch. Never merge automatically into
  known-good release v0.03.
* Require complete Win32 Release Build and Ferrari16 regression CI.
* With external **OFF**, confirm original v0.03 behavior.
* With selected external model **missing/corrupt**, confirm native PMT.
* With CPU Reading/GPU Uploading, confirm native PMT and no per-eye drawing.
* With a forced RIGHT-eye failure, confirm `EXTERNAL_PARTIAL_QUARANTINED`;
  never draw native body over an already rasterized eye; next-frame fallback.
* With both eyes complete, confirm `verifiedEyePairs==expectedMeshes`,
  `attempted==submitted==expected`, and matching epoch/pose.
* Manually verify headset world/sky, menus, HUD, rank/rival, 2D F11, passenger
  visibility, dashboard, geometry scale/pivot, transparent glass and framerate.
* CI static/compile success is **not** evidence of Quest 3 runtime stereo success.
