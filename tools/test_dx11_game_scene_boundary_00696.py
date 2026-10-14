#!/usr/bin/env python3
"""00696: real game Clear/RT0 events invalidate partially native menu/race scenes."""
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
batch = (ROOT / "src/vr/d3d11/native_game_frame_batch.hpp").read_text()
bridge = (ROOT / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
header = (ROOT / "src/vr/d3d11/live_game_frame_bridge.hpp").read_text()
hook = (ROOT / "src/vr/d3d9/stereo_renderer.cpp").read_text()
workflow = (ROOT / ".github/workflows/dx11-fast-structural.yml").read_text()

def connected(b, c, h, r):
    rt = r.split("HRESULT __stdcall SetRenderTargetDestR9(", 1)[-1].split(
        "HRESULT __stdcall ClearDestR9(", 1)[0]
    clear = r.split("HRESULT __stdcall ClearDestR9(", 1)[-1].split(
        "HRESULT __stdcall ", 1)[0]
    # Keep the historical boundary assertion scoped to that callback. The
    # 00728 full-Clear restart legitimately has another s.pending=false in
    # observe_game_clear(), which must not mask a broken scene boundary.
    event = c.split("void observe_scene_boundary(", 1)[-1].split(
        "void observe_game_clear(", 1)[0]
    present = c.split("void before_game_present(", 1)[-1].split(
        "void before_game_reset(", 1)[0]
    return all((
        'vr/d3d11/live_game_frame_bridge.hpp' in r,
        "live_game_frame::diagnostic_enabled()" in rt,
        "device->GetRenderTarget(0, &previous)" in rt,
        "previous != surface" in rt,
        "previous->QueryInterface(" in rt,
        "surface->QueryInterface(" in rt,
        "IID_IUnknown, reinterpret_cast<void**>(&previousIdentity)" in rt,
        "IID_IUnknown, reinterpret_cast<void**>(&nextIdentity)" in rt,
        "previousIdentity != nextIdentity" in rt,
        "if (previousIdentity) previousIdentity->Release();" in rt,
        "if (nextIdentity) nextIdentity->Release();" in rt,
        "if ((flags & (D3DCLEAR_TARGET | D3DCLEAR_ZBUFFER |" in clear,
        "if (previous) previous->Release();" in rt,
        "SUCCEEDED(hr) && nativeTargetChanged" in rt,
        "live_game_frame::observe_scene_boundary(device)" in rt,
        "if (!IsGameDevice(device) || InternalStereoPass)" in clear,
        "live_game_frame::observe_scene_boundary(device)" in clear,
        0 <= clear.find("live_game_frame::observe_scene_boundary(device)") <
            clear.find("++R9ClearCalls;"),
        "void observe_scene_boundary(IDirect3DDevice9* gameDevice) noexcept;" in h,
        "if (!diagnostic_enabled() || !game) return;" in event,
        "s.sourceGameDevice != reinterpret_cast<std::uintptr_t>(game)" in event,
        "s.frameBatch.scene_boundary();" in event,
        "s.pending = false;" in event,
        "if (submitted != 0u) stopped = true;" in b,
        "s.frameBatch.publishable_full(s.pending, s.sourceDrawsThisFrame)" in present,
        ": s.frameBatch.publishable(s.pending);" in present,
        "if (complete && outputWritable &&" in present,
        "ctx->CopyResource(next.staging.Get(), s.backend.color_texture())" in present,
    ))

assert connected(batch, bridge, header, hook), "Clear/RT0 -> native batch -> GPU readback integration"
for name, body, token in (
    ("rt0 owner query", hook, "device->GetRenderTarget(0, &previous)"),
    ("rt0 successful switch", hook, "SUCCEEDED(hr) && nativeTargetChanged"),
    ("rt0 canonical COM alias", hook, "previousIdentity != nextIdentity"),
    ("rt0 identity lifetime", hook, "if (nextIdentity) nextIdentity->Release();"),
    ("zero-flags Clear survives", hook, "if ((flags & (D3DCLEAR_TARGET | D3DCLEAR_ZBUFFER |"),
    ("clear event", hook, "outrun::vr::dx11::live_game_frame::observe_scene_boundary(device);\n\t\t\t++R9ClearCalls;"),
    ("gpu boundary discard", bridge, "s.frameBatch.scene_boundary();"),
    ("pending upload discard", bridge, "s.pending = false;\n    } catch (...)"),
    ("frame-batch stop", batch, "if (submitted != 0u) stopped = true;"),
):
    mutant = body.replace(token, "/* deliberately broken 00696 */", 1)
    assert mutant != body, name
    a, b, c, d = batch, bridge, header, hook
    if body is hook: d = mutant
    elif body is bridge: b = mutant
    else: a = mutant
    assert not connected(a, b, c, d), name

assert "python tools/test_dx11_game_scene_boundary_00696.py" in workflow
compiler = shutil.which("g++") or shutil.which("clang++")
assert compiler, "portable C++17 compiler required"
code = r"""
#include "native_game_frame_batch.hpp"
using outrun::vr::dx11::live_game_frame::GameNativeFrameBatch;
constexpr bool check() {
    GameNativeFrameBatch b{};
    b.scene_boundary();  // scene begins with a game Clear: no prior native pixels
    if (!b.accepts(0u, 0u, false) || b.stopped) return false;
    b.succeeded(false);
    if (!b.publishable(true)) return false;
    b.scene_boundary();  // a game Clear or RT0 switch invalidates submitted pixels
    if (b.publishable(true) || b.accepts(1u, 0u, true)) return false;
    b.reset(); // next Present, same device, fresh scene
    if (!b.accepts(0u, 0u, true)) return false;
    for (unsigned i = 0; i < GameNativeFrameBatch::kMaxDraws; ++i)
        b.succeeded(false);
    if (!b.publishable(true)) return false;
    b.scene_boundary(); // also invalidate full batches, not just partial ones
    if (b.publishable(true)) return false;
    b.reset();
    return b.accepts(0u, 0u, false) && !b.publishable(false);
}
static_assert(check(), "native game Clear/RT0 must never publish stale scenes");
int main() { return check() ? 0 : 1; }
"""
with TemporaryDirectory(prefix="dx11-00696-") as dirname:
    path = Path(dirname)
    (path / "probe.cpp").write_text(code)
    cmd = [compiler, "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
           "-pedantic", "-I", str(ROOT / "src/vr/d3d11"),
           str(path / "probe.cpp"), "-o", str(path / "probe")]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert subprocess.run([str(path / "probe")]).returncode == 0
print("PASS 00696: D3D9 Clear/RT0 -> native Draw/DrawIndexed batch -> GPU readback fail-closed")
