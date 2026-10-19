#!/usr/bin/env python3
"""R9 real-game programmable declaration -> native SM3 IA/upload integration."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
bridge = (ROOT / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
unpack = (ROOT / "src/vr/d3d11/live_game_sm3_vertex_unpack.hpp").read_text()
p = bridge.split("bool submit_live_sm3_game_draw(", 1)[1].split(
    "// Reuse geometric growth buffers", 1)[0]
layout = bridge.split("bool live_sm3_input_layout(", 1)[1].split(
    "bool live_sm3_shader_bytes(", 1)[0]

def require(cond, desc):
    if not cond:
        raise SystemExit("DX11 real-game SM3 declaration regression FAIL: " + desc)

# Actual source-owned VB/IB/UP reaches the same Draw/DrawIndexed with the
# translated bytes/stride, not merely a dormant format table.
for token in ("GetVertexDeclaration(", "live_sm3_input_layout(declaration, stride, extra, input,",
              "repack, nativeStride", "game_sm3_assemble_streams(",
              "streams[0]={static_cast<const std::uint8_t*>(bytes),stride,vertexCount};",
              "nativeBytes=unpacked.data()", "s.fullGameVertexCapacity, nativeBytes, vertexBytes",
              "context->IASetVertexBuffers(0u, 1u, &stream, &nativeStride, &offset)",
              "context->DrawIndexed(nativeIndexCount", "context->Draw(vertexCount",
              "nativeByteCount > (1ull << 25u)",
              "GetStreamSourceFreq(0u, &sourceFrequency)",
              "sourceFrequency != 1u", "catch (...) { return false; }"):
    require(token in p, "game draw/upload/fail closed missing " + token)
for token in ("D3DDECLUSAGE_BLENDWEIGHT", "D3DDECLUSAGE_BLENDINDICES",
              "D3DDECLUSAGE_POSITIONT", "D3DDECLUSAGE_TANGENT",
              "D3DDECLTYPE_FLOAT1", "D3DDECLTYPE_FLOAT4",
              "game_sm3_decl_width(in.Type)", "in.Stream != 0u",
              "in.Method != D3DDECLMETHOD_DEFAULT", "in.UsageIndex >= 16u",
              "static_cast<UINT>(in.Offset) + width > sourceStride",
              "end.Type != D3DDECLTYPE_UNUSED", "default: return false;",
              "DXGI_FORMAT_R32G32B32A32_FLOAT", "AlignedByteOffset = static_cast<UINT>(i * 16u)"):
    require(token in layout, "unverified declaration or missing IA semantic: " + token)
for token in ("case 4u:", "case 5u:", "case 8u:", "case 9u:",
              "case 10u:", "case 11u:", "case 12u:", "case 15u:",
              "case 16u:", "src[2] / 255.0f", "src[0] / 255.0f",
              "signedValue / 32767.0f", "bits / 65535.0f",
              "game_sm3_half_to_float(", "default: return false;",
              "game_sm3_decl_width(13u) == 4u",
              "game_sm3_decl_width(14u) == 4u",
              "case 13u: case 14u:", "signed10",
              "game_sm3_decl_width(17u) == 0u"):
    require(token in unpack, "packed shader attribute decode not proven: " + token)
# R30 secondary VB streams must reach a real Draw only after correct
# physical-index mapping, bounded attribute repack and non-instance admission.
for token in ("referenced[declaration[i].Stream]=true",
              "GetStreamSourceFreq(slot,&frequency)",
              "frequency != 1u", "extra->extra[slot-1u].vertexCount < vertexCount",
              "elements.push_back({declaration[i].Stream",
              "game_sm3_assemble_streams(elements,streams,vertexCount,unpacked)"):
    require(token in p, "missing multistream VB/IB native admission " + token)
assembly = (ROOT / "src/vr/d3d11/live_game_sm3_stream_assembly.hpp").read_text()
for token in ("game_sm3_decl_width(e.type)", "src.vertexCount < count",
              "e.offset, decoded", "destination.swap(candidate)",
              "catch (...) { return false; }"):
    require(token in assembly, "missing safe SM3 VB stream assembly " + token)

require("if (nativeIndices[i] >= vertexCount) return false;" in p and
        "liveBatch.accepts_source_draw(" in p and
        "if (!env_full_game_opt_in()" in p and
        "liveBatch.record_source_draw(sourceOrdinal)" in p,
        "index/ordinal/opt-in D3D9 fallback not retained")
print("DX11 SM3 live packed vertex declaration/Draw regression PASS (HMD UNTESTED)")
