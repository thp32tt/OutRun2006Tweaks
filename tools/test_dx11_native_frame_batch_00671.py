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
 'if (s.frameBatch.clear_depth())', 's.frameBatch.succeeded(output.nativeDepthTest,',
 's.frameBatch.abort()', 's.frameBatch.reset()',
 'if (!submit(s, vertices, fanTriangles.data(),',
 'if (!submit(s, vertices, indices, indexCount, type, capture, output))',
 's.frameBatch.accepts_depth(output.nativeDepthTest,',
 'output.nativeDepthOrderingMode != 0u',
 's.frameBatch.must_abort_unsupported(fullMode, multiBatch)',
 's.frameBatch.must_abort_unsupported('):
    assert marker in src, marker
assert "s.attempted" not in src
# Test a real exception-safety transition in the live game observer.
# Destructive mutation to the old empty handler must be detected, while
# preserving D3D9 fallback even if a diagnostic allocation fails.
observer = src.split("void observe(IDirect3DDevice9*", 1)[1].split("} // namespace", 1)[0]
observer_catch = observer.split("    } catch (...) {", 1)[1]
exception_abort = "            s.frameBatch.abort();"
assert exception_abort in observer_catch
assert "std::lock_guard<std::mutex> lock(s.mutex);" in observer_catch
assert exception_abort not in observer_catch.replace(exception_abort, "", 1)
assert src.count("s.backend.begin_frame(kBackground)") == 1
assert src.count("ctx->ClearDepthStencilView(s.diagnosticDepthView.Get(),") == 1
assert header.count("kMaxDraws = 8u") == 1
for marker in ("OUTRUN_DX11_FULL_GAME_FRAME", "accepts_full(sourceOrdinal)",
               "publishable_full(s.pending, s.sourceDrawsThisFrame)",
               "ensure_pipeline(s, output.nativeWidth, output.nativeHeight)",
               "depthDesc.Width = s.nativeWidth", "next.completeFullFrame = fullMode",
               "oldest.completeFullFrame != fullMode"):
    assert marker in src, marker
assert "kMaxFullFrameDraws = 4096u" in header
cxx=shutil.which("g++") or shutil.which("clang++")
assert cxx
probe=(root/"tools/dx11_native_frame_batch_probe.cpp").read_text()
with TemporaryDirectory(prefix="dx11-native-frame-") as work:
    folder=Path(work)
    (folder/"probe.cpp").write_text(probe)
    for tag,text,passes in (("positive",header,True),
                            ("negative_mutant",header.replace("kMaxDraws = 8u","kMaxDraws = 1u"),False),
                            ("full_limit_mutant",header.replace("kMaxFullFrameDraws = 4096u","kMaxFullFrameDraws = 8u"),False),
                            ("full_contiguity_mutant",header.replace("ordinal == submitted","ordinal >= submitted"),False),
                            ("full_unsupported_mutant",header.replace("return fullMode ||","return (fullMode && false) ||"),False)):
        (folder/"native_game_frame_batch.hpp").write_text(text)
        binary=folder/tag
        subprocess.run([cxx,"-std=c++17","-O2","-Wall","-Wextra","-Werror","-pedantic",
                        "-I",str(folder),str(folder/"probe.cpp"),"-o",str(binary)],check=True)
        result=subprocess.run([str(binary)],check=False,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        assert (result.returncode == 0) == passes, (tag,result.returncode)
print("PASS: game Draw composition, Z clear lifecycle, 8-draw cap, destructive mutation")
