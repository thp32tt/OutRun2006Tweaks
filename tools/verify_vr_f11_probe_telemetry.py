#!/usr/bin/env python3
from pathlib import Path
src=(Path(__file__).resolve().parents[1]/"src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp").read_text(encoding="utf-8")
probe=src.split("VR F11 SOURCE-ASPECT PROBE:",1)[1].split("if (FAILED(rightHr))",1)[0]
required=(
    "viewport={},{},{},{} mode={} ",
    "state.hudWorldLockValid",
    '"FINITE_WORLD_LOCK_065"',
    '"FOV_ONLY_FAILSAFE"',
    "scissorL={},{},{},{} scissorR={},{},{},{} ",
    "leftHr=0x{:08X} rightHr=0x{:08X}",
)
for token in required:
    assert token in probe, token
assert "mode=FOV_ONLY_SCREEN2D" not in probe
# Destructive negative: old format silently shifted every field after viewport.
bad=probe.replace("viewport={},{},{},{} mode={} ","viewport={},{},{},{} mode=FOV_ONLY_SCREEN2D ",1)
assert "viewport={},{},{},{} mode={} " not in bad
print("PASS F11 source-aspect telemetry dynamic mode + L/R scissor/HRESULT alignment")