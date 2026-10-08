#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEMANTICS = ROOT / "src/vr/game/render_semantics.hpp"
UI = ROOT / "src/hooks_uiscaling.cpp"
FRAMERATE = ROOT / "src/hooks_framerate.cpp"
R30 = ROOT / "src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp"


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
framerate = read(FRAMERATE)
r30 = read(R30)

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
    "const ProjectedMarkerInfo* projectedMarker = nullptr) noexcept",
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
    valid = calc_body.find("info.valid = true;")
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
    calc.replace("info.valid = true;", "/* premature validity */", 1),
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

if "&RankMarkerProjectedInfo" not in rank13 or "&RankMarkerProjectedInfo" not in rank46:
    fail("rank marker nodes do not carry recovered rank anchor")
if "&projectedAnchor" not in rival or "RivalMarkerProjectedInfo = {};" not in rival:
    fail("rival marker must consume one exact recovered anchor and copy it to all sibling nodes")
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
exact_clip = function_body(ui, "static int __cdecl ExactScreenHud_putClipSprite(")
for label, body in (("rank 4th+ digits", rank_digit),
                    ("menu/result HUD", exact_clip)):
    if "TagAppendedNodes(tailsBefore," not in body:
        fail(f"{label} must propagate semantic tags to every appended sibling")
    if "Game::SpritePriorityCount" not in body:
        fail(f"{label} must enumerate original sprite priority queues")
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

print("VR projected marker anchor contract PASS")
