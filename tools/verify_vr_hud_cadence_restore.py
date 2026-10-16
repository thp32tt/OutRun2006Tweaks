#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UISCALE = ROOT / "src/hooks_uiscaling.cpp"
SEMANTICS = ROOT / "src/vr/game/render_semantics.hpp"
PROFILES = ROOT / "tools/OutRunVR-TestProfiles.ps1"
POLICY = ROOT / "tools/Test-OutRunVRTestPolicy.ps1"
OUTRUN_RENDERER = ROOT / "src/vr/game/outrun_renderer.cpp"
WORKFLOW = ROOT / ".github/workflows/vr-dx9ex-active.yml"


def fail(message: str) -> None:
    raise SystemExit(f"VR HUD/cadence restore contract FAILED\n - {message}")


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
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[brace + 1:i]
    fail(f"unterminated function body for: {marker}")
    return ""


def exact_int_array(source: str, name: str, expected: list[int]) -> None:
    match = re.search(
        rf"static\s+constexpr\s+int\s+{re.escape(name)}\s*\[\]\s*=\s*\{{(.*?)\}}\s*;",
        source,
        re.DOTALL,
    )
    if not match:
        fail(f"missing exact producer array: {name}")
    values = [int(v, 16) for v in re.findall(r"0x[0-9A-Fa-f]+", match.group(1))]
    if values != expected:
        fail(f"{name} changed: expected {[hex(v) for v in expected]}, got {[hex(v) for v in values]}")


uiscale = require_text(UISCALE)
semantics = require_text(SEMANTICS)
profiles = require_text(PROFILES)
policy = require_text(POLICY)
outrun_renderer = require_text(OUTRUN_RENDERER)
workflow = require_text(WORKFLOW)

exact_int_array(
    uiscale,
    "OptionArrow_ClipSpriteCalls",
    [0xE358B, 0xE35A3, 0xE35CC, 0xE35F7, 0xE481B, 0xE4833,
     0xE485C, 0xE4887, 0xEC24C, 0xEC277, 0xED4D4, 0xED7A3],
)
exact_int_array(
    uiscale,
    "ExactScreenHud_ClipSpriteCalls",
    [0x460F1, 0x463D6, 0x46410, 0x97BB7, 0x97DA7,
     0xBDB0E, 0xBDB2D, 0xBDB4C, 0xBDB8E,
     0xBE311, 0xBE343, 0xBE3E3, 0xBE424, 0xBE45D],
)
exact_int_array(
    uiscale,
    "ExactScreenHudRight_ClipSpriteCalls",
    [0xB9F3A, 0xB9F5E, 0xB9F81, 0xB9FD0,
     0xB9FFC, 0xBA01E, 0xBA035, 0xBA052,
     0xBD32E, 0xBD397, 0xBD414, 0xBD472,
     0xBE5CD, 0xBE603, 0xBE633, 0xBE66D, 0xBE690,
     0xBE6B5, 0xBE6D5, 0xBE7E8, 0xBE802, 0xBE81C,
     0xBE8D8, 0xBE915, 0xBE94A, 0xBE97A, 0xBE9A3],
)
exact_int_array(
    uiscale,
    "ExactScreenHudLeft_ClipSpriteCalls",
    [0xB9096, 0xB90B3],
)
exact_int_array(uiscale, "TextGlyph_PutSpriteCalls", [0x2C808, 0x2C9DB])

rival = re.search(
    r"static\s+constexpr\s+int\s+RivalMarker_SpraniCall\s*=\s*(0x[0-9A-Fa-f]+)\s*;",
    uiscale,
)
if not rival or int(rival.group(1), 16) != 0xBB796:
    fail("exact gameplay rival-marker producer must remain 0xBB796")

# The real sprite queue snapshot/tag moved to the shared owned implementation.
# Verify the original call still sits between the queue snapshot and the
# ScreenHud tag, and that each wrapper supplies ONLY its own producer token.
# Matching all three in the forwarding wrapper itself would miss the native
# Draw -> queued siblings ordering and incorrectly reject the refactor.
screen_hud_owned = function_body(uiscale, "static int ExactScreenHud_putClipSpriteOwned(")
screen_markers = [
    "tailsBefore",
    "Game::put_clip_sprite(",
    "TagAppendedNodes(tailsBefore,",
    "OutRunVR::GameSemantic::RenderScope::ScreenHud, producer",
]
screen_pos = [screen_hud_owned.find(m) for m in screen_markers]
if min(screen_pos) < 0 or screen_pos != sorted(screen_pos):
    fail("exact clip-sprite ScreenHud owned queue registration ordering changed")
if "WorldBillboard" in screen_hud_owned or "ScreenOverlay2D" in screen_hud_owned:
    fail("exact ScreenHud clip owner must not broaden spatial scope")
screen_hud = function_body(uiscale, "static int __cdecl ExactScreenHud_putClipSprite(")
if ("return ExactScreenHud_putClipSpriteOwned(" not in screen_hud or
        "ProducerToken::ExactScreenHudClipSprite" not in screen_hud or
        "PauseOptionArrow" in screen_hud):
    fail("ordinary clip-sprite must forward exact ScreenHud source, not pause arrows")

# Original paused-game option arrows get the separate semantic owner only
# when VR and the actual pause state are active. Their GPU batch must be
# drained before/after the owned original E8 call without broadening generic
# HUD, normal menu, or F11 ownership.
pause_arrow = function_body(uiscale, "static int __cdecl PauseOptionArrow_putClipSprite(")
pause_markers = [
    "!Settings::VREnabled",
    "GameState::STATE_SMPAUSEMENU",
    "return ExactScreenHud_putClipSprite(",
    "FlushD3DXBeforeDirectGoalSource();",
    "ScopedExactProducerSemantic directArrowOwner(",
    "ProducerToken::PauseOptionArrow",
    "ExactScreenHud_putClipSpriteOwned(",
    "FlushD3DXAtDirectGoalSourceExit();",
]
pause_positions = [pause_arrow.find(m) for m in pause_markers]
if min(pause_positions) < 0 or pause_positions != sorted(pause_positions):
    fail("exact pause-arrow source/flush ordering or inactive fallback changed")
if ("QueueRenderActive()" not in pause_arrow or
        "RenderScope::ScreenHud" not in pause_arrow or
        pause_arrow.count("ProducerToken::PauseOptionArrow") != 2 or
        "RenderScope::WorldBillboard" in pause_arrow):
    fail("pause-arrow exact VR producer must not borrow an unrelated owner")

rival_body = function_body(uiscale, "static int __cdecl RivalMarker_sprani(")
rival_markers = [
    "const auto projectedAnchor = RivalMarkerProjectedInfo;",
    "RivalMarkerProjectedInfo = {};",
    "OutRunVR::GameSemantic::RenderScope::WorldBillboard",
    "ScopedExactProducerSemantic producerScope(",
    "Game::sprani_play_ae_auth_alpha(",
    "TagAppendedNodes(before, scope,",
]
rival_pos = [rival_body.find(m) for m in rival_markers]
if min(rival_pos) < 0 or rival_pos != sorted(rival_pos):
    fail("rival must consume exact view anchor, scope original draw and then tag queued children")
if rival_body.count("projected ? &projectedAnchor : nullptr") != 2:
    fail("rival must preserve one frozen exact projected anchor for direct and queued draws")
if "ScreenHud" in rival_body or "ScreenOverlay2D" in rival_body:
    fail("rival marker wrapper must remain spatial and exact-only")

glyph_body = function_body(uiscale, "static int __cdecl TextGlyph_putSprite(")
# The previous one-branch order check mistook the new exact B9200 branch
# for the ordinary Sumo_Printf fallback. Prove each mutually exclusive
# source-to-queue route after put_sprite_ex independently, not by matching
# whichever TagAppendedNodes occurs first.
original_markers = ["tailsBefore", "Module::exe_ptr(0x2CFE0)",
                    "original(args, priority)"]
original_pos = [glyph_body.find(m) for m in original_markers]
if min(original_pos) < 0 or original_pos != sorted(original_pos):
    fail("result glyph must capture priority tails then call original put_sprite_ex")
try:
    begin_exact = glyph_body.index("if (exactGoalResult)\n        {\n            TagAppendedNodes")
    begin_default = glyph_body.index("else\n        {\n            // The untouched +TIME")
except ValueError:
    fail("B9200 result glyph exact/legacy branch missing")
if begin_exact <= original_pos[-1] or begin_default <= begin_exact:
    fail("GOAL B9200 result ownership must follow the original glyph")
for name, section, producer in (
    ("exact B9200", glyph_body[begin_exact:begin_default],
     "OutRunVR::GameSemantic::ProducerToken::ResultTextB9200"),
    ("legacy Sumo_Printf", glyph_body[begin_default:],
     "OutRunVR::GameSemantic::ProducerToken::TextGlyphPutSprite"),
):
    markers = ["TagAppendedNodes(tailsBefore,",
               "OutRunVR::GameSemantic::RenderScope::ScreenHud", producer]
    positions = [section.find(m) for m in markers]
    if min(positions) < 0 or positions != sorted(positions):
        fail(name + " glyph children must retain their own ScreenHud source")

right_clip = function_body(uiscale, "static int __cdecl ExactScreenHudRight_putClipSprite(")
if "AddSpriteSpacing(&x, false);" not in right_clip or "ExactScreenHud_putClipSprite(" not in right_clip:
    fail("right-side exact HUD wrapper must preserve spacing then register ScreenHud")
left_clip = function_body(uiscale, "static int __cdecl ExactScreenHudLeft_putClipSprite(")
if "AddSpriteSpacing(&x, true);" not in left_clip or "ExactScreenHud_putClipSprite(" not in left_clip:
    fail("left-side exact HUD wrapper must preserve spacing then register ScreenHud")

apply_body = function_body(uiscale, "bool apply() override")
for marker in (
    "for (int addr : OptionArrow_ClipSpriteCalls)",
    "Module::exe_ptr(addr), PauseOptionArrow_putClipSprite",
    "for (int addr : ExactScreenHud_ClipSpriteCalls)",
    "for (int addr : ExactScreenHudRight_ClipSpriteCalls)",
    # R64 exact rank 6th/6 is singled out *inside* this right-side
    # source group, while other TimeAttack/GOAL/C2C right sprites
    # retain the previous ScreenHud wrapper and spacing. Do not stack
    # original 15 E8 MID hooks or apply rank batch Flush to all sprites.
    "IsExactDispRankRightClipRva(addr)",
    "? DispRankRight_putClipSprite",
    ": ExactScreenHudRight_putClipSprite",
    "for (int addr : ExactScreenHudLeft_ClipSpriteCalls)",
    "Module::exe_ptr(addr), ExactScreenHudLeft_putClipSprite",
    "Module::exe_ptr(RivalMarker_SpraniCall)",
    "RivalMarker_sprani, Memory::HookType::Call",
    "for (int addr : TextGlyph_PutSpriteCalls)",
    "Module::exe_ptr(addr), TextGlyph_putSprite",
):
    if marker not in apply_body:
        fail(f"restored HUD producer install path missing: {marker}")

for legacy_mid in (
    "create_mid((void*)0x4BE5CD", "create_mid((void*)0x4BE603",
    "create_mid((void*)0x4BE633", "create_mid((void*)0x4BE66D",
    "create_mid((void*)0x4BE690", "create_mid((void*)0x4BE6B5",
    "create_mid((void*)0x4BE6D5", "create_mid((void*)0x4BE7E8",
    "create_mid((void*)0x4BE802", "create_mid((void*)0x4BE81C",
    "create_mid((void*)0x4BE8D8", "create_mid((void*)0x4BE915",
    "create_mid((void*)0x4BE94A", "create_mid((void*)0x4BE97A",
    "create_mid((void*)0x4BE9A3",
):
    if legacy_mid in apply_body:
        fail(f"exact TimeAttack call must not stack a mid-hook with its call-site producer: {legacy_mid}")

if "RenderScope fallback = RenderScope::ScreenOverlay2D" not in semantics:
    fail("generic SpriteNode fallback must remain ScreenOverlay2D")

correctness_start = profiles.rfind("Name='CORRECTNESS'")
if correctness_start < 0:
    fail("CORRECTNESS profile missing")
correctness = profiles[correctness_start:correctness_start + 1800]
for marker in (
    "'-FramerateLimit=0'",
    "'-FramerateInterpolation=true'",
    "'-FramerateUnlockExperimental=true'",
    "'-FrameCadenceMode=1'",
    "'-FrameCadenceTargetHz=0'",
    "'-DisableDesktopVsync=true'",
):
    if marker not in correctness:
        fail(f"CORRECTNESS XR cadence contract missing: {marker}")
for forbidden in (
    "'-FramerateLimit=60'",
    "'-FramerateInterpolation=false'",
    "'-FramerateUnlockExperimental=false'",
    "'-FrameCadenceMode=0'",
    "'-DisableDesktopVsync=false'",
):
    if forbidden in correctness:
        fail(f"CORRECTNESS regressed to stale cadence: {forbidden}")

# The XR cadence Present path runs at headset refresh. Process liveness must
# reuse one SYNCHRONIZE handle per host PID instead of OpenProcess/CloseHandle
# on every rendered frame; PID changes, host exit, and game Reset release it.
cadence_wait = function_body(
    outrun_renderer, "        void WaitForNextCadenceRequest() noexcept")
cadence_alive = function_body(
    outrun_renderer, "        bool CadenceHostProcessAlive(DWORD hostPid) noexcept")
cadence_close = function_body(
    outrun_renderer, "        void CloseCadenceHostProcess() noexcept")
reset_notify = function_body(
    outrun_renderer, "\tvoid NotifyGameReset()")

for marker in (
    "HANDLE CadenceHostProcess = nullptr;",
    "DWORD CadenceHostProcessPid = 0;",
):
    if marker not in outrun_renderer:
        fail(f"cadence host-process cache state missing: {marker}")

if "OpenProcess(" in cadence_wait or "CloseHandle(" in cadence_wait:
    fail("cadence wait path regressed to per-frame process-handle churn")

# An auto-reset event does NOT consume the SetEvent corresponding to a
# request accepted by the fast path. Reset-before-read must close that race.
# Waking is not acceptance: only a valid NEW request advances the game, and
# all spurious wakeups share one bounded deadline (including 100ms recovery).
cadence_order = (
    "ResetEvent(CadenceRequestEvent)",
    "!ReadCadenceHost(host)",
    "if (host.requestId && host.requestId != current)",
    "const LONGLONG deadlineQpc",
    "for (;;)",
    "WaitForSingleObject(CadenceRequestEvent, remainingMs)",
    "if (ReadCadenceHost(after) && after.requestId",
    "foundNewRequest = true;",
    "if (wait != WAIT_OBJECT_0)",
    "if (foundNewRequest)",
)
# Search each marker AFTER its predecessor: ReadCadenceHost(host) also
# appears once in the initial eligibility check before the event drain.
cadence_position = 0
for marker in cadence_order:
    index = cadence_wait.find(marker, cadence_position)
    if index < 0:
        fail(f"cadence auto-reset drain / re-read / bounded new-token order changed: {marker}")
    cadence_position = index + len(marker)
for marker in (
    "host.hostPid != CadenceHostProcessPid",
    "after.hostPid == host.hostPid",
    "(after.flags & required) == required",
    "end.QuadPart >= deadlineQpc",
    "wait == WAIT_FAILED",
    "CadenceTimedOutRequestId = 0;",
    "CadencePacingActive.store(false, std::memory_order_release);",
):
    if marker not in cadence_wait:
        fail(f"cadence host generation or fail-open contract missing: {marker}")
if cadence_wait.count("WaitForSingleObject(CadenceRequestEvent,") != 1:
    fail("cadence must have exactly one event wait inside the bounded loop")
if "WaitForSingleObject(CadenceRequestEvent, timeoutMs)" in cadence_wait:
    fail("cadence reverted to a one-shot wait that consumes stale signals")
for marker in (
    "CadenceHostProcessAlive(host.hostPid)",
    "CloseCadenceHostProcess();",
):
    if marker not in cadence_wait:
        fail(f"cadence wait path missing cached host-process contract: {marker}")

for marker in (
    "CadenceHostProcess = OpenProcess(SYNCHRONIZE, FALSE, hostPid);",
    "CadenceHostProcessPid != hostPid",
    "WaitForSingleObject(CadenceHostProcess, 0)",
    "wait == WAIT_TIMEOUT",
    "CloseCadenceHostProcess();",
):
    if marker not in cadence_alive:
        fail(f"cadence host-process cache helper missing: {marker}")

for marker in (
    "CloseHandle(CadenceHostProcess);",
    "CadenceHostProcess = nullptr;",
    "CadenceHostProcessPid = 0;",
):
    if marker not in cadence_close:
        fail(f"cadence host-process release helper missing: {marker}")

if "CloseCadenceHostProcess();" not in reset_notify:
    fail("game Reset must release the cached cadence host process handle")

for marker in (
    "Has-Argument $correctness '-FramerateLimit=0'",
    "Has-Argument $correctness '-FramerateInterpolation=true'",
    "Has-Argument $correctness '-FramerateUnlockExperimental=true'",
    "Has-Argument $correctness '-FrameCadenceMode=1'",
    "Has-Argument $correctness '-FrameCadenceTargetHz=0'",
    "Has-Argument $correctness '-DisableDesktopVsync=true'",
):
    if marker not in policy:
        fail(f"runtime-test policy lost corrected cadence assertion: {marker}")

for marker in (
    "- 'src/hooks_uiscaling.cpp'",
    "- 'tools/OutRunVR-TestProfiles.ps1'",
    "- 'tools/verify_vr_hud_cadence_restore.py'",
):
    if marker not in workflow:
        fail(f"DX9Ex Active workflow does not own regression input: {marker}")
for marker in (
    "'tools/verify_vr_hud_cadence_restore.py'",
    "foreach ($verifier in $verifiers)",
    "python $verifier",
    "if ($LASTEXITCODE -ne 0)",
):
    if marker not in workflow:
        fail(f"DX9Ex Active workflow lost fail-closed verifier execution: {marker}")
if "./tools/Test-OutRunVRTestPolicy.ps1" not in workflow:
    fail("DX9Ex Active workflow stopped executing the runtime-test policy")

print("VR HUD/cadence restore contract PASS")
