#!/usr/bin/env python3
"""Fail-before/pass-after R33 draw-route GPU profile instrumentation contract."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
r33=(root/'src/vr/d3d9/stereo_renderer_r33.cpp').read_text(encoding='utf-8')
gpu=(root/'src/vr/d3d9/gpu_water_profiler.hpp').read_text(encoding='utf-8')
routes=('Xyzrhw','ScreenHud','FastWorld','R29Fallback','RecordingRaw')
for route in routes:
    assert f'DrawRoute::{route}' in r33, route
    assert route in gpu, route
assert r33.count('DrawRoute::Xyzrhw')==4, 'all four indexed/VB/UP routes'
for route in ('ScreenHud','FastWorld','R29Fallback','RecordingRaw'):
    assert r33.count(f'DrawRoute::{route}')==1, route
assert r33.count('GpuWaterProbe::Enabled()')>=10, 'diagnostics default-off gate'
assert 'if(!Enabled()||!d) return false;\n        ++logicalDrawCalls_;' in gpu
assert 'if(unsupported_||skip_) return false;' in gpu
assert 'routeCounts_.fill(0);' in gpu
assert 'logicalDrawCalls_ - (routeCounts_' in gpu
assert 'waterAttribution=UNPROVEN' in gpu
assert 'GetData(&v,sizeof(v),0)' in gpu and 'D3DGETDATA_FLUSH' not in gpu
assert 'OUTRUN_VR_GPU_PROFILE' in gpu and 'std::strcmp(v,"1")==0' in gpu
# Mutation tests ensure losing any dispatch-route coverage fails the contract.
def route_coverage(x):
    return x.count('DrawRoute::Xyzrhw')==4 and all(x.count(f'DrawRoute::{r}')==1 for r in routes[1:])
for route in routes:
    assert not route_coverage(r33.replace(f'DrawRoute::{route}', 'DrawRoute::MISSING',1))
print('PASS DX9Ex R33 diagnostic route distribution (all 4 APIs, 5 mutation checks)')
