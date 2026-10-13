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
    # Skipped getters must remain fenced by state generations and setters.
    for guard in ("bool maskOnly = false;", "bool frontOnly = false;"):
        assert guard in state, guard
    for guard in ("if (next.writeMask == 0)", "next.maskOnly = true;",
                  "next.mayWrite = false;", "if (next.twoSided != FALSE)",
                  "next.frontOnly = true;", "if (!next.maskOnly)"):
        assert guard in sync, guard
    assert sync.index("if (next.writeMask == 0)") < sync.index(
        "D3DRS_STENCILFAIL, &next.fail")
    assert sync.index("if (next.twoSided != FALSE)") < sync.index(
        "D3DRS_CCW_STENCILFAIL, &next.ccwFail")
    for guard in (
        "if (R29StencilWrite.maskOnly)",
        "state == D3DRS_STENCILWRITEMASK && value != 0",
        "if (R29StencilWrite.frontOnly)",
        "state == D3DRS_TWOSIDEDSTENCILMODE && value != FALSE",
        "state == D3DRS_CCW_STENCILFAIL ||",
        "state == D3DRS_CCW_STENCILZFAIL ||",
        "state == D3DRS_CCW_STENCILPASS)",
    ):
        assert guard in setter, guard
    assert setter.index("if (R29StencilWrite.maskOnly)") < setter.index(
        "case D3DRS_STENCILWRITEMASK: R29StencilWrite.writeMask = value;")
    assert setter.index("if (R29StencilWrite.frontOnly)") < setter.index(
        "case D3DRS_TWOSIDEDSTENCILMODE: R29StencilWrite.twoSided = value;")
    assert "if (!device || !R29EffectCacheCurrent())" in sync
    assert "!R29EffectCacheCurrent())" in sync
    assert "R29StencilWrite.valid = false;" in sync
    assert "R29StencilWrite = next;" in sync
    assert sync.index("!R29EffectCacheCurrent())") < sync.index("next.valid = true;")
    assert "if (!R29StencilWriteCacheCurrent())" in setter
    assert "R29RefreshStencilWritePolicy();" in setter
    assert "R29OnStencilWriteSetter(state, value);" in hook
    # A successful unrelated SetRenderState must not hit StateBlock/cache work.
    # All fourteen policy-affecting setters must retain the original fail-closed
    # recording/generation and stencil-write invalidation behavior.
    fast = hook.split("// Non-policy render states", 1)[1].split(
        "// StateBlock recording setters", 1)[0]
    policy_states = (
        "ALPHABLENDENABLE",
        "ALPHATESTENABLE",
        "ZWRITEENABLE",
        "ZENABLE",
        "CULLMODE",
        "STENCILENABLE",
        "STENCILWRITEMASK",
        "STENCILFAIL",
        "STENCILZFAIL",
        "STENCILPASS",
        "TWOSIDEDSTENCILMODE",
        "CCW_STENCILFAIL",
        "CCW_STENCILZFAIL",
        "CCW_STENCILPASS",
    )
    for name in policy_states:
        assert fast.count("case D3DRS_" + name + ":") == 1, name
    assert fast.count("case D3DRS_") == len(policy_states)
    assert "default:\n                return hr;" in fast
    assert fast.index("switch (state)") < fast.index("default:")
    assert hook.index("if (FAILED(hr)") < hook.index("// Non-policy render states")
    assert hook.index("// Non-policy render states") < hook.index(
        "StateBlockTracker::Recording()")
    assert hook.index("StateBlockTracker::Recording()") < hook.index(
        "R29OnStencilWriteSetter(state, value);")
    assert hook.count("R29StencilWrite.valid = false;") >= 2
    assert "if (state == D3DRS_STENCILENABLE)" in hook
    assert "if (R29EffectCacheCurrent() && R29Effect.stencilEnable == FALSE)" in draw
    assert "if (R29EffectCacheCurrent() && R29Effect.stencilEnable != FALSE)" in draw
    assert draw.index("if (!SurfaceHasStencil(TrackedDepthStencil))") < draw.index("return R29StencilWrite.mayWrite;")
    # Current no-write snapshots are authoritative for this Present and may
    # bypass the per-draw depth-surface GetDesc. Positive/stale cases retain
    # the existing live format probe and conservative fallback.
    no_write = "if (R29StencilWriteCacheCurrent() && !R29StencilWrite.mayWrite)"
    assert no_write in draw
    assert draw.index(no_write) < draw.index("if (!SurfaceHasStencil(TrackedDepthStencil))")
    assert draw.index(no_write) < draw.index("if (R29SyncStencilWriteState(device))")
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


def staged_reads(values):
    mask, _, _, _, two, _, _, _ = values
    return 1 if mask == 0 else (8 if two else 5)


def staged_policy(values):
    mask, fail, zfail, passed, two, cf, cz, cp = values
    if mask == 0:
        return False
    if fail or zfail or passed:
        return True
    return bool(two and (cf or cz or cp))


def stencil_format_read_model(cache_current, may_write, has_stencil, sync_ok, fallback):
    """Return classification and number of live D3D9 format probes."""
    if cache_current and not may_write:
        return False, 0
    if not has_stencil:
        return False, 1
    if sync_ok:
        return bool(may_write), 1
    return bool(fallback), 1


def main():
    verify(SRC)
    # With a coherent R29 snapshot, sync must succeed. Positive writes,
    # stale snapshots and missing stencil formats keep identical semantics.
    avoided_format_reads = 0
    for current, may_write, has_stencil, fallback in product((False, True), repeat=4):
        sync_ok = current  # cache current guarantees a successful sync
        original = (False if not has_stencil else
                    bool(may_write) if sync_ok else bool(fallback))
        optimized, reads = stencil_format_read_model(
            current, may_write, has_stencil, sync_ok, fallback)
        assert optimized == original
        assert reads == (0 if current and not may_write else 1)
        avoided_format_reads += int(reads == 0)
    assert avoided_format_reads == 4
    for values in product((0, 1, 2), repeat=8):
        assert model(values) == legacy(values), values
        assert staged_policy(values) == legacy(values), values
        assert staged_reads(values) == (1 if values[0] == 0 else
                                        (8 if values[4] else 5)), values
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
        # Mutation of either lifetime fence or negative predicate must fail;
        # a truthy OR here would incorrectly bypass live depth queries.
        ("R29StencilWriteCacheCurrent() && !R29StencilWrite.mayWrite",
         "R29StencilWriteCacheCurrent() || !R29StencilWrite.mayWrite"),
        ("R29StencilWriteCacheCurrent() && !R29StencilWrite.mayWrite",
         "R29StencilWriteCacheCurrent() && R29StencilWrite.mayWrite"),
        ("if (!SurfaceHasStencil(TrackedDepthStencil))", "if (false)"),
        ("return LeftDrawMayWriteStencil(device);", "return false;"),
        ("if (state == D3DRS_STENCILENABLE)", "if (false)"),
        ("bool maskOnly = false;", "bool maskOnly = true;"),
        ("bool frontOnly = false;", "bool frontOnly = true;"),
        ("if (next.writeMask == 0)", "if (next.writeMask != 0)"),
        ("next.maskOnly = true;", "next.maskOnly = false;"),
        ("next.mayWrite = false;", "next.mayWrite = true;"),
        ("if (next.twoSided != FALSE)", "if (next.twoSided == FALSE)"),
        ("next.frontOnly = true;", "next.frontOnly = false;"),
        ("if (R29StencilWrite.maskOnly)", "if (false)"),
        ("if (R29StencilWrite.frontOnly)", "if (false)"),
        ("state == D3DRS_STENCILWRITEMASK && value != 0",
         "state == D3DRS_STENCILWRITEMASK && value == 0"),
        ("state == D3DRS_TWOSIDEDSTENCILMODE && value != FALSE",
         "state == D3DRS_TWOSIDEDSTENCILMODE && value == FALSE"),
        ("state == D3DRS_CCW_STENCILFAIL ||",
         "state == D3DRS_CCW_STENCILFAIL &&"),
        ("if (!next.maskOnly)", "if (false)"),
    ]
    for index, (needle, mutation) in enumerate(variants, 1):
        assert needle in SRC, (index, "ineffective mutation")
        changed = SRC.replace(needle, mutation, 1)
        try:
            verify(changed)
        except (AssertionError, ValueError):
            continue
        raise AssertionError("escaped negative mutation " + str(index))
    # Destructive tests target the NEW switch rather than earlier stencil-op
    # switches. Every omitted policy field, including two-sided CCW ops,
    # must fail the regression; unrelated states retain the early return.
    begin = SRC.index("// Non-policy render states", SRC.index(
        "HRESULT __stdcall SetRenderStateDestR29("))
    end = SRC.index("// StateBlock recording setters", begin)
    fast = SRC[begin:end]
    policy_states = (
        "ALPHABLENDENABLE",
        "ALPHATESTENABLE",
        "ZWRITEENABLE",
        "ZENABLE",
        "CULLMODE",
        "STENCILENABLE",
        "STENCILWRITEMASK",
        "STENCILFAIL",
        "STENCILZFAIL",
        "STENCILPASS",
        "TWOSIDEDSTENCILMODE",
        "CCW_STENCILFAIL",
        "CCW_STENCILZFAIL",
        "CCW_STENCILPASS",
    )
    for name in policy_states:
        old = "case D3DRS_" + name + ":"
        assert fast.count(old) == 1
        changed = SRC[:begin] + fast.replace(old, "/* omitted policy */", 1) + SRC[end:]
        try:
            verify(changed)
        except (AssertionError, ValueError):
            continue
        raise AssertionError("escaped policy-state mutation " + name)
    changed = SRC[:begin] + fast.replace("default:\n                return hr;",
        "default:\n                break;", 1) + SRC[end:]
    try:
        verify(changed)
    except (AssertionError, ValueError):
        pass
    else:
        raise AssertionError("unrelated setters no longer bypass cache work")
    print("PASS R29 conditional stencil policy (6561 cases), "
          "31 negative mutations, no-write GetDesc elision and 1/5/8 D3D9 getter paths")


if __name__ == "__main__":
    main()
