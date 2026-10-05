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
if "PeekSpriteNodeProducerToken(node)" not in capture:
    fail("Sumo replay capture must non-destructively snapshot producer token")
if "ConsumeSpriteNodeScope(" in capture:
    fail("Sumo replay capture must remain non-consuming")

replay = function_body(framerate, "static void replay()")
if "node, entry.vrScope, entry.vrProducer" not in replay:
    fail("Sumo replay must restore scope and producer token on the fresh node")

# c64 upload is the first durable renderer boundary after queue ownership.
record = function_body(renderer, "void RecordGameWvpWrite(")
for marker in (
    "CurrentQueueProducerToken()",
    "LastGameWvpProducerToken",
    "VR R51 C64 FINGERPRINT:",
):
    if marker not in record:
        fail(f"c64 provenance capture missing: {marker}")

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
same_node_counter = classify.find("++R51VsSemanticHudC64SameNode", semantic_hud)
if min(semantic_hud, same_node_counter) < 0:
    fail("semantic HUD c64 relation diagnostics are missing")
hud_telemetry_guard = classify.find(
    "if (Settings::VRTelemetry)", semantic_hud, same_node_counter)
if hud_telemetry_guard < 0:
    fail("semantic HUD c64 relation counters are not telemetry-gated")

print("VR producer provenance contract PASS")
