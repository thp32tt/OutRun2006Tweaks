#!/usr/bin/env python3
"""Guard the first R84 compile-ownership seam: explicit R32 review API."""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
api = (ROOT / "src/vr/core/r32_review_api.hpp").read_text(encoding="utf-8")
r32 = (ROOT / "src/vr/d3d9/stereo_renderer_r32.cpp").read_text(encoding="utf-8")
r33 = (ROOT / "src/vr/d3d9/stereo_renderer_r33.cpp").read_text(encoding="utf-8")
errors = []

required_api = (
    "R32ReviewEffectIsFragileLive",
    "R32ReviewGetSavedViewport",
    "R32ReviewSetWvpBatch",
    "R32ReviewRestoreRightPassState",
    "R32ReviewObserveFrameWorkload",
    "R32ReviewRunLowerFailClosedCallback",
    "R32ReviewResolveDirectTransportCallback",
    "R32ReviewRunResetLifecycleCallback",
    "R32ReviewRunPresentTelemetryCallback",
)
for marker in required_api:
    if marker not in api or marker not in r32:
        errors.append(f"R32 review API missing declaration/implementation: {marker}")

for private in (
    "R32EffectIsFragileLive(",
    "R32GetSavedViewport(",
    "R32SetWvpBatch(",
    "R32RestoreRightPassState(",
    "R32LowerFailClosed(",
    "R32ObserveFrameWorkload(",
    "R32ResolveDirectTransport(",
    "R32WithResetLifecycle(",
    "R32WithPresentTelemetry(",
):
    if private in r33:
        errors.append(f"R33 still consumes R32 private helper directly: {private}")

for public in (
    "R32ReviewEffectIsFragileLive(",
    "R32ReviewGetSavedViewport(",
    "R32ReviewSetWvpBatch(",
    "R32ReviewRestoreRightPassState(",
    "R32ReviewRunLowerFailClosed(",
    "R32ReviewObserveFrameWorkload(",
    "R32ReviewResolveDirectTransport(",
    "R32ReviewRunResetLifecycle(",
    "R32ReviewRunPresentTelemetry(",
):
    if public not in r33:
        errors.append(f"R33 missing explicit R32 review API use: {public}")

# This task intentionally prepares the seam without yet changing TU ownership.
# A later child may remove this include only after independent compilation is green.
if '#include "stereo_renderer_r32.cpp"' not in r33:
    errors.append("00507 must not retire the R33->R32 textual include yet")
if '#include "../core/r32_review_api.hpp"' not in r33:
    errors.append("R33 missing explicit R32 review API header")
if '#include "../core/r32_review_api.hpp"' not in r32:
    errors.append("R32 implementation missing its public review API contract")

if errors:
    for error in errors:
        print(f"R32 review API seam FAIL: {error}")
    sys.exit(1)
print("R32 review API seam PASS")
