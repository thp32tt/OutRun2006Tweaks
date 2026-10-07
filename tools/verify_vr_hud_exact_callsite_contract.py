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

    for func, token in (
        ("static int __cdecl ExactScreenHud_putClipSprite(", "ExactScreenHudClipSprite"),
        ("static int __cdecl TextGlyph_putSprite(", "TextGlyphPutSprite"),
    ):
        chunk = function_body(ui, func)
        ordered(chunk, func + " publishes before original draw",
                "tailBefore", "const int result = ", "if (node && node != tailBefore)",
                "RegisterSpriteNodeScope(")
        if "RenderScope::ScreenHud" not in chunk or "ProducerToken::" + token not in chunk:
            fail(func + " lost screen-HUD producer tag")
    sub = function_body(ui, "static int __cdecl RankMarkerSubSemanticDest(")
    ordered(sub, "NaviPub scope owner before original draw",
            "++RankMarkerSubScreenHudDepth;", "--RankMarkerSubScreenHudDepth;",
            "Module::exe_ptr(0xBAD20)", "return original(arg);")
    for func, token in (
        ("static int __cdecl RankMarker_sprani(", "RankMarkerSprani"),
        ("static int __cdecl RankMarker_putClipSprite(", "RankMarkerClipSprite"),
    ):
        chunk = function_body(ui, func)
        ordered(chunk, "rank screen-vs-world precedence",
                "if (RankMarkerSubScreenHudDepth != 0)", "RenderScope::ScreenHud",
                "const bool projected = RankMarkerProjectedInfo.valid",
                "RenderScope::ProjectedWorldMarker2D", "RenderScope::WorldBillboard")
        if "ProducerToken::" + token not in chunk or "RegisterSpriteNodeScope(" not in chunk:
            fail(func + " marker registration missing")
    # Rival's actual producer uses a bounded multi-node tagging helper,
    # unlike the single-node rank wrappers. Guard this real ownership path.
    rival = function_body(ui, "static int __cdecl RivalMarker_sprani(")
    for token in ("RivalMarkerProjectedInfo.valid", "RenderScope::ProjectedWorldMarker2D",
                  "RenderScope::WorldBillboard", "ProducerToken::RivalMarkerSprani",
                  "TagAppendedNodes("):
        if token not in rival:
            fail("rival world marker lost " + token)
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
    corrupt = copy.deepcopy(manifest)
    next(c for c in corrupt["contracts"] if int(c["rva"], 16) == 0xBB0FB)["expectedBytes"] = "e800000000"
    must_fail("direct CALL changed", changed_manifest=corrupt)
    corrupt = copy.deepcopy(manifest)
    next(c for c in corrupt["contracts"] if int(c["rva"], 16) == 0x2C808)["sourceBindings"] = []
    must_fail("glyph source evidence removed", changed_manifest=corrupt)
    print("P0 HUD mutation suite: 8/8 failures detected")


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
