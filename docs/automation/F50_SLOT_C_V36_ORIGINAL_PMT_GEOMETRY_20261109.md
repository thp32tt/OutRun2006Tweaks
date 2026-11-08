# Ferrari F50 Slot C v36 — original OutRun 2006 cockpit-only native geometry (2026-11-09 KST)

**State:** ACTIVE / PARTIAL_NEEDS_QA. Only slot C `active_by_slot.C=f50`; no vehicle promotion. This is a real Blender edit of a verified imported original game native resource, **not** a finished photo-accurate cockpit.

## Immutable native source and private deliverable

| Provenance | N100 private relative path | SHA256 |
| --- | --- | --- |
| Original read-only OutRun 2006 F50 PMT | `rea-input/outrun/outrun2006/Cars/obj_plcar_f50_pmt.sz` | `10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab` |
| Initial direct original imported .blend | `work_handoff/ferrari16_slotC_f50_source_audit_20261108/F50_OriginalPMT_CockpitSource_v1.blend` | `d82b3d024a812126da5b38c56572cfc326fbe3d1b5c0ddf8cad4cbd855119d31` |
| Accepted original-derived input v35 | `work_handoff/ferrari16_slotC_f50_source_audit_20261108/F50_OriginalPMT_P0_DashboardSteering_v35.blend` | `0259f05b9f5b2ae3beeb25644f36de971e269b71000152fdb53d89fc7d6876ff` |
| **New original-derived editable v36** | `work_handoff/ferrari16_slotC_f50_source_audit_20261108/F50_OriginalPMT_P0_DashboardSteering_v36.blend` | **`4f232ce124caab8afca8ddfcadb6b629267730d80a58ab50a1daddbfad591b3e`** |

The new private .blend contains 1,539,760 bytes. Private original source and previously accepted v35 are immutable and separately hashed; no original game asset or private binary was committed to public GitHub.

## Physical changes in three pre-existing original cockpit mesh objects

| Blender imported original object | Before v/f → after v/f | Moved existing vertices | Max movement | Before mesh SHA256 → after mesh SHA256 |
| --- | --- | ---: | ---: | --- |
| `PMT_F50_object00_group01_material028_a0` | 5506/7552 → 5506/7552 | 849 | 0.930011 mm | `e095c91c9deba43fbc776ff481d40856ef754ee4d78736a3066f0838e7aa8612` → `37fcd0e2021dbe8f6f60085fb81f33112fbc4632db9bce2a92f0518df0a10952` |
| `PMT_F50_object21_group01_material002_a0` | 13552/26496 → 13552/26496 | 1175 | 1.180001 mm | `f17c90b11bdf696bf84092df60e480689e9844ceadd7a33d11ed326caa392d9f` → `1112af79c06918f34a1855bd9bb692bd94621f641de477fabf1a2b13010abcde` |
| `PMT_F50_object21_group00_material000_a0` | 2738/4464 → 2738/4464 | 567 | 1.18 mm | `6f637af5c8dddd3e4ec1e0d40c57beca10bc5d42cd798cd75dcb701bf8d5488c` → `9efe1af01e96fade5966b24c43637cd771e80367ea75aab26c9eb1d003becc7b` |

The original PMT IDs are the names above without the `PMT_F50_` prefix. Total **2,591 actual original-mesh vertex position changes**: dashboard/instrument visor fairing, existing original three-spoke sheet and rim fairing, existing original six-bolt hub crown. All 39 other original mesh signatures identical; object IDs, vertices/faces, UV, material, world matrices, QA camera matrices and original wheel boundary vertices unchanged. Original eight open boundary loops `[48,48,72,72,72,96,96,120]` total 624 source open edges remain open and are **not** represented as repaired topology.

## Actual Blender 4.5.15 LTS execution and independent validation

- On N100 private authorized source, official Blender 4.5.15 actually opened hashed v35, moved existing source vertices, saved distinct v36, and rendered real original F50 scene BEFORE/AFTER for instrument visor and steering/hub.
- Separate fresh Blender 4.5.15 process opened v36 → reopened v35 → reopened v36 and checked original PMT SHA, import SHA, 42 named native meshes, exact 39 unchanged, 624 source boundary edges, UV/material/camera/transform invariants. **`PASS_F50_V36_OFFICIAL_4_5_15_FRESH_PROCESS_REOPEN_RENDER`**.
- Actual private 2×2 same non-game-camera model comparison `F50_SlotC_P0_v36_REAL_ORIGINAL_BEFORE_AFTER.jpg`, SHA256 `6aaeb5fec4e3285f9ccb91f1deada8c96e2c7d80712e7be82a078d644ea12d76`, RGB max-channel delta >3: gauge 1,048 / 345,600 pixels, steering 4,425 / 345,600 pixels. These are real model renders, not imagined/photo-generated concepts.
- Source editing script committed to `tools/car_modeling/slot_c/f50_p0_source_mesh_v36.py`, private script SHA256 `da920b4d3833810f2e4c285489537b2d04825bfe956766b8fd5a39b2b79e6c06`. Report/render/source remain available in verified private N100 path; only the permitted final three deliverables (.blend, script, compare JPG) were also copied to a private restricted Drive folder with full remote-content SHA256 readback. Sharing was not modified.

## Reference checks / incomplete gates

- N100 F50 references from private `outrun2_vr_refs/20261104_16car_cockpit/MANIFEST.json` and `COVERAGE_MATRIX_16x8.csv`: existing genuine F50 interior photos, including Mecum 1995 F50 LHD_NEEDS_VISUAL_REVIEW and PistonHeads closeup with RHD side warning. F50 dedicated center shifter is the only `PASS_VISUAL` component; seven required original-model/photo-matched views not complete.
- Comparison cameras are explicitly *non-game QA cameras*; no claimed original game's precise driver-eye or steering animation rig alignment.
- Current remaining F50 hub pitting and silhouette authenticity need human photo/view QA. The inherited wheel 624 source open edges have not been healed.
- Hosted GitHub Actions uses actual official Blender 4.5.15, but no authorized private proprietary F50 .blend exists on hosted runner. **`BLOCKED_INPUT_PRIVATE_BLEND_NOT_TRANSFERRED`** for hosted real-scene F50 QA. A successful hosted smoke cannot count as an actual F50 render.
- Slot C first material start `2026-11-08T04:35:52Z` (2026-11-08 13:35:52 KST); earliest 24h budget end `2026-11-09 13:35:52 KST`, yet passage of time never auto-promotes a vehicle. Keep `ACTIVE` and `PARTIAL_NEEDS_QA`.
- **AI2 score delta +0**: same ongoing original-source F50 P0 feature, no credit for retry, new checkpoint, readback, smoke or rollover.

No PMT/OVC/OVC3 conversion or output, external body/rim/tires, new textures/PBR/normal maps, game packaging or VR/runtime edits. Never change slot A Daytona, completed Dino 246, or Model2/DX11/DX9Ex/DXVK branches.
