#!/usr/bin/env python3
"""Installed GOAL 0-99/full-result source admission + negative mutation gate.
Does not simulate GPU or claim Quest3 stereo correctness.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
src = (root/"src/hooks_uiscaling.cpp").read_text(encoding="utf-8")
hdr = (root/"src/vr/game/goal_progress_source_admission.hpp").read_text(encoding="utf-8")
renderer = (root/"src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp").read_text(encoding="utf-8")
def body(a,b):
    start=src.index(a)
    end=src.index(b,start+len(a))
    return src[start:end]
inner=body("static void ResultProgressEnter(safetyhook::Context&)", "static void ResultProgressLeave(safetyhook::Context&)")
leave=body("static void ResultProgressLeave(safetyhook::Context&)", "using ResultProgressFullParentFn")
parent=body("static bool __cdecl ResultProgressFullParent()", "inline static SafetyHookMid StageExtensionEnterHooks")
goal_time=body("static void GoalTime_TagHelper(int helperRva)", "static void __cdecl GoalTime_Help020()")
b9200=body("static void __cdecl ResultTextB9200_dest(", "// REA-proven original graph parents")
def goal_snapshot_guard(code: str) -> bool:
    """Old D3DX producers must finish BEFORE GOAL takes its queue boundary."""
    needles = [
        "FlushD3DXBeforeDirectGoalSource();",
        "ResultProgressAdmittedAfterDrain = ResultProgressAdmission.mayPublish(",
        "if (ResultProgressAdmittedAfterDrain)",
        "ResultProgressEntrySerial =\n",
        "ResultProgressRootsBefore[prio] = root;",
        "ResultProgressTailsBefore[prio] = root ? root->tail_4 : nullptr;",
        "ResultProgressDirectDrawOwner.emplace(",
    ]
    offsets = [code.find(needle) for needle in needles]
    return all(i >= 0 for i in offsets) and offsets == sorted(offsets)

tests=[
    ("GOAL inner post-drain producer queue ownership",
        goal_snapshot_guard(inner)),
    ("reject unadmitted snapshot mutation",
        not goal_snapshot_guard(inner.replace(
            "if (ResultProgressAdmittedAfterDrain)", "if (true)", 1))),
    ("reject missing old-owner Flush mutation",
        not goal_snapshot_guard(inner.replace(
            "FlushD3DXBeforeDirectGoalSource();", "/* no flush */", 1))),
    ("reject missing live tail boundary mutation",
        not goal_snapshot_guard(inner.replace(
            "ResultProgressTailsBefore[prio] = root ? root->tail_4 : nullptr;",
            "/* stale old tail */", 1))),
    ("true native inner enter admission", "ResultProgressAdmission = {" in inner and
        "ResultProgressAdmission.mayBeginDirect()" in inner),
    ("inner pre-drain recheck",inner.index("FlushD3DXBeforeDirectGoalSource();") <
        inner.index("ResultProgressAdmittedAfterDrain = ResultProgressAdmission.mayPublish(") <
        inner.index("ResultProgressDirectDrawOwner.emplace(")),
    ("inner source exit guard",leave.index("const bool admitted = ResultProgressAdmittedAfterDrain &&") <
        leave.index("if (admitted)") < leave.index("TagAppendedNodes(ResultProgressTailsBefore")),
    ("inner exact native exit flush guarded",leave.index("if (admitted)") <
        leave.index("FlushD3DXAtDirectGoalSourceExit();") <
        leave.index("ResultProgressDirectDrawOwner.reset();")),
    ("inner full lifetime cleanup","ResultProgressAdmission = {};" in leave and
        "ResultProgressAdmittedAfterDrain = false;" in leave),
    ("full parent old batch flush before admission",parent.index("FlushD3DXBeforeDirectGoalSource();") <
        parent.index("if (!parentAdmission.mayPublish(") <
        parent.index("std::array<SpriteNode*")),
    ("full parent native original call once per path", "return original();" in parent and
        "const bool result = original();" in parent),
    ("full graph publication guarded",parent.index("const bool parentAdmittedAtExit") <
        parent.index("if (parentAdmittedAtExit)") <
        parent.index("TagAppendedNodes(before")),
    ("queue negative constexpr", "static_assert(!PreSourceFlushReenter());" in hdr and
        "static_assert(!InsideParentQueueReenter());" in hdr),
    ("reject epoch mutation", "queueEpoch == queueEpochAtEntry" in hdr),
    ("detailed GOAL percent source telemetry",
        "VR TRACE GOAL_PERCENT SOURCE ENTRY:" in inner and
        "VR TRACE GOAL_PERCENT SOURCE EXIT:" in leave and
        "entrySerial={}" in leave and "changedPriorities={}" in leave),
    ("detailed +TIME/GOAL physical telemetry",
        "VR TRACE RESULT PHYSICAL PRE:" in renderer and
        "VR TRACE RESULT PHYSICAL EYES:" in renderer and
        '"PLUS_TIME"' in renderer and '"GOAL_PERCENT"' in renderer and
        "projHashRaw=0x{:016X}" in renderer and
        "tex0=0x{:X} tex={}x{}" in renderer and
        "rightRt=0x{:X}" in renderer),
    ("GOAL time helper post-drain admission",
        "const OutRunVR::GoalProgress::SourceAdmission admission{" in goal_time and
        goal_time.index("FlushD3DXBeforeDirectGoalSource();") <
        goal_time.index("const bool admittedAfterDrain = admission.mayPublish(") <
        goal_time.index("SpriteNodeSemanticNextSerial.load(") <
        goal_time.index("ScopedExactProducerSemantic owner(") <
        goal_time.index("original(); // exact original helper once") and
        "if (!admission.mayBeginDirect())" in goal_time and
        "action=NATIVE_ORIGINAL_ONCE" in goal_time and
        "VR TRACE GOAL_TIME SOURCE:" in goal_time),
    ("GOAL time helper exit admission",
        "admittedAtExit = admission.mayPublish(" in goal_time and
        goal_time.index("admittedAtExit = admission.mayPublish(") <
        goal_time.index("TagAppendedNodes(before") <
        goal_time.index("FlushD3DXAtDirectGoalSourceExit();")),
    ("B9200 GOAL/TIMEUP/RESULT presentation symmetry",
        "ResultPresentationState()" in b9200 and
        "*Game::current_mode == GameState::STATE_GOAL" not in b9200),
    ("B9200 post-drain exact parent admission",
        "const OutRunVR::GoalProgress::SourceAdmission admission{" in b9200 and
        b9200.index("FlushD3DXBeforeDirectGoalSource();") <
        b9200.index("const bool admittedAfterDrain = admission.mayPublish(") <
        b9200.index("ScopedExactProducerSemantic owner(") and
        "VR TRACE GOAL TEXT ADMISSION:" in b9200 and
        "action=NATIVE_ORIGINAL_ONCE" in b9200),
    ("B9200 exit admission before exact flush",
        "admittedAtExit = admission.mayPublish(" in b9200 and
        b9200.index("admittedAtExit = admission.mayPublish(") <
        b9200.index("FlushD3DXAtDirectGoalSourceExit();")),
    ("original installed E8s preserved",
        "Module::exe_ptr(ResultProgressCallA), ResultProgressEnter" in src and
        "Module::exe_ptr(ResultProgressCallB), ResultProgressEnter" in src and
        "ResultProgressFullParent, Memory::HookType::Call" in src),
]
for name,good in tests:
    if not good:
        raise SystemExit("FAIL: "+name)
# Destructive controls: removing either post-drain/exit admission from the
# direct time/text helpers must fail the source contract above.
assert goal_time.count("admission.mayPublish(") >= 2
assert b9200.count("admission.mayPublish(") >= 2
assert "if (Settings::VREnabled)\n            goalDirectDrawOwner.emplace" not in goal_time
# Destructive state regression: a GOAL-only B9200 gate would recreate the
# observed TIMEUP/result-animation ownership hole while the other result
# producers still accept the complete presentation lifetime.
goal_only = b9200.replace(
    "ResultPresentationState()",
    "Game::current_mode && *Game::current_mode == GameState::STATE_GOAL", 1)
assert "ResultPresentationState()" not in goal_only.split(
    "const bool exactGoalParent =", 1)[1].split(";", 1)[0]
assert "*Game::current_mode == GameState::STATE_GOAL" in goal_only
print("PASS: real GOAL inner/full/time/B9200 entry, GOAL-TIMEUP-RESULT state symmetry, native drain, queue epoch and exit admission")
