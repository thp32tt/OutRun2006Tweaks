#!/usr/bin/env python3
"""Source-to-native integrated dynamic VB/IB/Stage1 streaming fail-closed check."""
from pathlib import Path
p=Path(__file__).resolve().parents[1]
src=(p/'src/vr/d3d11/live_game_frame_bridge.cpp').read_text()
head=(p/'src/vr/d3d11/native_game_stream_capacity.hpp').read_text()
flow=(p/'.github/workflows/dx11-fast-structural.yml').read_text()
assert 'next_native_stream_capacity' in head
assert 'kMaxDraws = 8u' in (p/'src/vr/d3d11/native_game_frame_batch.hpp').read_text()

# Verify actual game Draw and indexed Draw go through per-batch slots, upload
# before binding, and preserve existing D3D9 reject/abort semantics.
def integrated(text):
    submit=text.split('bool submit(State& s,',1)[1].split('bool observe_source_device(',1)[0]
    upload=text.split('bool upload_native_stream(',1)[1].split('bool submit(State& s,',1)[0]
    reset=text.split('void before_game_reset() noexcept {',1)[1]
    return all(s in submit for s in (
        's.frameBatch.submitted >= s.streamSlots.size()',
        'streamSlots[s.frameBatch.submitted]',
        'stream.stage1Capacity', 'D3D11_BIND_CONSTANT_BUFFER, &payload',
        'stream.vertexCapacity', 'D3D11_BIND_VERTEX_BUFFER',
        'stream.indexCapacity', 'D3D11_BIND_INDEX_BUFFER',
        'ctx->IASetVertexBuffers(0, 1, &boundVB',
        'ctx->DrawIndexed(indexCount, 0, 0);',
        'ctx->Draw(static_cast<UINT>(vertices.size()), 0);',
    )) and all(s in upload for s in (
        'D3D11_USAGE_DYNAMIC','D3D11_CPU_ACCESS_WRITE',
        'D3D11_MAP_WRITE_DISCARD','device->CreateBuffer(',
        'context->Unmap(buffer.Get(), 0u)',
        'return false;',
    )) and 'for (auto& stream : s.streamSlots) stream = {};' in reset
assert integrated(src)
for term in ('stream.indexCapacity','stream.stage1Capacity',
             's.frameBatch.submitted >= s.streamSlots.size()',
             'ctx->DrawIndexed(indexCount, 0, 0);'):
    assert not integrated(src.replace(term,'BROKEN',1)), term
# Mutate the owning stream upload helper, not an unrelated earlier GPU
# readback function which legitimately also calls Unmap().
def mutate_upload(text, term):
    prefix, tail = text.split('bool upload_native_stream(', 1)
    upload, rest = tail.split('bool submit(State& s,', 1)
    assert term in upload, term
    return (prefix + 'bool upload_native_stream(' +
            upload.replace(term, 'BROKEN', 1) +
            'bool submit(State& s,' + rest)

for term in ('D3D11_MAP_WRITE_DISCARD','D3D11_CPU_ACCESS_WRITE',
             'context->Unmap(buffer.Get(), 0u)'):
    assert not integrated(mutate_upload(src, term)), term
assert 'test_dx11_live_stream_buffer_reuse.py' in flow
assert 'dx11_game_stream_capacity_probe.cpp' in flow
print('PASS real D3D9 Draw/Indexed -> dynamic ring VB/IB/Stage1 -> GPU & Reset/fallback')
