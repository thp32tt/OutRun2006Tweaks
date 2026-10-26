#!/usr/bin/env python3
"""Execute the actual R26 C993 branch with synthetic XR views; no HMD claim."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser()
p.add_argument('--source', type=Path)
p.add_argument('--math-source', type=Path, help='Production R7 math, including mutation replay')
p.add_argument('--mutations', action='store_true', help='Require numerical failures for broken production math')
a = p.parse_args()
source = (a.source or ROOT / 'src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp').read_text()
start = source.index('// Only exact, nonqueued C993 sun objects use this correction.')
start = source.index('if (!OutRunVR::GameSemantic::QueueRenderActive()', start)
brace = source.index('{', start)
depth = 1
end = brace + 1
while depth:
    depth += (source[end] == '{') - (source[end] == '}')
    end += 1
actual = source[start:end]
harness = (ROOT / 'tools/tests/r26_lens_projection_harness.cpp').read_text()
harness = harness.replace('// @ACTUAL_C993_BRANCH@', actual)
math = (a.math_source or ROOT / 'src/vr/d3d9/stereo_renderer_r7.inc').read_text()
def function(signature):
    start = math.index(signature)
    brace = math.index('{', start)
    depth, end = 1, brace + 1
    while depth:
        depth += (math[end] == '{') - (math[end] == '}')
        end += 1
    return math[start:end]
helpers = '\n'.join(function('D3DMATRIX ' + name + '(') for name in (
    'IdentityMatrix', 'MatrixFromQuaternionTranslation', 'InverseRigid',
    'TransposeMatrix', 'ProjectionFromFov'))
harness = harness.replace('// @ACTUAL_RENDER_MATH@', helpers)
compiler = os.environ.get('CXX') or shutil.which('g++') or shutil.which('clang++')
if not compiler:
    raise SystemExit('C++17 compiler required for R26 C993 regression')
with tempfile.TemporaryDirectory(prefix='r26-lens-') as td:
    cpp = Path(td) / 'test.cpp'
    exe = Path(td) / ('test.exe' if os.name == 'nt' else 'test')
    cpp.write_text(harness)
    subprocess.run([compiler, '-std=c++17', '-O0', '-I', str(ROOT / 'src'),
                    str(cpp), '-o', str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
    if a.mutations:
        mutations = (
            ('asymmetric-FOV-sign', 'out._31 = (tanRight + tanLeft) / width;',
             'out._31 = -(tanRight + tanLeft) / width;'),
            ('yaw-rotation-sign', 'out._13=2*(xz-yw);', 'out._13=2*(xz+yw);'),
            ('shader-upload-transpose', 'out.m[r][c] = in.m[c][r];',
             'out.m[r][c] = in.m[r][c];'),
        )
        for label, before, after in mutations:
            if harness.count(before) != 1:
                raise SystemExit('Mutation anchor drift: ' + label)
            cpp.write_text(harness.replace(before, after, 1))
            subprocess.run([compiler, '-std=c++17', '-O0', '-I', str(ROOT / 'src'),
                            str(cpp), '-o', str(exe)], check=True)
            result = subprocess.run([str(exe)], capture_output=True, text=True)
            if result.returncode == 0:
                raise SystemExit('FAIL numerical mutation escaped: ' + label)
            print('PASS numerical mutation rejected:', label, 'exit', result.returncode)

