from pathlib import Path
import re
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
r29 = read("src/vr/d3d9/stereo_renderer_r29.cpp")
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
    "R30SupportPresentEpoch(": ("R29OwnerCaptureFrameSnapshot().presentEpoch",),
    "R30SupportTargetIsBackBuffer(": ("R29OwnerTargetIsBackBuffer()",),
    "R30SupportAnyAuxRenderTargetActive(": ("AnyAuxRenderTargetActive()",),
    "R30SupportTryGetTrackedViewport(": ("TryGetTrackedViewport(viewport)",),
    "R30SupportInvalidateEffectStateCache(": ("InvalidateEffectStateCache()",),
    "R30SupportInvalidateTrackedRasterShadow(": ("InvalidateTrackedRasterShadow()",),
    "R30SupportInvalidateLiveStateSample(": ("InvalidateLiveStateSample()",),
    "R30SupportWorldScale(": ("Settings::VRWorldScale",),
    "R30SupportMatrixFromQuaternionTranslation(": ("R29OwnerMatrixFromQuaternionTranslation(",),
    "R30SupportInverseRigid(": ("R29OwnerInverseRigid(matrix)",),
    "R30SupportProjectionFromFov(": ("R29OwnerProjectionFromFov(base, fov)",),
    "R30SupportMultiplyMatrix(": ("R29OwnerMultiplyMatrix(a, b)",),
    "R30SupportTransposeMatrix(": ("R29OwnerTransposeMatrix(matrix)",),
    "R30SupportMatrixFinite(": ("R29OwnerMatrixFinite(matrix)",),
    "R30SupportGetInverseProjection(": ("R29OwnerGetInverseProjection(projection, inverse)",),
    "R30SupportValidateVerifiedWvp(": (
        "GetVertexShaderConstantF(",
        "OutRunWvpRegister",
        "OutRunWvpRegisterCount",
        "FloatArrayNear(live, verified, 16, VerifiedWvpEpsilon)",
    ),
    "R30SupportGetVerifiedProjection(": ("OutRunVRRenderer::GetR28VerifiedProjection(",),
    "R30SupportResynchronizeShaderEpoch(": (
        "R29OwnerResynchronizeShaderEpoch(device)",
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

# Independent R29 TU now owns matrix/shader/frame ABI. Validate BOTH ends:
# an R30 delegate with no R29 implementation is a link error; a direct
# R30 private reference is a compile error under split.
owner_pairs = {
    "R29OwnerMatrixFromQuaternionTranslation(": ("MatrixFromQuaternionTranslation(",),
    "R29OwnerInverseRigid(": ("InverseRigid(matrix)",),
    "R29OwnerProjectionFromFov(": ("ProjectionFromFov(base, fov)",),
    "R29OwnerMultiplyMatrix(": ("MultiplyMatrix(a, b)",),
    "R29OwnerTransposeMatrix(": ("TransposeMatrix(matrix)",),
    "R29OwnerMatrixFinite(": ("MatrixFinite(matrix)",),
    "R29OwnerGetInverseProjection(": ("GetInverseProjection(matrix, inverse)",),
    "R29OwnerCurrentVertexShaderIdentity(": ("CurrentVertexShaderIdentity.load(",),
    "R29OwnerResynchronizeShaderEpoch(": (
        "CurrentVertexShaderIdentity.exchange(", "VertexShaderSerial.fetch_add("),
    "R29OwnerRecordWorldStereoDuplicate(": (
        "FrameHadDuplicatedDraw = true;", "++DuplicatedDraws;",
        "FrameStereoMetadata = stereo;"),
    "R29OwnerRecordXyzrhwWorldStereoDuplicate(": (
        "FrameHadDuplicatedDraw = true;", "++DuplicatedDraws;",
        "FrameRightDrawFailed = true;",
        "PoisonFrame(OutRunVR::StereoFailurePoseSequenceMismatch);"),
    "R29OwnerRecordHudStereoDuplicate(": (
        "FrameHadDuplicatedDraw = true;", "++NonWorldDuplicatedDraws;"),
}
owner_header = read("src/vr/core/r29_owner_api.hpp")
for marker, required in owner_pairs.items():
    if marker.rstrip("(") not in owner_header:
        errors.append(f"missing R29 declared owner: {marker}")
    try:
        body = function_body(r29, marker)
    except ValueError as exc:
        errors.append(str(exc))
        continue
    for token in required:
        if token not in body:
            errors.append(f"R29 owner lost physical binding {marker}: {token}")

for raw in ("FrameHadDuplicatedDraw", "FrameStereoMetadata",
            "VertexShaderSerial", "CurrentVertexShaderIdentity"):
    if re.search(r"(?<![A-Za-z0-9_])" + raw + r"(?![A-Za-z0-9_])", r30):
        errors.append(f"R30 retained private R29 symbol: {raw}")
for must in ("R29OwnerRecordXyzrhwWorldStereoDuplicate(",
             "R29OwnerRecordHudStereoDuplicate(",
             "R29OwnerCurrentVertexShaderIdentity()"):
    if must not in r30:
        errors.append(f"R30 lost R29 owner consumer: {must}")

# Integrated R33/R32/R31/R30 build now owns explicit R30 support and
# R31 upper owners in distinct translation units. Refuse the once-dangerous
# R31/R30 split when the prerequisite R32/R31 support boundary is absent.
full_split = "-DOUTRUN_VR_REFACTOR_SPLIT_R31_R30=ON" in workflow
if full_split:
    for required in (
        "-DOUTRUN_VR_REFACTOR_SPLIT_R33_R32=ON",
        "-DOUTRUN_VR_REFACTOR_SPLIT_R32_R31=ON",
    ):
        if required not in workflow:
            errors.append("integrated full-chain split lost predecessor " + required)
    for label, body in (("cmake.toml", read("cmake.toml")),
                        ("CMakeLists.txt", read("CMakeLists.txt"))):
        if 'option(OUTRUN_VR_REFACTOR_SPLIT_R31_R30' not in body:
            errors.append(label + " lacks integrated R31/R30 split option")
        if ("src/vr/d3d9/stereo_renderer_r30.cpp\n"
                "        PROPERTIES HEADER_FILE_ONLY FALSE)" not in body):
            errors.append(label + " lacks independent lower R30 source compilation")
if "'tools/verify_vr_r30_support_api_seam.py'" not in workflow:
    errors.append("DX9Ex workflow does not execute the R30 support seam verifier")
if "'src/vr/core/r30_support_api.hpp'" not in workflow:
    errors.append("DX9Ex workflow path filter does not track the R30 support API")

# Exact owner-boundary regression: R32 must never reintroduce lower
# anonymous state/screen-space/XYZRHW symbols after this extraction.
r32 = read("src/vr/d3d9/stereo_renderer_r32.cpp")
extracted = {
    "R30SupportClassifyScreenSpacePass": ("R30ClassifyScreenSpacePass(device)",),
    "R30SupportBuildScreenSpaceEyeConstants": (
        "R30ScreenSpaceKind::Hud2D", "R30ScreenSpaceKind::FlatPerspectiveEffect",
        "default:", "return false;", "R30BuildScreenSpaceEyeConstants("),
    "R30SupportNoteScreenSpaceFovDraw": ("R30TelemetryNoteScreenSpaceFovDraw()",),
    "R30SupportTryXyzrhwPrimitiveVB": ("R30TryXyzrhwPrimitiveVB(",),
    "R30SupportTryXyzrhwIndexedPrimitiveVB": ("R30TryXyzrhwIndexedPrimitiveVB(",),
    "R30SupportTryXyzrhwPrimitiveUP": ("R30TryXyzrhwPrimitiveUP(",),
    "R30SupportTryXyzrhwIndexedPrimitiveUP": ("R30TryXyzrhwIndexedPrimitiveUP(",),
    "R30SupportCallLowerDrawPrimitive": ("R30CallLowerDrawPrimitive(",),
    "R30SupportCallLowerDrawIndexedPrimitive": ("R30CallLowerDrawIndexedPrimitive(",),
    "R30SupportCallLowerDrawPrimitiveUP": ("R30CallLowerDrawPrimitiveUP(",),
    "R30SupportCallLowerDrawIndexedPrimitiveUP": ("R30CallLowerDrawIndexedPrimitiveUP(",),
    "R30SupportRunRasterReplayGuardCallback": (
        "if (!draw) return E_INVALIDARG;",
        "R22RasterReplayGuard replay(device, site);",
        "if (!replay.StateValid()) return draw(drawContext);",
        "if (active) active(activeContext);",
        "return draw(drawContext);"),
    "R30SupportLowerPrerequisiteStatus": (
        "R22InstallStatus()", "R13InstallStatus()",
        "State::Failed", "State::Ready", "State::Pending"),
    "R30SupportDrawPrimitiveTarget": ("&DrawPrimitiveDestR30",),
    "R30SupportDrawIndexedPrimitiveTarget": ("&DrawIndexedPrimitiveDestR30",),
    "R30SupportDrawPrimitiveUPTarget": ("&DrawPrimitiveUPDestR30",),
    "R30SupportDrawIndexedPrimitiveUPTarget": ("&DrawIndexedPrimitiveUPDestR30",),
}
for marker, delegated in extracted.items():
    if marker not in header or marker not in r32:
        errors.append(f"R32/R30 public declaration or consumer missing: {marker}")
    try:
        body = function_body(r30, marker + "(")
    except ValueError as exc:
        errors.append(str(exc))
        continue
    for token in delegated:
        if token not in body:
            errors.append(f"R30 owner {marker} lost delegation: {token}")

for forbidden in (
    "R30ClassifyScreenSpacePass(", "R30BuildScreenSpaceEyeConstants(",
    "R30TelemetryNoteScreenSpaceFovDraw(", "R30TryXyzrhwPrimitiveVB(",
    "R30TryXyzrhwIndexedPrimitiveVB(", "R30TryXyzrhwPrimitiveUP(",
    "R30TryXyzrhwIndexedPrimitiveUP(", "R30CallLowerDrawPrimitive(",
    "R30CallLowerDrawIndexedPrimitive(", "R30CallLowerDrawPrimitiveUP(",
    "R30CallLowerDrawIndexedPrimitiveUP(", "R22RasterReplayGuard replay(",
    "R22InstallStatus()", "R13InstallStatus()", "R13InstallStatusValue::",
    "&DrawPrimitiveDestR30", "&DrawIndexedPrimitiveDestR30",
    "&DrawPrimitiveUPDestR30", "&DrawIndexedPrimitiveUPDestR30",
):
    if forbidden in r32:
        errors.append(f"R32 regained lower anonymous owner: {forbidden}")

for kind in ("Hud2D", "FlatPerspectiveEffect", "None"):
    if f"R30SupportScreenSpaceKind::{kind}" not in r30 or f"R30SupportScreenSpaceKind::{kind}" not in r32:
        errors.append(f"R32 screen-space semantic mapping lost: {kind}")

if errors:
    for error in errors:
        print(f"R30 support API seam FAIL: {error}")
    sys.exit(1)

print("R30 support API seam PASS")