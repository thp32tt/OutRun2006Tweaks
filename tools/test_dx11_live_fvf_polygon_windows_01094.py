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
        and "if (streamedClippedPoints) {" in src_submit
        and "game_fvf_native_point_batch_window(" in src_submit
        and "ctx->Draw(count, 0u);" in src_submit
        # 01097: extending the authentic connected polygon source span to
        # the full 6144-element VB/IB requires BOTH source topologies to
        # cross the same bounded native multi-window GPU submit. Losing the
        # large-fan entry or full original-index preflight must fail this CI.
        and "const bool oversizedFan = type == D3DPT_TRIANGLEFAN &&" in src_observer
        and "const bool oversizedPointStrip = type == D3DPT_TRIANGLESTRIP &&" in src_observer
        and "std::uint64_t(primitives) * 3u > kMaxIndices" in src_observer
        and "for (UINT i=0; i<indexCount; ++i) {" in src_observer
        and "if (indices[i] >= vertexCount)" in src_observer
        # The complete original point-fill fan/strip is never split into
        # independent CPU clip transactions: an empty old first window must
        # not abort later visible game geometry or lose its source ordinal.
        # Legacy polygon windows remain mandatory for non-point fan/strip.
        and "const auto originalPointSource = game_fvf_native_original_point_source(" in src_observer
        and "if (originalPointSource.supported) {" in src_observer
        and "if (!submit(s, vertices, indices, indexCount, type,\n                        capture, output)) {" in src_observer
        and "if (oversizedFan || oversizedPointStrip)" in src_observer
        and "game_fvf_build_polygon_window(" in src_observer
        and "D3DPT_TRIANGLELIST, capture, output,\n"
            "                            first == 0u))" in src_observer
        and src_observer.count("s.frameBatch.succeeded(output.nativeDepthTest,") == 4
        and src_observer.count("s.frameBatch.record_source_draw(sourceOrdinal);") >= 4
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
    (submit, observer.replace(
        "if (originalPointSource.supported) {",
        "if (false /* missing full-source point fan/strip */) {", 1)),
    (submit, observer.replace(
        "const auto originalPointSource = game_fvf_native_original_point_source(",
        "const auto originalPointSource = suppressed_original_points(", 1)),
    (submit, observer.replace(
        "if (!submit(s, vertices, indices, indexCount, type,\n                        capture, output)) {",
        "if (false /* missing full-source GPU point dispatch */) {", 1)),
    (submit.replace(
        "game_fvf_native_point_batch_window(",
        "missing_point_gpu_batch_window(", 1), observer),
    (submit, observer.replace(
        "s.frameBatch.record_source_draw(sourceOrdinal);",
        "/* original game Draw source ordinal lost */", 1)),
    (submit, observer.replace(
        "const bool oversizedFan = type == D3DPT_TRIANGLEFAN &&",
        "const bool oversizedFan = false &&", 1)),
    (submit, observer.replace(
        "for (UINT i=0; i<indexCount; ++i) {",
        "for (UINT i=0; i<0u; ++i) {", 1)),
    (submit, observer.replace("s.frameBatch.abort();", "/* lost abort */", 1)),
]
# The seventh historical abort-only mutation is exercised separately below:
# other valid abort branches exist, so global first-occurrence removal is not
# itself a proof that the native GPU-window failure path disappeared.
for a, b in mutations[:-1]:
    assert not safe(a, b), "deleted native window source frame isolation"
# The preflight/error branch must not disappear even when another abort exists.
failure = observer[observer.index("if (oversizedFan || oversizedPointStrip)"):]
assert "if (!success) {\n                s.frameBatch.abort();" in failure
assert not safe(submit, observer.replace(
    "if (!success) {\n                s.frameBatch.abort();",
    "if (!success) {\n                /* lost batch abort */", 1))
print("01094 FVF whole-source point stream and legacy GPU polygon windows: source ordinal, first-frame seed and guarded fallback PASS")