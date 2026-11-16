# N100: Blender 5.2.4 LTS + KN5 Tools 2.0.3 independent conversion environment PASS

As of **2026-11-16 KST**. This is toolchain QA, not proof of an OutRun F430/13-car converted asset.

## Actual installed executable and addon

- Blender executable: `/home/chatgpt-runner/work_handoff/blender_5_2_4_official_cache/blender-5.2.4-linux-x64/blender`
- Blender archive: `blender-5.2.4-linux-x64.tar.xz`; exact official Blender SHA256 `2fd14c50987426897ba60237ee996edf2b4151f4b1a72a460ca20be58c1d2d86`; tar size 385,047,680 B
- Blender 5.x version QA: **PASS** `Blender 5.2.4 LTS`, build `2026-11-10`
- Headless Python QA: **PASS** `BLENDER_52_HEADLESS_API_PASS 5.2.4 LTS`
- Original Blender 4.5.15: **untouched** `/home/chatgpt-runner/work_handoff/blender_4_5_15_official_cache/blender-4.5.15-linux-x64/blender`
- KN5 Tools official addon v2.0.3: `https://extensions.blender.org/add-ons/kn5-blender-tools/`, Blender 5.0+, GPL-3.0-or-later, fixed sha256 `74c5bcd5760cbc22af0e2c6b956ddeed10a77d8ca50511f93aceae29aefe9196`, zip size 42,918 bytes
- Official extension manifest source: `https://extensions.blender.org/api/v1/extensions/?blender_version=5.2.4&platform=linux-x64`; sha check PASS, zip CRC PASS, manifest `id=kn5_blender_tools`, `version=2.0.3`.
- Install command **PASS**: `blender --command extension install-file --repo user_default --enable kn5_blender_tools-2.0.3-official.zip`
- Registration smoke QA **PASS**: `import bl_ext.user_default.kn5_blender_tools`, `bpy.ops.import_scene.assetto_corsa_kn5.get_rna_type()` succeeds under Blender 5.2.4.
- To isolate this test from all user Blender versions, CLI env overrides `HOME=/home/chatgpt-runner/work_handoff/blender_5_2_4_official_cache/isolated_home` and `XDG_CONFIG_HOME=$HOME/.config`. Addon only installed within `isolated_home/.config/blender/5.2/extensions/user_default/kn5_blender_tools`.
- Machine-readable QA on N100: `work_handoff/blender_5_2_4_official_cache/INSTALL_VALIDATION.json` and `KN5_EXTENSION_QA.json`; installer scripts `f50_hq_package_stage/install_blender52_nicetar.py`, `setup_official_kn5_blender52.py`.
- Source asset import verification: **NOT YET RUN** (no authorized source `.kn5` Ferrari source was downloaded during this task); no claim of F430 geometries/textures successfully converted.

## Runtime sidecar constraints independent from Blender

Code truth: `src/vr/game/dino_external_sidecar.hpp` and `tools/car_importer/ferrari16_hq_batch/tools/ferrari_batch_converter.py` cap a sidecar at **2,000,000 triangles, 1,000,000 vertices, 128 MiB file and 112 MiB GPU payload**. Upgrading Blender alone does not raise any of these limits. Actual Assetto Corsa F430 candidate triangle/vertex counts are **unknown until source KN5 imported**; the earlier 2.284M number was for a distinct Sketchfab F430 candidate, not this AC model. No automatic decimation or cap bypass applied.

## Useful sources

- Blender 5.2.4 LTS official release: https://www.blender.org/releases/5-2/
- KN5 extension official package/version: https://extensions.blender.org/add-ons/kn5-blender-tools/versions/
- Blender extension CLI: https://docs.blender.org/manual/en/5.2/advanced/command_line/extension_arguments.html
- Modern Ferrari model candidate priority: [Ferrari13 modern game mod source audit](ferrari13-modern-game-mod-only-blender52-20261116.md)

**AI 2 earned result:** independent Blender 5.2.4 side-by-side executable and KN5 2.0.3 addon installed with official sha/Blender API real QA, not converted car asset.
