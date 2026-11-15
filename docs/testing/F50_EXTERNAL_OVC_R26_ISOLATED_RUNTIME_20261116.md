# Ferrari F50 isolated external OVC R26 runtime test (2026-11-16)

This is a deliberately isolated **experimental** DLL build, derived from the Dino external sidecar renderer line, not from the current QuestCockpitV2 v0.02 release branch. Keep a copy of your existing **dinput8.dll** before swapping this test DLL.

## Original game remains intact
- The importer writes exclusively `<game>/CarImporter/f50/f50_external_test.ovc`, plus an importer receipt. It does **not** modify `Cars/obj_plcar_f50_pmt.sz`, `OR2006C2C.exe`, or the existing game resources.
- F50 model source ID is **0** (independent PC reverse-engineered resource table; Dino ID **1**); the player callback gate only allows F50 + the explicitly selected test setting.
- F50 sidecar loader is opt-in: `[VR] F50ExternalModelTest=true` in the relevant game/Tweaks INI, under the same settings mechanism as `DinoExternalCockpit`.
- It runs only with VR enabled, QuestCockpitV2 enabled, native mode-1 player driver seat, valid stereo XR pose, and no active state-block capture. Other vehicles/menus are not modified.
- It overlays a separate F50 model **on top of the original game car**, for visual-path testing. It is NOT yet a clean stock-mesh replacement, and may show depth conflict/double rendering.

## Authoritative input/output proof
- Input external F50 model was 16,324,176-byte GLB SHA256 `6aa960b4d79f5e9400aaa804c2301f3c344461a88abc264d131b567575cae2dc` (rights **unconfirmed**; not included in public builds).
- Blender stage and `OVRCABH2` serializer -> locally generated 8,869,368-byte `f50_external_test.ovc` SHA256 `f6d971a579966dc03937369801096e067897933b4f03cc8c3ae25fece2b67284`; 20 groups, 20 textures, 195,104 vertices, 218,664 triangles.
- Unmodified original F50 PMT SHA256 `10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab`.
- Real OVC file parsed by **existing C++ DinoSidecar::Parse** and independent Python CRC/geometry reader: PASS; corrupted CRC rejected.
- Isolated install + duplicate-install protection + uninstall + native PMT SHA retention: PASS.
- Windows Win32 test DLL GitHub Actions build is independent evidence only. **No live gameplay, texture orientation, per-eye depth or Quest 3 screenshot has been verified yet.**

## Manual runtime procedure
1. Back up your current stable `dinput8.dll` and Tweaks INI OUTSIDE the game. Do not overwrite the game EXE. Close the game.
2. Get a model you are legally allowed to convert. Run OutRunCarImporter v0.2 -> GLB -> OVC test. Importer install copies only the OVC to `CarImporter/f50/`.
3. Put the separately built test `dinput8.dll` in the game root **after backing up the previous DLL**.
4. Set `[VR] F50ExternalModelTest=true`; keep the QuestCockpitV2 VR stereo options required by the selected R26 test branch. Start a race with F50 in mode-1 driver seat. Monitor logs for `VR QUEST EXTERNAL SIDECAR` and any crash.
5. To roll back, restore your original `dinput8.dll` and Tweaks INI, and use the importer to remove the verified test OVC. Original PMT never needs restoring.

**Boundary:** No 3D external model or game asset is committed to GitHub. Do not redistribute the CSR2-derived external input or resulting OVC without validating underlying rights.
