#!/usr/bin/env python3
"""Baseline 0cff: rank-only source probes must preserve rival and draw path."""
from pathlib import Path
src=(Path(__file__).resolve().parents[1]/'src/hooks_uiscaling.cpp').read_text(encoding='utf-8')
def check(s):
    wrapper=s.split('static void __cdecl Calc3D2D_OrdinalExactCall(',1)[1].split('// The fraction of a pixel',1)[0]
    rank=s.split('static int __cdecl RankMarkerSub_dest(',1)[1].split('using RankMarkerSubFn',1)[0]
    for token in ('Calc3D2D_dest(a1, a2, in, out);','RankMarkerExactCalcEdge = previous;',
                  'VR R57 ORDINAL EDGE PROBE: e8=0xBAEE2 calls={}',
                  'projectionValid={} sourceZ={} screenZ={} navipubDepth={}',
                  'n <= 8 || (n & (n - 1)) == 0'):
        assert token in wrapper, token
    for token in ('RankMarkerSub_hk.call<int>(arg)', 'VR R57 RANK OWNER PROBE: sub=0x4BAD20 calls={}',
                  'RankMarkerProjectedInfo = saved;', 'n <= 8 || (n & (n - 1)) == 0'):
        assert token in rank,token
    assert wrapper.index('Calc3D2D_dest(a1, a2, in, out);') < wrapper.index('VR R57 ORDINAL EDGE PROBE')
    assert rank.index('RankMarkerSub_hk.call<int>(arg)') < rank.index('VR R57 RANK OWNER PROBE') < rank.index('RankMarkerProjectedInfo = saved;')
    assert 'returnAddress == Module::exe_ptr(0xBB6F5)' in s
    assert s.count('returnAddress == Module::exe_ptr(0xBB6F5)')==1
check(src)
for a,b in (
    ('"VR R57 ORDINAL EDGE PROBE: e8=0xBAEE2 calls={} rawFinite={} "','"VR R57 ORDINAL EDGE PROBE: calls={} rawFinite={} "'),
    ('"VR R57 RANK OWNER PROBE: sub=0x4BAD20 calls={} "','"VR R57 RANK OWNER PROBE: calls={} "')):
    assert a in src
    try:check(src.replace(a,b,1))
    except (AssertionError,ValueError):pass
    else:raise AssertionError("probe mutation escaped "+a)
print("PASS rank 0xBAEE2 exact call vs 0x4BAD20 parent telemetry, world/rival drawing unchanged")
