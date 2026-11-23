# EXT16-009 — actual private OVC audit, strictly historical (2026-11-24)

**Scope:** `thp32tt/OutRun2006Tweaks@automation/ferrari16-external-20261123`.
**Material code fix:** `90498aca5dea571ef98a076f3e9799928fe021dd` (not a new runtime model package).
**Input:** private **2026-11-16** dashboard test-package OVC3/4 bodies and manifests on N100, not current user install or source GLB proven for 2026-11-24. All binaries remained private and read-only.
**Outcome:** historical actual physical OVC files SHA256 match their dated manifest **16/16** (15 canonical ExternalCars sidecars + the F50 legacy root file); strict per-opaque-material PBR normal/ORM/UV/TBN/full DDS-mip gate **0/16 PASS**. The normal 16-slot preflight showed 15 FAIL + F50 MISSING canonical path; a separate exact F50 legacy-file inspection found its SHA and failed PBR, so the historical test set has 16 real **FAIL** assets, not an absent F50 binary.

## New independent source defect repair

Previous Python preflight recorded a material as UV-covered when *any one* triangle had a valid TBN basis, allowing same-material sibling triangles/meshes with degenerate UV or geometry to silently pass strict coverage. The source now marks **every** invalid opaque triangle's material and rejects partially degraded materials in `--require-pbr-maps`. It also rejects non-full-mip normal/ORM DDS only in the optional strict PBR admission gate, leaving readable/runtime-compatible DDS syntax unaffected. Positive and CRC-recomputed negative tests include mixed good/bad same-material meshes, truncated normal-map DDS, valid mapped material, and existing orphan/cross-material regressions.

GitHub source blob SHA1: `pbr_material_gate.py`=`6f1111fbe033ae75d1d23e3d46f6285e650e5073`, `verify_all_car_ovc.py`=`8f4793daf38f13dd72e52ae1d51f8d383827f43a`, `ferrari16_pbr_material_gate_test.py`=`00b449d506a7e8116459d250827c005f90eca693`.

Local isolated patched Python OVC self-test: **PASS**. GitHub exact material source SHA `90498aca...` multicar C++/Python and Windows PBR/HLSL workflow run [45290876714](https://github.com/thp32tt/OutRun2006Tweaks/actions/runs/45290876714): **SUCCESS**. Separate same-SHA Windows Win32 DLL workflow [45290876801](https://github.com/thp32tt/OutRun2006Tweaks/actions/runs/45290876801) and x86 DLL+x64 OpenXR/package workflow [45290876709](https://github.com/thp32tt/OutRun2006Tweaks/actions/runs/45290876709): check final conclusions independently; do not infer HMD success.

## Reproducible read-only dated package audit

`python3 tools/ferrari16/verify_all_car_ovc.py --game-root <PRIVATE_20261116_PACKAGE_MODEL_DIR> --require-pbr-maps --json-out <PRIVATE_QA_JSON>`

| Slot | Archived car identity (manifest only, not licensed source proof) | OVC SHA256 (matched) | Normal/ORM maps | Opaque materials missing normal/ORM | Partially bad UV materials | PBR |
|---:|---|---|---:|---:|---:|---|
| 0 | Dino 246 GTS (exact_external) | `d416ca3bdca429a1c598da2ba636ae8c7852a54cb745f0beb3aa6119447ad24b` | 14/0 | 8/21 | 12 | FAIL |
| 1 | 365 GTS/4 Daytona (exact_external) | `946f21d9bdeebb53c39a9b1042cc2128dcc9a1ff4b33c8371a1442b13c530ca4` | 4/3 | 13/14 | 13 | FAIL |
| 2 | F50 (exact_external_legacy_h3) | `52cd180f8743ae9fd7e7e4e68a39aca49ec943e29c1cf7bc0d39239cb7b66799` | 9/0 | 8/17 | 14 | FAIL |
| 3 | 360 Spider (exact_external) | `24b18e6a958004cc435334da000b9367087bd616fc4b7a83907b65e1575ea49a` | 6/0 | 15/21 | 19 | FAIL |
| 4 | F355 Spider (exact_external_private_only) | `41b4dcdaa35e240d66b3c5a2d889e321e5cef90e9e3537b80bb3a712783c4230` | 12/2 | 22/30 | 24 | FAIL |
| 5 | 575 Superamerica (external_donor_rework) | `b7cb49f17861ab0cd454f218738169b5c028dec047901e6d9380e791097577b5` | 34/13 | 7/28 | 11 | FAIL |
| 6 | Testarossa (exact_external) | `58e141a5e5627c66aca6e14557d352d08c91be1f870fe2160039ecf8a588416a` | 5/4 | 42/46 | 15 | FAIL |
| 7 | 288 GTO (exact_external) | `903a1ca9eb3fc77761c3dd1e43b6f19e10f4387796575a4db9227141b6f8682a` | 0/0 | 7/7 | 7 | FAIL |
| 8 | 328 GTS (external_donor_rework) | `a64277cdf42f02dbdc3a29c5af1cea5b2794ac01c182bf295e9b5feaea957f2e` | 1/1 | 22/23 | 15 | FAIL |
| 9 | 250 GTO (exact_external) | `fb6c3b827d6981f736f35f808c8c208bb2f4dbc36bd94a1eddd0676f84cfbb99` | 11/11 | 2/2 | 6 | FAIL |
| 10 | 512 BB (exact_external) | `10d8c5a562ce089ae3f0d1a12e75055e003b2dd076fa5cf98fcef037d611daec` | 17/1 | 15/29 | 21 | FAIL |
| 11 | F40 (exact_external) | `c15e3fb298ee9f3c4bc8c2f28dba7d1d72ae04c2b7f97277dd29c3e97f6bbeb8` | 0/0 | 28/28 | 28 | FAIL |
| 12 | 550 Barchetta (exact_external) | `17fa6bc91c8ad5b0c7d61cb5ea6cf389a97138c9443f93526a9868ca440b3d30` | 8/2 | 19/25 | 16 | FAIL |
| 13 | F430 Coupe (exact_external) | `7fbba9d121d0c3bdea74b0427abc52647189514ff2d5042560b04570bacef19a` | 16/15 | 3/3 | 11 | FAIL |
| 14 | Enzo / FX (exact_external) | `3abcb66901ad115a772085eaa8642965b931dc9576e3132e0bde3871dfdc9e26` | 13/13 | 3/3 | 11 | FAIL |
| 28 | F430 Spider (external_donor_rework) | `092a37d4f93fed45de43878698022aeb5eae263e05a59aaa6c58a7225dae26dd` | 34/19 | 15/35 | 17 | FAIL |

All 16 archived OVCs have no short mip record among *present maps*; missing maps or UV/TBN degeneration still fail. The whole OVC CRC32 and recorded SHA256 attest byte integrity, **not** semantic ORM channel packing, normal pixel correctness, wheels/interior physical fidelity, source rights, or current game install identity.

An independent *historical 2026-11-21* 575 Superamerica hybrid OVC4 (`sha256:16c15b9bd05bc69b581fa1fddda73bb7c6461ab59ff121109ae29ff30fa87e71`) also fails strict PBR: normal 16, ORM 4, eight opaque materials missing normal and 19 missing ORM, partial UV defects. This is not evidence of the 2026-11-24 active package.

**License/identity fail-closed:** archive manifest records F355 external-use restrictions; its `SourceKind` string is not proof of redistribution rights. Source GLB per-slot SHA/rights were unavailable for this exact current task; the 575M donor, 308/QV donor used for 328, and F430 Scuderia Spider 16M donor must not automatically replace higher-fidelity exact models. The 1987 Testarossa model is not documented as the authentic 1986 open-top Testarossa Spider. No binary redistributed, texture converted, quality downscale, existing model or protected v0.03 modified.

**WAIT_INPUT:** current installed/private 16 slot source+converted GLB and OVC4 SHA manifest, material IDs, albedo/normal/ORM original source (including channel mapping and DDS per-map CRC), lawful rights evidence and source-to-converted screenshots. Then run strict audit on those **current** bytes, repair only authorized broken material conversions, and retain original-game fallback for unqualified slots. Quest3/VDXR stereo, menus, performance and visual QA: **UNTESTED / WAITING_USER_HMD**.
