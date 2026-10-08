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

screen_hud = function_body(uiscale, "static int __cdecl ExactScreenHud_putClipSprite(")
screen_markers = [
    "tailsBefore",
    "Game::put_clip_sprite(",
    "TagAppendedNodes(tailsBefore,",
    "OutRunVR::GameSemantic::RenderScope::ScreenHud",
    "OutRunVR::GameSemantic::ProducerToken::ExactScreenHudClipSprite",
]
screen_pos = [screen_hud.find(m) for m in screen_markers]
if min(screen_pos) < 0 or screen_pos != sorted(screen_pos):
    fail("exact clip-sprite ScreenHud registration ordering changed")
if "WorldBillboard" in screen_hud or "ScreenOverlay2D" in screen_hud:
    fail("exact ScreenHud clip wrapper must not broaden ownership")

rival_body = function_body(uiscale, "static int __cdecl RivalMarker_sprani(")
rival_markers = [
    "Game::sprani_play_ae_auth_alpha(",
    "const auto projectedAnchor = RivalMarkerProjectedInfo;",
    "RivalMarkerProjectedInfo = {};",
    "TagAppendedNodes(",
    "OutRunVR::GameSemantic::RenderScope::WorldBillboard",
]
rival_pos = [rival_body.find(m) for m in rival_markers]
if min(rival_pos) < 0 or rival_pos != sorted(rival_pos):
    fail("rival marker must tag appended nodes as WorldBillboard after the exact producer")
if "ScreenHud" in rival_body or "ScreenOverlay2D" in rival_body:
    fail("rival marker wrapper must remain spatial and exact-only")

glyph_body = function_body(uiscale, "static int __cdecl TextGlyph_putSprite(")
glyph_markers = [
    "Module::exe_ptr(0x2CFE0)",
    "original(args, priority)",
    "if (node && node != tailBefore)",
    "OutRunVR::GameSemantic::RegisterSpriteNodeScope(",
    "node, OutRunVR::GameSemantic::RenderScope::ScreenHud",
]
glyph_pos = [glyph_body.find(m) for m in glyph_markers]
if min(glyph_pos) < 0 or glyph_pos != sorted(glyph_pos):
    fail("exact text glyph producer must tag only the newly appended node as ScreenHud")

right_clip = function_body(uiscale, "static int __cdecl ExactScreenHudRight_putClipSprite(")
if "AddSpriteSpacing(&x, false);" not in right_clip or "ExactScreenHud_putClipSprite(" not in right_clip:
    fail("right-side exact HUD wrapper must preserve spacing then register ScreenHud")
left_clip = function_body(uiscale, "static int __cdecl ExactScreenHudLeft_putClipSprite(")
if "AddSpriteSpacing(&x, true);" not in left_clip or "ExactScreenHud_putClipSprite(" not in left_clip:
    fail("left-side exact HUD wrapper must preserve spacing then register ScreenHud")

apply_body = function_body(uiscale, "bool apply() override")
for marker in (
    "for (int addr : OptionArrow_ClipSpriteCalls)",
    "Module::exe_ptr(addr), ExactScreenHud_putClipSprite",
    "for (int addr : ExactScreenHud_ClipSpriteCalls)",
    "for (int addr : ExactScreenHudRight_ClipSpriteCalls)",
    "Module::exe_ptr(addr), ExactScreenHudRight_putClipSprite",
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
