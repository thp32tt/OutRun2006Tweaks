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
        raise RuntimeError(f"{path}: expected one match, found {count}: {old[:160]!r}")
    write(path, text.replace(old, new, 1))


# ---------------------------------------------------------------------------
# Pose.v1 reserved-slot semantics: restore slot 14/15 to width/height. Full QPC
# now belongs exclusively to Frame.v1, so no existing Pose.v1 field is repurposed.
# ---------------------------------------------------------------------------
replace_once(
    "src/vr_shared.hpp",
    '''    inline constexpr std::uint32_t ClientStereoStateIndex = 12;
    inline constexpr std::uint32_t ClientStereoFrameIndex = 13;
    inline constexpr std::uint32_t ClientStereoPresentQpcLowIndex = 14;
    inline constexpr std::uint32_t ClientStereoBackbufferHeightIndex = 15;
    inline constexpr std::uint32_t ClientStereoBackbufferWidthIndex = ClientStereoPresentQpcLowIndex;
''',
    '''    inline constexpr std::uint32_t ClientStereoStateIndex = 12;
    inline constexpr std::uint32_t ClientStereoFrameIndex = 13;
    inline constexpr std::uint32_t ClientStereoBackbufferWidthIndex = 14;
    inline constexpr std::uint32_t ClientStereoBackbufferHeightIndex = 15;
    // Source-compatibility alias only. Slot 14 retains its original width semantics;
    // exact presentation timing is carried by SharedRenderFrameState::presentQpc.
    inline constexpr std::uint32_t ClientStereoPresentQpcLowIndex = ClientStereoBackbufferWidthIndex;
''',
)

# Provide stereo with the same original projection that renderer verification uses
# when the optional culling-union projection temporarily overrides the game global.
replace_once(
    "src/vr_shared.hpp",
    '''    bool GetLatchedStereoFrame(LatchedStereoFrame& out);
    bool GetLastVerifiedWvp(float outConstants[16], std::uint32_t& generation,
''',
    '''    bool GetLatchedStereoFrame(LatchedStereoFrame& out);
    bool GetRendererBaseProjection(float outMatrix[16]);
    bool GetLastVerifiedWvp(float outConstants[16], std::uint32_t& generation,
''',
)

renderer = read("src/vr_renderer_probe.cpp")
anchor = '''\tbool GetLatchedStereoFrame(LatchedStereoFrame& out)
\t{
\t\tout = LatchedStereo;
\t\treturn out.valid;
\t}
'''
if anchor not in renderer:
    raise RuntimeError("src/vr_renderer_probe.cpp: GetLatchedStereoFrame anchor not found")
projection_export = anchor + '''
\tbool GetRendererBaseProjection(float outMatrix[16])
\t{
\t\tif (!outMatrix || !ValidateRendererGlobals() || !RendererProjection)
\t\t\treturn false;
\t\tD3DMATRIX projection{};
\t\tif (CullingProjectionOverridden)
\t\t\tprojection = CullingProjectionSaved;
\t\telse
\t\t\tstd::memcpy(&projection, RendererProjection, sizeof(projection));
\t\tif (!MatrixFinite(projection))
\t\t\treturn false;
\t\tstd::memcpy(outMatrix, &projection, sizeof(projection));
\t\treturn true;
\t}
'''
renderer = renderer.replace(anchor, projection_export, 1)
write("src/vr_renderer_probe.cpp", renderer)

replace_once(
    "src/vr_stereo.cpp",
    '''\t\tbool ReadProjection(D3DMATRIX& projection)
\t\t{
\t\t\tif (!ImageContainsRange(OutRunProjectionRva, sizeof(D3DMATRIX)))
\t\t\t\treturn false;
\t\t\tconst auto* projectionPtr = Module::exe_ptr<D3DMATRIX>(OutRunProjectionRva);
\t\t\tif (!IsReadableRange(projectionPtr, sizeof(D3DMATRIX)))
\t\t\t\treturn false;
\t\t\tstd::memcpy(&projection, projectionPtr, sizeof(projection));
\t\t\treturn MatrixFinite(projection) &&
\t\t\t\tstd::fabs(projection._34 + 1.0f) < 0.25f && std::fabs(projection._44) < 0.25f;
\t\t}
''',
    '''\t\tbool ReadProjection(D3DMATRIX& projection)
\t\t{
\t\t\tfloat rendererProjection[16]{};
\t\t\tif (OutRunVRRenderer::GetRendererBaseProjection(rendererProjection))
\t\t\t{
\t\t\t\tstd::memcpy(&projection, rendererProjection, sizeof(projection));
\t\t\t}
\t\t\telse
\t\t\t{
\t\t\t\tif (!ImageContainsRange(OutRunProjectionRva, sizeof(D3DMATRIX)))
\t\t\t\t\treturn false;
\t\t\t\tconst auto* projectionPtr = Module::exe_ptr<D3DMATRIX>(OutRunProjectionRva);
\t\t\t\tif (!IsReadableRange(projectionPtr, sizeof(D3DMATRIX)))
\t\t\t\t\treturn false;
\t\t\t\tstd::memcpy(&projection, projectionPtr, sizeof(projection));
\t\t\t}
\t\t\treturn MatrixFinite(projection) &&
\t\t\t\tstd::fabs(projection._34 + 1.0f) < 0.25f && std::fabs(projection._44) < 0.25f;
\t\t}
''',
)

# Pose.v1 publication no longer accepts/writes a QPC low word. Keep width/height
# coherent for legacy diagnostics; Frame.v1 is the only exact timing source.
stereo = read("src/vr_stereo.cpp")
stereo = stereo.replace(
    '''\t\tvoid PublishStereoState(std::uint32_t state, bool worldStereo,
\t\t\tstd::uint32_t poseSequence, std::uint32_t frameId,
\t\t\tstd::uint32_t presentQpcLow)
''',
    '''\t\tvoid PublishStereoState(std::uint32_t state, bool worldStereo,
\t\t\tstd::uint32_t poseSequence, std::uint32_t frameId)
''',
    1,
)
stereo = stereo.replace(
    '''\t\t\tif (state != OutRunVR::StereoSbsActive || poseSequence == 0 || frameId == 0 || presentQpcLow == 0)
\t\t\t{
\t\t\t\tInterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->clientStereoPoseSequence), 0);
\t\t\t\tInterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->reserved[OutRunVR::ClientStereoPresentQpcLowIndex]), 0);
\t\t\t\tInterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->reserved[OutRunVR::ClientStereoStateIndex]),
\t\t\t\t\tstatic_cast<LONG>(state));
\t\t\t\treturn;
\t\t\t}

\t\t\tInterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->clientStereoPoseSequence),
\t\t\t\tstatic_cast<LONG>(poseSequence));
\t\t\tInterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->reserved[OutRunVR::ClientStereoPresentQpcLowIndex]),
\t\t\t\tstatic_cast<LONG>(presentQpcLow));
\t\t\tInterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->reserved[OutRunVR::ClientStereoBackbufferHeightIndex]),
\t\t\t\tstatic_cast<LONG>(BackBufferDesc.Height));
''',
    '''\t\t\tInterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->reserved[OutRunVR::ClientStereoBackbufferWidthIndex]),
\t\t\t\tstatic_cast<LONG>(BackBufferDesc.Width));
\t\t\tInterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->reserved[OutRunVR::ClientStereoBackbufferHeightIndex]),
\t\t\t\tstatic_cast<LONG>(BackBufferDesc.Height));
\n\t\t\tif (state != OutRunVR::StereoSbsActive || poseSequence == 0 || frameId == 0)
\t\t\t{
\t\t\t\tInterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->clientStereoPoseSequence), 0);
\t\t\t\tInterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->reserved[OutRunVR::ClientStereoStateIndex]),
\t\t\t\t\tstatic_cast<LONG>(state));
\t\t\t\treturn;
\t\t\t}

\t\t\tInterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->clientStereoPoseSequence),
\t\t\t\tstatic_cast<LONG>(poseSequence));
''',
    1,
)
# Active/fallback/reset callers.
stereo = stereo.replace(
    '''std::uint32_t low=static_cast<std::uint32_t>(presentStart.QuadPart);if(!low)low=1;PublishStereoState(OutRunVR::StereoSbsActive,true,pendingPoseSequence,frameId,low);''',
    '''PublishStereoState(OutRunVR::StereoSbsActive,true,pendingPoseSequence,frameId);''',
    1,
)
stereo = stereo.replace("PublishStereoState(fallback,false,0,0,0);", "PublishStereoState(fallback,false,0,0);", 1)
stereo = stereo.replace("PublishStereoState(OutRunVR::StereoDisabled,false,0,0,0);", "PublishStereoState(OutRunVR::StereoDisabled,false,0,0);", 1)
write("src/vr_stereo.cpp", stereo)

# Host legacy metadata reader must not reinterpret width as QPC.
host = read("vrhost/main_stereo.cpp")
host = host.replace("        std::uint32_t presentQpcLow = 0;\n", "", 1)
host = host.replace("                out.presentQpcLow = state_->reserved[OutRunVR::ClientStereoPresentQpcLowIndex];\n", "", 1)
write("vrhost/main_stereo.cpp", host)

# Final invariants for this pass.
required = {
    "src/vr_shared.hpp": [
        "ClientStereoBackbufferWidthIndex = 14",
        "ClientStereoBackbufferHeightIndex = 15",
        "SharedRenderFrameState::presentQpc",
        "GetRendererBaseProjection",
    ],
    "src/vr_renderer_probe.cpp": ["GetRendererBaseProjection", "CullingProjectionSaved"],
    "src/vr_stereo.cpp": [
        "GetRendererBaseProjection",
        "ClientStereoBackbufferWidthIndex",
        "PublishStereoState(OutRunVR::StereoSbsActive,true,pendingPoseSequence,frameId)",
    ],
}
for path, markers in required.items():
    text = read(path)
    for marker in markers:
        if marker not in text:
            raise RuntimeError(f"{path}: final semantic invariant missing: {marker}")

if "presentQpcLow" in read("vrhost/main_stereo.cpp"):
    raise RuntimeError("host still treats Pose.v1 slot 14 as QPC low word")

print("Pose.v1 reserved semantics and culling projection contract finalized")
