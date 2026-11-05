# Dino 246 original-dimension cockpit — real 3D steering-column repair v3

Date: 2026-11-06 KST
Branch: `feature/dino-hd-cockpit-column-v3-20261106`

## Goal

Fix the real, visible geometry defect where the old large steering-column shaft runs into the gauge cluster and through the dashboard. The requested Dino 246 reference images show a hub connected to a dark padded steering-column casing that meets the instrument panel **below** the gauges. Reference images are artistic targets; the changes below are actual mesh/source edits, not AI-generated concept illustrations.

## Previous failure and actual remedy

- Old v1/v2 `LHD_column_real_shafts` centerline at z~-0.42, y~0.69 intersects the central gauge centered at y=0.735 (radius .079). It also intersects the solid `dashboard_driver_instrument_recess` box, and the unsplit `dash_rolled_face` geometry.
- New v3 physically **removes** the old axle/shroud and those two blocking shell meshes from the model.
- New six-point sloped column centerline travels from the wheel hub `(-.320,.703,-.286)` to the dash lower aperture `(-.320,.571,-.475)`, then terminates behind the panel `(-.320,.524,-.605)`. An outer padded shroud follows that centerline; an internal metal axle, rubber grommet, leather mounting flange and cap finish it.
- Gauge panel is reconstructed as an upper beam with two side legs to leave a genuine empty cutout in the lower middle. The broad dashboard face is split into four independently modeled surface patches with a matching real opening, not a fake dark-texture hole. The shroud is tested to pass clear of these openings and all three existing instrument gauge circles.
- Wiper and indicator stalks now start on the exposed steering column rather than behind gauge faces.
- Added raised hub bolts, two rows of leather stitch segments and the joint lip around the aperture.

## Verified model artifact

- v2 baseline: **273** authoring groups, **49,377** vertices, **85,448** nonzero-area triangles; **9** batched runtime OVC meshes.
- v3 model: **364** authoring groups, **53,491** vertices, **91,652** nonzero-area triangles; **9** batched runtime OVC meshes, no extra material/texture slots.
- V3 analytic source-coordinate clearance: center gauge ~**0.01997** model units beyond assumed 0.031m shroud radius and 0.079m gauge radius at gauge plane z=-0.411. Left/right gauges have clearances ~0.07935 and 0.07719 model units. Grommet cutout has ~0.048m X and ~0.026m Y margin after shroud radius.
- The numerical meters approximate **original game asset coordinates**; they are NOT photographed physical Ferrari dimensions and NOT yet runtime-calibrated to Quest APK headset transforms.
- GLB model 2K material PNGs, separate editable objects: **15,402,036** bytes. R26 native `.ovc`, 1K source DDS maps: **40,011,867** bytes. **All existing materials remain deterministic procedural, not text-to-image generated**.
- Independent glTF 2.0 JSON/BIN/accessor/PNG structural validation PASS: 364 meshes, 9 texture images, 91,652 triangles.
- Existing native R26 `OutRunVR::DinoSidecar::Parse` compiled via C++ test and returned **PASS groups=9 textures=9 vertices=53491 triangles=91652 HQ=1**.
- New source-free tests assert the old intersecting object owners are absent, genuine hole topology, clearance at every gauge and dash crossing, no zero-area triangles, finite coordinates, and exact batched geometry totals.
- Original PC game input `Cars/obj_plcar_dino_pmt.sz` remains unmodified SHA-256 `1f8dfcb7b875d46bd58f110518c1a8815355162d4412fa4a0d4e2e2301d86284`. Private user-owned game assets have NOT been committed to public GitHub.

## Still NOT proven

- **Not yet ready to overwrite an existing game install**: no paired R26 original-player-car geometry suppression is implemented. The original steering wheel / dash can still appear if the v3 external cockpit is rendered on top.
- Native Quest APK per-car seat pose, HMD reference center/pivot, wheel turns, stereo alignment, car-selection/return-to-menu crash behavior and frame rate not empirically validated. **RUNTIME_VALIDATION=UNTESTED**.
- Truly photo-quality leather, precise Ferrari gauge labels, physically correct switches and seat quilting **are not fully reproduced**. The user's conceptual imagery is a target for another modeling/material pass. This task fixes measurable geometry collision and adds new detail without claiming photoreal visual parity.
- No AI image generation was invoked or used for this implementation. No image artifact is needed for verification.

## Usage

Edit/check the generated GLB in Blender; do not copy the experimental OVC over a working FitV6 model or run it through an unchanged launcher. Use `tools/dino_cockpit_hdgeometry_v3.py --game-dir <private PC OutRun data root> --output-dir <test dir> --glb-texture 2048 --ovc-texture 1024` on a machine with locally held valid PMT and dependencies installed. The exact private original PMT is a runtime input only.

Next integration: scoped original cockpit draw suppression in isolated R26 branch, model SHA binding and fail-closed launcher, actual Quest 3 camera/glass/passenger validation, then closer-to-photo material/mesh details.
