from pathlib import Path
root = Path(__file__).resolve().parents[1]
cpp = (root / "src/vr/d3d11/native_game_stereo_submission.cpp").read_text(encoding="utf-8")
hpp = (root / "src/vr/d3d11/native_game_eye_postpass_coverage.hpp").read_text(encoding="utf-8")
replay = cpp[cpp.index("bool NativeGameEyeDrawEncoder::replay_due_source_clears()"):
             cpp.index("bool NativeGameEyeDrawEncoder::finish_source_clear_timeline()")]
copy = replay[replay.index("Kind::SourceCopy"):replay.index("Kind::SourceStretch")]
stretch = replay[replay.index("Kind::SourceStretch"):]
assert "void invalidate(NativeGameOffscreenColorRegion overwritten)" in hpp
assert "native_game_offscreen_color_regions_intersect(existing, overwritten)" in hpp
assert "regions_ = survivors;" in hpp
assert "reset();" in hpp
# Both genuine GAME GPU writes happen BEFORE their corresponding proof
# correction; unsupported writes must fail closed before GPU mutation.
assert copy.index("native_game_gpu_eye_composite_write_admissible(") < copy.index("copy_game_surface(")
assert copy.index("copy_game_surface(") < copy.index("eyePostpassCoverage_.invalidate(visibleDest);")
assert copy.index("eyePostpassCoverage_.record(visibleDest);") < copy.index("eyePostpassCoverage_.invalidate(visibleDest);")
assert stretch.index("native_game_gpu_eye_composite_write_admissible(") < stretch.index("stretch_game_surface(")
assert stretch.index("stretch_game_surface(") < stretch.index("eyePostpassCoverage_.invalidate(")
assert stretch.index("eyePostpassCoverage_.record(") < stretch.index("eyePostpassCoverage_.invalidate(")
assert "encoder.postpass_full_eye_coverage()" in cpp
print("DX11 chronological game Copy/Stretch eye overwrite integration PASS")
