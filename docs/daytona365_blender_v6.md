# Daytona 365 GTS/4 genuine Blender 4.5.15 LTS rework v6

**Standalone editable cockpit modeling only.** No new game OVC/DLL/PMT. Original Dino remains untouched.

## Source and actual private material artifact

- Parent input: verified private Daytona v5 glTF GLB `387e4262b5768058e67ec3771a230c62a56317d8a7513ccfe45258b1508303df` (89 meshes), previously sourced from the user's own game PMT and v4 enhancement. Neither the private input GLB nor the proprietary game data are committed to this public repository.
- Rework performed by official native Blender 4.5.15 LTS (Oct 22 2026 release), binary archive SHA-256 `0d2b8bb2efe97e6c8eb57de6b7322f8800e1984e3125b60decca5f6771e4773` verified against official upstream checksum. Blender imported actual GLB, applied real Blender native Solidify, Subdivision Surface, Bevel, Weighted Normal modifiers, and created native Blender curves, bevelled solids, torus/seat upholstery details, door pockets, pedals, floor mats and shift boot, including studio area lights and cameras.
- New private self-contained `.blend`: `work_handoff/daytona365_rework_20261107/blender_v6/Daytona365_Cockpit_Blender_PBR_v6.blend` under N100 `/home/chatgpt-runner`. **SHA-256 `6e0a72c47466ea8c05870d594714fa5ef5797e31a8966193125b6d3242947df0`**; 3,982,849 bytes. Reopened fresh in official Blender, verified 103 mesh objects, 31 curve objects, 46 native mesh modifiers, 8 Principled PBR node materials, 24 packed image textures (0 unpacked images). New 45 geometry objects. 
- Final private ZIP `Daytona365_BLENDER_ACTUAL_REWORK_v6_PRIVATE.zip` (5,458,039 bytes), includes `.blend`, verified metadata, actual Blender Cycles CPU previews. ZIP SHA of internal `.blend` matches. None of .ovc/.exe/.pmt or game files are included.
- Normal/packed ORM images are present in Blender material nodes and packed in `.blend`. Standalone 3D voxel volume sampler support was not verified; do not treat height/displacement maps as volume textures.
- Real Blender Cycles preview `docs/images/daytona365-v6-blender/Daytona365_BLENDER_v6_POLISHED_CABIN.png` is not AI-generated or a Quest 3 screenshot. Cycles CPU with material nodes and studio lights. Camera arrangement and VR-play performance not tested.

## Remaining refinement

Visible side-seat edges, large flat backrest panel transitions, practical seat scale, dashboard/column seam, geometry collision, original-car movement/pivots and photorealism still need improvement. This is a source-backed **work-in-progress** model, not a production-quality completed cockpit.

Use `tools/blender_daytona365_v6_rework.py` via **actual Blender 4.5** `blender -b --python ...`, not standalone system Python. Private input path and user game originals are mandatory. Blender programmatic operators genuinely run, not a fake Blender illustration.
