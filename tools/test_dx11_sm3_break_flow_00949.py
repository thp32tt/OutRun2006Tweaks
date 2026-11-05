#!/usr/bin/env python3
"""SM3 BREAK/BREAKC shader-owned repetition to native VS/PS integration."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
backend = (root / 'src/vr/d3d11/native_backend.cpp').read_text()
flow = (root / 'src/vr/d3d11/native_sm3_repeat_flow.hpp').read_text()
fast = (root / '.github/workflows/dx11-fast-structural.yml').read_text()
for token in ('D3DSIO_BREAK', 'D3DSIO_BREAKC',
              'structuredFlow.record_break()', 'conditionalBreak ? 7u : 1u',
              'structuredFlow.begin_repeat(count, tempWritten, outputWritten)',
              'structuredFlow.end_repeat(tempWritten, outputWritten)',
              'append_native_sm3_break(', 'native_sm3_ifc_comparison',
              '!writtenFlow.begin(tempWritten, outputWritten)',
              'D3DSPR_TEMP', 'D3DSPR_INPUT', 'D3DSPR_CONST',
              'D3DSHADER_ADDRESSMODE_MASK', 'D3DSPSM_NONE',
              'D3DSIO_REP', 'D3DSIO_ENDREP',
              'build_r283_sm3_mov_shader_source(', 'D3D11'):
    assert token in backend, token
for token in ('bool record_break()', 'frame.hasBreak',
              'temps[i] &= frame.entryTemps[i]',
              'outputs[i] &= frame.entryOutputs[i]',
              'it->kind == 2u', 'it->tracksWrites',
              'append_native_sm3_break('):
    assert token in flow, token
assert 'dx11_sm3_break_flow_probe_00949.cpp' in fast
assert 'test_dx11_sm3_break_flow_00949.py' in fast
print('SM3 BREAK/BREAKC native game shader control flow checks PASS')
