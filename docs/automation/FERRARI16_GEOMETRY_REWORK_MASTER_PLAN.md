# OutRun 2006 Ferrari cockpit-only geometric rework, dual-slot 24h SSOT
Updated: 2026-11-08 KST, operator override (supersedes earlier all-car exterior geometry scope).
Source: `thp32tt/OutRun2006Tweaks@feature/ferrari16-geometry-rework-20261108`.
Queue: `docs/automation/FERRARI16_GEOMETRY_QUEUE.json` (schema v2); gate: `tools/car_modeling/queue_guard.py`.
Controller: `thp32tt/OutRun2006Tweaks@chat-controller-downloads`.
Owner: AI 2 ChatGPT2. This is modeling only; Model2VR, DX11, DX9Ex, DXVK, UW2, localization and game/VR runtime branches must not change.

## 2026-11-09 V3 operator correction — no all-day steering-wheel loop

NEW authoritative strategy: [FERRARI16_BREADTH_FIRST_STRATEGY.md](FERRARI16_BREADTH_FIRST_STRATEGY.md). It supersedes old hour 4–12 dashboard and 12–19 wheel time allocations. Previous repeated exact-original-PMT/source-backed Daytona R41 and F50 v36 P0 edits are preserved; they are no longer the automatic next task.

**Coverage-first rule:** Each 30-minute slot dispatch must target the next unfinished driver-visible region, with no more than two sent messages per part. New sequence: center console -> driver controls -> inner door -> windshield/A-pillar -> visible seat -> instrument cluster -> whole dashboard review -> explicit steering defect only -> whole cockpit QA. Both A and C start at center console as of this policy (not from an invented new model). P0 dashboard/wheel are withheld from new cosmetic iterations until other visible cockpit areas receive actual original mesh edits or evidence-backed blockers.

The **same car still owns 24 hours**, but 24h is a scheduling budget, NOT a demand to iterate a single part for 24h. Checkpoint each part once; commit authentic shape changes and record its evidence independently in its own workpack. Missing final 7-photo views or confidential hosted-Blender transfer does not justify an endless spoke/rim/hood modification cycle. No photos/mesh original => BLOCKED_INPUT, no invented substitute. No OVC3, game, textures, exterior.

Original source SHA, private .blend SHA and past reports must remain auditable; the large pre-V3 historical notes have been archived separately from the short queue. Material QA remains required before car advance, but **interim COVERED_PARTIAL_QA allows progressing to the NEXT COMPONENT on the SAME CAR**. Do not conflate a part-level progress mark with final whole-car acceptance.

## 2026-11-08 12:25 KST operator override: ORIGINAL GAME RESOURCE IN-PLACE BLENDER REWORK ONLY

**Every vehicle must begin from its actual OutRun 2006 game resource**—the original vehicle's PMT/native asset and a verified Blender import or a proven editable .blend derived from it. Work in a COPIED private baseline, never replace the read-only original game file. Do NOT create a new car from scratch, procedurally reconstruct an unrelated substitute car, import a third-party GLB as the new car, or count a Blender cube/test primitive as a vehicle.

The requested work is **editing the existing original imported cockpit mesh in Blender**, retaining source object identities, vehicle coordinates, camera transforms, steering/animation pivots and source-to-output SHA256 provenance. Directly refine the existing dashboard, wheel and driver-visible parts by vertex/face/edge-loop editing, bevel/subdivision/mesh refinement and accurately photo-guided additions *attached to the existing original cockpit objects*. A small detail such as gauge bezels may have added geometry, but it must demonstrably refine the original source mesh, not replace it with an invented complete cockpit.

**Deliverables are ONLY editable Blender modeling artifacts (.blend), non-proprietary Blender editing scripts and private before/after model renders.** Explicitly **do not export or convert to OVC3, OVC, PMT or game-playable formats; do not package/install into game; do not modify VR rendering code or perform integration/testing for this task**. The previous plan's "game-compatible export"/"original game runtime" language, if any, is superseded by this rule. Invariant: original game assets untouched; model edits saved separately.

Required source evidence per car before genuine modeling credit:
1. Exact original game car/resource filename, protected private source file SHA256 and exact model/variant identity.
2. Hash of the initial imported original resource-backed .blend, plus names/IDs of imported **original mesh objects**.
3. Edited original mesh object IDs and their before/after vertex/face metrics. Record independent Blender reopen and compare with the original model using matching driver-eye camera.
4. If source resource or verified import is unavailable, report **BLOCKED_INPUT**. Do not solve that by building a new replica from photos or stock models.

Verified local baseline available: N100 \`work_handoff/daytona365_v822_ai2_20261108/blender_v8/Daytona365_Cockpit_Blender_PBR_v8_22_r2.blend\` SHA256 \`30ddcbd01ef7e969bb1e4220ff4318c2f75b7fd7ab70bc4d6dafedcdc7954437\`; this is an **existing editable derivative** with a recorded Blender build, NOT independent proof of which original game PMT resource imported into the very first version. Audit that lineage first, then continue editing this existing scene without redoing v8 geometry or textures. For F50 and future cars, verify the original native asset on N100/private storage and build a genuine import baseline before opening a modeling session. Never claim missing F50 original input was found.

## 2026-11-08 user directions — priority
**Only model 3D structures actually visible from the original game's cockpit/driver-seat camera.**
External wheels, tires, body/silhouette, bumper, spoiler, hood surface unrelated to windshield visibility, suspension, exhaust, and outside-camera cosmetics are all **excluded**. A-pillar, windshield surround, inner mirror, inside-visible hood edge and windshield base may be revised only if clearly visible from cockpit. Do not invent an entire exterior.
**P0 = dashboard and steering wheel (both).** Specifically prioritize authentic instrument binnacle, dashboard upper/lower silhouette, gauge bezels and recesses, air vents, switch faces, steering rim sections, spoke count/shape, hub, column, stalks and spatial position. Next P1 = center console/shifter/handbrake/visible pedals. Then P2 = door tops/inner panels, seats, windscreen pillars and cockpit-visible mirrors. Maintain original game's camera mount, VR eye transform, steering animation pivot and vehicle local scale.
**Only geometric mesh improvements**: topology, bevels, sculpted contours, real thickness, edge loops and shading/face normals. Existing UVs/textures are preserved as baseline but no new DDS, texture, normal map, PBR or ORM creation/baking. Preserve read-only original game PMT; save modified imported mesh to a separate .blend. Material color changes and repeated renders are not a substitute for real geometric modifications.

## Two independent automatic slots, staggered exactly as requested
| Slot | KST trigger minutes | First dedicated 24h vehicle | Next new work |
|---|---|---|---|
| A | every hour `:00`, `:30` | Ferrari 365 GTS/4 Daytona (continue true v8.22-r2 source) | next PENDING |
| C | every hour `:15`, `:45` | Ferrari F50 | next PENDING |

- User-confirmed completed #2 **Dino 246 GTS** has `SKIPPED_DONE_BY_USER` status; never redo it or award a new score merely because of this skip. The inventory retains all 16 rows, but **15 rework candidates remain**, initially two in parallel.
- Each car has its **own 24-hour allocation from its first new material geometry source commit**. One schedule tick only starts/continues work and can take less than 30 minutes; it must not claim 24h of continuous machine work. A 60-minute chat lifetime can rotate without changing car ownership/time window.
- All chat sessions must retrieve *fresh* GitHub HEAD and JSON queue on every start, identify only `active_by_slot[slot]`, and never accidentally take the other slot's car. Each slot's ongoing private .blend folder and script prefix are unique to the car. Shared Git branch commits must be fast-forward/optimistic SHA safe and avoid overwriting the other slot's queue or files.
- Do not unlock next car **just because time elapsed**. When the 24h window expires, if real cockpit geometry + photo + Blender saved/fresh-reopened and P0 dashboard/steering quality gates fail, keep the car assigned and mark blocked or needs-rework. Never silently skip a PENDING car.
- Only a genuine independent source geometry improvement may earn a newly adjudicated AI point; failed CI, retries, same SHA or a simple schedule tick are not separate achievements. Always verify `AI_SCOREBOARD.md` SSOT before any score change.

## Actual photos already gathered (verified N100 file system, not uploaded publicly)
Reference library: `/home/chatgpt-runner/outrun2_vr_refs/20261104_16car_cockpit`.
- `MANIFEST.json`: URL, source/license, SHA256, exact/analogous variant status.
- `SOURCES.csv`: source index.
- `COVERAGE_MATRIX_16x8.csv`: 8 interior parts per 16 cars.
- `CONTACT_SHEET_ALL_221.jpg` and `CONTACT_SHEET_BEST_OF_16_FINAL.jpg`: private contact sheets.
- `02_365_GTS4_Daytona/`: Daytona photos; `03_F50/`: F50 photos; subsequent numbered car directories are the queue per-car photo subdirectories.
- Files are research material only; never commit copyright photos/PMT/OVC/game executables or .blend containing proprietary original models into public GitHub.
- Existing reference library records **221 photographs** but not every photo/angle is verified. Validate photo car/year/roadster vs coupe and LHD vs RHD, and do not map wrong car/trim to target geometry. Photographs of 365 GTB/4 coupe must not be treated uncritically as actual 365 GTS/4 spider. Same for Ferrari 512 BB vs BBi and F430 vs Spider.
- Missing essential reference -> keep `UNTESTED` and select a valid existing reference or authorized new research; never fabricate viewpoint details, image provenance, dimensions or triangulation.

## Vehicle phase budget V3 (24h dedicated target, not 24h CPU guarantee)
| Target hours | Work |
|---|---|
| 0–2 | Original game resource/photo/driver-eye baseline; immutable private import SHA |
| 2–4 | Dashboard meaningful geometry pass, no excessive tiny resculpting |
| 4–6 | Steering meaningful geometry pass, no repeated micro-polish |
| 6–14 | **Broad cockpit coverage** — console, controls, door, windshield, visible seats, gauges; each max two 30m dispatch turns |
| 14–18 | Reconcile silhouette/photo differences from driver seat, fix largest distinct missing area |
| 18–21 | Private actual Blender save/reopen, source derived before/after and coverage reports |
| 21–24 | Final targeted visible-defect corrections and QA, unresolved blocking evidence recorded |

For cars already deep into dashboard/steering (Daytona R41 and F50 v36), skip the old first-pass timeblocks; **start console immediately**. Report \`COVERED_PARTIAL_QA\` only after real source-mesh checkpoint and independent Blender reopen. Never use insufficient full QA as excuse to repeat wheel work, and never claim that interim coverage completes the car.

## Blender and validation environment
The existing `.github/workflows/ferrari-geometry-blender.yml` installs official Blender 4.5.15 LTS in a fresh GitHub-hosted VM; verified smoke run 42441624991 only proves the toolchain. Hosted VM does not contain N100 private photos or original game meshes automatically.
- Real-scene audit requires a permission-cleared source scene (or secure private transfer) and must explicitly validate loading/saving/fresh reopening of modified Blender scene plus actual view outputs. Never label smoke cube rendered views as a Ferrari or claim production improvement based on CI source tests.
- Model edits should be independent public Blender Python geometry scripts committed to the correct feature branch. Proprietary editable .blend files remain under private authorized storage with SHA256 provenance, immutable versioned backups. Prefer GitHub Actions for Blender CPU QA; N100 is only for light photo/asset lookup, verification and necessary transfer.
- Important caveat: GitHub Actions hosted runners are ephemeral; do not infer that 24h equals one uninterrupted 24h VM. Keep short jobs, stable checkpoints, and track actual elapsed work.

## Cockpit-only quality gate
A vehicle can progress to `COMPLETE` only if all are evidenced:
- Fresh, materially different original/source vs candidate geometry, versioned private Blender scene SHA256 and two useful material geometry commits.
- Exact same original camera & asset-space transforms preserved. Driver-eye field-of-view check, cockpit clipping/occlusion, steering pivot and gauge readability from normal seated position.
- **Dashboard and steering wheel both PASS** with human-auditable original-vs-new mesh screenshot and authentic car reference comparisons. Do not award PASS from source code or generated concept imagery alone.
- Driver-eye, full dashboard, steering, instrument cluster, center console, inner door, windshield frame: seven authentic photo reference URLs and seven actual Blender comparison views, with camera orientation/provenance explicitly labeled.
- Official Blender real-scene QA and independent save/reopen PASS. Mesh counts, normals, non-manifold findings, camera/position/original anchors and before/after SHA reported.
- No exterior/body/wheel work, no new textures/PBR/normal maps and no original game/runtime source branch changes.
- Game conversion/OVC3 packaging/runtime integration and Quest 3 validation are **NOT REQUESTED** for this modeling-only phase; do not spend time or CI on them. Historical runtime outcomes remain unchanged.

## Controller and deployment
- Controller Compose: `tools/chat-controller/v0.4/docker-compose.portainer-vr.yml` in `chat-controller-downloads`.
- Only A and C **car geometry** are enabled. A uses `CAR_MODEL_SCHEDULE_MINUTES=0,30`, C uses `CAR_MODEL_C_SCHEDULE_MINUTES=15,45`. `CONVERSION_ONLY_SLOT` must be empty to allow both; all legacy conversion lanes remain independently disabled. `MODEL2_AUTODEV_ENABLED=false`.
- Slots are isolated by `car_model_simple_A` and `car_model_simple_C` in persistent queue state and their own ChatGPT tabs; both use OutRun project, no Model2 project URL. Do not delete old Model2 conversations/state.
- Portainer Pull & redeploy (rebuild image) required to apply code; Git commits do not prove live N100 container transition. Preserve volumes and Chrome login.
