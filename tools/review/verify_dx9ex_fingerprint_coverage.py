#!/usr/bin/env python3
"""Static Role-A verifier for the active DX9Ex draw-fingerprint boundary.

The default mode records the current fail-before evidence without failing the
review job.  Use --require-fixed when a candidate claims to close the gaps.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def contains_all(text: str, needles: tuple[str, ...]) -> bool:
    return all(needle in text for needle in needles)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--require-fixed", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()

    workflow = (root / ".github/workflows/vr-dx9ex-active.yml").read_text(
        encoding="utf-8"
    )
    r26 = (root / "src/vr/d3d9/stereo_renderer_r26.cpp").read_text(
        encoding="utf-8"
    )
    r33 = (root / "src/vr/d3d9/stereo_renderer_r33.cpp").read_text(
        encoding="utf-8"
    )
    r34 = (root / "src/vr/d3d9/stereo_renderer_r34.cpp").read_text(
        encoding="utf-8"
    )
    helper = (root / "src/vr/d3d9/shader_fingerprint_gpl.hpp").read_text(
        encoding="utf-8"
    )

    active_full_r34 = contains_all(
        workflow,
        (
            "ACTIVE_FULL_R34",
            "-DOUTRUN_VR_SAFE_DRAW_COMPARE=OFF",
            "-DOUTRUN_VR_R26_HUD_COMPARE=OFF",
            "-DOUTRUN_VR_C1_COMPARE=OFF",
            "-DOUTRUN_VR_C2_COMPARE=OFF",
        ),
    ) and '#include "stereo_renderer_r33.cpp"' in r34

    final_dispatch_has_capture = (
        "R33Dispatch" in r33 and "R46TraceShaderFingerprint" in r33
    )
    lower_fallback_has_capture = contains_all(
        r26, ("R27GuardWorldEffect", "R46TraceShaderFingerprint(device, effect)")
    )
    fixed_function_collapses = contains_all(
        helper,
        (
            "pair.vertex.value",
            "pair.pixel.value",
            "result.vertexIdentity == 0 && result.pixelIdentity == 0",
        ),
    )

    log_record = r26[
        r26.find('"VR GPL SHADER:') : r26.find('"VR GPL SHADER:') + 700
    ]
    missing_route_discriminators = not contains_all(
        log_record, ("route", "primitive", "fvf", "projection")
    )

    pointer_only_cache = contains_all(
        helper,
        (
            "reinterpret_cast<std::uintptr_t>(shader)",
            "if (entry.first == identity)",
        ),
    )

    compliance_markers = (
        "COPYING.GPL3",
        "THIRD_PARTY_GPL_NOTICES.txt",
        "shader_fingerprint_gpl.hpp",
    )
    active_package_has_compliance = all(
        marker in workflow for marker in compliance_markers
    )

    checks = {
        "activeFullR34CallPath": active_full_r34,
        "finalR33DispatchHasFingerprintCapture": final_dispatch_has_capture,
        "lowerR27FallbackHasFingerprintCapture": lower_fallback_has_capture,
        "fixedFunctionDrawsCollapseToShaderPair": fixed_function_collapses,
        "fingerprintLogMissingRouteDiscriminators": missing_route_discriminators,
        "shaderHashCacheUsesComPointerOnly": pointer_only_cache,
        "activePackageHasGplCompliancePayload": active_package_has_compliance,
    }
    unresolved = [
        name
        for name in (
            "finalR33DispatchHasFingerprintCapture",
            "activePackageHasGplCompliancePayload",
        )
        if not checks[name]
    ]
    if checks["fixedFunctionDrawsCollapseToShaderPair"]:
        unresolved.append("fixedFunctionDrawsCollapseToShaderPair")
    if checks["fingerprintLogMissingRouteDiscriminators"]:
        unresolved.append("fingerprintLogMissingRouteDiscriminators")
    if checks["shaderHashCacheUsesComPointerOnly"]:
        unresolved.append("shaderHashCacheUsesComPointerOnly")

    print(
        json.dumps(
            {
                "root": str(root),
                "checks": checks,
                "unresolved": unresolved,
                "mode": "require-fixed" if args.require_fixed else "evidence",
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 1 if args.require_fixed and unresolved else 0


if __name__ == "__main__":
    raise SystemExit(main())
