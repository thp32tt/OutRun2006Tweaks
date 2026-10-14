#!/usr/bin/env python3
"""DX9Ex R32 DirectGPU: reuse validated per-slot D3D11 descriptors without per-frame GetDesc."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "vrhost/src/runtime/d3d9ex_direct_passthrough_r32.hpp"


def body(source: str, marker: str) -> str:
    at = source.index(marker)
    start = source.index("{", at)
    depth = 0
    for pos in range(start, len(source)):
        if source[pos] == "{":
            depth += 1
        elif source[pos] == "}":
            depth -= 1
            if depth == 0:
                return source[start:pos + 1]
    raise ValueError("unterminated C++ block: " + marker)


def verify(source: str) -> None:
    slot = body(source, "struct R32SharedSlotCache")
    opened = body(source, "inline bool R32OpenSharedSlot(")
    released = body(source, "inline void R32ReleaseSharedSlot(")
    reset = body(source, "inline void R32ResetDirectCaches(")
    inactive = body(source, "inline bool R32EnsureInactiveEyes(")
    copied = body(source, "inline bool CopySharedFrameToSafeEyesR32(")
    synchronized = body(source, "inline void R32SyncDirectDeviceOwner(")
    fastpath = body(source, "inline bool EnsureSafeFrameR32(")

    assert "D3D11_TEXTURE2D_DESC validatedDesc{};" in slot
    assert "ID3D11Device* device = nullptr;" in slot
    for token in ("R32ResetDirectCaches();", "ResetSafeEyes();",
                  "ResetSharedEyeCache();", "ReleaseCom(CopyFence);"):
        assert token in synchronized, "old-device resource survived epoch: " + token
    assert synchronized.index("R32ResetDirectCaches();") < synchronized.index("R32DirectDeviceOwner = current;")
    assert "R32DirectDeviceOwner == current" in synchronized
    assert fastpath.index("R32SyncDirectDeviceOwner();") < fastpath.index("SafeEyesOwnFrame(frame)")
    assert copied.index("R32SyncDirectDeviceOwner();") < copied.index("EnsureCopyFence()")
    assert "if (!OutRunVrFinalTest::Device)" in fastpath
    assert "slot = {};" in released, "eviction must drop both identities and descriptor"
    assert "R32ReleaseSharedSlot(slot);" in reset, "device/session reset must evict slots"

    hit = opened[opened.index("if (cache.eye[0]"):opened.index("++R32SharedCacheHits")]
    for token in (
        "cache.eye[0] && cache.eye[1]",
        "cache.generation == generation",
        "cache.runGeneration == runGeneration",
        "cache.gamePid == gamePid",
        "cache.leftHandle == left && cache.rightHandle == right",
        "cache.width == width && cache.height == height",
        "cache.format == declared",
        "cache.device == OutRunVrFinalTest::Device",
    ):
        assert token in hit, "stale slot descriptor reuse: " + token
    assert "cache.device = OutRunVrFinalTest::Device;" in opened
    assert "R32ReleaseSharedSlot(cache);" in opened
    assert opened.count("->GetDesc(") == 2, "descriptor reads must occur only on cache miss"
    for token in (
        "desc[0].Width == width", "desc[0].Height == height",
        "desc[1].Width == width", "desc[1].Height == height",
        "desc[0].Format == declared", "desc[1].Format == declared",
        "desc[0].SampleDesc.Count == 1 && desc[1].SampleDesc.Count == 1",
    ):
        assert token in opened, "producer validation lost: " + token
    assert opened.index("if (!valid)") < opened.index("cache.validatedDesc = desc[0];")
    assert opened.index("cache.validatedDesc = desc[0];") < opened.index("cache.generation = generation;")
    assert "R32ReleaseSharedSlot(cache);" in body(opened, "if (!valid)")
    assert "R32InactiveWidth == source.Width" in inactive
    assert "R32InactiveHeight == source.Height" in inactive
    assert "R32InactiveFormat == source.Format" in inactive
    assert "R32InactiveDevice == OutRunVrFinalTest::Device" in inactive
    assert "R32InactiveDevice = OutRunVrFinalTest::Device;" in inactive
    assert "R32InactiveDevice = nullptr;" in body(source, "inline void R32ReleaseInactiveEyes(")

    assert "GetDesc(" not in copied, "hot-frame D3D11 GetDesc round trip returned"
    assert "R32EnsureInactiveEyes(source->validatedDesc)" in copied
    for token in (
        "CopyResource(\n            R32InactiveEye[0], source->eye[0])",
        "CopyResource(\n            R32InactiveEye[1], source->eye[1])",
        "if (!WaitForCopyFence())",
        "if (!PublishCompletedFrame(frame))",
        "std::swap(SafeEye[eye], R32InactiveEye[eye]);",
        "SafeFrameId = frame.frameId;",
    ):
        assert token in copied, "safe copy/ACK/swap contract lost: " + token
    assert copied.index("WaitForCopyFence()") < copied.index("PublishCompletedFrame(frame)") < copied.index("std::swap(SafeEye[eye]")


def main() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    verify(source)
    mutations = (
        ("no_descriptor", "D3D11_TEXTURE2D_DESC validatedDesc{};", ""),
        ("ignore_slot_device", "cache.device == OutRunVrFinalTest::Device", "true"),
        ("ignore_inactive_device", "R32InactiveDevice == OutRunVrFinalTest::Device", "true"),
        ("keep_fence_after_reset", "ReleaseCom(CopyFence);", "/* stale D3D11 fence */"),
        ("keep_active_pair_after_reset", "ResetSafeEyes();", "/* stale active pair */"),
        ("keep_slot_cache_after_reset", "R32ResetDirectCaches();", "/* stale producer slots */"),
        ("accept_old_safeeye_frame", "R32SyncDirectDeviceOwner();\n        if (!OutRunVrFinalTest::Device)", "if (!OutRunVrFinalTest::Device)"),
        ("reuse_old_copy_fence", "R32SyncDirectDeviceOwner();\n        if (!OutRunVrFinalTest::Device ||", "if (!OutRunVrFinalTest::Device ||"),
        ("no_identity_generation", "cache.generation == generation", "true"),
        ("no_identity_pid", "cache.gamePid == gamePid", "true"),
        ("no_identity_handle", "cache.leftHandle == left && cache.rightHandle == right", "true"),
        ("no_identity_size", "cache.width == width && cache.height == height", "true"),
        ("no_eye_format_check", "desc[1].Format == declared", "true"),
        ("no_sample_check", "desc[0].SampleDesc.Count == 1 && desc[1].SampleDesc.Count == 1", "true"),
        ("no_descriptor_publish", "cache.validatedDesc = desc[0];", ""),
        ("lost_cache_clear", "slot = {};", "/* descriptor not evicted */"),
        ("hot_getdesc", "if (!R32EnsureInactiveEyes(source->validatedDesc))",
            "source->eye[0]->GetDesc(&desc);\n        if (!R32EnsureInactiveEyes(source->validatedDesc))"),
        ("wrong_eyes", "R32InactiveEye[1], source->eye[1]", "R32InactiveEye[1], source->eye[0]"),
        ("no_fence", "if (!WaitForCopyFence())", "if (false)"),
        ("no_ack", "if (!PublishCompletedFrame(frame))", "if (false)"),
    )
    for name, old, new in mutations:
        mutant = source.replace(old, new, 1)
        assert mutant != source, "ineffective negative mutation: " + name
        try:
            verify(mutant)
        except (AssertionError, ValueError):
            continue
        raise AssertionError("escaped negative mutation: " + name)
    print(f"PASS R32 DirectGPU validated descriptor cache: no frame GetDesc, {len(mutations)} mutations")


if __name__ == "__main__":
    main()
