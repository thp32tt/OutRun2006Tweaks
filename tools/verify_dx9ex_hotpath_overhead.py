#!/usr/bin/env python3
"""Guard source-only hot-path changes; integration build remains authoritative."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
graphics = (ROOT / "src/hooks_graphics.cpp").read_text(encoding="utf-8")
renderer = (ROOT / "src/vr/game/outrun_renderer.cpp").read_text(encoding="utf-8")
r29 = (ROOT / "src/vr/d3d9/stereo_renderer_r29.cpp").read_text(encoding="utf-8")
r30 = (ROOT / "src/vr/d3d9/stereo_renderer_r30.cpp").read_text(encoding="utf-8")
api = (ROOT / "src/vr/core/r29_owner_api.hpp").read_text(encoding="utf-8")

brightness = graphics.split("class RestoreXboxBrightness : public Hook", 1)[1].split("class RestoreSkyGlow", 1)[0]
anisotropic = graphics.split("class AnisotropicFiltering : public Hook", 1)[1].split("class VSyncOverride", 1)[0]
destination2 = anisotropic.split("static void destination2", 1)[1].split("public:", 1)[0]
assert "bool validate() override" in brightness
assert "return Settings::RestoreXboxBrightness;" in brightness
assert "Settings::RestoreXboxBrightness.needs_restart();" in brightness
assert brightness.index("bool validate() override") < brightness.index("bool apply() override")
assert "Memory::VP::Nop(Module::exe_ptr(IntensityLatch_Addr), 6)" in brightness
assert anisotropic.count("SetSamplerState(sampler,") == 1
assert "SetSamplerState(" not in destination2
assert "if (ctx.edi == D3DSAMP_MINFILTER)" in destination2
assert "ctx.edi == D3DSAMP_MINFILTER || ctx.edi == D3DSAMP_MAGFILTER" not in destination2
assert "PreserveScreenTextureFiltering()" in destination2

assert "static thread_local float patchedData[256 * 4];" in renderer
assert "float patchedData[256 * 4];" in renderer
assert "if (needView)" in renderer
assert "(!needView || MatrixFinite(view))" in renderer
assert "Settings::VRMatrixOrder != 0))" in renderer
assert "if (vector4fCount > OutRunWvpRegisterCount)" in renderer
assert "if (!UploadContainsOutRunWvp(startRegister, vector4fCount))" in renderer or "UploadContainsOutRunWvp(startRegister, vector4fCount)" in renderer
assert "std::memcpy(patchedData + wvpOffsetRegisters * 4, &transposed" in renderer
assert "R29OwnerSkyGlowCaptureStillValid(std::uint64_t presentEpoch)" in api
for probe in ["capturedEpoch == PresentEpoch", "FrameHadWorldStereo",
              "FrameHadDuplicatedDraw", "!FrameRightDrawFailed",
              "!FrameStereoIncomplete", "BackBuffer != nullptr",
              "RightEyeSurface != nullptr"]:
    assert probe in r29, probe
capture = r30.split("bool R30CaptureSkyGlowSceneBeforeHud(", 1)[1].split("bool R30ApplyStereoSkyGlow(", 1)[0]
assert capture.index("R29OwnerSkyGlowCaptureStillValid") < capture.index("R29OwnerCaptureFrameSnapshot")
assert "R30SkyGlowSceneCaptureEpoch = frame.presentEpoch;" in capture
assert "R30SkyGlowSceneCaptureEpoch = 0;" in r30
assert "GetVertexShaderConstantF(" in r30  # Unsafe raw-WVP shortcut deliberately NOT installed.
print("DX9Ex hotpath source guard PASS (runtime/Quest3 untested)")
