#!/usr/bin/env python3
"""R30 immutable VB/IB projected-depth classifier memoization regression.

The fast path eliminates an O(min(referenced_vertices, 512)) signature walk
on repeated static geometry. This validates the source fences and models
identity invalidation; it does not claim a measured Quest3 frame-time gain.
"""
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/vr/d3d9/stereo_renderer_r30.cpp"
WORKFLOW = ROOT / ".github/workflows/vr-dx9ex-active.yml"
NAME = "tools/verify_vr_r30_depth_signature_memo.py"


def segment(text, begin, end):
    return text.split(begin, 1)[1].split(end, 1)[0]


def valid(text):
    try:
        structure = segment(text,
            "struct R30XyzrhwDepthSignatureCache",
            "struct R30ScratchBuffers")
        configuration = segment(text,
            "bool R30ConfigureXyzrhwWorldEffect(",
            "// OutRun can disable Z")
        up = segment(text, "HRESULT R30TryXyzrhwIndexedPrimitiveUP(",
            "HRESULT R30TryXyzrhwPrimitiveVB(")
        nonindexed = segment(text, "HRESULT R30TryXyzrhwPrimitiveVB(",
            "HRESULT R30TryXyzrhwIndexedPrimitiveVB(")
        indexed = segment(text, "HRESULT R30TryXyzrhwIndexedPrimitiveVB(",
            "// Called on every eligible FlatPerspectiveEffect draw.")
    except (ValueError, IndexError):
        return False
    fields = ("R30ShadowCopyCache vertex", "R30ShadowCopyCache index",
              "bool indexed", "UINT vertexCount", "UINT stride",
              "float minZ", "float maxZ", "D3DMATRIX projection",
              "bool projectedDepth")
    if not all(f in structure for f in fields):
        return False
    fences = (
        "const bool canMemoize = haveBaseProjection && signatureCache &&",
        "vertexCopy && vertexCopy->entry",
        "(!indexed || (indexCopy && indexCopy->entry))",
        "signatureCache->indexed == indexed",
        "signatureCache->vertexCount == vertexCount",
        "signatureCache->stride == stride",
        "signatureCache->minZ == state.viewport.MinZ",
        "signatureCache->maxZ == state.viewport.MaxZ",
        "sameCopy(signatureCache->vertex, *vertexCopy)",
        "(!indexed || sameCopy(signatureCache->index, *indexCopy))",
        "std::memcmp(&signatureCache->projection, &baseProjection,",
        "a.entry == b.entry && a.revision == b.revision",
        "a.offset == b.offset && a.size == b.size",
        "state.rhwDepthEvidence = signatureCache->projectedDepth;",
        "R30XyzrhwHasProjectedDepthSignature(",
        "signatureCache->vertex = *vertexCopy;",
        "signatureCache->index = indexed",
        "signatureCache->projectedDepth = state.rhwDepthEvidence;",
    )
    if not all(f in configuration for f in fences):
        return False
    if not (configuration.index("if (memoHit)") <
            configuration.index("R30XyzrhwHasProjectedDepthSignature(")):
        return False
    if not (configuration.index("signatureCache->valid = false;") <
            configuration.index("signatureCache->valid = true;")):
        return False
    if "depthSignature;" not in text:
        return False
    if "depthSignature" in up:
        return False  # untracked UP caller must never borrow VB memo
    # The indexed-UP path now passes only a validated sparse touched list;
    # it must still not pass any cached shadow-signature identity.
    if "&scratch.upUsed, nullptr, nullptr, nullptr,\n" not in up or (
            "&scratch.upTouched))" not in up):
        return False
    return (
        "state, nullptr, &scratch.vertexCopy,\n"
        "                    nullptr, &scratch.depthSignature)" in nonindexed and
        "state, &scratch.used, &scratch.vertexCopy,\n"
        "                    &scratch.indexCopy, &scratch.depthSignature,\n"
        "                    &scratch.vbTouched)" in indexed
    )


def cache_key(vertex, index, count, stride, minz, maxz, projection):
    return (vertex, index, count, stride, minz, maxz, projection)


def main():
    text = SOURCE.read_text(encoding="utf-8")
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert valid(text), "R30 immutable-shadow memo safety fence missing"
    assert workflow.count(NAME) == 2, "Policy paths and active runner must agree"
    mutations = (
        ("signatureCache->vertexCount == vertexCount", "true /* vertexCount */"),
        ("signatureCache->stride == stride", "true /* stride */"),
        ("signatureCache->minZ == state.viewport.MinZ", "true /* minZ */"),
        ("signatureCache->maxZ == state.viewport.MaxZ", "true /* maxZ */"),
        ("sameCopy(signatureCache->vertex, *vertexCopy)", "true /* VB */"),
        ("(!indexed || sameCopy(signatureCache->index, *indexCopy))",
         "true /* IB */"),
        ("a.revision == b.revision", "true /* revision */"),
        ("a.offset == b.offset", "true /* offset */"),
        ("a.size == b.size", "true /* size */"),
        ("std::memcmp(&signatureCache->projection, &baseProjection,",
         "std::memcmp(&baseProjection, &baseProjection,"),
        ("signatureCache->indexed == indexed", "true /* topology */"),
        ("(!indexed || (indexCopy && indexCopy->entry))",
         "true /* IB coverage */"),
    )
    for before, after in mutations:
        assert before in text
        assert not valid(text.replace(before, after, 1)), before

    rng = random.Random(698)
    identities = set()
    baseline = cache_key(("vb-a", 7, 64, 2048),
                         ("ib-a", 2, 0, 512), 128, 16,
                         0.0, 1.0, tuple(range(16)))
    identities.add(baseline)
    for field in range(7):
        values = list(baseline)
        if field <= 1:
            item = list(values[field])
            item[rng.randrange(len(item))] = "other"
            values[field] = tuple(item)
        elif field == 6:
            item = list(values[field])
            item[6] = 0.321
            values[field] = tuple(item)
        else:
            values[field] = values[field] + 1
        assert tuple(values) != baseline
        identities.add(tuple(values))
    assert len(identities) == 8
    assert cache_key(*baseline) == baseline
    # A nonindexed VB always keys to an absent IB; an indexed VB never does.
    unindexed = list(baseline)
    unindexed[1] = None
    assert tuple(unindexed) != baseline
    print("PASS R30 VB/IB depth-signature memo: 12 negative mutations; "
          "8 independent cache invalidations; UP uncached")


if __name__ == "__main__":
    main()
