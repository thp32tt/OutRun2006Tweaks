#!/usr/bin/env python3
"""DX11 real Draw/DrawIndexed native frame batch positive and negative proof."""
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil
import subprocess
root=Path(__file__).resolve().parents[1]
src=(root/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
header=(root/"src/vr/d3d11/native_game_frame_batch.hpp").read_text()
for marker in ('#include "native_game_frame_batch.hpp"',
 'OUTRUN_DX11_FRAME_BATCH', 's.frameBatch.accepts(candidateOrdinal, s.probeSlot,',
 'if (s.frameBatch.first_draw()) s.backend.begin_frame(kBackground);',
 'if (s.frameBatch.clear_depth())', 's.frameBatch.succeeded(output.nativeDepthTest)',
 's.frameBatch.abort()', 's.frameBatch.reset()',
 's.frameBatch.accepts_depth(output.nativeDepthTest,',
 'output.nativeDepthOrderingMode != 0u'):
    assert marker in src, marker
assert "s.attempted" not in src
assert src.count("s.backend.begin_frame(kBackground)") == 1
assert src.count("ctx->ClearDepthStencilView(s.diagnosticDepthView.Get(),") == 1
assert header.count("kMaxDraws = 8u") == 1
cxx=shutil.which("g++") or shutil.which("clang++")
assert cxx
probe=(root/"tools/dx11_native_frame_batch_probe.cpp").read_text()
with TemporaryDirectory(prefix="dx11-native-frame-") as work:
    folder=Path(work)
    (folder/"probe.cpp").write_text(probe)
    for tag,text,passes in (("positive",header,True),
                            ("negative_mutant",header.replace("kMaxDraws = 8u","kMaxDraws = 1u"),False)):
        (folder/"native_game_frame_batch.hpp").write_text(text)
        binary=folder/tag
        subprocess.run([cxx,"-std=c++17","-O2","-Wall","-Wextra","-Werror","-pedantic",
                        "-I",str(folder),str(folder/"probe.cpp"),"-o",str(binary)],check=True)
        result=subprocess.run([str(binary)],check=False,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        assert (result.returncode == 0) == passes, (tag,result.returncode)
print("PASS: game Draw composition, Z clear lifecycle, 8-draw cap, destructive mutation")
