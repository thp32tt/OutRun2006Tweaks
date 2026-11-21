# Ferrari14 v0.03 exact-release parity and recovery plan (2026-11-21 KST)

Baseline: official v0.03 tag / branch `2446269aa33bc3c90a2a57f36a650cdd4d4fd5d7`; Ferrari source parent `f6f0e599450bc0fae1d38b8330728870c511084d`. The release differs from Ferrari's common v0.03 base only in workflow/readme. **Never modify the official release branch.**

## Implementation and acceptance gates

| Phase | Scope | Proof / safety bar |
|---|---|---|
| P0 | Exact official release game copy and preflight | Pin EXE/INI/DLL/x64-host SHA256; never install to production or unknown test folders; explicit marker and backup/rollback |
| P1 | Native callback parity and startup fallback | Model OFF, all menus/2D and rejected candidates must call original native callback; generic full-callback replacement is opt-in only |
| P2 | 575 placement | Apply original F50 vertical smoothing to F50 only; generic 575 uses native B0 + validated static floor lift; do not change saved seat/F11 or game camera |
| P3 | Stereo pipeline | Generic external PBR (VS c0/c4/c8) prohibited until per-eye c64-equivalent is proven; only opt-in fixed-function stereo A/B; native D3D9Ex/DirectGPU core unchanged |
| P4 | Performance / GPU | Avoid extra telemetry in normal A/B; state restore/reset retains fail-closed policy. Native D3D9 stateblock per sidecar draw remains a measured performance risk, **not** a proved cause of headset 25fps |
| P5 | Asset quality | Exclude previous black-paint/flat-gray hybrid from being called final. Optional owner-private Rosso/original-gauge OVC test only, not publicly committed |
| P6 | CI / package | Portable C++ regression tests, Win32 build, ZIP SHA256, Windows PowerShell syntax/installer checks, clean A/B pack without original game/model bytes |
| P7 | Physical HMD | Quest3 release-baseline → patched model OFF → 575 ON → TRACE, compare eye transforms, directReady, cached/fresh, FPS, first stage and occlusion; unresolved until observed |

## Original native callback boundary

`QuestCockpitGlassLive::PlayerCallback` captures native queued draw descriptors, while the original `0x49F3E0` callback itself can have other state/effect work. The Ferrari sidecar bypasses that entire callback after external submission. We **cannot** safely invoke both full original and full external draws or they may overlap. Generic replacement therefore requires a *second explicit acknowledgement* `ExternalFerrariNativeCallbackReplacement=true`, in addition to the selected 575 slot and fixed-function test path. This is a controlled A/B experiment, not proof of full release effect parity. Truly preserving partial native effects requires verified per-subdraw owners and Quest3 acceptance, not blind state masking.

## Strict status

The stable normal v0.03 behavior remains the fallback. Test-only/source-only success must not be reported as physically repaired 3D/FPS. Never mix a 2026-11-19 Ferrari13 recovery host/launcher with this release-based build.
