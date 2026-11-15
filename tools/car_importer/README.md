# OutRun 2006 Car Importer v0.2 (GLB -> experimental OVC sidecar preview)

**Status (2026-11-15): GLB preflight + Blender conversion/staging + native-game backup/reopen verification; NOT an installable car mod.**

## Goals

Players obtain **lawfully usable** third-party model files on their own, then pick a local GLB in the importer. No third-party or original game assets are bundled. Planned end state: one-click compatible model install and rollback. The native serializer / renderer integration is currently **unimplemented**, and the UI's Install button is deliberately disabled; do not describe this as complete one-click OutRun installation.

## Working importer features

- Small Windows desktop GUI (Tkinter), Python CLI, single-file Windows `.exe` CI packaging.
- Inspect GLB 2.0: magic/size/JSON/BIN structure, POSITION and index accessors, capped geometry, meshes, triangles, materials, source hash, reported license metadata, and clear warnings. No network requests or hidden downloads.
- Source-verified Ferrari F50 game profile (`Cars/obj_plcar_f50_pmt.sz` SHA-256 `10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab`). Unknown versions fail closed.
- Optionally load user's native PMT-derived `.blend` **read-only**, import GLB into an **independent collection**, align length and ground to verified F50 dimensions, export `staged_car.glb`, `staged_car.blend`, `car_preview.png`, and `stage_manifest.json`. Blender subprocess performs a separate independent reopened-file/hash QA.
- Verified backup of exact original game F50 PMT to a **directory outside the game**, with SHA-256 receipt; the v0.1 restore command **only validates the backup** and never copies files back, because game mod installation is disabled.
- User must explicitly acknowledge they have verified the right to use/convert the chosen model.
- The Windows one-file EXE embeds both the Blender worker and the `profiles.py` file needed by Blender’s **separate** Python interpreter. CI includes a headless EXE packaging smoke test.
- Staging refuses to write into the game folder or a non-empty output directory. Blender auto-execution of scripts embedded in `.blend` files is disabled.

## Experimental F50 separate-folder OVC pipeline (2026-11-16)

- GUI **2a. 외부 GLB → OVC 사이드카 테스트** combines preflight, Blender normalization, independent .blend reopen, OVRCABH2 v2 export (RGBA 128px per material), SHA256+CRC+bounded geometry validation. Produces `output/ovc_test/f50_external_test.ovc` while leaving all `Cars/obj_plcar_f50_pmt.sz` originals untouched.
- Verified locally with an actual user-held F50 GLB: 875 source meshes -> 20 OVC groups, 20 DDS materials, 195,104 vertices, 218,664 triangles, 8,869,368 bytes. **Existing DinoSidecar C++ V2 parser** accepts the exact produced payload. Test source binary contains external model rights still under review; do not redistribute compiled 3D model data.
- Command: `python tools/car_importer/cli.py stage-sidecar MODEL.glb --blender BLENDER --out EMPTY_FOLDER --slot f50 --rights-confirmed`; output is in `EMPTY_FOLDER/ovc_test/`.
- The F50 model is **not yet confirmed drawable in the game**. The older verified Dino sidecar format parser is NOT proof of a F50 runtime loader, draw ownership binding, or correct VR positions. Runtime installation remains blocked.

## What this does NOT do

- No native PMT serializer or validated **F50** game-runtime OVC loader / D3D9 draw binding; no substitution of actual game model; no VR/PC frame verification. Experimental OVC geometry serialization is available, but is NOT a verified playable in-game replacement.
- No guarantee that any purported CC licence on model metadata was issued by an actual underlying rightsholder. No copyrighted binary models included. The previous **CSR2-derived F50** is suitable only as a locally held research sample pending clearance; it is **not an approved redistributable input**.
- No bulk conversion of all OutRun vehicles. v0.1 recognises **only F50** to prevent guesses or damage.
- No read/write outside explicitly selected input, staging, and verified backup locations.

## Install and launch (Windows)

1. Download the ZIP/Windows EXE from the GitHub Actions `car-importer-v01` successful build of this branch. Extract the EXE to any folder; no Python required for the EXE. If using the source instead, install Python 3.12+ with Tkinter, then run `python tools/car_importer/gui.py` from the repo checkout.
2. Download a compatible model from its author with valid permissions. Select a `.glb` and select your **official Blender 4.5+** executable. Blender is required to make stage files; `inspect` does not require Blender.
3. Optional: choose the *original* PMT-derived Ferrari F50 Blender `.blend` as a geometric reference. Select a fresh, separate output directory.
4. Check the use/conversion permission acknowledgment; click **Blender 시제품 생성**. Inspect the output render and manifest.
5. For game backups only, pick your local OutRun 2006 installation with `OR2006C2C.exe`, and press **원본 게임 검증** then **원본 백업**. No game files are modified.
6. Game installation is disabled: the stage is **NOT** a `.sz` package. Do not copy stage output into `Cars/` manually.

## CLI

```bash
python tools/car_importer/cli.py inspect path/to/model.glb
python tools/car_importer/cli.py stage path/to/model.glb --blender path/to/blender --out path/to/EMPTY_STAGING_FOLDER --slot f50 --rights-confirmed
python tools/car_importer/cli.py stage path/to/model.glb --blender path/to/blender --out path/to/EMPTY_STAGING_FOLDER --slot f50 --reference-blend path/to/original.blend --rights-confirmed
python tools/car_importer/cli.py verify-game path/to/OutRun2006 --slot f50
python tools/car_importer/cli.py backup path/to/OutRun2006 path/to/OUTSIDE_BACKUPS --slot f50
python tools/car_importer/cli.py restore path/to/OutRun2006 path/to/OUTSIDE_BACKUPS/OutRunCarImporter_f50_.../receipt.json
python tools/car_importer/cli.py install path/to/OutRun2006 path/to/staged_car.glb  # explicitly BLOCKED
python -m unittest discover -s tools/car_importer/tests -v
```

## Engineering gates for v0.2 (not satisfied)

1. Native PMT serializer with verified structure, culling, materials/textures, wheels, LODs, and animations; independent full byte/semantic round-trip. Existing `.bt` PMT template and importer are **read-only**.
2. Reproducible native F50 PMT test on a legally owned game install, then 2D + Quest 3/OpenXR visual/frametime QA. Never overwrite an unexpected game SHA.
3. Enable **Apply** only for an exact verified converter output and transactional backups, receipt/hash checks, and safe automatic rollback.
4. Publish importer code without any original game model, third-party GLB, executable or licensed content.

## Project references

- Source format: `docs/file_formats/pmt_c2c.bt` in OutRun2006Tweaks.
- Original PMT reader: `thp32tt/imsi1/tools/car_modeling/import_360spider_native_pmt.py`.
- Verified external F50 staging experiment: `thp32tt/imsi1@poc/f50-external-model-import-20261115`.

Licence: this new importer code is part of the OutRun2006Tweaks project licence; this does **not** license imported 3D models or original game assets.