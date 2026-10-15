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
print('PASS GPU timing opt-in, nonblocking reads, alpha census, draw/reset/present wiring, 9 mutants')

# End-to-end dispatch histogram coverage: executed by the existing Active GPU gate.
from runpy import run_path
run_path(str(root/'tools/verify_dx9ex_translucent_route_profile.py'), run_name='__main__')
