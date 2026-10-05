#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

R30_PATH = ROOT / "src/vr/d3d9/stereo_renderer_r30.cpp"
R31_PATH = ROOT / "src/vr/d3d9/stereo_renderer_r31.cpp"
R32_PATH = ROOT / "src/vr/d3d9/stereo_renderer_r32.cpp"
R33_PATH = ROOT / "src/vr/d3d9/stereo_renderer_r33.cpp"
STATEBLOCK_PATH = ROOT / "src/vr/state/state_block_tracker.hpp"
WORKFLOW_PATH = ROOT / ".github/workflows/vr-dx9ex-active.yml"


def fail(message: str) -> None:
    raise SystemExit(
        "VR R31/R32 retirement precondition guard FAILED\n"
        f" - {message}"
    )


def load(path: Path) -> str:
    if not path.is_file():
        fail(f"missing required file: {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def require(text: str, owner: str, *markers: str) -> None:
    for marker in markers:
        if marker not in text:
            fail(f"{owner} missing retirement invariant: {marker}")


def function_body(source: str, marker: str) -> str:
    start = source.find(marker)
    if start < 0:
        fail(f"missing function marker: {marker}")
    brace = source.find("{", start)
    if brace < 0:
        fail(f"missing function body for: {marker}")
    depth = 0
    for index in range(brace, len(source)):
        ch = source[index]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return source[brace + 1:index]
    fail(f"unterminated function body for: {marker}")
    return ""


r30 = load(R30_PATH)
r31 = load(R31_PATH)
r32 = load(R32_PATH)
r33 = load(R33_PATH)
stateblock = load(STATEBLOCK_PATH)
workflow = load(WORKFLOW_PATH)

# 1) R31 remains the fallback-capable R30 successor until a replacement
# transaction proves equivalent draw and StateBlock ownership.
require(
    r31,
    "R31",
    "SafetyHookInline R31DrawPrimitiveR30Hook{};",
    "SafetyHookInline R31DrawIndexedPrimitiveR30Hook{};",
    "SafetyHookInline R31DrawPrimitiveUPR30Hook{};",
    "SafetyHookInline R31DrawIndexedPrimitiveUPR30Hook{};",
    "SafetyHookInline R31CreateStateBlockHook{};",
    "SafetyHookInline R31BeginStateBlockHook{};",
    "SafetyHookInline R31EndStateBlockHook{};",
    "SafetyHookInline R31StateBlockApplyHook{};",
)
r31_install = function_body(r31, "DWORD WINAPI R31InstallThread(void*)")
require(
    r31_install,
    "R31 install",
    "const auto r30 = R30InstallStatus();",
    "const auto renderer = OutRunVRRenderer::R29RendererState();",
    "R30 or renderer prerequisite failed; R30 remains authoritative",
    "reinterpret_cast<void*>(&DrawPrimitiveDestR30)",
    "DrawPrimitiveDestR31, disabled",
    "reinterpret_cast<void*>(&DrawIndexedPrimitiveDestR30)",
    "DrawIndexedPrimitiveDestR31, disabled",
    "reinterpret_cast<void*>(&DrawPrimitiveUPDestR30)",
    "DrawPrimitiveUPDestR31, disabled",
    "reinterpret_cast<void*>(&DrawIndexedPrimitiveUPDestR30)",
    "DrawIndexedPrimitiveUPDestR31, disabled",
    "StateBlockTracker::LifecycleHooksReady()",
    "R22 lifecycle hooks are authoritative; R31 physical StateBlock hooks are not installed",
    "R31 fallback StateBlock hooks armed",
    "fallbackEndArmed = R31EndStateBlockHook.enable().has_value();",
    "fallbackBeginArmed = R31BeginStateBlockHook.enable().has_value();",
    "fallbackCreateArmed = R31CreateStateBlockHook.enable().has_value();",
    "R31RollbackDrawHooks();",
    "StateBlockEvents::Clear();",
    "StateBlockRecovery::Clear();",
    "StateBlockTracker::MarkCoverageLost();",
)
fallback_end = r31_install.find(
    "fallbackEndArmed = R31EndStateBlockHook.enable().has_value();")
fallback_begin = r31_install.find(
    "fallbackBeginArmed = R31BeginStateBlockHook.enable().has_value();")
fallback_create = r31_install.find(
    "fallbackCreateArmed = R31CreateStateBlockHook.enable().has_value();")
ready_publish = r31_install.find(
    "StateBlockTracker::SetEventConsumerReady(true)")
if min(fallback_end, fallback_begin, fallback_create, ready_publish) < 0 or not (
    fallback_end < fallback_begin < fallback_create < ready_publish
):
    fail(
        "R31 fallback StateBlock transaction must arm End -> Begin -> Create "
        "before publishing EventConsumerReady"
    )

require(
    stateblock,
    "StateBlockTracker",
    "return R22Reliable() &&",
    "EventConsumerReady() &&",
    "!CoverageLost();",
    "static bool LifecycleHooksReady() noexcept",
)

# 2) R32 is still a behavior-bearing owner, not a removable alias. It joins
# R31 draw behavior with R22 Reset and R13 Present/DirectGPU ownership.
require(
    r32,
    "R32",
    "SafetyHookInline R32ResetR22Hook{};",
    "SafetyHookInline R32ResolveDirectR13Hook{};",
    "SafetyHookInline R32PresentR13Hook{};",
    "SafetyHookInline R32DrawPrimitiveR31Hook{};",
    "SafetyHookInline R32DrawIndexedPrimitiveR31Hook{};",
    "SafetyHookInline R32DrawPrimitiveUPR31Hook{};",
    "SafetyHookInline R32DrawIndexedPrimitiveUPR31Hook{};",
)
r32_install = function_body(r32, "DWORD WINAPI R32InstallThread(void*)")
require(
    r32_install,
    "R32 install",
    "const auto r31 = R31InstallStatus();",
    "const auto r22 = R22InstallStatus();",
    "const auto r13 = R13InstallStatus();",
    "r31 == State::Failed || r22 == State::Failed",
    "r31 == State::Ready && r22 == State::Ready",
    "reinterpret_cast<void*>(&ResetDestR22), ResetDestR32, disabled",
    "reinterpret_cast<void*>(&ResolveDirectTransportR13)",
    "ResolveDirectTransportR32, disabled",
    "reinterpret_cast<void*>(&PresentDestR13), PresentDestR32, disabled",
    "reinterpret_cast<void*>(&DrawPrimitiveDestR31)",
    "DrawPrimitiveDestR32, disabled",
    "reinterpret_cast<void*>(&DrawIndexedPrimitiveDestR31)",
    "DrawIndexedPrimitiveDestR32, disabled",
    "reinterpret_cast<void*>(&DrawPrimitiveUPDestR31)",
    "DrawPrimitiveUPDestR32, disabled",
    "reinterpret_cast<void*>(&DrawIndexedPrimitiveUPDestR31)",
    "DrawIndexedPrimitiveUPDestR32, disabled",
    "R32RollbackHooks();",
    "R31/R22 remain authoritative",
)
reset32 = function_body(r32, "HRESULT __stdcall ResetDestR32(")
reset_lower = reset32.find("R32ResetR22Hook.stdcall<HRESULT>")
reset_rearm = reset32.find("R32ResetAfterGameReset();")
if min(reset_lower, reset_rearm) < 0 or reset_lower > reset_rearm:
    fail("R32 Reset must complete the R22 lifecycle before R32 cache/safety rearm")

present32 = function_body(r32, "HRESULT __stdcall PresentDestR32(")
require(
    present32,
    "R32 Present",
    "R32PresentR13Hook.stdcall<HRESULT>",
)
resolve32 = function_body(r32, "bool ResolveDirectTransportR32(")
require(
    resolve32,
    "R32 DirectGPU",
    "R32ResolveDirectR13Hook.call<bool>",
)
lower_fail_closed = function_body(r32, "HRESULT R32LowerFailClosed(")
require(
    lower_fail_closed,
    "R32 lower fail-close",
    "!R9StereoBaselineSeeded()",
    "return lowerDraw();",
    "CurrentVertexShaderIdentity.exchange(0",
    "const HRESULT hr = lowerDraw();",
    "R32FailClosedZeroDisparityDraws",
)

# 3) R33 is the final dispatcher, but its physical entry chain still depends
# on R32 for Reset/Present and every draw entry. A safe retirement must replace
# these targets atomically while preserving the lower owners on failure.
r33_install = function_body(r33, "DWORD WINAPI R33InstallThread(void*)")
require(
    r33_install,
    "R33 install",
    "const auto r32 = R32InstallStatus();",
    "if (r32 == State::Failed)",
    "if (r32 == State::Ready)",
    "reinterpret_cast<void*>(&ResetDestR32)",
    "ResetDestR33, disabled",
    "reinterpret_cast<void*>(&PresentDestR32)",
    "PresentDestR33, disabled",
    "reinterpret_cast<void*>(&DrawPrimitiveDestR32)",
    "DrawPrimitiveDestR33, disabled",
    "reinterpret_cast<void*>(&DrawIndexedPrimitiveDestR32)",
    "DrawIndexedPrimitiveDestR33, disabled",
    "reinterpret_cast<void*>(&DrawPrimitiveUPDestR32)",
    "DrawPrimitiveUPDestR33, disabled",
    "reinterpret_cast<void*>(&DrawIndexedPrimitiveUPDestR32)",
    "DrawIndexedPrimitiveUPDestR33, disabled",
    "R33RollbackHooks();",
    "corrected R32 remains authoritative",
)
reset33 = function_body(r33, "HRESULT __stdcall ResetDestR33(")
require(
    reset33,
    "R33 Reset",
    "R33ResetR32Hook.stdcall<HRESULT>",
    "R33 -> R32 -> R22",
)
present33 = function_body(r33, "HRESULT __stdcall PresentDestR33(")
require(
    present33,
    "R33 Present",
    "R33PresentR32Hook.stdcall<HRESULT>",
)

# 4) R33's final fallback intentionally bypasses the R31/R32 stereo overlays
# but still passes through R32's fail-close guard and R30-owned lower-R29
# storage. This exact ownership must survive any future physical flattening.
dispatch33 = function_body(
    r33,
    "HRESULT R33Dispatch(IDirect3DDevice9* device,")
require(
    dispatch33,
    "R33 dispatch",
    "R31DiscardUnreliableDrawCaches();",
    "return R32LowerFailClosed(device,",
    "std::forward<LowerR29Draw>(lowerR29Draw)",
)

r33_lower_calls = (
    "R30CallLowerDrawPrimitive(",
    "R30CallLowerDrawIndexedPrimitive(",
    "R30CallLowerDrawPrimitiveUP(",
    "R30CallLowerDrawIndexedPrimitiveUP(",
)
for marker in r33_lower_calls:
    if marker not in r33:
        fail(f"R33 final fallback lost lower-R29 owner call: {marker}")

lower_owner_pairs = (
    ("R30CallLowerDrawPrimitive(", "R30DrawPrimitiveR29Hook.stdcall<HRESULT>"),
    ("R30CallLowerDrawIndexedPrimitive(", "R30DrawIndexedPrimitiveR29Hook.stdcall<HRESULT>"),
    ("R30CallLowerDrawPrimitiveUP(", "R30DrawPrimitiveUPR29Hook.stdcall<HRESULT>"),
    ("R30CallLowerDrawIndexedPrimitiveUP(", "R30DrawIndexedPrimitiveUPR29Hook.stdcall<HRESULT>"),
)
for function_marker, owner_marker in lower_owner_pairs:
    body = function_body(r30, f"inline HRESULT {function_marker}")
    if owner_marker not in body:
        fail(
            f"{function_marker.rstrip('(')} no longer delegates to "
            f"{owner_marker}"
        )

# 5) The guard itself must be owned by the canonical DX9Ex Active Gate. The
# first TDD commit intentionally fails here until the workflow wiring lands.
require(
    workflow,
    "DX9Ex Active workflow",
    "- 'tools/verify_vr_r31_r32_retirement_guard.py'",
    "python tools/verify_vr_r31_r32_retirement_guard.py",
)

print(
    "VR R31/R32 retirement precondition guard PASS "
    "(physical retirement remains DEFERRED until an atomic replacement "
    "preserves install fallback, Reset/Present/DirectGPU, StateBlock coverage "
    "and lower-R29 fallback)"
)
