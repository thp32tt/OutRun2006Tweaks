from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")

def function_body(source: str, marker: str) -> str:
    start = source.find(marker)
    if start < 0:
        raise ValueError(f"missing function marker: {marker}")
    brace = source.find("{", start)
    if brace < 0:
        raise ValueError(f"missing function body: {marker}")
    depth = 0
    for index in range(brace, len(source)):
        ch = source[index]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return source[brace:index + 1]
    raise ValueError(f"unterminated function body: {marker}")

header = read("src/vr/core/r30_support_api.hpp")
r30 = read("src/vr/d3d9/stereo_renderer_r30.cpp")
r31 = read("src/vr/d3d9/stereo_renderer_r31.cpp")
workflow = read(".github/workflows/vr-dx9ex-active.yml")
errors = []

api = (
    "R30SupportTelemetryEnabled",
    "R30SupportIsGameDevice",
    "R30SupportInternalStereoPassActive",
    "R30SupportPresentEpoch",
    "R30SupportTargetIsBackBuffer",
    "R30SupportAnyAuxRenderTargetActive",
    "R30SupportTryGetTrackedViewport",
    "R30SupportInvalidateEffectStateCache",
    "R30SupportInvalidateTrackedRasterShadow",
    "R30SupportInvalidateLiveStateSample",
    "R30SupportWorldScale",
    "R30SupportMatrixFromQuaternionTranslation",
    "R30SupportInverseRigid",
    "R30SupportProjectionFromFov",
    "R30SupportMultiplyMatrix",
    "R30SupportTransposeMatrix",
    "R30SupportMatrixFinite",
    "R30SupportGetInverseProjection",
    "R30SupportValidateVerifiedWvp",
    "R30SupportGetVerifiedProjection",
    "R30SupportResynchronizeShaderEpoch",
    "R30SupportInvalidateRendererStateAfterExternalRestore",
    "R30SupportRendererInstallStatus",
    "R30SupportPrimeTrackedRasterShadow",
)
for marker in api:
    if marker not in header:
        errors.append(f"R30 support API missing declaration: {marker}")
    if marker not in r30:
        errors.append(f"R30 support API missing implementation: {marker}")
    if marker not in r31:
        errors.append(f"R31 missing R30 support API use: {marker}")

if '#include "../core/r30_support_api.hpp"' not in r30:
    errors.append("R30 implementation missing support API header")
if '#include "../core/r30_support_api.hpp"' not in r31:
    errors.append("R31 missing explicit R30 support API boundary")
if '#include "stereo_renderer_r30.cpp"' not in r31:
    errors.append("R31 textual include must remain until the later TU-split task")
if "#ifndef OUTRUN_VR_REFACTOR_SPLIT_R31_R30" not in r31:
    errors.append("R31 split preflight guard missing")

legacy = (
    "Settings::VRTelemetry",
    "Settings::VRWorldScale",
    " IsGameDevice(",
    " InternalStereoPass",
    " PresentEpoch",
    " TargetIsBackBuffer()",
    " AnyAuxRenderTargetActive()",
    " TryGetTrackedViewport(",
    " InvalidateEffectStateCache();",
    " InvalidateTrackedRasterShadow();",
    " InvalidateLiveStateSample();",
    " MatrixFromQuaternionTranslation(",
    " InverseRigid(",
    " ProjectionFromFov(",
    " MultiplyMatrix(",
    " MatrixFinite(",
    " GetInverseProjection(",
    " TransposeMatrix(",
    "OutRunWvpRegister",
    "OutRunWvpRegisterCount",
    "VerifiedWvpEpsilon",
    "FloatArrayNear(",
    "OutRunVRRenderer::GetR28VerifiedProjection(",
    "CurrentVertexShaderIdentity",
    "VertexShaderSerial",
    "OutRunVRRenderer::R29InvalidateRendererStateAfterExternalRestore(",
    "OutRunVRRenderer::R29RendererState(",
)
for marker in legacy:
    if marker in r31:
        errors.append(f"R31 retained lower private dependency: {marker.strip()}")

if "DrawStereoState" in r31:
    errors.append("R31 retained lower private DrawStereoState type")
if "R31SupportFastWorldConstants& draw" not in r31:
    errors.append("R31 fast-world builder does not use public support constants")

delegations = {
    "R30SupportTelemetryEnabled(": ("Settings::VRTelemetry",),
    "R30SupportIsGameDevice(": ("IsGameDevice(device)",),
    "R30SupportInternalStereoPassActive(": ("InternalStereoPass",),
    "R30SupportPresentEpoch(": ("PresentEpoch",),
    "R30SupportTargetIsBackBuffer(": ("TargetIsBackBuffer()",),
    "R30SupportAnyAuxRenderTargetActive(": ("AnyAuxRenderTargetActive()",),
    "R30SupportTryGetTrackedViewport(": ("TryGetTrackedViewport(viewport)",),
    "R30SupportInvalidateEffectStateCache(": ("InvalidateEffectStateCache()",),
    "R30SupportInvalidateTrackedRasterShadow(": ("InvalidateTrackedRasterShadow()",),
    "R30SupportInvalidateLiveStateSample(": ("InvalidateLiveStateSample()",),
    "R30SupportWorldScale(": ("Settings::VRWorldScale",),
    "R30SupportMatrixFromQuaternionTranslation(": ("MatrixFromQuaternionTranslation(",),
    "R30SupportInverseRigid(": ("InverseRigid(matrix)",),
    "R30SupportProjectionFromFov(": ("ProjectionFromFov(base, fov)",),
    "R30SupportMultiplyMatrix(": ("MultiplyMatrix(a, b)",),
    "R30SupportTransposeMatrix(": ("TransposeMatrix(matrix)",),
    "R30SupportMatrixFinite(": ("MatrixFinite(matrix)",),
    "R30SupportGetInverseProjection(": ("GetInverseProjection(projection, inverse)",),
    "R30SupportValidateVerifiedWvp(": (
        "GetVertexShaderConstantF(",
        "OutRunWvpRegister",
        "OutRunWvpRegisterCount",
        "FloatArrayNear(live, verified, 16, VerifiedWvpEpsilon)",
    ),
    "R30SupportGetVerifiedProjection(": ("OutRunVRRenderer::GetR28VerifiedProjection(",),
    "R30SupportResynchronizeShaderEpoch(": (
        "CurrentVertexShaderIdentity.exchange(",
        "VertexShaderSerial.fetch_add(",
    ),
    "R30SupportInvalidateRendererStateAfterExternalRestore(": (
        "OutRunVRRenderer::R29InvalidateRendererStateAfterExternalRestore()",
    ),
    "R30SupportRendererInstallStatus(": ("OutRunVRRenderer::R29RendererState()",),
    "R30SupportPrimeTrackedRasterShadow(": ("PrimeTrackedRasterShadow(device)",),
}
for marker, expected in delegations.items():
    try:
        body = function_body(r30, marker)
    except ValueError as exc:
        errors.append(str(exc))
        continue
    for token in expected:
        if token not in body:
            errors.append(f"{marker.rstrip('(')} lost lower-owner delegation: {token}")

if "-DOUTRUN_VR_REFACTOR_SPLIT_R31_R30=ON" in workflow:
    errors.append("canonical full-chain gate still forces incomplete R31/R30 TU split")
if "'tools/verify_vr_r30_support_api_seam.py'" not in workflow:
    errors.append("DX9Ex workflow does not execute the R30 support seam verifier")
if "'src/vr/core/r30_support_api.hpp'" not in workflow:
    errors.append("DX9Ex workflow path filter does not track the R30 support API")

if errors:
    for error in errors:
        print(f"R30 support API seam FAIL: {error}")
    sys.exit(1)

print("R30 support API seam PASS")
