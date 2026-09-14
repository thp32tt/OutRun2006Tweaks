from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def write(rel, text):
    (ROOT / rel).write_text(text, encoding="utf-8", newline="\n")


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one exact match, got {count}")
    return text.replace(old, new, 1)


def sub_once(text, pattern, repl, label):
    out, count = re.subn(pattern, repl, text, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError(f"{label}: expected one regex match, got {count}")
    return out


# -----------------------------------------------------------------------------
# Shared IPC ABI v2: explicit adapter contract + interop probe + 4-slot frame ring
# -----------------------------------------------------------------------------
rel = "src/vr_shared.hpp"
s = read(rel)
if "SharedRenderFrameRing" not in s:
    s = replace_once(s,
        'inline constexpr wchar_t SharedMemoryName[] = L"Local\\\\OutRun2006Tweaks.VR.Pose.v1";\n'
        '    inline constexpr std::uint32_t SharedMagic = 0x5256524Fu; // \'ORVR\' in little endian\n'
        '    inline constexpr std::uint32_t SharedProtocolVersion = 1;\n\n'
        '    inline constexpr wchar_t RenderFrameMemoryName[] = L"Local\\\\OutRun2006Tweaks.VR.Frame.v1";\n'
        '    inline constexpr std::uint32_t RenderFrameMagic = 0x4656524Fu; // \'ORVF\'\n'
        '    inline constexpr std::uint32_t RenderFrameProtocolVersion = 1;\n',
        'inline constexpr wchar_t SharedMemoryName[] = L"Local\\\\OutRun2006Tweaks.VR.Pose.v2";\n'
        '    inline constexpr std::uint32_t SharedMagic = 0x5256524Fu; // \'ORVR\' in little endian\n'
        '    inline constexpr std::uint32_t SharedProtocolVersion = 2;\n\n'
        '    inline constexpr wchar_t RenderFrameMemoryName[] = L"Local\\\\OutRun2006Tweaks.VR.Frame.v2";\n'
        '    inline constexpr std::uint32_t RenderFrameMagic = 0x4656524Fu; // \'ORVF\'\n'
        '    inline constexpr std::uint32_t RenderFrameProtocolVersion = 2;\n'
        '    inline constexpr std::uint32_t RenderFrameRingSize = 4;\n',
        "ipc version")

    s = replace_once(s,
        '        HostDirectGpuTransport = 1u << 8,\n'
        '        HostDirectGpuReady = 1u << 9,\n',
        '        HostDirectGpuTransport = 1u << 8,\n'
        '        HostDirectGpuReady = 1u << 9,\n'
        '        HostAdapterLuidValid = 1u << 10,\n',
        "host adapter flag")

    s = replace_once(s,
        '    inline constexpr std::uint32_t RenderFrameDirectGenerationIndex = 5;\n',
        '    inline constexpr std::uint32_t RenderFrameDirectGenerationIndex = 5;\n'
        '    inline constexpr std::uint32_t RenderFrameDirectSlotIndex = 6;\n',
        "direct slot index")

    s = replace_once(s,
        '        std::uint32_t recommendedWidth[2];\n'
        '        std::uint32_t recommendedHeight[2];\n'
        '        char runtimeName[64];\n',
        '        std::uint32_t recommendedWidth[2];\n'
        '        std::uint32_t recommendedHeight[2];\n'
        '        std::uint32_t hostAdapterLuidLow;\n'
        '        std::uint32_t hostAdapterLuidHigh;\n'
        '        volatile std::uint32_t clientAdapterLuidLow;\n'
        '        volatile std::uint32_t clientAdapterLuidHigh;\n'
        '        volatile std::uint32_t clientInteropProbeHandle;\n'
        '        volatile std::uint32_t clientInteropProbeToken;\n'
        '        volatile std::uint32_t hostInteropProbeAckToken;\n'
        '        volatile std::uint32_t hostDirectConsumedFrameId;\n'
        '        char runtimeName[64];\n',
        "pose transport fields")

    ring_struct = '''\n    struct SharedRenderFrameRing\n    {\n        std::uint32_t magic;\n        std::uint32_t protocolVersion;\n        std::uint32_t structSize;\n        std::uint32_t slotCount;\n        volatile std::uint32_t publishSequence;\n        volatile std::uint32_t latestSlot;\n        volatile std::uint32_t clientPid;\n        std::uint32_t reserved0;\n        SharedRenderFrameState slots[RenderFrameRingSize];\n    };\n'''
    s = replace_once(s,
        '    };\n#pragma pack(pop)\n\n    static_assert(sizeof(SharedFov) == 16);',
        '    };\n' + ring_struct + '#pragma pack(pop)\n\n    static_assert(sizeof(SharedFov) == 16);',
        "frame ring struct")

    s = replace_once(s,
        '    static_assert(sizeof(SharedPoseState) == 248);\n'
        '    static_assert(offsetof(SharedPoseState, recommendedWidth) == 104);\n'
        '    static_assert(offsetof(SharedPoseState, recommendedHeight) == 112);\n'
        '    static_assert(offsetof(SharedPoseState, runtimeName) == 120);\n'
        '    static_assert(offsetof(SharedPoseState, reserved) == 184);\n',
        '    static_assert(sizeof(SharedPoseState) == 280);\n'
        '    static_assert(offsetof(SharedPoseState, recommendedWidth) == 104);\n'
        '    static_assert(offsetof(SharedPoseState, recommendedHeight) == 112);\n'
        '    static_assert(offsetof(SharedPoseState, hostAdapterLuidLow) == 120);\n'
        '    static_assert(offsetof(SharedPoseState, runtimeName) == 152);\n'
        '    static_assert(offsetof(SharedPoseState, reserved) == 216);\n',
        "pose abi asserts")
    s = replace_once(s,
        '    static_assert(sizeof(SharedRenderFrameState) == 256);\n',
        '    static_assert(sizeof(SharedRenderFrameState) == 256);\n'
        '    static_assert(sizeof(SharedRenderFrameRing) == 1056);\n',
        "ring abi assert")
    write(rel, s)


# -----------------------------------------------------------------------------
# x86 producer: fail-closed D3D9Ex/LUID/probe gate + 4 fenced stereo resource slots
# -----------------------------------------------------------------------------
rel = "src/vr_stereo.cpp"
s = read(rel)
if "DirectInteropProbeToken" not in s:
    s = replace_once(s,
        '\t\tOutRunVR::SharedRenderFrameState* RenderFrameState = nullptr;\n',
        '\t\tOutRunVR::SharedRenderFrameRing* RenderFrameRing = nullptr;\n',
        "frame ring pointer")

    old_direct_globals = '''\t\tIDirect3DTexture9* DirectLeftTexture = nullptr;\n\t\tIDirect3DSurface9* DirectLeftSurface = nullptr;\n\t\tIDirect3DTexture9* DirectRightTexture = nullptr;\n\t\tIDirect3DSurface9* DirectRightSurface = nullptr;\n\t\tIDirect3DQuery9* DirectTransportFence = nullptr;\n\t\tHANDLE DirectLeftSharedHandle = nullptr;\n\t\tHANDLE DirectRightSharedHandle = nullptr;\n\t\tD3DFORMAT DirectTransportFormat = D3DFMT_UNKNOWN;\n\t\tstd::uint32_t DirectTransportGeneration = 0;\n\t\tbool DirectTransportResourcesReady = false;\n'''
    new_direct_globals = '''\t\tstruct DirectTransportSlot\n\t\t{\n\t\t\tIDirect3DTexture9* leftTexture = nullptr;\n\t\t\tIDirect3DSurface9* leftSurface = nullptr;\n\t\t\tIDirect3DTexture9* rightTexture = nullptr;\n\t\t\tIDirect3DSurface9* rightSurface = nullptr;\n\t\t\tIDirect3DQuery9* fence = nullptr;\n\t\t\tHANDLE leftHandle = nullptr;\n\t\t\tHANDLE rightHandle = nullptr;\n\t\t\tstd::uint32_t frameId = 0;\n\t\t};\n\n\t\tstd::array<DirectTransportSlot, OutRunVR::RenderFrameRingSize> DirectTransportSlots{};\n\t\tIDirect3DTexture9* DirectInteropProbeTexture = nullptr;\n\t\tIDirect3DSurface9* DirectInteropProbeSurface = nullptr;\n\t\tIDirect3DQuery9* DirectInteropProbeFence = nullptr;\n\t\tHANDLE DirectInteropProbeHandle = nullptr;\n\t\tstd::uint32_t DirectInteropProbeToken = 0;\n\t\tstd::uint32_t ActiveDirectTransportSlot = 0;\n\t\tD3DFORMAT DirectTransportFormat = D3DFMT_UNKNOWN;\n\t\tstd::uint32_t DirectTransportGeneration = 0;\n\t\tbool DirectTransportResourcesReady = false;\n\t\tbool DirectInteropVerified = false;\n'''
    s = replace_once(s, old_direct_globals, new_direct_globals, "direct globals")

    s = replace_once(s,
        '\t\tstd::uint64_t DirectTransportFenceTimeouts = 0;\n',
        '\t\tstd::uint64_t DirectTransportFenceTimeouts = 0;\n'
        '\t\tstd::uint64_t DirectTransportRingBackpressure = 0;\n'
        '\t\tstd::uint64_t DirectInteropProbeFailures = 0;\n',
        "direct counters")
    s = replace_once(s,
        '\t\tbool FirstDirectFallbackLogged = false;\n',
        '\t\tbool FirstDirectFallbackLogged = false;\n'
        '\t\tbool FirstD3D9ExUnavailableLogged = false;\n'
        '\t\tbool FirstAdapterMismatchLogged = false;\n'
        '\t\tbool FirstInteropVerifiedLogged = false;\n',
        "direct logs")

    new_ring_state = r'''\t\tbool EnsureRenderFrameState()\n\t\t{\n\t\t\tif (RenderFrameRing)\n\t\t\t\treturn RenderFrameRing->magic == OutRunVR::RenderFrameMagic &&\n\t\t\t\t\tRenderFrameRing->protocolVersion == OutRunVR::RenderFrameProtocolVersion &&\n\t\t\t\t\tRenderFrameRing->structSize == sizeof(OutRunVR::SharedRenderFrameRing) &&\n\t\t\t\t\tRenderFrameRing->slotCount == OutRunVR::RenderFrameRingSize;\n\t\t\tRenderFrameMapping = CreateFileMappingW(INVALID_HANDLE_VALUE, nullptr, PAGE_READWRITE, 0,\n\t\t\t\tstatic_cast<DWORD>(sizeof(OutRunVR::SharedRenderFrameRing)), OutRunVR::RenderFrameMemoryName);\n\t\t\tif (!RenderFrameMapping) return false;\n\t\t\tconst bool existed = GetLastError() == ERROR_ALREADY_EXISTS;\n\t\t\tRenderFrameRing = static_cast<OutRunVR::SharedRenderFrameRing*>(MapViewOfFile(\n\t\t\t\tRenderFrameMapping, FILE_MAP_ALL_ACCESS, 0, 0, sizeof(OutRunVR::SharedRenderFrameRing)));\n\t\t\tif (!RenderFrameRing) return false;\n\t\t\tif (!existed)\n\t\t\t{\n\t\t\t\tstd::memset(RenderFrameRing, 0, sizeof(*RenderFrameRing));\n\t\t\t\tRenderFrameRing->protocolVersion = OutRunVR::RenderFrameProtocolVersion;\n\t\t\t\tRenderFrameRing->structSize = sizeof(*RenderFrameRing);\n\t\t\t\tRenderFrameRing->slotCount = OutRunVR::RenderFrameRingSize;\n\t\t\t\tfor (auto& slot : RenderFrameRing->slots)\n\t\t\t\t{\n\t\t\t\t\tslot.protocolVersion = OutRunVR::RenderFrameProtocolVersion;\n\t\t\t\t\tslot.structSize = sizeof(slot);\n\t\t\t\t\tslot.magic = OutRunVR::RenderFrameMagic;\n\t\t\t\t}\n\t\t\t\tMemoryBarrier();\n\t\t\t\tRenderFrameRing->magic = OutRunVR::RenderFrameMagic;\n\t\t\t}\n\t\t\treturn RenderFrameRing->magic == OutRunVR::RenderFrameMagic &&\n\t\t\t\tRenderFrameRing->protocolVersion == OutRunVR::RenderFrameProtocolVersion &&\n\t\t\t\tRenderFrameRing->structSize == sizeof(*RenderFrameRing) &&\n\t\t\t\tRenderFrameRing->slotCount == OutRunVR::RenderFrameRingSize;\n\t\t}\n'''
    s = sub_once(s,
        r'\t\tbool EnsureRenderFrameState\(\)\n\t\t\{.*?\n\t\t\}\n(?=\t\tvoid PoisonFrame)',
        new_ring_state,
        "frame ring mapping")

    release_new = '''\t\t\tStereoResourcesReady = false;\n\t\t\tDirectTransportResourcesReady = false;\n\t\t\tfor (auto& slot : DirectTransportSlots)\n\t\t\t{\n\t\t\t\tReleaseCom(slot.fence);\n\t\t\t\tReleaseCom(slot.leftSurface);\n\t\t\t\tReleaseCom(slot.leftTexture);\n\t\t\t\tReleaseCom(slot.rightSurface);\n\t\t\t\tReleaseCom(slot.rightTexture);\n\t\t\t\tslot = {};\n\t\t\t}\n\t\t\tReleaseCom(DirectInteropProbeFence);\n\t\t\tReleaseCom(DirectInteropProbeSurface);\n\t\t\tReleaseCom(DirectInteropProbeTexture);\n\t\t\tDirectInteropProbeHandle = nullptr;\n\t\t\tDirectInteropProbeToken = 0;\n\t\t\tDirectInteropVerified = false;\n\t\t\tif (SharedState && SharedState->magic == OutRunVR::SharedMagic)\n\t\t\t{\n\t\t\t\tInterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->clientInteropProbeHandle), 0);\n\t\t\t\tInterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->clientInteropProbeToken), 0);\n\t\t\t}\n\t\t\tDirectTransportFormat = D3DFMT_UNKNOWN;'''
    s = sub_once(s,
        r'\t\t\tStereoResourcesReady = false;\n\t\t\tDirectTransportResourcesReady = false;\n.*?\t\t\tDirectTransportFormat = D3DFMT_UNKNOWN;',
        release_new,
        "release direct resources")

    new_direct_functions = r'''\t\tD3DFORMAT ChooseDirectTransportFormat(D3DFORMAT source)\n\t\t{\n\t\t\tswitch (source)\n\t\t\t{\n\t\t\tcase D3DFMT_A2B10G10R10: return D3DFMT_A2B10G10R10;\n\t\t\tcase D3DFMT_A16B16G16R16F: return D3DFMT_A16B16G16R16F;\n\t\t\tdefault: return D3DFMT_A8B8G8R8;\n\t\t\t}\n\t\t}\n\n\t\tbool CanConvertForDirectTransport(IDirect3DDevice9* device, D3DFORMAT source, D3DFORMAT target)\n\t\t{\n\t\t\tif (!device) return false;\n\t\t\tD3DDEVICE_CREATION_PARAMETERS cp{};\n\t\t\tif (FAILED(device->GetCreationParameters(&cp))) return false;\n\t\t\tIDirect3D9* d3d = nullptr;\n\t\t\tif (FAILED(device->GetDirect3D(&d3d)) || !d3d) return false;\n\t\t\tconst HRESULT hr = d3d->CheckDeviceFormatConversion(cp.AdapterOrdinal, cp.DeviceType, source, target);\n\t\t\td3d->Release();\n\t\t\treturn SUCCEEDED(hr);\n\t\t}\n\n\t\tbool FrameIdAtOrAfter(std::uint32_t candidate, std::uint32_t reference)\n\t\t{\n\t\t\treturn reference == 0 || static_cast<std::int32_t>(candidate - reference) >= 0;\n\t\t}\n\n\t\tbool WaitForEventQuery(IDirect3DQuery9* query, ULONGLONG timeoutMs)\n\t\t{\n\t\t\tif (!query) return false;\n\t\t\tconst ULONGLONG deadline = GetTickCount64() + timeoutMs;\n\t\t\tfor (;;)\n\t\t\t{\n\t\t\t\tconst HRESULT ready = query->GetData(nullptr, 0, D3DGETDATA_FLUSH);\n\t\t\t\tif (ready == S_OK) return true;\n\t\t\t\tif (ready != S_FALSE) return false;\n\t\t\t\tif (GetTickCount64() >= deadline) return false;\n\t\t\t\tSleep(0);\n\t\t\t}\n\t\t}\n\n\t\tbool QueryGameAdapterLuid(IDirect3DDevice9* device, LUID& luid)\n\t\t{\n\t\t\tIDirect3DDevice9Ex* deviceEx = nullptr;\n\t\t\tif (!device || FAILED(device->QueryInterface(__uuidof(IDirect3DDevice9Ex),\n\t\t\t\treinterpret_cast<void**>(&deviceEx))) || !deviceEx)\n\t\t\t{\n\t\t\t\tif (!FirstD3D9ExUnavailableLogged)\n\t\t\t\t{\n\t\t\t\t\tFirstD3D9ExUnavailableLogged = true;\n\t\t\t\t\tspdlog::warn("VR direct transport: game device is not D3D9Ex; zero-copy disabled, SBS/Desktop Duplication remains active");\n\t\t\t\t}\n\t\t\t\treturn false;\n\t\t\t}\n\t\t\tD3DDEVICE_CREATION_PARAMETERS cp{};\n\t\t\tIDirect3D9* base = nullptr;\n\t\t\tIDirect3D9Ex* d3dEx = nullptr;\n\t\t\tconst bool ok = SUCCEEDED(deviceEx->GetCreationParameters(&cp)) &&\n\t\t\t\tSUCCEEDED(deviceEx->GetDirect3D(&base)) && base &&\n\t\t\t\tSUCCEEDED(base->QueryInterface(__uuidof(IDirect3D9Ex), reinterpret_cast<void**>(&d3dEx))) && d3dEx &&\n\t\t\t\tSUCCEEDED(d3dEx->GetAdapterLUID(cp.AdapterOrdinal, &luid));\n\t\t\tReleaseCom(d3dEx);\n\t\t\tReleaseCom(base);\n\t\t\tReleaseCom(deviceEx);\n\t\t\treturn ok;\n\t\t}\n\n\t\tbool EnsureDirectInteropProbe(IDirect3DDevice9* device)\n\t\t{\n\t\t\tif (!HostDirectTransportSupported() || !EnsureSharedState() ||\n\t\t\t\t(SharedState->flags & OutRunVR::HostAdapterLuidValid) == 0) return false;\n\n\t\t\tLUID gameLuid{};\n\t\t\tif (!QueryGameAdapterLuid(device, gameLuid)) return false;\n\t\t\tInterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->clientAdapterLuidLow),\n\t\t\t\tstatic_cast<LONG>(gameLuid.LowPart));\n\t\t\tInterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->clientAdapterLuidHigh),\n\t\t\t\tstatic_cast<LONG>(gameLuid.HighPart));\n\t\t\tconst bool adapterMatches = SharedState->hostAdapterLuidLow == gameLuid.LowPart &&\n\t\t\t\tSharedState->hostAdapterLuidHigh == static_cast<std::uint32_t>(gameLuid.HighPart);\n\t\t\tif (!adapterMatches)\n\t\t\t{\n\t\t\t\tif (!FirstAdapterMismatchLogged)\n\t\t\t\t{\n\t\t\t\t\tFirstAdapterMismatchLogged = true;\n\t\t\t\t\tspdlog::warn("VR direct transport: OpenXR D3D11 adapter LUID does not match the game D3D9Ex adapter; forcing SBS fallback");\n\t\t\t\t}\n\t\t\t\treturn false;\n\t\t\t}\n\n\t\t\tif (DirectInteropProbeToken &&\n\t\t\t\tSharedState->hostInteropProbeAckToken == DirectInteropProbeToken)\n\t\t\t{\n\t\t\t\tDirectInteropVerified = true;\n\t\t\t\tif (!FirstInteropVerifiedLogged)\n\t\t\t\t{\n\t\t\t\t\tFirstInteropVerifiedLogged = true;\n\t\t\t\t\tspdlog::info("VR direct transport: D3D9Ex -> D3D11 shared-resource probe verified on the OpenXR adapter");\n\t\t\t\t}\n\t\t\t\treturn true;\n\t\t\t}\n\n\t\t\tif (!DirectInteropProbeTexture)\n\t\t\t{\n\t\t\t\tHANDLE handle = nullptr;\n\t\t\t\tif (FAILED(device->CreateTexture(1, 1, 1, D3DUSAGE_RENDERTARGET, D3DFMT_A8B8G8R8,\n\t\t\t\t\tD3DPOOL_DEFAULT, &DirectInteropProbeTexture, &handle)) || !DirectInteropProbeTexture || !handle ||\n\t\t\t\t\tFAILED(DirectInteropProbeTexture->GetSurfaceLevel(0, &DirectInteropProbeSurface)) ||\n\t\t\t\t\tFAILED(device->ColorFill(DirectInteropProbeSurface, nullptr, D3DCOLOR_ARGB(0xFF, 0x7B, 0x7B, 0x7B))) ||\n\t\t\t\t\tFAILED(device->CreateQuery(D3DQUERYTYPE_EVENT, &DirectInteropProbeFence)) || !DirectInteropProbeFence ||\n\t\t\t\t\tFAILED(DirectInteropProbeFence->Issue(D3DISSUE_END)) || !WaitForEventQuery(DirectInteropProbeFence, 50))\n\t\t\t\t{\n\t\t\t\t\t++DirectInteropProbeFailures;\n\t\t\t\t\tReleaseCom(DirectInteropProbeFence);\n\t\t\t\t\tReleaseCom(DirectInteropProbeSurface);\n\t\t\t\t\tReleaseCom(DirectInteropProbeTexture);\n\t\t\t\t\tDirectInteropProbeHandle = nullptr;\n\t\t\t\t\treturn false;\n\t\t\t\t}\n\t\t\t\tDirectInteropProbeHandle = handle;\n\t\t\t\tDirectInteropProbeToken = static_cast<std::uint32_t>(GetTickCount()) ^ GetCurrentProcessId() ^ 0x4F525652u;\n\t\t\t\tif (!DirectInteropProbeToken) DirectInteropProbeToken = 1;\n\t\t\t\tInterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->hostInteropProbeAckToken), 0);\n\t\t\t\tInterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->clientInteropProbeHandle),\n\t\t\t\t\tstatic_cast<LONG>(reinterpret_cast<std::uintptr_t>(DirectInteropProbeHandle)));\n\t\t\t\tInterlockedExchange(reinterpret_cast<volatile LONG*>(&SharedState->clientInteropProbeToken),\n\t\t\t\t\tstatic_cast<LONG>(DirectInteropProbeToken));\n\t\t\t}\n\t\t\treturn false;\n\t\t}\n\n\t\tvoid ReleaseDirectTransportSlots()\n\t\t{\n\t\t\tDirectTransportResourcesReady = false;\n\t\t\tfor (auto& slot : DirectTransportSlots)\n\t\t\t{\n\t\t\t\tReleaseCom(slot.fence);\n\t\t\t\tReleaseCom(slot.leftSurface);\n\t\t\t\tReleaseCom(slot.leftTexture);\n\t\t\t\tReleaseCom(slot.rightSurface);\n\t\t\t\tReleaseCom(slot.rightTexture);\n\t\t\t\tslot = {};\n\t\t\t}\n\t\t}\n\n\t\tbool EnsureDirectTransportResources(IDirect3DDevice9* device)\n\t\t{\n\t\t\tif (!device || !BackBufferDesc.Width || !BackBufferDesc.Height || !EnsureDirectInteropProbe(device))\n\t\t\t\treturn false;\n\t\t\tif (DirectTransportResourcesReady) return true;\n\n\t\t\tReleaseDirectTransportSlots();\n\t\t\tDirectTransportFormat = ChooseDirectTransportFormat(BackBufferDesc.Format);\n\t\t\tif (!CanConvertForDirectTransport(device, BackBufferDesc.Format, DirectTransportFormat)) return false;\n\n\t\t\tfor (auto& slot : DirectTransportSlots)\n\t\t\t{\n\t\t\t\tHANDLE leftHandle = nullptr, rightHandle = nullptr;\n\t\t\t\tconst HRESULT leftHr = device->CreateTexture(BackBufferDesc.Width, BackBufferDesc.Height, 1,\n\t\t\t\t\tD3DUSAGE_RENDERTARGET, DirectTransportFormat, D3DPOOL_DEFAULT, &slot.leftTexture, &leftHandle);\n\t\t\t\tconst HRESULT rightHr = SUCCEEDED(leftHr) ? device->CreateTexture(BackBufferDesc.Width, BackBufferDesc.Height, 1,\n\t\t\t\t\tD3DUSAGE_RENDERTARGET, DirectTransportFormat, D3DPOOL_DEFAULT, &slot.rightTexture, &rightHandle) : E_FAIL;\n\t\t\t\tif (FAILED(leftHr) || FAILED(rightHr) || !leftHandle || !rightHandle ||\n\t\t\t\t\tFAILED(slot.leftTexture->GetSurfaceLevel(0, &slot.leftSurface)) ||\n\t\t\t\t\tFAILED(slot.rightTexture->GetSurfaceLevel(0, &slot.rightSurface)) ||\n\t\t\t\t\tFAILED(device->CreateQuery(D3DQUERYTYPE_EVENT, &slot.fence)) || !slot.fence)\n\t\t\t\t{\n\t\t\t\t\tReleaseDirectTransportSlots();\n\t\t\t\t\treturn false;\n\t\t\t\t}\n\t\t\t\tslot.leftHandle = leftHandle;\n\t\t\t\tslot.rightHandle = rightHandle;\n\t\t\t}\n\t\t\tif (++DirectTransportGeneration == 0) ++DirectTransportGeneration;\n\t\t\tDirectTransportResourcesReady = true;\n\t\t\tspdlog::info("VR stereo: verified 4-slot D3D9Ex shared eye ring ready {}x{} format={} generation={}",\n\t\t\t\tBackBufferDesc.Width, BackBufferDesc.Height, static_cast<int>(DirectTransportFormat), DirectTransportGeneration);\n\t\t\treturn true;\n\t\t}\n\n\t\tbool ResolveDirectTransport(IDirect3DDevice9* device, std::uint32_t frameId)\n\t\t{\n\t\t\tif (!frameId || !EnsureDirectTransportResources(device) || !BackBuffer || !RightEyeSurface) return false;\n\t\t\tconst std::uint32_t slotIndex = (frameId - 1u) % OutRunVR::RenderFrameRingSize;\n\t\t\tauto& slot = DirectTransportSlots[slotIndex];\n\t\t\tconst std::uint32_t consumed = SharedState ? SharedState->hostDirectConsumedFrameId : 0;\n\t\t\tif (slot.frameId && !FrameIdAtOrAfter(consumed, slot.frameId))\n\t\t\t{\n\t\t\t\t++DirectTransportRingBackpressure;\n\t\t\t\treturn false;\n\t\t\t}\n\t\t\t{\n\t\t\t\tInternalPassScope guard;\n\t\t\t\tif (FAILED(device->StretchRect(BackBuffer, nullptr, slot.leftSurface, nullptr, D3DTEXF_NONE)) ||\n\t\t\t\t\tFAILED(device->StretchRect(RightEyeSurface, nullptr, slot.rightSurface, nullptr, D3DTEXF_NONE)) ||\n\t\t\t\t\tFAILED(slot.fence->Issue(D3DISSUE_END))) return false;\n\t\t\t}\n\t\t\tif (!WaitForEventQuery(slot.fence, 12))\n\t\t\t{\n\t\t\t\t++DirectTransportFenceTimeouts;\n\t\t\t\treturn false;\n\t\t\t}\n\t\t\tslot.frameId = frameId;\n\t\t\tActiveDirectTransportSlot = slotIndex;\n\t\t\treturn true;\n\t\t}\n\n'''
    s = sub_once(s,
        r'\t\tD3DFORMAT ChooseDirectTransportFormat\(D3DFORMAT source\).*?\n(?=\t\tbool EnsureStereoResources\(IDirect3DDevice9\* device\))',
        new_direct_functions,
        "direct transport implementation")

    new_publish = r'''\t\tvoid PublishRenderFrame(std::uint32_t state, std::uint32_t frameId, std::uint32_t sourcePoseSequence,\n\t\t\tstd::int64_t presentQpc, OutRunVR::StereoFailureReason failureReason,\n\t\t\tconst OutRunVRRenderer::LatchedStereoFrame* stereo, bool presentInFlight = false, bool directTransport = false)\n\t\t{\n\t\t\tif (!EnsureRenderFrameState()) return;\n\t\t\tconst std::uint32_t slotIndex = frameId ? (frameId - 1u) % OutRunVR::RenderFrameRingSize\n\t\t\t\t: (RenderFrameRing->latestSlot + 1u) % OutRunVR::RenderFrameRingSize;\n\t\t\tauto& frame = RenderFrameRing->slots[slotIndex];\n\t\t\tLONG seq = InterlockedIncrement(reinterpret_cast<volatile LONG*>(&frame.sequence));\n\t\t\tif ((seq & 1) == 0) InterlockedIncrement(reinterpret_cast<volatile LONG*>(&frame.sequence));\n\t\t\tMemoryBarrier();\n\t\t\tframe.magic = OutRunVR::RenderFrameMagic;\n\t\t\tframe.protocolVersion = OutRunVR::RenderFrameProtocolVersion;\n\t\t\tframe.structSize = sizeof(frame);\n\t\t\tframe.clientPid = GetCurrentProcessId();\n\t\t\tframe.state = state;\n\t\t\tframe.frameId = frameId;\n\t\t\tframe.sourcePoseSequence = sourcePoseSequence;\n\t\t\tframe.presentationMode = GameplayActive() ? OutRunVR::PresentationGameplay : OutRunVR::PresentationTheater;\n\t\t\tframe.flags = presentInFlight ? OutRunVR::RenderFramePresentInFlight : 0;\n\t\t\tframe.failureReason = static_cast<std::uint32_t>(failureReason);\n\t\t\tframe.backbufferWidth = BackBufferDesc.Width;\n\t\t\tframe.backbufferHeight = BackBufferDesc.Height;\n\t\t\tframe.presentQpc = presentQpc;\n\t\t\tstd::memset(frame.eye, 0, sizeof(frame.eye));\n\t\t\tstd::memset(frame.reserved, 0, sizeof(frame.reserved));\n\n\t\t\tif (directTransport && DirectTransportResourcesReady && ActiveDirectTransportSlot < DirectTransportSlots.size())\n\t\t\t{\n\t\t\t\tconst auto& transport = DirectTransportSlots[ActiveDirectTransportSlot];\n\t\t\t\tif (transport.leftHandle && transport.rightHandle && transport.frameId == frameId)\n\t\t\t\t{\n\t\t\t\t\tframe.flags |= OutRunVR::RenderFrameDirectGpuTransport;\n\t\t\t\t\tframe.reserved[OutRunVR::RenderFrameDirectLeftHandleIndex] = static_cast<std::uint32_t>(reinterpret_cast<std::uintptr_t>(transport.leftHandle));\n\t\t\t\t\tframe.reserved[OutRunVR::RenderFrameDirectRightHandleIndex] = static_cast<std::uint32_t>(reinterpret_cast<std::uintptr_t>(transport.rightHandle));\n\t\t\t\t\tframe.reserved[OutRunVR::RenderFrameDirectWidthIndex] = BackBufferDesc.Width;\n\t\t\t\t\tframe.reserved[OutRunVR::RenderFrameDirectHeightIndex] = BackBufferDesc.Height;\n\t\t\t\t\tframe.reserved[OutRunVR::RenderFrameDirectFormatIndex] = static_cast<std::uint32_t>(DirectTransportFormat);\n\t\t\t\t\tframe.reserved[OutRunVR::RenderFrameDirectGenerationIndex] = DirectTransportGeneration;\n\t\t\t\t\tframe.reserved[OutRunVR::RenderFrameDirectSlotIndex] = ActiveDirectTransportSlot;\n\t\t\t\t}\n\t\t\t}\n\t\t\tif (!presentInFlight && state == OutRunVR::StereoSbsActive && stereo && stereo->valid && frameId)\n\t\t\t{\n\t\t\t\tconst std::uint32_t transportFlag = frame.flags & OutRunVR::RenderFrameDirectGpuTransport;\n\t\t\t\tframe.flags = transportFlag | OutRunVR::RenderFrameStereoComplete | OutRunVR::RenderFrameWorldStereo |\n\t\t\t\t\tOutRunVR::RenderFrameDrawDuplicated | OutRunVR::RenderFrameEffectivePoseValid;\n\t\t\t\tfor (int eye = 0; eye < 2; ++eye)\n\t\t\t\t{\n\t\t\t\t\tstd::memcpy(frame.eye[eye].orientation, stereo->effectiveEyeOrientation[eye], sizeof(frame.eye[eye].orientation));\n\t\t\t\t\tstd::memcpy(frame.eye[eye].position, stereo->effectiveEyePosition[eye], sizeof(frame.eye[eye].position));\n\t\t\t\t\tframe.eye[eye].fov = stereo->eyeFov[eye];\n\t\t\t\t}\n\t\t\t}\n\t\t\tMemoryBarrier();\n\t\t\tseq = InterlockedIncrement(reinterpret_cast<volatile LONG*>(&frame.sequence));\n\t\t\tif (seq & 1) InterlockedIncrement(reinterpret_cast<volatile LONG*>(&frame.sequence));\n\n\t\t\tLONG ringSeq = InterlockedIncrement(reinterpret_cast<volatile LONG*>(&RenderFrameRing->publishSequence));\n\t\t\tif ((ringSeq & 1) == 0) InterlockedIncrement(reinterpret_cast<volatile LONG*>(&RenderFrameRing->publishSequence));\n\t\t\tMemoryBarrier();\n\t\t\tRenderFrameRing->clientPid = GetCurrentProcessId();\n\t\t\tRenderFrameRing->latestSlot = slotIndex;\n\t\t\tMemoryBarrier();\n\t\t\tringSeq = InterlockedIncrement(reinterpret_cast<volatile LONG*>(&RenderFrameRing->publishSequence));\n\t\t\tif (ringSeq & 1) InterlockedIncrement(reinterpret_cast<volatile LONG*>(&RenderFrameRing->publishSequence));\n\t\t}\n'''
    s = sub_once(s,
        r'\t\tvoid PublishRenderFrame\(std::uint32_t state.*?\n\t\t\}\n(?=\n\t\tstruct ScreenVertex)',
        new_publish,
        "ring frame publisher")

    new_present = r'''\t\tHRESULT __stdcall PresentDest(IDirect3DDevice9* device, const RECT* sourceRect, const RECT* destRect,\n\t\t\tHWND destWindowOverride, const RGNDATA* dirtyRegion)\n\t\t{\n\t\t\tif (!IsGameDevice(device))\n\t\t\t\treturn PresentHook.stdcall<HRESULT>(device, sourceRect, destRect, destWindowOverride, dirtyRegion);\n\t\t\tconst std::uint64_t beginNow = OutRunVRRenderer::GetBeginSceneCallCount();\n\t\t\tconst std::uint64_t beginDelta = beginNow >= LastBeginSceneCountAtPresent ? beginNow - LastBeginSceneCountAtPresent : 0;\n\t\t\tLastBeginSceneCountAtPresent = beginNow;\n\t\t\tif (GameplayActive())\n\t\t\t{\n\t\t\t\tif (beginDelta > 1) ++MultiBeginScenePresents;\n\t\t\t\tMaxBeginScenesPerPresent = std::max(MaxBeginScenesPerPresent, beginDelta);\n\t\t\t}\n\n\t\t\tconst bool stereoRequested = StereoWanted();\n\t\t\tconst std::uint32_t pendingFrameId = stereoRequested ? NextStereoFrameId() : 0;\n\t\t\tbool composedStereo = false;\n\t\t\tbool directTransport = false;\n\t\t\tstd::uint32_t pendingPoseSequence = 0;\n\t\t\tif (stereoRequested && FrameHadWorldStereo && FrameHadDuplicatedDraw && !FrameRightDrawFailed &&\n\t\t\t\t!FrameStereoIncomplete && FrameStereoPoseSequence && FrameStereoMetadata.valid && EnsureStereoResources(device))\n\t\t\t{\n\t\t\t\tdirectTransport = ResolveDirectTransport(device, pendingFrameId);\n\t\t\t\tif (directTransport)\n\t\t\t\t{\n\t\t\t\t\t++DirectTransportFrames;\n\t\t\t\t\tcomposedStereo = true;\n\t\t\t\t\tpendingPoseSequence = FrameStereoPoseSequence;\n\t\t\t\t\tif (!FirstDirectTransportLogged)\n\t\t\t\t\t{\n\t\t\t\t\t\tFirstDirectTransportLogged = true;\n\t\t\t\t\t\tspdlog::info("VR stereo: verified 4-slot direct GPU eye transport armed; source eye={}x{}",\n\t\t\t\t\t\t\tBackBufferDesc.Width, BackBufferDesc.Height);\n\t\t\t\t\t}\n\t\t\t\t\tif (!HostDirectTransportReady())\n\t\t\t\t\t{\n\t\t\t\t\t\tif (ComposeSbs(device)) ++StereoComposeSuccess; else ++StereoComposeFailure;\n\t\t\t\t\t}\n\t\t\t\t}\n\t\t\t\telse if (ComposeSbs(device))\n\t\t\t\t{\n\t\t\t\t\t++StereoComposeSuccess;\n\t\t\t\t\tcomposedStereo = true;\n\t\t\t\t\tpendingPoseSequence = FrameStereoPoseSequence;\n\t\t\t\t\t++DirectTransportFallbacks;\n\t\t\t\t\tif (!FirstDirectFallbackLogged)\n\t\t\t\t\t{\n\t\t\t\t\t\tFirstDirectFallbackLogged = true;\n\t\t\t\t\t\tspdlog::warn("VR stereo: direct transport not verified/available; keeping SBS/Desktop Duplication fallback");\n\t\t\t\t\t}\n\t\t\t\t}\n\t\t\t\telse\n\t\t\t\t{\n\t\t\t\t\t++StereoComposeFailure;\n\t\t\t\t\tPoisonFrame(OutRunVR::StereoFailureComposeFailed);\n\t\t\t\t}\n\t\t\t}\n\n\t\t\tMaybeLogSummary();\n\t\t\tLARGE_INTEGER presentStart{};\n\t\t\tQueryPerformanceCounter(&presentStart);\n\t\t\tif (stereoRequested)\n\t\t\t\tPublishRenderFrame(OutRunVR::StereoSbsFallbackMono, pendingFrameId, pendingPoseSequence,\n\t\t\t\t\tpresentStart.QuadPart, OutRunVR::StereoFailureNone, nullptr, true, directTransport);\n\t\t\tconst HRESULT hr = PresentHook.stdcall<HRESULT>(device, sourceRect, destRect, destWindowOverride, dirtyRegion);\n\t\t\tif (composedStereo && SUCCEEDED(hr) && !FrameStereoIncomplete)\n\t\t\t{\n\t\t\t\tPublishStereoState(OutRunVR::StereoSbsActive, true, pendingPoseSequence, pendingFrameId);\n\t\t\t\tPublishRenderFrame(OutRunVR::StereoSbsActive, pendingFrameId, pendingPoseSequence, presentStart.QuadPart,\n\t\t\t\t\tOutRunVR::StereoFailureNone, &FrameStereoMetadata, false, directTransport);\n\t\t\t\tif (!FirstStereoActiveLogged)\n\t\t\t\t{\n\t\t\t\t\tFirstStereoActiveLogged = true;\n\t\t\t\t\tspdlog::info("VR stereo: TRUE STEREO active; transport={} sourceEye={}x{} PC={}",\n\t\t\t\t\t\tdirectTransport ? "verified D3D9Ex->D3D11 ring" : "SBS Desktop Duplication",\n\t\t\t\t\t\tBackBufferDesc.Width, BackBufferDesc.Height,\n\t\t\t\t\t\t(directTransport && HostDirectTransportReady()) ? "left-eye mirror" : "SBS fallback");\n\t\t\t\t}\n\t\t\t}\n\t\t\telse\n\t\t\t{\n\t\t\t\tif (FAILED(hr) && FrameFailureReason == OutRunVR::StereoFailureNone)\n\t\t\t\t\tPoisonFrame(OutRunVR::StereoFailurePresentFailed);\n\t\t\t\tconst std::uint32_t fallback = stereoRequested ? OutRunVR::StereoSbsFallbackMono : OutRunVR::StereoDisabled;\n\t\t\t\tPublishStereoState(fallback, false, 0, 0);\n\t\t\t\tPublishRenderFrame(fallback, 0, 0, presentStart.QuadPart, FrameFailureReason, nullptr);\n\t\t\t}\n\t\t\tOutRunVRRenderer::NotifyGamePresent();\n\t\t\tFrameHadDuplicatedDraw = false; FrameHadWorldStereo = false; FrameRightDrawFailed = false;\n\t\t\tFrameStereoIncomplete = false; FramePoseMismatchLogged = false; FrameFailureReason = OutRunVR::StereoFailureNone;\n\t\t\tFrameStereoPoseSequence = 0; FrameStereoMetadata = {};\n\t\t\treturn hr;\n\t\t}\n'''
    s = sub_once(s,
        r'\t\tHRESULT __stdcall PresentDest\(IDirect3DDevice9\* device.*?\n\t\t\}\n(?=\n\t\tHRESULT __stdcall ResetDest)',
        new_present,
        "present transport flow")
    write(rel, s)


# -----------------------------------------------------------------------------
# x64 consumer: publish OpenXR adapter LUID, verify 1x1 interop probe, read ring,
# cache each direct slot, ACK consumed frames.
# -----------------------------------------------------------------------------
rel = "vrhost/main_stereo.cpp"
s = read(rel)
if "ServiceInteropProbe" not in s:
    s = replace_once(s,
        '        SharedWriter()\n        {',
        '        explicit SharedWriter(const LUID& adapterLuid) : adapterLuid_(adapterLuid)\n        {',
        "writer ctor")
    s = replace_once(s,
        '            AcquireOwnership();\n        }\n',
        '            AcquireOwnership();\n'
        '            Begin();\n'
        '            state_->hostAdapterLuidLow = adapterLuid_.LowPart;\n'
        '            state_->hostAdapterLuidHigh = static_cast<std::uint32_t>(adapterLuid_.HighPart);\n'
        '            End();\n'
        '        }\n',
        "publish host luid")
    s = replace_once(s,
        '            if (directTransportEnabled) flags |= OutRunVR::HostDirectGpuTransport;\n',
        '            if (directTransportEnabled) flags |= OutRunVR::HostDirectGpuTransport;\n'
        '            flags |= OutRunVR::HostAdapterLuidValid;\n',
        "luid valid flag")

    service_method = r'''\n        bool ServiceInteropProbe(ID3D11Device* device, ID3D11DeviceContext* context)\n        {\n            if (!HeaderValid() || !device || !context) return false;\n            const std::uint32_t handleValue = state_->clientInteropProbeHandle;\n            const std::uint32_t token = state_->clientInteropProbeToken;\n            if (!handleValue || !token) return false;\n            if (interopVerifiedToken_ == token && state_->hostInteropProbeAckToken == token) return true;\n            if (state_->clientAdapterLuidLow != adapterLuid_.LowPart ||\n                state_->clientAdapterLuidHigh != static_cast<std::uint32_t>(adapterLuid_.HighPart)) return false;\n\n            ID3D11Resource* resource = nullptr;\n            ID3D11Texture2D* texture = nullptr;\n            ID3D11Texture2D* staging = nullptr;\n            const HANDLE handle = reinterpret_cast<HANDLE>(static_cast<std::uintptr_t>(handleValue));\n            bool verified = false;\n            if (SUCCEEDED(device->OpenSharedResource(handle, __uuidof(ID3D11Resource), reinterpret_cast<void**>(&resource))) && resource &&\n                SUCCEEDED(resource->QueryInterface(__uuidof(ID3D11Texture2D), reinterpret_cast<void**>(&texture))) && texture)\n            {\n                D3D11_TEXTURE2D_DESC desc{};\n                texture->GetDesc(&desc);\n                if (desc.Width == 1 && desc.Height == 1 && desc.SampleDesc.Count == 1 &&\n                    (desc.Format == DXGI_FORMAT_R8G8B8A8_UNORM || desc.Format == DXGI_FORMAT_B8G8R8A8_UNORM))\n                {\n                    D3D11_TEXTURE2D_DESC sd = desc;\n                    sd.BindFlags = 0; sd.MiscFlags = 0; sd.Usage = D3D11_USAGE_STAGING;\n                    sd.CPUAccessFlags = D3D11_CPU_ACCESS_READ;\n                    if (SUCCEEDED(device->CreateTexture2D(&sd, nullptr, &staging)) && staging)\n                    {\n                        context->CopyResource(staging, texture);\n                        D3D11_MAPPED_SUBRESOURCE mapped{};\n                        if (SUCCEEDED(context->Map(staging, 0, D3D11_MAP_READ, 0, &mapped)) && mapped.pData)\n                        {\n                            const auto* px = static_cast<const std::uint8_t*>(mapped.pData);\n                            verified = px[0] == 0x7B && px[1] == 0x7B && px[2] == 0x7B && px[3] == 0xFF;\n                            context->Unmap(staging, 0);\n                        }\n                    }\n                }\n            }\n            ReleaseCom(staging); ReleaseCom(texture); ReleaseCom(resource);\n            if (verified)\n            {\n                interopVerifiedToken_ = token;\n                InterlockedExchange(reinterpret_cast<volatile LONG*>(&state_->hostInteropProbeAckToken), static_cast<LONG>(token));\n                if (!interopVerifiedLogged_)\n                {\n                    interopVerifiedLogged_ = true;\n                    std::cout << "D3D9Ex/D3D11 interop verification pixel passed on the OpenXR adapter.\\n";\n                }\n            }\n            return verified;\n        }\n\n        void AckDirectFrame(std::uint32_t frameId)\n        {\n            if (HeaderValid() && frameId)\n                InterlockedExchange(reinterpret_cast<volatile LONG*>(&state_->hostDirectConsumedFrameId), static_cast<LONG>(frameId));\n        }\n'''
    s = replace_once(s,
        '        std::uint32_t Write(const XrSpaceLocation& head,',
        service_method + '\n        std::uint32_t Write(const XrSpaceLocation& head,',
        "interop service")
    s = replace_once(s,
        '        std::uint32_t referenceGeneration_ = 1;\n',
        '        std::uint32_t referenceGeneration_ = 1;\n'
        '        LUID adapterLuid_{};\n'
        '        std::uint32_t interopVerifiedToken_ = 0;\n'
        '        bool interopVerifiedLogged_ = false;\n',
        "writer fields")

    new_reader = r'''    class RenderFrameReader\n    {\n    public:\n        RenderFrameReader()\n        {\n            mapping_ = CreateFileMappingW(INVALID_HANDLE_VALUE, nullptr, PAGE_READWRITE, 0,\n                static_cast<DWORD>(sizeof(OutRunVR::SharedRenderFrameRing)), OutRunVR::RenderFrameMemoryName);\n            if (!mapping_) throw std::runtime_error("CreateFileMappingW Frame.v2 failed");\n            const bool existed = GetLastError() == ERROR_ALREADY_EXISTS;\n            state_ = static_cast<OutRunVR::SharedRenderFrameRing*>(MapViewOfFile(mapping_, FILE_MAP_ALL_ACCESS,\n                0, 0, sizeof(OutRunVR::SharedRenderFrameRing)));\n            if (!state_) throw std::runtime_error("MapViewOfFile Frame.v2 failed");\n            if (!existed)\n            {\n                std::memset(state_, 0, sizeof(*state_));\n                state_->protocolVersion = OutRunVR::RenderFrameProtocolVersion;\n                state_->structSize = sizeof(*state_);\n                state_->slotCount = OutRunVR::RenderFrameRingSize;\n                for (auto& slot : state_->slots)\n                {\n                    slot.protocolVersion = OutRunVR::RenderFrameProtocolVersion;\n                    slot.structSize = sizeof(slot);\n                    slot.magic = OutRunVR::RenderFrameMagic;\n                }\n                MemoryBarrier();\n                state_->magic = OutRunVR::RenderFrameMagic;\n            }\n        }\n        ~RenderFrameReader() { if (state_) UnmapViewOfFile(state_); if (mapping_) CloseHandle(mapping_); }\n\n        bool Read(OutRunVR::SharedRenderFrameState& out) const\n        {\n            if (!state_ || state_->magic != OutRunVR::RenderFrameMagic ||\n                state_->protocolVersion != OutRunVR::RenderFrameProtocolVersion ||\n                state_->structSize != sizeof(*state_) || state_->slotCount != OutRunVR::RenderFrameRingSize) return false;\n            for (int attempt = 0; attempt < 6; ++attempt)\n            {\n                const std::uint32_t ringBefore = state_->publishSequence;\n                if (ringBefore & 1u) continue;\n                const std::uint32_t index = state_->latestSlot;\n                if (index >= OutRunVR::RenderFrameRingSize) continue;\n                const auto& slot = state_->slots[index];\n                const std::uint32_t before = slot.sequence;\n                if (before & 1u) continue;\n                MemoryBarrier();\n                std::memcpy(&out, &slot, sizeof(out));\n                MemoryBarrier();\n                const std::uint32_t after = slot.sequence;\n                const std::uint32_t ringAfter = state_->publishSequence;\n                if (ringBefore == ringAfter && !(ringAfter & 1u) && before == after && !(after & 1u) &&\n                    out.magic == OutRunVR::RenderFrameMagic && out.protocolVersion == OutRunVR::RenderFrameProtocolVersion &&\n                    out.structSize == sizeof(out)) return true;\n            }\n            return false;\n        }\n    private:\n        HANDLE mapping_ = nullptr;\n        OutRunVR::SharedRenderFrameRing* state_ = nullptr;\n    };\n'''
    s = sub_once(s,
        r'    class RenderFrameReader\n    \{.*?\n    \};\n(?=\n    struct ViewHistoryEntry)',
        new_reader,
        "ring reader")

    # Cache all four shared resource pairs instead of re-opening handles every frame.
    new_commit = r'''        bool CommitDirectStereoSource(const OutRunVR::SharedRenderFrameState& frame)\n        {\n            if (!directTransportEnabled_ || (frame.flags & OutRunVR::RenderFrameDirectGpuTransport) == 0) return false;\n            const std::uint32_t slot = frame.reserved[OutRunVR::RenderFrameDirectSlotIndex];\n            const std::uint32_t leftHandleValue = frame.reserved[OutRunVR::RenderFrameDirectLeftHandleIndex];\n            const std::uint32_t rightHandleValue = frame.reserved[OutRunVR::RenderFrameDirectRightHandleIndex];\n            const std::uint32_t width = frame.reserved[OutRunVR::RenderFrameDirectWidthIndex];\n            const std::uint32_t height = frame.reserved[OutRunVR::RenderFrameDirectHeightIndex];\n            const std::uint32_t generation = frame.reserved[OutRunVR::RenderFrameDirectGenerationIndex];\n            if (slot >= OutRunVR::RenderFrameRingSize || !leftHandleValue || !rightHandleValue || !width || !height || !generation) return false;\n\n            const bool same = directLeft_[slot] && directRight_[slot] && directLeftSrv_[slot] && directRightSrv_[slot] &&\n                directLeftHandle_[slot] == leftHandleValue && directRightHandle_[slot] == rightHandleValue &&\n                directGeneration_[slot] == generation;\n            if (!same)\n            {\n                ReleaseCom(directLeftSrv_[slot]); ReleaseCom(directLeft_[slot]);\n                ReleaseCom(directRightSrv_[slot]); ReleaseCom(directRight_[slot]);\n                directFrameValid_ = false;\n                auto openOne = [&](std::uint32_t raw, ID3D11Texture2D** texture, ID3D11ShaderResourceView** srv) -> bool\n                {\n                    ID3D11Resource* resource = nullptr;\n                    const HANDLE handle = reinterpret_cast<HANDLE>(static_cast<std::uintptr_t>(raw));\n                    if (FAILED(device_->OpenSharedResource(handle, __uuidof(ID3D11Resource), reinterpret_cast<void**>(&resource))) || !resource) return false;\n                    const HRESULT q = resource->QueryInterface(__uuidof(ID3D11Texture2D), reinterpret_cast<void**>(texture));\n                    resource->Release();\n                    if (FAILED(q) || !*texture) return false;\n                    D3D11_TEXTURE2D_DESC d{}; (*texture)->GetDesc(&d);\n                    if (d.Width != width || d.Height != height || d.SampleDesc.Count != 1 ||\n                        (d.Format != DXGI_FORMAT_R8G8B8A8_UNORM && d.Format != DXGI_FORMAT_R10G10B10A2_UNORM &&\n                         d.Format != DXGI_FORMAT_R16G16B16A16_FLOAT) ||\n                        FAILED(device_->CreateShaderResourceView(*texture, nullptr, srv)) || !*srv)\n                    {\n                        ReleaseCom(*texture); ReleaseCom(*srv); return false;\n                    }\n                    return true;\n                };\n                if (!openOne(leftHandleValue, &directLeft_[slot], &directLeftSrv_[slot]) ||\n                    !openOne(rightHandleValue, &directRight_[slot], &directRightSrv_[slot]))\n                {\n                    ReleaseCom(directLeftSrv_[slot]); ReleaseCom(directLeft_[slot]);\n                    ReleaseCom(directRightSrv_[slot]); ReleaseCom(directRight_[slot]);\n                    directTransportReady_ = false;\n                    if (!directOpenFailureLogged_)\n                    {\n                        directOpenFailureLogged_ = true;\n                        std::cout << "Direct GPU eye ring open failed; host will request SBS fallback.\\n";\n                    }\n                    return false;\n                }\n                D3D11_TEXTURE2D_DESC ld{}; directLeft_[slot]->GetDesc(&ld);\n                D3D11_TEXTURE2D_DESC rd{}; directRight_[slot]->GetDesc(&rd);\n                if (ld.Format != rd.Format) return false;\n                directLeftHandle_[slot] = leftHandleValue; directRightHandle_[slot] = rightHandleValue;\n                directGeneration_[slot] = generation; directFormat_[slot] = ld.Format;\n                directTransportReady_ = true;\n                std::cout << "Direct GPU eye ring slot " << slot << " opened: source " << width << "x" << height\n                    << " -> OpenXR " << projection_.width << "x" << projection_.height << ".\\n";\n            }\n            directActiveSlot_ = slot;\n            directFrameValid_ = true;\n            return true;\n        }\n'''
    s = sub_once(s,
        r'        bool CommitDirectStereoSource\(const OutRunVR::SharedRenderFrameState& frame\).*?\n        \}\n(?=\n        bool DirectTransportReady)',
        new_commit,
        "host direct slot cache")

    s = replace_once(s,
        '            ReleaseCom(directLeftSrv_); ReleaseCom(directLeft_);\n'
        '            ReleaseCom(directRightSrv_); ReleaseCom(directRight_);\n'
        '            directFrameValid_ = false; directTransportReady_ = false;\n'
        '            directLeftHandle_ = directRightHandle_ = directGeneration_ = 0;\n',
        '            for (std::uint32_t slot = 0; slot < OutRunVR::RenderFrameRingSize; ++slot)\n'
        '            {\n'
        '                ReleaseCom(directLeftSrv_[slot]); ReleaseCom(directLeft_[slot]);\n'
        '                ReleaseCom(directRightSrv_[slot]); ReleaseCom(directRight_[slot]);\n'
        '                directLeftHandle_[slot] = directRightHandle_[slot] = directGeneration_[slot] = 0;\n'
        '                directFormat_[slot] = DXGI_FORMAT_UNKNOWN;\n'
        '            }\n'
        '            directFrameValid_ = false; directTransportReady_ = false;\n',
        "host reset direct ring")

    s = replace_once(s,
        '            if (directFrameValid_ && directLeftSrv_ && directRightSrv_)\n'
        '            {\n'
        '                eyes[0] = eyes[1] = { 0.f, 0.f, 1.f, 1.f };\n'
        '                eyeSrv[0] = directLeftSrv_; eyeSrv[1] = directRightSrv_;\n'
        '                eyeFormat[0] = eyeFormat[1] = directFormat_;\n',
        '            if (directFrameValid_ && directActiveSlot_ < OutRunVR::RenderFrameRingSize &&\n'
        '                directLeftSrv_[directActiveSlot_] && directRightSrv_[directActiveSlot_])\n'
        '            {\n'
        '                eyes[0] = eyes[1] = { 0.f, 0.f, 1.f, 1.f };\n'
        '                eyeSrv[0] = directLeftSrv_[directActiveSlot_]; eyeSrv[1] = directRightSrv_[directActiveSlot_];\n'
        '                eyeFormat[0] = eyeFormat[1] = directFormat_[directActiveSlot_];\n',
        "host render active direct slot")

    old_fields = '''        ID3D11Texture2D* directLeft_ = nullptr;\n        ID3D11Texture2D* directRight_ = nullptr;\n        ID3D11ShaderResourceView* directLeftSrv_ = nullptr;\n        ID3D11ShaderResourceView* directRightSrv_ = nullptr;\n        std::uint32_t directLeftHandle_ = 0, directRightHandle_ = 0, directGeneration_ = 0;\n        std::uint32_t directWidth_ = 0, directHeight_ = 0;\n        DXGI_FORMAT directFormat_ = DXGI_FORMAT_UNKNOWN;\n'''
    new_fields = '''        std::array<ID3D11Texture2D*, OutRunVR::RenderFrameRingSize> directLeft_{};\n        std::array<ID3D11Texture2D*, OutRunVR::RenderFrameRingSize> directRight_{};\n        std::array<ID3D11ShaderResourceView*, OutRunVR::RenderFrameRingSize> directLeftSrv_{};\n        std::array<ID3D11ShaderResourceView*, OutRunVR::RenderFrameRingSize> directRightSrv_{};\n        std::array<std::uint32_t, OutRunVR::RenderFrameRingSize> directLeftHandle_{};\n        std::array<std::uint32_t, OutRunVR::RenderFrameRingSize> directRightHandle_{};\n        std::array<std::uint32_t, OutRunVR::RenderFrameRingSize> directGeneration_{};\n        std::array<DXGI_FORMAT, OutRunVR::RenderFrameRingSize> directFormat_{};\n        std::uint32_t directActiveSlot_ = 0;\n'''
    s = replace_once(s, old_fields, new_fields, "host direct fields")

    s = replace_once(s,
        '        SharedWriter shared;RenderFrameReader renderFrames;StereoCompositor compositor(session,d3d.device,d3d.context,gameWindow,configs,directTransportEnabled,renderScale);compositor.Initialize();ViewHistory viewHistory;HostTimings timings;\n',
        '        SharedWriter shared(req.adapterLuid);RenderFrameReader renderFrames;StereoCompositor compositor(session,d3d.device,d3d.context,gameWindow,configs,directTransportEnabled,renderScale);compositor.Initialize();ViewHistory viewHistory;HostTimings timings;\n',
        "writer construct with luid")

    s = replace_once(s,
        '            const std::uint32_t hostSequence = shared.Write(head, views, vc, configs,\n'
        '                state, vs.viewStateFlags, fs.shouldRender == XR_TRUE, directTransportEnabled,\n'
        '                compositor.DirectTransportReady(), ip.runtimeName);\n',
        '            const std::uint32_t hostSequence = shared.Write(head, views, vc, configs,\n'
        '                state, vs.viewStateFlags, fs.shouldRender == XR_TRUE, directTransportEnabled,\n'
        '                compositor.DirectTransportReady(), ip.runtimeName);\n'
        '            if (directTransportEnabled) shared.ServiceInteropProbe(d3d.device, d3d.context);\n',
        "service interop probe")

    # A direct frame is safe to recycle only after the x64 consumer has opened/accepted it.
    s = replace_once(s,
        'if(sourceReady&&same){for(int eye=0;eye<2;++eye){matchedViews[eye]={XR_TYPE_VIEW};',
        'if(sourceReady&&same){if(directFrame)shared.AckDirectFrame(before.frameId);for(int eye=0;eye<2;++eye){matchedViews[eye]={XR_TYPE_VIEW};',
        "direct consume ack")
    write(rel, s)


# -----------------------------------------------------------------------------
# Renderer comment contract: ABI is now Frame.v2.
# -----------------------------------------------------------------------------
rel = "src/vr_renderer_probe.cpp"
s = read(rel)
s = s.replace("Frame.v1 positions are OpenXR LOCAL-space metres", "Frame.v2 positions are OpenXR LOCAL-space metres")
write(rel, s)

rel = "src/hooks_vr.cpp"
s = read(rel)
s = s.replace("Pose.v1 remains layout-compatible; exact rendered-frame timing/effective eye poses\n// are published separately through Frame.v1 after a successful real D3D9 Present.",
              "Pose.v2 carries the OpenXR adapter/interop contract; exact rendered-frame timing/effective eye poses\n// are published through the 4-slot Frame.v2 ring after a successful real D3D9 Present.")
write(rel, s)

# -----------------------------------------------------------------------------
# Update CI contract to v2 ABI and reference-hardening markers.
# -----------------------------------------------------------------------------
rel = ".github/workflows/vr-openxr.yml"
s = read(rel)
s = s.replace("'Frame.v1 positions are OpenXR LOCAL-space metres'", "'Frame.v2 positions are OpenXR LOCAL-space metres'")
s = s.replace("$effectiveStart = $renderer.IndexOf('Frame.v1 positions are OpenXR LOCAL-space metres')",
              "$effectiveStart = $renderer.IndexOf('Frame.v2 positions are OpenXR LOCAL-space metres')")
s = s.replace("throw 'Frame.v1 OpenXR pose must remain in metres'", "throw 'Frame.v2 OpenXR pose must remain in metres'")
s = s.replace("'static_assert(sizeof(SharedPoseState) == 248)'", "'static_assert(sizeof(SharedPoseState) == 280)'")
s = s.replace("'offsetof(SharedPoseState, runtimeName) == 120'", "'offsetof(SharedPoseState, runtimeName) == 152'")
s = s.replace("'offsetof(SharedPoseState, reserved) == 184'", "'offsetof(SharedPoseState, reserved) == 216'")
s = s.replace("'static_assert(sizeof(SharedRenderFrameState) == 256)'",
              "'static_assert(sizeof(SharedRenderFrameState) == 256)','static_assert(sizeof(SharedRenderFrameRing) == 1056)','RenderFrameRingSize = 4','HostAdapterLuidValid','clientInteropProbeHandle','hostDirectConsumedFrameId'")
s = s.replace("'PublishRenderFrame','SharedRenderFrameState','FrameStereoIncomplete',",
              "'PublishRenderFrame','SharedRenderFrameState','SharedRenderFrameRing','DirectInteropProbeToken','QueryGameAdapterLuid','RenderFrameDirectSlotIndex','FrameStereoIncomplete',")
s = s.replace("'recommendedImageRectWidth','RenderFrameReader','SharedRenderFrameState',",
              "'recommendedImageRectWidth','RenderFrameReader','SharedRenderFrameState','SharedRenderFrameRing','ServiceInteropProbe','AckDirectFrame','RenderFrameDirectSlotIndex',")
write(rel, s)

print("VR reference-derived hardening applied successfully")
