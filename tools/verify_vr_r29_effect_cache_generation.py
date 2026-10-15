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
    warm_owner = body(s, "bool R29OwnerTryGetEffectTelemetrySnapshot(")
    depth_owner = body(s, "bool R29OwnerLeftDrawMayWriteDepth(")
    stencil_owner = body(s, "bool R29OwnerLeftDrawMayWriteStencil(")
    effect_state = body(s, "struct R29EffectState")
    policy_refresh = body(s, "void R29RefreshFragilePolicy() noexcept")
    fragile_draw = body(s, "bool R29FragileEffectCached(")
    stereo = body(s, "HRESULT R29DirectTwoEye(")
    world = body(s, "HRESULT R29GuardStableDraw(")
    return all((
        # CPU hot path: once a reliable live six-field snapshot has been
        # synchronized, derived alpha/depth/cull stereo policy is memoized
        # until a tracked policy setter changes it. A StateBlock generation
        # mismatch still forces a fresh live read and policy recomputation.
        "bool fragileWorld = true;" in effect_state,
        "OutRunVR::PassPolicy::ClassifyEffectStereo(" in policy_refresh,
        "R29Effect.alphaBlend != FALSE," in policy_refresh,
        "R29Effect.alphaTest != FALSE," in policy_refresh,
        "R29Effect.zWrite != FALSE," in policy_refresh,
        "R29Effect.zEnable != D3DZB_FALSE," in policy_refresh,
        "R29Effect.cullMode == D3DCULL_NONE" in policy_refresh,
        "R29Effect.fragileWorld =" in policy_refresh,
        "!OutRunVR::PassPolicy::AllowsEffectWorldStereo(policy)" in policy_refresh,
        "R29Effect.stencilEnable = stencilEnable;\n            R29RefreshFragilePolicy();" in sync,
        "if (state != D3DRS_STENCILENABLE)\n                    R29RefreshFragilePolicy();" in setter,
        "fragile = R29Effect.fragileWorld;" in fragile_draw,
        "ClassifyEffectStereo(" not in fragile_draw,
        fragile_draw.find("if (!R29SyncEffectState(device))") <
            fragile_draw.find("fragile = R29Effect.fragileWorld;"),
        "StateBlockTracker::Reliable()" in cache,
        "StateBlockTracker::Recording()" in cache,
        "R29Effect.applyGeneration !=" in cache,
        "R29Effect.recordingGeneration !=" in cache,
        "StateBlockTracker::ApplyGeneration()" in cache,
        "StateBlockTracker::RecordingGeneration()" in cache,
        "R29Effect.presentEpoch == PresentEpoch" in cache,
        "TopLevelDrawSerial() >= R29Effect.drawSerial" in cache,
        "TopLevelDrawSerial() - R29Effect.drawSerial < 64" not in cache,
        # Hot world-effect draws issue at most one expensive R13 live
        # snapshot, while exact HUD/post-process ownership always vetoes
        # even a generic R27 world classification.
        "const bool forceZeroDisparity =" in world,
        "OutRunVR::GameSemantic::ForceZeroDisparity(semanticScope);" in world,
        "bool worldGateChecked = false;" in world,
        "else if (OutRunVR::GameSemantic::CorroboratesWorld(semanticScope))" in world,
        "worldGateChecked = true;" in world,
        "if (R27ShouldBypassLegacyZeroDisparity(device))" in world,
        "if (fragile && !forceZeroDisparity && !worldGateChecked &&" in world,
        world.count("R27ShouldBypassLegacyZeroDisparity(device)") == 2,
        # Destructive source mutations remove these anchors; find() must
        # return -1 rather than raising ValueError, so contract() fails cleanly.
        world.find("bool worldGateChecked = false;") <
            world.find("worldGateChecked = true;") <
            world.find("if (fragile && !forceZeroDisparity && !worldGateChecked &&"),
        "R29DirectTwoEye(device" in world,
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
        # The R30/R33 classification-only consumer fills the state once
        # before depth-off effects, but only under a trustworthy generation.
        "if (!TryGetEffectTelemetrySnapshot(lower))" in warm_owner,
        "!OutRunVR::State::StateBlockTracker::Reliable()" in warm_owner,
        "OutRunVR::State::StateBlockTracker::Recording()" in warm_owner,
        "InternalStereoPass" in warm_owner,
        "IDirect3DDevice9* const device = R29OwnerGameDevice();" in warm_owner,
        "!R29SyncEffectState(device)" in warm_owner,
        "!TryGetEffectTelemetrySnapshot(lower)" in warm_owner,
        sync.find("recordingGenerationBefore") < sync.find("device->GetRenderState(")
            < sync.find("StateBlockTracker::RecordingGeneration() !="),
        setter.find("StateBlockTracker::Recording()") <
            setter.find("case D3DRS_ALPHABLENDENABLE:\n                R29Effect.alphaBlend = value;"),
        "if (false)" not in cache and "if (false)" not in sync,
        "if (false)" not in setter and "if (false)" not in telemetry,
        "if (!device || !TrackedDepthStencil)" in depth_owner,
        "if (R29EffectCacheCurrent())" in depth_owner,
        "return R29Effect.zEnable != D3DZB_FALSE &&" in depth_owner,
        "R29Effect.zWrite != FALSE;" in depth_owner,
        "return false;" in depth_owner,
        "return LeftDrawMayWriteDepth(device);" in depth_owner,
        "DWORD stencilEnable = FALSE;" in effect_state,
        "D3DRS_STENCILENABLE, &stencilEnable" in sync,
        "R29Effect.stencilEnable = stencilEnable;" in sync,
        "case D3DRS_STENCILENABLE:\n                R29Effect.stencilEnable = value;" in setter,
        "R29Effect.stencilEnable = value;" in setter,
        "if (!device || !TrackedDepthStencil)" in stencil_owner,
        "if (R29EffectCacheCurrent() && R29Effect.stencilEnable == FALSE)" in stencil_owner,
        "return false;" in stencil_owner,
        "return LeftDrawMayWriteStencil(device);" in stencil_owner,
        stencil_owner.find("R29EffectCacheCurrent()") < stencil_owner.find("return LeftDrawMayWriteStencil(device);"),
        "R29OwnerLeftDrawMayWriteStencil(device)" in stereo,
        depth_owner.find("if (!device || !TrackedDepthStencil)") <
            depth_owner.find("if (R29EffectCacheCurrent())") <
            depth_owner.find("return R29Effect.zEnable != D3DZB_FALSE &&") <
            depth_owner.find("return LeftDrawMayWriteDepth(device);"),
        "R29OwnerLeftDrawMayWriteDepth(device)" in stereo,
        "R29OwnerLeftDrawMayWriteStencil(device)" in stereo,
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
    ("recording setter", "if (OutRunVR::State::StateBlockTracker::Recording())\n            {\n                R29Effect.valid = false;\n                R29StencilWrite.valid = false;\n                return hr;",
     "if (false)\n            {\n                R29Effect.valid = false;\n                R29StencilWrite.valid = false;\n                return hr;"),
    ("stale setter", "R29Effect.recordingGeneration !=\n                     OutRunVR::State::StateBlockTracker::RecordingGeneration()",
     "R29Effect.recordingGeneration ==\n                     OutRunVR::State::StateBlockTracker::RecordingGeneration()"),
    ("telemetry", "if (!R29EffectCacheCurrent())\n            return false;",
     "if (false)\n            return false;"),
    ("depth surface gate",
     "if (!device || !TrackedDepthStencil)\n            return false;\n        if (R29EffectCacheCurrent())",
     "if (false)\n            return false;\n        if (R29EffectCacheCurrent())"),
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
    ("stencil getter", "D3DRS_STENCILENABLE, &stencilEnable", "D3DRS_CULLMODE, &stencilEnable"),
    ("stencil synced value", "R29Effect.stencilEnable = stencilEnable;", "R29Effect.stencilEnable = FALSE;"),
    ("stencil setter",
     "case D3DRS_STENCILENABLE:\n                R29Effect.stencilEnable = value;",
     "case D3DRS_SCISSORTESTENABLE:\n                R29Effect.stencilEnable = value;"),
    ("stencil setter value", "R29Effect.stencilEnable = value;", "R29Effect.stencilEnable = FALSE;"),
    ("stencil cached only if reliable",
     "if (R29EffectCacheCurrent() && R29Effect.stencilEnable == FALSE)",
     "if (R29Effect.stencilEnable == FALSE)"),
    ("stencil disabled predicate",
     "R29Effect.stencilEnable == FALSE)", "R29Effect.stencilEnable != FALSE)"),
    ("stencil conservative fallback",
     "return LeftDrawMayWriteStencil(device);", "return false;"),
    ("stencil no depth",
     "if (!device || !TrackedDepthStencil)\n            return false;\n        // Only a reliable",
     "if (false)\n            return false;\n        // Only a reliable"),
    ("stencil direct stereo owner",
     "R29OwnerLeftDrawMayWriteStencil(device))", "LeftDrawMayWriteStencil(device))"),
]
# Derived-policy caching must fail closed for stale/missing updates, and the
# stereo classifier itself must stay identical to the original draw policy.
mutations += [
    ("policy cache flag", "bool fragileWorld = true;", "bool fragileWorld = false;"),
    ("live resync policy", "R29Effect.stencilEnable = stencilEnable;\n            R29RefreshFragilePolicy();",
     "R29Effect.stencilEnable = stencilEnable;"),
    ("setter policy refresh", "if (state != D3DRS_STENCILENABLE)\n                    R29RefreshFragilePolicy();",
     "if (false)\n                    R29RefreshFragilePolicy();"),
    ("draw cached value", "fragile = R29Effect.fragileWorld;", "fragile = true;"),
    ("classify alpha state", "R29Effect.alphaBlend != FALSE,", "R29Effect.alphaBlend == FALSE,"),
    ("classify alpha test", "R29Effect.alphaTest != FALSE,", "R29Effect.alphaTest == FALSE,"),
    ("classify zwrite", "R29Effect.zWrite != FALSE,", "R29Effect.zWrite == FALSE,"),
    ("classify zenable", "R29Effect.zEnable != D3DZB_FALSE,", "R29Effect.zEnable == D3DZB_FALSE,"),
    ("classify cullmode", "R29Effect.cullMode == D3DCULL_NONE", "R29Effect.cullMode != D3DCULL_NONE"),
    ("classify allow", "!OutRunVR::PassPolicy::AllowsEffectWorldStereo(policy)",
     "OutRunVR::PassPolicy::AllowsEffectWorldStereo(policy)"),
]
# The hotpath's exact guards must reject disabled HUD vetoes, lost
# one-probe fencing, and reintroduced unconditional duplicated reads.
mutations += [
    ("R29 forced post-process veto",
     "if (fragile && !forceZeroDisparity && !worldGateChecked &&",
     "if (fragile && !worldGateChecked &&"),
    ("R29 duplicate-world probe",
     "if (fragile && !forceZeroDisparity && !worldGateChecked &&",
     "if (fragile && !forceZeroDisparity &&"),
    ("R29 missing probe stamp",
     "worldGateChecked = true;", "worldGateChecked = false;"),
    ("R29 missing semantic gate",
     "else if (OutRunVR::GameSemantic::CorroboratesWorld(semanticScope))",
     "else if (true)"),
    ("R29 missing exact semantic veto",
     "OutRunVR::GameSemantic::ForceZeroDisparity(semanticScope);",
     "false;"),
]
# Model each semantic/effect branch: corroborated world must never query
# twice; explicit ForceZero beats generic world evidence; untagged fragile
# candidates are probed once and may graduate only on positive R27 proof.
for fragile_initial in (False, True):
    for forced in (False, True):
        for corroborated in (False, True):
            for world_proof in (False, True):
                fragile = fragile_initial
                probes = 0
                checked = False
                if forced:
                    fragile = True
                elif corroborated:
                    checked = True
                    probes += 1
                    if world_proof:
                        fragile = False
                if fragile and not forced and not checked:
                    probes += 1
                    if world_proof:
                        fragile = False
                assert probes <= 1
                assert not forced or (fragile and probes == 0)
                assert not (corroborated and not forced) or probes == 1

for name, before, after in mutations:
    if src.count(before) != 1:
        errors.append("bad mutation fixture: " + name)
    elif contract(src.replace(before, after, 1)):
        errors.append("negative escaped: " + name)
if errors:
    print("FAIL " + ", ".join(errors), file=sys.stderr)
    sys.exit(1)
print(f"PASS R29 memoized alpha/depth/cull stereo policy, generation-fenced effect cache, depth/stencil safety, and {len(mutations)} negative mutations plus 16 semantic/effect branch combinations")
