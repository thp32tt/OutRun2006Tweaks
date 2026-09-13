// OpenXR compatibility + diagnostic compositor for VDXR.
//
// This milestone is still a mono mirror, but unlike the earlier diagnostic
// build it is color-managed and resilient enough to use for real head-tracking
// validation:
//   * accepts both SDR BGRA8 and HDR/scRGB FP16 desktop-duplication surfaces;
//   * converts everything to linear SDR on the GPU;
//   * prefers an OpenXR sRGB swapchain so the runtime interprets colors correctly;
//   * reports host pose and game-camera telemetry;
//   * exits the OpenXR session when OutRun closes so Virtual Desktop comes back.

#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#ifndef XR_USE_PLATFORM_WIN32
#define XR_USE_PLATFORM_WIN32
#endif
#ifndef XR_USE_GRAPHICS_API_D3D11
#define XR_USE_GRAPHICS_API_D3D11
#endif

#include <Windows.h>
#include <TlHelp32.h>
#include <d3d11.h>
#include <d3dcompiler.h>
#include <dxgi1_5.h>
#include <openxr/openxr.h>
#include <openxr/openxr_platform.h>

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <cwchar>
#include <iostream>
#include <string>
#include <vector>

#include "vr_shared.hpp"

namespace
{
    constexpr wchar_t GameExeName[] = L"OR2006C2C.EXE";

    template <typename T>
    void ReleaseCom(T*& value)
    {
        if (value)
        {
            value->Release();
            value = nullptr;
        }
    }

    struct WindowSearch
    {
        DWORD pid = 0;
        HWND best = nullptr;
        long long bestArea = 0;
    };

    BOOL CALLBACK EnumGameWindows(HWND hwnd, LPARAM param)
    {
        auto* search = reinterpret_cast<WindowSearch*>(param);
        DWORD pid = 0;
        GetWindowThreadProcessId(hwnd, &pid);
        if (pid != search->pid || !IsWindowVisible(hwnd))
            return TRUE;

        RECT client{};
        if (!GetClientRect(hwnd, &client))
            return TRUE;
        const long long width = client.right - client.left;
        const long long height = client.bottom - client.top;
        const long long area = width * height;
        if (width >= 320 && height >= 200 && area > search->bestArea)
        {
            search->best = hwnd;
            search->bestArea = area;
        }
        return TRUE;
    }

    DWORD FindGameProcess()
    {
        HANDLE snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
        if (snapshot == INVALID_HANDLE_VALUE)
            return 0;

        PROCESSENTRY32W entry{};
        entry.dwSize = sizeof(entry);
        DWORD pid = 0;
        if (Process32FirstW(snapshot, &entry))
        {
            do
            {
                if (_wcsicmp(entry.szExeFile, GameExeName) == 0)
                {
                    pid = entry.th32ProcessID;
                    break;
                }
            } while (Process32NextW(snapshot, &entry));
        }
        CloseHandle(snapshot);
        return pid;
    }

    HWND FindGameWindow(DWORD pid)
    {
        WindowSearch search{};
        search.pid = pid;
        EnumWindows(EnumGameWindows, reinterpret_cast<LPARAM>(&search));
        return search.best;
    }

    HWND WaitForGameWindow()
    {
        std::cout
            << "Waiting for OR2006C2C.EXE before taking over the headset...\n"
            << "Launch OutRun from the Virtual Desktop screen.\n";

        DWORD lastPid = 0;
        for (;;)
        {
            const DWORD pid = FindGameProcess();
            if (pid && pid != lastPid)
            {
                std::cout << "OutRun process detected (pid=" << pid << "). Waiting for its window...\n";
                lastPid = pid;
            }
            if (pid)
            {
                if (HWND hwnd = FindGameWindow(pid))
                {
                    std::cout << "OutRun window detected. Starting OpenXR mirror session.\n";
                    return hwnd;
                }
            }
            Sleep(100);
        }
    }

    float QuerySdrWhiteScale(HMONITOR monitor)
    {
        char overrideValue[64]{};
        const DWORD overrideLength = GetEnvironmentVariableA(
            "OUTRUN_VR_SDR_WHITE_SCALE", overrideValue, static_cast<DWORD>(sizeof(overrideValue)));
        if (overrideLength > 0 && overrideLength < sizeof(overrideValue))
        {
            char* end = nullptr;
            const float parsed = std::strtof(overrideValue, &end);
            if (end != overrideValue && std::isfinite(parsed) && parsed >= 0.25f && parsed <= 8.0f)
            {
                std::cout << "VR color: using OUTRUN_VR_SDR_WHITE_SCALE=" << parsed << ".\n";
                return parsed;
            }
        }

        MONITORINFOEXW monitorInfo{};
        monitorInfo.cbSize = sizeof(monitorInfo);
        if (!monitor || !GetMonitorInfoW(monitor, &monitorInfo))
            return 1.0f;

        UINT32 pathCount = 0;
        UINT32 modeCount = 0;
        if (GetDisplayConfigBufferSizes(QDC_ONLY_ACTIVE_PATHS, &pathCount, &modeCount) != ERROR_SUCCESS)
            return 1.0f;

        std::vector<DISPLAYCONFIG_PATH_INFO> paths(pathCount);
        std::vector<DISPLAYCONFIG_MODE_INFO> modes(modeCount);
        if (QueryDisplayConfig(QDC_ONLY_ACTIVE_PATHS, &pathCount, paths.data(),
            &modeCount, modes.data(), nullptr) != ERROR_SUCCESS)
            return 1.0f;

        for (UINT32 i = 0; i < pathCount; ++i)
        {
            DISPLAYCONFIG_SOURCE_DEVICE_NAME sourceName{};
            sourceName.header.type = DISPLAYCONFIG_DEVICE_INFO_GET_SOURCE_NAME;
            sourceName.header.size = sizeof(sourceName);
            sourceName.header.adapterId = paths[i].sourceInfo.adapterId;
            sourceName.header.id = paths[i].sourceInfo.id;
            if (DisplayConfigGetDeviceInfo(&sourceName.header) != ERROR_SUCCESS)
                continue;
            if (_wcsicmp(sourceName.viewGdiDeviceName, monitorInfo.szDevice) != 0)
                continue;

            DISPLAYCONFIG_SDR_WHITE_LEVEL white{};
            white.header.type = DISPLAYCONFIG_DEVICE_INFO_GET_SDR_WHITE_LEVEL;
            white.header.size = sizeof(white);
            white.header.adapterId = paths[i].targetInfo.adapterId;
            white.header.id = paths[i].targetInfo.id;
            if (DisplayConfigGetDeviceInfo(&white.header) == ERROR_SUCCESS && white.SDRWhiteLevel > 0)
            {
                const float scale = std::clamp(static_cast<float>(white.SDRWhiteLevel) / 1000.0f, 0.25f, 8.0f);
                std::cout << "VR color: Windows SDR white=" << (scale * 80.0f)
                          << " nits (scRGB scale=" << scale << ").\n";
                return scale;
            }
        }

        std::cout << "VR color: SDR white query unavailable; using 80-nit scale 1.0.\n";
        return 1.0f;
    }

    ID3DBlob* CompileShader(const char* source, const char* entry, const char* target)
    {
        ID3DBlob* code = nullptr;
        ID3DBlob* errors = nullptr;
        const HRESULT hr = D3DCompile(source, std::strlen(source), "OutRunVRMirror",
            nullptr, nullptr, entry, target,
            D3DCOMPILE_ENABLE_STRICTNESS | D3DCOMPILE_OPTIMIZATION_LEVEL3,
            0, &code, &errors);
        if (FAILED(hr))
        {
            std::string message = "D3DCompile failed";
            if (errors && errors->GetBufferPointer())
                message += std::string(": ") + static_cast<const char*>(errors->GetBufferPointer());
            ReleaseCom(errors);
            ReleaseCom(code);
            throw std::runtime_error(message);
        }
        ReleaseCom(errors);
        return code;
    }

    const char* MirrorShader = R"HLSL(
Texture2D SourceTexture : register(t0);
SamplerState SourceSampler : register(s0);

cbuffer MirrorParams : register(b0)
{
    float SdrWhiteScale;
    float SourceIsScRgb;
    float2 Padding;
};

struct VSOut
{
    float4 position : SV_Position;
    float2 uv : TEXCOORD0;
};

VSOut VSMain(uint id : SV_VertexID)
{
    VSOut o;
    float2 uv = float2((id << 1) & 2, id & 2);
    o.position = float4(uv * float2(2.0, -2.0) + float2(-1.0, 1.0), 0.0, 1.0);
    o.uv = uv;
    return o;
}

float3 SrgbToLinear(float3 c)
{
    return float3(
        c.r <= 0.04045 ? c.r / 12.92 : pow((c.r + 0.055) / 1.055, 2.4),
        c.g <= 0.04045 ? c.g / 12.92 : pow((c.g + 0.055) / 1.055, 2.4),
        c.b <= 0.04045 ? c.b / 12.92 : pow((c.b + 0.055) / 1.055, 2.4));
}

float4 PSMain(VSOut input) : SV_Target
{
    float4 src = SourceTexture.Sample(SourceSampler, input.uv);
    float3 linear;
    if (SourceIsScRgb > 0.5)
    {
        // Windows scRGB is linear and 1.0 == 80 nits. SDR content on an HDR
        // desktop is multiplied by the user's SDR-white scale, so divide that
        // boost back out before submitting to the SDR OpenXR compositor.
        linear = max(src.rgb, 0.0) / max(SdrWhiteScale, 0.001);
    }
    else
    {
        // BGRA8 desktop duplication contains display-referred sRGB values.
        linear = SrgbToLinear(saturate(src.rgb));
    }

    // OutRun itself is SDR. Preserve normal SDR contrast and clip only real HDR
    // highlight energy instead of passing it through as blown-out white.
    linear = saturate(linear);
    return float4(linear, 1.0);
}
)HLSL";

    class MonoMirror
    {
    public:
        ~MonoMirror() { ResetAll(); }

        void OnSessionCreated(XrSession session, ID3D11Device* device, HWND hwnd)
        {
            ResetAll();
            session_ = session;
            hwnd_ = hwnd;
            GetWindowThreadProcessId(hwnd_, &gamePid_);
            if (gamePid_)
                gameProcess_ = OpenProcess(SYNCHRONIZE | PROCESS_QUERY_LIMITED_INFORMATION, FALSE, gamePid_);

            device_ = device;
            if (device_)
            {
                device_->AddRef();
                device_->GetImmediateContext(&context_);
            }
            TryOpenSharedTelemetry();
        }

        void OnViewSpaceCreated(XrSpace space) { viewSpace_ = space; }

        XrSession Session() const { return session_; }

        bool GameAlive() const
        {
            if (gameProcess_)
                return WaitForSingleObject(gameProcess_, 0) == WAIT_TIMEOUT;
            return IsWindow(hwnd_) != FALSE;
        }

        void PollClientTelemetry()
        {
            TryOpenSharedTelemetry();
            if (!sharedState_)
                return;

            const ULONGLONG now = GetTickCount64();
            if (now - lastClientTelemetryLogMs_ < 1000)
                return;
            lastClientTelemetryLogMs_ = now;

            const std::uint32_t clientPid = sharedState_->clientPid;
            const std::uint32_t heartbeat = sharedState_->reserved[OutRunVR::ClientHeartbeatIndex];
            const std::uint32_t flags = sharedState_->reserved[OutRunVR::ClientFlagsIndex];
            const std::uint32_t angleBits = sharedState_->reserved[OutRunVR::ClientLastAngleBitsIndex];
            float angle = 0.0f;
            std::memcpy(&angle, &angleBits, sizeof(angle));

            if (clientPid != lastClientPid_)
            {
                lastClientPid_ = clientPid;
                if (clientPid)
                    std::cout << "VR bridge: x86 game client connected (pid=" << clientPid << ").\n";
            }

            if (clientPid)
            {
                std::cout << "VR bridge: cameraHeartbeat=" << heartbeat
                          << " flags=0x" << std::hex << flags << std::dec
                          << " appliedAngle=" << angle << "deg"
                          << ((flags & OutRunVR::ClientPoseApplied) ? " [CAMERA APPLIED]" : " [NOT APPLIED]")
                          << "\n";
            }
        }

        bool Initialize()
        {
            if (initialized_)
                return true;
            if (session_ == XR_NULL_HANDLE || !device_ || !context_ || !IsWindow(hwnd_))
            {
                std::cerr << "VR mirror: session/device/game window is not ready.\n";
                return false;
            }

            targetMonitor_ = MonitorFromWindow(hwnd_, MONITOR_DEFAULTTONEAREST);
            sdrWhiteScale_ = QuerySdrWhiteScale(targetMonitor_);

            IDXGIDevice* dxgiDevice = nullptr;
            if (FAILED(device_->QueryInterface(__uuidof(IDXGIDevice), reinterpret_cast<void**>(&dxgiDevice))))
            {
                std::cerr << "VR mirror: ID3D11Device -> IDXGIDevice failed.\n";
                return false;
            }

            IDXGIAdapter* adapter = nullptr;
            const HRESULT adapterHr = dxgiDevice->GetAdapter(&adapter);
            dxgiDevice->Release();
            if (FAILED(adapterHr) || !adapter)
                return false;

            IDXGIOutput* selectedOutput = nullptr;
            DXGI_OUTPUT_DESC selectedDesc{};
            for (UINT i = 0;; ++i)
            {
                IDXGIOutput* output = nullptr;
                if (adapter->EnumOutputs(i, &output) == DXGI_ERROR_NOT_FOUND)
                    break;
                DXGI_OUTPUT_DESC desc{};
                output->GetDesc(&desc);
                if (desc.Monitor == targetMonitor_)
                {
                    selectedOutput = output;
                    selectedDesc = desc;
                    break;
                }
                output->Release();
            }
            adapter->Release();

            if (!selectedOutput)
            {
                std::cerr << "VR mirror: game monitor is not on the OpenXR GPU adapter.\n";
                return false;
            }

            selectedOutput->QueryInterface(__uuidof(IDXGIOutput1), reinterpret_cast<void**>(&output1_));
            selectedOutput->QueryInterface(__uuidof(IDXGIOutput5), reinterpret_cast<void**>(&output5_));
            selectedOutput->Release();
            if (!output1_)
            {
                std::cerr << "VR mirror: IDXGIOutput1 is unavailable.\n";
                return false;
            }

            outputDesktop_ = selectedDesc.DesktopCoordinates;
            width_ = static_cast<std::uint32_t>(outputDesktop_.right - outputDesktop_.left);
            height_ = static_cast<std::uint32_t>(outputDesktop_.bottom - outputDesktop_.top);
            if (!width_ || !height_)
                return false;

            if (!CreateShaders())
                return false;
            if (!RecreateDuplication(true))
                return false;
            if (!CreateOpenXrSwapchain())
                return false;

            initialized_ = true;
            std::cout << "OpenXR mono mirror ready: " << width_ << "x" << height_
                      << ", color-managed GPU conversion enabled.\n"
                      << "Mirror accepts BGRA8 SDR and FP16 scRGB HDR frames.\n"
                      << "This is still a temporary mono HMD view; true stereo is the next renderer milestone.\n";

            CaptureDesktopFrame(1000);
            return true;
        }

        bool CaptureAndRenderToSwapchain()
        {
            if (!initialized_ && !Initialize())
                return false;

            CaptureDesktopFrame(haveFrame_ ? 0 : 1000);
            PollClientTelemetry();
            if (!haveFrame_ || !latestSourceSrv_ || swapchain_ == XR_NULL_HANDLE)
                return false;

            XrSwapchainImageAcquireInfo acquireInfo{ XR_TYPE_SWAPCHAIN_IMAGE_ACQUIRE_INFO };
            std::uint32_t imageIndex = 0;
            XrResult xr = ::xrAcquireSwapchainImage(swapchain_, &acquireInfo, &imageIndex);
            if (XR_FAILED(xr) || imageIndex >= images_.size())
                return false;

            XrSwapchainImageWaitInfo waitInfo{ XR_TYPE_SWAPCHAIN_IMAGE_WAIT_INFO };
            waitInfo.timeout = XR_INFINITE_DURATION;
            xr = ::xrWaitSwapchainImage(swapchain_, &waitInfo);
            if (XR_FAILED(xr))
                return false;

            RenderConvertedFrame(imageIndex);

            XrSwapchainImageReleaseInfo releaseInfo{ XR_TYPE_SWAPCHAIN_IMAGE_RELEASE_INFO };
            xr = ::xrReleaseSwapchainImage(swapchain_, &releaseInfo);
            return XR_SUCCEEDED(xr);
        }

        XrCompositionLayerQuad MakeQuad() const
        {
            XrCompositionLayerQuad quad{ XR_TYPE_COMPOSITION_LAYER_QUAD };
            quad.space = viewSpace_;
            quad.eyeVisibility = XR_EYE_VISIBILITY_BOTH;
            quad.subImage.swapchain = swapchain_;
            quad.subImage.imageRect.offset = { 0, 0 };
            quad.subImage.imageRect.extent = {
                static_cast<std::int32_t>(width_), static_cast<std::int32_t>(height_)
            };
            quad.pose.orientation.w = 1.0f;
            quad.pose.position.z = -1.0f;
            quad.size.width = 2.0f;
            const float aspect = height_ ? static_cast<float>(width_) / static_cast<float>(height_) : 16.0f / 9.0f;
            quad.size.height = quad.size.width / aspect;
            return quad;
        }

        bool ReadyForLayer() const
        {
            return initialized_ && haveFrame_ && swapchain_ != XR_NULL_HANDLE && viewSpace_ != XR_NULL_HANDLE;
        }

        void BeforeSessionDestroy(XrSession session)
        {
            if (session == session_)
                ResetAll();
        }

    private:
        struct MirrorParams
        {
            float sdrWhiteScale;
            float sourceIsScRgb;
            float padding[2];
        };

        void TryOpenSharedTelemetry()
        {
            if (sharedState_)
                return;
            if (!sharedMapping_)
                sharedMapping_ = OpenFileMappingW(FILE_MAP_READ, FALSE, OutRunVR::SharedMemoryName);
            if (sharedMapping_)
            {
                sharedState_ = static_cast<const OutRunVR::SharedPoseState*>(MapViewOfFile(
                    sharedMapping_, FILE_MAP_READ, 0, 0, sizeof(OutRunVR::SharedPoseState)));
            }
        }

        bool CreateShaders()
        {
            try
            {
                ID3DBlob* vsCode = CompileShader(MirrorShader, "VSMain", "vs_5_0");
                ID3DBlob* psCode = CompileShader(MirrorShader, "PSMain", "ps_5_0");
                const HRESULT vsHr = device_->CreateVertexShader(
                    vsCode->GetBufferPointer(), vsCode->GetBufferSize(), nullptr, &vertexShader_);
                const HRESULT psHr = device_->CreatePixelShader(
                    psCode->GetBufferPointer(), psCode->GetBufferSize(), nullptr, &pixelShader_);
                ReleaseCom(vsCode);
                ReleaseCom(psCode);
                if (FAILED(vsHr) || FAILED(psHr))
                    return false;
            }
            catch (const std::exception& e)
            {
                std::cerr << "VR color shader: " << e.what() << "\n";
                return false;
            }

            D3D11_SAMPLER_DESC samplerDesc{};
            samplerDesc.Filter = D3D11_FILTER_MIN_MAG_MIP_LINEAR;
            samplerDesc.AddressU = D3D11_TEXTURE_ADDRESS_CLAMP;
            samplerDesc.AddressV = D3D11_TEXTURE_ADDRESS_CLAMP;
            samplerDesc.AddressW = D3D11_TEXTURE_ADDRESS_CLAMP;
            if (FAILED(device_->CreateSamplerState(&samplerDesc, &sampler_)))
                return false;

            D3D11_BUFFER_DESC cbDesc{};
            cbDesc.ByteWidth = sizeof(MirrorParams);
            cbDesc.Usage = D3D11_USAGE_DYNAMIC;
            cbDesc.BindFlags = D3D11_BIND_CONSTANT_BUFFER;
            cbDesc.CPUAccessFlags = D3D11_CPU_ACCESS_WRITE;
            return SUCCEEDED(device_->CreateBuffer(&cbDesc, nullptr, &constantBuffer_));
        }

        bool RecreateDuplication(bool initial)
        {
            const ULONGLONG now = GetTickCount64();
            if (!initial && lastDuplicationRetryMs_ && now - lastDuplicationRetryMs_ < 500)
                return false;
            lastDuplicationRetryMs_ = now;

            ReleaseCom(duplication_);
            HRESULT hr = E_FAIL;
            if (output5_)
            {
                const DXGI_FORMAT supported[] = {
                    DXGI_FORMAT_R16G16B16A16_FLOAT,
                    DXGI_FORMAT_B8G8R8A8_UNORM
                };
                hr = output5_->DuplicateOutput1(device_, 0,
                    static_cast<UINT>(std::size(supported)), supported, &duplication_);
            }
            if ((!duplication_ || FAILED(hr)) && output1_)
            {
                ReleaseCom(duplication_);
                hr = output1_->DuplicateOutput(device_, &duplication_);
            }

            if (FAILED(hr) || !duplication_)
            {
                if (initial || hr != lastDuplicationError_)
                    std::cerr << "VR mirror: DuplicateOutput failed, HRESULT=" << static_cast<long>(hr) << ".\n";
                lastDuplicationError_ = hr;
                return false;
            }

            DXGI_OUTDUPL_DESC desc{};
            duplication_->GetDesc(&desc);
            std::cout << "VR mirror: duplication mode format=" << static_cast<int>(desc.ModeDesc.Format)
                      << (output5_ ? " (DuplicateOutput1 HDR-aware path).\n" : " (DuplicateOutput fallback).\n");
            if (!initial)
                std::cout << "VR mirror: desktop duplication recovered.\n";
            lastDuplicationError_ = S_OK;
            return true;
        }

        bool EnsureSourceTexture(const D3D11_TEXTURE2D_DESC& desktopDesc)
        {
            if (latestSource_ && desktopDesc.Width == sourceWidth_ && desktopDesc.Height == sourceHeight_ &&
                desktopDesc.Format == sourceFormat_)
                return true;

            ReleaseCom(latestSourceSrv_);
            ReleaseCom(latestSource_);

            D3D11_TEXTURE2D_DESC desc{};
            desc.Width = desktopDesc.Width;
            desc.Height = desktopDesc.Height;
            desc.MipLevels = 1;
            desc.ArraySize = 1;
            desc.Format = desktopDesc.Format;
            desc.SampleDesc.Count = 1;
            desc.Usage = D3D11_USAGE_DEFAULT;
            desc.BindFlags = D3D11_BIND_SHADER_RESOURCE;
            if (FAILED(device_->CreateTexture2D(&desc, nullptr, &latestSource_)))
                return false;

            D3D11_SHADER_RESOURCE_VIEW_DESC srvDesc{};
            srvDesc.Format = desktopDesc.Format;
            srvDesc.ViewDimension = D3D11_SRV_DIMENSION_TEXTURE2D;
            srvDesc.Texture2D.MipLevels = 1;
            if (FAILED(device_->CreateShaderResourceView(latestSource_, &srvDesc, &latestSourceSrv_)))
            {
                ReleaseCom(latestSource_);
                return false;
            }

            sourceWidth_ = desktopDesc.Width;
            sourceHeight_ = desktopDesc.Height;
            sourceFormat_ = desktopDesc.Format;
            std::cout << "VR mirror: source surface now " << sourceWidth_ << "x" << sourceHeight_
                      << " format=" << static_cast<int>(sourceFormat_)
                      << (sourceFormat_ == DXGI_FORMAT_R16G16B16A16_FLOAT ? " [FP16 scRGB/HDR]" : " [SDR]")
                      << ".\n";
            return true;
        }

        bool CaptureDesktopFrame(DWORD timeoutMs)
        {
            if (!IsWindow(hwnd_))
                return haveFrame_;
            if (!duplication_ && !RecreateDuplication(false))
                return haveFrame_;

            DXGI_OUTDUPL_FRAME_INFO frameInfo{};
            IDXGIResource* resource = nullptr;
            const HRESULT acquireHr = duplication_->AcquireNextFrame(timeoutMs, &frameInfo, &resource);
            if (acquireHr == DXGI_ERROR_WAIT_TIMEOUT)
                return haveFrame_;
            if (FAILED(acquireHr) || !resource)
            {
                if (acquireHr == DXGI_ERROR_ACCESS_LOST)
                {
                    std::cout << "VR mirror: desktop duplication access lost; rebuilding.\n";
                    ReleaseCom(duplication_);
                    RecreateDuplication(false);
                }
                else
                    std::cerr << "VR mirror: AcquireNextFrame failed, HRESULT=" << static_cast<long>(acquireHr) << ".\n";
                return haveFrame_;
            }

            ID3D11Texture2D* desktopTexture = nullptr;
            const HRESULT textureHr = resource->QueryInterface(
                __uuidof(ID3D11Texture2D), reinterpret_cast<void**>(&desktopTexture));
            resource->Release();

            bool copied = false;
            if (SUCCEEDED(textureHr) && desktopTexture)
            {
                D3D11_TEXTURE2D_DESC desktopDesc{};
                desktopTexture->GetDesc(&desktopDesc);
                if (desktopDesc.Format == DXGI_FORMAT_B8G8R8A8_UNORM ||
                    desktopDesc.Format == DXGI_FORMAT_R16G16B16A16_FLOAT)
                {
                    if (EnsureSourceTexture(desktopDesc))
                    {
                        context_->CopyResource(latestSource_, desktopTexture);
                        context_->Flush();
                        copied = true;
                    }
                }
                else if (desktopDesc.Format != lastUnsupportedFormat_)
                {
                    lastUnsupportedFormat_ = desktopDesc.Format;
                    std::cerr << "VR mirror: unsupported desktop surface format="
                              << static_cast<int>(desktopDesc.Format) << ".\n";
                }
                desktopTexture->Release();
            }

            duplication_->ReleaseFrame();
            if (copied)
                haveFrame_ = true;
            return haveFrame_;
        }

        bool CreateOpenXrSwapchain()
        {
            std::uint32_t count = 0;
            XrResult xr = ::xrEnumerateSwapchainFormats(session_, 0, &count, nullptr);
            if (XR_FAILED(xr) || !count)
                return false;
            std::vector<std::int64_t> formats(count);
            xr = ::xrEnumerateSwapchainFormats(session_, count, &count, formats.data());
            if (XR_FAILED(xr))
                return false;

            const std::array<DXGI_FORMAT, 4> preferences{
                DXGI_FORMAT_B8G8R8A8_UNORM_SRGB,
                DXGI_FORMAT_R8G8B8A8_UNORM_SRGB,
                DXGI_FORMAT_B8G8R8A8_UNORM,
                DXGI_FORMAT_R8G8B8A8_UNORM,
            };

            swapchainFormat_ = DXGI_FORMAT_UNKNOWN;
            for (DXGI_FORMAT preferred : preferences)
            {
                if (std::find(formats.begin(), formats.end(), static_cast<std::int64_t>(preferred)) != formats.end())
                {
                    swapchainFormat_ = preferred;
                    break;
                }
            }
            if (swapchainFormat_ == DXGI_FORMAT_UNKNOWN)
            {
                std::cerr << "VR mirror: no supported 8-bit OpenXR color swapchain. Runtime formats:";
                for (auto format : formats) std::cerr << " " << format;
                std::cerr << "\n";
                return false;
            }

            const bool srgb = swapchainFormat_ == DXGI_FORMAT_B8G8R8A8_UNORM_SRGB ||
                              swapchainFormat_ == DXGI_FORMAT_R8G8B8A8_UNORM_SRGB;
            std::cout << "VR color: OpenXR swapchain format=" << static_cast<int>(swapchainFormat_)
                      << (srgb ? " [sRGB; correct non-linear signaling].\n" : " [linear UNORM fallback].\n");

            XrSwapchainCreateInfo info{ XR_TYPE_SWAPCHAIN_CREATE_INFO };
            info.usageFlags = XR_SWAPCHAIN_USAGE_SAMPLED_BIT | XR_SWAPCHAIN_USAGE_COLOR_ATTACHMENT_BIT;
            info.format = static_cast<std::int64_t>(swapchainFormat_);
            info.sampleCount = 1;
            info.width = width_;
            info.height = height_;
            info.faceCount = 1;
            info.arraySize = 1;
            info.mipCount = 1;
            xr = ::xrCreateSwapchain(session_, &info, &swapchain_);
            if (XR_FAILED(xr))
                return false;

            std::uint32_t imageCount = 0;
            xr = ::xrEnumerateSwapchainImages(swapchain_, 0, &imageCount, nullptr);
            if (XR_FAILED(xr) || !imageCount)
                return false;
            images_.resize(imageCount);
            for (auto& image : images_)
                image = { XR_TYPE_SWAPCHAIN_IMAGE_D3D11_KHR };
            xr = ::xrEnumerateSwapchainImages(swapchain_, imageCount, &imageCount,
                reinterpret_cast<XrSwapchainImageBaseHeader*>(images_.data()));
            if (XR_FAILED(xr))
                return false;

            renderTargets_.resize(imageCount, nullptr);
            for (std::uint32_t i = 0; i < imageCount; ++i)
            {
                D3D11_RENDER_TARGET_VIEW_DESC rtvDesc{};
                rtvDesc.Format = swapchainFormat_;
                rtvDesc.ViewDimension = D3D11_RTV_DIMENSION_TEXTURE2D;
                if (FAILED(device_->CreateRenderTargetView(images_[i].texture, &rtvDesc, &renderTargets_[i])))
                    return false;
            }
            return true;
        }

        void RenderConvertedFrame(std::uint32_t imageIndex)
        {
            if (imageIndex >= renderTargets_.size() || !renderTargets_[imageIndex] || !latestSourceSrv_)
                return;

            D3D11_MAPPED_SUBRESOURCE mapped{};
            if (SUCCEEDED(context_->Map(constantBuffer_, 0, D3D11_MAP_WRITE_DISCARD, 0, &mapped)))
            {
                auto* params = static_cast<MirrorParams*>(mapped.pData);
                params->sdrWhiteScale = sdrWhiteScale_;
                params->sourceIsScRgb = sourceFormat_ == DXGI_FORMAT_R16G16B16A16_FLOAT ? 1.0f : 0.0f;
                params->padding[0] = params->padding[1] = 0.0f;
                context_->Unmap(constantBuffer_, 0);
            }

            D3D11_VIEWPORT viewport{};
            viewport.Width = static_cast<float>(width_);
            viewport.Height = static_cast<float>(height_);
            viewport.MinDepth = 0.0f;
            viewport.MaxDepth = 1.0f;
            context_->RSSetViewports(1, &viewport);
            context_->OMSetRenderTargets(1, &renderTargets_[imageIndex], nullptr);
            context_->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
            context_->VSSetShader(vertexShader_, nullptr, 0);
            context_->PSSetShader(pixelShader_, nullptr, 0);
            context_->PSSetShaderResources(0, 1, &latestSourceSrv_);
            context_->PSSetSamplers(0, 1, &sampler_);
            context_->PSSetConstantBuffers(0, 1, &constantBuffer_);
            context_->Draw(3, 0);

            ID3D11ShaderResourceView* nullSrv = nullptr;
            context_->PSSetShaderResources(0, 1, &nullSrv);
            ID3D11RenderTargetView* nullRtv = nullptr;
            context_->OMSetRenderTargets(1, &nullRtv, nullptr);
            context_->Flush();
        }

        void ResetAll()
        {
            for (auto*& rtv : renderTargets_)
                ReleaseCom(rtv);
            renderTargets_.clear();
            images_.clear();
            if (swapchain_ != XR_NULL_HANDLE)
            {
                ::xrDestroySwapchain(swapchain_);
                swapchain_ = XR_NULL_HANDLE;
            }

            ReleaseCom(latestSourceSrv_);
            ReleaseCom(latestSource_);
            ReleaseCom(constantBuffer_);
            ReleaseCom(sampler_);
            ReleaseCom(pixelShader_);
            ReleaseCom(vertexShader_);
            ReleaseCom(duplication_);
            ReleaseCom(output5_);
            ReleaseCom(output1_);
            ReleaseCom(context_);
            ReleaseCom(device_);

            if (sharedState_)
            {
                UnmapViewOfFile(sharedState_);
                sharedState_ = nullptr;
            }
            if (sharedMapping_)
            {
                CloseHandle(sharedMapping_);
                sharedMapping_ = nullptr;
            }
            if (gameProcess_)
            {
                CloseHandle(gameProcess_);
                gameProcess_ = nullptr;
            }

            session_ = XR_NULL_HANDLE;
            viewSpace_ = XR_NULL_HANDLE;
            hwnd_ = nullptr;
            gamePid_ = 0;
            targetMonitor_ = nullptr;
            width_ = height_ = sourceWidth_ = sourceHeight_ = 0;
            sourceFormat_ = DXGI_FORMAT_UNKNOWN;
            swapchainFormat_ = DXGI_FORMAT_UNKNOWN;
            lastUnsupportedFormat_ = DXGI_FORMAT_UNKNOWN;
            outputDesktop_ = {};
            haveFrame_ = false;
            initialized_ = false;
            lastDuplicationRetryMs_ = 0;
            lastDuplicationError_ = S_OK;
            lastClientPid_ = 0;
            lastClientTelemetryLogMs_ = 0;
        }

        XrSession session_ = XR_NULL_HANDLE;
        XrSpace viewSpace_ = XR_NULL_HANDLE;
        ID3D11Device* device_ = nullptr;
        ID3D11DeviceContext* context_ = nullptr;
        HWND hwnd_ = nullptr;
        DWORD gamePid_ = 0;
        HANDLE gameProcess_ = nullptr;
        HMONITOR targetMonitor_ = nullptr;

        IDXGIOutput1* output1_ = nullptr;
        IDXGIOutput5* output5_ = nullptr;
        IDXGIOutputDuplication* duplication_ = nullptr;
        RECT outputDesktop_{};

        ID3D11Texture2D* latestSource_ = nullptr;
        ID3D11ShaderResourceView* latestSourceSrv_ = nullptr;
        DXGI_FORMAT sourceFormat_ = DXGI_FORMAT_UNKNOWN;
        DXGI_FORMAT lastUnsupportedFormat_ = DXGI_FORMAT_UNKNOWN;
        std::uint32_t sourceWidth_ = 0;
        std::uint32_t sourceHeight_ = 0;

        ID3D11VertexShader* vertexShader_ = nullptr;
        ID3D11PixelShader* pixelShader_ = nullptr;
        ID3D11SamplerState* sampler_ = nullptr;
        ID3D11Buffer* constantBuffer_ = nullptr;

        XrSwapchain swapchain_ = XR_NULL_HANDLE;
        DXGI_FORMAT swapchainFormat_ = DXGI_FORMAT_UNKNOWN;
        std::vector<XrSwapchainImageD3D11KHR> images_;
        std::vector<ID3D11RenderTargetView*> renderTargets_;

        HANDLE sharedMapping_ = nullptr;
        const OutRunVR::SharedPoseState* sharedState_ = nullptr;
        std::uint32_t lastClientPid_ = 0;
        ULONGLONG lastClientTelemetryLogMs_ = 0;

        std::uint32_t width_ = 0;
        std::uint32_t height_ = 0;
        float sdrWhiteScale_ = 1.0f;
        bool haveFrame_ = false;
        bool initialized_ = false;
        ULONGLONG lastDuplicationRetryMs_ = 0;
        HRESULT lastDuplicationError_ = S_OK;
    };

    MonoMirror Mirror;
    bool GameExitRequested = false;
    bool SyntheticExitSent = false;
    ULONGLONG GameExitRequestMs = 0;
    ULONGLONG LastPoseTelemetryMs = 0;

    XrResult XRAPI_PTR OutRunRetryingXrGetSystem(
        XrInstance instance, const XrSystemGetInfo* getInfo, XrSystemId* systemId)
    {
        bool waitingReported = false;
        for (;;)
        {
            const XrResult result = ::xrGetSystem(instance, getInfo, systemId);
            if (result != XR_ERROR_FORM_FACTOR_UNAVAILABLE)
            {
                if (waitingReported && XR_SUCCEEDED(result))
                    std::cout << "OpenXR HMD is now available. Continuing startup.\n";
                return result;
            }
            if (!waitingReported)
            {
                std::cout
                    << "OpenXR runtime is available, but no HMD is ready yet.\n"
                    << "Waiting for Quest / Virtual Desktop VR session...\n"
                    << "Keep the headset awake and connected. Ctrl+C cancels.\n";
                waitingReported = true;
            }
            Sleep(1000);
        }
    }

    XrResult XRAPI_PTR OutRunMirrorXrCreateSession(
        XrInstance instance, const XrSessionCreateInfo* createInfo, XrSession* session)
    {
        SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);
        const HWND gameWindow = WaitForGameWindow();

        ID3D11Device* d3dDevice = nullptr;
        for (auto* chain = reinterpret_cast<const XrBaseInStructure*>(createInfo->next);
             chain; chain = chain->next)
        {
            if (chain->type == XR_TYPE_GRAPHICS_BINDING_D3D11_KHR)
            {
                d3dDevice = reinterpret_cast<const XrGraphicsBindingD3D11KHR*>(chain)->device;
                break;
            }
        }

        const XrResult result = ::xrCreateSession(instance, createInfo, session);
        if (XR_SUCCEEDED(result) && session && *session != XR_NULL_HANDLE)
        {
            GameExitRequested = false;
            SyntheticExitSent = false;
            GameExitRequestMs = 0;
            Mirror.OnSessionCreated(*session, d3dDevice, gameWindow);
            if (!Mirror.Initialize())
            {
                Mirror.BeforeSessionDestroy(*session);
                ::xrDestroySession(*session);
                *session = XR_NULL_HANDLE;
                return XR_ERROR_RUNTIME_FAILURE;
            }
        }
        return result;
    }

    XrResult XRAPI_PTR OutRunMirrorXrCreateReferenceSpace(
        XrSession session, const XrReferenceSpaceCreateInfo* createInfo, XrSpace* space)
    {
        const XrResult result = ::xrCreateReferenceSpace(session, createInfo, space);
        if (XR_SUCCEEDED(result) && createInfo && space &&
            createInfo->referenceSpaceType == XR_REFERENCE_SPACE_TYPE_VIEW)
            Mirror.OnViewSpaceCreated(*space);
        return result;
    }

    XrResult XRAPI_PTR OutRunTelemetryXrLocateSpace(
        XrSpace space, XrSpace baseSpace, XrTime time, XrSpaceLocation* location)
    {
        const XrResult result = ::xrLocateSpace(space, baseSpace, time, location);
        if (XR_SUCCEEDED(result) && location &&
            (location->locationFlags & XR_SPACE_LOCATION_ORIENTATION_VALID_BIT))
        {
            const ULONGLONG now = GetTickCount64();
            if (now - LastPoseTelemetryMs >= 1000)
            {
                LastPoseTelemetryMs = now;
                const auto& q = location->pose.orientation;
                const auto& p = location->pose.position;
                std::cout << "VR pose: q=(" << q.x << "," << q.y << "," << q.z << "," << q.w
                          << ") p=(" << p.x << "," << p.y << "," << p.z << ") flags=0x"
                          << std::hex << location->locationFlags << std::dec << ".\n";
            }
        }
        return result;
    }

    XrResult XRAPI_PTR OutRunMirrorXrEndFrame(XrSession session, const XrFrameEndInfo* frameEndInfo)
    {
        if (!frameEndInfo)
            return ::xrEndFrame(session, frameEndInfo);

        if (!Mirror.GameAlive())
        {
            if (!GameExitRequested)
            {
                GameExitRequested = true;
                GameExitRequestMs = GetTickCount64();
                std::cout << "OutRun process exited. Requesting OpenXR session shutdown and Virtual Desktop return...\n";
                const XrResult request = ::xrRequestExitSession(session);
                if (XR_FAILED(request))
                    std::cerr << "xrRequestExitSession returned " << request << "; cleanup fallback will still release the session.\n";
            }
            XrFrameEndInfo empty = *frameEndInfo;
            empty.layerCount = 0;
            empty.layers = nullptr;
            return ::xrEndFrame(session, &empty);
        }

        if (frameEndInfo->layerCount != 0 || !Mirror.CaptureAndRenderToSwapchain() || !Mirror.ReadyForLayer())
            return ::xrEndFrame(session, frameEndInfo);

        XrCompositionLayerQuad quad = Mirror.MakeQuad();
        const XrCompositionLayerBaseHeader* layer =
            reinterpret_cast<const XrCompositionLayerBaseHeader*>(&quad);
        XrFrameEndInfo patched = *frameEndInfo;
        patched.layerCount = 1;
        patched.layers = &layer;
        return ::xrEndFrame(session, &patched);
    }

    XrResult XRAPI_PTR OutRunExitAwareXrPollEvent(XrInstance instance, XrEventDataBuffer* eventData)
    {
        const XrResult result = ::xrPollEvent(instance, eventData);
        if (result != XR_EVENT_UNAVAILABLE)
            return result;

        if (GameExitRequested && !SyntheticExitSent &&
            GameExitRequestMs && GetTickCount64() - GameExitRequestMs > 2000 && eventData)
        {
            auto* changed = reinterpret_cast<XrEventDataSessionStateChanged*>(eventData);
            *changed = { XR_TYPE_EVENT_DATA_SESSION_STATE_CHANGED };
            changed->session = Mirror.Session();
            changed->state = XR_SESSION_STATE_EXITING;
            SyntheticExitSent = true;
            std::cout << "OpenXR runtime did not finish shutdown promptly; forcing host cleanup now.\n";
            return XR_SUCCESS;
        }
        return result;
    }

    XrResult XRAPI_PTR OutRunMirrorXrDestroySession(XrSession session)
    {
        Mirror.BeforeSessionDestroy(session);
        return ::xrDestroySession(session);
    }
}

#undef XR_CURRENT_API_VERSION
#define XR_CURRENT_API_VERSION XR_MAKE_VERSION(1, 0, 0)

#define xrGetSystem OutRunRetryingXrGetSystem
#define xrCreateSession OutRunMirrorXrCreateSession
#define xrCreateReferenceSpace OutRunMirrorXrCreateReferenceSpace
#define xrLocateSpace OutRunTelemetryXrLocateSpace
#define xrEndFrame OutRunMirrorXrEndFrame
#define xrPollEvent OutRunExitAwareXrPollEvent
#define xrDestroySession OutRunMirrorXrDestroySession
#include "main.cpp"
