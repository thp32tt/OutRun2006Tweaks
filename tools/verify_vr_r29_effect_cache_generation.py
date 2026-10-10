#!/usr/bin/env python3
"""Fail-closed R29 effect-cache contract across StateBlock Apply generations."""
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
src = (root / "src/vr/d3d9/stereo_renderer_r29.cpp").read_text(encoding="utf-8")
tracker = (root / "src/vr/state/state_block_tracker.hpp").read_text(encoding="utf-8")
r31 = (root / "src/vr/d3d9/stereo_renderer_r31.cpp").read_text(encoding="utf-8")

def body(s, key):
    pos = s.find(key)
    if pos < 0: return ""
    start = s.find("{", pos)
    if start < 0: return ""
    level = 0
    for i in range(start, len(s)):
        level += (s[i] == "{") - (s[i] == "}")
        if level == 0: return s[start:i+1]
    return ""

def contract(s):
    cache = body(s, "bool R29EffectCacheCurrent() noexcept")
    sync = body(s, "bool R29SyncEffectState(")
    setter = body(s, "HRESULT __stdcall SetRenderStateDestR29(")
    tel = body(s, "inline bool TryGetEffectTelemetrySnapshot(")
    return all((
        "StateBlockTracker::Reliable()" in cache,
        "StateBlockTracker::ApplyGeneration()" in cache,
        "R29Effect.applyGeneration !=" in cache,
        "R29Effect.presentEpoch == PresentEpoch" in cache,
        "TopLevelDrawSerial() - R29Effect.drawSerial < 64" in cache,
        "R29EffectCacheCurrent()" in sync,
        "const auto applyGenerationBefore =" in sync,
        "StateBlockTracker::ApplyGeneration() !=" in sync,
        "R29Effect.applyGeneration = applyGenerationBefore;" in sync,
        "R29Effect.valid = false;" in sync,
        "R29Effect.applyGeneration !=" in setter,
        "if (!R29EffectCacheCurrent())" in tel,
        sync.find("applyGenerationBefore") < sync.find("device->GetRenderState(")
            < sync.find("StateBlockTracker::ApplyGeneration() !="),
        setter.find("R29Effect.applyGeneration !=") < setter.find("switch (state)"),
        "if (false && R29Effect.applyGeneration !=" not in s,
        "R29Effect.valid && false &&" not in s,
        "R29Effect.applyGeneration = 0;" not in s,
        "if (false)" not in cache and "if (false)" not in sync and "if (false)" not in tel,
    ))

errors = []
if not contract(src):
    errors.append("R29 effect-cache generation/read fencing contract")
if "static void R31OnStateBlockApply(" not in r31 or "StateBlockTracker::NoteApply();" not in r31:
    errors.append("R31 StateBlock Apply generation producer")
if "static bool Reliable() noexcept" not in tracker or "static std::uint64_t ApplyGeneration()" not in tracker:
    errors.append("shared generation/coverage tracker")
mutations = [
    ("reliability", "if (!OutRunVR::State::StateBlockTracker::Reliable())", "if (false)"),
    ("apply generation", "if (R29Effect.applyGeneration !=", "if (false && R29Effect.applyGeneration !="),
    ("torn read", "if (OutRunVR::State::StateBlockTracker::ApplyGeneration() !=\n                applyGenerationBefore)", "if (false)"),
    ("stale setter", "if (R29Effect.valid &&\n                R29Effect.applyGeneration !=", "if (R29Effect.valid && false &&\n                R29Effect.applyGeneration !="),
    ("telemetry", "if (!R29EffectCacheCurrent())\n            return false;", "if (false)\n            return false;"),
    ("stamp", "R29Effect.applyGeneration = applyGenerationBefore;", "R29Effect.applyGeneration = 0;"),
]
for name, before, after in mutations:
    if src.count(before) != 1:
        errors.append("bad mutation fixture: " + name)
    elif contract(src.replace(before, after, 1)):
        errors.append("negative escaped: " + name)
if errors:
    print("FAIL " + ", ".join(errors), file=sys.stderr)
    sys.exit(1)
print("PASS R29 cross-thread Apply generation and 6 negative mutations")
