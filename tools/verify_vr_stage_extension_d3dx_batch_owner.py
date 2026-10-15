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
    # Check each predicate within its owning function. A second GOAL
    # predicate must not hide a destructive mutation of the +TIME one.
    def predicate(name: str) -> str:
        begin = header.find("inline constexpr bool " + name + "(")
        finish = header.find("    static_assert(", begin)
        return header[begin:finish] if begin >= 0 and finish > begin else ""
    stage_predicate = predicate("CanFlushD3DXDirectStageAtExit")
    goal_predicate = predicate("CanFlushD3DXDirectGoalAtExit")
    queued_stage_predicate = predicate("CanArmD3DXQueueStageAfterDraw")
    queued_goal_predicate = predicate("CanArmD3DXQueueGoalAfterDraw")
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
    # A successful explicit native D3DX Flush terminates the preceding
    # queue's GPU submission lifetime. It must reset the boundary as well
    # as PendingDraws so that no next producer inherits that old permission.
    native_flush_begin = hook.find("static HRESULT __stdcall FlushDest(")
    native_flush_end = hook.find("static HRESULT __stdcall EndDest(", native_flush_begin)
    native_flush = hook[native_flush_begin:native_flush_end] if (
        native_flush_begin >= 0 and native_flush_end > native_flush_begin) else ""
    need("if (SUCCEEDED(hr))\n            {" in native_flush and
         "ForgetBatch();\n                StageBoundaryReady = false;" in native_flush and
         native_flush.find("ForgetBatch();") <
         native_flush.find("StageBoundaryReady = false;") and
         "BatchActive = false;" in native_flush and
         "return hr;" in native_flush,
         "successful native D3DX Flush must retire old +TIME/GOAL queue boundary")
    # Failure-injection contract for the original ID3DXSprite lifecycle:
    # a rejected nested Begin does NOT terminate the previous active batch.
    # A failed Draw has unknown internal submission progress and must revoke
    # its +TIME/GOAL ownership rather than presenting stale state at Flush/End.
    begin_pos = hook.find("static HRESULT __stdcall BeginDest(")
    flush_pos = hook.find("static HRESULT __stdcall FlushDest(", begin_pos)
    begin_path = hook[begin_pos:flush_pos] if begin_pos >= 0 else ""
    draw_pos = hook.find("static HRESULT __stdcall DrawDest(")
    install_pos = hook.find("static DWORD WINAPI InstallThread(", draw_pos)
    draw_path = hook[draw_pos:install_pos] if draw_pos >= 0 else ""
    need("const bool existingBatch =" in begin_path and
         "BatchActive && self == TrackedSprite && IsExactSprite(self)" in begin_path and
         "if (FAILED(hr) && existingBatch)\n                return hr;" in begin_path and
         begin_path.find("if (FAILED(hr) && existingBatch)") <
         begin_path.find("ForgetBatch();"),
         "failed nested D3DX Begin must keep existing exact sprite provenance")
    failed_start = draw_path.find("if (FAILED(hr))")
    failed_end = draw_path.find("return hr;", failed_start)
    failed_draw = draw_path[failed_start:failed_end] if (
        0 <= failed_start < failed_end) else ""
    need("if (self && self == TrackedSprite)" in failed_draw and
         "BatchActive = false;" in failed_draw and
         "StageBoundaryReady = false;" in failed_draw and
         "ForgetBatch();" in failed_draw and
         failed_end < draw_path.find("const auto scope = EffectiveScope();"),
         "failed D3DX Draw must invalidate untrusted +TIME/GOAL batch ownership")
    # Inspect the actual HRESULT-accepted, tracked Draw's mixed-owner branch.
    # A matching assignment in lifecycle/queue/failure handling is not proof
    # that the GPU batch stops being homogeneous when its producer changes.
    owner_switch = draw_path.find(
        "else if (PendingScope != scope || PendingProducer != source)")
    next_draw_count = draw_path.find("if (PendingDraws != ~0u)", owner_switch)
    mixed_owner = draw_path[owner_switch:next_draw_count] if (
        0 <= owner_switch < next_draw_count) else ""
    need("PendingHomogeneous = false;" in mixed_owner,
         "successful D3DX Draw must quarantine mixed scope/producer batches")
    flush_start = hook.find("static HRESULT __stdcall FlushDest(")
    flush_end = hook.find("static HRESULT __stdcall EndDest(", flush_start)
    explicit_flush = hook[flush_start:flush_end] if (
        0 <= flush_start < flush_end) else ""
    need("if (self == TrackedSprite)" in explicit_flush and
         "if (SUCCEEDED(hr))" in explicit_flush and
         "ForgetBatch();\n                StageBoundaryReady = false;" in explicit_flush and
         "BatchActive = false;" in explicit_flush and
         "return hr;" in explicit_flush,
         "explicit native Flush must discard consumed +TIME/GOAL ownership only on success")
    # The tracked object can outlive the mutable 0x55B218 global sprite.
    # Verify BOTH the old owner reset path and live-sprite Flush identity.
    lifetime_start = code.find("namespace DX9ExD3DXSpriteLifetime")
    lifetime_guard = code[lifetime_start:start] if 0 <= lifetime_start < start else ""
    need("constexpr bool CanFlush(" in lifetime_guard and
         "candidate != nullptr && candidate == tracked &&" in lifetime_guard and
         "candidate == live;" in lifetime_guard and
         "static_assert(CanFlush(&OldSprite, &OldSprite, &OldSprite));" in lifetime_guard and
         "static_assert(!CanFlush(&OldSprite, &OldSprite, &NewSprite));" in lifetime_guard and
         "static_assert(!CanFlush(&OldSprite, nullptr, &OldSprite));" in lifetime_guard,
         "Flush requires non-null same tracked and live D3DXSprite object")
    need("constexpr bool OwnsLifecycle(" in lifetime_guard and
         "callback != nullptr &&" in lifetime_guard and
         "(callback == tracked || callback == live);" in lifetime_guard and
         "static_assert(OwnsLifecycle(&OldSprite, &OldSprite, nullptr));" in lifetime_guard and
         "static_assert(!OwnsLifecycle(&ForeignSprite, &OldSprite, &NewSprite));" in lifetime_guard,
         "device loss must invalidate the tracked old sprite or current live sprite, not foreign sprites")
    lifecycle_start = hook.find("static void InvalidateForDeviceLifecycle(")
    lifecycle_end = hook.find("static bool FlushTracked(", lifecycle_start)
    lifecycle = hook[lifecycle_start:lifecycle_end] if (
        lifecycle_start >= 0 and lifecycle_end > lifecycle_start) else ""
    need("if (!wasTrackedOrExactGameSprite)" in lifecycle and
         "BatchActive = false;" in lifecycle and
         "StageBoundaryReady = false;" in lifecycle and
         "ForgetBatch();" in lifecycle and
         "TrackedSprite = nullptr;" in lifecycle,
         "tracked/live D3DX sprite must revoke pending batch on device loss")
    for method, slot in (("LostDevice", 12), ("ResetDevice", 13)):
        callback_begin = lifecycle.find(f"static HRESULT __stdcall {method}Dest(void* self)")
        callback_end = lifecycle.find("\n    }", callback_begin)
        callback = lifecycle[callback_begin:callback_end] if (
            callback_begin >= 0 and callback_end > callback_begin) else ""
        owner = "const bool ownsBatch = DX9ExD3DXSpriteLifetime::OwnsLifecycle("
        live_argument = "self, TrackedSprite, *Module::exe_ptr<void*>(0x55B218));"
        trampoline = f"const HRESULT hr = {method}_hk.stdcall<HRESULT>(self);"
        invalidate = "InvalidateForDeviceLifecycle(ownsBatch);"
        need(owner in callback and live_argument in callback and
             trampoline in callback and invalidate in callback and
             "return hr;" in callback and
             callback.index(owner) < callback.index(trampoline) <
             callback.index(invalidate) < callback.index("return hr;") and
             lifecycle.count(invalidate) == 2 and
             f"vtable[{slot}]" in hook and
             f"reinterpret_cast<void*>(&{method}Dest)" in hook and
             f"{method}_hk.enable().has_value()" in hook and
             f"{method}_hk = {{}};" in hook,
             f"{method} old/live sprite lifecycle callback must preserve original HRESULT")
    flush_start = hook.find("static bool FlushTracked(")
    flush_end = hook.find("\npublic:", flush_start)
    flush = hook[flush_start:flush_end] if (
        flush_start >= 0 and flush_end > flush_start) else ""
    read_live = "void* liveSprite = *Module::exe_ptr<void*>(0x55B218);"
    predicate = "!DX9ExD3DXSpriteLifetime::CanFlush("
    invalidate_stale = "if (self && self == TrackedSprite && self != liveSprite)"
    dereference = "void** vtable = *reinterpret_cast<void***>(self);"
    need(read_live in flush and "if (!BatchActive ||" in flush and
         predicate in flush and "self, TrackedSprite, liveSprite)" in flush and
         invalidate_stale in flush and "InvalidateForDeviceLifecycle(true);" in flush and
         "return false;" in flush and dereference in flush and
         flush.find(read_live) < flush.find(predicate) <
         flush.find(invalidate_stale) < flush.find(dereference) and
         flush.find("return false;") < flush.find(dereference),
         "FlushTracked must prevent stale vtable dereference and forget replaced D3DX batch")
    need("LostDevice_hk && ResetDevice_hk" in hook and
         "vtable[12] && vtable[13]" in hook,
         "batch hook installation must include both reset edges")
    direct_begin = hook.find("static void BeforeDirectStageSource() noexcept")
    # The new exit hook also uses PendingScope/PendingProducer. Keep the
    # OLD entry admission check bounded to its own function, not both hooks.
    direct_end = hook.find("static void AfterDirectStageSource() noexcept", direct_begin)
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
    need("pendingDraws != 0 && homogeneous" in stage_predicate and
         "pendingProducer == ProducerToken::StageExtensionTime" in stage_predicate and
         "currentScope == pendingScope" in stage_predicate and
         "currentProducer == pendingProducer" in stage_predicate,
         "direct source-exit predicate may not promote unrelated batches")
    need("PendingHomogeneous = false" in hook and
         "CanFlushD3DXPreQueueStageBatch(" in hook and
         "!QueueRenderActive()" in hook,
         "mixed/unknown owner fail-closed fallback missing")
    need("CanFlushD3DXPreQueueStageBatch(" in hook and
         "QueueRenderActive(), enteringStage || enteringGoal," in hook and
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
    need("queueActive && batchActive && exactSprite" in queued_goal_predicate and
         "pendingDraws == 1u && homogeneous" in queued_goal_predicate and
         "pendingScope == RenderScope::ScreenHud" in queued_goal_predicate and
         all(("pendingProducer == ProducerToken::" + token) in queued_goal_predicate
             for token in ("GoalTime020", "GoalTime150", "ResultProgress")) and
         "currentScope == pendingScope" in queued_goal_predicate and
         "currentProducer == pendingProducer" in queued_goal_predicate and
         "if (exactGoal && CanArmD3DXQueueGoalAfterDraw(" in hook and
         "(QueueRenderActive() && StageBoundaryReady)" in hook,
         "late GOAL queue Begin must rearm exact original GOAL GPU submission")
    # A clean queued GOAL family can now batch all of its glyphs until
    # BeforeQueueNode/End submits under the previous exact producer.
    # Do not silently regress into per-Draw native Flush while the GOAL
    # source still has its own queue boundary and proven ownership.
    need("if (CanDeferD3DXQueueGoalBatch(" in hook and
         "StageBoundaryReady,\n                PendingDraws, PendingHomogeneous" in hook and
         "if (FlushTracked(self))" in hook,
         "exact queued GOAL GPU batch must defer to owned queue boundary")
    need("GoalOwner(scope, source) && PendingHomogeneous" in hook and
         "exactGoal &&\n            PendingScope == scope" in hook and
         "GoalFlushes" in hook and "GoalFallbacks" in hook,
         "GOAL direct and deferred GPU submission requires exact source proof")
    for token in ("GoalTime020", "GoalTime150", "ResultProgress"):
        need(f"source == ProducerToken::{token}" in hook,
             f"GOAL token {token} missing")
    # The original three safe Sumo_Printf GOAL text parents use the same
    # finite producer as their appended SpriteNodes. Check their entry and
    # return boundaries *independently* of the progress/helper parents;
    # otherwise a global replacement mutation can hit this first call
    # without invalidating either of the old GOAL tests.
    printf_start = source.find("static void OutRunStagePrintfEnter(")
    printf_exit_start = source.find("static void OutRunStagePrintfLeave(", printf_start)
    printf_end = source.find("// R74 exact result-progress CALL boundaries",
                             printf_exit_start)
    printf_enter = source[printf_start:printf_exit_start] if (
        0 <= printf_start < printf_exit_start) else ""
    printf_exit = source[printf_exit_start:printf_end] if (
        0 <= printf_exit_start < printf_end) else ""
    need("0x975EE, 0x97727, 0x977FB" in source and
         "FlushD3DXBeforeDirectGoalSource();" in printf_enter and
         "!OutRunVR::GameSemantic::QueueRenderActive()" in printf_enter and
         "ProducerToken::OutRunStagePrintf" in printf_enter and
         printf_enter.find("FlushD3DXBeforeDirectGoalSource();") <
         printf_enter.find("OutRunStagePrintfDirectDrawOwner.emplace("),
         "three GOAL Sumo_Printf direct parents must split old D3DX batch before source takeover")
    need("TagAppendedNodes(OutRunStagePrintfBefore" in printf_exit and
         "FlushD3DXAtDirectGoalSourceExit();" in printf_exit and
         printf_exit.find("TagAppendedNodes(OutRunStagePrintfBefore") <
         printf_exit.find("FlushD3DXAtDirectGoalSourceExit();") <
         printf_exit.find("OutRunStagePrintfDirectDrawOwner.reset();"),
         "three GOAL Sumo_Printf parents must submit their own D3DX draw before source restoration")
    need("source == ProducerToken::OutRunStagePrintf" in hook and
         "pendingProducer == ProducerToken::OutRunStagePrintf" in queued_goal_predicate and
         "pendingProducer == ProducerToken::OutRunStagePrintf" in goal_predicate,
         "direct and queued GOAL D3DX admission must retain exact Sumo_Printf source")
    # GOAL time/title helper batching is independent of the +TIME owner.
    # Prove both original CALL boundaries and the exact producer limitation
    # survive refactors, while accepting eager native GOAL Flush behavior.
    goal_helper_start = source.find("static void GoalTime_TagHelper(")
    goal_helper_end = source.find("static void __cdecl GoalTime_Help020()", goal_helper_start)
    goal_helper = source[goal_helper_start:goal_helper_end] if (
        goal_helper_start >= 0 and goal_helper_end > goal_helper_start) else ""
    need("FlushD3DXBeforeDirectGoalSource();" in goal_helper and
         "FlushD3DXAtDirectGoalSourceExit();" in goal_helper and
         "goalDirectDrawOwner.emplace(" in goal_helper and
         goal_helper.find("FlushD3DXBeforeDirectGoalSource();") <
         goal_helper.find("goalDirectDrawOwner.emplace(") <
         goal_helper.find("FlushD3DXAtDirectGoalSourceExit();") <
         goal_helper.find("goalDirectDrawOwner.reset();") and
         "ProducerToken::GoalTime020" in goal_helper and
         "ProducerToken::GoalTime150" in goal_helper,
         "direct GOAL producer must split previous and submit own D3DX batch")
    need("static void BeforeDirectGoalSource() noexcept" in hook and
         "static void AfterDirectGoalSource() noexcept" in hook and
         "CanFlushD3DXDirectGoalAtExit(" in hook and
         "VRProjectedD3DXSpriteIsolationR64::BeforeDirectGoalSource();" in code and
         "VRProjectedD3DXSpriteIsolationR64::AfterDirectGoalSource();" in code,
         "GOAL direct owner hooks must reach actual D3DX batch submission")
    progress_start = source.find("static void ResultProgressEnter(")
    progress_end = source.find("static void ResultProgressLeave(", progress_start)
    progress_enter = source[progress_start:progress_end] if (
        progress_start >= 0 and progress_end > progress_start) else ""
    progress_exit_start = source.find("static void ResultProgressLeave(")
    progress_exit_end = source.find("inline static SafetyHookMid StageExtensionEnterHooks[",
                                     progress_exit_start)
    progress_exit = source[progress_exit_start:progress_exit_end] if (
        progress_exit_start >= 0 and progress_exit_end > progress_exit_start) else ""
    need("QueueRenderActive()" in progress_enter and
         "FlushD3DXBeforeDirectGoalSource();" in progress_enter and
         "ProducerToken::ResultProgress" in progress_enter and
         progress_enter.find("FlushD3DXBeforeDirectGoalSource();") <
         progress_enter.find("ResultProgressDirectDrawOwner.emplace("),
         "GOAL 0-99% must flush proven outgoing direct batch before acquiring ScreenHud")
    need("TagAppendedNodes(ResultProgressTailsBefore" in progress_exit and
         "FlushD3DXAtDirectGoalSourceExit();" in progress_exit and
         progress_exit.find("TagAppendedNodes(ResultProgressTailsBefore") <
         progress_exit.find("FlushD3DXAtDirectGoalSourceExit();") <
         progress_exit.find("ResultProgressDirectDrawOwner.reset();"),
         "GOAL 0-99% direct D3DX GPU batch must flush under original progress owner")
    need("pendingDraws != 0 && homogeneous" in goal_predicate and
         "pendingProducer == ProducerToken::GoalTime020" in goal_predicate and
         "pendingProducer == ProducerToken::GoalTime150" in goal_predicate and
         "pendingProducer == ProducerToken::ResultProgress" in goal_predicate and
         "currentScope == pendingScope" in goal_predicate and
         "currentProducer == pendingProducer" in goal_predicate and
         "!queueActive && batchActive && exactSprite" in goal_predicate,
         "GOAL direct source must fail closed for mixed, stale or foreign buffers")
    # +TIME now coalesces draws until the exact queue transition/exit or
    # direct source exit. A per-Draw stage Flush regresses GPU batching and
    # can break the original texture grouping; GOAL stays eager separately.
    stage_draw = hook[hook.find("const bool exactStage = StageOwner(scope, source)"):
                      hook.find("// Preserve HMD-verified R64 rank isolation")]
    need("queueActive && batchActive && exactSprite" in queued_stage_predicate and
         "pendingDraws == 1u && homogeneous" in queued_stage_predicate and
         "pendingScope == RenderScope::ScreenHud" in queued_stage_predicate and
         "pendingProducer == ProducerToken::StageExtensionTime" in queued_stage_predicate and
         "currentScope == pendingScope" in queued_stage_predicate and
         "currentProducer == pendingProducer" in queued_stage_predicate,
         "late Begin stage rearm must require the first clean exact owner")
    need("if (exactStage && CanArmD3DXQueueStageAfterDraw(" in stage_draw and
         "QueueRenderActive(), BatchActive, self == TrackedSprite," in stage_draw and
         "PendingDraws, PendingHomogeneous, PendingScope, PendingProducer," in stage_draw and
         "scope, source))\n            StageBoundaryReady = true;" in stage_draw and
         stage_draw.find("StageBoundaryReady = true;") <
         stage_draw.find("if (exactStage)\n            return hr;"),
         "post-queue Begin must rearm exact +TIME flush before source exit")
    need("const bool exactStage = StageOwner(scope, source) && PendingHomogeneous;" in stage_draw and
         "if (exactStage)\n            return hr;" in stage_draw and
         stage_draw.find("if (exactStage)\n            return hr;") <
         stage_draw.find("const bool exactGoal = GoalOwner(scope, source)") and
         "exactGoal &&\n            PendingScope == scope" in stage_draw and
         "(exactStage || exactGoal)" not in stage_draw and
         "GoalFlushes.fetch_add(" in stage_draw and
         "StageFlushes.fetch_add(" not in stage_draw,
         "+TIME must defer batched D3DX GPU submission to its queue/source exit; GOAL eager owner protected")
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


def check_exact_goal_xyzrhw_plane(renderer: str, semantics: str) -> list[str]:
    """Source-path and mutation guard for exact GOAL physical XYZRHW draws.

    The C++ static_asserts exercise positive and protected negative tokens;
    this additionally requires that the R84 physical draw actually calls
    that exact predicate BEFORE the generic 2D/fog depth classifier.
    """
    errors: list[str] = []
    begin = renderer.find("bool R30PrepareXyzrhwState(")
    # The actual draw branch follows its state-preparation helper.
    physical = renderer.find("CorroboratesProjectedWorldMarker(", begin)
    generic = renderer.find("// Smoke/sand can redraw", physical)
    section = renderer[physical:generic] if 0 <= begin < physical < generic else ""
    predicate = semantics[semantics.find("inline constexpr bool CanReprojectFiniteResultHudPlane("):
                          semantics.find("    static_assert(CanReprojectFiniteResultHudPlane(")]
    required = ("StageExtensionTime", "GoalTime020", "GoalTime150",
                "ResultProgress", "OutRunStagePrintf")
    if not all(("producer == ProducerToken::" + token) in predicate for token in required):
        errors.append("exact stage/GOAL source family missing from C++ predicate")
    if ("scope == RenderScope::ScreenHud" not in predicate or
            "ProducerToken::ResultTextB9200" in predicate or
            "ProducerToken::DispRankClipSprite" in predicate):
        errors.append("GOAL plane admits unsafe non-owned result/rank draws")
    if ("CanReprojectFiniteResultHudPlane(" not in section or
            "CurrentRenderProducerToken()" not in section or
            "R30BuildStageExtensionXyzrhwEyePlane(" not in section or
            "return haveBaseProjection &&" not in section):
        errors.append("physical R84 XYZRHW draw bypasses exact GOAL eye plane")
    return errors


def main() -> int:
    code = SOURCE.read_text(encoding="utf-8")
    header = SEMANTICS.read_text(encoding="utf-8")
    errors = check(code, header)
    renderer = (ROOT / "src/vr/d3d9/stereo_renderer_r30.cpp").read_text(encoding="utf-8")
    errors.extend(check_exact_goal_xyzrhw_plane(renderer, header))
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
            code.replace(
                "else if (PendingScope != scope || PendingProducer != source)\n"
                "            {\n"
                "                PendingHomogeneous = false;\n"
                "            }",
                "else if (PendingScope != scope || PendingProducer != source)\n"
                "            {\n"
                "                PendingHomogeneous = true;\n"
                "            }", 1),
        "explicit-flush-keeps-stale-stage-owner":
            code.replace(
                "ForgetBatch();\n                StageBoundaryReady = false;",
                "ForgetBatch();\n                StageBoundaryReady = true;", 1),
        "native-flush-keeps-stale-queue-boundary":
            code.replace(
                "ForgetBatch();\n                StageBoundaryReady = false;",
                "ForgetBatch();\n                StageBoundaryReady = true;", 1),
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
        "late-begin-stage-not-rearmed":
            code.replace("scope, source))\n            StageBoundaryReady = true;",
                         "scope, source))\n            StageBoundaryReady = false;", 1),
        "late-begin-stage-foreign-promoted":
            code.replace("if (exactStage && CanArmD3DXQueueStageAfterDraw(",
                         "if (exactStage || CanArmD3DXQueueStageAfterDraw(", 1),
        "stage-eager-draw-regression":
            code.replace("if (exactStage)\n            return hr;",
                         "if (false)\n            return hr;", 1),
        "stage-draw-steals-goal-eager-path":
            code.replace("            exactGoal &&\n            PendingScope == scope",
                         "            (exactStage || exactGoal) &&\n            PendingScope == scope", 1),
        "goal-late-begin-rearm-removed":
            code.replace("if (exactGoal && CanArmD3DXQueueGoalAfterDraw(",
                         "if (false && CanArmD3DXQueueGoalAfterDraw(", 1),
        "goal-prequeue-old-owner-split-removed":
            code.replace("enteringStage || enteringGoal,",
                         "enteringStage,", 1),
        "goal-queue-eager-flush-removed":
            code.replace("(QueueRenderActive() && StageBoundaryReady)",
                         "(false && StageBoundaryReady)", 1),
        "goal-batch-source-lost":
            code.replace("GoalOwner(scope, source) && PendingHomogeneous",
                         "false && PendingHomogeneous", 1),
        "goal-helper-boundary-lost":
            code.replace("nextProducer != CurrentRenderProducerToken()",
                         "false", 1),
        "goal-queue-admission-lost":
            code.replace("StageBoundaryReady = enteringStage || enteringGoal",
                         "StageBoundaryReady = enteringStage;", 1),
        "goal-direct-before-removed":
            code.replace("            FlushD3DXBeforeDirectGoalSource();",
                         "            // GOAL old batch not flushed", 1),
        "goal-direct-after-removed":
            code.replace("            FlushD3DXAtDirectGoalSourceExit();",
                         "            // GOAL exit not flushed", 1),
        "goal-progress-owner-lost":
            code.replace("source == ProducerToken::ResultProgress",
                         "source == ProducerToken::None", 1),
        "progress-preflush-lost":
            code.replace(
                "                FlushD3DXBeforeDirectGoalSource();",
                "                // missing result progress old-batch split", 1),
        "progress-exit-flush-lost":
            code.replace(
                "        FlushD3DXAtDirectGoalSourceExit();\n"
                "        ResultProgressDirectDrawOwner.reset();",
                "        ResultProgressDirectDrawOwner.reset();", 1),
        "failed-nested-begin-wipes-pending-owner":
            code.replace("if (FAILED(hr) && existingBatch)\n                return hr;",
                         "if (FAILED(hr) && false)\n                return hr;", 1),
        "failed-draw-keeps-old-owner":
            code.replace("if (self && self == TrackedSprite)\n            {\n                BatchActive = false;",
                         "if (self && false)\n            {\n                BatchActive = false;", 1),
        "lost-device-invalidates-no-batch":
            code.replace(
                "const HRESULT hr = LostDevice_hk.stdcall<HRESULT>(self);\n"
                "        InvalidateForDeviceLifecycle(ownsBatch);",
                "const HRESULT hr = LostDevice_hk.stdcall<HRESULT>(self);", 1),
        "reset-device-invalidates-no-batch":
            code.replace(
                "const HRESULT hr = ResetDevice_hk.stdcall<HRESULT>(self);\n"
                "        InvalidateForDeviceLifecycle(ownsBatch);",
                "const HRESULT hr = ResetDevice_hk.stdcall<HRESULT>(self);", 1),
        "reset-must-not-promote-stale-owner":
            code.replace("        TrackedSprite = nullptr;",
                         "        TrackedSprite = self;", 1),
        "reset-must-not-include-foreign-sprite":
            code.replace("        if (!wasTrackedOrExactGameSprite)\n            return;",
                         "        if (false)\n            return;", 1),
        "reset-hook-absent":
            code.replace("ResetDevice_hk.enable().has_value()", "false", 1),
        "lost-must-propagate-original-error":
            code.replace(
                "InvalidateForDeviceLifecycle(ownsBatch);\n        return hr;\n"
                "    }\n\n    static HRESULT __stdcall ResetDeviceDest",
                "InvalidateForDeviceLifecycle(ownsBatch);\n        return D3D_OK;\n"
                "    }\n\n    static HRESULT __stdcall ResetDeviceDest", 1),
        "reset-must-propagate-original-error":
            code.replace(
                "const HRESULT hr = ResetDevice_hk.stdcall<HRESULT>(self);\n"
                "        InvalidateForDeviceLifecycle(ownsBatch);\n        return hr;",
                "const HRESULT hr = ResetDevice_hk.stdcall<HRESULT>(self);\n"
                "        InvalidateForDeviceLifecycle(ownsBatch);\n        return D3D_OK;", 1),
        "lost-must-capture-exact-before-original":
            code.replace(
                "const bool ownsBatch = DX9ExD3DXSpriteLifetime::OwnsLifecycle(\n"
                "            self, TrackedSprite, *Module::exe_ptr<void*>(0x55B218));\n"
                "        const HRESULT hr = LostDevice_hk.stdcall<HRESULT>(self);",
                "const HRESULT hr = LostDevice_hk.stdcall<HRESULT>(self);\n"
                "        const bool ownsBatch = DX9ExD3DXSpriteLifetime::OwnsLifecycle(\n"
                "            self, TrackedSprite, *Module::exe_ptr<void*>(0x55B218));", 1),
        "reset-must-capture-exact-before-original":
            code.replace(
                "const bool ownsBatch = DX9ExD3DXSpriteLifetime::OwnsLifecycle(\n"
                "            self, TrackedSprite, *Module::exe_ptr<void*>(0x55B218));\n"
                "        const HRESULT hr = ResetDevice_hk.stdcall<HRESULT>(self);",
                "const HRESULT hr = ResetDevice_hk.stdcall<HRESULT>(self);\n"
                "        const bool ownsBatch = DX9ExD3DXSpriteLifetime::OwnsLifecycle(\n"
                "            self, TrackedSprite, *Module::exe_ptr<void*>(0x55B218));", 1),
        "lost-old-tracked-sprite-missed":
            code.replace("(callback == tracked || callback == live);",
                         "(callback == live);", 1),
        "foreign-sprite-revokes-old-batch":
            code.replace("callback != nullptr &&",
                         "true &&", 1),
        "flush-live-instance-proof-missing":
            code.replace("candidate == live;", "true;", 1),
        "flush-allows-null-candidate":
            code.replace("candidate != nullptr && candidate == tracked &&",
                         "candidate == tracked &&", 1),
        "flush-dead-instance-promoted":
            code.replace("!DX9ExD3DXSpriteLifetime::CanFlush(",
                         "DX9ExD3DXSpriteLifetime::CanFlush(", 1),
        "flush-old-owner-not-revoked":
            code.replace("InvalidateForDeviceLifecycle(true);",
                         "// stale owner retained", 1),
        "flush-skips-live-identity-read":
            code.replace("void* liveSprite = *Module::exe_ptr<void*>(0x55B218);",
                         "void* liveSprite = TrackedSprite;", 1),
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
        "late-begin-permit-extra-draw": header.replace(
            "pendingDraws == 1u && homogeneous",
            "pendingDraws != 0 && homogeneous", 1),
        "late-begin-permit-no-queue": header.replace(
            "return queueActive && batchActive && exactSprite &&",
            "return batchActive && exactSprite &&", 1),
        "permit-wrong-producer": header.replace(
            "pendingProducer == outgoingProducer",
            "pendingProducer != outgoingProducer", 1),
    }.items():
        if altered == header or not check(code, altered):
            print("DX9Ex +TIME D3DX FAIL: header mutation", label)
            return 1
    # Mutate only the GOAL function: the still-intact +TIME predicate must
    # not mask loss of GOAL's separate batch ownership.
    goal_begin = header.find("inline constexpr bool CanFlushD3DXDirectGoalAtExit(")
    goal_end = header.find("    static_assert(CanFlushD3DXDirectGoalAtExit(", goal_begin)
    if goal_begin < 0 or goal_end <= goal_begin:
        print("DX9Ex +TIME D3DX FAIL: GOAL predicate boundary missing")
        return 1
    goal_body = header[goal_begin:goal_end]
    for label, before, after in (
        ("goal-permit-mixed", "pendingDraws != 0 && homogeneous",
         "pendingDraws != 0 && true"),
        ("goal-permit-foreign", "pendingProducer == ProducerToken::GoalTime020",
         "pendingProducer != ProducerToken::GoalTime020"),
        ("progress-owner-lost", "pendingProducer == ProducerToken::ResultProgress",
         "pendingProducer == ProducerToken::None"),
        ("goal-permit-owner-swap", "currentProducer == pendingProducer",
         "true"),
    ):
        changed = goal_body.replace(before, after, 1)
        altered = header[:goal_begin] + changed + header[goal_end:]
        if changed == goal_body or not check(code, altered):
            print("DX9Ex +TIME D3DX FAIL: GOAL header mutation", label)
            return 1
    print("DX9Ex +TIME/GOAL isolated direct D3DX owner and negative mutations PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
