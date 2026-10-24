from pathlib import Path
root = Path(__file__).resolve().parents[1]
source = (root / "src/vr/d3d11/native_game_stereo_submission.cpp").read_text(encoding="utf-8")
header = (root / "src/vr/d3d11/native_game_stereo_submission.hpp").read_text(encoding="utf-8")
ledger = (root / "src/vr/d3d11/native_game_eye_postpass_coverage.hpp").read_text(encoding="utf-8")
helper = (root / "src/vr/d3d11/native_game_stereo_draw_evidence.hpp").read_text(encoding="utf-8")
clear = source[source.index("bool NativeGameEyeDrawEncoder::clear_target_argb("):
               source.index("bool NativeGameEyeDrawEncoder::clear_depth_stencil(")]
producer = source[source.index("bool NativeGameStereoSubmission::render_game_eye_passes("):
                  source.index("bool NativeGameStereoSubmission::render_direct_eyes(")]
assert "eyeColorChronology_.record_authored_target_clear({" in clear
assert "unpredicatedEyeAtLastPartialClear_ = unpredicatedEyeDrawCount_;" in clear
assert "authored_partial_clear_full_eye_coverage()" in header
assert "full_authored_clear_eye(" in ledger
assert "(void)authoredClears_.invalidate(dest);" in ledger
assert "authoredClears_.record(dest);" in ledger
assert "authored_partial_target_mosaic_eye_ready(" in helper
assert "const bool partialClearEyeReady =" in producer
assert "encoder.unpredicated_eye_at_last_partial_clear()" in producer
assert "!partialClearEyeReady" in producer
assert "!encoder.eye_color_chronology_safe()" in producer
assert "ring_.render_eye_pair(" in producer
print("DX11 authentic partial TARGET mosaic -> native L/R frame admission linkage PASS")
