#!/usr/bin/env python3
"""Guard ABC C isolated GOAL replaced-empty-root single-child experiment.
Only source/static verification; Quest HMD evidence still required.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
src = (root / "src/hooks_uiscaling.cpp").read_text(encoding="utf-8")
head = (root / "src/vr/game/sprite_queue_tail_proof.hpp").read_text(encoding="utf-8")
flow = (root / ".github/workflows/vr-dx9ex-official-focus-test.yml").read_text(encoding="utf-8")
p = src[src.index("static bool __cdecl ResultProgressFullParent()"):
        src.index("inline static SafetyHookMid StageExtensionEnterHooks")]
require = [
 ("original() exactly once admitted",p.count("const bool result = original();") == 1),
 ("protected original E8", "Module::exe_ptr(ResultProgressFullParentTarget)" in p),
 ("no broad queue tags",p.count("TagAppendedNodes(before,")==1),
 ("epoch-admitted only",p.index("if (parentAdmittedAtExit)")<p.index("recoveredSingleChildren")),
 ("source-root empty proof", "emptyBefore[p] = root && before[p] == root &&" in p),
 ("one bounded child proof", "FirstVerifiedRebuiltEmptySingleChild(" in p),
 ("single node scope", "RegisterSpriteNodeScope(" in p and "onlyChild," in p),
 ("nested exact serial", "nullptr, entrySerial);" in p),
 ("no general fallback",src.count("FirstVerifiedRebuiltEmptySingleChild(")==1),
 ("const-expr guard","static_assert(SingleChildOwnerProof()" in head),
 ("bounded rebuilt-root diagnostic",
     "CountVerifiedRebuiltEmptyChildren(" in head and
     "static_assert(ChildCountDiagnosticProof()" in head and
     "VR ABC C GOAL REBUILT EMPTY ROOT REJECTED:" in p and
     "action=KEEP_NATIVE_UNOWNED" in p),
 ("diagnostic never broadens ownership",
     p.count("RegisterSpriteNodeScope(") == 1 and
     p.count("FirstVerifiedRebuiltEmptySingleChild(") == 1),
 ("only single terminal child","currentRoot->next_0 == newTail &&" in head and
                                "newTail->next_0 == nullptr" in head),
 ("not old reused root","currentRoot == oldRoot" in head and "oldTail != oldRoot" in head),
 ("not missing first-write evidence","!wasEmptyAtEntry" in head),
 ("TEST/DEBUG both deliver", "foreach ($mode in @('TEST','DEBUG'))" in flow),
 ("variant strict write", 'Set-Content "$dir/DX9EX_VARIANT.txt" "variant=$variant" -Encoding ascii' in flow),
 ("no additional metadata in variant", 'variant=$variant; abc=C' not in flow),
 ("variant line count and exact parser guard", '$variantLines.Count -ne 1' in flow and
                                            '$parsedVariant -cne $variant' in flow),
 ("build provenance metadata separate", 'Set-Content "$dir/FOCUS_BUILD.txt"' in flow),
 ("zip start batch preserved","START_HERE.cmd" in flow and "Run-FocusOfficialTest.ps1" in flow),
]
for desc, good in require:
    if not good:
        raise SystemExit("ABC-C GOAL VERIFY FAIL: "+desc)
print("ABC-C GOAL source provenance/one-node safe subset PASS; Quest UNTESTED")
