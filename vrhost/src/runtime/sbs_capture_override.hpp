#pragma once

// R10 hardware-fix bridge.
//
// R9 proved that the game-side renderer is now producing complete SBS frames
// (StereoSbsActive, composeOk increasing, no depth/stencil/depthState failures),
// but the Quest still did not receive the game image.  This module bypasses the
// legacy host's fragile frame/QPC matching and crop path at the final OpenXR
// submission boundary:
//
//   D3D9 SBS on monitor -> Desktop Duplication -> host-owned D3D11 texture
//   -> split left/right -> dedicated OpenXR projection swapchain.
//
// It deliberately keeps the exact projection poses/FOV already chosen by the
// legacy host when those are available.  If the frame ring advances while the
// desktop capture is copied, the copied texture stays valid because it is
// host-owned; the ring no longer has to remain byte-identical after capture.
//
// Menus are also mirrored through an independent VIEW-space quad so the HMD does
// not depend on the old theater blit path.  Set OUTRUN_VR_CAPTURE_OVERRIDE=0 to
// disable this bridge without changing binaries.

#include "openxr_api_compat.hpp"

#ifdef xrEndFrame
#undef xrEndFrame
#endif
#ifdef xrDestroySession
#undef xrDestroySession
#endif

#include <TlHelp32.h>
#include <d3dcompiler.h>
#include <dxgi1_5.h>

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <vector>

namespace OutRunVrSbsCaptureOverride
{
    inline constexpr const char* BuildId = "R10-sbs-capture-override-20260915";
    inline constexpr wchar_t GameExeName[] = L"OR2006C2C.EXE";

    template <typename T>
    inline void ReleaseCom(T*& value)
    {
        if (value)
        {
            value->Release();
            value = nullptr;
        }
    }

    inline bool Enabled()
    {
        const char* value = std::getenv("OUTRUN_VR_CAPTURE_OVERRIDE");
        return !value || (std::strcmp(value, "0") != 0 && _stricmp(value, "false") != 0 && _stricmp(value, "off") != 0);
    }

    inline DWORD FindGamePid()
    {
        HANDLE snap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
        if (snap == INVALID_HANDLE_VALUE)
            return 0;
        PROCESSENTRY32W entry{};
        entry.dwSize = sizeof(entry);
        DWORD pid = 0;
        if (Process32FirstW(snap, &entry))
        {
            do
            {
                if (_wcsicmp(entry.szExeFile, GameExeName) == 0)
                {
                    pid = entry.th32ProcessID;
                    break;
                }
            } while (Process32NextW(snap, &entry));
        }
        CloseHandle(snap);
        return pid;
    }

    struct WindowSearch
    {
        DWORD pid = 0;
        HWND best = nullptr;
        long long area = 0;
    };

    inline BOOL CALLBACK EnumWindowsProc(HWND hwnd, LPARAM param)
    {
        auto* state = reinterpret_cast<WindowSearch*>(param);
        DWORD pid = 0;
        GetWindowThreadProcessId(hwnd, &pid);
        if (pid != state->pid || !IsWindowVisible(hwnd))
            return TRUE;
        RECT r{};
        if (!GetClientRect(hwnd, &r))
            return TRUE;
        const long long w = r.right - r.left;
        const long long h = r.bottom - r.top;
        const long long area = w * h;
        if (w >= 320 && h >= 200 && area > state->area)
        {
            state->best = hwnd;
            state->area = area;
        }
        return TRUE;
    }

    inline HWND FindGameWindow()
    {
        WindowSearch state{};
        state.pid = FindGamePid();
        if (!state.pid)
            return nullptr;
        EnumWindows(EnumWindowsProc, reinterpret_cast<LPARAM>(&state));
        return state.best;
    }

    struct UvRect
    {
        float x = 0.f;
        float y = 0.f;
        float w = 1.f;
        float h = 1.f;
    };

    struct BlitParams
    {
        float uvScale[2];
        float uvOffset[2];
        float sdrWhiteScale;
        float sourceIsScRgb;
        float padding[2];
    };

    inline constexpr const char* BlitShader = R"HLSL(
Texture2D SourceTexture : register(t0);
SamplerState SourceSampler : register(s0);
cbuffer BlitParams : register(b0)
{
    float2 UvScale;
    float2 UvOffset;
    float SdrWhiteScale;
    float SourceIsScRgb;
    float2 Padding;
};
struct VSOut { float4 position : SV_Position; float2 uv : TEXCOORD0; };
VSOut VSMain(uint id : SV_VertexID)
{
    VSOut o;
    float2 uv = float2((id << 1) & 2, id & 2);
    o.position = float4(uv * float2(2.0, -2.0) + float2(-1.0, 1.0), 0.0, 1.0);
    o.uv = uv * UvScale + UvOffset;
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
    float3 linearColor = SourceIsScRgb > 0.5
        ? max(src.rgb, 0.0) / max(SdrWhiteScale, 0.001)
        : SrgbToLinear(saturate(src.rgb));
    return float4(saturate(linearColor), 1.0);
}
)HLSL";

    struct Swapchain
    {
        XrSwapchain handle = XR_NULL_HANDLE;
        std::uint32_t width = 0;
        std::uint32_t height = 0;
        std::uint32_t arraySize = 1;
        DXGI_FORMAT format = DXGI_FORMAT_UNKNOWN;
        std::vector<XrSwapchainImageD3D11KHR> images;
        std::vector<std::array<ID3D11RenderTargetView*, 2>> rtvs;
        bool acquired = false;
        bool waited = false;
        std::uint32_t acquiredImage = 0;

        void Destroy()
        {
            for (auto& pair : rtvs)
            {
                ReleaseCom(pair[0]);
                ReleaseCom(pair[1]);
            }
            rtvs.clear();
            images.clear();
            if (handle != XR_NULL_HANDLE)
            {
                ::xrDestroySwapchain(handle);
                handle = XR_NULL_HANDLE;
            }
            width = height = 0;
            arraySize = 1;
            format = DXGI_FORMAT_UNKNOWN;
            acquired = false;
            waited = false;
            acquiredImage = 0;
        }
    };

    inline HWND GameWindow = nullptr;
    inline HMONITOR TargetMonitor = nullptr;
    inline RECT OutputDesktop{};
    inline IDXGIOutput1* Output1 = nullptr;
    inline IDXGIOutput5* Output5 = nullptr;
    inline IDXGIOutputDuplication* Duplication = nullptr;
    inline ID3D11Texture2D* Source = nullptr;
    inline ID3D11ShaderResourceView* SourceSrv = nullptr;
    inline std::uint32_t SourceWidth = 0;
    inline std::uint32_t SourceHeight = 0;
    inline DXGI_FORMAT SourceFormat = DXGI_FORMAT_UNKNOWN;
    inline bool HaveSource = false;
    inline float SdrWhiteScale = 1.f;

    inline ID3D11VertexShader* Vs = nullptr;
    inline ID3D11PixelShader* Ps = nullptr;
    inline ID3D11SamplerState* Sampler = nullptr;
    inline ID3D11Buffer* ConstantBuffer = nullptr;
    inline Swapchain Projection{};
    inline Swapchain Theater{};
    inline XrSpace ViewSpace = XR_NULL_HANDLE;

    inline OutRunVR::SharedRenderFrameState LastStereoFrame{};
    inline bool LastStereoFrameValid = false;
    inline ULONGLONG LastStereoFrameMs = 0;

    inline std::uint64_t EndFrames = 0;
    inline std::uint64_t CaptureFresh = 0;
    inline std::uint64_t CaptureTimeout = 0;
    inline std::uint64_t CaptureFailure = 0;
    inline std::uint64_t ProjectionAttempts = 0;
    inline std::uint64_t ProjectionSuccess = 0;
    inline std::uint64_t TheaterAttempts = 0;
    inline std::uint64_t TheaterSuccess = 0;
    inline std::uint64_t MainProjectionSeen = 0;
    inline std::uint64_t MainQuadSeen = 0;
    inline ULONGLONG LastSummaryMs = 0;
    inline bool CaptureInfoLogged = false;
    inline bool ProjectionLogged = false;
    inline bool TheaterLogged = false;

    inline void ResetCapture()
    {
        ReleaseCom(SourceSrv);
        ReleaseCom(Source);
        ReleaseCom(Duplication);
        ReleaseCom(Output5);
        ReleaseCom(Output1);
        TargetMonitor = nullptr;
        OutputDesktop = {};
        SourceWidth = SourceHeight = 0;
        SourceFormat = DXGI_FORMAT_UNKNOWN;
        HaveSource = false;
        CaptureInfoLogged = false;
    }

    inline void ResetAll()
    {
        Projection.Destroy();
        Theater.Destroy();
        if (ViewSpace != XR_NULL_HANDLE)
        {
            ::xrDestroySpace(ViewSpace);
            ViewSpace = XR_NULL_HANDLE;
        }
        ResetCapture();
        ReleaseCom(ConstantBuffer);
        ReleaseCom(Sampler);
        ReleaseCom(Ps);
        ReleaseCom(Vs);
        LastStereoFrame = {};
        LastStereoFrameValid = false;
        LastStereoFrameMs = 0;
    }

    inline float QuerySdrWhiteScale(HMONITOR monitor)
    {
        char value[64]{};
        const DWORD n = GetEnvironmentVariableA("OUTRUN_VR_SDR_WHITE_SCALE", value, sizeof(value));
        if (n > 0 && n < sizeof(value))
        {
            char* end = nullptr;
            const float v = std::strtof(value, &end);
            if (end != value && std::isfinite(v) && v >= 0.25f && v <= 8.f)
                return v;
        }

        MONITORINFOEXW mi{};
        mi.cbSize = sizeof(mi);
        if (!monitor || !GetMonitorInfoW(monitor, &mi))
            return 1.f;
        UINT32 pc = 0, mc = 0;
        if (GetDisplayConfigBufferSizes(QDC_ONLY_ACTIVE_PATHS, &pc, &mc) != ERROR_SUCCESS)
            return 1.f;
        std::vector<DISPLAYCONFIG_PATH_INFO> paths(pc);
        std::vector<DISPLAYCONFIG_MODE_INFO> modes(mc);
        if (QueryDisplayConfig(QDC_ONLY_ACTIVE_PATHS, &pc, paths.data(), &mc, modes.data(), nullptr) != ERROR_SUCCESS)
            return 1.f;
        for (UINT32 i = 0; i < pc; ++i)
        {
            DISPLAYCONFIG_SOURCE_DEVICE_NAME src{};
            src.header.type = DISPLAYCONFIG_DEVICE_INFO_GET_SOURCE_NAME;
            src.header.size = sizeof(src);
            src.header.adapterId = paths[i].sourceInfo.adapterId;
            src.header.id = paths[i].sourceInfo.id;
            if (DisplayConfigGetDeviceInfo(&src.header) != ERROR_SUCCESS ||
                _wcsicmp(src.viewGdiDeviceName, mi.szDevice) != 0)
                continue;
            DISPLAYCONFIG_SDR_WHITE_LEVEL white{};
            white.header.type = DISPLAYCONFIG_DEVICE_INFO_GET_SDR_WHITE_LEVEL;
            white.header.size = sizeof(white);
            white.header.adapterId = paths[i].targetInfo.adapterId;
            white.header.id = paths[i].targetInfo.id;
            if (DisplayConfigGetDeviceInfo(&white.header) == ERROR_SUCCESS && white.SDRWhiteLevel > 0)
                return std::clamp(static_cast<float>(white.SDRWhiteLevel) / 1000.f, 0.25f, 8.f);
        }
        return 1.f;
    }

    inline bool CreateShaders()
    {
        if (Vs && Ps && Sampler && ConstantBuffer)
            return true;
        if (!OutRunVrFinalTest::Device)
            return false;

        ID3DBlob* vsCode = nullptr;
        ID3DBlob* psCode = nullptr;
        ID3DBlob* errors = nullptr;
        HRESULT hr = D3DCompile(BlitShader, std::strlen(BlitShader), "OutRunR10Blit", nullptr, nullptr,
            "VSMain", "vs_5_0", D3DCOMPILE_ENABLE_STRICTNESS | D3DCOMPILE_OPTIMIZATION_LEVEL3,
            0, &vsCode, &errors);
        ReleaseCom(errors);
        if (FAILED(hr) || !vsCode)
            return false;
        hr = D3DCompile(BlitShader, std::strlen(BlitShader), "OutRunR10Blit", nullptr, nullptr,
            "PSMain", "ps_5_0", D3DCOMPILE_ENABLE_STRICTNESS | D3DCOMPILE_OPTIMIZATION_LEVEL3,
            0, &psCode, &errors);
        ReleaseCom(errors);
        if (FAILED(hr) || !psCode)
        {
            ReleaseCom(vsCode);
            return false;
        }
        hr = OutRunVrFinalTest::Device->CreateVertexShader(vsCode->GetBufferPointer(), vsCode->GetBufferSize(), nullptr, &Vs);
        if (SUCCEEDED(hr))
            hr = OutRunVrFinalTest::Device->CreatePixelShader(psCode->GetBufferPointer(), psCode->GetBufferSize(), nullptr, &Ps);
        ReleaseCom(vsCode);
        ReleaseCom(psCode);
        if (FAILED(hr) || !Vs || !Ps)
            return false;

        D3D11_SAMPLER_DESC sd{};
        sd.Filter = D3D11_FILTER_MIN_MAG_MIP_LINEAR;
        sd.AddressU = sd.AddressV = sd.AddressW = D3D11_TEXTURE_ADDRESS_CLAMP;
        if (FAILED(OutRunVrFinalTest::Device->CreateSamplerState(&sd, &Sampler)))
            return false;

        D3D11_BUFFER_DESC bd{};
        bd.ByteWidth = sizeof(BlitParams);
        bd.Usage = D3D11_USAGE_DYNAMIC;
        bd.BindFlags = D3D11_BIND_CONSTANT_BUFFER;
        bd.CPUAccessFlags = D3D11_CPU_ACCESS_WRITE;
        if (FAILED(OutRunVrFinalTest::Device->CreateBuffer(&bd, nullptr, &ConstantBuffer)))
            return false;
        return true;
    }

    inline bool BindOutput()
    {
        if (!OutRunVrFinalTest::Device)
            return false;
        if (!GameWindow || !IsWindow(GameWindow))
            GameWindow = FindGameWindow();
        if (!GameWindow)
            return false;
        const HMONITOR monitor = MonitorFromWindow(GameWindow, MONITOR_DEFAULTTONEAREST);
        if (!monitor)
            return false;
        if (Duplication && monitor == TargetMonitor)
            return true;

        ResetCapture();
        TargetMonitor = monitor;

        IDXGIDevice* dxgiDevice = nullptr;
        if (FAILED(OutRunVrFinalTest::Device->QueryInterface(__uuidof(IDXGIDevice), reinterpret_cast<void**>(&dxgiDevice))) || !dxgiDevice)
            return false;
        IDXGIAdapter* adapter = nullptr;
        const HRESULT adapterHr = dxgiDevice->GetAdapter(&adapter);
        dxgiDevice->Release();
        if (FAILED(adapterHr) || !adapter)
            return false;

        IDXGIOutput* selected = nullptr;
        DXGI_OUTPUT_DESC outputDesc{};
        for (UINT i = 0;; ++i)
        {
            IDXGIOutput* output = nullptr;
            if (adapter->EnumOutputs(i, &output) == DXGI_ERROR_NOT_FOUND)
                break;
            DXGI_OUTPUT_DESC d{};
            output->GetDesc(&d);
            if (d.Monitor == TargetMonitor)
            {
                selected = output;
                outputDesc = d;
                break;
            }
            output->Release();
        }
        adapter->Release();
        if (!selected)
            return false;

        selected->QueryInterface(__uuidof(IDXGIOutput1), reinterpret_cast<void**>(&Output1));
        selected->QueryInterface(__uuidof(IDXGIOutput5), reinterpret_cast<void**>(&Output5));
        selected->Release();
        if (!Output1)
            return false;

        OutputDesktop = outputDesc.DesktopCoordinates;
        SdrWhiteScale = QuerySdrWhiteScale(TargetMonitor);

        HRESULT hr = E_FAIL;
        if (Output5)
        {
            const DXGI_FORMAT formats[]{ DXGI_FORMAT_R16G16B16A16_FLOAT, DXGI_FORMAT_B8G8R8A8_UNORM };
            hr = Output5->DuplicateOutput1(OutRunVrFinalTest::Device, 0, 2, formats, &Duplication);
        }
        if ((FAILED(hr) || !Duplication) && Output1)
        {
            ReleaseCom(Duplication);
            hr = Output1->DuplicateOutput(OutRunVrFinalTest::Device, &Duplication);
        }
        if (FAILED(hr) || !Duplication)
        {
            ++CaptureFailure;
            return false;
        }

        std::cerr << "[R10] capture output bound desktop="
                  << (OutputDesktop.right - OutputDesktop.left) << "x"
                  << (OutputDesktop.bottom - OutputDesktop.top)
                  << " sdrWhiteScale=" << SdrWhiteScale << "\n";
        return true;
    }

    inline bool EnsureSource(const D3D11_TEXTURE2D_DESC& desc)
    {
        if (Source && SourceSrv && SourceWidth == desc.Width && SourceHeight == desc.Height && SourceFormat == desc.Format)
            return true;
        ReleaseCom(SourceSrv);
        ReleaseCom(Source);

        D3D11_TEXTURE2D_DESC d{};
        d.Width = desc.Width;
        d.Height = desc.Height;
        d.MipLevels = 1;
        d.ArraySize = 1;
        d.Format = desc.Format;
        d.SampleDesc.Count = 1;
        d.Usage = D3D11_USAGE_DEFAULT;
        d.BindFlags = D3D11_BIND_SHADER_RESOURCE;
        if (FAILED(OutRunVrFinalTest::Device->CreateTexture2D(&d, nullptr, &Source)) || !Source)
            return false;
        D3D11_SHADER_RESOURCE_VIEW_DESC vd{};
        vd.Format = d.Format;
        vd.ViewDimension = D3D11_SRV_DIMENSION_TEXTURE2D;
        vd.Texture2D.MipLevels = 1;
        if (FAILED(OutRunVrFinalTest::Device->CreateShaderResourceView(Source, &vd, &SourceSrv)) || !SourceSrv)
        {
            ReleaseCom(Source);
            return false;
        }
        SourceWidth = d.Width;
        SourceHeight = d.Height;
        SourceFormat = d.Format;
        CaptureInfoLogged = false;
        return true;
    }

    inline bool CaptureDesktop(DWORD timeoutMs)
    {
        if (!BindOutput() || !Duplication || !OutRunVrFinalTest::Context)
            return HaveSource;

        DXGI_OUTDUPL_FRAME_INFO info{};
        IDXGIResource* resource = nullptr;
        const DWORD waitMs = HaveSource ? timeoutMs : std::max<DWORD>(timeoutMs, 1000);
        const HRESULT hr = Duplication->AcquireNextFrame(waitMs, &info, &resource);
        if (hr == DXGI_ERROR_WAIT_TIMEOUT)
        {
            ++CaptureTimeout;
            return HaveSource;
        }
        if (FAILED(hr) || !resource)
        {
            ++CaptureFailure;
            if (hr == DXGI_ERROR_ACCESS_LOST)
                ResetCapture();
            return HaveSource;
        }

        ID3D11Texture2D* texture = nullptr;
        const HRESULT qi = resource->QueryInterface(__uuidof(ID3D11Texture2D), reinterpret_cast<void**>(&texture));
        resource->Release();
        bool copied = false;
        if (SUCCEEDED(qi) && texture)
        {
            D3D11_TEXTURE2D_DESC desc{};
            texture->GetDesc(&desc);
            if ((desc.Format == DXGI_FORMAT_B8G8R8A8_UNORM || desc.Format == DXGI_FORMAT_R16G16B16A16_FLOAT) && EnsureSource(desc))
            {
                OutRunVrFinalTest::Context->CopyResource(Source, texture);
                copied = true;
            }
            texture->Release();
        }
        Duplication->ReleaseFrame();

        if (copied)
        {
            HaveSource = true;
            ++CaptureFresh;
            if (!CaptureInfoLogged)
            {
                CaptureInfoLogged = true;
                std::cerr << "[R10] desktop source=" << SourceWidth << "x" << SourceHeight
                          << " fmt=" << static_cast<int>(SourceFormat)
                          << " accumulated=" << info.AccumulatedFrames << "\n";
            }
        }
        else
        {
            ++CaptureFailure;
        }
        return HaveSource;
    }

    inline bool GetGameUv(UvRect& uv)
    {
        if (!SourceWidth || !SourceHeight)
            return false;
        if (!GameWindow || !IsWindow(GameWindow))
            GameWindow = FindGameWindow();
        if (!GameWindow)
            return false;

        RECT client{};
        if (!GetClientRect(GameWindow, &client))
            return false;
        POINT tl{ client.left, client.top };
        POINT br{ client.right, client.bottom };
        if (!ClientToScreen(GameWindow, &tl) || !ClientToScreen(GameWindow, &br))
            return false;

        const long outputW = OutputDesktop.right - OutputDesktop.left;
        const long outputH = OutputDesktop.bottom - OutputDesktop.top;
        const long clientW = br.x - tl.x;
        const long clientH = br.y - tl.y;
        if (outputW > 0 && outputH > 0 &&
            clientW >= static_cast<long>(outputW * 0.90) && clientH >= static_cast<long>(outputH * 0.90))
        {
            uv = { 0.f, 0.f, 1.f, 1.f };
            return true;
        }

        const float l = static_cast<float>(tl.x - OutputDesktop.left) / static_cast<float>(SourceWidth);
        const float t = static_cast<float>(tl.y - OutputDesktop.top) / static_cast<float>(SourceHeight);
        const float r = static_cast<float>(br.x - OutputDesktop.left) / static_cast<float>(SourceWidth);
        const float b = static_cast<float>(br.y - OutputDesktop.top) / static_cast<float>(SourceHeight);
        uv.x = std::clamp(l, 0.f, 1.f);
        uv.y = std::clamp(t, 0.f, 1.f);
        const float rr = std::clamp(r, 0.f, 1.f);
        const float bb = std::clamp(b, 0.f, 1.f);
        uv.w = rr - uv.x;
        uv.h = bb - uv.y;
        return uv.w > 0.01f && uv.h > 0.01f;
    }

    inline DXGI_FORMAT ChooseSwapchainFormat(XrSession session)
    {
        std::uint32_t count = 0;
        if (XR_FAILED(::xrEnumerateSwapchainFormats(session, 0, &count, nullptr)) || !count)
            return DXGI_FORMAT_UNKNOWN;
        std::vector<std::int64_t> formats(count);
        if (XR_FAILED(::xrEnumerateSwapchainFormats(session, count, &count, formats.data())))
            return DXGI_FORMAT_UNKNOWN;
        const DXGI_FORMAT preferred[]{
            DXGI_FORMAT_R8G8B8A8_UNORM_SRGB,
            DXGI_FORMAT_B8G8R8A8_UNORM_SRGB,
            DXGI_FORMAT_R8G8B8A8_UNORM,
            DXGI_FORMAT_B8G8R8A8_UNORM
        };
        for (const auto format : preferred)
            if (std::find(formats.begin(), formats.end(), static_cast<std::int64_t>(format)) != formats.end())
                return format;
        return DXGI_FORMAT_UNKNOWN;
    }

    inline bool EnsureSwapchain(Swapchain& swapchain, XrSession session, std::uint32_t width,
        std::uint32_t height, std::uint32_t arraySize)
    {
        if (swapchain.handle != XR_NULL_HANDLE && swapchain.width == width && swapchain.height == height &&
            swapchain.arraySize == arraySize && !swapchain.images.empty())
            return true;

        swapchain.Destroy();
        const DXGI_FORMAT format = ChooseSwapchainFormat(session);
        if (format == DXGI_FORMAT_UNKNOWN || !width || !height || (arraySize != 1 && arraySize != 2))
            return false;

        XrSwapchainCreateInfo create{ XR_TYPE_SWAPCHAIN_CREATE_INFO };
        create.usageFlags = XR_SWAPCHAIN_USAGE_COLOR_ATTACHMENT_BIT | XR_SWAPCHAIN_USAGE_SAMPLED_BIT;
        create.format = static_cast<std::int64_t>(format);
        create.sampleCount = 1;
        create.width = width;
        create.height = height;
        create.faceCount = 1;
        create.arraySize = arraySize;
        create.mipCount = 1;
        if (XR_FAILED(::xrCreateSwapchain(session, &create, &swapchain.handle)))
            return false;

        std::uint32_t imageCount = 0;
        if (XR_FAILED(::xrEnumerateSwapchainImages(swapchain.handle, 0, &imageCount, nullptr)) || !imageCount)
        {
            swapchain.Destroy();
            return false;
        }
        swapchain.images.resize(imageCount);
        for (auto& image : swapchain.images)
            image = { XR_TYPE_SWAPCHAIN_IMAGE_D3D11_KHR };
        if (XR_FAILED(::xrEnumerateSwapchainImages(swapchain.handle, imageCount, &imageCount,
            reinterpret_cast<XrSwapchainImageBaseHeader*>(swapchain.images.data()))))
        {
            swapchain.Destroy();
            return false;
        }

        swapchain.rtvs.resize(imageCount);
        for (std::uint32_t i = 0; i < imageCount; ++i)
        {
            for (std::uint32_t slice = 0; slice < arraySize; ++slice)
            {
                D3D11_RENDER_TARGET_VIEW_DESC rd{};
                rd.Format = format;
                if (arraySize == 2)
                {
                    rd.ViewDimension = D3D11_RTV_DIMENSION_TEXTURE2DARRAY;
                    rd.Texture2DArray.MipSlice = 0;
                    rd.Texture2DArray.FirstArraySlice = slice;
                    rd.Texture2DArray.ArraySize = 1;
                }
                else
                {
                    rd.ViewDimension = D3D11_RTV_DIMENSION_TEXTURE2D;
                    rd.Texture2D.MipSlice = 0;
                }
                if (FAILED(OutRunVrFinalTest::Device->CreateRenderTargetView(swapchain.images[i].texture, &rd, &swapchain.rtvs[i][slice])))
                {
                    swapchain.Destroy();
                    return false;
                }
            }
        }

        swapchain.width = width;
        swapchain.height = height;
        swapchain.arraySize = arraySize;
        swapchain.format = format;
        return true;
    }

    inline bool RenderTo(ID3D11RenderTargetView* rtv, std::uint32_t width, std::uint32_t height, const UvRect& uv)
    {
        if (!rtv || !SourceSrv || !ConstantBuffer || !CreateShaders() || !OutRunVrFinalTest::Context)
            return false;

        D3D11_MAPPED_SUBRESOURCE mapped{};
        if (FAILED(OutRunVrFinalTest::Context->Map(ConstantBuffer, 0, D3D11_MAP_WRITE_DISCARD, 0, &mapped)))
            return false;
        auto* params = static_cast<BlitParams*>(mapped.pData);
        params->uvScale[0] = uv.w;
        params->uvScale[1] = uv.h;
        params->uvOffset[0] = uv.x;
        params->uvOffset[1] = uv.y;
        params->sdrWhiteScale = SdrWhiteScale;
        params->sourceIsScRgb = SourceFormat == DXGI_FORMAT_R16G16B16A16_FLOAT ? 1.f : 0.f;
        params->padding[0] = params->padding[1] = 0.f;
        OutRunVrFinalTest::Context->Unmap(ConstantBuffer, 0);

        D3D11_VIEWPORT viewport{};
        viewport.Width = static_cast<float>(width);
        viewport.Height = static_cast<float>(height);
        viewport.MaxDepth = 1.f;
        OutRunVrFinalTest::Context->RSSetViewports(1, &viewport);
        OutRunVrFinalTest::Context->OMSetRenderTargets(1, &rtv, nullptr);
        OutRunVrFinalTest::Context->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
        OutRunVrFinalTest::Context->VSSetShader(Vs, nullptr, 0);
        OutRunVrFinalTest::Context->PSSetShader(Ps, nullptr, 0);
        OutRunVrFinalTest::Context->PSSetShaderResources(0, 1, &SourceSrv);
        OutRunVrFinalTest::Context->PSSetSamplers(0, 1, &Sampler);
        OutRunVrFinalTest::Context->PSSetConstantBuffers(0, 1, &ConstantBuffer);
        OutRunVrFinalTest::Context->Draw(3, 0);
        ID3D11ShaderResourceView* nullSrv = nullptr;
        OutRunVrFinalTest::Context->PSSetShaderResources(0, 1, &nullSrv);
        ID3D11RenderTargetView* nullRtv = nullptr;
        OutRunVrFinalTest::Context->OMSetRenderTargets(1, &nullRtv, nullptr);
        return true;
    }

    inline bool Acquire(Swapchain& swapchain, std::uint32_t& image)
    {
        if (!swapchain.acquired)
        {
            XrSwapchainImageAcquireInfo acquire{ XR_TYPE_SWAPCHAIN_IMAGE_ACQUIRE_INFO };
            if (XR_FAILED(::xrAcquireSwapchainImage(
                    swapchain.handle, &acquire, &swapchain.acquiredImage)))
                return false;
            swapchain.acquired = true;
            swapchain.waited = false;
        }
        image = swapchain.acquiredImage;
        if (swapchain.waited)
            return true;

        XrSwapchainImageWaitInfo wait{ XR_TYPE_SWAPCHAIN_IMAGE_WAIT_INFO };
        wait.timeout = XR_INFINITE_DURATION;
        for (;;)
        {
            const XrResult result = ::xrWaitSwapchainImage(swapchain.handle, &wait);
            if (result == XR_TIMEOUT_EXPIRED)
                continue; // The same acquired image must be waited again; it cannot be released yet.
            if (XR_FAILED(result))
            {
                // Preserve acquiredImage. A later attempt must wait this oldest
                // acquired image again instead of violating acquire/wait order.
                return false;
            }
            swapchain.waited = true;
            return true;
        }
    }

    inline bool Release(Swapchain& swapchain)
    {
        if (!swapchain.acquired || !swapchain.waited)
            return false;
        XrSwapchainImageReleaseInfo release{ XR_TYPE_SWAPCHAIN_IMAGE_RELEASE_INFO };
        const XrResult result = ::xrReleaseSwapchainImage(swapchain.handle, &release);
        if (XR_SUCCEEDED(result))
        {
            swapchain.acquired = false;
            swapchain.waited = false;
            swapchain.acquiredImage = 0;
            return true;
        }
        return false;
    }

    inline bool FrameComplete(const OutRunVR::SharedRenderFrameState& frame)
    {
        constexpr std::uint32_t need = OutRunVR::RenderFrameStereoComplete |
            OutRunVR::RenderFrameWorldStereo | OutRunVR::RenderFrameDrawDuplicated |
            OutRunVR::RenderFrameEffectivePoseValid;
        return frame.state == OutRunVR::StereoSbsActive && frame.frameId && frame.sourcePoseSequence &&
            (frame.flags & OutRunVR::RenderFramePresentInFlight) == 0 && (frame.flags & need) == need;
    }

    inline void UpdateStereoFrameCache()
    {
        OutRunVR::SharedRenderFrameState frame{};
        std::uint32_t publish = 0;
        if (OutRunVrFinalTest::ReadLatestFrame(frame, publish) && FrameComplete(frame))
        {
            LastStereoFrame = frame;
            LastStereoFrameValid = true;
            LastStereoFrameMs = GetTickCount64();
        }
    }

    inline bool RenderProjectionOverride(XrSession session, const XrFrameEndInfo* endInfo,
        XrCompositionLayerProjection& projectionLayer,
        std::array<XrCompositionLayerProjectionView, 2>& views)
    {
        ++ProjectionAttempts;
        UpdateStereoFrameCache();
        if (!LastStereoFrameValid || GetTickCount64() - LastStereoFrameMs > 500)
            return false;
        if (!CaptureDesktop(8) || !HaveSource || !SourceSrv || !CreateShaders())
            return false;

        const XrCompositionLayerProjection* incoming = nullptr;
        if (endInfo && endInfo->layerCount > 0 && endInfo->layers && endInfo->layers[0] &&
            endInfo->layers[0]->type == XR_TYPE_COMPOSITION_LAYER_PROJECTION)
        {
            incoming = reinterpret_cast<const XrCompositionLayerProjection*>(endInfo->layers[0]);
            ++MainProjectionSeen;
        }

        std::uint32_t width = 1600;
        std::uint32_t height = 1600;
        if (incoming && incoming->viewCount >= 2 && incoming->views)
        {
            width = std::max(1, incoming->views[0].subImage.imageRect.extent.width);
            height = std::max(1, incoming->views[0].subImage.imageRect.extent.height);
        }
        if (!EnsureSwapchain(Projection, session, width, height, 2))
            return false;

        UvRect whole{};
        if (!GetGameUv(whole))
            return false;
        const UvRect eyeUv[2]{
            { whole.x, whole.y, whole.w * 0.5f, whole.h },
            { whole.x + whole.w * 0.5f, whole.y, whole.w * 0.5f, whole.h }
        };

        std::uint32_t image = 0;
        if (!Acquire(Projection, image))
            return false;
        if (image >= Projection.rtvs.size())
        {
            Release(Projection);
            return false;
        }
        bool ok = RenderTo(Projection.rtvs[image][0], Projection.width, Projection.height, eyeUv[0]);
        ok = RenderTo(Projection.rtvs[image][1], Projection.width, Projection.height, eyeUv[1]) && ok;
        Release(Projection);
        if (!ok)
            return false;

        for (int eye = 0; eye < 2; ++eye)
        {
            views[eye] = { XR_TYPE_COMPOSITION_LAYER_PROJECTION_VIEW };
            if (incoming && incoming->viewCount >= 2 && incoming->views)
            {
                views[eye].pose = incoming->views[eye].pose;
                views[eye].fov = incoming->views[eye].fov;
            }
            else
            {
                views[eye].pose.orientation = {
                    LastStereoFrame.eye[eye].orientation[0], LastStereoFrame.eye[eye].orientation[1],
                    LastStereoFrame.eye[eye].orientation[2], LastStereoFrame.eye[eye].orientation[3]
                };
                views[eye].pose.position = {
                    LastStereoFrame.eye[eye].position[0], LastStereoFrame.eye[eye].position[1],
                    LastStereoFrame.eye[eye].position[2]
                };
                views[eye].fov = {
                    LastStereoFrame.eye[eye].fov.angleLeft, LastStereoFrame.eye[eye].fov.angleRight,
                    LastStereoFrame.eye[eye].fov.angleUp, LastStereoFrame.eye[eye].fov.angleDown
                };
            }
            views[eye].subImage.swapchain = Projection.handle;
            views[eye].subImage.imageRect.offset = { 0, 0 };
            views[eye].subImage.imageRect.extent = {
                static_cast<std::int32_t>(Projection.width), static_cast<std::int32_t>(Projection.height)
            };
            views[eye].subImage.imageArrayIndex = eye;
        }

        projectionLayer = { XR_TYPE_COMPOSITION_LAYER_PROJECTION };
        projectionLayer.space = incoming && incoming->space != XR_NULL_HANDLE ? incoming->space : OutRunVrFinalTest::LocalSpace;
        projectionLayer.viewCount = 2;
        projectionLayer.views = views.data();
        ++ProjectionSuccess;
        if (!ProjectionLogged)
        {
            ProjectionLogged = true;
            std::cerr << "[R10] GAME projection override ACTIVE source=" << SourceWidth << "x" << SourceHeight
                      << " eyeSwapchain=" << Projection.width << "x" << Projection.height
                      << " uv=" << whole.x << "," << whole.y << "," << whole.w << "," << whole.h << "\n";
        }
        return true;
    }

    inline bool EnsureViewSpace(XrSession session)
    {
        if (ViewSpace != XR_NULL_HANDLE)
            return true;
        XrReferenceSpaceCreateInfo info{ XR_TYPE_REFERENCE_SPACE_CREATE_INFO };
        info.referenceSpaceType = XR_REFERENCE_SPACE_TYPE_VIEW;
        info.poseInReferenceSpace.orientation.w = 1.f;
        return XR_SUCCEEDED(OutRunVrFinalTest::CreateReferenceSpace(session, &info, &ViewSpace));
    }

    inline bool RenderTheaterOverride(XrSession session, XrCompositionLayerQuad& quad)
    {
        ++TheaterAttempts;
        if (!CaptureDesktop(0) || !HaveSource || !SourceSrv || !CreateShaders() || !EnsureViewSpace(session))
            return false;

        UvRect whole{};
        if (!GetGameUv(whole))
            return false;

        const std::uint32_t width = 1920;
        const std::uint32_t height = 1080;
        if (!EnsureSwapchain(Theater, session, width, height, 1))
            return false;
        std::uint32_t image = 0;
        if (!Acquire(Theater, image))
            return false;
        if (image >= Theater.rtvs.size())
        {
            Release(Theater);
            return false;
        }
        const bool ok = RenderTo(Theater.rtvs[image][0], Theater.width, Theater.height, whole);
        Release(Theater);
        if (!ok)
            return false;

        quad = { XR_TYPE_COMPOSITION_LAYER_QUAD };
        quad.space = ViewSpace;
        quad.eyeVisibility = XR_EYE_VISIBILITY_BOTH;
        quad.pose.orientation.w = 1.f;
        quad.pose.position.z = -1.5f;
        quad.subImage.swapchain = Theater.handle;
        quad.subImage.imageRect.offset = { 0, 0 };
        quad.subImage.imageRect.extent = { static_cast<std::int32_t>(Theater.width), static_cast<std::int32_t>(Theater.height) };
        quad.subImage.imageArrayIndex = 0;
        const float aspect = whole.h > 0.f ? (whole.w * SourceWidth) / (whole.h * SourceHeight) : (16.f / 9.f);
        quad.size.width = 2.f;
        quad.size.height = 2.f / std::max(0.5f, aspect);
        ++TheaterSuccess;
        if (!TheaterLogged)
        {
            TheaterLogged = true;
            std::cerr << "[R10] MENU theater override ACTIVE source=" << SourceWidth << "x" << SourceHeight
                      << " uv=" << whole.x << "," << whole.y << "," << whole.w << "," << whole.h << "\n";
        }
        return true;
    }

    inline void MaybeLogSummary()
    {
        const ULONGLONG now = GetTickCount64();
        if (now - LastSummaryMs < 5000)
            return;
        LastSummaryMs = now;
        std::cerr << "[R10] summary build=" << BuildId
                  << " end=" << EndFrames
                  << " capture[fresh=" << CaptureFresh << ",timeout=" << CaptureTimeout << ",fail=" << CaptureFailure << "]"
                  << " projection[try=" << ProjectionAttempts << ",ok=" << ProjectionSuccess << ",mainSeen=" << MainProjectionSeen << "]"
                  << " theater[try=" << TheaterAttempts << ",ok=" << TheaterSuccess << ",mainSeen=" << MainQuadSeen << "]"
                  << " source=" << SourceWidth << "x" << SourceHeight << " fmt=" << static_cast<int>(SourceFormat)
                  << " frame=" << (LastStereoFrameValid ? LastStereoFrame.frameId : 0) << "\n";
    }

    inline XrResult XRAPI_CALL EndFrame(XrSession session, const XrFrameEndInfo* endInfo)
    {
        ++EndFrames;
        if (!Enabled() || !endInfo || !OutRunVrFinalTest::Device || !OutRunVrFinalTest::Context)
            return OutRunVrFinalTest::EndFrame(session, endInfo);

        UpdateStereoFrameCache();
        const bool gameplay = LastStereoFrameValid && GetTickCount64() - LastStereoFrameMs <= 500;

        XrFrameEndInfo patched = *endInfo;
        const XrCompositionLayerBaseHeader* layerPtr = nullptr;
        XrCompositionLayerProjection projection{};
        std::array<XrCompositionLayerProjectionView, 2> views{};
        XrCompositionLayerQuad quad{};

        bool replaced = false;
        if (gameplay)
        {
            if (RenderProjectionOverride(session, endInfo, projection, views))
            {
                layerPtr = reinterpret_cast<const XrCompositionLayerBaseHeader*>(&projection);
                patched.layerCount = 1;
                patched.layers = &layerPtr;
                replaced = true;
            }
        }
        else
        {
            if (endInfo->layerCount > 0 && endInfo->layers && endInfo->layers[0] &&
                endInfo->layers[0]->type == XR_TYPE_COMPOSITION_LAYER_QUAD)
                ++MainQuadSeen;
            if (RenderTheaterOverride(session, quad))
            {
                layerPtr = reinterpret_cast<const XrCompositionLayerBaseHeader*>(&quad);
                patched.layerCount = 1;
                patched.layers = &layerPtr;
                replaced = true;
            }
        }

        MaybeLogSummary();
        return OutRunVrFinalTest::EndFrame(session, replaced ? &patched : endInfo);
    }

    inline XrResult XRAPI_CALL DestroySession(XrSession session)
    {
        ResetAll();
        return OutRunVrFinalTest::DestroySession(session);
    }
}

#define xrEndFrame OutRunVrSbsCaptureOverride::EndFrame
#define xrDestroySession OutRunVrSbsCaptureOverride::DestroySession
