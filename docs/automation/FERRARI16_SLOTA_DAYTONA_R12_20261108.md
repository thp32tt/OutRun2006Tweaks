# Ferrari 365 GTS/4 Daytona — slot A native cockpit R12 checkpoint

Date: 2026-11-08 KST. Slot **A** only; queue active_by_slot.A = `daytona365`.
Source branch: `thp32tt/OutRun2006Tweaks@feature/ferrari16-geometry-rework-20261108`.
24h allocation began 2026-11-08 13:13:41 KST; no early rotation.

## Read-only original resource provenance and direct existing-mesh editing

- Original game PMT (read-only): `/home/chatgpt-runner/rea-input/outrun/outrun2006/Cars/obj_plcar_dayts_pmt.sz` SHA256 `f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe`.
- Original PMT-derived verified editable imported source: `work_handoff/daytona365_rework_20261107/original_game_blender/Daytona365_ORIGINAL_GAME_COCKPIT_COMPARE.blend` SHA256 `92c82ee5c4e0631195cb314e0d8e2f56a78a6a58da3c809c46b1da0f9d2c71a3`.
- Original native object IDs retained: `object00_group01_material012_a0` (source dashboard) and `object22_group00_material000_a0` (factory spoke pressing); verified source-derived existing Blender objects below, never replaced by a GLB/replica.
- Immutable private input `Daytona365_SlotA_SourceCockpit_P0_DashWheel_v9_r11.blend` SHA256 `2324f2e496d18073d8bd81433512a0a569f13936f0e8930dcb0ee8100723d026`.
- **New real private output** `work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108/Daytona365_SlotA_SourceCockpit_P0_DashWheel_v10_r12.blend` SHA256 **`2995c8b21e519d7e7da4de71bf3bd35186ef8f7159506d619c312083cf5fd518`**. This was actually saved with official Blender 4.5.15, then independently reopened in a separate Blender process; not uploaded publicly.
- Official Blender geometry source script: `tools/car_modeling/slotA_daytona_r12_original_spoke_roll_dashboard.py` material commit `71ee69e59f7b0768561bb17039b3cc62f6835244`.
- Independent native reopen and actual private-scene Cycles script: `tools/car_modeling/slotA_daytona_r12_independent_native_cycles.py` commit `4680a195ac312719f6bc22e1d2ae97aeba0f2186`.

## Source-derived P0 changes, exact existing mesh names

| Existing mesh | Before v/f | After v/f | Vertices physically moved |
|---|---:|---:|---:|
| `V5_DASHBOARD_SOURCE_REFERENCED_PADDED_FACE` | 1885/3584 | 1885/3584 | 359 |
| `V8_17_ORIGINAL_GUIDED_GAUGE_COWL` | 650/648 | 650/648 | 504 |
| `DAYTONA_GAUGE_METAL_BEZEL_ACTUAL_GEOMETRY` | 908/1344 | 908/1344 | 811 |
| `V5_ORIGINAL_THREESPOKE_WHEEL_object22_group00_material000_a0` | 9720/17285 | 9720/17285 | 6157 |
| `V7_3_HIGH_RES_WALNUT_SINGLE_STEERING_RIM` | 1536/1536 | 1536/1536 | 288 |
| `V7_SHORT_SHAFT_AT_WHEEL_HUB` | 224/210 | 224/210 | 103 |
| **Total** | | | **8222** |

Physical changes: source-derived dash front instrument trough, padded gauge-cowl arch, existing metal gauge bezel rolled relief, specifically the **eight original-source three-spoke through-hole metal lips** (all eight remain physically open in BVH rays), actual rim thumb shoulder surfaces and source hub collar. Every original-derived edited mesh retained UVs, original material assignments and world matrix; original dashboard/steering anchor IDs and camera objects preserved. All **107 other pre-existing mesh geometry signatures unchanged**. No new objects, material/texture creation, normal/PBR, exterior body/tires, game PMT/OVC/OVC3 export, game/VR source edits, or other-slot/Dino/Model2 changes.

Independent Blender v4.5.15 fresh reopen succeeded, mesh signatures and 8 source-hole BVH PASS. Remaining **original pre-existing nonmanifold edges**: dashboard 184, gauge bezel 466, spoke pressing 1597 (unchanged). This is **not** a claim of clean production topology.

## Real independent render / private reference comparison

- Actual private R11 Cycles 720x480 3 spp: SHA256 `0a169d07346c38bbc2b3892c75443c33f92e6970308269711d8728aa6d7a552d`.
- Actual private R12 Cycles same 720x480 3 spp: SHA256 `9154e6d1ac5025a6ff6672f628fee850fbe0a4287771d58d167da622eefc3b94`.
- Render before/after contact sheet: `work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108/SLOTA_DAYTONA_R11_VS_R12_REAL_CYCLES_COMPARISON.jpg` SHA256 `a1033386825b0b8530890e618cda1e1ce848400b15a8ca73b81d9507251e9c39`.
- Source photo (private authenticated 1971 Daytona Spider LHD reference): `outrun2_vr_refs/20261104_16car_cockpit/02_365_GTS4_Daytona/ADD_interior_LHD.jpg` SHA256 `6eae2fafd6369c1dbd4b82df8e24834d2d284bc3415cace15a9ea830cadd26eb`.
- Private photo/R11/R12 comparison JPEG: `work_handoff/ferrari16_slotA_daytona_dashboard_steering_20261108/SLOTA_R12_REAL_SPIDER_PHOTO_AND_NATIVE_CYCLES_PRIVATE.jpg` SHA256 `3fc8bbb9bd2eecb437743c63e096b9635eb9bd15d96ebc06a3600d7d6ec0f3b9`.
- True RGB comparison with Pillow: **12,884 / 345,600 pixels** had any channel difference >3; not a smoke cube. Both render cameras are the same approximate aligned view, **not calibrated actual game driver eye**.
- Source N100 `MANIFEST.json`: Daytona entries found, and `COVERAGE_MATRIX_16x8.csv` all eight rows checked; only dashboard/gauges/steering had visually unverified candidates, and other required dedicated reference labels are absent. Do not claim seven authenticated exact-Spider matched-view PASS.

## Gates / isolation / scoring

**PARTIAL_NEEDS_QA, ACTIVE, not COMPLETE.** Real Blender 4.5.15 private-scene save/reopen/Cycles succeeded on N100. GitHub Actions hosted `ferrari-geometry-blender.yml` only has smoke inputs and does **not** receive private licensed `.blend`, PMT and photo; hosted **real original-scene audit is BLOCKED_INPUT_NOT_TRANSFERRED**, not a PASS. No proprietary model/photo committed.

Same previously scored slot A Daytona P0 source-based dashboard/steering geometry achievement (existing RUN_KEY `FERRARI16-SLOTA-DAYTONA-P0-SOURCE-DASH-WHEEL-20261108-0D388F55`) refinement; **no duplicate score**. GitHub scoreboard AI2 previous confirmed 2780; this +0, AI2 remains 2780. Revisit original calibrated camera, missing seven exact matched reference views, source nonmanifold, human-authenticated P0 and 24h allocation. Do not advance slot A or modify slot C.
