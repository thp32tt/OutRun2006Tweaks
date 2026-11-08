# Ferrari F50 slot C — original PMT cockpit v32 source-mesh rework (2026-11-09 KST)

**Status: F50 ACTIVE / PARTIAL_NEEDS_QA.** Only `active_by_slot.C=f50` changed. This is another verified local edit of already imported **actual OutRun 2006 F50 native** cockpit geometry, **not vehicle completion**, not the next car and not a PMT/OVC/OVC3 export. Slot A Daytona, user-completed Dino 246, Model2, VR, game source, outside body, tires, material/texture/normal/PBR remain untouched.

## Private read-only source and immutable edit parent

| Record | Private location relative to `/home/chatgpt-runner` | SHA256 |
| --- | --- | --- |
| OutRun 2006 original native Ferrari F50 compressed PMT (read-only) | `rea-input/outrun/outrun2006/Cars/obj_plcar_f50_pmt.sz` | `10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab` |
| Original PMT-derived imported editable Blender baseline | `work_handoff/ferrari16_slotC_f50_source_audit_20261108/F50_OriginalPMT_CockpitSource_v1.blend` | `d82b3d024a812126da5b38c56572cfc326fbe3d1b5c0ddf8cad4cbd855119d31` |
| Accepted immutable prior F50 cockpit scene | `work_handoff/ferrari16_slotC_f50_source_audit_20261108/F50_OriginalPMT_P0_DashboardSteering_v31_r2.blend` | `b0d70a7a984098ede5be9494e62a227aa989fe4ccacd6cdd0b9f013cbfa15814` |
| **New editable output v32** | `work_handoff/ferrari16_slotC_f50_source_audit_20261108/F50_OriginalPMT_P0_DashboardSteering_v32.blend` | **`16e2a9e17d83b8e77dd9c2636aeab8bfb60b19b850926f1641b26947382df193`** |

Private output size: **1,540,061 bytes**. Three source hash guards passed before build and again during fresh-process audit; original source input unchanged. No licensed original asset in public GitHub. Public non-proprietary edit script `tools/car_modeling/slot_c/f50_p0_source_mesh_v32.py` local SHA256 `9f8849b272f3c35d4a938e3890166d84d7186edeaac673f8d80bea1894fc190a`; material commit `6147b504694862eee762d98960b6e0a4140db589`. Script imports existing public v31-r2 helper, requires official Blender 4.5.15 and exact input SHA; it refuses any overwritten output.

## Proven original object IDs and geometrical delta

All changes are confined to **existing mesh vertex coordinates** in exactly three original PMT-imported objects. Source object names, transforms, 42 original mesh identities, indices/topology, UV and material slots, camera metadata and original steering pivot preserved; 39 other original meshes have unchanged SHA. No new geometry object was created.

| Native imported mesh ID | Vertices/faces before→after | Moved existing vertices | Max move | Per-mesh geometry SHA256 before→after |
| --- | --- | ---: | ---: | --- |
| `PMT_F50_object00_group01_material028_a0` (instrument hood) | 5506/7552 → 5506/7552 | **1,138** | 1.200020 mm | `0b7fcfb54288fb1e577fc872c6fe1f315fa340cb2d237547c00f177b824c141c` → `133a00c89864613ba299ab39dd39c2d6dff422af07b551389fc393bd75995436` |
| `PMT_F50_object21_group01_material002_a0` (actual 3-spoke wheel rim) | 13552/26496 → 13552/26496 | **6,098** | 1.505360 mm | `12145eaf2b444b504047c0b632436ac54b562d2b682e37db128f9269b79d9200` → `d3afbebcd59d994418db21ee4a045b7f718333f0ede5bc7538f2714552741444` |
| `PMT_F50_object21_group00_material000_a0` (original six-bolt hub plate) | 2738/4464 → 2738/4464 | **595** | 1.591691 mm | `b15e7e8756a3f9bf174e4945897ed343f9f51ad942a2dcaa839d72b3f0b33b68` → `618d3ed1f513b1bed124a5dc684e674ea98f5d3c0d13e5352d617a41df0919a8` |

Total **7,831** existing original imported vertices moved. Hood XY original silhouette retained, with original shoulder surface locally faired. Ring original handgrip contours and upper arc smoothing protect existing open/nonmanifold boundary vertices and three native spoke root regions. Original six-bolt plate center-badge and bolt islands masked while fairing local faces. This is visual surface improvement only: **624 inherited nonmanifold/open steering edges still exist**. Spoke-to-rim structural closure is **not proven**, and should not be described as repaired.

## Real native Blender validation and photographs

Official Linux **Blender 4.5.15 LTS** opened the genuine v31-r2 source, saved v32, and an **independent second Blender process** reopened `v32 → v31-r2 → v32`, asserting exact 42 source mesh identities, changed object SHA, 39 untouched objects and unchanged camera matrices; it rendered an actual wheel image. Receipt `F50_SlotC_P0_v32_Independent_Reopen_Audit.json`: `PASS_REAL_F50_V32_BLENDER_4_5_15_FRESH_PROCESS_REOPEN_AND_RENDER`. Fresh independent wheel render SHA256 `991c69e95b26540f2ab692a67726b2751392cfd1746bd160fa87769d9fae5c07`.

Genuine **before/after original-model** matched diagnostic camera 2×2 JPEG `F50_SlotC_P0_v32_ORIGINAL_BEFORE_AFTER.jpg`, SHA256 `2897eb0628c1eeebd5aca7c26f01383a8777ce35ab10002a3b4cb1cbb4514b68`. 800×560 Workbench views per subject; changed pixels at RGB delta >3 are **2,449 (gauge)** and **15,983 (steering)**. These are geometrical difference measurements, not automatically human-approved realistic fidelity.

Private authentic F50 photo library at `/home/chatgpt-runner/outrun2_vr_refs/20261104_16car_cockpit/` independently parsed. `MANIFEST.json` SHA `a4645b3bcc98443026951f4aba845bd8561aad85b8cd58a8c289be02d194225e` includes 17 F50 records, 16 marked downloaded. `COVERAGE_MATRIX_16x8.csv` SHA `1f16c1dddbd436954fdfc486807382ad75a97adc0fe3c70f902d9c3307cfaac3`: only F50 center shifter marked `PASS_VISUAL`; other seven category validations remain untested. Examples of actual F50 steering/dashboard source imagery: [PistonHeads F50 dashboard](https://www.pistonheads.com/news/ph-ferrari/ferrari-embarks-on-f50-30th-anniversary-tour/49812), [Mecum F50 interior](https://www.mecum.com/lots/1158440/1995-ferrari-f50/). Photos are **not** redistributed.

**Still blocked:** GitHub-hosted official Blender workflow has **not** securely received the proprietary source-derived F50 `.blend`. Hosted smoke-only CI, if successful, must not be represented as a real original-F50 validation. Exact game-driver-eye camera/FOV, calibrated seven photo/model view matching, inherited 624 nonmanifold wheel edges, final P0 shape approval and full quality acceptance remain incomplete. Slot C stays F50 / ACTIVE / PARTIAL_NEEDS_QA and does not advance even if the 24-hour window has elapsed.

**AI2 score delta: +0.** This is continuing work on the same F50 feature, not a separately scored achievement. No duplicate points for a new checkpoint, CI, render, fresh open or re-report.
