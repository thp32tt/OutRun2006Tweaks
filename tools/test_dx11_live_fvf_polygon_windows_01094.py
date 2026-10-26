#!/usr/bin/env python3
"""01094: protect real-game multi-window FVF native Draw frame initialization."""
from pathlib import Path

source = (Path(__file__).resolve().parents[1] /
          "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
submit = source[source.index("bool submit(State&"):source.index("bool observe_source_device(")]
observer = source[source.index("void observe("):source.index("} // namespace", source.index("void observe("))]

def safe(src_submit: str, src_observer: str) -> bool:
    return (
        "bool initializeFrame = true) noexcept" in src_submit
        and "if (initializeFrame && s.frameBatch.first_draw())" in src_submit
        and "s.backend.begin_frame(env_full_game_opt_in()" in src_submit
        and "if (oversizedFan || oversizedPointStrip)" in src_observer
        and "game_fvf_build_polygon_window(" in src_observer
        and "D3DPT_TRIANGLELIST, capture, output,\n"
            "                            first == 0u))" in src_observer
        and src_observer.count("s.frameBatch.succeeded(output.nativeDepthTest,") == 3
        and src_observer.count("s.frameBatch.record_source_draw(sourceOrdinal);") >= 3
        and "if (!success) {\n                s.frameBatch.abort();" in src_observer
    )
assert safe(submit, observer)
mutations = [
    (submit.replace("if (initializeFrame && s.frameBatch.first_draw())",
                    "if (s.frameBatch.first_draw())", 1), observer),
    (submit.replace("bool initializeFrame = true) noexcept",
                    "bool initializeFrame = false) noexcept", 1), observer),
    (submit, observer.replace("first == 0u))", "true))", 1)),
    (submit, observer.replace("first == 0u))", "false))", 1)),
    (submit, observer.replace("s.frameBatch.abort();", "/* lost abort */", 1)),
]
for a, b in mutations[:4]:
    assert not safe(a, b), "deleted native window source frame isolation"
# The preflight/error branch must not disappear even when another abort exists.
failure = observer[observer.index("if (oversizedFan || oversizedPointStrip)"):]
assert "if (!success) {\n                s.frameBatch.abort();" in failure
assert not safe(submit, observer.replace(
    "if (!success) {\n                s.frameBatch.abort();",
    "if (!success) {\n                /* lost batch abort */", 1))
print("01094 FVF window frame seed: first window only, original source abort preserved")
