#!/usr/bin/env python3
"""Game-authored D3D9 ColorFill -> clipped native full-frame ClearView integration."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
header = (root / "src/vr/d3d11/native_game_source_mutation.hpp").read_text(encoding="utf-8")
region = bridge.split("bool preserve_game_color_fill(", 1)[1].split(
    "\nvoid observe_scene_boundary(", 1)[0]
def wired(b, h):
    # The production header contains two different atomic records; the
    # negative mutation must inspect the ColorFill recorder itself rather
    # than pass on a second unrelated target-clear commit.
    rec = h.split("constexpr bool record(", 1)[1].split(
        "constexpr bool record_target_clear(", 1)[0]
    return all((
        "GameNativeSourceMutation::classify_color_fill_rect(" in b,
        "clipped.left == 0 && clipped.top == 0" in b,
        "coverage == GameNativeSourceMutation::ColorFillClip::Empty" in b,
        "return sameGameBackbuffer && s.sourceGameDevice == owner" in b,
        "s.preDrawFills.record(owner," in b,
        "clipped.left, clipped.top, clipped.right, clipped.bottom," in b,
        "const D3D11_RECT nativeRect{" in b,
        "static_cast<LONG>(clipped.left)" in b,
        "context1->ClearView(s.backend.color_rtv(), rgba, &nativeRect, 1u)" in b,
        "classify_color_fill_rect(" in h,
        # 01034: newer ColorFill can fully supersede older game-authored
        # rectangles, but overflow of genuinely distinct pixels stays closed.
        # 01104: source remains overwrite-equivalent when adjacent same
        # ARGB rects can fuse; capacity and owner failure stay transactional.
        # 01106: exact edge removal does not change the atomic native
        # ColorFill transaction, and interior/split overlap stays ordered.
        "Fill saved = entries[i];" in rec,
        "if (!covers(next, saved)) {" in rec,
        "(void)game_native_trim_partially_overwritten(saved, next);" in rec,
        "staged.entries[output++] = saved;" in rec,
        "if (output >= kCapacity) return false;" in rec,
        rec.count("game_native_merge_ordered_overwrite(") == 2,
        "staged.entries[output++] = next;" in rec,
        "*this = staged;" in rec,
    ))
assert wired(region, header)
for original, broken in (
    ("clipped.left == 0 && clipped.top == 0", "true /* always entire surface */"),
    ("static_cast<LONG>(clipped.left)", "rect->left"),
    ("s.preDrawFills.record(owner,", "s.preDrawFills.omitted_record(owner,"),
    ("coverage == GameNativeSourceMutation::ColorFillClip::Empty", "false"),
):
    assert original in region
    assert not wired(region.replace(original, broken, 1), header), original
# Reject mutations that drop the actual capacity/transaction boundary.
for original in ("if (output >= kCapacity) return false;",
                 "*this = staged;", "game_native_merge_ordered_overwrite(",
                 "(void)game_native_trim_partially_overwritten(saved, next);"):
    assert original in header
    assert not wired(region, header.replace(original, "/* omitted */", 1)), original
print("00799 clipped D3D9 ColorFill native game frame source integration PASS")
