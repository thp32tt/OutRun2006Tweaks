# Ferrari 16 NativeHD Dashboard V4 private-build workflow — 2026-11-16

This branch adds the public-safe tooling/runtime support required to build a private 16-car NativeHD set from the user's own OutRun 2006 assets.

## Runtime contract

- OVRCABH4 / OVCDASH4 dashboard bindings remain the transport.
- Native remasters use `NATIVE_OPAQUE_*` / `NATIVE_GLASS_*` group identities.
- `Model::nativeOriginPreserved` is enabled only when every parsed group is native-origin.
- Native-origin models retain the original PMT/OBJ local origin and get exactly 0.0 m automatic visual floor lift.
- External-mod OVCs retain the existing conservative floor-clearance policy unchanged.
- Speed / RPM / gear telemetry and stereo native-frame latching remain unchanged.

## Private NativeHD builder

`tools/car_importer/ferrari16_hq_batch/tools/native_hd_dashboard_builder_blender.py`:

- consumes original full-car OBJ/MTL plus 2x private textures supplied outside Git;
- consolidates materially identical source materials to stay under the OVC material cap;
- applies conservative smoothing and small angle-limited bevels without decimation;
- preserves the original game origin/axes;
- creates separate speed/RPM needle meshes from the verified PC mode-1 seat anchors;
- writes editable Blender, embedded GLB, strict source metadata and QA receipts.

Private source models, textures, Blender files and generated OVCs are intentionally not committed.

## Validation

Portable tests cover:
- existing external floor guard;
- native-origin floor bypass = exactly 0;
- external-car route gate;
- dashboard transform/latch;
- OVRCABH4 parser;
- native-origin group recognition.

The private 16-car batch must additionally pass strict converter audit, OVC verify, and Blender fresh-reopen QA before packaging.