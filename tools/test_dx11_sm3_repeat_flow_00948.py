#!/usr/bin/env python3
"""Live-game SM3 DEFI/REP/ENDREP native Draw and safe fallback source checks."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
backend = (root / "src/vr/d3d11/native_backend.cpp").read_text()
helper = (root / "src/vr/d3d11/native_sm3_repeat_flow.hpp").read_text()
workflow = (root / ".github/workflows/dx11-fast-structural.yml").read_text()
for s in (
    'D3DSIO_DEFI', 'D3DSIO_REP', 'D3DSIO_ENDREP',
    'D3DSPR_CONSTINT', 'intDefPresent[reg] = true',
    'native_sm3_static_repeat_count(', 'structuredFlow.begin_repeat(count)',
    'structuredFlow.end_repeat()', 'structuredFlow.begin_if()',
    'structuredFlow.end_if()', 'structuredFlow.otherwise()',
    '!structuredFlow.empty()', 'append_native_sm3_repeat_begin(',
    'native_sm3_const_reference(', 'NativeSm3ConditionalFlow writtenFlow;',
    'native_sm3_bool_reference(',
):
    assert s in backend, s
for s in ('copies > 64u / frame.count', 'count > 16u',
          'frames_.back().kind != 2u', 'frames_.back().kind != 1u',
          '[loop] for (int ', 'literal[0] == 0u'):
    assert s in helper, s
assert 'dx11_sm3_repeat_flow_probe_00948.cpp' in workflow
assert 'test_dx11_sm3_repeat_flow_00948.py' in workflow
print("SM3 DEFI/REP native source and original D3D9 fallback checks PASS")
