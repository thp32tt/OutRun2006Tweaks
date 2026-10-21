from pathlib import Path
root = Path(__file__).resolve().parents[1]
cpp = (root / "src/vr/d3d11/native_game_stereo_submission.cpp").read_text(encoding="utf-8")
hpp = (root / "src/vr/d3d11/native_game_stereo_submission.hpp").read_text(encoding="utf-8")
coverage = (root / "src/vr/d3d11/native_game_eye_postpass_coverage.hpp").read_text(encoding="utf-8")
replay = cpp[cpp.index("bool NativeGameEyeDrawEncoder::replay_due_source_clears()"):
             cpp.index("bool NativeGameEyeDrawEncoder::finish_source_clear_timeline()")]
submit = cpp[cpp.index("const auto& evidence = invocation.eye[eyeIndex];"):
             cpp.index("if (!ring_.render_eye_pair(", cpp.index("const auto& evidence = invocation.eye[eyeIndex];"))]
clear = cpp[cpp.index("bool NativeGameEyeDrawEncoder::clear_target_argb("):
            cpp.index("bool NativeGameEyeDrawEncoder::clear_depth_stencil(")]
assert "NativeGameEyeColorChronology eyeColorChronology_{};" in hpp
assert "bool eye_color_chronology_safe() const noexcept" in hpp
assert "unprovenGpuRegions_.record(dest);" in coverage
assert "unknownLedgerOverflow_ = true;" in coverage
assert "!unprovenGpuRegions_.full_eye(width, height)" in coverage
assert "postpasses_.full_eye(width, height)" in coverage
assert replay.count("eyeColorChronology_.record_unproven_gpu_postpass(") == 2
assert replay.count("eyeColorChronology_.record_proven_gpu_postpass(") == 2
assert replay.index("copy_game_surface(") < replay.index("eyeColorChronology_.record_unproven_gpu_postpass(")
assert replay.index("stretch_game_surface(") < replay.rindex("eyeColorChronology_.record_unproven_gpu_postpass(")
assert "eyeColorChronology_.reset_after_full_target_clear();" in clear
assert submit.index("!encoder.eye_color_chronology_safe()") < submit.index("evidence.drawCount != encoder.draw_count()")
assert "!encoder.postpass_full_eye_coverage()" in submit
print("DX11 chronological GPU overwrite vs native Draw/Clear PASS")
