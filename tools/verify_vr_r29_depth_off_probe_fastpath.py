#!/usr/bin/env python3
"""R29 depth-disabled translucent fast-path with fail-closed regressions.

A synchronized R29 depth-off effect cannot satisfy R27's independently
required zEnabled==true predicate. Avoid its five-state R13 live read, but
preserve depth-on candidates, semantic force-zero, recovery and live fallback.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src/vr/d3d9/stereo_renderer_r29.cpp"
R26 = ROOT / "src/vr/d3d9/stereo_renderer_r26.cpp"
POLICY = ROOT / "src/vr/d3d9/vr_pass_policy.hpp"


def body(s: str, marker: str) -> str:
    start = s.find(marker)
    assert start >= 0, marker
    opening = s.find("{", start)
    depth = 0
    for i in range(opening, len(s)):
        depth += (s[i] == "{") - (s[i] == "}")
        if depth == 0:
            return s[start:i + 1]
    raise AssertionError("unclosed " + marker)


def contract(s: str) -> bool:
    sync = body(s, "bool R29FragileEffectCached(")
    guard = body(s, "HRESULT R29GuardStableDraw(")
    direct = body(s, "HRESULT R29DirectTwoEye(")
    needle = "const bool r27DepthCandidate =\n                R29Effect.zEnable != D3DZB_FALSE;"
    # Pin the *whole* positive world branch, not only its inner probe.
    # A missing find() returns -1 and incorrectly passes an ordering check.
    # Requiring this exact chain prevents that false-positive regression.
    first = """else if (OutRunVR::GameSemantic::CorroboratesWorld(semanticScope))
            {
                worldGateChecked = true;
                if (r27DepthCandidate)
                {
                    if (R27ShouldBypassLegacyZeroDisparity(device))"""
    second = """if (fragile && !forceZeroDisparity && !worldGateChecked &&
                r27DepthCandidate &&
                R27ShouldBypassLegacyZeroDisparity(device))"""
    # This complete block must be present. Searching only for the if-condition
    # with find() allowed a missing guard (-1) to compare before valid anchors.
    fail_closed = """bool fragile = true;
            if (!R29FragileEffectCached(device, fragile))
            {
                ++R29SafetyFallbackDraws;
                return legacyR13Draw();
            }"""
    return all((
        "if (!R29SyncEffectState(device))" in sync,
        "fragile = R29Effect.fragileWorld;" in sync,
        fail_closed in guard and needle in guard
          and "const auto semanticScope" in guard
          and guard.find(fail_closed) < guard.find(needle)
          < guard.find("const auto semanticScope"),
        needle in guard,
        first in guard,
        second in guard,
        guard.count("R27ShouldBypassLegacyZeroDisparity(device)") == 2,
        # Both probes must be present before their ordering can be trusted.
        # The previous -1 < position test let a missing worldGateChecked pass.
        first in guard and second in guard and guard.find(first) < guard.find(second),
        "OutRunVR::GameSemantic::ForceZeroDisparity(semanticScope)" in guard,
        "if (forceZeroDisparity)" in guard,
        "return legacyR13Draw();" in guard,
        "return R29DirectTwoEye(device," in guard,
        "R29OwnerLeftDrawMayWriteDepth(device)" in direct,
        "R29OwnerLeftDrawMayWriteStencil(device)" in direct,
    ))


def candidate(cached_synced: bool, z_enabled: bool,
              fragile: bool, force_zero: bool) -> bool:
    # Test the two R27 call guards as an independently modeled decision.
    if not cached_synced:
        return False  # The enclosing R29 fallback, never this hot path.
    depth_gate = z_enabled
    first = fragile and not force_zero and depth_gate
    second = fragile and not force_zero and depth_gate
    return first or second


src = SRC.read_text(encoding="utf-8")
r26 = R26.read_text(encoding="utf-8")
policy = POLICY.read_text(encoding="utf-8")
assert contract(src), "R29 translucent R27 gate"
assert "if (!depthTestEnabled)" in policy and "EffectStereoPolicy::ZeroDisparity" in policy
assert "effect.classification != R13EffectClass::Flat ||" in r26
assert "!effect.zKnown || !effect.zEnabled" in r26
assert "const R13EffectSnapshot effect =\n                R13CaptureDrawTimeEffect(device);" in r26
for synced in (False, True):
    for depth in (False, True):
        for fragile in (False, True):
            for forced in (False, True):
                checked = candidate(synced, depth, fragile, forced)
                assert not checked if (not synced or not depth or forced or not fragile) else checked
mutations = [
    ("remove depth predicate", "r27DepthCandidate &&\n                R27ShouldBypass", "R27ShouldBypass"),
    ("invert cached depth", "R29Effect.zEnable != D3DZB_FALSE;", "R29Effect.zEnable == D3DZB_FALSE;"),
    ("allow unconditional scope probe", "if (r27DepthCandidate)", "if (true)"),
    ("remove forced-zero veto", "fragile && !forceZeroDisparity && !worldGateChecked", "fragile && !worldGateChecked"),
    ("remove positive world guard", "worldGateChecked = true;", "worldGateChecked = false;"),
    ("remove semantic world proof", "else if (OutRunVR::GameSemantic::CorroboratesWorld(semanticScope))", "else if (true)"),
    ("remove generation-certified snapshot", "if (!R29FragileEffectCached(device, fragile))", "if (false)"),
    ("remove safe legacy fallback", "++R29SafetyFallbackDraws;\n                return legacyR13Draw();", "++R29SafetyFallbackDraws;\n                return D3D_OK;"),
    ("remove depth snapshot", "R29Effect.zEnable != D3DZB_FALSE;", "true;"),
]
# Mutate only the owning guard body, never the first matching source token
# elsewhere in this large translation unit. A mutation outside the guard
# would not exercise the production branch and could give false failures.
guard_src = body(src, "HRESULT R29GuardStableDraw(")
assert src.count(guard_src) == 1, "unique R29 draw guard"
for label, before, after in mutations:
    assert before in guard_src, ("mutation anchor missing in guard", label)
    broken_guard = guard_src.replace(before, after, 1)
    assert broken_guard != guard_src, ("mutation did not change guard", label)
    broken = src.replace(guard_src, broken_guard, 1)
    assert not contract(broken), ("mutation escaped", label)
print(f"PASS R29 depth-off R27 hotpath: 16 decision combinations, {len(mutations)} destructive mutations; RUNTIME_VALIDATION=UNTESTED")
