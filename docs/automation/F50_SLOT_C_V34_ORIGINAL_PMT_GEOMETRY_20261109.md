# Ferrari F50 — slot C v34 original-game cockpit geometry checkpoint (2026-11-09 KST)

**Scope:** `active_by_slot.C=f50` only. Source-only driver-visible instrument hood, original three-spoke wheel with lower grip arc and original six-bolt hub. No Dino, Daytona/slot A, external body/wheels/tires, textures/normals/PBR, gameplay or VR/runtime, PMT/OVC/OVC3 export.

**State:** REAL N100 PRIVATE SOURCE BLEND SAVED / OFFICIAL BLENDER 4.5.15 FRESH-PROCESS REOPEN & SAME-CAMERA RENDER PASS. **F50 remains ACTIVE / PARTIAL_NEEDS_QA, not COMPLETE**. Hosted GitHub Actions real-scene test: **BLOCKED_INPUT_PRIVATE_BLEND_NOT_TRANSFERRED**. This checkpoint is not a game build.

## Immutable original game provenance

| Artifact | Exact path / identity | SHA256 |
| --- | --- | --- |
| Read-only original OutRun 2006 F50 PMT | `/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_f50_pmt.sz` | `10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab` |
| Native original source-import .blend | `work_handoff/ferrari16_slotC_f50_source_audit_20261108/F50_OriginalPMT_CockpitSource_v1.blend` | `d82b3d024a812126da5b38c56572cfc326fbe3d1b5c0ddf8cad4cbd855119d31` |
| Immutable accepted v33-r2 parent | `work_handoff/ferrari16_slotC_f50_source_audit_20261108/F50_OriginalPMT_P0_DashboardSteering_v33_r2.blend` | `40a555a8d265b87d6ad7fc109672ceb339629a8311c1f5c0ca96a717916b19df` |
| **New real editable v34 .blend** | `work_handoff/ferrari16_slotC_f50_source_audit_20261108/F50_OriginalPMT_P0_DashboardSteering_v34.blend` | **`3e5cc0f9d56f061d8c8c12a14ccc8aefdc0234dc4e845bd36c5a24ce8f66165a`** |

New private .blend size: 1,539,817 bytes. All original game files and previous private sources remain immutable.

## Actual edits to existing source mesh IDs

Edits are coordinate moves on original PMT-derived Blender objects, NOT new geometry objects, third-party GLB or a generated cockpit. Three existing source meshes changed, 39 other original meshes remained identical. No topology, source UV/material slots, object/world transforms or QA camera transforms changed.

| Original PMT object ID | Original+result vertices/faces | Moved vertices | Max coordinate displacement | Native mesh SHA256 before → after |
| --- | --- | ---: | ---: | --- |
| `object00_group01_material028_a0` instrument hood | 5506 / 7552 | 906 | 0.859976 mm | `0ca34ebe2d609fce82c8305c1bb06126b0daf5a7d9a239174fa7fb8885f7ebcd` → `2753414bdf45d2f0b46faf38d253cb874f74925046a81300cb724a7a819d3766` |
| `object21_group01_material002_a0` native 3-spoke metal sheet + lower leather ring | 13552 / 26496 | 1736 | 1.400000 mm | `3ac53bfb2b001d5955425fe5269138341a77e6d79d49d90b9d4ed87f8624e7d4` → `c7845a16fe23503f837f9fe35234139744dfeeee75089720726c87f280b93a11` |
| `object21_group00_material000_a0` original 6-bolt hub | 2738 / 4464 | 560 | 1.368099 mm | `36650b8054aafcbaf63ef9f0ae880440a1e0b3a8243e3d3859412c10c22d8b00` → `3932f604d521400c2b01467ee7d5e21288b65d93e9820c89638cf64b74c9defd` |

Total real source vertices moved: **3,202**. Original existing wheel open-boundary loops sizes `[48,48,72,72,72,96,96,120]` (624 nonmanifold/open edges) explicitly retained without damage. **Do not treat these source holes as sealed or final weld QA.** v33-r2 upper-rim scar regression is avoided by leaving the entire upper ring outside v34's lower-rim-only fairing.

## Photo source control and independent renders

Private N100 reference library: `/home/chatgpt-runner/outrun2_vr_refs/20261104_16car_cockpit/MANIFEST.json`, `COVERAGE_MATRIX_16x8.csv`, F50 folder `03_F50/`. F50 has 17 indexed records, 16 local photos; coverage still only validates center shifter and does **not** establish seven driver-eye-equivalent views.

- Real F50 cockpit wide photo local `03_F50/REF16_interior_1_b0df0e6809.jpg` SHA256 `9a52450918bfa4a0cb22cf56c0bf373175b212dcb20fe1e6ee7c512114546dad`.
- Instrument and 3-spoke wheel reference `03_F50/REF2_dashboard_closeup_dad64db8c0a5.jpg` SHA256 `6d2a66553b22fbf03f9bfdceed2a9bc5930cc0564da8b8bbe7a45bb01f6d8961`, source page https://www.pistonheads.com/news/ph-ferrari/ferrari-embarks-on-f50-30th-anniversary-tour/49812. **Reference is RHD; cannot assert matched original game LHD eye.**
- Additional LHD Ferrari F50 reference `03_F50/REF5_mecum_interior_01_f8afa7e2a.jpg` SHA256 `cd31303113763596eebada76ea964386522f4a03c9684c9132226963e8663ca2`.

Private authentic Blender output and reports, all under the F50 private folder:
- `F50_P0_DashboardSteering_MeshDelta_v34.json`: before/after object metadata/hashes and guarded edits.
- `F50_SlotC_P0_v34_Independent_Reopen_Audit.json`: **PASS_F50_V34_4_5_15_FRESH_PROCESS_SOURCE_REOPEN_RENDER**. Reopened both parent and v34 in a separate Blender 4.5.15 process; source identities, all 39 unchanged meshes, 624 original open edges, matrices, original game PMT SHA, and new SHA all checked.
- `F50_SlotC_P0_v34_REAL_SOURCE_BEFORE_AFTER.jpg`: same two **NON-GAME** Blender QA cameras, v33-r2 vs v34, 2×2 comparison, SHA256 **`1e0a67032de5d3eef0a99b92e7abe870513b847f87246087e26929f68527fc09`**. 1,188 gauge pixels and 6,649 steering pixels change by RGB difference >3. These measures only prove visual change, not photographic accuracy.
- Separate independently reopened steering render: SHA256 `750b9c8789780ba028fb880172a34dd61ef7699f5a56e8005cfcc18608ae4ec1`.

## Public modeling script, QA gates and ownership

- GitHub source: `tools/car_modeling/slot_c/f50_p0_source_mesh_v34.py` (SHA256 `16303a29cb100b4baa5d28302cdbd603c99d9f21094ebdd2363d941ccc370a17`; commit `5f333ebc44add54ff8a9cbebfd381bc4236334c2`).
- Script accepts only exact PMT, original-import and v33-r2 parent SHA256; saves separate private .blend and provides a second-process `--mode audit`; blocks unapproved source/object/camera/UV/material changes and output overwrite.
- Official Blender 4.5.15 on private N100: **real scene save/reopen/render PASS**. GitHub Actions runner: **BLOCKED_INPUT_PRIVATE_BLEND_NOT_TRANSFERRED**; no hosted real F50 scene QA or completion claim.
- Native original game driver-eye camera/FOV and seven exact authenticated photo views remain unverified, and original steering open edges remain. Keep `active_by_slot.C=f50`, `status=ACTIVE`, `geometry_gate=PARTIAL_NEEDS_QA`, `reference_gate=PARTIAL_NEEDS_7_VIEWS`.
- Slot C first material geometry `2026-11-08T04:35:52Z`; earliest 24-hour end `2026-11-09T04:35:52Z` (13:35:52 KST). Time elapsed alone cannot advance until gates pass.
- AI2 scoring: **+0**, same ongoing F50 P0 feature continuation; no duplicate credit for independent audit/renders or rollover.

No proprietary PMT, private original-derived .blend, downloaded reference photos or copyrighted game resource committed to public GitHub.
