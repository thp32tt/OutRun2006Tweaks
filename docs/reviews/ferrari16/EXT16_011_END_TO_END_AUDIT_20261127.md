# EXT16-011 end-to-end audit and implementation plan — 2026-11-27 KST

Scope: external Ferrari16 native-model replacement on automation/ferrari16-external-20261123.
Base reviewed: 3559d77a4139d73ad928e4e6c0d7de6b35bad22f. This is a targeted audit of the
external asset, native callback, private stereo, surface transfer and test-package path,
not an assertion that every line of all unrelated OutRun modules has been reviewed.

## Findings and applied changes

| Priority | Finding | Source action |
|---|---|---|
| P0 | Prior exact Windows build failed C3861 InSceneEffect | Qualify QuestCockpitV2 scene-effect guard (18aad6c). |
| P0 | Candidate seeding accepted a previous car's ready GPU asset, wrong camera/selection and missing dashboard | Bind readiness to device, canonical slot/current player, cockpit and DirectGPU; require dashboard needle and gear coverage. Never initiate new uploads inside private stage (0a3cc85). |
| P0 | Independent raw auxiliary raster still retired a valid candidate | Admit only proven disjoint attachments; invalidate on failed write or boundary change (0a3cc85). |
| P0 | Synchronous Reset in Clear, descriptor/proof or seed could leave stale right-eye work | Fence LEFT Clear and viewport getter, preserve the actual physical HRESULT, invalidate receipt, classify reset during seed as dirty (aefb645). |
| P0 | Opaque-only cockpit/native remaster assets could be mistaken for a whole external vehicle | Require a tagged body glass mesh before seed/omission/stage; cache count at successful mesh upload and clear on GPU retirement. This does not prove correct glass geometry/alpha. |
| P1 | Repeated isolated mesh state, transform and material bindings | Cache within one isolated draw StateBlock only, never across eye/reset/restore or legacy hooked draw (1289688). |
| P1 | Neutral ORM changed the BRDF versus absent ORM | Same roughness-aware ambient model with/without map; AO multiplies indirect light (0a3cc85). |
| P1 | Only F50 PBR launch path had explicit trace, stock benchmark lacked logs | Matched all-car PBR and stock-only GPU trace launchers, protected install and restore manifests (6cad977). |

## Actual asset evidence, not release acceptance

N100 private research outputs ext16_20261127_geometry_orm_16_v2: 16 files, 563 baked
AO ORM maps, 139 missing slots. Lightweight raw-header inspection confirmed all 16 have
zero normal DDS and zero tagged glass triangles. All have two dashboard bindings.
The repository read-only verifier passed structural inspection of car_id_02.ovc:
40 ORM, zero normal maps, zero glass triangles, speed/RPM bindings and no gears,
10 materials without valid UV basis, 22 partially degenerate UV materials.
A complete 16-car full verifier run timed out; do not report full parser acceptance.
These are old research derivatives, NOT approved whole-car assets. Do not overwrite
the working game or distribute them as full external cars.

## Remaining development, in order

1. P0: exact SHA Windows x86 build, x64 host/package, all-car/HLSL and HUD regression;
   fix each compile/failure before calling any milestone complete.
2. P0: identify current exact external source and converted OVC for each of 16,
   separate old native/cockpit assets, verify provenance, glass tag/alpha, wheel/floor,
   all gear/needle coverage and per-material DDS/UV/tangent basis. Use original fallback
   on missing or unverified source. Re-bake AO only for verified external source; do not
   invent authored roughness/metallic or overwrite existing normal/ORM maps.
3. P0: audit remaining physical raster/copy/state-block/readback routes, including
   texture aliases, main-depth identity and post-stage dependencies. A disjoint
   attachment alone is not proof of all read dependencies; unknown routes remain stock.
4. P1: measure matched PBR/stock at 120Hz, same track, camera, resolution and vehicle;
   record GPU P50/P95/P99, CPU stage, actual OpenXR submitted frame interval/drop rate.
   Current GPU profiler ends pre-Present and excludes final transport work. Add
   transfer-specific metrics before claiming a complete GPU cost; 8.33ms is target,
   not a measured result. If over budget, profile real scene replay and reduce
   redundant state/attachment operations without dropping one eye or depth correctness.
5. P0: user Quest3/VDXR runtime: every car both eyes, glass transparency, dashboard
   speed/RPM/gear, depth/road occlusion, stock fallback missing/corrupt assets, reset,
   menu and race transitions. Capture logs with exact SHA and compare both modes.
   Static CI does not constitute HMD PASS. A1-A6 remain in progress; no stable release overwrite.
