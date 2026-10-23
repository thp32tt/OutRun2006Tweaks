from pathlib import Path
root=Path(__file__).resolve().parents[1]
cpp=(root/"src/vr/d3d11/native_game_stereo_submission.cpp").read_text(encoding="utf-8")
hpp=(root/"src/vr/d3d11/native_game_offscreen_color_provenance.hpp").read_text(encoding="utf-8")
replay=cpp[cpp.index("bool NativeGameEyeDrawEncoder::replay_due_source_clears()"):cpp.index("bool NativeGameEyeDrawEncoder::finish_source_clear_timeline()")]
guard="if (!native_game_gpu_eye_composite_write_admissible("
assert replay.count(guard)==2
assert replay.index(guard)<replay.index("if (!copy_game_surface(")
assert replay.rindex(guard)<replay.index("if (!stretch_game_surface(")
assert replay.count("&nativeCameraAllocationTouched") == 2
assert "if (nativeCameraAllocationTouched &&" in cpp
assert "record.texture.Get() == source" in cpp
assert "native_game_gpu_eye_composite_write_admissible(" in hpp
assert "native_game_gpu_eye_composite_source_proven(" in cpp
assert "native_game_offscreen_color_region_fully_covered(" in hpp
assert "native_game_visible_stretch_sample_region(" in replay
assert "native_game_copy_clipped_region(" in replay
print("DX11 GPU camera native-eye COPY/STRETCH source provenance PASS")
