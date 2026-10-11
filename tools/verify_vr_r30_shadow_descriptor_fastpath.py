#!/usr/bin/env python3
"""R30 XYZRHW immutable VB/IB descriptor hot-path contract and negative tests."""
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "src/vr/d3d9/stereo_renderer_r30.cpp"


def body(text, signature):
    begin = text.index("{", text.index(signature))
    depth = 0
    for pos in range(begin, len(text)):
        if text[pos] == "{":
            depth += 1
        elif text[pos] == "}":
            depth -= 1
            if depth == 0:
                return text[begin:pos + 1]
    raise AssertionError("unclosed function " + signature)


def validate(source):
    ensure_vb = body(source, "R30ShadowPtr R30EnsureVertexShadow(")
    ensure_ib = body(source, "R30ShadowPtr R30EnsureIndexShadow(")
    copy_vb = body(source, "bool R30CopyVertexShadow(")
    copy_ib = body(source, "bool R30CopyIndexShadow(")
    draw_vb = body(source, "HRESULT R30TryXyzrhwPrimitiveVB(")
    draw_ib = body(source, "HRESULT R30TryXyzrhwIndexedPrimitiveVB(")
    assert "buffer->GetDesc(&desc)" in ensure_vb
    assert "buffer->GetDesc(&desc)" in ensure_ib
    assert "entry->size = desc.Size;" in ensure_vb
    assert "entry->size = desc.Size;" in ensure_ib
    assert "entry->indexFormat = desc.Format;" in ensure_ib
    assert "R30VertexShadows.erase(buffer);" in source
    assert "R30IndexShadows.erase(buffer);" in source
    assert "R30VertexShadows.clear();" in source
    assert "R30IndexShadows.clear();" in source
    for copy, signature in ((copy_vb, "const R30ShadowPtr& entry,"),
                            (copy_ib, "const R30ShadowPtr& entry,")):
        assert signature in source
        assert "if (!entry)" in copy
        assert "offset > entry->size || size > entry->size - offset" in copy
        assert "R30RangeValid(entry->valid, offset, offset + size)" in copy
        assert "std::lock_guard<std::mutex> lock(entry->mutex)" in copy
        assert "R30FindVertexShadow(" not in copy
        assert "R30FindIndexShadow(" not in copy
    for draw in (draw_vb, draw_ib):
        assert "GetDesc(" not in draw
        assert "R30EnsureVertexShadow(vb)" in draw
        assert "firstByte > desc.Size" not in draw
        assert "R30CopyVertexShadow(vbShadow," in draw
        assert "return E_NOTIMPL;" in draw
    assert "if (!vbShadow)" in draw_vb
    assert "firstByte > vbShadow->size" in draw_vb
    assert "byteCount > vbShadow->size - firstByte" in draw_vb
    assert "firstByte > UINT_MAX || byteCount > UINT_MAX" in draw_vb
    assert "R30EnsureIndexShadow(ib)" in draw_ib
    assert "if (!vbShadow || !ibShadow ||" in draw_ib
    assert "ibShadow->indexFormat != D3DFMT_INDEX16" in draw_ib
    assert "ibShadow->indexFormat != D3DFMT_INDEX32" in draw_ib
    assert "firstIndexByte > ibShadow->size" in draw_ib
    assert "indexBytes > ibShadow->size - firstIndexByte" in draw_ib
    assert "firstIndexByte > UINT_MAX || indexBytes > UINT_MAX" in draw_ib
    assert "firstVertexByte > vbShadow->size" in draw_ib
    assert "vertexBytes > vbShadow->size - firstVertexByte" in draw_ib
    assert "firstVertexByte > UINT_MAX || vertexBytes > UINT_MAX" in draw_ib
    assert "R30CopyIndexShadow(ibShadow," in draw_ib
    assert "rebased, ibShadow->indexFormat," in draw_ib


def main():
    source = SOURCE.read_text(encoding="utf-8")
    validate(source)
    mutations = (
        ("if (!vbShadow)", "if (false)"),
        ("firstByte > vbShadow->size", "false"),
        ("byteCount > vbShadow->size - firstByte", "false"),
        ("if (!vbShadow || !ibShadow ||", "if (false ||"),
        ("ibShadow->indexFormat != D3DFMT_INDEX32", "false"),
        ("firstIndexByte > ibShadow->size", "false"),
        ("indexBytes > ibShadow->size - firstIndexByte", "false"),
        ("firstVertexByte > vbShadow->size", "false"),
        ("vertexBytes > vbShadow->size - firstVertexByte", "false"),
        ("R30CopyIndexShadow(ibShadow,", "R30CopyIndexShadow(ib,"),
        ("R30CopyVertexShadow(vbShadow,", "R30CopyVertexShadow(vb,"),
    )
    for needle, bad in mutations:
        assert needle in source, needle
        mutant = source.replace(needle, bad, 1)
        try:
            validate(mutant)
        except AssertionError:
            pass
        else:
            raise AssertionError("mutation survived: " + needle)
    print("PASS R30 immutable VB/IB shadow descriptor fastpath; 11 negative mutations")


if __name__ == "__main__":
    main()
