#!/usr/bin/env python3
"""Compile and execute the actual R26 dispatch/core with a fake D3D9 device.

--source permits a pinned pre-change source for an executable red/green check.
No render math, physical GPU execution, or HMD acceptance is simulated as PASS.
"""
import argparse
from pathlib import Path
import os
import shutil
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser()
p.add_argument('--source', type=Path)
a = p.parse_args()
src = (a.source or root / 'src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp').read_text()
marker = '        template <typename RawDraw>\n        HRESULT R62TryFixedFunctionSpriteStereo('
if marker not in src:
    marker = '        HRESULT R62TryFixedFunctionSpriteIndexed('
body = src[src.index(marker):src.index('        void R30RollbackHooks()')]
harness = (root / 'tools/tests/r26_stage_fixedfn_harness.cpp').read_text().replace('// @ACTUAL_R26_SOURCE@', body)
compiler = os.environ.get('CXX') or shutil.which('g++') or shutil.which('clang++')
if not compiler:
    raise SystemExit('C++17 compiler required for actual-source regression')
with tempfile.TemporaryDirectory(prefix='r26-stage-') as td:
    cpp = Path(td) / 'test.cpp'
    exe = Path(td) / ('test.exe' if os.name == 'nt' else 'test')
    cpp.write_text(harness)
    subprocess.run([compiler, '-std=c++17', '-O0', str(cpp), '-o', str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
