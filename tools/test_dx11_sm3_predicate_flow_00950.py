#!/usr/bin/env python3
"""Native game D3D9 SM3 SETP/BREAKP shader predicate integration regression."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
backend = (root / 'src/vr/d3d11/native_backend.cpp').read_text()
flow = (root / 'src/vr/d3d11/native_sm3_predicate_flow.hpp').read_text()
fast = (root / '.github/workflows/dx11-fast-structural.yml').read_text()
for token in ('D3DSIO_SETP', 'D3DSIO_BREAKP', 'D3DSPR_PREDICATE',
              'predicateFlow.ready()', 'predicateFlow.write()',
              'predicateFlow.begin_if()', 'predicateFlow.otherwise()',
              'predicateFlow.end_if()', 'predicateFlow.begin_repeat()',
              'predicateFlow.end_repeat()', 'structuredFlow.record_break()',
              'append_native_sm3_setp(', 'append_native_sm3_breakp(',
              'build_r283_sm3_mov_shader_source(', 'D3D11',
              'D3DSPSM_NOT', 'D3DSHADER_ADDRESSMODE_MASK',
              'native_sm3_ifc_comparison'):
    assert token in backend, token
for token in ('initialized_ &=', 'entryInitialized', 'thenInitialized',
              'bool r283_p0', 'r283_p0 = (', 'if (r283_p0) break;',
              'if (!r283_p0) break;'):
    assert token in (flow + backend), token
assert 'dx11_sm3_predicate_flow_probe_00950.cpp' in fast
assert 'test_dx11_sm3_predicate_flow_00950.py' in fast
print('SM3 SETP/BREAKP native shader-to-game Draw source checks PASS')
