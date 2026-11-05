#!/usr/bin/env python3
"""R30 live VB/IB/UP zero-count game source and unchanged D3D9 fallback."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
r30=(root/"src/vr/d3d9/stereo_renderer_r30.cpp").read_text()
bridge=(root/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
header=(root/"src/vr/d3d11/live_game_frame_bridge.hpp").read_text()
primitive=(root/"src/vr/d3d11/live_game_primitive_span.hpp").read_text()
workflow=(root/".github/workflows/dx11-fast-structural.yml").read_text()

def part(code,start,end):
    a=code.find(start)
    z=code.find(end,a+len(start))
    assert a>=0 and z>a,(start,end)
    return code[a:z]

def integrated(r,b,h,p):
    if "void observe_empty_game_draw(" not in h or "d3d9Type >= 1u && d3d9Type <= 6u" not in p:
        return False
    for a,z,expensive in (
        ("void R30ObserveNativeLinearVB(","void R30ObserveNativeIndexedVB(","GetStreamSource("),
        ("void R30ObserveNativeIndexedVB(","void R30ObserveNativeLinearUP(","GetStreamSource("),
        ("void R30ObserveNativeLinearUP(","void R30ObserveNativeIndexedUP(","live::game_native_primitive_element_count("),
        ("void R30ObserveNativeIndexedUP(","void R30CompleteNativeGameSource(","!numVertices"),
    ):
        s=part(r,a,z)
        i=s.find("if (primitiveCount == 0u &&")
        j=s.find("live::game_native_empty_primitive_type(",i)
        k=s.find("nativeSource.forwarded = true;",j)
        n=s.find("live::observe_empty_game_draw(device, topology);",k)
        q=s.find(expensive)
        if min(i,j,k,n,q)<0 or not (i<j<k<n<q): return False
    linear=part(b,"void observe_linear(","void observe_indexed(")
    zero=part(b,"void observe_empty_game_draw(","void observe_linear(")
    source=part(b,"void observe(IDirect3DDevice9* game,","void observe_empty_game_draw(")
    complete=part(r,"void R30CompleteNativeGameSource(","HRESULT __stdcall DrawPrimitiveDestR30(")
    hooks=part(r,"HRESULT __stdcall DrawPrimitiveUPDestR30(","void R30RollbackHooks()")
    return (0<=linear.find("if (primitives == 0u &&") <
            linear.find("observe_empty_game_draw(game, type);") <
            linear.find("game_native_primitive_element_count(") and
            "observe(game, type, 0u, nullptr, 0u, 0u, nullptr, 0u, nullptr);" in zero and
            ("s.frameBatch.absorb_empty_source_draw(" in source and
             "sourceOrdinal, sameSourceFullClear))" in source and
             "s.clearColor.sourceDevice ==" in source) and
            "live_game_frame::observe_failed_game_draw(device)" in complete and
            hooks.count("R30CompleteNativeGameSource(device,")>=4 and
            "R30ObserveNativeLinearUP(device, type, primitiveCount, data, stride);" in hooks)

assert integrated(r30,bridge,header,primitive),"real R30 zero Draw source cannot reach native bridge"
for a,z,_ in (
    ("void R30ObserveNativeLinearVB(","void R30ObserveNativeIndexedVB(",0),
    ("void R30ObserveNativeIndexedVB(","void R30ObserveNativeLinearUP(",0),
    ("void R30ObserveNativeLinearUP(","void R30ObserveNativeIndexedUP(",0),
    ("void R30ObserveNativeIndexedUP(","void R30CompleteNativeGameSource(",0),
):
    begin=r30.index(a);end=r30.index(z,begin+len(a))
    changed=r30[:begin]+r30[begin:end].replace(
        "live::observe_empty_game_draw(device, topology);","/* absent */",1)+r30[end:]
    assert not integrated(changed,bridge,header,primitive),"hook omission not caught"
# Removing the explicit additional-stream nullptr from the real R30 empty
# draw must fail the same integration contract (C2660 signature regression).
bad_arity=bridge.replace(
    "observe(game, type, 0u, nullptr, 0u, 0u, nullptr, 0u, nullptr);",
    "observe(game, type, 0u, nullptr, 0u, 0u, nullptr, 0u);", 1)
assert not integrated(r30,bad_arity,header,primitive),"zero game draw arity omission not caught"
bad=bridge.replace("observe_empty_game_draw(game, type);",
                   "observe_unavailable_game_draw(game);",1)
assert not integrated(r30,bad,header,primitive),"UP shadow bypass regression not caught"
assert not integrated(r30,bridge,header,primitive.replace(
    "d3d9Type <= 6u","d3d9Type < 1u")),"unknown primitive regression not caught"
assert "test_dx11_zero_source_hook_00756.py" in workflow
assert "dx11_zero_source_hook_probe_00756.cpp" in workflow
print("PASS: 00756 live D3D9 4-path zero source -> full native batch with failed Draw/input fallback")
