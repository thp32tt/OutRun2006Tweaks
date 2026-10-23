from pathlib import Path
root = Path(__file__).resolve().parents[1]
cpp = (root / "src/vr/d3d11/native_game_stereo_submission.cpp").read_text(encoding="utf-8")
hpp = (root / "src/vr/d3d11/native_game_eye_postpass_coverage.hpp").read_text(encoding="utf-8")
replay = cpp[cpp.index("bool NativeGameEyeDrawEncoder::replay_due_source_clears()"):
             cpp.index("bool NativeGameEyeDrawEncoder::finish_source_clear_timeline()")]
copy = replay[replay.index("Kind::SourceCopy"):replay.index("Kind::SourceStretch")]
stretch = replay[replay.index("Kind::SourceStretch"):]
# Causal 00990 source API change: returning false exposes unknown-ledger
# fragmentation loss; retain all original exact overwrite assertions.
assert "bool invalidate(NativeGameOffscreenColorRegion overwritten)" in hpp
assert "return false;" in hpp[hpp.index("bool invalidate("):hpp.index("bool empty()")]
assert "native_game_offscreen_color_regions_intersect(existing, overwritten)" in hpp
assert "regions_ = survivors;" in hpp
assert "reset();" in hpp
# Both genuine GAME GPU writes happen BEFORE their corresponding proof
# correction; unsupported writes must fail closed before GPU mutation.
assert copy.index("native_game_gpu_eye_composite_write_admissible(") < copy.index("copy_game_surface(")
assert copy.index("copy_game_surface(") < copy.index("eyeColorChronology_.record_unproven_gpu_postpass(")
assert copy.index("eyeColorChronology_.record_proven_gpu_postpass(visibleDest);") < copy.index("eyeColorChronology_.record_unproven_gpu_postpass(")
assert stretch.index("native_game_gpu_eye_composite_write_admissible(") < stretch.index("stretch_game_surface(")
assert stretch.index("stretch_game_surface(") < stretch.index("eyeColorChronology_.record_unproven_gpu_postpass(")
assert stretch.index("eyeColorChronology_.record_proven_gpu_postpass(") < stretch.index("eyeColorChronology_.record_unproven_gpu_postpass(")
assert "encoder.postpass_full_eye_coverage()" in cpp
print("DX11 chronological game Copy/Stretch eye overwrite integration PASS")
