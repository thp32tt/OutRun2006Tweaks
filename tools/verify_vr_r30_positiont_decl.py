#!/usr/bin/env python3
"""R30 fixed-function FVF=0 declaration XYZRHW stereo admission regression."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"src/vr/d3d9/stereo_renderer_r30.cpp"
FLOW=ROOT/".github/workflows/vr-dx9ex-active.yml"

def function_body(source, signature):
    """Bound a C++ function at its matching closing brace, not at an unrelated later function.

    The R84 renderer now inserts independent stage, F11 and rank helpers
    between the XYZRHW admission function and the depth-signature helper.
    They may legitimately call GetFVF and must not be treated as part of
    R30PrepareXyzrhwState's no-duplicate-driver-read contract.
    """
    start = source.index(signature)
    opening = source.index("{", start + len(signature))
    depth = 0
    for index in range(opening, len(source)):
        ch = source[index]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return source[opening:index + 1]
    raise AssertionError("unbalanced C++ function body: " + signature)


def check(s):
    h=function_body(s,"bool R30HasXyzrhwInputLayout(")
    p=function_body(s,"bool R30PrepareXyzrhwState(")
    for token in ("FAILED(device->GetFVF(&fvf))", "if (fvf != 0)",
      "== D3DFVF_XYZRHW", "FAILED(device->GetVertexDeclaration(&declaration))",
      "declaration->GetDeclaration(elements, &count)", "declaration->Release();",
      "FAILED(hr) || count < 2u || count > MAXD3DDECLLENGTH",
      "e.Stream == 0xFFu && e.Type == D3DDECLTYPE_UNUSED",
      "i + 1u == count && positionT",
      "e.Stream != 0u || e.Method != D3DDECLMETHOD_DEFAULT",
      "e.Usage == D3DDECLUSAGE_POSITIONT", "positionT || i != 0u || e.Offset != 0u",
      "e.Type != D3DDECLTYPE_FLOAT4", "e.UsageIndex != 0u",
      "e.Offset < 4u * sizeof(float)", "e.Usage == D3DDECLUSAGE_POSITION"):
        assert token in h,token
    assert h.count("declaration->Release();") == 2  # failure path and success path
    assert "if (!R30HasXyzrhwInputLayout(device))" in p
    assert "device->GetFVF(&fvf)" not in p

def accept(fvf, elements):
    if fvf: return (fvf & 0xe)==0x4
    if elements is None or not 2<=len(elements)<=64: return False
    found=False
    for i,(stream,offset,kind,method,usage,index) in enumerate(elements):
        if stream==255 and kind==17: return i+1==len(elements) and found
        if stream!=0 or method!=0: return False
        if usage==9:
            if found or i!=0 or offset!=0 or kind!=3 or index!=0: return False
            found=True
        elif offset<16 or usage==0: return False
    return False

def main():
    s=SOURCE.read_text(encoding="utf-8")
    check(s)
    good=[(0,0,3,0,9,0),(0,16,1,0,5,0),(255,0,17,0,0,0)]
    assert accept(0x4,None) and not accept(0x2,None)
    assert accept(0,good)
    for bad in (
      [(1,0,3,0,9,0),*good[1:]],
      [(0,4,3,0,9,0),*good[1:]],
      [(0,0,2,0,9,0),*good[1:]],
      [(0,0,3,1,9,0),*good[1:]],
      [(0,0,3,0,9,1),*good[1:]],
      [good[0],(0,8,1,0,5,0),good[-1]],
      [good[0],(1,16,1,0,5,0),good[-1]],
      [good[0],(0,16,1,0,0,0),good[-1]],
      good[:-1],[*good,good[-1]],[good[0]]):
        assert not accept(0,bad),bad
    mutations=(
       ("if (fvf != 0)","if (fvf == 0)"),
       ("== D3DFVF_XYZRHW","!= D3DFVF_XYZRHW"),
       ("e.Type != D3DDECLTYPE_FLOAT4","e.Type == D3DDECLTYPE_FLOAT4"),
       ("i + 1u == count && positionT","i + 1u == count || positionT"),
       ("e.Stream != 0u || e.Method != D3DDECLMETHOD_DEFAULT","e.Stream == 0u || e.Method != D3DDECLMETHOD_DEFAULT"),
       ("if (!R30HasXyzrhwInputLayout(device))","if (R30HasXyzrhwInputLayout(device))"),
       ("declaration->Release();","// missing COM Release")
    )
    for original,replacement in mutations:
        assert original in s
        try: check(s.replace(original,replacement,1))
        except AssertionError: pass
        else: raise AssertionError("mutation escaped: "+original)
    # Mutation negative: a real GetFVF reintroduced inside the admission
    # function must still FAIL, even though F11/rank helpers legitimately
    # use the live getter elsewhere in the same translation unit.
    admission = "            if (!R30HasXyzrhwInputLayout(device))"
    assert admission in function_body(s, "bool R30PrepareXyzrhwState(")
    regressed = s.replace(admission,
        "            DWORD fvf = 0;\n"
        "            if (FAILED(device->GetFVF(&fvf))) return false;\n"
        + admission, 1)
    try:
        check(regressed)
    except AssertionError:
        pass
    else:
        raise AssertionError("duplicate XYZRHW GetFVF admission mutation escaped")
    # Independent F11's fixed-function draw identity is allowed to query
    # the actual FVF. Never remove this evidence to satisfy an XYZRHW test.
    assert "device->GetFVF(&fvf)" in function_body(
        s, "bool R30PrepareExternalImGuiProjection(")
    flow=FLOW.read_text(encoding="utf-8")
    assert "python tools/verify_vr_r30_positiont_decl.py" in flow
    assert "'tools/verify_vr_r30_positiont_decl.py'" in flow
    print("R30 POSITIONT FVF/decl model, 11 negative cases, 8 source mutations PASS")
if __name__=="__main__": main()
