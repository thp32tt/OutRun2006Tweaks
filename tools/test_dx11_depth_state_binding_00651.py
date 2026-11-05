"""00651: enforce exact game Z-write/read-only 4-way OM state creation and Draw binding."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = (ROOT / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
DEPTH = (ROOT / "src/vr/d3d11/live_game_depth_state.hpp").read_text(encoding="utf-8")
PROBE = (ROOT / "tools/dx11_game_depth_probe.cpp").read_text(encoding="utf-8")


def connected(cpp: str, header: str) -> bool:
    if not all(x in header for x in (
        'constexpr std::uint32_t game_native_depth_slot(',
        'return (writeEnabled ? 2u : 0u) + (lessEqual ? 1u : 0u);',
        'output = {true, zFunc == 4u, zWrite == 1u};',
    )):
        return False
    block = cpp.split("bool submit(", 1)[1].split("void before_game_present(", 1)[0]
    # Creation and OM binding MUST use the same 4-slot selector. The old
    # binding ignored nativeDepthWrite, choosing slot 0/1 for Z-write Draws.
    selector = r"game_native_depth_slot\(\s*output\.nativeDepthWrite,\s*output\.nativeDepthLessEqual\s*\)"
    creation = r"auto& depthState\s*=\s*s\.diagnosticDepthStates\[\s*" + selector + r"\s*\]"
    binding = r"ctx->OMSetDepthStencilState\(\s*s\.diagnosticDepthStates\[\s*" + selector + r"\s*\]\.Get\(\),\s*0\s*\)"
    return (bool(re.search(creation, block)) and bool(re.search(binding, block))
            and len(re.findall(selector, block)) == 2
            and 'ds.DepthWriteMask = output.nativeDepthWrite ?' in block
            and 'D3D11_DEPTH_WRITE_MASK_ALL : D3D11_DEPTH_WRITE_MASK_ZERO' in block
            and 'ds.DepthFunc = output.nativeDepthLessEqual ?' in block
            and 'ctx->DrawIndexed(indexCount, 0, 0);' in block
            and 'ctx->Draw(static_cast<UINT>(vertices.size()), 0);' in block
            and 'if (!diagnostic_enabled() || !game' in cpp)


assert connected(BRIDGE, DEPTH)
for broken in (
    BRIDGE.replace(
        'output.nativeDepthWrite, output.nativeDepthLessEqual)].Get(), 0);',
        'false, output.nativeDepthLessEqual)].Get(), 0);', 1),
    BRIDGE.replace(
        'output.nativeDepthWrite, output.nativeDepthLessEqual)]',
        'false, output.nativeDepthLessEqual)]', 1),
    BRIDGE.replace(
        'output.nativeDepthWrite, output.nativeDepthLessEqual)].Get(), 0);',
        'output.nativeDepthWrite, false)].Get(), 0);', 1),
    # Mutate BOTH state creators: ZFUNC ALWAYS is instantiated before the
    # original LESS/LEQUAL family. Mutating only the first occurrence no
    # longer tests the legacy read-only OM write-mask assertion.
    BRIDGE.replace(
        'D3D11_DEPTH_WRITE_MASK_ALL : D3D11_DEPTH_WRITE_MASK_ZERO',
        'D3D11_DEPTH_WRITE_MASK_ALL : D3D11_DEPTH_WRITE_MASK_ALL'),
):
    assert broken != BRIDGE and not connected(broken, DEPTH)
broken_header = DEPTH.replace(
    '(writeEnabled ? 2u : 0u) + (lessEqual ? 1u : 0u)',
    '(lessEqual ? 1u : 0u)')
assert broken_header != DEPTH and not connected(BRIDGE, broken_header)
for expected in (
    'game_native_depth_slot((slot & 2u) != 0u,',
    'game_native_depth_slot(false, false) !=',
    'game_native_depth_slot(false, true) !=',
):
    assert expected in PROBE
print("00651 PASS: four Z compare/write OM slots bind exactly as created, with DX9 fallback")
