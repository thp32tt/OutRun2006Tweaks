# Ferrari 365 GTS/4 Daytona — actual Blender v7.3 target-image cockpit rework

**Scope:** Real editable Blender file, NOT an AI-generated beauty illustration, game-ready OVC, DLL or native PMT replacement. The existing Dino 246, original user game and installed VR loader are untouched.

## Visual source

The user's AI-generated classic Ferrari Daytona tan-leather cockpit image is a **design reference only**. From the target image, derived target baseColor palettes for tan saddle leather (~RGB 166,98,58), dark dashboard (~34,31,30), and walnut wooden steering rim (~109,56,31). A tiny genuine fine-grain sample from the user's target image was available for tan leather; transported black/walnut samples were damaged and only the color palette was reused for those maps. Mesh geometry is NOT a 2D view projection. The GLB/PMT source cockpit is the structural anchor; the image provides visual goals.

## Geometry actually changed in official Blender 4.5.15

- Opened v6 `.blend`; removed **67** overlapping old seat bands/bolsters/raised stitching and the oversized original steering column, preserving original game wheel spoke/logo source.
- Built four **closed and continuous padded shells** (driver/passenger cushion+back), sculpted horizontal pleat relief into actual mesh, added geometry-following seams and subtle edge piping. Further Blender Subdivision correction in v7.2.
- Corrected steering column to begin **below the gauge plane** (the original v6 shaft visibly crossed the gauge cluster). Original source low-poly rim is kept hidden for edit provenance. One new smooth wooden steering rim torus, three physical short spoke extensions and native center Ferrari emblem visible.
- Identified the unnatural vertical gray panels as v6 floor mats via actual Blender scene ray-cast. Corrected left/right mats to **horizontal** footwell elements; added dark carpet base, black under-dashboard face and kick panels. Replaced nine upward-pointing vertical pedal grip tubes with flush rubber pedal ribs.
- Richer black dashboard/console and tan saddle upholstery; Blender Principled BSDF node graph uses true BaseColor PNGs, tangent-space normal images, packed R=AOG=RoughnessB=Metallic (ORM) textures, and subtle height/bump PNG. **Independent VR runtime volume texture sampling is not claimed**; these are editable Blender materials.
- Three correction passes, each saved as real `.blend` (`v7`, `v7_1`, `v7_2`, `v7_3`), not a generated picture. v7.3 is the latest recommended editable file.

## Evidence and private outputs

- Private path: `/home/chatgpt-runner/work_handoff/daytona365_rework_20261107/blender_v7/Daytona365_Cockpit_Blender_PBR_v7_3.blend`.
- SHA256: `0175ace3e51a0dfb4ec782694051a66089b04ed83ecb730d1bf8bc3c8a24c81a`, size **5,849,332 bytes**. Reopened fresh in actual Blender 4.5.15 LTS, passing 77 mesh / 28 curve objects, four integrated seat shells, one visible walnut rim, floor mat orientation and packed PBR image checks.
- PNG `docs/images/daytona365-v7-actual/Daytona365_v7_3_ACTUAL_CYCLES_CABIN.png` is a **real Blender Cycles rendered scene**, NOT AI-generated and NOT VR gameplay footage.
- ZIP `Daytona365_BLENDER_TARGET_REWORK_v7_3_PRIVATE.zip` on user's N100: **8,385,687 bytes**. Contains private .blend, 12 individual maps and authentic render, no game binaries. Private assets are not published in GitHub.
- Synthetic CI: `tools/test_daytona365_v7_materials.py` executes the actual source map baker against synthetic 48x48 reference crops, verifies 3 families × 4 normal/ORM/base/height texture maps without access to private source images.

**Honest remaining work:** exact reference image photorealism is not achieved. Seat side panels/seat-back transitions, pedal/steering column tolerances, dashboard underparts, manual Ferrari Daytona detail and source-vehicle game alignment remain incomplete. This is an editable 3D rework WIP, not an in-game-ready release.
