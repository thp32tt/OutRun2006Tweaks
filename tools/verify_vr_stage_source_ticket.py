#!/usr/bin/env python3
"""Run actual +TIME source exit, batch ledger and deferred-owner predicate."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser()
p.add_argument('--source', type=Path, help='Pinned pre-change UI source for a red/green replay')
a = p.parse_args()
source = (a.source or ROOT / 'src/hooks_uiscaling.cpp').read_text()
def function(signature):
    start = source.index(signature)
    brace = source.index('{', start)
    depth, end = 1, brace + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]
h = (ROOT / 'tools/tests/stage_source_ticket_harness.cpp').read_text()
h = h.replace('// @ACTUAL_LEAVE@', function('static void StageExtensionLeave('))
h = h.replace('// @ACTUAL_PREDICATE@', function('constexpr bool CanRestoreDeferredResultOwner('))
marker = 'static void CompleteDirectStageSource(bool admitted) noexcept'
if marker in source:
    entry = function('static void StageExtensionEnter(')
    draw = function('static HRESULT __stdcall DrawDest(')
    assert entry.index('FlushD3DXBeforeDirectStageSource();') < entry.index('BeginD3DXDirectStageSource();') < entry.index('StageExtensionDirectDrawOwner.emplace(')
    assert draw.index('const auto sourceTicket = DirectStageTicket;') < draw.index('Draw_hk.stdcall<HRESULT>')
    assert draw.index('HudBatch.completeNativeDraw(') < draw.index('HudBatch.recordDirectStageTicket(sourceTicket);')
    assert 'sourceTicket == DirectStageTicket' in draw
    assert '!command.queued && source == ProducerToken::StageExtensionTime)' in draw
    complete = function(marker).replace('static void CompleteDirectStageSource(',
                                       'void CompleteD3DXDirectStageSource(')
    h = '#define HAVE_STAGE_TICKET 1\n' + h
    begin = function('static void BeginDirectStageSource() noexcept')
else:
    complete = 'void CompleteD3DXDirectStageSource(bool) {}'
    begin = ''
h = h.replace('// @ACTUAL_COMPLETE@', complete)
h = h.replace('// @ACTUAL_BEGIN@', begin)
compiler = os.environ.get('CXX') or shutil.which('g++') or shutil.which('clang++')
if not compiler:
    raise SystemExit('C++17 compiler required for +TIME source ticket regression')
with tempfile.TemporaryDirectory(prefix='stage-ticket-') as td:
    cpp=Path(td)/'test.cpp'; exe=Path(td)/('test.exe' if os.name=='nt' else 'test')
    cpp.write_text(h)
    subprocess.run([compiler,'-std=c++17','-O0','-I',str(ROOT/'src'),str(cpp),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
