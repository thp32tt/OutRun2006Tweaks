#!/usr/bin/env python3
"""D3DX Lost/Reset outer callbacks must not invalidate a newer Begin generation."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SRC=(ROOT/'src/hooks_uiscaling.cpp').read_text(encoding='utf-8')
WF=(ROOT/'.github/workflows/vr-dx9ex-active.yml').read_text(encoding='utf-8')

def check(src: str) -> bool:
    try:
        start=src.index('static void InvalidateForDeviceLifecycle(')
        end=src.index('static bool FlushTracked(', start)
        block=src[start:end]
        assert 'const OutRunVR::HudCommandBatch::Ledger::NativeSnapshot& entry' in block
        assert '!HudBatch.sameGeneration(entry)' in block
        assert block.index('!HudBatch.sameGeneration(entry)') < block.index('HudBatch.invalidate();')
        for name,hook in (('LostDevice','LostDevice_hk'),('ResetDevice','ResetDevice_hk')):
            s=block.index(f'static HRESULT __stdcall {name}Dest(void* self)')
            e=block.index('\n    }',s)
            fn=block[s:e]
            assert 'const auto entry = HudBatch.snapshot();' in fn
            assert 'self, entry.sprite, *Module::exe_ptr<void*>(0x55B218)' in fn
            assert f'const HRESULT hr = {hook}.stdcall<HRESULT>(self);' in fn
            assert 'InvalidateForDeviceLifecycle(ownsBatch, entry);' in fn
            assert fn.index('HudBatch.snapshot()') < fn.index('OwnsLifecycle(') < fn.index(f'{hook}.stdcall') < fn.index('InvalidateForDeviceLifecycle(')
        return True
    except (AssertionError, ValueError):
        return False

assert WF.count('tools/verify_vr_d3dx_lifecycle_generation.py') == 2
assert check(SRC)
mut=SRC.replace('!HudBatch.sameGeneration(entry)', 'false', 1)
assert mut != SRC and not check(mut), 'generation fence mutation escaped'
mut=SRC.replace('self, entry.sprite, *Module::exe_ptr<void*>(0x55B218)', 'self, HudBatch.sprite, *Module::exe_ptr<void*>(0x55B218)', 1)
assert mut != SRC and not check(mut), 'entry ownership mutation escaped'
print('PASS D3DX Lost/Reset invalidates entry generation only; reentrant newer Begin preserved; HMD UNTESTED')
