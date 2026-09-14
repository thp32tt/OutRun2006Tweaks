from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8", newline="\n")


def replace_once(path: str, old: str, new: str) -> None:
    text = read(path)
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one match, found {count}: {old[:180]!r}")
    write(path, text.replace(old, new, 1))


# Frame.v1 eye positions are XrPosef positions and therefore remain in metres.
# VRWorldScale converts metres to OutRun game units only inside the D3D9 camera
# transform; applying it to the OpenXR submission pose would double-apply scale.
replace_once(
    "src/vr_renderer_probe.cpp",
    '''\t\t\t\tVec3 effectiveHeadPosition = CenterPositionValid ? CenterPosition : sample.position;
\t\t\t\tif (Settings::VRPositionalTracking && sample.positionValid && CenterPositionValid)
\t\t\t\t{
\t\t\t\t\tconst Vec3 delta{
\t\t\t\t\t\tsample.position.x - CenterPosition.x,
\t\t\t\t\t\tsample.position.y - CenterPosition.y,
\t\t\t\t\t\tsample.position.z - CenterPosition.z
\t\t\t\t\t};
\t\t\t\t\teffectiveHeadPosition = {
\t\t\t\t\t\tCenterPosition.x + delta.x * Settings::VRWorldScale,
\t\t\t\t\t\tCenterPosition.y + delta.y * Settings::VRWorldScale,
\t\t\t\t\t\tCenterPosition.z + delta.z * Settings::VRWorldScale
\t\t\t\t\t};
\t\t\t\t}
''',
    '''\t\t\t\t// Frame.v1 positions are OpenXR LOCAL-space metres. WorldScale is
\t\t\t\t// only the metres->game-units conversion used by LatchedHeadInverse.
\t\t\t\tVec3 effectiveHeadPosition = CenterPositionValid ? CenterPosition : sample.position;
\t\t\t\tif (Settings::VRPositionalTracking && sample.positionValid)
\t\t\t\t\teffectiveHeadPosition = sample.position;
''',
)
replace_once(
    "src/vr_renderer_probe.cpp",
    '''\t\t\t\t\tconst Vec3 localEye{
\t\t\t\t\t\tsample.eyeOffset[eye][0] * Settings::VRWorldScale,
\t\t\t\t\t\tsample.eyeOffset[eye][1] * Settings::VRWorldScale,
\t\t\t\t\t\tsample.eyeOffset[eye][2] * Settings::VRWorldScale
\t\t\t\t\t};
''',
    '''\t\t\t\t\t// eyeOffset is already head-local metres; keep the projection-layer
\t\t\t\t\t// pose in OpenXR units even though D3D9 multiplies IPD by WorldScale.
\t\t\t\t\tconst Vec3 localEye{
\t\t\t\t\t\tsample.eyeOffset[eye][0],
\t\t\t\t\t\tsample.eyeOffset[eye][1],
\t\t\t\t\t\tsample.eyeOffset[eye][2]
\t\t\t\t\t};
''',
)

# Record the actual right-eye failure stage instead of reporting every world-draw
# right-side error as a WVP upload failure. Correctness was already fail-closed;
# this makes limited-device diagnostics actionable.
replace_once(
    "src/vr_stereo.cpp",
    '''\t\t\tIDirect3DSurface9* savedRt = TrackedRenderTarget;
\t\t\tIDirect3DSurface9* savedDepth = TrackedDepthStencil;
\t\t\tHRESULT rightHr = D3D_OK;
\t\t\tbool restoreOk = true;
\t\t\t{
\t\t\t\tInternalPassScope guard;
\t\t\t\trightHr = SetRenderTargetHook.stdcall<HRESULT>(device, 0u, RightEyeSurface);
\t\t\t\tif (SUCCEEDED(rightHr))
\t\t\t\t\trightHr = SetDepthStencilSurfaceHook.stdcall<HRESULT>(device, RightEyeDepth);
\t\t\t\tif (SUCCEEDED(rightHr))
\t\t\t\t\trightHr = device->SetViewport(&savedViewport);
\t\t\t\tif (SUCCEEDED(rightHr) && draw.worldStereo)
\t\t\t\t\trightHr = SetWvpOneRegisterAtATime(device, draw.eyeConstants[1]) ? D3D_OK : E_FAIL;
\t\t\t\tif (SUCCEEDED(rightHr))
\t\t\t\t\trightHr = drawCall();

\t\t\t\trestoreOk = RestoreRightPassState(device, savedRt, savedDepth,
\t\t\t\t\tsavedViewport, draw.originalConstants, draw.worldStereo);
\t\t\t}
''',
    '''\t\t\tIDirect3DSurface9* savedRt = TrackedRenderTarget;
\t\t\tIDirect3DSurface9* savedDepth = TrackedDepthStencil;
\t\t\tHRESULT rightHr = D3D_OK;
\t\t\tOutRunVR::StereoFailureReason rightFailure = OutRunVR::StereoFailureRightStateFailed;
\t\t\tbool restoreOk = true;
\t\t\t{
\t\t\t\tInternalPassScope guard;
\t\t\t\trightHr = SetRenderTargetHook.stdcall<HRESULT>(device, 0u, RightEyeSurface);
\t\t\t\tif (SUCCEEDED(rightHr))
\t\t\t\t\trightHr = SetDepthStencilSurfaceHook.stdcall<HRESULT>(device, RightEyeDepth);
\t\t\t\tif (SUCCEEDED(rightHr))
\t\t\t\t\trightHr = device->SetViewport(&savedViewport);
\t\t\t\tif (SUCCEEDED(rightHr) && draw.worldStereo &&
\t\t\t\t\t!SetWvpOneRegisterAtATime(device, draw.eyeConstants[1]))
\t\t\t\t{
\t\t\t\t\trightFailure = OutRunVR::StereoFailureRightWvpUploadFailed;
\t\t\t\t\trightHr = E_FAIL;
\t\t\t\t}
\t\t\t\tif (SUCCEEDED(rightHr))
\t\t\t\t{
\t\t\t\t\trightFailure = OutRunVR::StereoFailureRightDrawFailed;
\t\t\t\t\trightHr = drawCall();
\t\t\t\t}

\t\t\t\trestoreOk = RestoreRightPassState(device, savedRt, savedDepth,
\t\t\t\t\tsavedViewport, draw.originalConstants, draw.worldStereo);
\t\t\t}
''',
)
replace_once(
    "src/vr_stereo.cpp",
    '''\t\t\tif(FAILED(rightHr)){FrameRightDrawFailed=true;PoisonFrame(draw.worldStereo?OutRunVR::StereoFailureRightWvpUploadFailed:OutRunVR::StereoFailureRightDrawFailed);}
''',
    '''\t\t\tif (FAILED(rightHr))
\t\t\t{
\t\t\t\tFrameRightDrawFailed = true;
\t\t\t\tPoisonFrame(rightFailure);
\t\t\t}
''',
)

# Session STOPPING invalidates cached captured/projection data and pose history so
# a resumed OpenXR session cannot use the previous grace-window stereo frame.
replace_once(
    "vrhost/main_stereo.cpp",
    '''                    else if (state == XR_SESSION_STATE_STOPPING && running)
                    {
                        CheckXr(xrEndSession(session), "xrEndSession");
                        running = false;
                    }
''',
    '''                    else if (state == XR_SESSION_STATE_STOPPING && running)
                    {
                        CheckXr(xrEndSession(session), "xrEndSession");
                        running = false;
                        viewHistory.Clear();
                        matchedStereoValid = false;
                        lastStereoMatchMs = 0;
                        compositor.ReferenceSpaceChanged();
                        OutRunVR::SharedRenderFrameState rf{};
                        if (renderFrames.Read(rf))
                            lastProcessedStereoFrame = rf.frameId;
                    }
''',
)

# Final unit/lifecycle/diagnostic invariants.
renderer = read("src/vr_renderer_probe.cpp")
if "delta.x * Settings::VRWorldScale" in renderer[renderer.find("effectiveHeadPosition"):renderer.find("const float w =", renderer.find("effectiveHeadPosition"))]:
    raise RuntimeError("Frame.v1 effective head pose still applies WorldScale")
if "sample.eyeOffset[eye][0] * Settings::VRWorldScale" in renderer:
    raise RuntimeError("Frame.v1 effective eye pose still applies WorldScale")

stereo = read("src/vr_stereo.cpp")
for marker in ("StereoFailureRightStateFailed", "StereoFailureRightWvpUploadFailed", "StereoFailureRightDrawFailed", "PoisonFrame(rightFailure)"):
    if marker not in stereo:
        raise RuntimeError(f"right-pass diagnostic marker missing: {marker}")

host = read("vrhost/main_stereo.cpp")
for marker in ("viewHistory.Clear();", "matchedStereoValid = false;", "lastStereoMatchMs = 0;", "compositor.ReferenceSpaceChanged();"):
    if marker not in host:
        raise RuntimeError(f"session lifecycle marker missing: {marker}")

print("OpenXR metre-space pose, right-pass diagnostics, and resume hygiene finalized")
