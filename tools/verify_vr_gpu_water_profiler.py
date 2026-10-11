#!/usr/bin/env python3
"""Opt-in GPU profiling static acceptance, including five destructive mutants."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
hdr=(root/'src/vr/d3d9/gpu_water_profiler.hpp').read_text(encoding='utf-8')
src=(root/'src/vr/d3d9/stereo_renderer_r33.cpp').read_text(encoding='utf-8')
tokens=['OUTRUN_VR_GPU_PROFILE','std::strcmp(v,"1")==0','D3DQUERYTYPE_TIMESTAMPDISJOINT',
'D3DQUERYTYPE_TIMESTAMPFREQ','D3DQUERYTYPE_TIMESTAMP','D3DISSUE_BEGIN',
'D3DRS_ALPHABLENDENABLE','D3DRS_ALPHATESTENABLE','q->GetData(&v,sizeof(v),0)',
'if(ready==S_FALSE) continue;','if(s.pending) { ++dropped_; skip_=true; return false; }',
'waterAttribution=UNPROVEN']
def good(x): return all(t in x for t in tokens) and 'D3DGETDATA_FLUSH' not in x
assert good(hdr),[t for t in tokens if t not in hdr]
assert hdr.count('CreateQuery(D3DQUERYTYPE_TIMESTAMP,')==4
assert src.count('GpuWaterProbe::instance().beforeDraw(device, primitiveCount)')==4
assert src.count('GpuWaterProbe::instance().afterDraw(gpuTimed);')==4
assert src.index('GpuWaterProbe::instance().beforePresent(device);')<src.index('R32ReviewRunPresentTelemetry')
assert src.index('GpuWaterProbe::instance().afterPresent(device);')>src.index('R32ReviewRunPresentTelemetry')
assert src.count('GpuWaterProbe::instance().reset();')==2
for old,new in [
('q->GetData(&v,sizeof(v),0)','q->GetData(&v,sizeof(v),D3DGETDATA_FLUSH)'),
('D3DQUERYTYPE_TIMESTAMPDISJOINT','D3DQUERYTYPE_EVENT'),
('D3DRS_ALPHABLENDENABLE','D3DRS_ZENABLE'),
('std::strcmp(v,"1")==0','true'),
('if(s.pending) { ++dropped_; skip_=true; return false; }','if(s.pending) { s.pending=false; }')]:
    assert not good(hdr.replace(old,new,1)),old
print('PASS GPU timing opt-in, nonblocking reads, alpha census, draw/reset/present wiring, 5 mutants')
