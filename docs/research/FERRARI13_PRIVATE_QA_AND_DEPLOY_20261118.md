# Ferrari13 exact-source private standalone test package — 2026-11-18 KST

## Completion and correctness boundary

The thirteen Ferrari body files classified exact in the previously available Ferrari16 source package are now built into a **standalone private test ZIP** with 13 paired speed/RPM/gear dashboard overlay files and a Windows integrated V4 runtime. Static validation is completed. **Actual Quest3 / game visual completion is NOT proven**. The source for the Testarossa is a 1987 road Testarossa, so open-roof Spider body identity is not established.

Original Ferrari16 donors for 575 Superamerica (575M), 328 GTS (308), and F430 Spider (16M) are intentionally excluded from this test package and not modified.

## Verified original private data

- N100 audited actual 13 body OVCs + 13 overlays read-only using tools/car_importer/ferrari16_hq_batch/tools/qa_ferrari13_exact.py.
- Checks: size and SHA256, OVC3/H4 signature, CRC32, geometry group/vertex/triangle totals, material/PBR, DDS bounds/mip formats, speed/RPM/gear overlay bindings, GPU memory cap, 30 retail alias IDs.
- F50 dedicated F50_HQ and F50_GLASS group names explicitly supported instead of generic model names.
- Total result: 13/13 body PASS; 13/13 dashboard overlay PASS; 30/30 retail aliases validated.

| Car ID | Car | Body triangles | Normal-map materials | Dash animation |
|---:|---|---:|---:|---|
| 0 | Dino 246 GTS | 51,091 | 14 | Separate live overlay |
| 1 | 365 GTS/4 Daytona | 49,222 | 4 | Separate live overlay |
| 2 | Ferrari F50 | 218,664 | 9 | Separate live overlay |
| 3 | Ferrari 360 Spider | 123,998 | 6 | Separate live overlay |
| 4 | Ferrari F355 Spider | 444,977 | 12 | V4 native speed/RPM |
| 6 | Ferrari Testarossa | 173,584 | 5 | Separate live overlay |
| 7 | Ferrari 288 GTO | 52,528 | 0 | Separate live overlay |
| 9 | Ferrari 250 GTO | 72,500 | 11 | Separate live overlay |
| 10 | Ferrari 512 BB | 265,611 | 48 | V4 native speed/RPM |
| 11 | Ferrari F40 | 171,765 | 0 | Separate live overlay |
| 12 | Ferrari 550 Barchetta | 154,980 | 8 | Separate live overlay |
| 13 | Ferrari F430 Coupe | 87,138 | 16 | Separate live overlay |
| 14 | Ferrari Enzo | 86,747 | 13 | Separate live overlay |

Two models already contain actual OVC4 native bound speed/RPM meshes: Ferrari F355 Spider (ID 4; 444,977 triangles), Ferrari 512 BB (ID 10; 265,611 triangles). The remaining eleven use separate dashboard overlays with live telemetry; their per-car placement has not been confirmed in VR.

**Known quality gaps:** Ferrari 288 GTO and F40 bodies both have 0 normal-map materials. Do not claim high-quality normals or actual Quest3 rendering for those cars. Testarossa Spider body identity must also be checked against an actual screenshot.

## Completed private ZIP artifact

- Filename: FERRARI13_EXACT_V4_COCKPIT_PRIVATE_20261118.zip
- Uncompressed ZIP_STORED model layout; ZIP size: 600257798 bytes, ZIP SHA256: eb02321c05367ea332a42f205c83e08f12fb69ff5bf1f67f7e689302b73f222c
- Container zip integrity: zipfile.testzip() 39/39 members PASS. 30 installer assets including 13 body + 13 overlay + dinput8.dll + host + two optional configuration defaults.
- Integrated DLL SHA256: 313d9925b48fab98dbe2445201cfc54a1e2a05ab34fb940b6bc3761c94e97a4e, source commit d140f6c05ed4d83aed914f223dc46788248cfaef. Older Windows Build 44276896969 SUCCESS; HUD Inspector CI 44276897265 SUCCESS.
- Uploaded to **private owner-only Google Drive** (not in public GitHub). Third-party vehicle redistribution rights not verified. Do not redistribute.
- Windows installer verifies hashes before modifying the game, backs up any existing target, preserves installed settings, and provides explicit restore; does not include or modify original OR2006C2C.EXE.
- GitHub Actions Windows PowerShell syntax and 30-file mock install/backup/rollback workflow **44302240641 SUCCESS**, workflow code commit 437ab633d46a842a5ddf76eae327e11a709346d9. Mock executable confirmed unchanged. Actual game launch was not covered.

## Next steps

1. Quest 3 driver-eye QA on these thirteen; validate every car camera/seat, cockpit gauge placement, texture normals, no road penetration and wheel motion.
2. Prioritize authentic normal maps for F40 and 288 GTO; do not silently invent source texture detail or decimate geometry.
3. Verify open roof / Spider body identity for Testarossa; preserve package until confirmed.
4. Source high-quality exact 328 GTS, Superamerica and F430 Spider, with valid private conversion rights. Paid sources cannot be automatically purchased.
5. Treat rechecking/retelling this exact ZIP as +0 AI score; no repeated scoring for F355/512 previously scored conversions.
