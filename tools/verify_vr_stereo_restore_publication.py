#!/usr/bin/env python3
"""R84: failed right-eye state restoration must poison the current Present.

Tests real R30/R33 source contracts and negative in-memory mutations. A later
mono safety epoch alone is insufficient: the already-drawn current frame must
be excluded from DirectGPU publication and stereo SkyGlow composition.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
GUARDS = (
    ("src/vr/d3d9/stereo_renderer_r30.cpp",
     "R29OwnerMarkRightDrawFailed();",
     "R29OwnerInvalidateRightDepthStencilIfLeftMayWrite(device);",
     "R29OwnerArmMonoSafety();"),
    ("src/vr/d3d9/stereo_renderer_r33.cpp",
     "R32ReviewMarkFrameRightDrawFailed();",
     "R33InvalidateRightForLeftWrite(",
     "R32ReviewArmStereoRecoverySafety();"),
)
RESTORE = re.compile(r"if\s*\(\s*!restoreOk\s*\)\s*\{([^{}]*)\}", re.S)


def check(source: str, marker: str, invalidate: str, arm: str) -> bool:
    blocks = [match.group(1) for match in RESTORE.finditer(source)]
    return len(blocks) == 2 and all(
        marker in block and invalidate in block and arm in block and
        block.index(marker) < block.index(invalidate) < block.index(arm)
        for block in blocks
    )


def main() -> None:
    for path, marker, invalidate, arm in GUARDS:
        source = (ROOT / path).read_text(encoding="utf-8")
        assert check(source, marker, invalidate, arm), path
        # Each of the two physical paths must veto publication independently.
        for i in range(2):
            match = list(RESTORE.finditer(source))[i]
            mutant = source[:match.start(1)] + (
                match.group(1).replace(marker, "/* omitted frame veto */", 1)
            ) + source[match.end(1):]
            assert not check(mutant, marker, invalidate, arm), (path, i)
        # A accidentally inverted condition must fail the regression as well.
        mutant = source.replace("if (!restoreOk)", "if (restoreOk)", 1)
        assert not check(mutant, marker, invalidate, arm), path
    print("R84 right-eye restore failure publication veto: PASS (4 paths, 6 mutations)")


if __name__ == "__main__":
    main()
