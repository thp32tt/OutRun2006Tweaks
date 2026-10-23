from pathlib import Path
root = Path(__file__).resolve().parents[1]
cpp = (root/"src/vr/d3d11/native_game_stereo_submission.cpp").read_text(encoding="utf-8")
hpp = (root/"src/vr/d3d11/native_game_stereo_submission.hpp").read_text(encoding="utf-8")
regions = (root/"src/vr/d3d11/native_game_offscreen_color_provenance.hpp").read_text(encoding="utf-8")
assert "void NativeGameEyeDrawEncoder::remember_offscreen_color_region(" in cpp
assert "native_game_offscreen_exact_rect_union(" in cpp
assert "native_game_offscreen_color_key_matches(" in cpp
assert "record = {};" in cpp
assert "remember_offscreen_color_region(\n        texture.Get(), view.arraySlice, view.mip, region);" in cpp
assert "remember_offscreen_color_region(\n            texture.Get(), camera.arraySlice, camera.mip, filled);" in cpp
assert "void remember_offscreen_color_region(" in hpp
assert "native_game_offscreen_exact_rect_union(" in regions
# Coverage proof may live in a shared helper after a same-task renderer
# refactor. Preserve the original source-link assertion across both forms:
# direct DrawEncoder -> coverage OR DrawEncoder -> keyed proof -> coverage.
assert (
    "native_game_offscreen_color_region_fully_covered(" in cpp
    or (
        "native_game_gpu_eye_composite_source_proven(" in cpp
        and "native_game_offscreen_color_region_fully_covered(" in regions
        and "native_game_gpu_eye_composite_source_proven(" in regions
    )
)
assert "sourceClearCursor_" in cpp and "authoredColorPostpassCount_" in cpp
print("DX11 00984 keyed camera Draw/Clear compact GPU postpass source-link PASS")
