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
p.add_argument('--mutations', action='store_true', help='Execute broken native hook controls')
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
lifetime = '\n'.join(function(signature) for signature in (
    'constexpr bool CanFlush(', 'constexpr bool CanDrainDeferredResultBeforeForeignDraw('))
h = h.replace('// @ACTUAL_LIFETIME@',
    'namespace DX9ExD3DXSpriteLifetime {\n'
    'using namespace OutRunVR::GameSemantic;\n'
    'using ::CanRestoreDeferredResultOwner;\n' + lifetime + '\n}')
native = '\n'.join(function(signature) for signature in (
    'static bool StageOwner(', 'static bool GoalOwner(',
    'static HRESULT __stdcall FlushDest(', 'static HRESULT __stdcall EndDest(',
    'static HRESULT __stdcall DrawDest('))
h = h.replace('// @ACTUAL_NATIVE_HOOKS@', native)
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
    if a.mutations:
        mutations = (
            ('rejected-ticket-not-revoked',
             '!admitted && HudBatch.revokeDirectStageTicket(DirectStageTicket)',
             'false && HudBatch.revokeDirectStageTicket(DirectStageTicket)'),
            ('draw-ticket-not-stamped', 'HudBatch.recordDirectStageTicket(sourceTicket);',
             '(void)sourceTicket;'),
            ('reentrant-ticket-not-checked', 'sourceTicket == DirectStageTicket', 'true'),
            ('foreign-Flush-consumes-ledger',
             'if (self && self == submission.sprite)\n            HudBatch.completeNativeFlush',
             'if (self)\n            HudBatch.completeNativeFlush'),
            ('foreign-End-consumes-ledger',
             'if (self && self == submission.sprite)\n            HudBatch.completeNativeEnd',
             'if (self)\n            HudBatch.completeNativeEnd'),
        )
        for label,before,after in mutations:
            if h.count(before) != 1:
                raise SystemExit('Mutation anchor drift: '+label)
            cpp.write_text(h.replace(before,after,1))
            subprocess.run([compiler,'-std=c++17','-O0','-I',str(ROOT/'src'),str(cpp),'-o',str(exe)],check=True)
            result=subprocess.run([str(exe)],capture_output=True,text=True)
            if result.returncode == 0:
                raise SystemExit('FAIL native hook mutation escaped: '+label)
            print('PASS native hook mutation rejected:',label,'exit',result.returncode)

