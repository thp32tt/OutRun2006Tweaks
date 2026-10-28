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
# Exact C993 lens draws interpose a short-lived middle branch between
# queued SpriteNodes and direct glyph producers. Validate executable branch
# priority rather than a removed three-token conditional expression.
producer_priority = (
    "if (SpriteQueueDepth != 0)",
    "return CurrentSpriteQueueProducer;",
    "if (ExactLensCentreDrawOwnsSemantic())",
    "return ProducerToken::LensFlareCentre;",
    "return CurrentDirectExactProducer;",
)
if any(marker not in producer_selector for marker in producer_priority):
    fail("render producer selector lost queue/centre/direct fallback")
if [producer_selector.index(marker) for marker in producer_priority] != sorted(
    producer_selector.index(marker) for marker in producer_priority
):
    fail("render producer selector reordered queue/centre/direct priority")
# Mutations in either selected source or the lens interposition must be
# rejected without granting the centre owner to queued HUD/world nodes.
for origin, corrupt in (
    ("if (SpriteQueueDepth != 0)", "if (false)"),
    ("return CurrentSpriteQueueProducer;", "return CurrentDirectExactProducer;"),
    ("if (ExactLensCentreDrawOwnsSemantic())", "if (false)"),
    ("return ProducerToken::LensFlareCentre;", "return ProducerToken::None;"),
    ("return CurrentDirectExactProducer;", "return ProducerToken::None;"),
):
    mutant = producer_selector.replace(origin, corrupt, 1)
    if mutant == producer_selector or all(p in mutant for p in producer_priority):
        fail("producer priority mutation was not detected: " + origin)
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
# Current R30 records the actual RivalMarkerSprani physical-GPU boundary in
# opt-in telemetry. Exact producer tags still must not steer the screen-space
# classification function or grant binocular draw admission.
for token in required_tokens:
    if f"ProducerToken::{token}" in classify:
        fail(
            f"R30 screen-space classifier gained exact-producer token {token}; "
            "producer identity is diagnostic-only"
        )
rival = function_body(r30, "HRESULT R30TryScreenSpaceFovDraw(")
if "ProducerToken::RivalMarkerSprani" in rival:
    if ("const bool rivalGpuProbe = Settings::VRTelemetry &&" not in rival or
            "if (rivalGpuProbe)" not in rival or
            "const bool baseAdmitted = R30SafeStereoBase(device);" not in rival):
        fail("R30 rival diagnostic may not replace shared stereo admission")
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
    # The source now snapshots entry admission AND checks live VR state
    # before entering native D3DX. Merely finding another == 0 later in
    # the function would let a mutated source snapshot escape this guard.
    if re.search(
        r"StageExtensionAdmission\s*=\s*\{\s*Settings::VREnabled\s*,\s*"
        r"!OutRunVR::GameSemantic::QueueRenderActive\(\)\s*,\s*"
        r"OutRunVR::GameSemantic::CurrentQueueNodeEpoch\(\)\s*\}",
        enter,
    ) is None:
        fail("stage +TIME entry VR/queue snapshot lost")
    if re.search(
        r"if\s*\(\s*Settings::VREnabled\s*&&\s*"
        r"OutRunVR::GameSemantic::SpriteQueueDepth\s*==\s*0\s*&&\s*"
        r"StageExtensionAdmission\.mayBeginDirect\(\)\s*\)",
        enter,
    ) is None:
        fail("stage +TIME live VR/queue direct ownership fence lost")
    # Ticket-aware gate in the installed exact +TIME exit hook. A changed
    # queue epoch suppresses native D3DX HUD ownership for this source only.
    if not (
        "const bool admitted = sourceTicket != 0 &&" in leave and
        "StageExtensionAdmission.mayPublish(" in leave and
        "if (admitted)" in leave and
        "RevokeD3DXDirectStageTicket(sourceTicket);" in leave and
        "StageExtensionDirectDrawOwner.reset();" in leave and
        leave.find("if (admitted)") <
        leave.find("TagAppendedNodes(StageExtensionBefore,") <
        leave.find("RevokeD3DXDirectStageTicket(sourceTicket);") <
        leave.find("StageExtensionDirectDrawOwner.reset();")
    ):
        fail("stage +TIME queued sibling/native flush exit admission lost")
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


# The live exact BA9D0 HUD text call can draw before the clip/sprani nodes
# exist. Distinct from the six stage +TIME sources, this caller also produces
# ordinary HUD and some GOAL glyphs. Keep its direct token and isolate a
# previously armed world/marker Draw only inside the exact ScreenHud scope.
# The queue and unclassified callers must never be promoted.
def hud_text_direct_binding_ok(source: str) -> bool:
    body = function_body(source, "static void __cdecl OutRunHudTextProducer_dest(")
    start = body.find("directHudOwner.emplace(")
    end = body.find("OutRunHudTextProducerHook.call(", start)
    scope = body[start:end] if start >= 0 and end > start else ""
    return (
        "semantic.space == OutRunVRHudSemantics::SpacePolicy::ScreenHud" in body
        and "Settings::VREnabled" in body
        and "ScopedExactProducerSemantic" in body
        and "ProducerToken::OutRunHudPeripheralText" in body
        and "ProducerToken::OutRunHudText" in body
        and "RenderScope::ScreenHud" in scope
        and re.search(r"nullptr,\s*true,\s*token", scope) is not None
        and "OutRunHudTextProducerHook.call(" in body
        and "OutRunHudPeripheralText = previousPeripheral;" in ui
        and "OutRunHudTextScreenHud = previous;" in ui
    )

if not hud_text_direct_binding_ok(ui):
    fail("exact BA9D0 direct HUD glyph must isolate prior pending world Draw")
for before, after in (
    ("nullptr, true, token", "nullptr, false, token"),
    ("nullptr, true, token", "nullptr, true, ProducerToken::None"),
):
    mutated = ui.replace(before, after, 1)
    if mutated == ui or hud_text_direct_binding_ok(mutated):
        fail("HUD text owner verifier failed negative mutation: " + after)

check_stage_extension_direct_owner(ui)
for old, replacement in (
    ("SpriteQueueDepth == 0", "SpriteQueueDepth != 0"),
    ("nullptr, true,", "nullptr, false,"),
    ("ProducerToken::StageExtensionTime);", "ProducerToken::None);"),
    ("StageExtensionDirectDrawOwner.reset();", "/* missing reset */"),
    ("StageExtensionAdmission.mayPublish(", "StageExtensionAdmission.mayBeginDirect("),
):
    # Mutate the selected +TIME function, not the first matching marker
    # elsewhere in the file (GOAL progress now owns the same direct flag).
    # A global replace silently mutated GOAL and falsely failed this gate.
    function_marker = ("static void StageExtensionLeave("
                       if old in {"StageExtensionDirectDrawOwner.reset();",
                                  "StageExtensionAdmission.mayPublish("}
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
                   "const OutRunVR::GoalProgress::SourceAdmission admission{",
                   "FlushD3DXBeforeDirectGoalSource();",
                   "const bool admittedAfterDrain = admission.mayPublish(",
                   "if (!admittedAfterDrain)", "action=NATIVE_ORIGINAL_ONCE",
                   "ScopedExactProducerSemantic owner(",
                   "nullptr, true, producer", "original(); // exact original helper once",
                   "admittedAtExit = admission.mayPublish(",
                   "TagAppendedNodes(before,", "RenderScope::ScreenHud, producer",
                   "FlushD3DXAtDirectGoalSourceExit();"):
        if marker not in goal:
            fail("GOAL title/time post-drain owner lost: " + marker)
    order = (
        "FlushD3DXBeforeDirectGoalSource();",
        "const bool admittedAfterDrain = admission.mayPublish(",
        "SpriteNodeSemanticNextSerial.load(",
        "ScopedExactProducerSemantic owner(",
        "original(); // exact original helper once",
        "admittedAtExit = admission.mayPublish(",
        "TagAppendedNodes(before,",
        "FlushD3DXAtDirectGoalSourceExit();",
    )
    if [goal.index(marker) for marker in order] != sorted(
            goal.index(marker) for marker in order):
        fail("GOAL title/time drain/admission/owner order regressed")
    if goal.index("const auto producer") > goal.index(
            "original(); // exact original helper once"):
        fail("GOAL direct producer identity assigned after glyph Draw")
    if "goalDirectDrawOwner.emplace(" in goal:
        fail("GOAL time helper regressed to pre-drain unconditional owner")
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
    ("static void GoalTime_TagHelper(", "const bool admittedAfterDrain = admission.mayPublish(",
     "const bool admittedAfterDrain = admission.mayBeginDirect("),
    ("static void GoalTime_TagHelper(", "admittedAtExit = admission.mayPublish(",
     "admittedAtExit = admission.mayBeginDirect("),
    ("static void GoalTime_TagHelper(", "if (!admittedAfterDrain)", "if (false)"),
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

# The original B9200 final-result text wrapper must obey the same post-drain
# admission fence. The call-stack parent is necessary but not sufficient after
# a native Flush that can reenter the queue or change the selection epoch.
def verify_b9200_owner(source: str) -> None:
    body = function_body(source, "static void __cdecl ResultTextB9200_dest(")
    required = (
        "IsOriginalB9200ParentReturn(",
        "const OutRunVR::GoalProgress::SourceAdmission admission{",
        "FlushD3DXBeforeDirectGoalSource();",
        "const bool admittedAfterDrain = admission.mayPublish(",
        "if (!admittedAfterDrain)",
        "action=NATIVE_ORIGINAL_ONCE",
        "ScopedExactProducerSemantic owner(",
        "ProducerToken::ResultTextB9200",
        "admittedAtExit = admission.mayPublish(",
        "FlushD3DXAtDirectGoalSourceExit();",
    )
    for marker in required:
        if marker not in body:
            fail("B9200 post-drain provenance lost: " + marker)
    drain = body.index("FlushD3DXBeforeDirectGoalSource();")
    admitted = body.index(
        "const bool admittedAfterDrain = admission.mayPublish(", drain)
    owner = body.index("ScopedExactProducerSemantic owner(", admitted)
    accepted_draw = body.index(
        "ResultTextB9200InlineHook.call<void>(text, x, y, step);", owner)
    exit_admission = body.index(
        "admittedAtExit = admission.mayPublish(", accepted_draw)
    final_flush = body.index(
        "FlushD3DXAtDirectGoalSourceExit();", exit_admission)
    if not (drain < admitted < owner < accepted_draw <
            exit_admission < final_flush):
        fail("B9200 drain/admission/owner order regressed")
    # The earlier call is the intentional native fallback after a rejected
    # post-drain admission; it must remain before the accepted owner and
    # terminate immediately rather than being mistaken for the owned draw.
    fallback_gate = body.index("if (!admittedAfterDrain)", admitted)
    fallback_draw = body.index(
        "ResultTextB9200InlineHook.call<void>(text, x, y, step);",
        fallback_gate)
    fallback_return = body.index("return;", fallback_draw)
    if not (admitted < fallback_gate < fallback_draw < fallback_return < owner):
        fail("B9200 rejected post-drain fallback ordering regressed")


verify_b9200_owner(ui)
for old, replacement in (
    ("const bool admittedAfterDrain = admission.mayPublish(",
     "const bool admittedAfterDrain = admission.mayBeginDirect("),
    ("admittedAtExit = admission.mayPublish(",
     "admittedAtExit = admission.mayBeginDirect("),
    ("if (!admittedAfterDrain)", "if (false)"),
):
    body = function_body(ui, "static void __cdecl ResultTextB9200_dest(")
    if old not in body:
        fail("B9200 mutation has no source: " + old)
    mutant = ui.replace(body, body.replace(old, replacement, 1), 1)
    try:
        verify_b9200_owner(mutant)
    except SystemExit:
        pass
    else:
        fail("unsafe B9200 ownership mutation escaped: " + old)


# The three 0x97xxx original Sumo_Printf result parents render glyphs
# synchronously, before their queued SpriteNode children acquire source tags.
# CurrentScope alone loses to NextDrawScope (and carries no direct producer);
# require bounded RAII ownership for BOTH the direct GPU path and the queue.
def verify_result_stage_print_owner(source: str) -> None:
    enter = function_body(source, "static void OutRunStagePrintfEnter(")
    leave = function_body(source, "static void OutRunStagePrintfLeave(")
    expected = (
        "OutRunStagePrintfDirectDrawOwner.emplace(",
        "RenderScope::ScreenHud,",
        "nullptr, true,",
        "ProducerToken::OutRunStagePrintf",
    )
    for marker in expected:
        if marker not in enter:
            fail("result stage Sumo_Printf synchronous owner missing: " + marker)
    if "GameSemantic::CurrentScope =" in enter or "ArmNextDraw(" in enter:
        fail("result stage direct source bypasses bounded owner or queue priority")
    for marker in (
        "TagAppendedNodes(OutRunStagePrintfBefore,",
        "RenderScope::ScreenHud,",
        "ProducerToken::OutRunStagePrintf",
        "OutRunStagePrintfDirectDrawOwner.reset();",
    ):
        if marker not in leave:
            fail("result stage Sumo_Printf queued sibling/restore missing: " + marker)
    if "OutRunStagePrintfCalls[] = {" not in source:
        fail("original stage-print CALL array lost")
    for rva in ("0x975EE", "0x97727", "0x977FB"):
        if rva not in source:
            fail("original Sumo_Printf E8 caller lost: " + rva)
    if "OutRunStagePrintfCalls[i] + 5" not in source:
        fail("original result Sumo_Printf parent leave scope absent")


verify_result_stage_print_owner(ui)
for seam, replacement in (
    ("nullptr, true,", "nullptr, false,"),
    ("ProducerToken::OutRunStagePrintf);", "ProducerToken::None);"),
    ("OutRunStagePrintfDirectDrawOwner.emplace(", "/* removed direct owner */ ("),
):
    body = function_body(ui, "static void OutRunStagePrintfEnter(")
    if seam not in body:
        fail("result stage mutation lacks actual source: " + seam)
    mutant = ui.replace(body, body.replace(seam, replacement, 1), 1)
    try:
        verify_result_stage_print_owner(mutant)
    except SystemExit:
        pass
    else:
        fail("unsafe result stage source mutation escaped: " + seam)


print("VR producer provenance contract PASS")
