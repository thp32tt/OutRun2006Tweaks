# F50 SLOT=C — center console / original gear-selector knob v38 (2026-11-09)

**Scope:** only the existing genuine original OutRun 2006 F50 PMT `object20_group00_material000_a0` gear selector head. `center_console = COVERED_PARTIAL_QA` for knob only, **NOT vehicle QA PASS**. No dashboard/steering modification. The stem (`object20_group00_material001_a0`) and other **41** original scene meshes were preserved.

## Provenance
- Original game read-only `obj_plcar_f50_pmt.sz` SHA256: `10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab`.
- Original direct PMT imported private `F50_OriginalPMT_CockpitSource_v1.blend`: `d82b3d024a812126da5b38c56572cfc326fbe3d1b5c0ddf8cad4cbd855119d31`.
- **Accepted source** private v36 `F50_OriginalPMT_P0_DashboardSteering_v36.blend`: `4f232ce124caab8afca8ddfcadb6b629267730d80a58ab50a1daddbfad591b3e`.
- **New immutable editable scene** N100 `work_handoff/ferrari16_slotC_f50_source_audit_20261108/F50_OriginalPMT_CenterConsole_Shifter_v38.blend` (1,542,225 bytes): SHA256 `8e9081c15a071e2b2edde4f44dc529470ac08d9f34a8e4516a93b8926e933ec2`.
- Reproducible original-source editor: `tools/car_modeling/slot_c/f50_center_console_original_shifter_v38.py`, N100 executing copy SHA256 `06244e01854d9e2d59755bf2f1972e48aa632e15dd1d5294b2a50ef09e037d3e`; source commit `4b53fc21a42608297f001bd85e9044cd3cfbdd82`.

## Physical geometric difference
Existing native original shifter head **16 vertices / 19 faces → 103 vertices / 171 faces**, 91 vertices physically repositioned (max 8.5498 mm). Original PMT triangular/pyramidal knob was source-topology subdivided and rounded to a spherical metal shift-knob silhouette based on F50 authentic photos. Existing original source mesh name, pivot, original supporting shaft, other 41 meshes, UV/materials, camera objects unchanged. No new mesh object, procedural replacement, altered wheel/dashboard, exterior, textures/PBR, or PMT/OVC/OVC3/game export.

## Private reference and audit
N100 authentic F50 reference `03_F50/REF16_transmission_1_f25e58b6da.jpg` SHA256 `261f56618c936d9a12d39ce9b6c0709ece555f9e184793d5d45caabf44868da4` depicts rounded metal shift knob and H-pattern gate; secondary `REF5_mecum_interior_02_552c4a048.jpg` for seat/tunnel context. Rights retained as private reference; no public photo upload; exact camera/variant comparison is not final QA. Same-camera private Workbench before/after PNG: `F50_CenterConsole_Shifter_v38_BEFORE.png` SHA256 `955cd027cc124ea7582cd41e0190b583466eb66e640168ca363c25ee0d21cd5b`, AFTER SHA256 `d9935da483dd75c1e276f23a7e70543579a3b4a8457d0512c5a80426aad85ba0`.
- **Blender 4.5.15 LTS fresh-process reopen PASS**: independently reopen new v38, reopen immutable v36, compare 42 per-original-object geometry/UV/material/transforms, reopen v38 again; original shifter stem and all other 41 source meshes identical.
- **BLOCKED scope within center_console:** H-pattern metal shift gate, base plate and full tunnel panel not positively attributed to an existing original PMT submesh. No arbitrary new gate/model synthesized. Camera calibration and seven fully matched references remain external final QA blockers.

## Breadth-first disposition
`center_console=COVERED_PARTIAL_QA` (knob only, remainder source-blocked). **Next component `driver_controls`** on same F50 in SLOT C. One successful source geometry dispatch consumed, below two-turn ceiling. Remains `ACTIVE / PARTIAL_NEEDS_QA`; 24-hour assigned car start unchanged; other slots, other cars, original PMT bytes untouched. This is not whole-car acceptance and is independent of prior P0 dashboard/steering work.
