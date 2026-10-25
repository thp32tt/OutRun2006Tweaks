#!/usr/bin/env python3
"""Execute actual R26 F11 preparation/draw transaction on a recording D3D9 fake.
This verifies raster state and failure restoration, not HMD optical fusion.
"""
import argparse, os, shutil, subprocess, tempfile
from pathlib import Path
root = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser()
p.add_argument('--source', type=Path)
a = p.parse_args()
src = (a.source or root/'src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp').read_text()
start = src.index('        bool R30PrepareExternalImGuiProjection(')
end = src.index('        bool R30IsExactResultHudDraw()', start)
body = src[start:end]
harness = (root/'tools/tests/f11_eye_viewport_harness.cpp').read_text().replace('// @ACTUAL_F11_SOURCE@', body)
compiler = os.environ.get('CXX') or shutil.which('g++') or shutil.which('clang++')
if not compiler: raise SystemExit('C++17 compiler required')
with tempfile.TemporaryDirectory(prefix='f11-viewport-') as td:
    cpp = Path(td)/'test.cpp'
    exe = Path(td)/('test.exe' if os.name == 'nt' else 'test')
    cpp.write_text(harness)
    subprocess.run([compiler, '-std=c++17', '-O0', str(cpp), '-o', str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
