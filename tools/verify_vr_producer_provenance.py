#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEMANTICS = ROOT / "src/vr/game/render_semantics.hpp"
UI = ROOT / "src/hooks_uiscaling.cpp"
FRAMERATE = ROOT / "src/hooks_framerate.cpp"
RENDERER = ROOT / "src/vr/game/outrun_renderer.cpp"
R30 = ROOT / "src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp"


def fail(message: str) -> None:
    raise SystemExit(
        "VR producer provenance contract FAILED\n"
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
                return source[brace + 1 : i]
    fail(f"unterminated function body: {marker}")
    return ""


semantics = read(SEMANTICS)
ui = read(UI)
framerate = read(FRAMERATE)
renderer = read(RENDERER)
r30 = read(R30)

# Producer identity is diagnostic metadata attached only to an already-explicit
# RenderScope. Keep this list bounded and exact so future broad heuristics cannot
# silently acquire producer authority.
required_tokens = (
    "RankMarkerSprani",
    "RankMarkerClipSprite",
    "ExactScreenHudClipSprite",
    "RivalMarkerSprani",
    "TextGlyphPutSprite",
)
if "enum class ProducerToken : std::uint8_t" not in semantics:
    fail("ProducerToken enum is missing")
for token in required_tokens:
    if token not in semantics:
        fail(f"ProducerToken missing exact family: {token}")
if "ProducerToken producer = ProducerToken::None;" not in semantics:
    fail("SpriteNodeSemanticTag no longer carries producer identity")
if "ProducerToken producer = ProducerToken::None" not in semantics:
    fail("RegisterSpriteNodeScope must default producer identity to None")
if "PeekSpriteNodeProducerToken(" not in semantics:
    fail("non-consuming producer-token peek API is missing")
if "CurrentQueueProducerToken()" not in semantics:
    fail("current queue producer-token accessor is missing")

select = function_body(semantics, "inline void SelectSpriteQueueNode(")
for marker in (
    "CurrentSpriteQueueProducer = ProducerToken::None;",
    "&CurrentSpriteQueueProducer",
):
    if marker not in select:
        fail(f"queue selection no longer consumes producer provenance: {marker}")

# Exact reverse-engineered producer wrappers must attach identity only while
# attaching their existing explicit semantic scope.
ui_requirements = {
    "RankMarkerSprani": "ProducerToken::RankMarkerSprani",
    "RankMarkerClipSprite": "ProducerToken::RankMarkerClipSprite",
    "ExactScreenHudClipSprite": "ProducerToken::ExactScreenHudClipSprite",
    "RivalMarkerSprani": "ProducerToken::RivalMarkerSprani",
    "TextGlyphPutSprite": "ProducerToken::TextGlyphPutSprite",
}
for label, marker in ui_requirements.items():
    if marker not in ui:
        fail(f"exact producer wrapper missing token: {label}")

if "ProducerToken producer =" not in ui or "TagAppendedNodes(" not in ui:
    fail("multi-node exact producer helper no longer propagates ProducerToken")

# Non-tick Sumo replay allocates fresh SpriteNodes, so producer identity must be
# captured non-destructively and restored together with the explicit scope.
entry_start = framerate.find("struct Entry")
entry_end = framerate.find("};", entry_start)
entry = framerate[entry_start:entry_end] if entry_start >= 0 and entry_end >= 0 else ""
for marker in (
    "RenderScope vrScope",
    "ProducerToken vrProducer",
):
    if marker not in entry:
        fail(f"Sumo replay Entry missing provenance field: {marker}")

capture = function_body(framerate, "static void capture()")
scope_peek = capture.find(
    "OutRunVR::GameSemantic::PeekSpriteNodeScope(")
producer_out = capture.find("&entry.vrProducer", scope_peek)
if min(scope_peek, producer_out) < 0:
    fail(
        "Sumo replay capture must snapshot scope and producer in one "
        "non-consuming semantic-tag lookup"
    )
if "PeekSpriteNodeProducerToken(node)" in capture:
    fail(
        "Sumo replay capture regressed to a second semantic-tag scan "
        "for producer provenance"
    )
if "ConsumeSpriteNodeScope(" in capture:
    fail("Sumo replay capture must remain non-consuming")

replay = function_body(framerate, "static void replay()")
if "node, entry.vrScope, entry.vrProducer" not in replay:
    fail("Sumo replay must restore scope and producer token on the fresh node")

# c64 upload is the first durable renderer boundary after queue OR a
# direct original producer. The renderer must save the selected queue token
# before a direct token, but a queue-free central sun has no queue token.
producer_selector = function_body(semantics, "inline ProducerToken CurrentRenderProducerToken()")
if not re.search(
    r"return\\s+SpriteQueueDepth\\s*!=\\s*0\\s*\\?\\s*"
    r"CurrentSpriteQueueProducer\\s*:\\s*CurrentDirectExactProducer\\s*;",
    producer_selector,
):
    fail("render producer selector lost queue priority or direct fallback")
record = function_body(renderer, "void RecordGameWvpWrite(")
for marker in (
    "CurrentRenderProducerToken()",
    "LastGameWvpProducerToken",
    "VR R51 C64 FINGERPRINT:",
    "LastGameWvpLensCentreCallEpoch",
    "CurrentLensCentreCallEpoch",
    "QueueRenderActive()",
):
    if marker not in record:
        fail(f"c64 producer or lens-call provenance capture missing: {marker}")
if "LastGameWvpProducerToken =" not in record:
    fail("c64 recorder no longer saves the unified renderer producer")
if "CurrentQueueProducerToken()" in record:
    fail("c64 recorder reverted to queue-only provenance, losing direct lens source")

# Exact original central sun consumes only its own raw c64; this deliberate
# exception must NOT give all diagnostic producer families render authority.
centre = function_body(r30, "bool R30GetExactLensCentreRawWvp(")
for marker in (
    "QueueRenderActive()",
    "CurrentRenderProducerToken() != ProducerToken::LensFlareCentre",
    "GetLastRawGameWvpWrite(",
    "GetLastGameWvpLensCentreCallEpoch()",
    "CurrentLensCentreCallEpoch",
    "OwnsRawWvp({",
    "sourceProducer == ProducerToken::LensFlareCentre",
    "queueNode == nullptr",
):
    if marker not in centre:
        fail(f"central sun raw matrix provenance missing: {marker}")
enter = function_body(read(ROOT / "src/hooks_graphics.cpp"), "static void LensCentreEnter(")
leave = function_body(read(ROOT / "src/hooks_graphics.cpp"), "static void LensCentreLeave(")
for marker in (
    "CurrentLensCentreCallEpoch = next;",
    "CurrentDirectExactProducer =",
    "ProducerToken::LensFlareCentre;",
):
    if marker not in enter:
        fail(f"central source entry epoch/direct owner lost: {marker}")
for marker in (
    "CurrentDirectExactProducer = LensCentreSavedProducer;",
    "CurrentLensCentreCallEpoch = LensCentreSavedEpoch;",
):
    if marker not in leave:
        fail(f"central source leave no longer restores nested owner: {marker}")

getter = function_body(renderer, "bool GetLastGameWvpSemanticProvenance(")
if "ProducerToken& producerToken" not in renderer:
    fail("c64 provenance getter no longer exposes producer token")
if "producerToken = LastGameWvpProducerToken;" not in getter:
    fail("c64 provenance getter does not return captured producer token")

# Draw-time correlation is telemetry only. It may compare scope/node lifetime,
# but exact producer families must not become rendering classifiers.
classify = function_body(r30, "R30ScreenSpaceKind R30ClassifyScreenSpacePass(")
for marker in (
    "ProducerToken c64Producer",
    "VR R51 DRAW FINGERPRINT:",
    "R51ProducerFingerprintScopeMismatch",
):
    if marker not in classify:
        fail(f"draw-time producer correlation missing: {marker}")
for token in required_tokens:
    if f"ProducerToken::{token}" in r30:
        fail(
            f"R30 must not classify rendering from exact producer token {token}; "
            "producer identity is diagnostic-only"
        )
if re.search(r"c64Producer\s*==\s*OutRunVR::GameSemantic::ProducerToken::", classify):
    fail("draw classifier gained producer-specific equality authority")
if "existing RenderScope + projection/world gates remain authoritative" not in classify:
    fail("diagnostic-only ownership invariant comment is missing")

# Producer/c64 correlation is telemetry-only. The latest DX9Ex maintenance
# deliberately keeps the provenance getter and node-relation bookkeeping off
# the normal HUD draw path when telemetry is disabled.
if "if (semanticHud || Settings::VRTelemetry)" in classify:
    fail("producer provenance lookup leaked back onto the telemetry-off HUD hot path")
getter_call = classify.find("GetLastGameWvpSemanticProvenance(")
if getter_call < 0:
    fail("draw classifier lost c64 provenance getter")
telemetry_guard = classify.rfind("if (Settings::VRTelemetry)", 0, getter_call)
if telemetry_guard < 0:
    fail("c64 provenance getter is not guarded by VRTelemetry")
semantic_hud = classify.find("if (semanticHud)")
accepted_counter = classify.find("++R51VsSemanticHudAccepted", semantic_hud)
same_node_counter = classify.find("++R51VsSemanticHudC64SameNode", semantic_hud)
if min(semantic_hud, accepted_counter, same_node_counter) < 0:
    fail("semantic HUD c64 relation diagnostics are missing")
hud_telemetry_guard = classify.find(
    "if (Settings::VRTelemetry)", semantic_hud, accepted_counter)
if hud_telemetry_guard < 0:
    fail("semantic HUD acceptance counter is not telemetry-gated")
if not (hud_telemetry_guard < accepted_counter < same_node_counter):
    fail("semantic HUD telemetry counters escaped their telemetry guard")


# The original +TIME sprani and numeric/print E8 parents must share one
# exact ScreenHud identity across both direct immediate Draw and appended
# SpriteNodes. An old pending world Draw must survive rather than hijack the
# immediate number glyph; an already active SpriteQueue must retain its scope.
def check_stage_extension_direct_owner(text: str) -> None:
    enter = function_body(text, "static void StageExtensionEnter(")
    leave = function_body(text, "static void StageExtensionLeave(")
    install = function_body(text, "static void Install") if "static void Install" in text else text
    expected = (
        "Settings::VREnabled &&",
        "GameSemantic::SpriteQueueDepth == 0",
        "StageExtensionDirectDrawOwner.emplace(",
        "RenderScope::ScreenHud,",
        "nullptr, true,",
        "ProducerToken::StageExtensionTime",
    )
    for marker in expected:
        if marker not in enter:
            fail("stage +TIME immediate parent lost ownership: " + marker)
    if "GameSemantic::CurrentScope =" in enter:
        fail("stage +TIME immediate parent overrides an active sprite queue")
    for marker in (
        "TagAppendedNodes(StageExtensionBefore,",
        "RenderScope::ScreenHud,",
        "ProducerToken::StageExtensionTime",
        "StageExtensionDirectDrawOwner.reset();",
        "CurrentScope = StageExtensionSavedScope;",
    ):
        if marker not in leave:
            fail("stage +TIME deferred/restore path regressed: " + marker)
    if "StageExtensionSpraniCalls[i]" not in install or \
       "StageExtensionPrintCalls[i]" not in install:
        fail("original +TIME decoration and number producers must both be hooked")

check_stage_extension_direct_owner(ui)
for old, replacement in (
    ("SpriteQueueDepth == 0", "SpriteQueueDepth != 0"),
    ("nullptr, true,", "nullptr, false,"),
    ("ProducerToken::StageExtensionTime);", "ProducerToken::None);"),
    ("StageExtensionDirectDrawOwner.reset();", "/* missing reset */"),
):
    # Mutate the selected +TIME function, not the first matching marker
    # elsewhere in the file (GOAL progress now owns the same direct flag).
    # A global replace silently mutated GOAL and falsely failed this gate.
    function_marker = ("static void StageExtensionLeave("
                       if old == "StageExtensionDirectDrawOwner.reset();"
                       else "static void StageExtensionEnter(")
    body = function_body(ui, function_marker)
    if old not in body:
        fail("stage +TIME mutation could not be constructed: " + old)
    mutant = ui.replace(body, body.replace(old, replacement, 1), 1)
    try:
        check_stage_extension_direct_owner(mutant)
    except SystemExit:
        pass
    else:
        fail("unsafe stage +TIME ownership mutation escaped: " + old)


# GOAL progress, title/time synchronous glyphs and their queued siblings
# must share exact provenance without consuming an earlier world Draw.
def verify_goal_owner(source: str) -> None:
    progress = function_body(source, "static void ResultProgressEnter(")
    leave = function_body(source, "static void ResultProgressLeave(")
    goal = function_body(source, "static void GoalTime_TagHelper(")
    for marker in ("Settings::VREnabled", "ResultProgressDirectDrawOwner.emplace(",
                   "RenderScope::ScreenHud,", "nullptr, true,",
                   "ProducerToken::ResultProgress"):
        if marker not in progress:
            fail("GOAL progress direct producer lost: " + marker)
    for marker in ("TagAppendedNodes(ResultProgressTailsBefore,",
                   "ProducerToken::ResultProgress",
                   "ResultProgressDirectDrawOwner.reset();"):
        if marker not in leave:
            fail("GOAL progress deferred producer lost: " + marker)
    for marker in ("helperRva == 0xBE020", "ProducerToken::GoalTime020",
                   "helperRva == 0xBE150", "ProducerToken::GoalTime150",
                   "goalDirectDrawOwner.emplace(", "nullptr, true, producer",
                   "original();", "goalDirectDrawOwner.reset();",
                   "TagAppendedNodes(before,", "RenderScope::ScreenHud, producer"):
        if marker not in goal:
            fail("GOAL title/time owner lost: " + marker)
    if goal.index("const auto producer") > goal.index("original();"):
        fail("GOAL direct producer identity assigned after glyph Draw")
    if "GameSemantic::CurrentScope =" in goal:
        fail("GOAL time helper overrides an active queue")
    for marker in ("ResultProgressCallA + 5", "ResultProgressCallB + 5",
                   "GoalTime_Help020, Memory::HookType::Call",
                   "GoalTime_Help150, Memory::HookType::Call"):
        if marker not in source:
            fail("an exact original GOAL E8 producer disappeared: " + marker)
    if "ResultTextEnterHooks[i] = safetyhook::create_mid" in source:
        fail("crash-prone 19 GOAL result-text return detours re-enabled")

verify_goal_owner(ui)
for func, old, replacement in (
    ("static void ResultProgressEnter(", "nullptr, true,", "nullptr, false,"),
    ("static void ResultProgressEnter(", "ProducerToken::ResultProgress", "ProducerToken::None"),
    ("static void GoalTime_TagHelper(", "nullptr, true, producer", "nullptr, false, producer"),
    ("static void GoalTime_TagHelper(", "ProducerToken::GoalTime020", "ProducerToken::None"),
    ("static void GoalTime_TagHelper(", "goalDirectDrawOwner.reset();", "/* missing reset */"),
):
    body = function_body(ui, func)
    if old not in body:
        fail("GOAL mutation has no source: " + old)
    mutant = ui.replace(body, body.replace(old, replacement, 1), 1)
    try:
        verify_goal_owner(mutant)
    except SystemExit:
        pass
    else:
        fail("GOAL negative mutation escaped: " + old)

print("VR producer provenance contract PASS")
