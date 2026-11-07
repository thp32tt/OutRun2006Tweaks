# Daytona 365 GTS/4 — Blender vehicle-model improvement (automation SSOT)

Updated: 2026-11-08 KST. Owner: OutRun Chat Controller slot **A** (not legacy DX11).
Repository: `thp32tt/OutRun2006Tweaks`.
Production branch: `feature/daytona365-blender-v8-20261108`.
Never edit `vr-dx11-native-r71`, `vr-d3d9ex-focus`, `Model2VR-tools`, localization, UW2 or the original game files.

## User goal
Keep improving the **second Ferrari, 365 GTS/4 Daytona**, not Dino 246. Match the reference appearance as closely as practical using actual Blender geometry and PBR textures/normal maps. Compare **actual original-game-derived geometry renders** against **actual new Blender Cycles renders**, both from measured source assets, with consistent camera, lighting and framing. Image-generation illustrations are not evidence of a rendered game model. Do not claim in-game integration, OVC conversion, or Quest 3 validation without those actual steps.

## Verified handoff at the time this plan was created
- The N100 source workspace is `/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/` (private assets stay there).
- Local latest Blender baseline: `blender_v8/Daytona365_Cockpit_Blender_PBR_v8_4.blend`, `DAYTONA_V8_4_VERIFIED.json`, `Daytona365_v8_4_ACTUAL_CYCLES_CABIN.png`, `Daytona365_ORIGINAL_vs_V8_4_ACTUAL_RENDER_COMPARE.png`.
- GitHub already contains `tools/blender_daytona365_v8_shape_rework.py`, `tools/blender_daytona365_v8_1_cleanup.py` through `v8_4_fine_cleanup.py`, `tools/test_daytona365_v8_source_contract.py`, and `.github/workflows/daytona-blender-v8.yml`.
- `docs/images/daytona365-v8/` holds only evidence of actual rendered imagery; it is **not** a user-supplied original model.
- Baseline is v8.4, so the next material work is **v8.5**, not rebuilding/revalidating successful v8.0–v8.4 milestones.

## Repeating real-work loop
1. Read the **latest branch HEAD**, this plan, v8.4 manifests and actual side-by-side comparison. Read prior incomplete changes before selecting the next visible defect.
2. Work on a **materially useful batch**: correct real object proportions and topology (dash/gauge binnacle, wheel, door cards, seat profile, console, footwell), object-local transforms, UVs, normal-map/bump treatment, BaseColor/roughness/metallic/ORM and texture packing. Favor source-model faithful changes; no stretched vehicle or made-up asset claims.
3. Change Blender Python tooling/assets on the above branch, adding focused tests. Preserve the original meshes, pivot/UV references, original source and runnable baseline. Never overwrite the last verified `.blend`; save versioned `v8_5`, `v8_6` etc. Keep heavy proprietary original game/PMT/OVC assets off public GitHub.
4. **Render for real**, using Blender on a suitable Windows workstation or a GitHub Actions runner where sources are available. N100 is a light-control/provenance/transport host; do not saturate the N100 with repeated high-resolution CPU Cycles runs. If a real render is not possible, mark `RENDER_VALIDATION=UNTESTED`; do not fabricate output.
5. Save provenance (input version and SHA, Blender version, render engine and settings, camera and framing, render path, output SHA), actual original/candidate comparison image, changed areas, and remaining visible mismatches. Run script/source contract and commit coherent material changes. Keep commits on the **v8 branch only**.
6. Continue from the next uncorrected visible issue. Do not stop at a plan, repeated review or a one-line cosmetic change. Never score the same achievement twice, and never mark a CI pass as headset or runtime validation.

## Automation boundaries
- Slot A exclusively owns Daytona365 modeling. Slot C exclusively owns `thp32tt/Model2VR-tools@main`. Legacy DX11 and DXVK stay disabled/frozen.
- The new ChatGPT session **must** re-read GitHub HEAD and this plan, not trust a stale task-id or replay previous done work. No auto-merge into game/VR branches or OVC/game runtime deployment.
- Use actual render evidence to guide improvement. If Windows Blender MCP is not actually connected, do not claim to have controlled it. Prefer GitHub-hosted tools and local ChatGPT computation; use N100 only for light authorized file operations.
- Each result should report commit SHA, updated model/script paths, real render and comparison paths (if produced), verification status and **one specific next improvement**.
