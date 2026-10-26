#!/usr/bin/env python3
"""Installed GOAL 0-99/full-result source admission + negative mutation gate.
Does not simulate GPU or claim Quest3 stereo correctness.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
src = (root/"src/hooks_uiscaling.cpp").read_text(encoding="utf-8")
hdr = (root/"src/vr/game/goal_progress_source_admission.hpp").read_text(encoding="utf-8")
def body(a,b):
    start=src.index(a)
    end=src.index(b,start+len(a))
    return src[start:end]
inner=body("static void ResultProgressEnter(safetyhook::Context&)", "static void ResultProgressLeave(safetyhook::Context&)")
leave=body("static void ResultProgressLeave(safetyhook::Context&)", "using ResultProgressFullParentFn")
parent=body("static bool __cdecl ResultProgressFullParent()", "inline static SafetyHookMid StageExtensionEnterHooks")
tests=[
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
    ("original installed E8s preserved",
        "Module::exe_ptr(ResultProgressCallA), ResultProgressEnter" in src and
        "Module::exe_ptr(ResultProgressCallB), ResultProgressEnter" in src and
        "ResultProgressFullParent, Memory::HookType::Call" in src),
]
for name,good in tests:
    if not good:
        raise SystemExit("FAIL: "+name)
print("PASS: real GOAL inner/full E8 entry, native drain, queue epoch and exit admission")
