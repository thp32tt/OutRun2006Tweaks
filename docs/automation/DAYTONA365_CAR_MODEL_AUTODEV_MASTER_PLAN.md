# Daytona 365 GTS/4 — Blender vehicle-model improvement (automation SSOT)

Updated: 2026-11-08 KST (v8.6 measured geometry/UV/PBR handoff). Owner: OutRun Chat Controller slot **A** (not legacy DX11).
Repository: `thp32tt/OutRun2006Tweaks`.
Production branch: `feature/daytona365-blender-v8-20261108`.
Never edit `vr-dx11-native-r71`, `vr-d3d9ex-focus`, `Model2VR-tools`, localization, UW2 or the original game files.

## User goal
Keep improving the **second Ferrari, 365 GTS/4 Daytona**, not Dino 246. Match the reference appearance as closely as practical using actual Blender geometry and PBR textures/normal maps. Compare **actual original-game-derived geometry renders** against **actual new Blender Cycles renders**, both from measured source assets, with consistent camera, lighting and framing. Image-generation illustrations are not evidence of a rendered game model. Do not claim in-game integration, OVC conversion, or Quest 3 validation without those actual steps.

## Verified handoff at the time this plan was created
- The N100 source workspace is `/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/` (private assets stay there).
- Latest verified private Blender baseline: `blender_v8/Daytona365_Cockpit_Blender_PBR_v8_6.blend` (SHA-256 `cb0eba836a69b3154012bd755fafac92b92b223be0e9394a876c322123e1f2f4`), `DAYTONA_V8_6_VERIFIED.json`, `Daytona365_v8_6_ACTUAL_CYCLES_PREVIEW.png`, and the actual original PMT/v8.5/v8.6 three-way preview comparison.
- GitHub contains v8.0–v8.5 historical tooling and new `tools/blender_daytona365_v8_6_source_contoured_console_seats.py` plus v8.6 reopen/render/compare/package/source-contract scripts; `.github/workflows/daytona-blender-v8.yml` tests source only.
- `docs/images/daytona365-v8/` holds only actual rendered image evidence (now including v8.6 PMT/v8.5/v8.6 comparison); it is **not** a source model or an image-generation substitute.
- v8.5 already completed and v8.6 actual Blender save/reopen/low-res Cycles verified. **Next material stage is v8.7**: source-visible seat side returns and real PMT console/facia silhouette matching; do not retry or re-score v8.0–v8.6.

## Repeating real-work loop
1. Read the **latest branch HEAD**, this plan, v8.6 manifests and the genuine PMT/v8.5/v8.6 render comparison. Read prior incomplete changes before selecting the next visible defect.
2. Work on a **materially useful batch**: correct real object proportions and topology (dash/gauge binnacle, wheel, door cards, seat profile, console, footwell), object-local transforms, UVs, normal-map/bump treatment, BaseColor/roughness/metallic/ORM and texture packing. Favor source-model faithful changes; no stretched vehicle or made-up asset claims.
3. Change Blender Python tooling/assets on the above branch, adding focused tests. Preserve original meshes, pivot/UV references, original source and runnable baseline. Never overwrite the last verified `.blend`; save sequentially versioned `v8_7`, `v8_8` etc. Keep heavy proprietary original game/PMT/OVC and private editable `.blend` assets off public GitHub.
4. **Render for real**, using Blender on a suitable Windows workstation or a GitHub Actions runner where sources are available. N100 is a light-control/provenance/transport host; do not saturate the N100 with repeated high-resolution CPU Cycles runs. If a real render is not possible, mark `RENDER_VALIDATION=UNTESTED`; do not fabricate output.
5. Save provenance (input version and SHA, Blender version, render engine and settings, camera and framing, render path, output SHA), actual original/candidate comparison image, changed areas, and remaining visible mismatches. Run script/source contract and commit coherent material changes. Keep commits on the **v8 branch only**.
6. Continue from the next uncorrected visible issue. Do not stop at a plan, repeated review or a one-line cosmetic change. Never score the same achievement twice, and never mark a CI pass as headset or runtime validation.

## Automation boundaries
- Slot A exclusively owns Daytona365 modeling. Slot C exclusively owns `thp32tt/Model2VR-tools@main`. Legacy DX11 and DXVK stay disabled/frozen.
- The new ChatGPT session **must** re-read GitHub HEAD and this plan, not trust a stale task-id or replay previous done work. No auto-merge into game/VR branches or OVC/game runtime deployment.
- Use actual render evidence to guide improvement. If Windows Blender MCP is not actually connected, do not claim to have controlled it. Prefer GitHub-hosted tools and local ChatGPT computation; use N100 only for light authorized file operations.
- Each result should report commit SHA, updated model/script paths, real render and comparison paths (if produced), verification status and **one specific next improvement**.

## v8.6 verified handoff (append-only milestone)
- `docs/daytona365_blender_v8_6.md` records measured source PMT group016/group018 bounds, 9-station tunnel with metric tangent UV, sculpted dashboard/fairing, four original seat-shell bolster refinements and door UV/PBR.
- Official Blender 4.5.15 LTS saved v8.6 and reopened it: 102 meshes / 61 curves, preservation and packed-map checks PASS. Original game binaries and runtime branches untouched.
- Actual Cycles preview: 480×320, 4 spp, 2 CPU threads; v8.5 same resolution/samples, original PMT downsampled from 960×640/10 spp. Same-camera visual comparison PASS, photometric/full-resolution equivalence NOT claimed.
- `RENDER_VALIDATION=PREVIEW_ONLY`; `FULL_RESOLUTION_MATCHED_CYCLES=UNTESTED`; `GAME_RUNTIME/OVC/QUEST3=UNTESTED`.
- Private immutable archive `Daytona365_BLENDER_REWORK_v8_6_PRIVATE.zip` SHA-256 `0d13d742602c92c0f7fdd513d475dabbdc2026a8c5adc5d562b4915e61e9fe48`; avoid uploading source PMT/OVC/executable assets.
