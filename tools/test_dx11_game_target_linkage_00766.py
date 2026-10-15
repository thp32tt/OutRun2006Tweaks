#!/usr/bin/env python3
"""00766: Win32 LNK2019 regression: R9 target hook must link to public DX11 bridge."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
header = (root / "src/vr/d3d11/live_game_frame_bridge.hpp").read_text(encoding="utf-8")
hook = (root / "src/vr/d3d9/stereo_renderer.cpp").read_text(encoding="utf-8")
build = (root / "CMakeLists.txt").read_text(encoding="utf-8")
workflow = (root / ".github/workflows/dx11-fast-structural.yml").read_text(encoding="utf-8")

definition = "bool preserve_game_target_transition(IDirect3DDevice9* game) noexcept {"
closing = "} // namespace\n\nbool preserve_game_target_transition("
def linked(source):
    # The original bug defined this function inside the anonymous namespace:
    # compile succeeded, but stereo_pipeline.obj could not link the public API.
    if source.count(definition) != 1 or closing not in source:
        return False
    anonymous_close = source.index("} // namespace", source.index("namespace {"))
    entry = source.index(definition)
    body = source[entry:source.index("\n}\n", entry) + 3]
    return (
        entry > anonymous_close and
        "GetRenderTarget(0, target.GetAddressOf())" in body and
        "GetBackBuffer(0, 0, D3DBACKBUFFER_TYPE_MONO," in body and
        "s.clearColor.matches(owner," in body and
        "s.sourceGameDevice == 0u || s.sourceGameDevice == owner" in body and
        "s.frameBatch.stopped" in body and
        "GameNativeOffscreenPass::preserve_transition(" in body and
        "return false; // Unproved RT changes" in body
    )

assert linked(bridge), "public DX11 game-target transition absent or internal"
assert "bool preserve_game_target_transition(IDirect3DDevice9* gameDevice) noexcept;" in header
assert "live_game_frame::preserve_game_target_transition(device)" in hook
assert '"src/vr/d3d11/live_game_frame_bridge.cpp"' in build
assert "python tools/test_dx11_game_target_linkage_00766.py" in workflow

# Recreate the historical internal-linkage regression: move the exact working
# implementation above the anonymous-namespace close and require rejection.
begin = bridge.index("// A successful R9 RT0 switch to/from a verified auxiliary game target")
end = bridge.index("bool diagnostic_enabled() noexcept", begin)
section = bridge[begin:end]
source_without = bridge[:begin] + bridge[end:]
location = source_without.index("} // namespace", source_without.index("namespace {"))
broken = source_without[:location] + section + source_without[location:]
assert not linked(broken), "anonymous-namespace linker regression undetected"
assert not linked(bridge.replace("s.clearColor.matches(owner,", "s.clearColor.matches(0u,", 1) if False else
    bridge[:bridge.index(definition)] + bridge[bridge.index(definition):].replace(
        "s.clearColor.matches(owner,", "s.clearColor.matches(0u,", 1)),  # exact-function mutation
    "foreign owner color seed mutation undetected"
print("00766 external R9 target-linkage and fail-closed DX9Ex fallback PASS")
