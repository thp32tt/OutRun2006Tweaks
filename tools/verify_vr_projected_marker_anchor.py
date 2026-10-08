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
