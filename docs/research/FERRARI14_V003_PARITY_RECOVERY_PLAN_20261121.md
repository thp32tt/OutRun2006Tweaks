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

## Corrected official RELEASE ASSET SHA (verified by Windows GitHub Actions 2026-11-21)

Do not mistake the older `normal-v003-final-5eb41778-artifact.zip` workflow artifact for the exact published `v0.03` GitHub Release asset. The **actually published** `OutRun2_VR_v0.03_Beta_Cockpit.zip`, freshly downloaded in Windows runner 44908510911, contains:

- `OR2006C2C.EXE`: SHA256 `68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3`
- `OutRun2006Tweaks.ini`: SHA256 `630fc782a7b99666bc6f62ee0c791f160bddb6b1a879ef97f39f38763ac77358`
- `dinput8.dll`: SHA256 `5d3c4fa550f3589323d1bddf65f475915f97b1bcdd3904ba50df865e002b7443`
- `outrun-vr-host.exe`: SHA256 `8c7e574214eb39a11db906e97465da77e69402bc7aeaeb835bc8e732ad3d661f`

**Critical compatibility rule:** do not distribute the older `bbeb46ea...` host in this new Ferrari test package. The installer verifies and preserves the official actual `8c7e5742...` host; only the experimental x86 DLL changes. Earlier patches using a different host are no longer accepted as the clean v0.03 baseline. This is a release artifact vs prior CI artifact discrepancy, not a newly confirmed host ABI defect.
