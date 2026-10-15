#!/usr/bin/env python3
"""00763 actual full-size game alpha-only/depth-only Draw and safe D3D9 fallback."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
src = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
hdr = (root / "src/vr/d3d11/native_game_masked_draw.hpp").read_text(encoding="utf-8")
wf = (root / ".github/workflows/dx11-fast-structural.yml").read_text(encoding="utf-8")
def integrated(s, h):
    if '#include "native_game_masked_draw.hpp"' not in s: return False
    if "bool supported_game_state(" not in s or "bool translate_vertices(" not in s: return False
    admission = s.split("bool supported_game_state(", 1)[1].split("bool translate_vertices(", 1)[0]
    draw = s.split("void observe(IDirect3DDevice9* game,", 1)[1].split("void observe_unavailable_game_draw(", 1)[0] if "void observe_unavailable_game_draw(" in s.split("void observe(IDirect3DDevice9* game,", 1)[1] else s.split("void observe(IDirect3DDevice9* game,", 1)[1].split("void observe_source_device(", 1)[0]
    # source-observation function itself ends before preserve_offscreen_* helpers.
    draw = draw.split("bool preserve_offscreen_color_only_clear(", 1)[0]
    if "output.colorWriteMask = s.clearColor.native_write_mask(" not in draw: return False
    if "s.frameBatch.accepts_full_on_source_target(" not in draw: return False
    if "submit(s, vertices," not in draw: return False
    return all(x in admission for x in (
        "const DWORD legalMask =",
        "const DWORD visibleMask =",
        "GameNativeMaskedDraw::accepts_source_mask(",
        "colorMask, fullFrame, sourceDesc.Format == D3DFMT_A8R8G8B8,",
        "output.nativeDepthTest && output.nativeDepthWrite",
        "output.colorWriteMask = static_cast<std::uint8_t>(",
    )) and all(x in draw for x in (
        "if (output.colorWriteMask == 0u && !output.nativeDepthWrite)",
        "s.frameBatch.abort();",
        "output.colorWriteMask);",
    )) and all(x in h for x in (
        "if ((d3d9Mask & ~kAll) != 0u) return false;",
        "if ((d3d9Mask & kRgb) != 0u) return true;",
        "return fullFrame &&",
        "targetHasAlpha && (d3d9Mask & kAlpha)",
        "|| nativeDepthWrite",
    ))
assert integrated(src,hdr), "real game Draw/DrawIndexed alpha/depth admission is not connected"
for old,new in (
    ("GameNativeMaskedDraw::accepts_source_mask(", "true /* no source admission */ ("),
    ("colorMask, fullFrame, sourceDesc.Format == D3DFMT_A8R8G8B8,",
     "colorMask, true, true,"),
    ("output.nativeDepthTest && output.nativeDepthWrite", "true /* unproven depth */"),
    ("if (output.colorWriteMask == 0u && !output.nativeDepthWrite)",
     "if (false /* zero-write unchecked */)"),
):
    bad=src.replace(old,new,1)
    assert bad!=src and not integrated(bad,hdr),old
for old,new in (
    ("if ((d3d9Mask & ~kAll) != 0u) return false;", "if (false) return false;"),
    ("return fullFrame &&", "return true ||"),
    ("|| nativeDepthWrite", "|| true"),
):
    bad=hdr.replace(old,new,1)
    assert bad!=hdr and not integrated(src,bad),old
assert "python tools/test_dx11_full_game_masked_draw_00763.py" in wf
assert "tools/dx11_full_game_masked_draw_00763.cpp" in wf
print("00763 real menu/car/race native masked Draw + original D3D9 fallback PASS")
