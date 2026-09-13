// Compatibility / diagnostic compositor translation unit for OpenXR runtimes
// such as VDXR.
//
// Milestone 1.5 is intentionally a mono diagnostic mirror. It lets us verify
// the x86 pose/camera bridge in the headset before true per-eye D3D9 rendering
// is implemented.
//
// Important DXGI rule: IDXGIOutputDuplication::GetDesc().ModeDesc.Format is
// the DISPLAY MODE format, not the format of the duplicated desktop surface.
// The Desktop Duplication API guarantees that the acquired desktop image is
// DXGI_FORMAT_B8G8R8A8_UNORM. HDR displays can therefore report display mode
// format 10 (R16G16B16A16_FLOAT) while AcquireNextFrame returns format 87
// (B8G8R8A8_UNORM). Do not use ModeDesc.Format for capture textures/swapchains.

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
#include <dxgi1_2.h>
#include <openxr/openxr.h>
#include <openxr/openxr_platform.h>

#include <algorithm>
#include <array>
#include <cstdint>
#include <cwchar>
#include <iostream>
#include <string>
#include <vector>

namespace
{
    constexpr wchar_t GameExeName[] = L"OR2006C2C.EXE";
    constexpr DXGI_FORMAT DesktopDuplicationSurfaceFormat = DXGI_FORMAT_B8G8R8A8_UNORM;
    static_assert(DXGI_FORMAT_B8G8R8A8_UNORM == 87,
        "Unexpected Windows SDK value for DXGI_FORMAT_B8G8R8A8_UNORM");

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
        if (!pid)
            return nullptr;
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

    class MonoMirror
    {
    public:
        ~MonoMirror() { ResetAll(); }

        void OnSessionCreated(XrSession session, ID3D11Device* device, HWND hwnd)
        {
            ResetAll();
            session_ = session;
            hwnd_ = hwnd;
            device_ = device;
            if (device_)
            {
                device_->AddRef();
                device_->GetImmediateContext(&context_);
            }
        }

        void OnViewSpaceCreated(XrSpace space)
        {
            viewSpace_ = space;
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

            const HMONITOR targetMonitor = MonitorFromWindow(hwnd_, MONITOR_DEFAULTTONEAREST);

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
            {
                std::cerr << "VR mirror: failed to get DXGI adapter.\n";
                return false;
            }

            IDXGIOutput* selectedOutput = nullptr;
            DXGI_OUTPUT_DESC selectedDesc{};
            for (UINT i = 0;; ++i)
            {
                IDXGIOutput* output = nullptr;
                if (adapter->EnumOutputs(i, &output) == DXGI_ERROR_NOT_FOUND)
                    break;
                DXGI_OUTPUT_DESC desc{};
                output->GetDesc(&desc);
                if (desc.Monitor == targetMonitor)
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

            const HRESULT outputHr = selectedOutput->QueryInterface(
                __uuidof(IDXGIOutput1), reinterpret_cast<void**>(&output1_));
            selectedOutput->Release();
            if (FAILED(outputHr) || !output1_)
            {
                std::cerr << "VR mirror: IDXGIOutput1 is unavailable.\n";
                return false;
            }

            outputDesktop_ = selectedDesc.DesktopCoordinates;
            width_ = static_cast<std::uint32_t>(outputDesktop_.right - outputDesktop_.left);
            height_ = static_cast<std::uint32_t>(outputDesktop_.bottom - outputDesktop_.top);
            if (!width_ || !height_)
            {
                std::cerr << "VR mirror: selected monitor has an invalid desktop size.\n";
                return false;
            }

            // DuplicateOutput surfaces are always BGRA8. RecreateDuplication()
            // logs ModeDesc.Format separately only as display-mode diagnostics.
            captureFormat_ = DesktopDuplicationSurfaceFormat;
            if (!RecreateDuplication(true))
                return false;

            std::uint32_t formatCount = 0;
            XrResult xr = ::xrEnumerateSwapchainFormats(session_, 0, &formatCount, nullptr);
            if (XR_FAILED(xr) || !formatCount)
            {
                std::cerr << "VR mirror: xrEnumerateSwapchainFormats(count) failed: " << xr << "\n";
                return false;
            }
            std::vector<std::int64_t> formats(formatCount);
            xr = ::xrEnumerateSwapchainFormats(session_, formatCount, &formatCount, formats.data());
            if (XR_FAILED(xr))
            {
                std::cerr << "VR mirror: xrEnumerateSwapchainFormats(list) failed: " << xr << "\n";
                return false;
            }

            const std::int64_t wantedFormat = static_cast<std::int64_t>(captureFormat_);
            if (std::find(formats.begin(), formats.end(), wantedFormat) == formats.end())
            {
                std::cerr << "VR mirror: OpenXR runtime does not expose required BGRA8 swapchain format (87).\n"
                          << "VR mirror: runtime formats:";
                for (const auto format : formats)
                    std::cerr << " " << format;
                std::cerr << "\n";
                return false;
            }
            std::cout << "VR mirror: OpenXR BGRA8 swapchain support confirmed (format 87).\n";

            D3D11_TEXTURE2D_DESC captureDesc{};
            captureDesc.Width = width_;
            captureDesc.Height = height_;
            captureDesc.MipLevels = 1;
            captureDesc.ArraySize = 1;
            captureDesc.Format = captureFormat_;
            captureDesc.SampleDesc.Count = 1;
            captureDesc.Usage = D3D11_USAGE_DEFAULT;
            const HRESULT textureHr = device_->CreateTexture2D(&captureDesc, nullptr, &latestFrame_);
            if (FAILED(textureHr) || !latestFrame_)
            {
                std::cerr << "VR mirror: CreateTexture2D failed, HRESULT="
                          << static_cast<long>(textureHr) << "\n";
                return false;
            }

            XrSwapchainCreateInfo swapchainInfo{ XR_TYPE_SWAPCHAIN_CREATE_INFO };
            swapchainInfo.createFlags = 0;
            swapchainInfo.usageFlags = XR_SWAPCHAIN_USAGE_SAMPLED_BIT |
                                       XR_SWAPCHAIN_USAGE_COLOR_ATTACHMENT_BIT;
            swapchainInfo.format = wantedFormat;
            swapchainInfo.sampleCount = 1;
            swapchainInfo.width = width_;
            swapchainInfo.height = height_;
            swapchainInfo.faceCount = 1;
            swapchainInfo.arraySize = 1;
            swapchainInfo.mipCount = 1;
            xr = ::xrCreateSwapchain(session_, &swapchainInfo, &swapchain_);
            if (XR_FAILED(xr))
            {
                std::cerr << "VR mirror: xrCreateSwapchain failed: " << xr << "\n";
                return false;
            }

            std::uint32_t imageCount = 0;
            xr = ::xrEnumerateSwapchainImages(swapchain_, 0, &imageCount, nullptr);
            if (XR_FAILED(xr) || !imageCount)
            {
                std::cerr << "VR mirror: xrEnumerateSwapchainImages(count) failed: " << xr << "\n";
                return false;
            }
            images_.resize(imageCount);
            for (auto& image : images_)
                image = { XR_TYPE_SWAPCHAIN_IMAGE_D3D11_KHR };
            xr = ::xrEnumerateSwapchainImages(
                swapchain_, imageCount, &imageCount,
                reinterpret_cast<XrSwapchainImageBaseHeader*>(images_.data()));
            if (XR_FAILED(xr))
            {
                std::cerr << "VR mirror: xrEnumerateSwapchainImages(list) failed: " << xr << "\n";
                return false;
            }

            initialized_ = true;
            std::cout << "OpenXR mono mirror ready: " << width_ << "x" << height_
                      << " (Desktop Duplication surface format " << static_cast<int>(captureFormat_) << ").\n"
                      << "Mirror source is the whole game monitor and will auto-recover after display-mode changes.\n"
                      << "This is a temporary mono HMD view for head-tracking tests; true stereo is next.\n";

            // Not receiving a frame during the first second is not fatal. Keep
            // the OpenXR session alive and retry every xrEndFrame instead of
            // converting a transient timeout into a fake xrCreateSession error.
            CaptureDesktopFrame(1000);
            if (!haveFrame_)
                std::cout << "VR mirror: no desktop frame yet; continuing and retrying in the frame loop.\n";
            return true;
        }

        bool CaptureAndCopyToSwapchain()
        {
            if (!initialized_ && !Initialize())
                return false;
            CaptureDesktopFrame(haveFrame_ ? 0 : 1000);
            if (!haveFrame_ || swapchain_ == XR_NULL_HANDLE)
                return false;

            XrSwapchainImageAcquireInfo acquireInfo{ XR_TYPE_SWAPCHAIN_IMAGE_ACQUIRE_INFO };
            std::uint32_t imageIndex = 0;
            XrResult xr = ::xrAcquireSwapchainImage(swapchain_, &acquireInfo, &imageIndex);
            if (XR_FAILED(xr) || imageIndex >= images_.size())
            {
                std::cerr << "VR mirror: xrAcquireSwapchainImage failed: " << xr << "\n";
                return false;
            }

            XrSwapchainImageWaitInfo waitInfo{ XR_TYPE_SWAPCHAIN_IMAGE_WAIT_INFO };
            waitInfo.timeout = XR_INFINITE_DURATION;
            xr = ::xrWaitSwapchainImage(swapchain_, &waitInfo);
            if (XR_FAILED(xr))
            {
                std::cerr << "VR mirror: xrWaitSwapchainImage failed: " << xr << "\n";
                return false;
            }

            context_->CopyResource(images_[imageIndex].texture, latestFrame_);
            context_->Flush();

            XrSwapchainImageReleaseInfo releaseInfo{ XR_TYPE_SWAPCHAIN_IMAGE_RELEASE_INFO };
            xr = ::xrReleaseSwapchainImage(swapchain_, &releaseInfo);
            if (XR_FAILED(xr))
            {
                std::cerr << "VR mirror: xrReleaseSwapchainImage failed: " << xr << "\n";
                return false;
            }
            return true;
        }

        XrCompositionLayerQuad MakeQuad() const
        {
            XrCompositionLayerQuad quad{ XR_TYPE_COMPOSITION_LAYER_QUAD };
            quad.layerFlags = 0;
            quad.space = viewSpace_;
            quad.eyeVisibility = XR_EYE_VISIBILITY_BOTH;
            quad.subImage.swapchain = swapchain_;
            quad.subImage.imageRect.offset = { 0, 0 };
            quad.subImage.imageRect.extent = {
                static_cast<std::int32_t>(width_), static_cast<std::int32_t>(height_)
            };
            quad.subImage.imageArrayIndex = 0;
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
        bool RecreateDuplication(bool initial)
        {
            if (!output1_ || !device_)
                return false;

            const ULONGLONG now = GetTickCount64();
            if (!initial && lastDuplicationRetryMs_ != 0 && now - lastDuplicationRetryMs_ < 500)
                return false;
            lastDuplicationRetryMs_ = now;

            if (duplication_)
            {
                duplication_->Release();
                duplication_ = nullptr;
            }

            const HRESULT hr = output1_->DuplicateOutput(device_, &duplication_);
            if (FAILED(hr) || !duplication_)
            {
                if (initial || hr != lastDuplicationError_)
                {
                    std::cerr << "VR mirror: DuplicateOutput failed, HRESULT="
                              << static_cast<long>(hr)
                              << ". Will retry automatically.\n";
                    lastDuplicationError_ = hr;
                }
                return false;
            }

            DXGI_OUTPUT_DESC outputDesc{};
            output1_->GetDesc(&outputDesc);
            outputDesktop_ = outputDesc.DesktopCoordinates;

            DXGI_OUTDUPL_DESC duplicationDesc{};
            duplication_->GetDesc(&duplicationDesc);
            lastDisplayModeFormat_ = duplicationDesc.ModeDesc.Format;

            // ModeDesc.Format can be HDR/FP16 (for example value 10). The
            // actual duplicated desktop surface from DuplicateOutput is BGRA8.
            captureFormat_ = DesktopDuplicationSurfaceFormat;
            lastDuplicationError_ = S_OK;

            std::cout << "VR mirror: DXGI display mode format="
                      << static_cast<int>(lastDisplayModeFormat_)
                      << ", Desktop Duplication surface format="
                      << static_cast<int>(captureFormat_)
                      << " (BGRA8, fixed by API contract).\n";
            if (!initial)
                std::cout << "VR mirror: desktop duplication recovered after display-mode change.\n";
            return true;
        }

        bool CaptureDesktopFrame(DWORD timeoutMs)
        {
            if (!latestFrame_ || !IsWindow(hwnd_))
                return false;

            if (!duplication_ && !RecreateDuplication(false))
                return haveFrame_;

            DXGI_OUTDUPL_FRAME_INFO frameInfo{};
            IDXGIResource* desktopResource = nullptr;
            const HRESULT acquireHr = duplication_->AcquireNextFrame(timeoutMs, &frameInfo, &desktopResource);
            if (acquireHr == DXGI_ERROR_WAIT_TIMEOUT)
                return haveFrame_;
            if (FAILED(acquireHr) || !desktopResource)
            {
                if (acquireHr == DXGI_ERROR_ACCESS_LOST)
                {
                    std::cerr << "VR mirror: desktop duplication access was lost; rebuilding capture automatically.\n";
                    if (duplication_)
                    {
                        duplication_->Release();
                        duplication_ = nullptr;
                    }
                    RecreateDuplication(false);
                }
                else
                {
                    std::cerr << "VR mirror: AcquireNextFrame failed, HRESULT="
                              << static_cast<long>(acquireHr) << "\n";
                }
                return haveFrame_;
            }

            ID3D11Texture2D* desktopTexture = nullptr;
            const HRESULT textureHr = desktopResource->QueryInterface(
                __uuidof(ID3D11Texture2D), reinterpret_cast<void**>(&desktopTexture));
            desktopResource->Release();

            bool copied = false;
            if (SUCCEEDED(textureHr) && desktopTexture)
            {
                D3D11_TEXTURE2D_DESC desktopDesc{};
                desktopTexture->GetDesc(&desktopDesc);

                if (!firstFrameLogged_)
                {
                    std::cout << "VR mirror: first duplicated frame "
                              << desktopDesc.Width << "x" << desktopDesc.Height
                              << ", format=" << static_cast<int>(desktopDesc.Format) << ".\n";
                    firstFrameLogged_ = true;
                }

                if (desktopDesc.Format != DesktopDuplicationSurfaceFormat)
                {
                    std::cerr << "VR mirror: API-contract violation: acquired desktop surface format="
                              << static_cast<int>(desktopDesc.Format)
                              << ", expected BGRA8 format 87.\n";
                }
                else
                {
                    const UINT copyWidth = std::min<UINT>(width_, desktopDesc.Width);
                    const UINT copyHeight = std::min<UINT>(height_, desktopDesc.Height);
                    if (copyWidth && copyHeight)
                    {
                        D3D11_BOX sourceBox{};
                        sourceBox.left = 0;
                        sourceBox.top = 0;
                        sourceBox.front = 0;
                        sourceBox.right = copyWidth;
                        sourceBox.bottom = copyHeight;
                        sourceBox.back = 1;
                        context_->CopySubresourceRegion(
                            latestFrame_, 0, 0, 0, 0, desktopTexture, 0, &sourceBox);
                        context_->Flush();
                        copied = true;
                    }
                }
                desktopTexture->Release();
            }

            duplication_->ReleaseFrame();
            if (copied)
                haveFrame_ = true;
            return haveFrame_;
        }

        void ResetAll()
        {
            images_.clear();
            if (swapchain_ != XR_NULL_HANDLE)
            {
                ::xrDestroySwapchain(swapchain_);
                swapchain_ = XR_NULL_HANDLE;
            }
            if (latestFrame_)
            {
                latestFrame_->Release();
                latestFrame_ = nullptr;
            }
            if (duplication_)
            {
                duplication_->Release();
                duplication_ = nullptr;
            }
            if (output1_)
            {
                output1_->Release();
                output1_ = nullptr;
            }
            if (context_)
            {
                context_->Release();
                context_ = nullptr;
            }
            if (device_)
            {
                device_->Release();
                device_ = nullptr;
            }
            session_ = XR_NULL_HANDLE;
            viewSpace_ = XR_NULL_HANDLE;
            hwnd_ = nullptr;
            width_ = height_ = 0;
            captureFormat_ = DXGI_FORMAT_UNKNOWN;
            lastDisplayModeFormat_ = DXGI_FORMAT_UNKNOWN;
            outputDesktop_ = {};
            initialized_ = false;
            haveFrame_ = false;
            firstFrameLogged_ = false;
            lastDuplicationRetryMs_ = 0;
            lastDuplicationError_ = S_OK;
        }

        XrSession session_ = XR_NULL_HANDLE;
        XrSpace viewSpace_ = XR_NULL_HANDLE;
        ID3D11Device* device_ = nullptr;
        ID3D11DeviceContext* context_ = nullptr;
        HWND hwnd_ = nullptr;
        IDXGIOutput1* output1_ = nullptr;
        IDXGIOutputDuplication* duplication_ = nullptr;
        ID3D11Texture2D* latestFrame_ = nullptr;
        RECT outputDesktop_{};
        DXGI_FORMAT captureFormat_ = DXGI_FORMAT_UNKNOWN;
        DXGI_FORMAT lastDisplayModeFormat_ = DXGI_FORMAT_UNKNOWN;
        XrSwapchain swapchain_ = XR_NULL_HANDLE;
        std::vector<XrSwapchainImageD3D11KHR> images_;
        std::uint32_t width_ = 0;
        std::uint32_t height_ = 0;
        bool initialized_ = false;
        bool haveFrame_ = false;
        bool firstFrameLogged_ = false;
        ULONGLONG lastDuplicationRetryMs_ = 0;
        HRESULT lastDuplicationError_ = S_OK;
    };

    MonoMirror Mirror;

    static XrResult XRAPI_PTR OutRunRetryingXrGetSystem(
        XrInstance instance,
        const XrSystemGetInfo* getInfo,
        XrSystemId* systemId)
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

    static XrResult XRAPI_PTR OutRunMirrorXrCreateSession(
        XrInstance instance,
        const XrSessionCreateInfo* createInfo,
        XrSession* session)
    {
        // Creating/beginning an immersive OpenXR session makes VDXR leave its
        // desktop view. Wait until the actual game window exists so the user
        // can launch OutRun while still seeing Virtual Desktop.
        SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);
        const HWND gameWindow = WaitForGameWindow();

        ID3D11Device* d3dDevice = nullptr;
        for (auto* chain = reinterpret_cast<const XrBaseInStructure*>(createInfo->next);
             chain; chain = chain->next)
        {
            if (chain->type == XR_TYPE_GRAPHICS_BINDING_D3D11_KHR)
            {
                const auto* binding = reinterpret_cast<const XrGraphicsBindingD3D11KHR*>(chain);
                d3dDevice = binding->device;
                break;
            }
        }

        const XrResult result = ::xrCreateSession(instance, createInfo, session);
        if (XR_SUCCEEDED(result) && session && *session != XR_NULL_HANDLE)
        {
            Mirror.OnSessionCreated(*session, d3dDevice, gameWindow);
            if (!Mirror.Initialize())
            {
                std::cerr << "VR mirror initialization failed. Returning to Virtual Desktop.\n";
                Mirror.BeforeSessionDestroy(*session);
                ::xrDestroySession(*session);
                *session = XR_NULL_HANDLE;
                return XR_ERROR_RUNTIME_FAILURE;
            }
        }
        return result;
    }

    static XrResult XRAPI_PTR OutRunMirrorXrCreateReferenceSpace(
        XrSession session,
        const XrReferenceSpaceCreateInfo* createInfo,
        XrSpace* space)
    {
        const XrResult result = ::xrCreateReferenceSpace(session, createInfo, space);
        if (XR_SUCCEEDED(result) && createInfo && space &&
            createInfo->referenceSpaceType == XR_REFERENCE_SPACE_TYPE_VIEW)
        {
            Mirror.OnViewSpaceCreated(*space);
        }
        return result;
    }

    static XrResult XRAPI_PTR OutRunMirrorXrEndFrame(
        XrSession session,
        const XrFrameEndInfo* frameEndInfo)
    {
        if (!frameEndInfo || frameEndInfo->layerCount != 0 ||
            !Mirror.CaptureAndCopyToSwapchain() || !Mirror.ReadyForLayer())
        {
            return ::xrEndFrame(session, frameEndInfo);
        }

        XrCompositionLayerQuad quad = Mirror.MakeQuad();
        const XrCompositionLayerBaseHeader* layer =
            reinterpret_cast<const XrCompositionLayerBaseHeader*>(&quad);
        XrFrameEndInfo patched = *frameEndInfo;
        patched.layerCount = 1;
        patched.layers = &layer;
        return ::xrEndFrame(session, &patched);
    }

    static XrResult XRAPI_PTR OutRunMirrorXrDestroySession(XrSession session)
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
#define xrEndFrame OutRunMirrorXrEndFrame
#define xrDestroySession OutRunMirrorXrDestroySession
#include "main.cpp"
