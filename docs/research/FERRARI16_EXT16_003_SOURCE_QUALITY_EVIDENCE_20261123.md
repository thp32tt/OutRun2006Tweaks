# EXT16-003 exact-body four-car source evidence (2026-11-23 KST)

## Scope and material source fixes

Branch: automation/ferrari16-external-20261123; input SHA cf337e2fd67a2d95dcbc367453e5d8f80446cb72.
Material code SHA 1f92f6df8627c6fc5174466436abf009ccc46474 (installed corrupt optional dashboard must FAIL, not PASS).
Quality gate SHA 7f9317ba49ba4852954e3d23c4ae6bb239254473 (offline exact body/roof, private source GLB SHA, converted GLB SHA, OVC4 SHA, rights, previews, triangle and embedded texture resolution checks).
Regressions: tests/ferrari16_overlay_status_test.py and tests/ferrari16_exact_variant_quality_gate_test.py, both positive and deliberate CRC/roof/license/SHA/geometry/texture regression examples; GitHub action Ferrari16 run 45196925338 SUCCESS for this exact source SHA, both multicar and D3DCompiler HLSL.

The executable source gate is:
`python3 tools/ferrari16/exact_variant_quality_gate.py --manifest "PRIVATE_MANIFEST.json" --json-out "PRIVATE_REPORT.json"`

The private manifest schema is enforced in the dedicated tests and the gate itself. A synthetic PASS proves the gate's control flow only; it does NOT certify any private real model's body or copyright rights. SHA matches protect against substituting assets after review, not against false human attestations. Even PASS_STATIC_SOURCE_ONLY remains subordinate to Windows binary, manual game/Quest3 HMD, and rights decisions.

## Required reference bodies

| Game canonical ID | Exact body target | Reject |
| --- | --- | --- |
| 08 | 328 GTS, removable targa roof | 328 GTB full coupe; renamed body |
| 05 | 575 Superamerica, pivoting Revocromico glass roof | 575M Maranello fixed roof masquerading as Superamerica |
| 28 | F430 Spider, electrically folding fabric roof | F430 Coupe body with missing roof |
| 06 | 1986 Ferrari Testarossa Spider, Gianni Agnelli one-off chassis 62897, open top | production Testarossa coupe (or unrelated 849 Testarossa Spider) |

Vehicle configuration evidence (NOT a license to use 3D content):
- 328 GTS removable targa: https://rmsothebys.com/auctions/pa22/lots/r0054-1987-ferrari-328-gts/
- 575 Superamerica Revocromico rotating roof: https://www.mecum.com/lots/381133/2005-ferrari-575-superamerica/ and owner manual description https://www.easymanua.ls/ferrari/575m-superamerica/manual?p=88
- F430 Spider fabric soft top: https://www.caranddriver.com/reviews/a18202471/ferrari-f430-spider-first-drive-review/
- 1986 Testarossa Spider factory one-off: https://cdn.ferrari.com/cms/network/media/pdf/cs_mostra_gianni_agnelli_gbr.pdf and chassis reference https://www.artcurial.com/en/sales/2877/lots/116-a

## Current gates and blockers

No current **owner-private** source GLB/converted GLB/OVC4/rights record/source+converted screenshot SHA was supplied or validated for any of the four in this run; previous low-detail exact candidates are NOT promoted. Exact-shape proof and any source license/redistribution consent remain unverified. No third-party binaries or original game files shipped to public Git. Existing 13 nominally high-quality variants were not re-certified in this run.
No claim for normal/ORM display, physical stereo, glass, game menu focus, frames-per-second or in-game dashboard parity: Quest 3 user-only physical testing stays UNTESTED. Windows Win32 Build 45196924796 must be read on its final exact-SHA state; no x64 host gate established at the moment of recording. Protected v0.03 source untouched.

Status: BLOCKED (material code delivered and source-only CI PASS; real licensed assets and full binary/HMD evidence absent). Queue proceeds to independent EXT16-004; prior EXT16-001/002 are not falsely re-scored or completed.
