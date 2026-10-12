#!/usr/bin/env python3
"""R29 positive-stencil fastpath; StateBlock, setter and draw safety regression."""
from itertools import product
from pathlib import Path

SRC = (Path(__file__).resolve().parents[1] /
       "src/vr/d3d9/stereo_renderer_r29.cpp").read_text(encoding="utf-8")
STATES = (
    "STENCILWRITEMASK", "STENCILFAIL", "STENCILZFAIL", "STENCILPASS",
    "TWOSIDEDSTENCILMODE", "CCW_STENCILFAIL", "CCW_STENCILZFAIL", "CCW_STENCILPASS",
)
FIELDS = ("writeMask", "fail", "zFail", "pass", "twoSided",
          "ccwFail", "ccwZFail", "ccwPass")


def body(source, signature):
    pos = source.index(signature)
    begin = source.index("{", pos)
    depth = 0
    for end in range(begin, len(source)):
        depth += (source[end] == "{") - (source[end] == "}")
        if depth == 0:
            return source[begin:end + 1]
    raise AssertionError("unclosed " + signature)


def verify(source):
    state = body(source, "struct R29StencilWriteState")
    policy = body(source, "void R29RefreshStencilWritePolicy() noexcept")
    current = body(source, "bool R29StencilWriteCacheCurrent() noexcept")
    sync = body(source, "bool R29SyncStencilWriteState(")
    setter = body(source, "void R29OnStencilWriteSetter(")
    hook = body(source, "HRESULT __stdcall SetRenderStateDestR29(")
    draw = body(source, "bool R29OwnerLeftDrawMayWriteStencil(")
    for field in FIELDS:
        assert "DWORD " + field + " =" in state
        assert "&next." + field in sync
        assert "R29StencilWrite." + field + " = value;" in setter
    for name in STATES:
        assert "D3DRS_" + name in sync
        assert setter.count("case D3DRS_" + name + ":") == 2
    for phrase in (
        "state.writeMask != 0",
        "state.fail != D3DSTENCILOP_KEEP",
        "state.zFail != D3DSTENCILOP_KEEP",
        "state.pass != D3DSTENCILOP_KEEP",
        "state.twoSided != FALSE",
        "state.ccwFail != D3DSTENCILOP_KEEP",
        "state.ccwZFail != D3DSTENCILOP_KEEP",
        "state.ccwPass != D3DSTENCILOP_KEEP",
    ):
        assert phrase in policy, phrase
    for phrase in ("R29StencilWrite.valid && R29EffectCacheCurrent()",
                   "R29StencilWrite.presentEpoch == PresentEpoch",
                   "R29StencilWrite.applyGeneration == R29Effect.applyGeneration",
                   "R29StencilWrite.recordingGeneration == R29Effect.recordingGeneration"):
        assert phrase in current
    assert "if (!device || !R29EffectCacheCurrent())" in sync
    assert "!R29EffectCacheCurrent())" in sync
    assert "R29StencilWrite.valid = false;" in sync
    assert "R29StencilWrite = next;" in sync
    assert sync.index("!R29EffectCacheCurrent())") < sync.index("next.valid = true;")
    assert "if (!R29StencilWriteCacheCurrent())" in setter
    assert "R29RefreshStencilWritePolicy();" in setter
    assert "R29OnStencilWriteSetter(state, value);" in hook
    assert hook.count("R29StencilWrite.valid = false;") >= 2
    assert "if (state == D3DRS_STENCILENABLE)" in hook
    assert "if (R29EffectCacheCurrent() && R29Effect.stencilEnable == FALSE)" in draw
    assert "if (R29EffectCacheCurrent() && R29Effect.stencilEnable != FALSE)" in draw
    assert draw.index("if (!SurfaceHasStencil(TrackedDepthStencil))") < draw.index("return R29StencilWrite.mayWrite;")
    assert "if (R29SyncStencilWriteState(device))" in draw
    assert "return LeftDrawMayWriteStencil(device);" in draw


def model(values):
    mask, fail, zfail, passed, two, cf, cz, cp = values
    return bool(mask and (fail or zfail or passed or (two and (cf or cz or cp))))


def legacy(values):
    mask, fail, zfail, passed, two, cf, cz, cp = values
    if mask == 0:
        return False
    if fail != 0 or zfail != 0 or passed != 0:
        return True
    if not two:
        return False
    return bool(cf != 0 or cz != 0 or cp != 0)


def main():
    verify(SRC)
    for values in product((0, 1, 2), repeat=8):
        assert model(values) == legacy(values), values
    variants = [
        ("state.writeMask != 0", "state.writeMask == 0"),
        ("state.fail != D3DSTENCILOP_KEEP", "state.fail == D3DSTENCILOP_KEEP"),
        ("state.zFail != D3DSTENCILOP_KEEP", "state.zFail == D3DSTENCILOP_KEEP"),
        ("state.pass != D3DSTENCILOP_KEEP", "state.pass == D3DSTENCILOP_KEEP"),
        ("state.twoSided != FALSE", "state.twoSided == FALSE"),
        ("state.ccwFail != D3DSTENCILOP_KEEP", "state.ccwFail == D3DSTENCILOP_KEEP"),
        ("state.ccwZFail != D3DSTENCILOP_KEEP", "state.ccwZFail == D3DSTENCILOP_KEEP"),
        ("state.ccwPass != D3DSTENCILOP_KEEP", "state.ccwPass == D3DSTENCILOP_KEEP"),
        ("R29StencilWrite.applyGeneration == R29Effect.applyGeneration",
         "R29StencilWrite.applyGeneration != R29Effect.applyGeneration"),
        ("R29StencilWrite.recordingGeneration == R29Effect.recordingGeneration",
         "R29StencilWrite.recordingGeneration != R29Effect.recordingGeneration"),
        ("R29StencilWrite.presentEpoch == PresentEpoch",
         "R29StencilWrite.presentEpoch != PresentEpoch"),
        ("if (!R29StencilWriteCacheCurrent())", "if (false)"),
        ("R29OnStencilWriteSetter(state, value);", "/* missing setter */"),
        ("if (!SurfaceHasStencil(TrackedDepthStencil))", "if (false)"),
        ("return LeftDrawMayWriteStencil(device);", "return false;"),
        ("if (state == D3DRS_STENCILENABLE)", "if (false)"),
    ]
    for index, (needle, mutation) in enumerate(variants, 1):
        assert needle in SRC, (index, "ineffective mutation")
        changed = SRC.replace(needle, mutation, 1)
        try:
            verify(changed)
        except (AssertionError, ValueError):
            continue
        raise AssertionError("escaped negative mutation " + str(index))
    print("PASS R29 stencil write-cache model (6561 cases), 16 negative mutations")


if __name__ == "__main__":
    main()
