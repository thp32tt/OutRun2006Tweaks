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
    # A D3DX internal Draw may flush before local producer scope lookup. The
    # early queue status call must resolve its actual GameSemantic namespace
    # in an independently compiled R84 source translation unit.
    early_draw = draw_path.split("const HRESULT hr = Draw_hk.stdcall", 1)[0]
    need("BatchActive, OutRunVR::GameSemantic::QueueRenderActive()," in early_draw and
         "PendingHomogeneous," in early_draw,
         "pre-draw deferred owner handoff must call qualified queue state")
    # Physically submitting the outgoing homogeneous +TIME/GOAL batch
    # from an incoming foreign Draw MUST rebind the saved producer. Merely
    # remembering the old token for telemetry still draws under the new
    # GameSemantic scope and can create a duplicate/head-locked overlay.
    outgoing = early_draw[early_draw.find("const bool wasStage = StageOwner("):]
    need("const auto outgoingScope = PendingScope;" in outgoing and
         "const auto outgoingProducer = PendingProducer;" in outgoing and
         "ScopedExactProducerSemantic outgoingBatch(" in outgoing and
         "outgoingScope, nullptr, true, outgoingProducer);" in outgoing and
         outgoing.find("ScopedExactProducerSemantic outgoingBatch(") <
         outgoing.find("flushed = FlushTracked(self);") <
         outgoing.find("if (flushed)") and
         "PendingHomogeneous" in early_draw and
         "CanDrainDeferredResultBeforeForeignDraw(" in early_draw,
         "foreign D3DX Draw must submit old +TIME/GOAL GPU triangles under saved producer")
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
    flush_identity_predicate = "!DX9ExD3DXSpriteLifetime::CanFlush("
    invalidate_stale = "if (self && self == TrackedSprite && self != liveSprite)"
    dereference = "void** vtable = *reinterpret_cast<void***>(self);"
    need(read_live in flush and "if (!BatchActive ||" in flush and
         flush_identity_predicate in flush and "self, TrackedSprite, liveSprite)" in flush and
         invalidate_stale in flush and "InvalidateForDeviceLifecycle(true);" in flush and
         "return false;" in flush and dereference in flush and
         flush.find(read_live) < flush.find(flush_identity_predicate) <
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

    # The first SpriteNode is not yet QueueRenderActive. Prove the live
    # implementation drains a preceding *direct* result under its saved
    # source before entering that new node, never under the new producer.
    queue_start = hook.find("static void BeforeQueueNode(")
    queue_end = hook.find("static void BeforeQueueEnd(", queue_start)
    first_queue = hook[queue_start:queue_end] if (
        0 <= queue_start < queue_end) else ""
    first_guard_begin = header.find(
        "inline constexpr bool CanDrainDirectResultBeforeFirstQueueNode(")
    first_guard_end = header.find("    static_assert(", first_guard_begin)
    exact_first = header[first_guard_begin:first_guard_end] if (
        first_guard_begin >= 0 and first_guard_end > first_guard_begin) else ""
    need("if (CanDrainDirectResultBeforeFirstQueueNode(" in first_queue and
         "QueueRenderActive(), BatchActive," in first_queue and
         "DX9ExD3DXSpriteLifetime::CanFlush(" in first_queue and
         "PendingDraws, PendingHomogeneous," in first_queue and
         "PendingScope, PendingProducer, nextScope, nextProducer" in first_queue and
         "ScopedExactProducerSemantic outgoingBatch(" in first_queue and
         "flushed = FlushTracked(firstQueueSprite);" in first_queue and
         first_queue.index("flushed = FlushTracked(firstQueueSprite);") <
         first_queue.index("const bool enteringStage") and
         "BatchActive = false;" in first_queue and
         "ForgetBatch();" in first_queue,
         "first queue node must submit previous direct result under saved exact GPU owner")
    need("!batchActive || !exactLiveSprite" in exact_first and
         "!homogeneous || pendingDraws == 0u" in exact_first and
         "pendingScope != RenderScope::ScreenHud" in exact_first and
         "incomingProducer != pendingProducer" in exact_first and
         "ProducerToken::ResultTextB9200" not in exact_first and
         all("pendingProducer == ProducerToken::" + token in exact_first
             for token in ("StageExtensionTime", "GoalTime020", "GoalTime150",
                           "ResultProgress", "OutRunStagePrintf")),
         "first queue transition must exclude untracked, mixed, B9200 or same-owner buffers")
    need("pendingScope != RenderScope::None" in header and
         "pendingProducer != ProducerToken::None" in header,
         "pre-queue transition may not flush an unknown None/None batch")
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
                "ResultProgress", "OutRunStagePrintf", "ResultTextB9200")
    if not all(("producer == ProducerToken::" + token) in predicate for token in required):
        errors.append("exact stage/GOAL source family missing from C++ predicate")
    if ("scope == RenderScope::ScreenHud" not in predicate or
            "ProducerToken::DispRankClipSprite" in predicate):
        errors.append("GOAL plane admits unsafe non-owned rank draws")
    # B9200 is now safe only after its exact original E8 caller is proven
    # by the existing glyph wrapper; never revive the crashing +5 midhooks.
    ui = SOURCE.read_text(encoding="utf-8")
    if ("IsOriginalB9200GoalGlyph()" not in ui or
            "GoalResult::IsOriginalB9200ParentReturn(" not in ui or
            "RtlCaptureStackBackTrace(" not in ui):
        errors.append("B9200 HUD-plane source lacks exact return-stack proof")
    if ("CanReprojectFiniteResultHudPlane(" not in section or
            "CurrentRenderProducerToken()" not in section or
            "R30BuildStageExtensionXyzrhwEyePlane(" not in section or
            "return haveBaseProjection &&" not in section):
        errors.append("physical R84 XYZRHW draw bypasses exact GOAL eye plane")
    return errors



def check_current_ledger(code: str, header: str, ledger: str) -> list[str]:
    """Validate actual Quest-style Ledger + live D3DX GPU owner, not old TLS spelling.

    Check only each owning callback's body and validate Ledger's method
    implementation; comments or a declaration of the new class cannot pass.
    The original pre-refactor verifier below remains available for old code.
    """
    errors: list[str] = []
    def need(conditions: bool, what: str) -> None:
        if not conditions:
            errors.append(what)
    def scope(text: str, start: str, end: str) -> str:
        a = text.find(start)
        b = text.find(end, a + len(start)) if a >= 0 else -1
        return text[a:b] if a >= 0 and b > a else ""
    start = code.find("class VRProjectedD3DXSpriteIsolationR64 : public Hook")
    finish = code.find("class VRHudQueueSemanticBridge : public Hook", start)
    need(start >= 0 and finish > start, "live R64 GPU hook must exist")
    if start < 0 or finish <= start:
        return errors
    h = code[start:finish]
    pre = code[:start]
    begin = scope(h, "static HRESULT __stdcall BeginDest(", "static HRESULT __stdcall FlushDest(")
    flush = scope(h, "static HRESULT __stdcall FlushDest(", "static HRESULT __stdcall EndDest(")
    end = scope(h, "static HRESULT __stdcall EndDest(", "static void InvalidateForDeviceLifecycle(")
    lifecycle = scope(h, "static void InvalidateForDeviceLifecycle(", "static bool FlushTracked(")
    live_flush = scope(h, "static bool FlushTracked(", "\npublic:")
    direct_stage = scope(h, "static void BeforeDirectStageSource() noexcept", "static void AfterDirectStageSource() noexcept")
    exit_stage = scope(h, "static void AfterDirectStageSource() noexcept", "static void BeforeDirectGoalSource() noexcept")
    node = scope(h, "static void BeforeQueueNode(", "static void BeforeQueueEnd() noexcept")
    queue_end = scope(h, "static void BeforeQueueEnd() noexcept", "\nprivate:")
    draw = scope(h, "static HRESULT __stdcall DrawDest(", "static DWORD WINAPI InstallThread(")
    ledger_begin = scope(ledger, "void begin(", "void recordDraw(")
    ledger_draw = scope(ledger, "void recordDraw(", "void forget(")
    ledger_forget = scope(ledger, "void forget(", "void onFlushSuccess(")
    ledger_flush = scope(ledger, "void onFlushSuccess(", "void onFlushFailure(")
    ledger_fail = scope(ledger, "void onFlushFailure(", "void end(")
    ledger_end = scope(ledger, "void end(", "void invalidate(")
    ledger_reset = scope(ledger, "void invalidate(", "bool exactUniformOwner(")
    stage_predicate = scope(header, "inline constexpr bool CanFlushD3DXDirectStageAtExit(", "    static_assert(")
    goal_predicate = scope(header, "inline constexpr bool CanFlushD3DXDirectGoalAtExit(", "    static_assert(")
    need("pendingProducer == ProducerToken::StageExtensionTime" in stage_predicate and
         "pendingDraws != 0 && homogeneous" in stage_predicate and
         "currentProducer == pendingProducer" in stage_predicate,
         "pure +TIME exit predicate exact owner/homogeneity")
    need("pendingProducer == ProducerToken::GoalTime020" in goal_predicate and
         "pendingProducer == ProducerToken::GoalTime150" in goal_predicate and
         "pendingProducer == ProducerToken::ResultProgress" in goal_predicate and
         "currentProducer == pendingProducer" in goal_predicate,
         "pure GOAL exit predicate exact source admission")
    need("vr/game/hud_command_batch.hpp" in code and
         "inline static thread_local OutRunVR::HudCommandBatch::Ledger HudBatch{};" in h,
         "live R64 uses one thread-local command ledger")
    need("0x9898E, 0x98A36, 0x98AC6" in pre and
         "0x989AD, 0x98A10, 0x98A89" in pre and
         "TagAppendedNodes(StageExtensionBefore" in pre,
         "six exact +TIME sprite/numeric parents survive")
    need("FlushD3DXBeforeDirectStageSource();" in pre and
         "FlushD3DXAtDirectStageSourceExit();" in pre and
         "StageExtensionDirectDrawOwner.reset();" in pre,
         "direct +TIME Begin/exit must split and restore owner")
    need("ProducerToken::ResultProgress" in pre and
         "ProducerToken::GoalTime020" in pre and
         "ProducerToken::GoalTime150" in pre and
         "ProducerToken::OutRunStagePrintf" in pre,
         "exact GOAL production source edges survive")
    need("const auto beforeBegin = HudBatch.snapshot();" in begin and
         "if (HudBatch.generation == beforeBegin.generation)" in begin and
         "HudBatch.onBeginResult(" in begin and
         "self, SUCCEEDED(hr), hr == D3DERR_INVALIDCALL);" in begin and
         "else if (self && self == HudBatch.sprite)" in begin and
         "HudBatch.invalidate();" in begin and
         begin.index("const auto beforeBegin = HudBatch.snapshot();") <
         begin.index("Begin_hk.stdcall<HRESULT>(self, flags)") <
         begin.index("if (HudBatch.generation == beforeBegin.generation)") <
         begin.index("HudBatch.onBeginResult("),
         "new native Begin cannot overwrite nested successful Begin")
    # Check the actual Ledger failure transition, not only a renamed game
    # hook. DEVICELOST/other Begin failures must revoke old +TIME/GOAL
    # GPU owner, while the same-sprite nested INVALIDCALL is lossless.
    need("void onBeginResult(" in ledger_begin and
         "if (succeeded)" in ledger_begin and
         "begin(exactSprite, true);" in ledger_begin and
         "if (reentrantInvalidCall && active && exactSprite != nullptr &&" in ledger_begin and
         "sprite == exactSprite)" in ledger_begin and
         "invalidate();" in ledger_begin and
         ledger_begin.find("begin(exactSprite, true);") <
         ledger_begin.find("if (reentrantInvalidCall && active") <
         ledger_begin.find("invalidate();"),
         "Ledger must quarantine failed device Begin and preserve only nested INVALIDCALL")
    need("sprite = exactSprite;" in ledger_begin and "active = succeeded;" in ledger_begin and
         "forget();" in ledger_begin and
         "if (succeeded && generation != UINT64_MAX)" in ledger_begin,
         "Ledger Begin must clear ownership only after accepted native Begin")
    # Node and queue epoch are part of the *physical* GPU source, not just
    # a semantic token. Keep direct glyphs isolated from queued sprites and
    # reject reentrant native Draws from a different SpriteNode.
    need("if (!active)" in ledger_draw and "if (drawCount == 0)" in ledger_draw and
         "scope = newScope;" in ledger_draw and "producer = newProducer;" in ledger_draw and
         "const bool validQueue = !drawQueued ||" in ledger_draw and
         "drawQueueNode != nullptr && drawQueueEpoch != 0" in ledger_draw and
         "queued = drawQueued;" in ledger_draw and
         "queueNode = drawQueued ? drawQueueNode : nullptr;" in ledger_draw and
         "queueEpoch = drawQueued ? drawQueueEpoch : 0;" in ledger_draw and
         "homogeneous = validQueue;" in ledger_draw and
         "else if (!validQueue || scope != newScope ||" in ledger_draw and
         "producer != newProducer || queued != drawQueued ||" in ledger_draw and
         "queueNode != drawQueueNode" in ledger_draw and
         "queueEpoch != drawQueueEpoch" in ledger_draw and
         "homogeneous = false;" in ledger_draw and "++drawCount;" in ledger_draw and
         "std::numeric_limits<unsigned>::max" in ledger_draw,
         "Ledger must quarantine mixed token, direct/queue and distinct node/epoch Draws")
    need("drawCount = 0;" in ledger_forget and "homogeneous = true;" in ledger_forget and
         "scope = Scope::None;" in ledger_forget and "producer = Producer::None;" in ledger_forget,
         "Ledger forget must withdraw old source, not silently promote it")
    need("forget();" in ledger_flush and "boundaryReady = false;" in ledger_flush and
         "active = false;" in ledger_fail and "boundaryReady = false;" in ledger_fail and
         "active = false;" in ledger_end and "forget();" in ledger_end and
         "end();" in ledger_reset and "sprite = nullptr;" in ledger_reset,
         "Ledger Flush success/failure/End/Reset transition contracts")
    need("CanRestoreDeferredResultOwner(" in flush and
         "HudBatch.active, QueueRenderActive(), HudBatch.homogeneous" in flush and
         "HudBatch.scope, HudBatch.producer" in flush and
         "ScopedExactProducerSemantic owned(" in flush and
         "const auto submission = HudBatch.snapshot();" in flush and
         "Flush_hk.stdcall<HRESULT>(self)" in flush and
         "HudBatch.completeNativeFlush(submission, SUCCEEDED(hr));" in flush and
         "return hr;" in flush and
         flush.index("const auto submission = HudBatch.snapshot();") <
         flush.index("Flush_hk.stdcall<HRESULT>(self)") <
         flush.index("HudBatch.completeNativeFlush(submission, SUCCEEDED(hr));"),
         "native Flush must retire only matching exact batch generation")
    need("CanRestoreDeferredResultOwner(" in end and
         "ScopedExactProducerSemantic owned(" in end and
         "const auto submission = HudBatch.snapshot();" in end and
         "End_hk.stdcall<HRESULT>(self)" in end and
         "HudBatch.completeNativeEnd(submission);" in end and
         "return hr;" in end and
         end.index("const auto submission = HudBatch.snapshot();") <
         end.index("End_hk.stdcall<HRESULT>(self)") <
         end.index("HudBatch.completeNativeEnd(submission);"),
         "native End must preserve newer nested Begin")
    need("if (!wasTrackedOrExactGameSprite)" in lifecycle and
         "HudBatch.invalidate();" in lifecycle and
         "DX9ExD3DXSpriteLifetime::OwnsLifecycle(" in lifecycle and
         "LostDevice_hk.stdcall<HRESULT>(self)" in lifecycle and
         "ResetDevice_hk.stdcall<HRESULT>(self)" in lifecycle and
         lifecycle.count("InvalidateForDeviceLifecycle(ownsBatch);") == 2 and
         lifecycle.count("return hr;") >= 2,
         "OnLost/OnReset must invalidate old/live sprite and propagate HRESULT")
    need("void* liveSprite = *Module::exe_ptr<void*>(0x55B218);" in live_flush and
         "!HudBatch.active ||" in live_flush and
         "self, HudBatch.sprite, liveSprite" in live_flush and
         "if (self && self == HudBatch.sprite && self != liveSprite)" in live_flush and
         "InvalidateForDeviceLifecycle(true);" in live_flush and
         "void** vtable = *reinterpret_cast<void***>(self);" in live_flush and
         live_flush.index("liveSprite =") < live_flush.index("CanFlush(") <
         live_flush.index("InvalidateForDeviceLifecycle(true)") <
         live_flush.index("reinterpret_cast<void***>(self)"),
         "stale D3DX pointer must not be dereferenced before live identity")
    need("CanDrainDeferredResultBeforeForeignDraw(" in draw and
         "HudBatch.active, OutRunVR::GameSemantic::QueueRenderActive()" in draw and
         "HudBatch.homogeneous" in draw and
         "ScopedExactProducerSemantic outgoingBatch(" in draw and
         "flushed = FlushTracked(self);" in draw and
         draw.index("ScopedExactProducerSemantic outgoingBatch(") <
         draw.index("flushed = FlushTracked(self);") <
         draw.index("const HRESULT hr = Draw_hk.stdcall"),
         "foreign Draw must submit previous batch under outgoing owner")
    need("const auto command = CapturePhysicalDrawCommand();" in draw and
         "const auto scope = command.scope;" in draw and
         "const auto source = command.producer;" in draw and
         "const auto submission = HudBatch.snapshot();" in draw and
         "const auto afterNative = CapturePhysicalDrawCommand();" in draw and
         "afterNative.scope == command.scope" in draw and
         "afterNative.producer == command.producer" in draw and
         "afterNative.queued == command.queued" in draw and
         "afterNative.queueNode == command.queueNode" in draw and
         "afterNative.queueEpoch == command.queueEpoch" in draw and
         "const bool sameSourceAfterNative =" in draw and
         "if (self && self == submission.sprite &&" in draw and
         "HudBatch.completeNativeDraw(" in draw and
         "submission, SUCCEEDED(hr), scope, source," in draw and
         "sameSourceAfterNative, command.queued," in draw and
         "command.queueNode, command.queueEpoch))" in draw and
         "if (FAILED(hr) || !self)" in draw and
         draw.index("const auto command = CapturePhysicalDrawCommand();") <
         draw.index("const auto submission = HudBatch.snapshot();") <
         draw.index("const HRESULT hr = Draw_hk.stdcall<HRESULT>(") <
         draw.index("const auto afterNative = CapturePhysicalDrawCommand();") <
         draw.index("HudBatch.completeNativeDraw("),
         "native Draw must preserve exact scope, queue node and epoch across original D3DX")
    need("CanFlushD3DXPreQueueStageBatch(" in direct_stage and
         "false, true, HudBatch.homogeneous" in direct_stage and
         "HudBatch.scope, HudBatch.producer" in direct_stage and
         "!FlushTracked(sprite)" in direct_stage,
         "direct +TIME source entry must split prior exact batch")
    need("CanFlushD3DXDirectStageAtExit(" in exit_stage and
         "HudBatch.drawCount, HudBatch.homogeneous" in exit_stage and
         "if (FlushTracked(sprite))" in exit_stage,
         "direct +TIME source exit must submit complete proven batch")
    first_guard = scope(header, "inline constexpr bool CanDrainDirectResultBeforeFirstQueueNode(", "    static_assert(")
    need("CanDrainDirectResultBeforeFirstQueueNode(" in node and
         "HudBatch.drawCount, HudBatch.homogeneous" in node and
         "HudBatch.scope, HudBatch.producer, nextScope, nextProducer" in node and
         "!HudBatch.queued && HudBatch.queueNode == nullptr &&" in node and
         "HudBatch.queueEpoch == 0" in node and
         "return knownResult && pendingBatchDirect;" in first_guard and
         "ScopedExactProducerSemantic outgoingBatch(" in node and
         "flushed = FlushTracked(firstQueueSprite);" in node and
         node.index("flushed = FlushTracked(firstQueueSprite);") <
         node.index("const bool enteringStage"),
         "first queue node must submit previous direct result under original owner")
    need("GoalOwner(nextScope, nextProducer)" in node and
         "nextProducer != CurrentRenderProducerToken()" in node and
         "HudBatch.boundaryReady = enteringStage || enteringGoal;" in node,
         "GOAL Stage/Result queue-owner boundary must remain selective")
    need("HudBatch.boundaryReady && QueueRenderActive()" in queue_end and
         "HudBatch.drawCount != 0 && HudBatch.homogeneous" in queue_end and
         "HudBatch.producer == CurrentRenderProducerToken()" in queue_end and
         "FlushTracked(HudBatch.sprite)" in queue_end,
         "queue exit must flush only proven exact pending source")
    need("if (exactStage && CanArmD3DXQueueStageAfterDraw(" in draw and
         "HudBatch.drawCount, HudBatch.homogeneous, HudBatch.scope, HudBatch.producer" in draw and
         "HudBatch.boundaryReady = true;" in draw and
         "if (exactStage)\n            return hr;" in draw and
         "const bool exactGoal = GoalOwner(scope, source) && HudBatch.homogeneous" in draw and
         "CanDeferD3DXQueueGoalBatch(" in draw and
         "GoalFlushes.fetch_add(" in draw,
         "post-draw +TIME batches defer while GOAL exact source retains separate path")
    # Validate actual batch transaction logic rather than a stale naming
    # convention. Native D3DX callbacks may reenter with a new Begin.
    snap = scope(ledger, "NativeSnapshot snapshot(", "void touch(")
    cf = scope(ledger, "bool completeNativeFlush(", "bool completeNativeEnd(")
    ce = scope(ledger, "bool completeNativeEnd(", "bool completeNativeDraw(")
    cd = scope(ledger, "bool completeNativeDraw(", "// Only an actual Begin or Reset")
    need("std::uint64_t mutationSerial = 0;" in ledger and
         "return { sprite, generation, mutationSerial };" in snap and
         "sprite == previous.sprite" in snap and
         "generation == previous.generation" in snap and
         "mutationSerial == previous.mutationSerial" in snap and
         "touch();" in ledger_draw and "touch();" in ledger_forget,
         "native batch must track source sprite/generation/mutation identity")
    need("if (!sameGeneration(previous))" in cf and
         "if (!unchanged(previous) || !succeeded)" in cf and
         "onFlushFailure();" in cf and "onFlushSuccess();" in cf and
         cf.find("onFlushFailure();") < cf.find("onFlushSuccess();"),
         "native Flush must not retire newer Begin or promote reentrant Draw")
    need("if (!sameGeneration(previous))" in ce and
         "end();" in ce and
         ce.find("if (!sameGeneration(previous))") < ce.find("end();"),
         "native End must preserve a reentrant Begin")
    # D3DX Sprite::Draw can synchronously call the hooked native Flush on a
    # texture switch. Do not throw away the incoming Draw's owner after that
    # exact successful GPU drain. Failed/mixed/new-generation callbacks still
    # cannot inherit a clean texture-transition stamp.
    ledger_flush_success = scope(ledger, "void onFlushSuccess()", "void onFlushFailure()")
    need("if (!sameGeneration(previous))" in cd and
         "if (!succeeded || !sourceStillMatches)" in cd and
         "if (!unchanged(previous))" in cd and
         "active && drawCount == 0" in cd and
         "homogeneous && scope == Scope::None" in cd and
         "producer == Producer::None" in cd and
         "lastSuccessfulFlushMutationSerial != 0" in cd and
         "lastSuccessfulFlushMutationSerial == mutationSerial" in cd and
         "if (!cleanInternalFlush)" in cd and
         "onFlushFailure();" in cd and
         "recordDraw(drawScope, drawProducer," in cd and
         "drawQueued, drawQueueNode, drawQueueEpoch);" in cd and
         cd.find("if (!succeeded || !sourceStillMatches)") < cd.find("if (!unchanged(previous))") <
         cd.find("if (!cleanInternalFlush)") <
         cd.rfind("onFlushFailure();") < cd.find("recordDraw(drawScope, drawProducer,") and
         "lastSuccessfulFlushMutationSerial = mutationSerial;" in ledger_flush_success and
         "lastSuccessfulFlushMutationSerial = 0;" in ledger_draw and
         "lastSuccessfulFlushMutationSerial = 0;" in ledger_begin and
         "lastSuccessfulFlushMutationSerial = 0;" in ledger_fail and
         "lastSuccessfulFlushMutationSerial = 0;" in ledger_end,
         "native Draw must preserve only successful internal texture Flush and reject all unsafe reentry")
    need("vtable[8]" in h and "vtable[9]" in h and "vtable[10]" in h and
         "vtable[11]" in h and "vtable[12]" in h and "vtable[13]" in h and
         "LostDevice_hk.enable().has_value()" in h and
         "ResetDevice_hk.enable().has_value()" in h,
         "all six lifecycle hooks must atomically install")
    return errors


def check_r30_stage_raw_wvp(renderer: str) -> list[str]:
    """R84's XYZRHW/fixedfn +TIME must stamp raw game c64 like R33 shader."""
    begin = renderer.find("        bool R30CaptureStagePhysicalSource(")
    end = renderer.find("        bool R30CaptureGoalPhysicalSource(", begin)
    if begin < 0 or end <= begin:
        return ["R30 physical +TIME source boundary missing"]
    stage = renderer[begin:end]
    evidence = (
        ("GetLastRawGameWvpWrite(", "original game c64 serial never sampled"),
        ("rawWriteSerial == 0 || rawDrawSerial == 0",
         "partial raw game WVP must clear both serials"),
        ("rawWriteSerial = 0;\n                rawDrawSerial = 0;",
         "unknown c64 generation must retain zero/zero fallback"),
        ("rawWriteSerial, rawDrawSerial};",
         "raw game c64 generation missing from R30 source stamp"),
        ("StageExtensionPhysical::IsValid(source)",
         "R30 must validate the stamped stage source"),
    )
    return [msg for needle, msg in evidence if needle not in stage]


def main_current_ledger(code: str, header: str) -> int:
    ledger_path = ROOT / "src/vr/game/hud_command_batch.hpp"
    if not ledger_path.is_file():
        print("DX9Ex +TIME D3DX FAIL: missing live command ledger")
        return 1
    ledger = ledger_path.read_text(encoding="utf-8")
    renderer = (ROOT / "src/vr/d3d9/stereo_renderer_r30.cpp").read_text(encoding="utf-8")
    errors = check_current_ledger(code, header, ledger)
    errors.extend(check_exact_goal_xyzrhw_plane(renderer, header))
    errors.extend(check_r30_stage_raw_wvp(renderer))
    if errors:
        print("DX9Ex +TIME D3DX FAIL: " + "; ".join(errors))
        return 1
    # Deliberately remove the *physical* raw-game WVP source stamp in
    # R30 only. R33 remaining intact cannot mask loss of XYZRHW stereo proof.
    capture_begin = renderer.find("        bool R30CaptureStagePhysicalSource(")
    capture_end = renderer.find("        bool R30CaptureGoalPhysicalSource(", capture_begin)
    captured = renderer[capture_begin:capture_end]
    for label, before, after in (
        ("missing-original-c64-capture", "GetLastRawGameWvpWrite(",
         "GetLastLiveStereoWvpWrite("),
        ("missing-partial-pair-clear",
         "rawWriteSerial == 0 || rawDrawSerial == 0", "false"),
        ("missing-right-eye-c64-stamp",
         "rawWriteSerial, rawDrawSerial};", "0, 0};"),
    ):
        changed = captured.replace(before, after, 1)
        mutant = renderer[:capture_begin] + changed + renderer[capture_end:]
        if changed == captured or not check_r30_stage_raw_wvp(mutant):
            print("DX9Ex +TIME R30 FAIL: source mutation not detected:", label)
            return 1
    # Every mutation must materially modify an existing live source, and
    # the validator must detect its exact missing safety condition. This
    # protects against blindly accepting a class name or a dead mock.
    mutations = [
        ("begin-does-not-clear", "ledger", "forget();\n            if (succeeded", "// forgot source;\n            if (succeeded"),
        ("begin-stale", "code", "HudBatch.onBeginResult(", "HudBatch.end(); // "),
        ("nested-begin-wipes", "ledger",
         "if (reentrantInvalidCall && active && exactSprite != nullptr &&",
         "if (false && active && exactSprite != nullptr &&"),
        ("device-error-promoted-to-nested", "code", "hr == D3DERR_INVALIDCALL", "FAILED(hr)"),
        ("foreign-begin-keeps-owner", "code",
         "else if (self && self == HudBatch.sprite)",
         "else if (self && false)"),
        ("foreign-nested-retains-owner", "ledger",
         "sprite == exactSprite)",
         "sprite != exactSprite)"),
        ("failed-begin-revocation-removed", "ledger",
         "            invalidate();\n        }\n\n        // CPU-side Draw",
         "            return;\n        }\n\n        // CPU-side Draw"),
        ("foreign-draw-steals-owner", "code", "ScopedExactProducerSemantic outgoingBatch(", "ScopedExactProducerSemantic wrongBatch("),
        ("foreign-batch-no-split", "code", "flushed = FlushTracked(self);", "flushed = false;"),
        ("mix-becomes-homogeneous", "ledger", "homogeneous = false;", "homogeneous = true;"),
        ("queue-invalid-owner-accepted", "ledger", "homogeneous = validQueue;", "homogeneous = true;"),
        ("queue-direct-mix-accepted", "ledger", "queued != drawQueued", "queued == drawQueued"),
        ("queue-node-mix-accepted", "ledger", "queueNode != drawQueueNode", "queueNode == drawQueueNode"),
        ("queue-epoch-mix-accepted", "ledger", "queueEpoch != drawQueueEpoch", "queueEpoch == drawQueueEpoch"),

        ("successful-draw-untracked", "ledger",
         "recordDraw(drawScope, drawProducer,\n                drawQueued, drawQueueNode, drawQueueEpoch);",
         "(void)drawScope; (void)drawProducer;"),
        ("texture-flush-stamp-lost", "ledger", "lastSuccessfulFlushMutationSerial = mutationSerial;", "lastSuccessfulFlushMutationSerial = 0;"),
        ("texture-flush-stamp-ignored", "ledger", "lastSuccessfulFlushMutationSerial == mutationSerial", "true"),
        ("texture-flush-promotes-source-switch", "ledger", "if (!succeeded || !sourceStillMatches)", "if (!succeeded)"),
        ("texture-flush-source-check-unused", "code",
         "sameSourceAfterNative, command.queued,", "true, command.queued,"),
        ("texture-flush-wrong-mutation", "ledger", "if (!unchanged(previous))", "if (false)"),
        ("texture-flush-draw-failure-promoted", "ledger", "if (!succeeded || !sourceStillMatches)", "if (!sourceStillMatches)"),

        ("failed-draw-keeps", "code", "HudBatch.completeNativeDraw(", "HudBatch.completeNativeUnsafeDraw("),

        ("flush-no-revoke", "code", "HudBatch.completeNativeFlush(submission, SUCCEEDED(hr));", "HudBatch.boundaryReady = true;"),

        ("flush-failure-retains", "ledger", "void onFlushFailure() noexcept\n        {\n            lastSuccessfulFlushMutationSerial = 0;\n            active = false;", "void onFlushFailure() noexcept\n        {\n            lastSuccessfulFlushMutationSerial = 0;\n            active = true;"),
        ("ledger-failure-retains", "ledger", "void onFlushFailure() noexcept\n        {\n            lastSuccessfulFlushMutationSerial = 0;\n            active = false;", "void onFlushFailure() noexcept\n        {\n            lastSuccessfulFlushMutationSerial = 0;\n            active = true;"),
        ("ledger-end-retains", "ledger", "void end() noexcept\n        {\n            lastSuccessfulFlushMutationSerial = 0;\n            active = false;", "void end() noexcept\n        {\n            lastSuccessfulFlushMutationSerial = 0;\n            active = true;"),
        ("reset-no-forget", "code", "HudBatch.invalidate();", "HudBatch.boundaryReady = true;"),
        ("reset-keeps-sprite", "ledger", "void invalidate() noexcept\n        {\n            end();\n            sprite = nullptr;", "void invalidate() noexcept\n        {\n            end();\n            sprite = exactSprite;"),
        ("missing-live-pointer", "code", "void* liveSprite = *Module::exe_ptr<void*>(0x55B218);", "void* liveSprite = HudBatch.sprite;"),
        ("wrong-live-owner", "code", "self, HudBatch.sprite, liveSprite", "self, HudBatch.sprite, self"),
        ("queue-exit-without-provenance", "code", "HudBatch.producer == CurrentRenderProducerToken()", "true"),
        ("queue-first-unowned", "code", "flushed = FlushTracked(firstQueueSprite);", "flushed = false;"),
        ("queue-first-direct-proof-lost", "code",
         "!HudBatch.queued && HudBatch.queueNode == nullptr &&", "true &&"),
        ("native-queue-node-context-lost", "code",
         "afterNative.queueNode == command.queueNode", "true"),
        ("native-queue-epoch-context-lost", "code",
         "afterNative.queueEpoch == command.queueEpoch", "true"),
        ("first-queue-predicate-not-direct", "header",
         "return knownResult && pendingBatchDirect;", "return knownResult;"),
        ("goal-transition-lost", "code", "HudBatch.boundaryReady = enteringStage || enteringGoal;", "HudBatch.boundaryReady = enteringStage;"),
        ("source-exit-no-flush", "code", "if (FlushTracked(sprite))", "if (false)"),
        ("shader-loses-goal-route", "code", "CanDeferD3DXQueueGoalBatch(", "CanDeferD3DXQueueNoneBatch("),
        ("post-draw-stage-no-boundary", "code", "if (exactStage && CanArmD3DXQueueStageAfterDraw(", "if (false && CanArmD3DXQueueStageAfterDraw("),
        ("flush-ignores-new-Begin", "ledger", "if (!sameGeneration(previous))", "if (false)"),
        ("flush-ignores-mutation", "ledger", "if (!unchanged(previous) || !succeeded)", "if (!succeeded)"),
        ("end-clears-reentrant-Begin", "code", "HudBatch.completeNativeEnd(submission);", "HudBatch.end();"),
        ("begin-clears-reentrant-Begin", "code", "if (HudBatch.generation == beforeBegin.generation)", "if (true)"),
        ("draw-mutation-not-counted", "ledger", "            touch();\n        }\n\n        void forget()", "            // no mutation counted\n        }\n\n        void forget()"),
        ("lost-retains-batch", "code", "InvalidateForDeviceLifecycle(ownsBatch);", "(void)ownsBatch;"),
    ]
    for name, source, before, after in mutations:
        orig = {"code": code, "ledger": ledger, "header": header}[source]
        modified = orig.replace(before, after, 1)
        if modified == orig:
            print("DX9Ex +TIME D3DX FAIL: mutation fixture missing: " + name)
            return 1
        c = modified if source == "code" else code
        l = modified if source == "ledger" else ledger
        h = modified if source == "header" else header
        mutated_errors = check_current_ledger(c, h, l)
        if source == "header":
            mutated_errors.extend(check_exact_goal_xyzrhw_plane(renderer, h))
        if not mutated_errors:
            print("DX9Ex +TIME D3DX FAIL: mutation was not detected: " + name)
            return 1
    for label, name, token in (
        ("stage-foreign-owner", "CanFlushD3DXDirectStageAtExit", "StageExtensionTime"),
        ("goal-foreign-owner", "CanFlushD3DXDirectGoalAtExit", "GoalTime020"),
        ("goal-progress-source", "CanFlushD3DXDirectGoalAtExit", "ResultProgress")):
        begin = header.index("inline constexpr bool " + name + "(")
        end = header.index("    static_assert(", begin)
        block = header[begin:end]
        changed = block.replace("pendingProducer == ProducerToken::" + token,
                                "pendingProducer == ProducerToken::None", 1)
        if changed == block or not check_current_ledger(code, header[:begin]+changed+header[end:], ledger):
            print("DX9Ex +TIME D3DX FAIL: exact-owner predicate mutation undetected: " + label)
            return 1
    print("DX9Ex +TIME/GOAL QUEST LEDGER PASS: real native lifecycle/physical owner, "
          + str(len(mutations)) + " destructive mutations, exact original XYZ/RHW contract")
    return 0


def main() -> int:
    code = SOURCE.read_text(encoding="utf-8")
    header = SEMANTICS.read_text(encoding="utf-8")
    # The live R84 game now calls Ledger::onBeginResult rather than the old
    # inline HudBatch.begin spelling. Dispatch by the actual installed ledger
    # type, so a source lifecycle fix cannot silently invoke the retired
    # pre-ledger verifier and skip all modern destructive mutations.
    if "inline static thread_local OutRunVR::HudCommandBatch::Ledger HudBatch{};" in code:
        return main_current_ledger(code, header)
    errors = check(code, header)
    renderer = (ROOT / "src/vr/d3d9/stereo_renderer_r30.cpp").read_text(encoding="utf-8")
    errors.extend(check_exact_goal_xyzrhw_plane(renderer, header))
    errors.extend(check_r30_stage_raw_wvp(renderer))
    if errors:
        print("DX9Ex +TIME D3DX FAIL: " + "; ".join(errors))
        return 1
    mutations = {
        "foreign-draw-loses-outgoing-gpu-owner":
            code.replace(
                "OutRunVR::GameSemantic::ScopedExactProducerSemantic outgoingBatch(\n"
                "                    outgoingScope, nullptr, true, outgoingProducer);",
                "// the foreign incoming producer now owns the old GPU Draw", 1),
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