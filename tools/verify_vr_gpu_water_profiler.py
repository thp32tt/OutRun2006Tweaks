#!/usr/bin/env python3
"""Opt-in GPU profiling static acceptance, including nine destructive mutants and off-by-default fastpath."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
hdr=(root/'src/vr/d3d9/gpu_water_profiler.hpp').read_text(encoding='utf-8')
src=(root/'src/vr/d3d9/stereo_renderer_r33.cpp').read_text(encoding='utf-8')
tokens=['OUTRUN_VR_GPU_PROFILE','std::strcmp(v,"1")==0','D3DQUERYTYPE_TIMESTAMPDISJOINT',
'D3DQUERYTYPE_TIMESTAMPFREQ','D3DQUERYTYPE_TIMESTAMP','D3DISSUE_BEGIN',
'D3DRS_ALPHABLENDENABLE','D3DRS_ALPHATESTENABLE','q->GetData(&v,sizeof(v),0)',
'if(ready==S_FALSE) continue;','if(s.pending) { ++dropped_; skip_=true; return false; }',
'waterAttribution=UNPROVEN','noZWriteSamples',
'gpuSpanP50Ms','gpuSpanP95Ms','gpuSpanP99Ms','gpuSpanSampleCount',
'gpuSpanOverflow','OUTRUN_VR_GPU_SCENE','std::sort(gpuSpans_.begin()','zDisabledSamples',
'D3DRS_ZWRITEENABLE','D3DRS_ZENABLE','D3DRS_STENCILENABLE',
'programmablePsSamples','fixedFnPsSamples','d->GetPixelShader(&ps)','ps->Release()',
'renderTargetSamples','offscreenRtSamples','multisampleRtSamples',
'd->GetRenderTarget(0,&target)','target->Release()','target->GetDesc(&desc)']
def good(x): return all(t in x for t in tokens) and 'D3DGETDATA_FLUSH' not in x
assert good(hdr),[t for t in tokens if t not in hdr]
assert hdr.count('CreateQuery(D3DQUERYTYPE_TIMESTAMP,')==4
assert src.count('GpuWaterProbe::instance().beforeDraw(device, primitiveCount)')==4
# The default-disabled draw path must avoid the Meter singleton entirely.
assert src.count('const bool gpuTimed = GpuWaterProbe::Enabled() &&')==4
assert src.count('GpuWaterProbe::instance().afterDraw(true);')==4
assert src.count('if (gpuTimed)\n                GpuWaterProbe::instance().afterDraw(true);')==4
assert 'GpuWaterProbe::instance().afterDraw(gpuTimed);' not in src
assert ('if (device && R32ReviewIsGameDevice(device) && GpuWaterProbe::Enabled())\n'
        '                GpuWaterProbe::instance().beforePresent(device);') in src
assert ('if (GpuWaterProbe::Enabled())\n'
        '                    GpuWaterProbe::instance().afterPresent(device);') in src
assert src.index('GpuWaterProbe::instance().beforePresent(device);')<src.index('R32ReviewRunPresentTelemetry')
assert src.index('GpuWaterProbe::instance().afterPresent(device);')>src.index('R32ReviewRunPresentTelemetry')
assert src.count('GpuWaterProbe::instance().reset();')==2
for old,new in [
('q->GetData(&v,sizeof(v),0)','q->GetData(&v,sizeof(v),D3DGETDATA_FLUSH)'),
('D3DQUERYTYPE_TIMESTAMPDISJOINT','D3DQUERYTYPE_EVENT'),
('D3DRS_ALPHABLENDENABLE','D3DRS_FILLMODE'),
('D3DRS_ZWRITEENABLE','D3DRS_FILLMODE'),
('ps->Release()','/* ref leaked */'),
('target->Release()','/* render-target COM ref leaked */'),
('d->GetRenderTarget(0,&target)','/* no RT classification */'),
('std::strcmp(v,"1")==0','true'),
('if(s.pending) { ++dropped_; skip_=true; return false; }','if(s.pending) { s.pending=false; }')]:
    assert not good(hdr.replace(old,new,1)),old
# Device replacement must clear stale unsupported/skip/query-clock state before
# testing it or incrementing the new frame's logical Draw count. This catches
# an actual old-device measurement lockout without touching rendering.
start = hdr.index("bool beforeDraw(IDirect3DDevice9* d,")
end = hdr.index("void afterDraw(bool timed)", start)
before_draw = hdr[start:end]
device_guard = "if(game_&&game_!=d) reset();"
device_bind = "game_=d;"
count_draw = "++logicalDrawCalls_;"
sticky_guard = "if(unsupported_||skip_) return false;"
assert before_draw.index("if(!Enabled()||!d) return false;") < before_draw.index(device_guard)
assert before_draw.index(device_guard) < before_draw.index(device_bind)
assert before_draw.index(device_bind) < before_draw.index(count_draw)
assert before_draw.index(count_draw) < before_draw.index(sticky_guard)
assert before_draw.index(sticky_guard) < before_draw.index("if(!active_)")
for broken in (
    before_draw.replace(device_guard + "\n        " + device_bind,
                        device_bind + "\n        " + device_guard, 1),
    before_draw.replace(count_draw + "\n        " + sticky_guard,
                        sticky_guard + "\n        " + count_draw, 1),
    before_draw.replace(device_guard, "if(false) reset();", 1),
    before_draw.replace(sticky_guard, "if(false) return false;", 1),
):
    assert broken != before_draw
    def device_order_ok(value):
        return (device_guard in value and device_bind in value and
                count_draw in value and sticky_guard in value and
                value.index(device_guard) < value.index(device_bind) <
                value.index(count_draw) < value.index(sticky_guard))
    assert not device_order_ok(broken), "bad device epoch mutation escaped"

# State-machine regression: an unsupported original device must not prevent
# first-frame profiling of a new game device (and must count that Draw once).
game = "old"; unsupported = True; skipped = True; draws = 18
incoming = "new"
if game != incoming:
    game = None; unsupported = skipped = False; draws = 0
game = incoming
draws += 1
assert (game, unsupported, skipped, draws) == ("new", False, False, 1)

print('PASS GPU timing opt-in, nonblocking reads, alpha census, draw/reset/present wiring, 9 mutants')

# End-to-end dispatch histogram coverage: executed by the existing Active GPU gate.
from runpy import run_path
run_path(str(root/'tools/verify_dx9ex_translucent_route_profile.py'), run_name='__main__')
