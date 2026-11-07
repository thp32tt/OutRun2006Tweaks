# Ferrari 365 GTS/4 Daytona — source-aligned photo-mesh v4

This v4 continues experimental original-game cockpit remodeling. It is not a generated concept image.

- Previous branch: `feature/daytona365-photo-mesh-pbr-v3-20261107`.
- New geometry: actual 4-slider vertical chrome frames, black slots, physical slider caps and 3 under-panel toggle levers, aligned only to the verified PMT tex15 upper/lower planar instrument housing. Replaces inaccurate v2 circular placeholder switches instead of doubling them.
- Real seat detail: raised double-row stitching (288 individual physical stitches) on eight curved original-game anchored black leather seat bands; preserves original game steering wheel and native player car.
- Photo BaseColor: two corresponding photographic switch regions are mapped into the original tex15 UV atlas. No inferred full-scene photograph or extra full-car mesh.
- Mesh build: `tools/build_daytona365_photo_mesh_v4.py`; local N100 original PMT and reference photographs required. Byte-level original-game data is NEVER committed.
- Native game result: `Daytona365_Cockpit_R26_v2.ovc` (existing D3D9Ex filename retained for C++ ABI compatibility). 16 mesh groups, 5,642 vertices, 7,086 triangles, 7 embedded DDS textures. `obj_plcar_dayts_pmt.sz` remains the v3 byte-preserving six-texture photo repaint. Dino and original game PMT untouched.
- Verified with portable actual `src/vr/game/dino_external_sidecar.hpp` C++ parser and CRC corrupt-frame test on N100, plus source-free synthesized five-regression tests in CI.
- Original PMT hash is pinned. Engine shader uses BaseColor fixed-function; Normal/Roughness from v3 are offline-only. True VR quality and carKind=2 switch must be observed in Quest 3 gameplay.
- Private output stored in N100 `work_handoff/daytona365_rework_20261107/runtime_v4`. Do not distribute game asset derivatives.

Static test proof is NOT a statement that Daytona enters the actual VR scene without a Quest 3 hardware run.
