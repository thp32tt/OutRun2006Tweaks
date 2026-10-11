#!/usr/bin/env python3
"""R29 effect-cache hot-path and StateBlock generation regression gate.

A reliable R22/R31 setter+Apply+recording coverage permits reuse for one
Present without repeated five-field GetRenderState after every 64 draws.
Never reuse across a Present, recording, lost coverage, Apply/Begin/End or
a reversed draw serial. Destructive mutations must break the contract.
"""
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
src = (root / "src/vr/d3d9/stereo_renderer_r29.cpp").read_text(encoding="utf-8")
tracker = (root / "src/vr/state/state_block_tracker.hpp").read_text(encoding="utf-8")
r31 = (root / "src/vr/d3d9/stereo_renderer_r31.cpp").read_text(encoding="utf-8")

def body(s, key):
    pos = s.find(key)
    if pos < 0:
        return ""
    start = s.find("{", pos)
    if start < 0:
        return ""
    level = 0
    for i in range(start, len(s)):
        level += (s[i] == "{") - (s[i] == "}")
        if level == 0:
            return s[start:i + 1]
    return ""

def contract(s):
    cache = body(s, "bool R29EffectCacheCurrent() noexcept")
    sync = body(s, "bool R29SyncEffectState(")
    setter = body(s, "HRESULT __stdcall SetRenderStateDestR29(")
    telemetry = body(s, "inline bool TryGetEffectTelemetrySnapshot(")
    depth_owner = body(s, "bool R29OwnerLeftDrawMayWriteDepth(")
    stereo = body(s, "HRESULT R29DirectTwoEye(")
    return all((
        "StateBlockTracker::Reliable()" in cache,
        "StateBlockTracker::Recording()" in cache,
        "R29Effect.applyGeneration !=" in cache,
        "R29Effect.recordingGeneration !=" in cache,
        "StateBlockTracker::ApplyGeneration()" in cache,
        "StateBlockTracker::RecordingGeneration()" in cache,
        "R29Effect.presentEpoch == PresentEpoch" in cache,
        "TopLevelDrawSerial() >= R29Effect.drawSerial" in cache,
        "TopLevelDrawSerial() - R29Effect.drawSerial < 64" not in cache,
        "R29EffectCacheCurrent()" in sync,
        "if (!device || OutRunVR::State::StateBlockTracker::Recording())" in sync,
        "const auto applyGenerationBefore =" in sync,
        "const auto recordingGenerationBefore =" in sync,
        "StateBlockTracker::ApplyGeneration() !=" in sync,
        "StateBlockTracker::RecordingGeneration() !=" in sync,
        "StateBlockTracker::Recording())" in sync,
        "R29Effect.applyGeneration = applyGenerationBefore;" in sync,
        "R29Effect.recordingGeneration = recordingGenerationBefore;" in sync,
        "R29Effect.valid = false;" in sync,
        "StateBlockTracker::Recording()" in setter,
        "R29Effect.applyGeneration !=" in setter,
        "R29Effect.recordingGeneration !=" in setter,
        "if (!R29EffectCacheCurrent())" in telemetry,
        sync.find("recordingGenerationBefore") < sync.find("device->GetRenderState(")
            < sync.find("StateBlockTracker::RecordingGeneration() !="),
        setter.find("StateBlockTracker::Recording()") < setter.find("switch (state)"),
        "if (false)" not in cache and "if (false)" not in sync,
        "if (false)" not in setter and "if (false)" not in telemetry,
        "if (!device || !TrackedDepthStencil)" in depth_owner,
        "if (R29EffectCacheCurrent())" in depth_owner,
        "return R29Effect.zEnable != D3DZB_FALSE &&" in depth_owner,
        "R29Effect.zWrite != FALSE;" in depth_owner,
        "return false;" in depth_owner,
        "return LeftDrawMayWriteDepth(device);" in depth_owner,
        depth_owner.find("if (!device || !TrackedDepthStencil)") <
            depth_owner.find("if (R29EffectCacheCurrent())") <
            depth_owner.find("return R29Effect.zEnable != D3DZB_FALSE &&") <
            depth_owner.find("return LeftDrawMayWriteDepth(device);"),
        "R29OwnerLeftDrawMayWriteDepth(device)" in stereo,
        "LeftDrawMayWriteStencil(device)" in stereo,
        "if (R29OwnerLeftDrawMayWriteDepth(device) ||" in stereo,
        "R29Effect.applyGeneration = 0;" not in sync,
        "R29Effect.recordingGeneration = 0;" not in sync,
        "R29Effect.valid && false" not in s,
        "if (false && R29Effect.applyGeneration" not in cache,
    ))

errors = []
if not contract(src):
    errors.append("R29 effect-cache time-window/generation contract")
if "void R31OnStateBlockBegin(" not in r31 or "void R31OnStateBlockEnd(" not in r31 or (
        "StateBlockTracker::NoteRecording();" not in r31 or
        "StateBlockTracker::NoteApply();" not in r31):
    errors.append("R31 Begin/End/Apply generation producers")
if not all(k in tracker for k in (
        "static bool Reliable() noexcept",
        "static bool Recording() noexcept",
        "static std::uint64_t RecordingGeneration()",
        "static std::uint64_t ApplyGeneration()")):
    errors.append("shared generation/coverage tracker")

mutations = [
    ("reliability", "if (OutRunVR::State::StateBlockTracker::Recording() ||\n                !OutRunVR::State::StateBlockTracker::Reliable())",
     "if (OutRunVR::State::StateBlockTracker::Recording() ||\n                false)"),
    ("recording cache", "if (OutRunVR::State::StateBlockTracker::Recording() ||\n", "if (false ||\n"),
    ("apply generation", "if (R29Effect.applyGeneration !=", "if (false && R29Effect.applyGeneration !="),
    ("record generation", "R29Effect.recordingGeneration !=\n                    OutRunVR::State::StateBlockTracker::RecordingGeneration()",
     "R29Effect.recordingGeneration ==\n                    OutRunVR::State::StateBlockTracker::RecordingGeneration()"),
    ("present fence", "R29Effect.presentEpoch == PresentEpoch", "R29Effect.presentEpoch != PresentEpoch"),
    ("draw monotonicity", "TopLevelDrawSerial() >= R29Effect.drawSerial", "TopLevelDrawSerial() < R29Effect.drawSerial"),
    ("no periodic getter", "TopLevelDrawSerial() >= R29Effect.drawSerial;",
     "TopLevelDrawSerial() >= R29Effect.drawSerial &&\n                TopLevelDrawSerial() - R29Effect.drawSerial < 64;"),
    ("recording entry", "if (!device || OutRunVR::State::StateBlockTracker::Recording())",
     "if (!device || false)"),
    ("recording stamp", "R29Effect.recordingGeneration = recordingGenerationBefore;",
     "R29Effect.recordingGeneration = 0;"),
    ("apply stamp", "R29Effect.applyGeneration = applyGenerationBefore;",
     "R29Effect.applyGeneration = 0;"),
    ("record torn read", "StateBlockTracker::RecordingGeneration() !=\n                    recordingGenerationBefore",
     "StateBlockTracker::RecordingGeneration() ==\n                    recordingGenerationBefore"),
    ("recording setter", "if (OutRunVR::State::StateBlockTracker::Recording())\n            {\n                R29Effect.valid = false;\n                return hr;",
     "if (false)\n            {\n                R29Effect.valid = false;\n                return hr;"),
    ("stale setter", "R29Effect.recordingGeneration !=\n                     OutRunVR::State::StateBlockTracker::RecordingGeneration()",
     "R29Effect.recordingGeneration ==\n                     OutRunVR::State::StateBlockTracker::RecordingGeneration()"),
    ("telemetry", "if (!R29EffectCacheCurrent())\n            return false;",
     "if (false)\n            return false;"),
    ("depth surface gate", "if (!device || !TrackedDepthStencil)\n            return false;",
     "if (false)\n            return false;"),
    ("depth cache trust", "if (R29EffectCacheCurrent())\n        {\n            return R29Effect.zEnable",
     "if (false)\n        {\n            return R29Effect.zEnable"),
    ("depth enabled predicate", "return R29Effect.zEnable != D3DZB_FALSE &&\n                R29Effect.zWrite != FALSE;",
     "return R29Effect.zEnable == D3DZB_FALSE &&\n                R29Effect.zWrite != FALSE;"),
    ("depth write predicate", "return R29Effect.zEnable != D3DZB_FALSE &&\n                R29Effect.zWrite != FALSE;",
     "return R29Effect.zEnable != D3DZB_FALSE &&\n                R29Effect.zWrite == FALSE;"),
    ("depth positive cache getter bypass", "return R29Effect.zEnable != D3DZB_FALSE &&\n                R29Effect.zWrite != FALSE;",
     "return LeftDrawMayWriteDepth(device);"),
    ("depth conservative fallback", "return LeftDrawMayWriteDepth(device);",
     "return false;"),
    ("direct stereo depth owner", "if (R29OwnerLeftDrawMayWriteDepth(device) ||",
     "if (LeftDrawMayWriteDepth(device) ||"),
    ("depth or stencil serial safety",
     "if (R29OwnerLeftDrawMayWriteDepth(device) ||",
     "if (R29OwnerLeftDrawMayWriteDepth(device) &&"),
]
for name, before, after in mutations:
    if src.count(before) != 1:
        errors.append("bad mutation fixture: " + name)
    elif contract(src.replace(before, after, 1)):
        errors.append("negative escaped: " + name)
if errors:
    print("FAIL " + ", ".join(errors), file=sys.stderr)
    sys.exit(1)
print(f"PASS R29 single-Present effect cache, positive/negative depth-write fastpath, and {len(mutations)} negative mutations")
