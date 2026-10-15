#!/usr/bin/env python3
"""R29/R30 borrowed stereo surface fastpath and DirectGPU snapshot regressions."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HEADER = ROOT / "src/vr/core/r29_owner_api.hpp"
OWNER = ROOT / "src/vr/d3d9/stereo_renderer_r29.cpp"
BRIDGE = ROOT / "src/vr/d3d9/stereo_renderer_r30.cpp"


def body(source: str, function: str) -> str:
    pos = source.index(function + "(")
    begin = source.index("{", pos)
    depth = 0
    for i in range(begin, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[begin:i + 1]
    raise AssertionError("unclosed function: " + function)


def verify(header: str, owner: str, bridge: str) -> None:
    # Each fast per-draw accessor returns its existing lower-owned pointer
    # directly. It must not manufacture a per-draw frame POD or own a COM ref.
    fields = (
        ("TrackedDepthStencil", "TrackedDepthStencil"),
        ("RightEyeSurface", "RightEyeSurface"),
        ("RightEyeDepth", "RightEyeDepth"),
    )
    for suffix, lower_field in fields:
        accessor = "R29OwnerBorrow" + suffix
        facade = "R30SupportBorrowed" + suffix
        assert "IDirect3DSurface9* " + accessor + "() noexcept;" in header
        owned = body(owner, accessor)
        assert "return " + lower_field + ";" in owned, accessor
        assert "R29OwnerCaptureFrameSnapshot" not in owned
        assert "AddRef" not in owned and "Release" not in owned
        routed = body(bridge, facade)
        assert "return " + accessor + "();" in routed, facade
        assert "R29OwnerCaptureFrameSnapshot" not in routed, facade

    source = body(bridge, "R30SupportTryGetDirectTransportSourceSurfaces")
    assert source.count("R29OwnerCaptureFrameSnapshot()") == 1
    assert "const auto frame = R29OwnerCaptureFrameSnapshot();" in source
    assert "out.left = frame.backBuffer;" in source
    assert "out.right = frame.rightEyeSurface;" in source
    assert "return out.left != nullptr && out.right != nullptr;" in source


def main() -> None:
    src = (HEADER.read_text(encoding="utf-8"),
           OWNER.read_text(encoding="utf-8"),
           BRIDGE.read_text(encoding="utf-8"))
    verify(*src)
    header, owner, bridge = src
    mutations = (
        (header.replace("R29OwnerBorrowRightEyeDepth() noexcept;",
                        "R29OwnerBorrowRightEyeDepth() noexcept;", 1)
          .replace("IDirect3DSurface9* R29OwnerBorrowRightEyeDepth() noexcept;",
                   "// deleted", 1), owner, bridge),
        (header, owner.replace("return TrackedDepthStencil;",
                               "return R29OwnerCaptureFrameSnapshot().trackedDepthStencil;", 1),
         bridge),
        (header, owner, bridge.replace(
            "return R29OwnerBorrowRightEyeSurface();",
            "return R29OwnerCaptureFrameSnapshot().rightEyeSurface;", 1)),
        (header, owner, bridge.replace(
            "const auto frame = R29OwnerCaptureFrameSnapshot();\n"
            "        out.left = frame.backBuffer;\n"
            "        out.right = frame.rightEyeSurface;",
            "out.left = R29OwnerCaptureFrameSnapshot().backBuffer;\n"
            "        out.right = R29OwnerCaptureFrameSnapshot().rightEyeSurface;", 1)),
        (header, owner, bridge.replace("out.right = frame.rightEyeSurface;",
                                       "out.right = frame.backBuffer;", 1)),
    )
    for number, mutant in enumerate(mutations, 1):
        assert mutant != src, ("ineffective mutation", number)
        try:
            verify(*mutant)
        except (AssertionError, ValueError):
            continue
        raise AssertionError("borrowed-surface regression escaped mutation " + str(number))
    print("PASS R29/R30 borrowed stereo surfaces, single DirectGPU snapshot, 5 negative mutations")


if __name__ == "__main__":
    main()
