# F50 slot C — v20 authentic OutRun 2006 native-PMT cockpit geometry (2026-11-08 KST)

**State:** `ACTIVE / PARTIAL_NEEDS_QA`. F50 remains slot C; slot A Daytona and already-complete Dino 246 untouched. No car transition; AI2 score +0 (same ongoing original F50 P0 feature, not a new independent score adjudication).

## Verified original and private immutable lineage

- Read-only original game resource: `/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_f50_pmt.sz` SHA256 `10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab`.
- True native direct import, initial editable .blend: `work_handoff/ferrari16_slotC_f50_source_audit_20261108/F50_OriginalPMT_CockpitSource_v1.blend` SHA256 `d82b3d024a812126da5b38c56572cfc326fbe3d1b5c0ddf8cad4cbd855119d31`.
- Exact immutable input v19 .blend SHA256 `fc37c4682aee385fab9d06fdf6abec8fc0325faa14996ed371b730a805d928bd`.
- **New private editable v20 .blend** `work_handoff/ferrari16_slotC_f50_source_audit_20261108/F50_OriginalPMT_P0_DashboardSteering_v20.blend`, SHA256 **`e4b82bf586ac8459960b61117d4fb68b8a0e5fa22beae2006fb18b1edc0f47bc`**, file verified on N100 after independent re-open, size 1,539,039 bytes.
- All 42 original PMT-derived mesh objects remain, original mesh ID/transform/camera/UV/material and face/vertex counts unchanged. Only the exact three original cockpit mesh objects below were edited in-place; no new objects.

## Actual per-object geometry delta (v19 → v20)

| Original source mesh ID | vertices/faces before → after | moved existing vertices | maximum local displacement | mesh SHA256 before → after |
|---|---:|---:|---:|---|
| `object00_group01_material028_a0` instrument cowl/visor | 5506/7552 → 5506/7552 | 1432 | 3.096 mm | `248992cd049a29c2c69b026979d863ef6c5f5a516167cb37e4455131c31f0c67` → `2beef9bfedd70361f8be1d55c58d95959e0eaf185493c6eb2fa6b352f082ee16` |
| `object21_group01_material002_a0` native 3-spoke rim/grip | 13552/26496 → 13552/26496 | 11416 | 1.450 mm | `328077c4d14747258f1fe67f9be344428add117a677c31a3cc04aef57af7e3a6` → `ff0d50d358343794daef0183a0e0f4c1456859932e9609df1af2e55beb1d90db` |
| `object21_group00_material000_a0` existing center hub/horn cup | 2738/4464 → 2738/4464 | 2211 | 1.248 mm | `b53b248f0301fe1c23ff05959ba2d116640fbcd8e9b7a7aa66d8b8d7d643c580` → `ff4f9ced8d5d6873ebf57922ecf6da3efd1519eaf5f16342f0b32c04895f6a31` |

Visor: repeat native top/bottom normal-separated local quadratic fitting to reduce remaining faceted wrinkles, without changing source outline or closing layers. Steering: refine existing three-spoke shoulder and rim grip contours. Hub: contour relief on existing center cup/ring and six source fastener seats. Do not claim visual likeness PASS yet: render inspection still shows faceting and authentic F50-specific deviations. The **other 39 PMT-derived original mesh geometry hashes are identical**. Existing native steering-wheel 624 open/nonmanifold edges remain 624, deliberately not filled.

## Genuine Blender 4.5.15 and private reference QA

- Native original PMT + first imported .blend + v19 SHA gates verified *before* build; original input and 24h ownership not modified.
- Official **Blender 4.5.15 LTS** on N100 saved actual v20; **fresh separate 4.5.15 process** opened v20, opened v19, reopened v20, compared all 42 real original mesh identities / signatures / cameras / transforms and independently rendered real steering mesh. Receipt `F50_SlotC_P0_v20_Independent_Reopen_Audit.json`: `PASS_INDEPENDENT_F50_V20_TRUE_ORIGINAL_BLENDER_4_5_15_REOPEN_RENDER`.
- Private source-derived before/after 2×2 render sheet `F50_SlotC_P0_v20_TRUE_SOURCE_BEFORE_AFTER.jpg` SHA256 `c8040c0260ab575adff2071a0f52bd9bacf8975f60b4d2335a071e048f3a592f`. Separate independent render SHA256 `f41671322772f0d99534904bf86075474e130a0ef7372d48a484f89da384db53`. These are non-game diagnostic cameras, **NOT original game driver-eye**.
- Photo library `03_F50` checked against `MANIFEST.json` and `COVERAGE_MATRIX_16x8.csv`. Exact-model F50 source photo `REF2_dashboard_closeup_dad64db8c0a5.jpg`, source page PistonHeads, local SHA256 `6d2a66553b22fbf03f9bfdceed2a9bc5930cc0564da8b8bbe7a45bb01f6d8961`; private-only photo+Blender comparison `F50_SlotC_P0_v20_PRIVATE_REAL_PHOTO_COMPARE.jpg` SHA256 `e73d16d4019358123efd1c8b5cdd9fe80fadd589ac0fe1954658c9f98284a04c`. Photo not published or repurposed as texture. Matrix full driver-eye / gauges / steering / door / windshield views still not independently verified.

## Gates and restrictions

- **BLOCKED_INPUT_PRIVATE_BLEND_NOT_TRANSFERRED for GitHub-hosted real-scene QA**: official hosted Actions does not have the proprietary native PMT/import/v20 .blend; public source-only CI cannot prove hosted original scene or render. Local official Blender real-scene QA is PASS, but **vehicle is not COMPLETE**.
- **P0 PARTIAL:** visually acceptable F50 instrument cowl, wheel hub and rim not yet signed off; native game driver eye, correct full seven photo-matched viewpoints, camera/pivot placement, 24h allocation and 624 source wheel open edges unresolved.
- Source editing scripts only: `tools/car_modeling/slot_c/f50_p0_source_mesh_v20.py`, `tools/car_modeling/slot_c/f50_v20_independent_reopen.py`. Original PMT, original v19, Dino, slot A, Model2/VR/DX branches unchanged.
- Forbidden outputs **zero**: no OVC3/OVC/PMT conversion/output, game runtime or mod package, new GLB, exterior wheels/body, newly made texture/normal/PBR/ORM or public proprietary .blend upload.
