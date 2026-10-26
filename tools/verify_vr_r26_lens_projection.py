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
