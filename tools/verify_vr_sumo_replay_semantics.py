#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEMANTICS = ROOT / "src/vr/game/render_semantics.hpp"
FRAMERATE = ROOT / "src/hooks_framerate.cpp"


def fail(message: str) -> None:
    raise SystemExit(f"VR Sumo replay semantic contract FAILED\n - {message}")


def require_text(path: Path) -> str:
    if not path.is_file():
        fail(f"missing required source: {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def function_body(source: str, marker: str) -> str:
    start = source.find(marker)
    if start < 0:
        fail(f"missing function marker: {marker}")
    brace = source.find("{", start)
    if brace < 0:
        fail(f"missing function body for: {marker}")

    depth = 0
    for i in range(brace, len(source)):
        ch = source[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return source[brace + 1 : i]
    fail(f"unterminated function body for: {marker}")
    return ""


semantics = require_text(SEMANTICS)
framerate = require_text(FRAMERATE)

peek = function_body(semantics, "inline RenderScope PeekSpriteNodeScope(")
if "RenderScope fallback = RenderScope::None" not in semantics:
    fail("PeekSpriteNodeScope must default to RenderScope::None")
if "return SpriteNodeSemanticTags[i].scope;" not in peek:
    fail("PeekSpriteNodeScope no longer returns the registered explicit scope")
if "return fallback;" not in peek:
    fail("PeekSpriteNodeScope lost fallback behavior")
if "ConsumeSpriteNodeScope(" in peek:
    fail("PeekSpriteNodeScope must remain non-consuming")
if re.search(r"SpriteNodeSemanticCount\s*(?:\+\+|--|[+\-]?=)", peek):
    fail("PeekSpriteNodeScope must not mutate SpriteNodeSemanticCount")
if re.search(r"SpriteNodeSemanticTags\s*\[[^\]]+\]\s*=", peek):
    fail("PeekSpriteNodeScope must not mutate semantic tags")

entry_start = framerate.find("struct Entry")
entry_end = framerate.find("};", entry_start)
if entry_start < 0 or entry_end < 0:
    fail("Sumo replay Entry definition is missing")
entry = framerate[entry_start:entry_end]
for marker in (
    "OutRunVR::GameSemantic::RenderScope vrScope",
    "OutRunVR::GameSemantic::RenderScope::None",
):
    if marker not in entry:
        fail(f"Sumo replay Entry missing semantic snapshot field: {marker}")

capture = function_body(framerate, "static void capture()")
if "ConsumeSpriteNodeScope(" in capture:
    fail("capture must not consume the original SpriteNode semantic tag")
capture_peek = capture.find("entry.vrScope")
peek_call = capture.find("OutRunVR::GameSemantic::PeekSpriteNodeScope(", capture_peek)
peek_node = capture.find("node, OutRunVR::GameSemantic::RenderScope::None", peek_call)
if min(capture_peek, peek_call, peek_node) < 0 or not (
    capture_peek <= peek_call <= peek_node
):
    fail("capture must snapshot explicit scope with non-consuming PeekSpriteNodeScope(node, None)")

replay = function_body(framerate, "static void replay()")
required_order = [
    "Game::put_sprite_ex(&scratch, entry.priority);",
    "if (!node || node == tailBefore)",
    "node->kind_C = entry.kind;",
    "node->args_10 = entry.args;",
    "node->args2_58 = entry.args2;",
    "if (entry.vrScope !=",
    "OutRunVR::GameSemantic::RenderScope::None",
    "OutRunVR::GameSemantic::RegisterSpriteNodeScope(",
    "node, entry.vrScope",
]
positions = [replay.find(marker) for marker in required_order]
if min(positions) < 0 or positions != sorted(positions):
    fail("replay semantic restore ordering changed or required guard is missing")

register_pos = replay.find("OutRunVR::GameSemantic::RegisterSpriteNodeScope(")
none_guard_pos = replay.rfind("if (entry.vrScope !=", 0, register_pos)
if none_guard_pos < 0:
    fail("replay must guard semantic registration with explicit non-None scope")
guard_slice = replay[none_guard_pos:register_pos]
if "OutRunVR::GameSemantic::RenderScope::None" not in guard_slice:
    fail("replay non-None guard no longer checks RenderScope::None")
if "ScreenHud" in guard_slice or "WorldBillboard" in guard_slice:
    fail("replay must preserve captured scope, not promote to a fixed HUD/world scope")

if replay.count("RegisterSpriteNodeScope(") != 1:
    fail("replay must have exactly one explicit semantic re-registration site")
if "ConsumeSpriteNodeScope(" in replay:
    fail("replay must not consume semantic state while reconstructing the queue")

update = function_body(framerate, "static void update(int numUpdates)")
capture_pos = update.find("capture();")
replay_pos = update.find("replay();")
if min(capture_pos, replay_pos) < 0 or capture_pos > replay_pos:
    fail("update must capture on tick frames and replay on non-tick frames")

print("VR Sumo replay semantic contract PASS")
