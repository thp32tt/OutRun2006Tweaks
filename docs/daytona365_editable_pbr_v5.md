# Daytona 365 GTS/4 - independent editable PBR v5 rework

Real standalone cockpit model rework, not an additional OVC converter or game installer. Dino 246 and original game PMT remain read-only.

- Original Daytona PMT SHA256: f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe; prior v4 enhancement source SHA256: 6b7b8c0544702c80d41beb220d7ae0db576ddf2bc16c35f6e0cf783085ba8694.
- Private N100: /home/chatgpt-runner/work_handoff/daytona365_rework_20261107/editable_v5
- Output Daytona365_Cockpit_EDITABLE_HiDetail_PBR_v5.glb: 89 editable meshes, 31,488 vertices, 54,873 triangles, nine photo-source materials, 36 embedded maps. GLB SHA256: 387e4262b5768058e67ec3771a230c62a56317d8a7513ccfe45258b1508303df.
- Replaced flat source upholstery with two sculpted seat cushions/backs, rolled side bolsters, raised stripes and stitching. Built curved dashboard, door cards, vents and manual shifter; placed the original native three-spoke wheel once. Original source silhouette anchors are not independently HMD-verified.
- Eliminated macro-shadow patterns on leather tiles, retained authentic fine photo grain. Packed ORM has R=AO, G=roughness, B=metallic; glTF uses normative baseColorTexture, normalTexture, occlusionTexture and metallicRoughnessTexture.
- Each material also contains standalone grayscale height/displacement maps for later authoring under extras.HeightMapImageIndex, NOT independently supported 3D volume texture runtime. Confirmed PBR loader at feature/dino-external-pbr-runtime-v1-20261106 supports optional Normal and packed ORM; this v5 branch does not edit game loader.
- Private ZIP Daytona365_EDITABLE_ONLY_PBR_v5_PRIVATE.zip includes GLB, all BaseColor/Normal/ORM/Height PNGs and real model-preview JPGs. No OVC, game DLL or PMT replacements are included.
- GitHub CI synthetic test: tools/test_daytona365_editable_v5.py. On N100 --actual also verifies full real GLB and exact source geometry/map bindings.
- Not claimed: Blender file load or render, Quest3 real display or final high-quality appearance. The CPU preview uses painter-sorted triangles and shows its own artifacts.
