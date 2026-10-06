from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R23_PATH = ROOT / "vrhost/src/runtime/r23_runtime_hardening.hpp"
R24_PATH = ROOT / "vrhost/src/runtime/r24_black_screen_guard.hpp"
R32_PATH = ROOT / "vrhost/src/runtime/r32_direct_submit.hpp"


def fail(message: str) -> None:
    raise SystemExit(f"VR final-submission contract FAIL: {message}")


def load(path: Path) -> str:
    if not path.is_file():
        fail(f"missing {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def body(source: str, signature: str) -> str:
    start = source.find(signature)
    if start < 0:
        fail(f"missing function {signature}")
    brace = source.find("{", start)
    if brace < 0:
        fail(f"missing body for {signature}")
    depth = 0
    for pos in range(brace, len(source)):
        if source[pos] == "{":
            depth += 1
        elif source[pos] == "}":
            depth -= 1
            if depth == 0:
                return source[brace:pos + 1]
    fail(f"unterminated body for {signature}")
    return ""


def require(source: str, label: str, *markers: str) -> None:
    for marker in markers:
        if marker not in source:
            fail(f"{label}: missing {marker!r}")


def require_order(source: str, label: str, *markers: str) -> None:
    cursor = -1
    for marker in markers:
        pos = source.find(marker, cursor + 1)
        if pos < 0:
            fail(f"{label}: missing {marker!r}")
        if pos < cursor:
            fail(f"{label}: out-of-order {marker!r}")
        cursor = pos


r23 = load(R23_PATH)
r24 = load(R24_PATH)
r32 = load(R32_PATH)

owner = body(r23, "inline XrResult RecordFinalSubmissionResult(")
require_order(
    owner,
    "result-aware final submission owner",
    "RecordFinalSubmission(frameId, kind,",
    "XR_SUCCEEDED(result) && intendedHasLayer",
    "return result;",
)

if "OutRunVrR23RuntimeHardening::RecordFinalSubmission(" in r24:
    fail("R24 bypasses result-aware owner with a direct final-submission write")

submit_original = body(r24, "inline XrResult SubmitOriginal(")
require_order(
    submit_original,
    "classic projection result ordering",
    "OutRunVrFinalTest::EndFrame(session, endInfo)",
    "RecordFinalSubmissionResult(",
    "result, snapshot.frameId, snapshot.kind, true",
)

direct_safe = body(r24, "inline bool TrySubmitDirectSafeProjection(")
require_order(
    direct_safe,
    "direct SafeEye result ordering",
    "result = OutRunVrFinalTest::EndFrame(session, &patched);",
    "RecordFinalSubmissionResult(",
    "result, snapshot.frameId, snapshot.kind, true",
    "return true;",
)

visible = body(r24, "inline XrResult SubmitVisibleFallback(")
require(
    visible,
    "visible fallback result ownership",
    "SubmitNoLayer(session, endInfo)",
    "RecordFinalSubmissionResult(",
    "OutRunVrFinalTest::EndFrame(session, &patched)",
)
no_layer_pos = visible.find("SubmitNoLayer(session, endInfo)")
no_layer_record = visible.find("RecordFinalSubmissionResult(", no_layer_pos)
visible_end = visible.rfind("OutRunVrFinalTest::EndFrame(session, &patched)")
visible_record = visible.find("RecordFinalSubmissionResult(", visible_end)
if min(no_layer_pos, no_layer_record, visible_end, visible_record) < 0:
    fail("visible fallback result-aware ordering missing")
if not (no_layer_pos < no_layer_record and visible_end < visible_record):
    fail("visible fallback records before actual EndFrame result")

end_frame = body(r24, "inline XrResult XRAPI_CALL EndFrame(")
require(
    end_frame,
    "R24 top-level result-aware submission",
    "IntentionalMonoProjectionSubmits",
    "MixedValidatedSubmits",
    "OutRunVrSbsCaptureOverride::EndFrame(session, endInfo)",
    "RecordFinalSubmissionResult(",
)
if end_frame.count("RecordFinalSubmissionResult(") < 4:
    fail("R24 top-level paths are not consistently result-aware")

# Keep the already-correct R32 fast path as the reference contract: result first,
# success-derived submitted flag second, final-state publication third.
r32_end = body(r32, "inline XrResult XRAPI_CALL EndFrame(")
require_order(
    r32_end,
    "R32 result-aware reference path",
    "const XrResult result =",
    "const bool submitted = XR_SUCCEEDED(result)",
    "RecordFinalSubmission(",
)

print("VR final-submission contract PASS (R24 final state follows actual xrEndFrame result)")
