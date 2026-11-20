# Ferrari 575 Superamerica exact-body + HQ 575M dial-cluster optional hybrid — 2026-11-21 KST

## Scope, provenance, privacy

This is an **actual newly created, offline-validated private model candidate**, not another URL-only source search and **not a default vehicle promotion**.

- Base exact body: retained Assetto Garage Ferrari 575 Superamerica native-needle GLB, SHA256 `07ba422ae28628fb14244cd2bc68ed40c4f022c173c46c2ed799bc2aaddff2b1`, 51,444 triangles. It retains the correct Superamerica body variant and two dynamic gauge nodes.
- Interior gauge donor: retained higher-density Ferrari 575M cockpit GLB, SHA256 `d2d90ff8d44a7dfc146390ebc3a279ce8227a3ac950bce09cb764b9373086f96` (200,069 imported face triangles). This is **not** the Superamerica exterior; only the dial-surface subset was transplanted.
- Rights: original third-party cross-game redistribution permission not established. **No vehicle binaries committed to GitHub.** Owner-private ZIP stored in the previously used private Drive test folder, no public sharing.
- Normal/non-model VR and Ferrari13 default packages were not modified. Driver-eye actual Quest 3/gameplay still pending.

## New real modeling / Blender stage

1. Imported both private source GLBs with Blender **5.2.4** at 1 CPU thread. 575M native gauge materials selected exclusively: material **32 = 6,074** triangles, **28 = 178**, **29 = 178**; the resulting donor gauge surface is a **new 6,430-triangle mesh** with 7,604 imported vertices, preserving source UV/material references and never using decimate.
2. Corrected donor-vs-exact model forward-axis disagreement: rotated donor gauge 180° about Blender Z. Aligned initial gauge anchor to the exact source speed/RPM pivot mean. A separate visual-comparison adjustment applied **-0.067 m Blender X**, final translation `[-0.02065852098,-0.16986228526,0.44207516313]`; this is **static-provisional**, not calibrated in game.
3. Removed **only** the original 575 exact static gauge-glass and gauge-face mesh nodes `ferrari_sa_gaugeglass_cpit.001`, `ferrari_sa_gauges_cpit_SUB0`, `ferrari_sa_gauges_cpit_SUB1`, leaving exterior, cockpit, steering, wheels and unique `ARROW_SPEED`/`ARROW_RPM` nodes. New Blender checkpoint SHA256 `1ee2a6e9b89a2b0afbadcbe1c31172a8e78be9356e935eca1b716b42c1ea3560`.
4. Blender exported separate **4,442,324-byte** private hybrid GLB SHA256 `4f946c560f25294337da91585cad8b1df64a883ad842bcfb646504d7468e5c2b`.
5. Converter strict PBR gate initially **BLOCKED**, not concealed: donor `Material_28` normal strength **3** exceeds native maximum **2**, and original `ferrari_sa_windows` roughness `0.0399999991059` missed the minimum `0.04` due float precision. GLB **JSON material factors only** amended 3→2 and near-0.04→0.04, with BIN chunk SHA unchanged (geometry, images and texture bytes untouched); distinct final native-ready GLB **4,442,312 bytes** SHA256 `f84d3e8a9a0ffe5a6e6a8513e2b4b57437fe6cef760f04b0e3a38e17ed2768a1`. The editable .blend checkpoint predates these two JSON-only bounds adjustments.

## Independent artifact verification and actual converter output

| Check | Exact result |
|---|---|
| Raw GLB structural independent parser | **PASS**: 76 meshes, 137 nodes, 57,786 indexed triangles, 30 materials, 47 images, 52 textures, 0 missing UV, 0 missing normals |
| Needle source nodes | Unique `ARROW_SPEED` and `ARROW_RPM` each once |
| Existing Ferrari V4 batch converter | `audit --strict` **PASS**; `convert` **PASS** after explicit PBR-factor repair; `verify` **PASS** |
| OVRCABH4 native output | **57,786 triangles**, **64,392 vertices**, **78 groups**, **30 materials**, 16 normal-mapped materials, 1,307 glass triangles |
| Native dial binding | 2 (speed & RPM), unique mesh group IDs, finite axis, speed/RPM input mapping provisional |
| Independent OVC parser | **PASS**: header V4, matching counts, complete DDS / `OVCPBR3!` / `OVCDASH4`, CRC32, bounded material factors, all bytes consumed, 0 trailing |
| New OVC filename | `575superamerica_External_Test.ovc` |
| Native OVC SHA256 | `16c15b9bd05bc69b581fa1fddda73bb7c6461ab59ff121109ae29ff30fa87e71` |
| Native OVC bytes | **8,194,803** |
| Private source and editable package | ZIP **13,966,081** bytes SHA256 `10d2a919678a4c618b8a8b128fc91b7c637614d3218fa0a98ced6a0027e6028e`, 11 members, ZIP CRC PASS |
| Private upload | Owner-only Google Drive folder `OutRun2006_Private_Model_Tests`, remote size verified, **not publicly shared** |

Private ZIP includes OVC plus native-ready GLB, editable Blender checkpoint, verification reports, and optional PowerShell installer with **verify-only default**. Installation requires both `-Install` and `-AllowExperimental`, validates source SHA, saves unique previous-OVC backup and has hash-guarded rollback. No game DLL/host/EXE is included or changed.

## Critical visual quality blockers

- Four 768×512 Blender Workbench static views and an additional higher-eye view were generated. Isolated donor cluster showed dial faces and the two color-highlighted exact needle meshes after lateral alignment.
- However, whole-cockpit Workbench views show the instrument cluster **heavily obscured by foreground cockpit/steering geometry**. Workbench may display transparent gauges/glass opaquely; therefore these images cannot establish a real Quest3 view, absence of occlusion, or usable speed/RPM animations.
- No user-facing default install promotion; no 16/16 **high-quality exact default** claim. The old 575M donor still carries ~200,071 triangles vs this **57,786-triangle** new exact variant, so full-body geometric quality superiority is **not** proven.
- **Next**: investigate ray-cast/material visibility at actual game seat eye; confirm native speed/RPM dial sweep direction/angles and windshield/roof, then physical Quest3 screenshots. 328 GTS and F430 Spider high-quality exact defaults remain pending better authorized source files.

## SSOT / scoring

**Unique RUN_KEY:** `FERRARI575-EXACT-HQCLUSTER-HYBRID-OVC4-20261121-16C15B9B`. Distinct from previously scored exact 575 UV repair and native needles. This pass newly produced a donor+exact mesh hybrid, native PBR-bounded GLB, independent OVC4 parser PASS, private auditable install/rollback package and Drive owner-only upload. Later retests/ZIP re-uploads/verification do **not** re-score the same achievement.

AI2 scoreboard is updated separately after reading current `thp32tt/ai-dev-lab@main/AI_SCOREBOARD.md` SSOT. Never infer score from this report alone.
