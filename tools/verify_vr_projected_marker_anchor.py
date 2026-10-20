#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEMANTICS = ROOT / "src/vr/game/render_semantics.hpp"
UI = ROOT / "src/hooks_uiscaling.cpp"
RANK_FRACTION = ROOT / "src/vr/game/rank_marker_fraction.hpp"
FRAMERATE = ROOT / "src/hooks_framerate.cpp"
R30 = ROOT / "src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp"
R84 = ROOT / "src/vr/d3d9/stereo_renderer_r30.cpp"
RANK_PHYSICAL = ROOT / "src/vr/game/rank_marker_physical_source.hpp"
RANK_STEREO = ROOT / "src/vr/game/projected_rank_stereo.hpp"


def fail(message: str) -> None:
    raise SystemExit(
        "VR projected marker anchor contract FAILED\n"
        f" - {message}"
    )


def read(path: Path) -> str:
    if not path.is_file():
        fail(f"missing required source: {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def function_body(source: str, marker: str) -> str:
    start = source.find(marker)
    if start < 0:
        fail(f"missing function marker: {marker}")
    brace = source.find("{", start)
    if brace < 0:
        fail(f"missing function body: {marker}")
    depth = 0
    for i in range(brace, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[brace + 1:i]
    fail(f"unterminated function body: {marker}")
    return ""


semantics = read(SEMANTICS)
ui = read(UI)
rank_fraction = read(RANK_FRACTION)
framerate = read(FRAMERATE)
r30 = read(R30)
r84 = read(R84)
rank_physical = read(RANK_PHYSICAL)
rank_stereo = read(RANK_STEREO)

# Exact projected rank/rival markers must carry a recovered game-view anchor.
for marker in (
    "ProjectedWorldMarker2D",
    "struct ProjectedMarkerInfo",
    "float viewX = 0.0f;",
    "float viewY = 0.0f;",
    "float viewZ = 0.0f;",
    "CurrentQueueProjectedMarker",
    "CurrentProjectedMarker()",
    "CorroboratesProjectedWorldMarker",
):
    if marker not in semantics:
        fail(f"render semantic projected-marker contract missing: {marker}")

tag_start = semantics.find("struct SpriteNodeSemanticTag")
register_start = semantics.find("inline constexpr std::size_t SpriteNodeSemanticCapacity", tag_start)
if tag_start < 0 or register_start <= tag_start:
    fail("SpriteNodeSemanticTag block is missing")
tag = semantics[tag_start:register_start]
for marker in (
    "ProducerToken producer = ProducerToken::None;",
    "ProjectedMarkerInfo projectedMarker{};",
):
    if marker not in tag:
        fail(f"SpriteNode tag lost projected/provenance field: {marker}")

for marker in (
    "ProducerToken producer = ProducerToken::None,",
    # The +TIME registry path extends registration; projected marker is still
    # mandatory, with an additional exact producer entry-serial argument.
    "const ProjectedMarkerInfo* projectedMarker = nullptr,",
    "std::uint64_t preserveNewerExactSince = 0) noexcept",
):
    if marker not in semantics:
        fail(f"registration signature does not preserve projected marker: {marker}")
register = function_body(semantics, "inline void RegisterSpriteNodeScope(")
if "projectedMarker ? *projectedMarker : ProjectedMarkerInfo{}" not in register:
    fail("registration body does not persist projected marker payload")

if "ProjectedMarkerInfo* projectedMarker = nullptr) noexcept" not in semantics:
    fail("non-consuming lookup signature lost projected marker output")
peek = function_body(semantics, "inline RenderScope PeekSpriteNodeScope(")
for marker in (
    "*projectedMarker = {};",
    "*projectedMarker = SpriteNodeSemanticTags[i].projectedMarker;",
):
    if marker not in peek:
        fail(f"non-consuming projected marker lookup missing: {marker}")

consume = function_body(semantics, "inline RenderScope ConsumeSpriteNodeScope(")
for marker in (
    "CurrentQueueProjectedMarker = {};",
    "CurrentQueueProjectedMarker =",
    "SpriteNodeSemanticTags[i].projectedMarker",
):
    if marker not in consume:
        fail(f"queue consume does not publish projected marker: {marker}")

select = function_body(semantics, "inline void SelectSpriteQueueNode(")
if "CurrentQueueProjectedMarker = {};" not in select:
    fail("queue node selection must clear stale projected marker before consume")
end = function_body(semantics, "inline void EndSpriteQueueRender() noexcept")
if "CurrentQueueProjectedMarker = {};" not in end:
    fail("queue end must clear current projected marker")

# Recovered finite screen values can still overflow to infinity during the
# x*(-z)/scale inverse. A poisoned projected anchor can propagate through
# replay/queue metadata to the eye transforms, so validity must be published
# only after both computed view coordinates are confirmed finite.
def require_finite_projected_anchor(calc_body: str) -> None:
    x = calc_body.find("info.viewX = out->x * (-out->z) / a1;")
    y = calc_body.find("info.viewY = out->y * (-out->z) / a2;")
    fx = calc_body.find("!std::isfinite(info.viewX)")
    fy = calc_body.find("!std::isfinite(info.viewY)")
    clear = calc_body.find("info = {};", fy)
    valid = calc_body.find("info.valid = true;", y)
    if min(x, y, fx, fy, clear, valid) < 0 or not (
        x < y < fx < fy < clear < valid
    ):
        fail("Calc3D2D anchor must reject nonfinite inverse coordinates before valid=true")


# Only exact Calc3D2D callsites for rank/rival may populate this payload.
calc = function_body(ui, "static void Calc3D2D_dest(")
for marker in (
    "_ReturnAddress()",
    "Module::exe_ptr(0xBAEE7)",
    "Module::exe_ptr(0xBB6F5)",
    "RankMarkerProjectedInfo",
    "RivalMarkerProjectedInfo",
    "info.viewX = out->x * (-out->z) / a1;",
    "info.viewY = out->y * (-out->z) / a2;",
):
    if marker not in calc:
        fail(f"Calc3D2D anchor recovery missing: {marker}")

require_finite_projected_anchor(calc)

# The exact original 0xBAEE7 return edge is authoritative, but the
# independently hooked sub_4BAD20 rank-producer lifetime can salvage the
# same view-space anchor if x86 inline-hook return-site provenance drifts.
# Neither condition may become a requirement for the other; NaviPub
# ScreenHud scopes must always block vehicle-world capture.
def require_historical_rank_capture_gate(body: str) -> None:
    for marker in (
        "returnAddress == Module::exe_ptr(0xBAEE7)",
        "ordinalProducerScope = RankMarkerSubActiveDepth != 0",
        "ordinalReturnSite || ordinalProducerScope",
        "RankMarkerSubScreenHudDepth == 0",
        "recoverViewPoint(RankMarkerProjectedInfo, true);",
    ):
        if marker not in body:
            fail("rank two-path exact ownership lost: " + marker)
    section = body[body.index("const bool ordinalReturnSite ="):
                   body.index("recoverViewPoint(RankMarkerProjectedInfo, true);",
                              body.index("const bool ordinalReturnSite ="))]
    if not (section.index("ordinalReturnSite || ordinalProducerScope") <
            section.index("RankMarkerSubScreenHudDepth == 0")):
        fail("NaviPub ScreenHud exclusion must guard both ordinal sources")
    if "ordinalReturnSite && ordinalProducerScope" in section:
        fail("rank fallback must never REQUIRE optional sub-entry hook")

require_historical_rank_capture_gate(calc)
for label, bad_gate in (
    ("rank exact 0xBAEE7 lost", calc.replace(
        "returnAddress == Module::exe_ptr(0xBAEE7)",
        "returnAddress == Module::exe_ptr(0xBAEE8)", 1)),
    ("parent salvage lost", calc.replace(
        "ordinalReturnSite || ordinalProducerScope",
        "ordinalReturnSite && ordinalProducerScope", 1)),
    ("NaviPub exclusion lost", calc.replace(
        "RankMarkerSubScreenHudDepth == 0",
        "RankMarkerSubScreenHudDepth >= 0", 1)),
):
    if bad_gate == calc:
        fail("rank capture-gate fault injection failed: " + label)
    try:
        require_historical_rank_capture_gate(bad_gate)
    except SystemExit:
        pass
    else:
        fail("rank capture-gate regression escaped: " + label)

# The ordinal rank producer has the actual view-space input before
# Calc3D2D flattens its result. Accept it only with a matching original
# game-screen projection; keep the previously HMD-confirmed rival unchanged.
def require_rank_original_input(source: str) -> None:
    body = function_body(source, "static void Calc3D2D_dest(")
    for marker in (
        "const D3DVECTOR originalInput = in ? *in : D3DVECTOR{};",
        "const bool finiteInput = in &&",
        "const float projectedX =",
        "const float projectedY =",
        "std::fabs(projectedX - out->x)",
        "std::fabs(projectedY - out->y)",
        "info.viewX = originalInput.x;",
        "info.viewY = originalInput.y;",
        "info.viewZ = originalInput.z;",
        "recoverViewPoint(RankMarkerProjectedInfo, true);",
        "recoverViewPoint(RivalMarkerProjectedInfo, false);",
    ):
        if marker not in body:
            fail(f"rank original-input projection contract missing: {marker}")
    if not (body.index("const D3DVECTOR originalInput =") <
            body.index("Calc3D2D_hk.call(") <
            body.index("const float projectedX =") <
            body.index("info.viewX = originalInput.x;")):
        fail("original Calc3D2D input must be copied before aliasable output")

require_rank_original_input(ui)
for invalid in (
    ui.replace("recoverViewPoint(RankMarkerProjectedInfo, true);",
               "recoverViewPoint(RankMarkerProjectedInfo, false);", 1),
    ui.replace("recoverViewPoint(RivalMarkerProjectedInfo, false);",
               "recoverViewPoint(RivalMarkerProjectedInfo, true);", 1),
    ui.replace("std::fabs(projectedX - out->x)",
               "std::fabs(projectedX - projectedX)", 1),
):
    if invalid == ui:
        fail("rank projection mutation did not alter the source")
    try:
        require_rank_original_input(invalid)
    except SystemExit:
        pass
    else:
        fail("rank original-input projection mutation escaped verifier")

# Two distinct fault injections, not repeated audits of unchanged content.
for bad_calc in (
    calc.replace("!std::isfinite(info.viewX)", "false", 1),
    calc[:calc.rfind("info.valid = true;")] +
    "/* removed fallback validity */" +
    calc[calc.rfind("info.valid = true;") + len("info.valid = true;"):],
):
    try:
        require_finite_projected_anchor(bad_calc)
    except SystemExit:
        pass
    else:
        fail("nonfinite projected-anchor fault injection escaped verifier")

rank13 = function_body(ui, "static int __cdecl RankMarker_sprani(")
rank46 = function_body(ui, "static int __cdecl RankMarker_putClipSprite(")
rival = function_body(ui, "static int __cdecl RivalMarker_sprani(")
for body, label, producer in (
    (rank13, "rank13", "ProducerToken::RankMarkerSprani"),
    (rank46, "rank46", "ProducerToken::RankMarkerClipSprite"),
    (rival, "rival", "ProducerToken::RivalMarkerSprani"),
):
    if "RenderScope::ProjectedWorldMarker2D" not in body:
        fail(f"{label} does not select projected marker ownership")
    if "RenderScope::WorldBillboard" not in body:
        fail(f"{label} lost fail-soft WorldBillboard fallback")
    if producer not in body:
        fail(f"{label} lost diagnostic producer token: {producer}")

if "&projectedAnchor" not in rank13 or "&projectedAnchor" not in rank46:
    fail("rank marker nodes do not carry snapshotted vehicle rank anchor")

# Original sub_4BAD20 already projects car-local (0,1,0). The shared -32px
# shift is desktop presentation spacing, not a second physical car anchor.
# Cancel it only for exact projected vehicle-rank producers in VR.
for token in (
    "return vrEnabled && projectedVehicleRank ? 32 : 0;",
    "static_assert(VehicleAnchorDesktopLiftPixels(true, true) == 32);",
    "static_assert(VehicleAnchorDesktopLiftPixels(false, true) == 0);",
    "static_assert(VehicleAnchorDesktopLiftPixels(true, false) == 0);",
):
    if token not in rank_fraction:
        fail("vehicle-rank desktop lift contract missing: " + token)
for body, label, token in (
    (rank13, "rank 1st-3rd", "y + RankMarkerFracY + float(anchorLiftY)"),
    (rank46, "rank 4th+", "xstnum, x, y + anchorLiftY, flags"),
):
    if "VehicleAnchorDesktopLiftPixels(" not in body or        "Settings::VREnabled" not in body or token not in body:
        fail(label + " lost exact projected desktop-lift cancellation")
if "VehicleAnchorDesktopLiftPixels(" in rival:
    fail("protected rival marker inherited vehicle-rank desktop lift correction")

if "&projectedAnchor" not in rival or "RivalMarkerProjectedInfo = {};" not in rival:
    fail("rival marker must consume one exact recovered anchor and copy it to all sibling nodes")
# Both immediate (pre-queue) and deferred SpriteNode draws for each exact
# vehicle marker must use the *same* anchor. The old rival wrapper captured
# its anchor after the original sprani CALL and tagged only new SpriteNodes,
# allowing a synchronous Draw to inherit the previous queue semantic.
def require_exact_marker_source_and_queue(body: str, label: str,
                                          is_rival: bool = False) -> None:
    frozen = body.find("const auto projectedAnchor =")
    owner = body.find("ScopedExactProducerSemantic producerScope(")
    direct = body.find("Game::sprani_play_ae_auth_alpha(") if label != "rank clip" else body.find("Game::put_clip_sprite(")
    queued = body.find("TagAppendedNodes(")
    if min(frozen, owner, direct, queued) < 0 or not (frozen < owner < direct < queued):
        fail(label + " must snapshot anchor, scope direct original and tag queued siblings in order")
    if "&RankMarkerProjectedInfo" in body or (
        is_rival and "&RivalMarkerProjectedInfo" in body
    ):
        fail(label + " reuses mutable thread-local anchor after direct Draw")
    if "projected ? &projectedAnchor : nullptr" not in body:
        fail(label + " direct/queue scope lost exact per-vehicle projected anchor")
    if is_rival:
        consume = body.find("RivalMarkerProjectedInfo = {};")
        if not (frozen < consume < owner):
            fail("rival exact anchor must be consumed before invoking original sprani")
        if "RenderScope::WorldBillboard" not in body or "TagAppendedNodes(before, scope," not in body:
            fail("rival lost its established queued WorldBillboard fallback")


for label, body in (
    ("rank sprani", rank13),
    ("rank clip", rank46),
    ("rival sprani", rival),
):
    require_exact_marker_source_and_queue(body, label, label == "rival sprani")

# Destructive, independently detected mutations (not repeated PASS audits).
for label, body, old, new in (
    ("rank sprani", rank13, "const auto projectedAnchor =", "const auto removedAnchor ="),
    ("rank clip", rank46, "ScopedExactProducerSemantic producerScope(", "ScopedRenderSemantic producerScope("),
    ("rival sprani", rival, "RivalMarkerProjectedInfo = {};", "/* consume lost */"),
    ("rival sprani", rival, "TagAppendedNodes(before, scope,", "TagAppendedNodes(before, RenderScope::ScreenHud,"),
):
    mutant = body.replace(old, new, 1)
    if mutant == body:
        fail("projected marker negative test setup did not mutate " + label)
    try:
        require_exact_marker_source_and_queue(mutant, label, label == "rival sprani")
    except SystemExit:
        pass
    else:
        fail("projected marker direct/queue mutant escaped: " + label)

# Original emoose/OutRun2006Tweaks 0xBB046 fractional correction is
# retained for all finite inputs. This exact producer can otherwise forward
# NaN/Inf through both 1st-3rd sprani and 4th+ clip-sprite sibling draws.
# Reject corrupt stack or computed offsets before publishing either fraction.
def require_finite_rank_fraction(body: str) -> None:
    tokens = (
        "!std::isfinite(x) || !std::isfinite(y)",
        "RankMarkerFracX = RankMarkerFracY = 0.0f;",
        "!std::isfinite(fracX) || !std::isfinite(fracY)",
        "RankMarkerFracX = fracX;",
        "RankMarkerFracY = fracY;",
    )
    positions = [body.find(token) for token in tokens]
    if min(positions) < 0 or positions != sorted(positions):
        fail("rank truncate must reject invalid raw/computed fractions before publishing")
    if body.count("RankMarkerFracX = RankMarkerFracY = 0.0f;") != 2:
        fail("rank truncate must clear both fractional offsets on either invalid path")


truncate = function_body(ui, "static void RankMarker_Truncate_dest(")
require_finite_rank_fraction(truncate)
# Two independent one-step source mutations; no unchanged 1000/5000 loop.
for broken in (
    truncate.replace(
        "!std::isfinite(x) || !std::isfinite(y)", "false", 1),
    truncate.replace(
        "!std::isfinite(fracX) || !std::isfinite(fracY)", "false", 1),
):
    if broken == truncate:
        fail("rank fraction fault-injection setup did not mutate source")
    try:
        require_finite_rank_fraction(broken)
    except SystemExit:
        pass
    else:
        fail("rank fraction invalid-value mutant escaped verifier")

rank_owner = function_body(ui, "static int __cdecl RankMarkerSub_dest(")
for marker in (
    "RankMarkerProjectedInfo = {};",
    "++RankMarkerSubActiveDepth;",
    "RankMarkerSub_hk.call<int>(arg)",
    "--RankMarkerSubActiveDepth;",
    "RankMarkerProjectedInfo = saved;",
):
    if marker not in rank_owner:
        fail(f"rank sub_4BAD20 must own its per-vehicle view anchor: {marker}")
if "RankMarkerSub_hk = safetyhook::create_inline(" not in ui:
    fail("original rank sub_4BAD20 hook not installed")
if "RankMarkerSubScreenHudDepth == 0" not in calc:
    fail("NaviPub rank HUD must not poison the next vehicle's projected anchor")
rank_digit = function_body(ui, "static int __cdecl RankMarker_putClipSprite(")
exact_owned = function_body(ui, "static int ExactScreenHud_putClipSpriteOwned(")
exact_clip = function_body(ui, "static int __cdecl ExactScreenHud_putClipSprite(")
pause_clip = function_body(ui, "static int __cdecl PauseOptionArrow_putClipSprite(")
# Shared queue snapshot/tagging now lives in Owned, not in the forwarding
# exact clip wrapper. Keep the full priority-queue sibling requirement on
# the REAL registration function and verify both caller-specific tokens.
for label, body in (("rank 4th+ digits", rank_digit),
                    ("menu/result HUD", exact_owned)):
    if "TagAppendedNodes(tailsBefore," not in body:
        fail(f"{label} must propagate semantic tags to every appended sibling")
    if "Game::SpritePriorityCount" not in body:
        fail(f"{label} must enumerate original sprite priority queues")
if ("Game::put_clip_sprite(" not in exact_owned or
        "RenderScope::ScreenHud, producer" not in exact_owned or
        exact_owned.find("Game::put_clip_sprite(") >
        exact_owned.find("TagAppendedNodes(tailsBefore,")):
    fail("menu/result owned original Draw must precede all sibling tags")
if ("ExactScreenHud_putClipSpriteOwned(" not in exact_clip or
        "ProducerToken::ExactScreenHudClipSprite" not in exact_clip or
        "PauseOptionArrow" in exact_clip):
    fail("generic HUD clip must not borrow exact pause-arrow semantics")
if ("ExactScreenHud_putClipSpriteOwned(" not in pause_clip or
        "ProducerToken::PauseOptionArrow" not in pause_clip or
        "GameState::STATE_SMPAUSEMENU" not in pause_clip or
        "return ExactScreenHud_putClipSprite(" not in pause_clip):
    fail("pause-specific E8 producer/fallback lost its own queue authority")
for marker in ("const auto projectedAnchor = RivalMarkerProjectedInfo;",
               "RivalMarkerProjectedInfo = {};",
               "projected ? &projectedAnchor : nullptr"):
    if marker not in rival:
        fail(f"rival producer leaked stale anchor: {marker}")

# Sumo no-tick replay allocates fresh nodes, so projected anchor metadata must
# survive together with the already-preserved RenderScope and ProducerToken.
entry_start = framerate.find("struct Entry")
entry_end = framerate.find("static Entry Captured", entry_start)
if entry_start < 0 or entry_end <= entry_start:
    fail("Sumo replay Entry block is missing")
entry = framerate[entry_start:entry_end]
if "ProjectedMarkerInfo vrProjectedMarker{};" not in entry:
    fail("Sumo replay Entry does not preserve projected marker payload")

capture = function_body(framerate, "static void capture()")
for marker in (
    "&entry.vrProducer",
    "&entry.vrProjectedMarker",
):
    if marker not in capture:
        fail(f"Sumo replay capture missing semantic payload output: {marker}")

replay = function_body(framerate, "static void replay()")
for marker in (
    "entry.vrProducer",
    "entry.vrProjectedMarker.valid",
    "&entry.vrProjectedMarker",
):
    if marker not in replay:
        fail(f"Sumo replay restore missing projected payload: {marker}")

# No-tick Sumo replay does not share the original SpriteNode address:
# semantic owner, identity AND 3D view anchor all have to survive the
# capture/requeue pair for car-relative rank instead of turning into a flat HUD.
# Keep this independent of the existing front-facing clip-W admission check.
def verify_exact_sumo_requeue_payload(src: str) -> None:
    capture_fn = function_body(src, "static void capture()")
    replay_fn = function_body(src, "static void replay()")
    snapshots = (
        "entry.vrScope =",
        "OutRunVR::GameSemantic::PeekSpriteNodeScope(",
        "&entry.vrProducer, &entry.vrProjectedMarker",
    )
    snapshot_positions = [capture_fn.find(x) for x in snapshots]
    if min(snapshot_positions) < 0 or snapshot_positions != sorted(snapshot_positions):
        fail("Sumo capture lost coherent original scope+producer+view-anchor snapshot")
    for snippet in (
        "if (entry.vrScope !=",
        "OutRunVR::GameSemantic::RenderScope::None",
        "OutRunVR::GameSemantic::RegisterSpriteNodeScope(",
        "node, entry.vrScope, entry.vrProducer,",
        "entry.vrProjectedMarker.valid",
        "? &entry.vrProjectedMarker : nullptr",
    ):
        if snippet not in replay_fn:
            fail("Sumo replay lost exact projected marker payload: " + snippet)
    if replay_fn.count("RegisterSpriteNodeScope(") != 1:
        fail("Sumo replay unexpected additional semantic owner")
    reg = replay_fn.index("OutRunVR::GameSemantic::RegisterSpriteNodeScope(")
    if replay_fn.find("if (entry.vrScope !=", 0, reg) < 0:
        fail("unverified Sumo frame promoted untagged node to rank/HUD")

verify_exact_sumo_requeue_payload(framerate)
for label, changed in (
    ("capture projected anchor lost", framerate.replace(
        "&entry.vrProducer, &entry.vrProjectedMarker",
        "&entry.vrProducer, nullptr", 1)),
    ("replay projected anchor lost", framerate.replace(
        "? &entry.vrProjectedMarker : nullptr",
        "? nullptr : nullptr", 1)),
    ("replay producer identity lost", framerate.replace(
        "node, entry.vrScope, entry.vrProducer,",
        "node, entry.vrScope, OutRunVR::GameSemantic::ProducerToken::None,", 1)),
    ("replay missing validity gate", framerate.replace(
        "entry.vrProjectedMarker.valid",
        "true", 1)),
):
    if changed == framerate:
        fail("invalid independent Sumo mutation: " + label)
    try:
        verify_exact_sumo_requeue_payload(changed)
    except SystemExit:
        pass
    else:
        fail("Sumo projected-marker semantic negative control escaped: " + label)

# Exact projected world markers must only project points in front of the
# camera. R44's spatial-billboard gate already uses positive clip W. The
# historical fabs(W) condition accepted negative/behind-eye coordinates.
def require_front_facing_projected_marker(source: str) -> None:
    project = function_body(source, "bool R57ProjectViewPoint(")
    required = "clipW <= 1.0e-6f"
    valid = project.find(required)
    perspective = project.find("!std::isfinite(clipW)")
    divide = project.find("ndcX = clipX / clipW;")
    if min(valid, perspective, divide) < 0 or not (
        perspective < valid < divide
    ) or "std::fabs(clipW)" in project:
        fail("R57 per-eye rank/rival projection must reject negative/zero clip W")


require_front_facing_projected_marker(r30)
# Two distinct deliberate regressions; no repeated static cycles.
for original, replacement in (
    ("clipW <= 1.0e-6f", "std::fabs(clipW) <= 1.0e-6f"),
    ("clipW <= 1.0e-6f", "clipW < -1.0e-6f"),
):
    mutated = r30.replace(original, replacement, 1)
    if mutated == r30:
        fail("projected-marker negative-W mutation did not modify source")
    try:
        require_front_facing_projected_marker(mutated)
    except SystemExit:
        pass
    else:
        fail("projected-marker negative-W mutant escaped the verifier")

# R30 must classify only the explicit projected semantic and then reproject the
# recovered view-space anchor through the latched head+per-eye OpenXR transform.
for marker in (
    "ProjectedWorldMarker2D",
    "R57ProjectViewPoint(",
    "R57BuildProjectedMarkerDelta(",
):
    if marker not in r30:
        fail(f"R30 projected marker implementation missing: {marker}")

classify = function_body(r30, "R30ScreenSpaceKind R30ClassifyScreenSpacePass(")
for marker in (
    "CorroboratesProjectedWorldMarker",
    "CurrentProjectedMarker()",
    "R30ScreenSpaceKind::ProjectedWorldMarker2D",
):
    if marker not in classify:
        fail(f"R30 classifier projected-marker gate missing: {marker}")

build = function_body(r30, "bool R30BuildScreenSpaceEyeConstants(")
for marker in (
    "screenKind == R30ScreenSpaceKind::ProjectedWorldMarker2D",
    "R57BuildProjectedMarkerDelta(",
    "(1.0f - markerScale) * baseAnchorX",
    "(1.0f - markerScale) * baseAnchorY",
):
    if marker not in build:
        fail(f"R30 per-eye projected-marker reconstruction missing: {marker}")

draw = function_body(r30, "HRESULT R30TryScreenSpaceFovDraw(")
if "CorroboratesProjectedWorldMarker" not in draw:
    fail("R30 draw ownership gate does not require exact projected semantic")
if "ProducerToken::RankMarkerSprani" in classify or    "ProducerToken::RankMarkerClipSprite" in classify or    "ProducerToken::RivalMarkerSprani" in classify:
    fail("ProducerToken became rendering classification authority")

# Do not solve this by widening the generic 2D queue.
if "return scope == RenderScope::ScreenOverlay2D ||" in semantics:
    fail("generic ScreenOverlay2D was widened into projected-world ownership")


# The three exact vehicle-marker producers may synchronously Draw before
# queuing their sprites. Preserve any previous one-shot Draw token for its
# original owner, and freeze the 4th+ ordinal digits through nested producers.
def require_rank_direct_isolation(source: str, helper: str = rank_fraction) -> None:
    for func, token in (
        ("static int __cdecl RankMarker_sprani(", "RankMarkerSprani"),
        ("static int __cdecl RankMarker_putClipSprite(", "RankMarkerClipSprite"),
        ("static int __cdecl RivalMarker_sprani(", "RivalMarkerSprani"),
    ):
        body = function_body(source, func)
        begin = body.find("ScopedExactProducerSemantic producerScope(")
        end = body.find(");", begin)
        direct = body.find("Game::put_clip_sprite(" if token ==
                           "RankMarkerClipSprite" else
                           "Game::sprani_play_ae_auth_alpha(")
        tag = body.find("TagAppendedNodes(")
        if min(begin, end, direct, tag) < 0 or not (
            begin < end < direct < tag):
            fail("marker source/queue ordering changed: " + token)
        owner = body[begin:end]
        if ("Settings::VREnabled" not in owner or
            "ProducerToken::" + token not in owner or
            "scope," not in owner):
            fail("exact direct marker pending-token isolation lost: " + token)
    clip = function_body(source, "static int __cdecl RankMarker_putClipSprite(")
    a = clip.find("const float frozenFractionX = RankMarkerFracX;")
    b = clip.find("const float frozenFractionY = RankMarkerFracY;")
    c = clip.find("Game::put_clip_sprite(")
    d = clip.find("OutRunVR::RankMarker::RestoreAppendedRankFractions(")
    e = clip.find("frozenFractionX, frozenFractionY);", d)
    if min(a,b,c,d,e) < 0 or not (a < b < c < d < e):
        fail("nested 4th+ rank glyph offsets not snapshotted before live-queue correction")
    # Original root/tail proof is unchanged. The source fix now preflights
    # EVERY sibling before the second bounded commit pass; rejecting a bad
    # later glyph must not leave a previously mutated vehicle-rank sprite.
    for required in (
        "FirstVerifiedAppendedNode(",
        "root, oldTail, newTail, bound);",
        "if (!first)",
        "for (Node* node = first; node && count < bound; node = node->next_0)",
        "if (!FractionCandidate(*node, dx, dy, x, y))",
        "if (node == newTail)",
        "if (!reachedTail)",
        "for (unsigned i = 0; i < count; ++i)",
        "RestoreFraction(*node, dx, dy);",
    ):
        if required not in helper:
            fail("rank live-root/two-pass child proof changed: " + required)
    preflight = helper.find("for (Node* node = first; node && count < bound;")
    commit = helper.find("for (unsigned i = 0; i < count; ++i)")
    if not (0 <= preflight < helper.find("if (!reachedTail)") < commit):
        fail("rank siblings must be fully validated before any coordinate commit")
    if '#include "vr/game/rank_marker_fraction.hpp"' not in source:
        fail("rank caller not using shared two-layout correction")
    for required in (
        "if (node.kind_C == 0u)",
        "x = &node.args_10.float24;",
        "y = &node.args_10.float28;",
        "else if (node.kind_C == 1u)",
        "x = &node.args2_58.mtx_14._41;",
        "y = &node.args2_58.mtx_14._42;",
        "!std::isfinite(dx) || !std::isfinite(dy)",
        "std::fabs(dx) > 1.0f || std::fabs(dy) > 1.0f",
        "const float nextX = *x + dx;",
        "const float nextY = *y + dy;",
        "if (!std::isfinite(nextX) || !std::isfinite(nextY))",
        "candidateX = nextX;",
        "candidateY = nextY;",
        "if (!FractionCandidate(node, dx, dy, x, y))",
        "node.args_10.float24 = x;",
        "node.args_10.float28 = y;",
        "node.args2_58.mtx_14._41 = x;",
        "node.args2_58.mtx_14._42 = y;",
    ):
        if required not in helper:
            fail("rank affine/clip candidate and atomic correction changed: " + required)

require_rank_direct_isolation(ui)

def require_projected_rank_desktop_lift(source: str, helper: str) -> None:
    r13 = function_body(source, "static int __cdecl RankMarker_sprani(")
    r46 = function_body(source, "static int __cdecl RankMarker_putClipSprite(")
    rv = function_body(source, "static int __cdecl RivalMarker_sprani(")
    if "return vrEnabled && projectedVehicleRank ? 32 : 0;" not in helper:
        fail("rank desktop-lift helper widened or removed")
    if "scope == OutRunVR::GameSemantic::RenderScope::ProjectedWorldMarker2D" not in r13:
        fail("rank sprani desktop lift is not projected-only")
    if "y + RankMarkerFracY + float(anchorLiftY)" not in r13:
        fail("rank sprani desktop lift cancellation lost")
    if "const bool projected = !screenHud && projectedAnchor.valid;" not in r46:
        fail("rank clip desktop lift lost ScreenHud exclusion")
    if "xstnum, x, y + anchorLiftY, flags" not in r46:
        fail("rank clip desktop lift cancellation lost")
    if "VehicleAnchorDesktopLiftPixels(" in rv:
        fail("rival marker inherited rank desktop lift correction")

require_projected_rank_desktop_lift(ui, rank_fraction)
for name, source_old, source_new, helper_old, helper_new in (
    ("rank sprani lift removed",
     "y + RankMarkerFracY + float(anchorLiftY)", "y + RankMarkerFracY",
     None, None),
    ("rank clip lift removed",
     "xstnum, x, y + anchorLiftY, flags", "xstnum, x, y, flags",
     None, None),
    ("rank lift widened",
     None, None,
     "return vrEnabled && projectedVehicleRank ? 32 : 0;",
     "return vrEnabled ? 32 : 0;"),
):
    changed_source = ui if source_old is None else ui.replace(source_old, source_new, 1)
    changed_helper = rank_fraction if helper_old is None else rank_fraction.replace(helper_old, helper_new, 1)
    if changed_source == ui and changed_helper == rank_fraction:
        fail("rank desktop-lift mutation setup failed: " + name)
    try:
        require_projected_rank_desktop_lift(changed_source, changed_helper)
    except SystemExit:
        pass
    else:
        fail("rank desktop-lift mutant escaped: " + name)

for name, original, replacement in (
    ("rank sprani pending", "Settings::VREnabled,\n                OutRunVR::GameSemantic::ProducerToken::RankMarkerSprani", "false,\n                OutRunVR::GameSemantic::ProducerToken::RankMarkerSprani"),
    ("rank clip direct", "ProducerToken::RankMarkerClipSprite);", "ProducerToken::RivalMarkerSprani);"),
    ("rival direct", "ProducerToken::RivalMarkerSprani);", "ProducerToken::RankMarkerSprani);"),
    ("digit producer frozen X", "frozenFractionX, frozenFractionY);", "RankMarkerFracX, frozenFractionY);"),
    ("digit producer frozen Y", "frozenFractionX, frozenFractionY);", "frozenFractionX, RankMarkerFracY);"),
):
    changed = ui.replace(original, replacement, 1)
    if changed == ui:
        fail("mutation setup failed: " + name)
    try:
        require_rank_direct_isolation(changed)
    except SystemExit:
        pass
    else:
        fail("destructive marker owner mutant escaped: " + name)

# Destructive regressions guard both queue-root proof and the entire
# preflight/commit transaction. No duplicate test-only task is created.
for name, old, new in (
    ("rank queue proof removed", "FirstVerifiedAppendedNode(", "UnprovenAppendedNode("),
    ("rank queue bound removed", "node && count < bound", "node && count < 0"),
    ("later sibling candidate bypassed", "if (!FractionCandidate(*node, dx, dy, x, y))", "if (false)"),
    ("rank failed-tail gate removed", "if (!reachedTail)", "if (false)"),
    ("rank commit pass dropped", "for (unsigned i = 0; i < count; ++i)", "for (unsigned i = count; i < count; ++i)"),
):
    changed = rank_fraction.replace(old, new, 1)
    if changed == rank_fraction:
        fail("rank queue proof mutation setup failed: " + name)
    try:
        require_rank_direct_isolation(ui, changed)
    except SystemExit:
        pass
    else:
        fail("rank queue proof mutation escaped: " + name)

for name, old, new in (
    ("kind0 X", "x = &node.args_10.float24;", "x = &node.args2_58.mtx_14._41;"),
    ("kind1 X", "x = &node.args2_58.mtx_14._41;", "x = &node.args_10.float24;"),
    ("kind1 Y", "y = &node.args2_58.mtx_14._42;", "y = &node.args_10.float28;"),
    ("overflow guard", "if (!std::isfinite(nextX) || !std::isfinite(nextY))", "if (false)"),
):
    changed = rank_fraction.replace(old, new, 1)
    if changed == rank_fraction:
        fail("rank correction negative setup failed: " + name)
    try:
        require_rank_direct_isolation(ui, changed)
    except SystemExit:
        pass
    else:
        fail("rank correction negative mutation escaped: " + name)


# R84 physical left/right rank source is distinct from the R26_SAFE fallback.
# Guard identical SpriteNode and Calc3D2D markers against intervening native
# Draw and fixed-function input-layout changes before publishing RIGHT.
def require_r84_physical_rank_transaction(header: str, renderer: str) -> None:
    for token in (
        "std::uint64_t drawSerial;", "std::uint32_t fvf;",
        "s.drawSerial != 0", "before.drawSerial == after.drawSerial",
        "before.fvf == after.fvf",
    ):
        if token not in header:
            fail("R84 rank source identity lost: " + token)
    capture = function_body(renderer, "bool R30CaptureProjectedRankPhysicalSource(")
    for token in (
        "device->GetFVF(&fvf)",
        "R29OwnerTopLevelDrawSerial(), fvf, shader, shaderEpoch",
        "ValidRankSource(source)",
    ):
        if token not in capture:
            fail("R84 physical rank capture lost: " + token)
    physical = function_body(renderer, "HRESULT R30ExecuteXyzrhwStereo(")
    for token in (
        "R30CaptureProjectedRankPhysicalSource(device, rankBefore)",
        "const HRESULT leftHr = leftDraw();",
        "R30CaptureProjectedRankPhysicalSource(device, rankAfter)",
        "OutRunVR::RankMarker::PhysicalRankSource atRight{};",
        "R30CaptureProjectedRankPhysicalSource(\n                            device, atRight)",
        "SameRankSourceAfterNativeLeft(",
        "R29OwnerMarkRightDrawFailed();", "R29OwnerArmMonoSafety();",
    ):
        if token not in physical:
            fail("R84 native rank stereo gate lost: " + token)
    first_same = physical.index("SameRankSourceAfterNativeLeft(")
    at_right = physical.index("OutRunVR::RankMarker::PhysicalRankSource atRight{};")
    right_capture = physical.index(
        "R30CaptureProjectedRankPhysicalSource(\n                            device, atRight)")
    second_same = physical.index("SameRankSourceAfterNativeLeft(", first_same + 1)
    right_draw = physical.index("rightHr = rightDraw();")
    if not (physical.index("R30CaptureProjectedRankPhysicalSource(device, rankBefore)") <
            physical.index("const HRESULT leftHr = leftDraw();") <
            physical.index("R30CaptureProjectedRankPhysicalSource(device, rankAfter)") <
            first_same < at_right < right_capture < second_same < right_draw):
        fail("R84 rank physical LEFT/RIGHT source gates misordered")

require_r84_physical_rank_transaction(rank_physical, r84)
for label, original, broken in (
    ("same-node next Draw", "before.drawSerial == after.drawSerial",
     "before.drawSerial != after.drawSerial"),
    ("fixedfn FVF switch", "before.fvf == after.fvf", "true"),
    ("unknown draw", "s.drawSerial != 0", "true"),
):
    if original not in rank_physical:
        fail("R84 rank mutation input missing: " + label)
    try:
        require_r84_physical_rank_transaction(
            rank_physical.replace(original, broken, 1), r84)
    except SystemExit:
        pass
    else:
        fail("R84 rank mutation escaped: " + label)
for label, original, broken in (
    ("lost native Draw identity", "R29OwnerTopLevelDrawSerial(), fvf, shader, shaderEpoch",
     "0u, fvf, shader, shaderEpoch"),
    ("lost native FVF", "device->GetFVF(&fvf)", "device->GetFVF(nullptr)"),
    ("reused old snapshot", "R30CaptureProjectedRankPhysicalSource(device, rankAfter)",
     "R30CaptureProjectedRankPhysicalSource(device, rankBefore)"),
    ("right-eye owner recheck lost",
     "R30CaptureProjectedRankPhysicalSource(\n                            device, atRight)",
     "R30CaptureProjectedRankPhysicalSource(\n                            device, rankAfter)"),
):
    if original not in r84:
        fail("R84 rank native mutation input missing: " + label)
    # Inject into the actual capture function, not the earlier
    # R30HasXyzrhwInputLayout GetFVF probe. A file-wide replace changes
    # the wrong callsite and leaves this physical-rank guard untouched.
    # The FVF/serial snapshot belongs to the capture function; the
    # after-native-left snapshot call belongs to the stereo executor.
    # Never mutate an unrelated first occurrence in this large renderer.
    target_function = (
        "HRESULT R30ExecuteXyzrhwStereo("
        if label in ("reused old snapshot", "right-eye owner recheck lost")
        else "bool R30CaptureProjectedRankPhysicalSource("
    )
    target_body = function_body(r84, target_function)
    if original not in target_body:
        fail("R84 rank mutation input missing in target function: " + label)
    target_start = r84.find(target_body, r84.find(target_function))
    if target_start < 0:
        fail("R84 rank mutation target span missing: " + label)
    modified_body = target_body.replace(original, broken, 1)
    mutant = (r84[:target_start] + modified_body +
              r84[target_start + len(target_body):])
    try:
        require_r84_physical_rank_transaction(rank_physical, mutant)
    except SystemExit:
        pass
    else:
        fail("R84 physical rank mutation escaped: " + label)

# R84 projected vehicle markers use the HMD-proven rival policy: preserve the
# original sprite Z/RHW/clip depth and derive binocular placement from the
# recovered per-car Calc3D2D anchor. Rank 1-5 must not re-enable the separate
# physical-depth override that regressed RivalMarkerSprani.
def require_r84_rank_depth_contract(stereo_header: str, renderer: str) -> None:
    depth_owner = function_body(
        semantics, "inline constexpr bool ProjectedMarkerOwnsVehicleDepth(")
    for token in (
        "(void)producer;",
        "return false;",
    ):
        if token not in depth_owner:
            fail("R84 rival-policy depth gate lost: " + token)
    for producer in (
        "ProducerToken::RankMarkerSprani",
        "ProducerToken::RankMarkerClipSprite",
        "ProducerToken::RivalMarkerSprani",
    ):
        assertion = (
            "!ProjectedMarkerOwnsVehicleDepth(\n        " + producer + ")")
        if assertion not in semantics:
            fail("projected marker re-enabled physical depth: " + producer)

    # Keep the dormant depth machinery isolated behind the gate so a future
    # evidence-backed experiment can be reintroduced without changing the
    # proven rival-style XY path. Normal rank/rival draws must pass false.
    delta = function_body(renderer, "bool R30BuildProjectedRankDelta(")
    for token in (
        "carryPhysicalDepth ? &shift.ndcZ[eye] : nullptr",
        "carryPhysicalDepth ? &shift.invW[eye] : nullptr",
        "shift.deltaX[eye] = projectedX - shift.baseX;",
        "shift.deltaY[eye] = projectedY - shift.baseY;",
    ):
        if token not in delta:
            fail("R84 projected marker XY/depth isolation lost: " + token)

    positiont = function_body(renderer, "bool R30ConfigureXyzrhwWorldEffect(")
    for token in (
        "ProjectedMarkerOwnsVehicleDepth(",
        "state.projectedWorldMarker = true;",
        "state.projectedVehicleRankDepth = vehicleRankDepth;",
    ):
        if token not in positiont:
            fail("R84 projected marker POSITIONT gate lost: " + token)

    fixedfn = function_body(renderer, "HRESULT R30TryFixedFunctionOriginalSpriteStereo(")
    if "state.projectedVehicleRankDepth &&" not in fixedfn or \
            "R30ApplyProjectedRankClipDepth(" not in fixedfn:
        fail("R84 projected marker fixed-function depth gate lost")

    shader = function_body(renderer, "bool R30BuildScreenSpaceEyeConstants(")
    for token in (
        "const bool vehicleRankDepth =",
        "ProjectedMarkerOwnsVehicleDepth(",
        "if (vehicleRankDepth &&",
        "R30ApplyProjectedRankClipDepth(",
    ):
        if token not in shader:
            fail("R84 projected marker shader depth gate lost: " + token)


require_r84_rank_depth_contract(rank_stereo, r84)

# Mutation guard: re-enabling rank-only physical depth must be detectable.
depth_policy_mutant = semantics.replace(
    "(void)producer;\n        return false;",
    "return producer == ProducerToken::RankMarkerSprani ||\n"
    "            producer == ProducerToken::RankMarkerClipSprite;",
    1)
if depth_policy_mutant == semantics:
    fail("projected marker rival-policy mutation setup failed")
mutated_owner = function_body(
    depth_policy_mutant,
    "inline constexpr bool ProjectedMarkerOwnsVehicleDepth(")
if "(void)producer;" in mutated_owner or "return false;" in mutated_owner:
    fail("projected marker rival-policy mutation did not alter depth gate")

print("VR projected marker anchor contract PASS")
