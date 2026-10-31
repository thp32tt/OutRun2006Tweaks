#!/usr/bin/env python3
"""01108: source-graph contract for authentic tiled full TARGET|Z source."""
from pathlib import Path
r=Path(__file__).resolve().parents[1]
coverage=(r/"src/vr/d3d11/native_game_clear_coverage.hpp").read_text()
bridge=(r/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
batch=(r/"src/vr/d3d11/native_game_frame_batch.hpp").read_text()
assert "kMaxFullSourceRects = 128u" in coverage
assert "std::array<ClippedRect, kMaxFullSourceRects>" in coverage
assert "count > kMaxFullSourceRects" in coverage
assert bridge.count("GameNativeClearCoverage::covers_whole(")>=3
full=bridge[bridge.index("void observe_game_clear("):bridge.index("void observe_unavailable_game_draw(")]
assert "precedingSourceMayHaveDepth" in full
assert full.index("precedingSourceMayHaveDepth") < full.index("s.frameBatch.reset();")
assert "s.frameBatch.preserve_depth_provenance_after_target_seed(" in full
assert "GameNativeClearCoverage::covers_whole(" in full
assert "GameNativeMainStencilClear::may_ignore(" in full
assert "GameNativeFullColorDepthClear::can_mirror(" in full
depth=bridge[bridge.index("bool observe_game_depth_clear("):bridge.index("void observe_game_clear(")]
assert "waitingForGameZ" in depth and "resume_after_game_full_depth_clear(" in depth
assert "sameMainDepthStencil" in depth and "coversDepth" in depth
assert "awaitingColorFillDepthReset = true" in batch
assert "return !stopped && !awaitingColorFillDepthReset" in batch
print("01108 tiled game TARGET/Z/stencil native seed and retained-depth hold source graph PASS")
