from pathlib import Path
root=Path(__file__).resolve().parents[1]
cpp=(root/"src/vr/d3d11/native_game_stereo_submission.cpp").read_text(encoding="utf-8")
hpp=(root/"src/vr/d3d11/native_game_stereo_submission.hpp").read_text(encoding="utf-8")
cov=(root/"src/vr/d3d11/native_game_eye_postpass_coverage.hpp").read_text(encoding="utf-8")
replay=cpp[cpp.index("bool NativeGameEyeDrawEncoder::replay_due_source_clears()"):cpp.index("bool NativeGameEyeDrawEncoder::finish_source_clear_timeline()")]
ready=cpp[cpp.index("if (!live_game_stereo::authored_visible_eye_frame_ready("):]
assert replay.count("eyeColorChronology_.record_proven_gpu_postpass(")==2
assert replay.count("if (proven) {")==1
assert replay.count("if (proven && visibleDest.valid) {")==1
assert replay.index("if (!copy_game_surface(")<replay.index("eyeColorChronology_.record_proven_gpu_postpass(")
assert replay.index("if (!stretch_game_surface(")<replay.rindex("eyeColorChronology_.record_proven_gpu_postpass(")
assert "clipped.destX" in replay and "visibleDest.valid" in replay
assert "eyeColorChronology_.reset_after_full_target_clear();" in cpp
assert "postpass_full_eye_coverage()" in ready
assert "encoder.authored_full_color_clear_count() == 0u" in ready
assert "encoder.color_draw_count() == 0u" in ready
assert "NativeGameEyeColorChronology eyeColorChronology_" in hpp
assert "native_game_offscreen_color_region_fully_covered(" in cov
assert "native_game_offscreen_exact_rect_union(" in cov
print("DX11 native authored GPU postpass destination eye coverage PASS")
