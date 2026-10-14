#!/usr/bin/env python3
"""Changed-area +TIME D3DX semantic-batch boundary contract and mutation guards.

This verifies exact upstream ownership and fail-closed hook wiring; it does
not claim Quest3/VDXR visual verification or simulate real D3D execution.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/hooks_uiscaling.cpp"
SEMANTICS = ROOT / "src/vr/game/render_semantics.hpp"


def check(code: str, header: str) -> list[str]:
    errors: list[str] = []
    def need(ok: bool, name: str) -> None:
        if not ok:
            errors.append(name)
    start = code.find("class VRProjectedD3DXSpriteIsolationR64 : public Hook")
    end = code.find("// VR semantic bridge for the game's canonical queued 2D renderer.", start)
    need(start >= 0 and end > start, "R64 exact sprite-hook owner missing")
    if start < 0 or end < start:
        return errors
    hook = code[start:end]
    queue = code[end:]
    source = code[:start]
    need("StageExtensionSpraniCalls[]" in source and
         "0x9898E, 0x98A36, 0x98AC6" in source and
         "StageExtensionPrintCalls[]" in source and
         "0x989AD, 0x98A10, 0x98A89" in source,
         "six original source edges are not preserved")
    stage_enter = source[source.find("static void StageExtensionEnter("):
                         source.find("static void StageExtensionLeave(")]
    need("FlushD3DXBeforeDirectStageSource();" in stage_enter and
         stage_enter.find("FlushD3DXBeforeDirectStageSource();") <
         stage_enter.find("StageExtensionDirectDrawOwner.emplace(") and
         "static void FlushD3DXBeforeDirectStageSource() noexcept;" in source,
         "direct +TIME must drain proven prior D3DX batch before new ScreenHud owner")
    stage_leave = source[source.find("static void StageExtensionLeave("):
                         source.find("inline static SafetyHookMid ResultTextEnterHooks")]
    need("static void FlushD3DXAtDirectStageSourceExit() noexcept;" in source and
         "FlushD3DXAtDirectStageSourceExit();" in stage_leave and
         stage_leave.find("TagAppendedNodes(StageExtensionBefore") <
         stage_leave.find("FlushD3DXAtDirectStageSourceExit();") <
         stage_leave.find("StageExtensionDirectDrawOwner.reset();"),
         "direct +TIME source exit must submit owned batch before RAII restores prior owner")
    need("ScopedExactProducerSemantic" in source and
         "ProducerToken::StageExtensionTime" in source and
         "TagAppendedNodes(StageExtensionBefore" in source,
         "immediate print and queued sprite producer owners missing")
    for method, number in (("BeginDest", 8), ("DrawDest", 9),
                           ("FlushDest", 10), ("EndDest", 11)):
        need(f"static HRESULT __stdcall {method}(" in hook,
             f"{method} hook callback missing")
        need(f"vtable[{number}]" in hook,
             f"{method} vtable slot missing")
    need("BatchActive = SUCCEEDED(hr)" in hook and
         "BatchActive = false" in hook and
         "ForgetBatch();" in hook,
         "Begin/End/failed-Flush state invalidation missing")
    lifecycle_start = hook.find("static void InvalidateForDeviceLifecycle(")
    lifecycle_end = hook.find("static bool FlushTracked(", lifecycle_start)
    lifecycle = hook[lifecycle_start:lifecycle_end] if (
        lifecycle_start >= 0 and lifecycle_end > lifecycle_start) else ""
    need("if (!wasExactGameSprite)" in lifecycle and
         "BatchActive = false;" in lifecycle and
         "StageBoundaryReady = false;" in lifecycle and
         "ForgetBatch();" in lifecycle and
         "TrackedSprite = nullptr;" in lifecycle,
         "only exact D3DX sprite may invalidate stale device-loss batch")
    for method, slot in (("LostDevice", 12), ("ResetDevice", 13)):
        need(f"static HRESULT __stdcall {method}Dest(void* self)" in lifecycle and
             (f"const bool wasExactGameSprite = IsExactSprite(self);\n"
              f"        const HRESULT hr = {method}_hk.stdcall<HRESULT>(self);\n"
              "        InvalidateForDeviceLifecycle(wasExactGameSprite);\n"
              "        return hr;") in lifecycle and
             lifecycle.count("InvalidateForDeviceLifecycle(wasExactGameSprite);") == 2 and
             f"vtable[{slot}]" in hook and
             f"reinterpret_cast<void*>(&{method}Dest)" in hook and
             f"{method}_hk.enable().has_value()" in hook and
             f"{method}_hk = {{}};" in hook,
             f"{method} exact D3DX lifecycle trampoline missing")
    need("LostDevice_hk && ResetDevice_hk" in hook and
         "vtable[12] && vtable[13]" in hook,
         "batch hook installation must include both reset edges")
    direct_begin = hook.find("static void BeforeDirectStageSource() noexcept")
    direct_end = hook.find("static void BeforeQueueNode(", direct_begin)
    direct_stage = hook[direct_begin:direct_end] if 0 <= direct_begin < direct_end else ""
    # Match the exact direct producer boundary, not the separate queued path.
    # A global PendingScope/Producer substring can accidentally survive when
    # the direct source starts using ProducerToken::None (regression 00861).
    need("false, true, PendingHomogeneous," in direct_stage and
         "PendingScope, PendingProducer," in direct_stage and
         "EffectiveScope(), CurrentRenderProducerToken()" in direct_stage and
         "||" in direct_stage and "!FlushTracked(sprite)" in direct_stage and
         "StageBoundaryReady = false;" in direct_stage and
         "StageFlushes.fetch_add" in direct_stage and
         "StageFallbacks.fetch_add" in direct_stage and
         "static void FlushD3DXBeforeDirectStageSource() noexcept" in code[end-1800:] and
         "VRProjectedD3DXSpriteIsolationR64::BeforeDirectStageSource();" in code,
         "direct +TIME must split only a proven homogeneous batch under its exact outgoing scope and producer")
    need("static void AfterDirectStageSource() noexcept" in hook and
         "CanFlushD3DXDirectStageAtExit(" in hook and
         "PendingDraws, PendingHomogeneous, PendingScope, PendingProducer," in hook and
         "EffectiveScope(), CurrentRenderProducerToken()" in hook and
         "if (FlushTracked(sprite))" in hook and
         "VRProjectedD3DXSpriteIsolationR64::AfterDirectStageSource();" in code,
         "source exit must flush only proven homogeneous live +TIME D3DX batch")
    need("pendingDraws != 0 && homogeneous" in header and
         "pendingProducer == ProducerToken::StageExtensionTime" in header and
         "currentScope == pendingScope" in header and
         "currentProducer == pendingProducer" in header,
         "direct source-exit predicate may not promote unrelated batches")
    need("PendingHomogeneous = false" in hook and
         "CanFlushD3DXPreQueueStageBatch(" in hook and
         "!QueueRenderActive()" in hook,
         "mixed/unknown owner fail-closed fallback missing")
    need("CanFlushD3DXPreQueueStageBatch(" in hook and
         "QueueRenderActive(), enteringStage, PendingHomogeneous" in hook and
         "PendingScope, PendingProducer" in hook and
         "EffectiveScope(), CurrentRenderProducerToken()" in hook,
         "first +TIME queue old-direct-source boundary not wired")
    need("homogeneous && (wasQueueActive || enteringExactStage)" in header and
         "pendingScope == outgoingScope" in header and
         "pendingProducer == outgoingProducer" in header,
         "pre-queue predicate must reject mixed or stale source")
    need("PeekSpriteNodeScope(nextNode, RenderScope::None, &nextProducer)" in hook and
         "StageOwner(nextScope, nextProducer)" in hook,
         "next node must have exact +TIME tag before promotion")
    need("GoalTimeHelperCallA = 0xBEA5A" in source and
         "GoalTimeHelperCallB = 0xBEA5F" in source and
         "ProducerToken::GoalTime020" in source and
         "ProducerToken::GoalTime150" in source and
         "ProducerToken::ResultProgress" in source,
         "finite GOAL production source calls missing")
    need("GoalOwner(nextScope, nextProducer)" in hook and
         "GoalOwner(EffectiveScope(), CurrentRenderProducerToken())" in hook and
         "nextProducer != CurrentRenderProducerToken()" in hook and
         "StageBoundaryReady = enteringStage || enteringGoal" in hook,
         "GOAL queue enter/leave and two-helper switching must isolate old batch")
    need("GoalOwner(scope, source) && PendingHomogeneous" in hook and
         "(exactStage || exactGoal)" in hook and
         "GoalFlushes" in hook and "GoalFallbacks" in hook,
         "GOAL direct and deferred GPU submission requires exact source proof")
    for token in ("GoalTime020", "GoalTime150", "ResultProgress"):
        need(f"source == ProducerToken::{token}" in hook,
             f"GOAL token {token} missing")
    need("StageOwner(scope, source) && PendingHomogeneous" in hook and
         "queuedStageIsolated || directStageIsolated" in hook and
         "FlushTracked(self)" in hook,
         "+TIME submission must flush only under proven ScreenHud producer")
    need("StageBoundaryReady = false" in hook and
         "StageFallbacks.fetch_add" in hook,
         "failed preboundary should never promote an unknown batch")
    need("queuedSource == ProducerToken::RankMarkerSprani" in hook and
         "queuedSource == ProducerToken::RankMarkerClipSprite" in hook and
         "queuedSource == ProducerToken::DispRankFirst" in hook and
         "queuedSource == ProducerToken::DispRankClipSprite" in hook,
         "HMD-proven R64 rank ownership must be retained")
    need("VRProjectedD3DXSpriteIsolationR64::BeforeQueueNode(node);" in queue and
         "VRProjectedD3DXSpriteIsolationR64::BeforeQueueEnd();" in queue,
         "stage batch boundaries not connected to canonical queue")
    node = queue.find("VRProjectedD3DXSpriteIsolationR64::BeforeQueueNode(node);")
    select = queue.find("OutRunVR::GameSemantic::SelectSpriteQueueNode(node);")
    leave = queue.find("VRProjectedD3DXSpriteIsolationR64::BeforeQueueEnd();")
    finish = queue.find("OutRunVR::GameSemantic::EndSpriteQueueRender();")
    need(0 <= node < select and 0 <= leave < finish,
         "prior producer must flush BEFORE queue ownership is replaced")
    need("QueueRenderActive() && StageBoundaryReady" in hook and
         "!QueueRenderActive() && PendingDraws == 1u" in hook and
         "if (FlushTracked(self))" in hook,
         "post-Draw +TIME flush not constrained to queue-owned proof")
    return errors


def main() -> int:
    code = SOURCE.read_text(encoding="utf-8")
    header = SEMANTICS.read_text(encoding="utf-8")
    errors = check(code, header)
    if errors:
        print("DX9Ex +TIME D3DX FAIL: " + "; ".join(errors))
        return 1
    mutations = {
        "missing-direct-exit-flush":
            code.replace("        FlushD3DXAtDirectStageSourceExit();",
                         "        // delayed source batch ignored", 1),
        "direct-exit-after-restore":
            code.replace(
                "        FlushD3DXAtDirectStageSourceExit();\n"
                "        // Always restore",
                "        // Always restore", 1),
        "missing-direct-exit-owner":
            code.replace(
                "VRProjectedD3DXSpriteIsolationR64::AfterDirectStageSource();",
                "// no source exit hook", 1),
        "lost-direct-old-batch-isolation":
            code.replace("            FlushD3DXBeforeDirectStageSource();",
                         "            // direct GPU submission not isolated", 1),
        "premature-direct-owner":
            code.replace(
                "            FlushD3DXBeforeDirectStageSource();\n"
                "            StageExtensionDirectDrawOwner.emplace(",
                "            StageExtensionDirectDrawOwner.emplace(", 1),
        "direct-mixed-batch-promoted":
            code.replace("false, true, PendingHomogeneous,",
                         "false, true, true,", 1),
        "wrong-before-after-node-order":
            code.replace(
                "VRProjectedD3DXSpriteIsolationR64::BeforeQueueNode(node);\n"
                "\t\tOutRunVR::GameSemantic::SelectSpriteQueueNode(node);",
                "OutRunVR::GameSemantic::SelectSpriteQueueNode(node);\n"
                "\t\tVRProjectedD3DXSpriteIsolationR64::BeforeQueueNode(node);",
                1),
        "stale-shared-batch":
            code.replace("PendingHomogeneous = false;", "PendingHomogeneous = true;", 1),
        "missing-old-owner-proof":
            code.replace(
                "false, true, PendingHomogeneous,\n"
                "                PendingScope, PendingProducer,",
                "false, true, PendingHomogeneous,\n"
                "                PendingScope, ProducerToken::None,", 1),
        "unproven-direct-batch":
            code.replace("!QueueRenderActive() && PendingDraws == 1u",
                         "false", 1),
        "missing-end-boundary":
            code.replace("VRProjectedD3DXSpriteIsolationR64::BeforeQueueEnd();",
                         "// no end flush", 1),
        "lost-rank-exact-source":
            code.replace("queuedSource == ProducerToken::DispRankClipSprite",
                         "queuedSource == ProducerToken::None", 1),
        "goal-batch-source-lost":
            code.replace("GoalOwner(scope, source) && PendingHomogeneous",
                         "false && PendingHomogeneous", 1),
        "goal-helper-boundary-lost":
            code.replace("nextProducer != CurrentRenderProducerToken()",
                         "false", 1),
        "goal-queue-admission-lost":
            code.replace("StageBoundaryReady = enteringStage || enteringGoal",
                         "StageBoundaryReady = enteringStage;", 1),
        "goal-progress-owner-lost":
            code.replace("source == ProducerToken::ResultProgress",
                         "source == ProducerToken::None", 1),
        "lost-device-invalidates-no-batch":
            code.replace(
                "const HRESULT hr = LostDevice_hk.stdcall<HRESULT>(self);\n"
                "        InvalidateForDeviceLifecycle(wasExactGameSprite);",
                "const HRESULT hr = LostDevice_hk.stdcall<HRESULT>(self);", 1),
        "reset-device-invalidates-no-batch":
            code.replace(
                "const HRESULT hr = ResetDevice_hk.stdcall<HRESULT>(self);\n"
                "        InvalidateForDeviceLifecycle(wasExactGameSprite);",
                "const HRESULT hr = ResetDevice_hk.stdcall<HRESULT>(self);", 1),
        "reset-must-not-promote-stale-owner":
            code.replace("        TrackedSprite = nullptr;",
                         "        TrackedSprite = self;", 1),
        "reset-must-not-include-foreign-sprite":
            code.replace("        if (!wasExactGameSprite)\n            return;",
                         "        if (false)\n            return;", 1),
        "reset-hook-absent":
            code.replace("ResetDevice_hk.enable().has_value()",
                         "false", 1),
        "lost-must-propagate-original-error":
            code.replace(
                "InvalidateForDeviceLifecycle(wasExactGameSprite);\n        return hr;\n"
                "    }\n\n    static HRESULT __stdcall ResetDeviceDest",
                "InvalidateForDeviceLifecycle(wasExactGameSprite);\n        return D3D_OK;\n"
                "    }\n\n    static HRESULT __stdcall ResetDeviceDest", 1),
        "reset-must-propagate-original-error":
            code.replace(
                "const HRESULT hr = ResetDevice_hk.stdcall<HRESULT>(self);\n"
                "        InvalidateForDeviceLifecycle(wasExactGameSprite);\n        return hr;",
                "const HRESULT hr = ResetDevice_hk.stdcall<HRESULT>(self);\n"
                "        InvalidateForDeviceLifecycle(wasExactGameSprite);\n        return D3D_OK;", 1),
        "lost-must-capture-exact-before-original":
            code.replace(
                "const bool wasExactGameSprite = IsExactSprite(self);\n"
                "        const HRESULT hr = LostDevice_hk.stdcall<HRESULT>(self);",
                "const HRESULT hr = LostDevice_hk.stdcall<HRESULT>(self);\n"
                "        const bool wasExactGameSprite = IsExactSprite(self);", 1),
        "reset-must-capture-exact-before-original":
            code.replace(
                "const bool wasExactGameSprite = IsExactSprite(self);\n"
                "        const HRESULT hr = ResetDevice_hk.stdcall<HRESULT>(self);",
                "const HRESULT hr = ResetDevice_hk.stdcall<HRESULT>(self);\n"
                "        const bool wasExactGameSprite = IsExactSprite(self);", 1),
    }
    for label, mutated in mutations.items():
        if mutated == code or not check(mutated, header):
            print("DX9Ex +TIME D3DX FAIL: mutation not detected:", label)
            return 1
    for label, altered in {
        "exit-permit-mixed": header.replace(
            "pendingDraws != 0 && homogeneous", "pendingDraws != 0 && true", 1),
        "exit-permit-foreign": header.replace(
            "pendingProducer == ProducerToken::StageExtensionTime",
            "pendingProducer != ProducerToken::StageExtensionTime", 1),
        "exit-permit-owner-swap": header.replace(
            "currentProducer == pendingProducer", "true", 1),
        "lost-first-stage": header.replace(
            "(wasQueueActive || enteringExactStage)", "wasQueueActive", 1),
        "permit-any-first-node": header.replace(
            "(wasQueueActive || enteringExactStage)", "true", 1),
        "permit-mixed": header.replace(
            "homogeneous && (wasQueueActive", "true && (wasQueueActive", 1),
        "permit-wrong-producer": header.replace(
            "pendingProducer == outgoingProducer",
            "pendingProducer != outgoingProducer", 1),
    }.items():
        if altered == header or not check(code, altered):
            print("DX9Ex +TIME D3DX FAIL: header mutation", label)
            return 1
    print("DX9Ex +TIME/GOAL D3DX first-queue source and 14 negative regressions PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
