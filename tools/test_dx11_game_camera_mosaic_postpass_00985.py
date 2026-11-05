from pathlib import Path
root = Path(__file__).resolve().parents[1]
cpp = (root / "src/vr/d3d11/native_game_stereo_submission.cpp").read_text(encoding="utf-8")
hpp = (root / "src/vr/d3d11/native_game_offscreen_color_provenance.hpp").read_text(encoding="utf-8")
assert "const bool saturated = (std::all_of)(" in cpp
assert "native_game_offscreen_color_mosaic_compaction(" in cpp
assert "native_game_offscreen_color_key_matches(" in cpp
assert "native_game_offscreen_color_region_fully_covered(" in hpp
print("DX11 00985 mosaic source integration PASS")
