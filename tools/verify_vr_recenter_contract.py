#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

R26_PATH = ROOT / "vrhost/src/runtime/r26_recenter_hardening.hpp"
MAIN_PATH = ROOT / "vrhost/src/main_r23.cpp"
R32_PATH = ROOT / "vrhost/src/runtime/r32_direct_submit.hpp"
API_PATH = ROOT / "vrhost/src/runtime/openxr_api_compat.hpp"


def load(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"recenter contract missing {path.relative_to(ROOT)}: {exc}", file=sys.stderr)
        raise SystemExit(1)


def fail(message: str) -> None:
    print(f"VR recenter lifecycle contract FAILED: {message}", file=sys.stderr)
    raise SystemExit(1)


def body(source: str, marker: str) -> str:
    start = source.find(marker)
    if start < 0:
        fail(f"missing function marker: {marker}")
    brace = source.find("{", start)
    if brace < 0:
        fail(f"missing body for: {marker}")
    depth = 0
    for index in range(brace, len(source)):
        ch = source[index]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    fail(f"unterminated body for: {marker}")
    return ""


def require(source: str, label: str, *markers: str) -> None:
    for marker in markers:
        if marker not in source:
            fail(f"{label} missing: {marker}")


def forbid(source: str, label: str, *markers: str) -> None:
    for marker in markers:
        if marker in source:
            fail(f"{label} regained forbidden marker: {marker}")


def require_order(source: str, label: str, *markers: str) -> None:
    positions = [source.find(marker) for marker in markers]
    if min(positions) < 0:
        missing = [marker for marker, pos in zip(markers, positions) if pos < 0]
        fail(f"{label} missing ordered markers: {missing}")
    if positions != sorted(positions):
        fail(f"{label} order changed: {markers}")


r26 = load(R26_PATH)
main = load(MAIN_PATH)
r32 = load(R32_PATH)
api = load(API_PATH)

queue = body(r26, "inline void QueueApplicationRecenter() noexcept")
require_order(
    queue,
    "queue recenter fail-close",
    "PendingApplicationRecenter.store(true, std::memory_order_release)",
    "InvalidateFallbackAnchor();",
)

apply = body(r26, "inline bool ApplyPendingApplicationRecenter(")
require(
    apply,
    "application LOCAL recenter",
    "OutRunVrFinalTest::BaseLocalSpace != XR_NULL_HANDLE",
    "::xrLocateSpace(viewSpace, base, displayTime, &location)",
    "XR_SPACE_LOCATION_ORIENTATION_VALID_BIT",
    "XR_SPACE_LOCATION_POSITION_VALID_BIT",
    "create.referenceSpaceType = XR_REFERENCE_SPACE_TYPE_LOCAL",
    "create.poseInReferenceSpace = location.pose",
    "::xrCreateReferenceSpace(session, &create, &recentered)",
    "OutRunVrFinalTest::LocalSpace = recentered",
    "ApplicationSpaceGeneration.fetch_add(1, std::memory_order_acq_rel)",
    "PendingApplicationRecenter.store(false, std::memory_order_release)",
    "if (previous != XR_NULL_HANDLE && previous != base)",
    "::xrDestroySpace(previous)",
)
require_order(
    apply,
    "application LOCAL publication",
    "::xrCreateReferenceSpace(session, &create, &recentered)",
    "localSpace = recentered",
    "OutRunVrFinalTest::LocalSpace = recentered",
    "ApplicationSpaceGeneration.fetch_add(1, std::memory_order_acq_rel)",
    "PendingApplicationRecenter.store(false, std::memory_order_release)",
    "InvalidateFallbackAnchor();",
    "::xrDestroySpace(previous)",
)

requester_owner = body(
    r26, "inline bool RequesterMatchesCurrentGameProcess(")
require_order(
    requester_owner,
    "game recenter requester process ownership",
    "OutRunVrSbsCaptureOverride::FindGamePid()",
    "requesterPid != 0",
    "currentGamePid != 0",
    "requesterPid == currentGamePid",
)
discard_stale = body(r26, "inline void DiscardStaleGameRequest(")
require_order(
    discard_stale,
    "stale game recenter request disposal",
    "channel.MarkReceived(requestId);",
    "++StaleGameRequestsDropped;",
    "FirstStaleGameRequestLogged = true;",
)

poll = body(r26, "inline XrResult XRAPI_CALL PollEvent(")
require_order(
    poll,
    "game recenter requester validation before ownership",
    "if (channel.Pending(requestId, requesterPid))",
    "DWORD currentGamePid = 0;",
    "if (!RequesterMatchesCurrentGameProcess(",
    "if (!requesterPid || currentGamePid != 0)",
    "DiscardStaleGameRequest(",
    "const std::uint64_t targetGeneration =",
)
require_order(
    poll,
    "game recenter receive",
    "PendingGameTargetGeneration.store(",
    "QueueApplicationRecenter();",
    "WriteSyntheticLocalChange(eventData, XR_NULL_HANDLE);",
    "channel.MarkReceived(requestId);",
    "PendingGameRequestId.store(requestId, std::memory_order_release);",
)
focus_start = poll.find("if (PendingFocusRecenter && eventData)")
focus_end = poll.find("const XrResult result = ::xrPollEvent", focus_start)
if focus_start < 0 or focus_end <= focus_start:
    fail("focus recenter synthesis block missing")
focus_block = poll[focus_start:focus_end]
require_order(
    focus_block,
    "focus recenter synthesis",
    "if (PendingFocusRecenter && eventData)",
    "QueueApplicationRecenter();",
    "WriteSyntheticLocalChange(eventData, PendingFocusSession);",
    "PendingFocusRecenter = false;",
    "PendingFocusSession = XR_NULL_HANDLE;",
)
require(
    poll,
    "runtime reference-space normalization",
    "XR_TYPE_EVENT_DATA_REFERENCE_SPACE_CHANGE_PENDING",
    "change->referenceSpaceType = XR_REFERENCE_SPACE_TYPE_LOCAL",
    "InvalidateFallbackAnchor();",
)
require(
    poll,
    "focus-return ownership",
    "state->state == XR_SESSION_STATE_FOCUSED",
    "PendingFocusRecenter = true",
    "PendingFocusSession = state->session",
)

complete = body(
    r26, "inline bool CompletePendingGameRequestAfterVisibleProjection() noexcept")
require_order(
    complete,
    "fresh projection completion",
    "!ApplicationRecenterAppliedForPendingGameRequest()",
    "channel.MarkApplied(pending);",
    "PendingGameRequestId.compare_exchange_strong(",
    "PendingGameTargetGeneration.store(0, std::memory_order_release);",
)

end_frame = body(r26, "inline XrResult XRAPI_CALL EndFrame(")
require(
    end_frame,
    "fallback completion gate",
    "ApplicationRecenterAppliedForPendingGameRequest()",
    "XR_SUCCEEDED(result)",
    "!r24ViewFallback",
    "anchoredStartup || (endInfo && endInfo->layerCount > 0)",
    "channel.MarkApplied(pending)",
)
require_order(
    end_frame,
    "head-locked fallback rejection",
    "const bool r24ViewFallback",
    "if (pending != 0 && ApplicationRecenterAppliedForPendingGameRequest()",
    "else if (pending != 0 && r24ViewFallback)",
    "InvalidateFallbackAnchor();",
)

# R26 state is session-scoped. A destroyed OpenXR session must not leak a
# pending game/focus recenter, target generation or LOCAL fallback anchor into
# the next session created by the long-lived host process.
reset_session = body(r26, "inline void ResetSessionState() noexcept")
require_order(
    reset_session,
    "recenter session-state reset",
    "PendingFocusRecenter = false;",
    "PendingFocusSession = XR_NULL_HANDLE;",
    "PendingGameRequestId.store(0, std::memory_order_release)",
    "PendingApplicationRecenter.store(false, std::memory_order_release)",
    "ApplicationSpaceGeneration.store(0, std::memory_order_release)",
    "PendingGameTargetGeneration.store(0, std::memory_order_release)",
    "InvalidateFallbackAnchor();",
)
destroy_r26 = body(r26, "inline XrResult XRAPI_CALL DestroySession(")
require_order(
    destroy_r26,
    "recenter destroy forwarding",
    "ResetSessionState();",
    "return OutRunVrR24BlackScreenGuard::DestroySession(session);",
)
require(
    r26,
    "recenter destroy hook",
    "#define xrDestroySession OutRunVrR26RecenterHardening::DestroySession",
)

# The immutable base LOCAL must survive repeated application-space recenters and
# be released only during session teardown when it differs from the active LOCAL.
create_space = body(api, "inline XrResult XRAPI_CALL CreateReferenceSpace(")
require_order(
    create_space,
    "base LOCAL capture",
    "if (BaseLocalSpace == XR_NULL_HANDLE)",
    "BaseLocalSpace = *space",
    "LocalSpace = *space",
)
destroy_session = body(api, "inline XrResult XRAPI_CALL DestroySession(")
require(
    destroy_session,
    "base LOCAL teardown",
    "BaseLocalSpace != XR_NULL_HANDLE",
    "BaseLocalSpace != LocalSpace",
    "::xrDestroySpace(BaseLocalSpace)",
    "BaseLocalSpace = XR_NULL_HANDLE",
    "LocalSpace = XR_NULL_HANDLE",
)

# The host must consume the synthetic LOCAL change and invalidate all pose/layer
# caches before applying the new application LOCAL; that application must occur
# after xrBeginFrame but before either head or stereo view locate.
main_frame_start = main.find("if (pendingReferenceSpaceChange &&")
main_frame_end = main.find("const std::uint32_t hostSequence =", main_frame_start)
if main_frame_start < 0 or main_frame_end <= main_frame_start:
    fail("main frame recenter transaction missing")
main_frame = main[main_frame_start:main_frame_end]
require(
    main_frame,
    "main reference-space invalidation",
    "shared.ReferenceSpaceChanged()",
    "compositor.ReferenceSpaceChanged()",
    "viewHistory.Clear()",
    "matchedStereoValid = false",
    "cachedProjectionValid = false",
    "cachedMenuProjectionValid = false",
    "OutRunVrR23VerifiedBundle::Invalidate()",
)
require_order(
    main_frame,
    "main application-space locate order",
    "XrFrameBeginInfo bi",
    "xrBeginFrame(session, &bi)",
    "OutRunVrR26RecenterHardening::ApplyPendingApplicationRecenter(",
    "xrLocateSpace(viewSpace, localSpace, fs.predictedDisplayTime, &head)",
    "vl.space = localSpace",
    "xrLocateViews(session, &vl, &vs, 2, &vc, views.data())",
)

# A focus recenter blocks the fast path until its synthetic event has been
# consumed. A game F10 request deliberately stays fast-path eligible so the first
# fresh DirectGPU projection can be the visible completion proof.
can_fast = body(r32, "inline bool CanFastSubmit(")
require(
    can_fast,
    "DirectGPU focus recenter gate",
    "OutRunVrR26RecenterHardening::PendingFocusRecenter",
    "FastRejectReason::PendingRecenter",
)
forbid(
    can_fast,
    "DirectGPU game recenter path",
    "PendingGameRequestId.load",
    "PendingGameRequestId.store",
    "PendingApplicationRecenter.load",
    "PendingApplicationRecenter.store",
)
direct_end = body(r32, "inline XrResult XRAPI_CALL EndFrame(")
require_order(
    direct_end,
    "DirectGPU visible recenter completion",
    "const bool submitted = XR_SUCCEEDED(result)",
    "RecordFinalSubmission(",
    "if (submitted)",
    "CompletePendingGameRequestAfterVisibleProjection();",
)

print(
    "VR recenter lifecycle contract PASS "
    "(application LOCAL before locate, immutable base LOCAL, "
    "cache invalidation, fresh-visible completion)"
)
