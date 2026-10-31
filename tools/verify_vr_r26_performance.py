#!/usr/bin/env python3
"""Compile actual production functions and compare against pinned pre-change output."""
import os,shutil,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
s=(ROOT/'src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp').read_text()
r7=(ROOT/'src/vr/d3d9/stereo_renderer_r7.inc').read_text()
def fn(source, marker):
 start=source.index(marker);i=source.index('{',start);depth=1;j=i+1
 while depth:
  depth+=(source[j]=='{')-(source[j]=='}');j+=1
 return source[start:j]
reference=(ROOT/'tools/tests/r26_perf_reference.cpp').read_text()
reference=reference.replace('R30TransformXyzrhw','ReferenceTransformXyzrhw')
reference=reference.replace('float restoredView[4]{};', '++referenceRestores; float restoredView[4]{};')
actual=fn(s,'bool R30TransformXyzrhwVertices(')+'\n'+fn(s,'bool R30TransformXyzrhwStereo(')
actual=actual.replace('const float clipW = 1.0f / rhw;', '++actualRestores; const float clipW = 1.0f / rhw;')
state=fn(s,'struct R30XyzrhwState')+';'
math='\n'.join(fn(r7,x) for x in ['D3DMATRIX IdentityMatrix(', 'D3DMATRIX MatrixFromQuaternionTranslation(', 'D3DMATRIX InverseRigid(', 'bool MatrixFinite(', 'D3DMATRIX ProjectionFromFov('])
cache=fn(r7,'struct R26EyeMathPair')+';\n'+fn(r7,'const R26EyeMathPair* R26CachedEyeMath(')
# Count cache-miss evaluations in the actual production cache body.
cache=cache.replace('R26EyeMathPair candidate{};', '++cacheBuilds; R26EyeMathPair candidate{};')
h=(ROOT/'tools/tests/r26_performance_harness.cpp').read_text()
h=h.replace('// @STATE@',state).replace('// @MATH@',math).replace('// @CACHE@',cache)
h=h.replace('// @REFERENCE@',reference).replace('// @ACTUAL@',actual)
h=h.replace('// @COPY@',fn(r7,'HRESULT StretchDirectEye('))
h=h.replace('// @SPARSE@',fn(s,'bool R30CopySparseVertexShadow('))
cc=os.environ.get('CXX') or shutil.which('g++') or shutil.which('clang++')
if not cc: raise SystemExit('C++17 compiler required')
with tempfile.TemporaryDirectory(prefix='r26-perf-') as tmp:
 cpp=Path(tmp)/'test.cpp';exe=Path(tmp)/('test.exe' if os.name=='nt' else 'test')
 cpp.write_text(h)
 subprocess.run([cc,'-std=c++17','-O2','-I',str(ROOT/'src'),str(cpp),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True)
print('PASS production-source CPU differential, cache and transfer policy')
