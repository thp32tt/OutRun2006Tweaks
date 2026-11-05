from pathlib import Path
root = Path(__file__).resolve().parents[1]
cpp = (root / "src/vr/d3d11/native_game_stereo_submission.cpp").read_text(encoding="utf-8")
coverage = (root / "src/vr/d3d11/native_game_eye_postpass_coverage.hpp").read_text(encoding="utf-8")
replay = cpp[cpp.index("bool NativeGameEyeDrawEncoder::replay_due_source_clears()"):
             cpp.index("bool NativeGameEyeDrawEncoder::finish_source_clear_timeline()")]
clear = cpp[cpp.index("bool NativeGameEyeDrawEncoder::clear_target_argb("):
            cpp.index("bool NativeGameEyeDrawEncoder::clear_depth_stencil(")]
assert replay.count("eyeColorChronology_.record_unproven_gpu_postpass(") == 2
assert "visibleDest, targetWidth_, targetHeight_" in replay
assert "targetWidth_, targetHeight_);" in replay
assert "eyeColorChronology_.record_authored_target_clear({" in clear
assert clear.index("eyeColorChronology_.reset_after_full_target_clear();") < clear.index("eyeColorChronology_.record_authored_target_clear({")
assert "completeUnknownReplacement_ = true;" in coverage
assert "!completeUnknownReplacement_" in coverage
assert "if (!unprovenGpuRegions_.invalidate(dest))" in coverage
assert "(void)postpasses_.invalidate(dest);" in coverage
assert "return false;" in coverage[coverage.index("bool invalidate("):coverage.index("[[nodiscard]] bool empty()")]
print("DX11 native eye real TARGET Clear + source-proven GPU repair chronology PASS")
