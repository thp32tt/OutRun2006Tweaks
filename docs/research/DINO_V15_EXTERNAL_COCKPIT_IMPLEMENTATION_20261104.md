# Dino 246 GTS v15 independent VR cockpit

Branch: feature/dino-v15-external-cockpit-20261104
Base: vr-d3d9ex-focus; no game .sz / EXE / PMT modification.

Implemented source:
- 70-group / 19 DDS R2 extractor: tools/cockpit/dino_v15_external/build_sidecar.py
- Bounded atomic 1.12MB sidecar parser: src/vr/game/dino_external_sidecar.hpp
- D3D9Ex DEFAULT-pool textures/VB/IB, scoped D3D state: src/vr/game/dino_external_d3d9.hpp
- Two explicit OpenXR-latched eye-view render targets with state restoration: src/vr/game/dino_external_stereo_bridge.hpp
- Existing EXE+0x69764 verified player-car model-state callback opt-in glue: src/hooks_graphics.cpp
- Independent life-cycle cleanup on Reset / ResetEx.
- Original car kind 1 confirmed by r4dius/outrun2-decomp src/platform/frontend_vehicle_data.hpp (model order is NOT menu order).
- Default OFF: [VR] DinoExternalCockpit=true enables the experimental renderer.
- The .ovc file must be alongside the game executable.
- In car-selection, 2D, mono/theater and non-Dino modes the new renderer performs zero file reads, zero GPU allocations and zero cockpit draws.

Warnings: exact VR stereo runtime and real-game regression untested. The R29 frame snapshot can refuse the draw when eye depth or pose ownership is uncertain. No modified PMT should be installed; restore the original first. Neither game assets nor copyrighted game executable are checked into GitHub.

Known testing objective: validate car selection survives unmodified PMT, then verify passenger/exterior, both eyes, scale/orientation, lost-device and Reset/ResetEx. Do not release as official v0.01 until HMD test passes.

Sidecar from user-provided R2 test ZIP:
  Name: Dino246_Cockpit_LHD_v15.ovc
  SHA-256: dbdf70ac0751f1627c4e07a8a08f8d52fe8a68a9502bc18bb3ac1aeead20823a
  Size: 1124166 bytes.
