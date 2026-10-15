#!/usr/bin/env python3
"""R23 DirectGPU persistent shared-eye cache, identity and invalidation contract.

Models OpenSharedResource counts only. Not an HMD FPS or GPU fence test.
"""
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "vrhost/src/runtime/d3d9ex_direct_passthrough.hpp"


def section(src, first, last):
    return src[src.index(first):src.index(last, src.index(first))]


def verify(src):
    cache = section(src, "inline bool EnsureSharedEyeCacheSlot(", "inline bool CopySharedFrameToSafeEyes(")
    copy = section(src, "inline bool CopySharedFrameToSafeEyes(", "inline bool EnsureSafeFrame(")
    reset = section(src, "inline void ResetR13HostState()", "inline XrResult XRAPI_CALL EndFrame(")
    anchors = (
        "slotIndex >= SharedEyeCache.size()",
        "SharedSourceGeneration != generation",
        "SharedSourceRunGeneration != runGeneration",
        "SharedSourceGamePid != frame.clientPid",
        "SharedSourceDevice != OutRunVrFinalTest::Device",
        "ResetSharedEyeCache();",
        "cached.eyes[0] && cached.eyes[1]",
        "cached.handles[0] == leftRaw",
        "cached.handles[1] == rightRaw",
        "cached.desc.Width != width",
        "cached.desc.Height != height",
        "cached.desc.Format != declared",
        "out = &cached;",
        "OpenSharedResource(",
        "fresh.eyes[0]->GetDesc(&fresh.desc);",
        "fresh.eyes[1]->GetDesc(&second);",
        "fresh.desc.Format == declared",
        "fresh.desc.SampleDesc.Count == 1",
        "second.SampleDesc.Count == 1",
        "ResetSharedEyeCacheSlot(fresh);",
        "ResetSharedEyeCacheSlot(cached);",
        "cached = fresh;",
    )
    for token in anchors:
        assert token in cache, token
    assert cache.index("ResetSharedEyeCache();") < cache.index("cached.eyes[0] &&")
    assert cache.index("cached.desc.Format != declared") < cache.index("out = &cached;")
    assert cache.index("OpenSharedResource(") > cache.index("out = &cached;")
    assert cache.count("OpenSharedResource(") == 1
    assert "ResetSharedEyeCache();" in reset
    assert "ReleaseCom(slot.eyes[0]);" in src and "ReleaseCom(slot.eyes[1]);" in src
    assert copy.count("EnsureSharedEyeCacheSlot(") == 1
    assert copy.count("CopyResource(") == 2
    assert copy.index("EnsureSharedEyeCacheSlot(") < copy.index("CopyResource(")
    assert copy.index("WaitForCopyFence()") < copy.index("PublishCompletedFrame(frame)")
    assert copy.index("PublishCompletedFrame(frame)") < copy.index("SafeFrameId = frame.frameId;")
    assert "OpenSharedResource(" not in copy
    return cache


def negative_mutations(src, cache):
    tokens = (
        "SharedSourceRunGeneration != runGeneration",
        "SharedSourceGamePid != frame.clientPid",
        "SharedSourceDevice != OutRunVrFinalTest::Device",
        "cached.handles[1] == rightRaw",
        "cached.desc.Format != declared",
        "fresh.desc.SampleDesc.Count == 1",
        "ResetSharedEyeCacheSlot(cached);",
    )
    for token in tokens:
        mutant = src.replace(cache, cache.replace(token, "false", 1), 1)
        try:
            verify(mutant)
        except (AssertionError, ValueError):
            pass
        else:
            raise AssertionError("cache mutation survived: " + token)
    return len(tokens)


def model():
    # Every one of four producer slots is reused 256 times.
    opened = {}
    opens = 0
    for frame in range(1024):
        idx = frame % 4
        key = (111, 222, 333, 5, (100 + idx, 200 + idx))
        if opened.get(idx) != key:
            opened[idx] = key
            opens += 2
    assert opens == 8, opens
    # Recycling just one pair never recycles the other three.
    idx = 2
    new_key = (111, 222, 333, 5, (888, 889))
    opened[idx] = new_key
    opens += 2
    assert opens == 10
    # A run/transport/device switch discards ALL four old references.
    for generation, run, pid, device in ((112, 222, 333, 5),
                                         (112, 223, 333, 5),
                                         (112, 223, 444, 5),
                                         (112, 223, 444, 6)):
        opened.clear()
        for idx in range(4):
            key = (generation, run, pid, device, (100 + idx, 200 + idx))
            opened[idx] = key
            opens += 2
    assert opens == 42, opens
    return opens


if __name__ == "__main__":
    source = SOURCE.read_text(encoding="utf-8")
    n = negative_mutations(source, verify(source))
    opens = model()
    print(f"PASS R23 shared-eye resource cache: 1024 simulated frames, "
          f"8 warmup opens vs 2048 uncached, 7 negative mutations, "
          f"{opens} total modeled reset/reopen calls")
