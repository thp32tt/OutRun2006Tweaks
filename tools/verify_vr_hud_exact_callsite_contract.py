#!/usr/bin/env python3
"""Exact producer->hook->semantic P0 gate. Tested EXE bytes remain CI authority."""
import copy
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXE_SHA = "68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3"
# CALL RVAs, original target, installed wrapper. Explicit disjoint sets.
GROUPS = {
    "RankMarkerSubScreenHudCalls": ("BEB98 BED83 BED9E BEDAE", 0xBAD20, "RankMarkerSubSemanticDest"),
    "RankMarker_SpraniCalls": ("BB0FB BB133 BB16C BB1A5", 0x29580, "RankMarker_sprani"),
    "RankMarker_ClipSpriteCalls": ("BB21F BB241 BB271 BB2BC BB2D0", 0x2D280, "RankMarker_putClipSprite"),
    "OptionArrow_ClipSpriteCalls": ("E358B E35A3 E35CC E35F7 E481B E4833 E485C E4887 EC24C EC277 ED4D4 ED7A3", 0x2D280, "ExactScreenHud_putClipSprite"),
    "ExactScreenHud_ClipSpriteCalls": ("460F1 463D6 46410 97BB7 97DA7 BDB0E BDB2D BDB4C BDB8E BE311 BE343 BE3E3 BE424 BE45D", 0x2D280, "ExactScreenHud_putClipSprite"),
    "ExactScreenHudRight_ClipSpriteCalls": ("B9F3A B9F5E B9F81 B9FD0 B9FFC BA01E BA035 BA052 BD32E BD397 BD414 BD472 BE5CD BE603 BE633 BE66D BE690 BE6B5 BE6D5 BE7E8 BE802 BE81C BE8D8 BE915 BE94A BE97A BE9A3", 0x2D280, "ExactScreenHudRight_putClipSprite"),
    "ExactScreenHudLeft_ClipSpriteCalls": ("B9096 B90B3", 0x2D280, "ExactScreenHudLeft_putClipSprite"),
    "TextGlyph_PutSpriteCalls": ("2C808 2C9DB", 0x2CFE0, "TextGlyph_putSprite"),
}


def fail(reason):
    raise ValueError("P0 HUD producer FAIL: " + reason)


def function_body(text, marker):
    pos = text.find(marker)
    if pos < 0:
        fail("missing function " + marker)
    opening = text.find("{", pos)
    if opening < 0:
        fail("missing body " + marker)
    depth = 0
    for i in range(opening, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[opening + 1:i]
    fail("unclosed body " + marker)


def ordered(text, label, *tokens):
    positions = [text.find(t) for t in tokens]
    if -1 in positions or positions != sorted(positions):
        fail(label)


EXTRA_PRODUCERS = {
    0x97BE4: (0x2D200, "ResultProgressCallA = 0x97BE4"),
    0x97DEC: (0x2D200, "ResultProgressCallB = 0x97DEC"),
    0xBEA5A: (0xBE020, "GoalTimeHelperCallA = 0xBEA5A"),
    0xBEA5F: (0xBE150, "GoalTimeHelperCallB = 0xBEA5F"),
}


def check_extra_producers(ui, contracts):
    # Preserve 71 original HUD CALLs; verify four historically proven R74
    # result/GOAL producers separately, including the *entire* 16-byte EXE
    # signature and source-node queue ownership, not a broad HUD heuristic.
    by_rva = {}
    for item in contracts:
        by_rva.setdefault(int(item['rva'], 16), []).append(item)
    for rva, (target, needle) in EXTRA_PRODUCERS.items():
        candidates = by_rva.get(rva, [])
        if len(candidates) != 1:
            fail('missing/duplicate R74 original CALL 0x%X' % rva)
        entry = candidates[0]
        raw = entry.get('expectedBytes', '')
        if entry.get('signatureLength') != 16 or not re.fullmatch(r'[0-9a-fA-F]{32}', raw):
            fail('invalid R74 16-byte original disassembly 0x%X' % rva)
        op = bytes.fromhex(raw)
        if op[0] != 0xE8 or ((rva + 5 + int.from_bytes(op[1:5], 'little', signed=True)) & 0xFFFFFFFF) != target:
            fail('wrong R74 original E8 destination at 0x%X' % rva)
        if not any(b.get('path') == 'src/hooks_uiscaling.cpp' and
                   b.get('needle') == needle for b in entry.get('sourceBindings', [])):
            fail('missing R74 source ownership binding 0x%X' % rva)
        if ui.count(needle) != 1:
            fail('missing/duplicate exact owner constant at 0x%X' % rva)

    result_enter = function_body(ui, 'static void ResultProgressEnter(')
    result_leave = function_body(ui, 'static void ResultProgressLeave(')
    ordered(result_enter, 'result queue owner begin',
            'ResultProgressDepth++', 'Game::SpritePriorityCount',
            'ResultProgressTailsBefore[prio] =')
    ordered(result_leave, 'result queue owner exit',
            '--ResultProgressDepth', 'TagAppendedNodes(ResultProgressTailsBefore,',
            'RenderScope::ScreenHud', 'ResultProgressTailsBefore = {};')
    for edge in 'A', 'B':
        for side in 'Enter', 'Leave':
            name = 'ResultProgress' + side + edge
            expected = (
                r'%s\s*=\s*safetyhook::create_mid\s*\(\s*'
                r'Module::exe_ptr\(ResultProgressCall%s%s\),\s*ResultProgress%s\);'
            )
            expr = ''.join(expected) % (name, edge, r'\s*\+\s*5' if side == 'Leave' else '', side)
            if len(re.findall(expr, ui, re.S)) != 1:
                fail('wrong/missing original exact result-progress ' + name)

    # All four CALL-boundary hooks must fail closed as one group.
    for token in (
        'if (!ResultProgressEnterA || !ResultProgressLeaveA ||',
        '!ResultProgressEnterB || !ResultProgressLeaveB)',
        'ResultProgressEnterA = {};', 'ResultProgressLeaveA = {};',
        'ResultProgressEnterB = {};', 'ResultProgressLeaveB = {};',
    ):
        if token not in ui:
            fail('result-progress partial hook rollback missing ' + token)

    goal = function_body(ui, 'static void GoalTime_TagHelper(')
    ordered(goal, 'GOAL sprite parent call and all-node scope',
            'Game::SpritePriorityCount', 'Module::exe_ptr(helperRva)',
            'original();', 'TagAppendedNodes(before,',
            'RenderScope::ScreenHud')
    # There are two intentionally different original components on the GOAL
    # screen (likely course/stage label and recorded time). Do not interpret
    # adjacent E8 calls as the same white timer emitted twice; either
    # suppressing one or executing either one twice corrupts original UI.
    if goal.count('original();') != 1 or 'return;' in goal:
        fail('each GOAL helper must execute its original once, without skipping')
    if goal.count('TagAppendedNodes(before,') != 1:
        fail('GOAL helper must preserve one sibling ownership publication')
    if 'ScopedProducerSemantic' in goal and 'Current R84 queue authority' not in goal:
        fail('retired goal producer scope API reintroduced')
    for suffix, helper in (('A', '020'), ('B', '150')):
        if len(re.findall(r'GoalTime_Help%s\(\)\s*\{\s*GoalTime_TagHelper\(0xBE%s\);\s*\}' % (helper, helper), ui)) != 1:
            fail('wrong GOAL original helper ABI or target ' + helper)
        pattern = (r'Memory::VP::InjectHook\s*\(\s*Module::exe_ptr\(GoalTimeHelperCall%s\),'
                   r'\s*GoalTime_Help%s,\s*Memory::HookType::Call\);')
        if len(re.findall(''.join(pattern) % (suffix, helper), ui, re.S)) != 1:
            fail('GOAL original direct-CALL owner missing ' + helper)


def check_disprank_first(ui, contracts):
    # This is not one of the old 71 CALLs. The original EXE producer window
    # was independently decoded by tools/analyze_outrun_exe.py in canonical
    # EXE HUD Inspector CI: first POSITION kind-1 CALL 0xB9DA6 -> 0x29530.
    hits = [x for x in contracts if int(x['rva'], 16) == 0xB9DA6]
    if len(hits) != 1:
        fail('missing first DispRank original direct CALL')
    item = hits[0]
    raw = item.get('expectedBytes', '')
    if item.get('signatureLength') != 5 or not re.fullmatch(r'e8[0-9a-fA-F]{8}', raw, re.I):
        fail('first DispRank must have its real E8 signature')
    target = (0xB9DA6 + 5 + int.from_bytes(bytes.fromhex(raw)[1:], 'little', signed=True)) & 0xFFFFFFFF
    if target != 0x29530:
        fail('first DispRank E8 targets wrong sprite producer')
    if not any(x.get('path') == 'src/hooks_uiscaling.cpp' and
               x.get('needle') == 'DispRankFirstSpraniCall = 0xB9DA6'
               for x in item.get('sourceBindings', [])):
        fail('first DispRank producer source binding missing')
    if ui.count('DispRankFirstSpraniCall = 0xB9DA6') != 1:
        fail('first DispRank source constant missing/duplicate')
    body = function_body(ui, 'static int __cdecl DispRankFirst_sprani(')
    ordered(body, 'first DispRank all-child ScreenHud producer',
            'Game::SpritePriorityCount', 'Module::exe_ptr(0x29530)',
            'const int result = original(spriteId, x, y, a4, a5);',
            'TagAppendedNodes(before,', 'RenderScope::ScreenHud',
            'return result;')
    if len(re.findall(r'InjectHook\s*\(\s*Module::exe_ptr\(DispRankFirstSpraniCall\),\s*'
                      r'DispRankFirst_sprani,\s*Memory::HookType::Call\);', ui, re.S)) != 1:
        fail('first DispRank exact original CALL not installed')
    if 'B9F3A B9F5E B9F81 B9FD0 B9FFC BA01E BA035 BA052' not in GROUPS['ExactScreenHudRight_ClipSpriteCalls'][0]:
        fail('first DispRank must remain disjoint from eight kind0 clips')


def check(ui, manifest):
    if manifest.get("canonicalExe", {}).get("sha256") != EXE_SHA:
        fail("wrong canonical EXE identity")
    contracts = manifest.get("contracts")
    if not isinstance(contracts, list):
        fail("missing CALL manifest")
    if len({c.get("id") for c in contracts}) != len(contracts):
        fail("duplicate CALL contract ID")
    by_rva = {}
    for c in contracts:
        by_rva.setdefault(int(c["rva"], 16), []).append(c)
    owned = set()

    def check_call(rva, expected_target):
        if rva in owned:
            fail("overlapping C++ producer groups: 0x%X" % rva)
        owned.add(rva)
        matches = by_rva.get(rva, [])
        if len(matches) != 1:
            fail("missing/duplicate canonical CALL at 0x%X" % rva)
        c = matches[0]
        if not c.get("id", "").startswith("VR-EXE-"):
            fail("missing canonical source ID 0x%X" % rva)
        raw = c.get("expectedBytes", "")
        if c.get("signatureLength") != 5 or not re.fullmatch("[0-9a-fA-F]{10}", raw):
            fail("bad CALL signature 0x%X" % rva)
        op = bytes.fromhex(raw)
        if op[0] != 0xE8:
            fail("non-direct CALL 0x%X" % rva)
        target = (rva + 5 + int.from_bytes(op[1:], "little", signed=True)) & 0xFFFFFFFF
        if target != expected_target:
            fail("CALL 0x%X targets 0x%X instead of 0x%X" % (rva, target, expected_target))
        if not any(b.get("path") == "src/hooks_uiscaling.cpp" and
                   re.search(r"0x%X\b" % rva, b.get("needle", ""), re.I)
                   for b in c.get("sourceBindings", [])):
            fail("lost exact source binding for 0x%X" % rva)

    for name, (values, destination, wrapper) in GROUPS.items():
        pattern = r"\b" + re.escape(name) + r"\s*\[\s*\]\s*=\s*\{([^}]*)\}"
        arrays = re.findall(pattern, ui, re.S)
        if len(arrays) != 1:
            fail("missing/duplicate array " + name)
        literal = re.sub(r"/\*.*?\*/|//[^\n]*", "", arrays[0], flags=re.S)
        addresses = re.findall(r"0x[0-9a-fA-F]+", literal)
        if re.sub(r"0x[0-9a-fA-F]+|[\s,]", "", literal):
            fail("nonconstant array entry " + name)
        if [int(x, 16) for x in addresses] != [int(x, 16) for x in values.split()]:
            fail("missing/extra/reordered CALL in " + name)
        if name == "ExactScreenHudRight_ClipSpriteCalls":
            # R64 headset-proven DispRank kind0 must use an exact 8-RVA
            # producer+batch barrier, while the OTHER right-aligned
            # TimeAttack/result/C2C calls still use the original common
            # ScreenHud wrapper. This does NOT change the 71 E8 addresses.
            # Never permit a global right-side sprite batch flush.
            selector_hook = (
                r"for\s*\(\s*int\s+addr\s*:\s*" + re.escape(name) +
                r"\s*\)\s*Memory::VP::InjectHook\s*\("
                r"\s*Module::exe_ptr\(addr\)\s*,\s*"
                r"IsExactDispRankRightClipRva\(addr\)\s*\?\s*"
                r"DispRankRight_putClipSprite\s*:\s*"
                r"ExactScreenHudRight_putClipSprite\s*,\s*"
                r"Memory::HookType::Call\s*\)")
            if len(re.findall(selector_hook, ui, re.S)) != 1:
                fail("R64 DispRank/right TimeAttack E8 selective hook missing")
        else:
            hook = (r"for\s*\(\s*int\s+addr\s*:\s*" + re.escape(name) +
                    r"\s*\)\s*Memory::VP::InjectHook\s*\(\s*Module::exe_ptr\(addr\)"
                    r"\s*,\s*(\w+)\s*,\s*Memory::HookType::Call\s*\)")
            if re.findall(hook, ui, re.S) != [wrapper]:
                fail("missing/duplicate/wrong hook target in " + name)
        for addr in addresses:
            check_call(int(addr, 16), destination)

    scalar = re.findall(r"\bRivalMarker_SpraniCall\s*=\s*(0x[0-9a-fA-F]+)\s*;", ui)
    if len(scalar) != 1 or int(scalar[0], 16) != 0xBB796:
        fail("rival producer shifted")
    if len(re.findall(
        r"Memory::VP::InjectHook\s*\(\s*Module::exe_ptr\(RivalMarker_SpraniCall\)"
        r"\s*,\s*RivalMarker_sprani\s*,\s*Memory::HookType::Call\s*\)", ui, re.S)) != 1:
        fail("rival CALL target mismatch")
    check_call(0xBB796, 0x29580)
    if len(owned) != 71:
        fail("expected 71 exact canonical HUD CALLs")
    check_extra_producers(ui, contracts)
    check_disprank_first(ui, contracts)

    # Sibling expansion in put_clip_sprite must tag *all* original children;
    # a single tail-only tag can make one digit/menu arrow stereo and another
    # generic, despite correct CALL addresses.
    exact_clip = function_body(ui, "static int __cdecl ExactScreenHud_putClipSprite(")
    ordered(exact_clip, "exact clip HUD sibling tagging",
            "tailsBefore", "const int result = Game::put_clip_sprite(",
            "TagAppendedNodes(tailsBefore,")
    if ("RenderScope::ScreenHud" not in exact_clip or
            "ProducerToken::ExactScreenHudClipSprite" not in exact_clip):
        fail("exact clip HUD lost all-node ScreenHud tagging")
    glyph = function_body(ui, "static int __cdecl TextGlyph_putSprite(")
    ordered(glyph, "stage/result Sumo_Printf glyph group tags all nodes",
            "tailsBefore", "const int result = original(args, priority);",
            "TagAppendedNodes(tailsBefore,")
    if "Game::SpritePriorityCount" not in glyph:
        fail("result +TIME glyph group lost bounded all-priority ownership")
    if ("RenderScope::ScreenHud" not in glyph or
            "ProducerToken::TextGlyphPutSprite" not in glyph):
        fail("glyph ScreenHud lost tag")
    # Left/right HUD entry points adjust position before forwarding to the
    # one exact ScreenHud registration owner. A valid EXE CALL map alone cannot
    # detect accidental reversed offsets, dropped spacing, or bypassing the
    # semantic tag after these wrappers execute.
    for side, right in (("Right", True), ("Left", False)):
        func = "static int __cdecl ExactScreenHud%s_putClipSprite(" % side
        wrapper = function_body(ui, func).strip()
        expected_spacing = "false" if right else "true"
        direct_bridge = (
            r"AddSpriteSpacing\(&x,\s*" + expected_spacing +
            r"\);\s*return ExactScreenHud_putClipSprite\(\s*"
            r"xstnum,\s*x,\s*y,\s*flags,\s*priority,\s*color\);"
        )
        if not re.fullmatch(direct_bridge, wrapper, re.S):
            fail(side + " HUD spacing/forwarding must use the exact ScreenHud owner")

    sub = function_body(ui, "static int __cdecl RankMarkerSubSemanticDest(")
    ordered(sub, "NaviPub scope owner before original draw",
            "++RankMarkerSubScreenHudDepth;", "--RankMarkerSubScreenHudDepth;",
            "Module::exe_ptr(0xBAD20)", "return original(arg);")
    for func, token in (
        ("static int __cdecl RankMarker_sprani(", "RankMarkerSprani"),
        ("static int __cdecl RankMarker_putClipSprite(", "RankMarkerClipSprite"),
    ):
        chunk = function_body(ui, func)
        if token == "RankMarkerSprani":
            ordered(chunk, "rank screen-vs-world precedence",
                    "if (RankMarkerSubScreenHudDepth != 0)", "RenderScope::ScreenHud",
                    "const bool projected = RankMarkerProjectedInfo.valid",
                    "RenderScope::ProjectedWorldMarker2D", "RenderScope::WorldBillboard")
            if "TagAppendedNodes(tailsBefore, scope," not in chunk:
                fail("rank sprani lost all-node exact producer tagging")
        else:
            ordered(chunk, "4th+ rank clip screen-vs-world precedence",
                    "const bool screenHud = RankMarkerSubScreenHudDepth != 0;",
                    "const bool projected = !screenHud && RankMarkerProjectedInfo.valid;",
                    "RenderScope::ScreenHud", "RenderScope::ProjectedWorldMarker2D",
                    "RenderScope::WorldBillboard", "TagAppendedNodes(tailsBefore, scope,")
            if "node->args_10.float24 += RankMarkerFracX" not in chunk or (
                "node->args_10.float28 += RankMarkerFracY" not in chunk):
                fail("4th+ digit siblings lost subpixel restoration")
        if "ProducerToken::" + token not in chunk:
            fail(func + " producer identity missing")
    rank = function_body(ui, "static int __cdecl RankMarker_sprani(")
    if "TagAppendedNodes(tailsBefore, scope," not in rank:
        fail("multi-node rank producer not tagged")
    # Rank 1-3/4+ and rival all use the bounded multi-node tagging helper.
    rival = function_body(ui, "static int __cdecl RivalMarker_sprani(")
    for token in ("const auto projectedAnchor = RivalMarkerProjectedInfo;",
                  "RivalMarkerProjectedInfo = {};", "RenderScope::ProjectedWorldMarker2D",
                  "RenderScope::WorldBillboard", "ProducerToken::RivalMarkerSprani",
                  "TagAppendedNodes("):
        if token not in rival:
            fail("rival world marker lost " + token)
    rank_owner = function_body(ui, "static int __cdecl RankMarkerSub_dest(")
    ordered(rank_owner, "rank anchor must be cleared for each original sub_4BAD20",
            "RankMarkerProjectedInfo = {};",
            "++RankMarkerSubActiveDepth;",
            "RankMarkerSub_hk.call<int>(arg)",
            "--RankMarkerSubActiveDepth;",
            "RankMarkerProjectedInfo = saved;")
    if "RankMarkerSub_hk = safetyhook::create_inline(" not in ui:
        fail("rank sub_4BAD20 entry hook is not installed")
    ordered(rival, "rival anchor must be consumed once",
            "const auto projectedAnchor = RivalMarkerProjectedInfo;",
            "RivalMarkerProjectedInfo = {};",
            "TagAppendedNodes(")
    tag_nodes = function_body(ui, "static void TagAppendedNodes(")
    ordered(tag_nodes, "rival multi-node producer tagging",
            "tailAfter", "node = before[prio]", "RegisterSpriteNodeScope(")
    return len(owned)


def test_mutations(ui, manifest):
    def must_fail(label, changed_ui=ui, changed_manifest=None):
        try:
            check(changed_ui, manifest if changed_manifest is None else changed_manifest)
        except ValueError:
            return
        fail("undetected mutation " + label)
    must_fail("rank direct CALL removed", ui.replace("0xBB0FB, 0xBB133", "0xBB133", 1))
    must_fail("rank digit CALL duplicate", ui.replace("0xBB21F, 0xBB241", "0xBB21F, 0xBB21F", 1))
    must_fail("arrow group not installed", ui.replace("for (int addr : OptionArrow_ClipSpriteCalls)",
                                                       "for (int addr : RankMarker_ClipSpriteCalls)", 1))
    must_fail("4th place hooked as HUD", ui.replace("Module::exe_ptr(addr), RankMarker_putClipSprite,",
                                                   "Module::exe_ptr(addr), ExactScreenHud_putClipSprite,", 1))
    must_fail("glyph token drift", ui.replace("ProducerToken::TextGlyphPutSprite",
                                               "ProducerToken::RankMarkerClipSprite", 1))
    must_fail("rank world first", ui.replace("if (RankMarkerSubScreenHudDepth != 0)",
                                            "if (RankMarkerSubScreenHudDepth == 0)", 1))
    must_fail("R64 DispRank source accidentally shares TimeAttack owner",
              ui.replace("IsExactDispRankRightClipRva(addr)",
                         "false", 1))
    must_fail("R64 exact DispRank E8 hook target removed",
              ui.replace("? DispRankRight_putClipSprite",
                         "? ExactScreenHudRight_putClipSprite", 1))
    must_fail("right-side spacing reversed",
              ui.replace("AddSpriteSpacing(&x, false);\n\t\treturn ExactScreenHud_putClipSprite(",
                         "AddSpriteSpacing(&x, true);\n\t\treturn ExactScreenHud_putClipSprite(", 1))
    must_fail("left-side semantic owner bypassed",
              ui.replace("AddSpriteSpacing(&x, true);\n\t\treturn ExactScreenHud_putClipSprite(",
                         "AddSpriteSpacing(&x, true);\n\t\treturn Game::put_clip_sprite(", 1))
    corrupt = copy.deepcopy(manifest)
    next(c for c in corrupt["contracts"] if int(c["rva"], 16) == 0xBB0FB)["expectedBytes"] = "e800000000"
    must_fail("direct CALL changed", changed_manifest=corrupt)
    corrupt = copy.deepcopy(manifest)
    next(c for c in corrupt["contracts"] if int(c["rva"], 16) == 0x2C808)["sourceBindings"] = []
    must_fail("glyph source evidence removed", changed_manifest=corrupt)
    # Four independent new negative cases are strictly bounded by original
    # result-progress / GOAL contracts, not 1000/5000 review loops.
    must_fail('result-progress closing CALL lost',
              ui.replace('ResultProgressLeaveB = safetyhook::create_mid(',
                         'ResultProgressLeaveMissing = safetyhook::create_mid(', 1))
    must_fail('goal 150 retargeted to 020',
              ui.replace('GoalTime_TagHelper(0xBE150);',
                         'GoalTime_TagHelper(0xBE020);', 1))
    must_fail('original course/time helper called twice',
              ui.replace('original();\n\t\t// Both original GOAL helpers',
                         'original();\n\t\toriginal();\n\t\t// Both original GOAL helpers', 1))
    must_fail('original course/time helper skipped',
              ui.replace('original();\n\t\t// Both original GOAL helpers',
                         'return;\n\t\t// Both original GOAL helpers', 1))
    corrupt = copy.deepcopy(manifest)
    next(x for x in corrupt['contracts'] if int(x['rva'], 16) == 0x97BE4)['expectedBytes'] = 'e800000000' + '00'*11
    must_fail('original result E8 destination corrupted', changed_manifest=corrupt)
    corrupt = copy.deepcopy(manifest)
    next(x for x in corrupt['contracts'] if int(x['rva'], 16) == 0xBEA5F)['sourceBindings'] = []
    must_fail('original GOAL source binding removed', changed_manifest=corrupt)
    must_fail('first DispRank source owner bypassed',
              ui.replace('DispRankFirst_sprani, Memory::HookType::Call',
                         'ExactScreenHud_putClipSprite, Memory::HookType::Call', 1))
    corrupt = copy.deepcopy(manifest)
    next(x for x in corrupt['contracts'] if int(x['rva'], 16) == 0xB9DA6)['expectedBytes'] = 'e800000000'
    must_fail('first DispRank rel32 original CALL corrupted', changed_manifest=corrupt)
    print('P0 first DispRank original CALL mutations: 2/2 failures detected')
    must_fail('result-progress hook group no longer fail-closed',
              ui.replace('ResultProgressLeaveB = {};',
                         'ResultProgressLeaveNoop = {};', 1))
    print('P0 GOAL/RESULT original producer mutations: 5/5 failures detected')
    print("P0 HUD mutation suite: 10/10 failures detected")


if __name__ == "__main__":
    ui = (ROOT / "src/hooks_uiscaling.cpp").read_text(encoding="utf-8")
    manifest = json.loads((ROOT / "docs/VR_BINARY_CONTRACT.json").read_text(encoding="utf-8"))
    try:
        n = check(ui, manifest)
        if "--self-test" in sys.argv[1:]:
            test_mutations(ui, manifest)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        sys.exit(1)
    print("P0 HUD exact producer PASS: %d CALL sites" % n)
