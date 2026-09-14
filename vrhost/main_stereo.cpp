#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#define XR_USE_PLATFORM_WIN32
#define XR_USE_GRAPHICS_API_D3D11

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
#include <iostream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include "vr_shared.hpp"
#include "stereo_shader.hpp"

namespace
{
    constexpr wchar_t GameExeName[] = L"OR2006C2C.EXE";
    constexpr ULONGLONG StereoGraceMs = 250;
    constexpr std::size_t ViewHistorySize = 128;

    template <typename T>
    void ReleaseCom(T*& p)
    {
        if (p) { p->Release(); p = nullptr; }
    }

    void CheckXr(XrResult r, const char* what)
    {
        if (XR_FAILED(r))
            throw std::runtime_error(std::string(what) + " failed, XrResult=" + std::to_string(r));
    }

    void CheckHr(HRESULT r, const char* what)
    {
        if (FAILED(r))
            throw std::runtime_error(std::string(what) + " failed, HRESULT=" + std::to_string(static_cast<long>(r)));
    }

    bool HasExtension(const char* wanted)
    {
        std::uint32_t count = 0;
        CheckXr(xrEnumerateInstanceExtensionProperties(nullptr, 0, &count, nullptr),
            "xrEnumerateInstanceExtensionProperties(count)");
        std::vector<XrExtensionProperties> ext(count);
        for (auto& e : ext) e = { XR_TYPE_EXTENSION_PROPERTIES };
        CheckXr(xrEnumerateInstanceExtensionProperties(nullptr, count, &count, ext.data()),
            "xrEnumerateInstanceExtensionProperties(list)");
        for (const auto& e : ext)
            if (std::strcmp(e.extensionName, wanted) == 0) return true;
        return false;
    }

    struct WindowSearch
    {
        DWORD pid = 0;
        HWND best = nullptr;
        long long bestArea = 0;
    };

    BOOL CALLBACK EnumGameWindows(HWND hwnd, LPARAM param)
    {
        auto* s = reinterpret_cast<WindowSearch*>(param);
        DWORD pid = 0;
        GetWindowThreadProcessId(hwnd, &pid);
        if (pid != s->pid || !IsWindowVisible(hwnd)) return TRUE;
        RECT r{};
        if (!GetClientRect(hwnd, &r)) return TRUE;
        const long long w = r.right - r.left;
        const long long h = r.bottom - r.top;
        const long long area = w * h;
        if (w >= 320 && h >= 200 && area > s->bestArea)
        {
            s->best = hwnd;
            s->bestArea = area;
        }
        return TRUE;
    }

    DWORD FindGameProcess()
    {
        HANDLE snap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
        if (snap == INVALID_HANDLE_VALUE) return 0;
        PROCESSENTRY32W e{};
        e.dwSize = sizeof(e);
        DWORD pid = 0;
        if (Process32FirstW(snap, &e))
        {
            do
            {
                if (_wcsicmp(e.szExeFile, GameExeName) == 0)
                {
                    pid = e.th32ProcessID;
                    break;
                }
            } while (Process32NextW(snap, &e));
        }
        CloseHandle(snap);
        return pid;
    }

    HWND FindGameWindow(DWORD pid)
    {
        WindowSearch s{};
        s.pid = pid;
        EnumWindows(EnumGameWindows, reinterpret_cast<LPARAM>(&s));
        return s.best;
    }

    HWND WaitForGameWindow()
    {
        std::cout << "Waiting for OR2006C2C.EXE... Launch OutRun from the Virtual Desktop screen.\n";
        DWORD last = 0;
        for (;;)
        {
            const DWORD pid = FindGameProcess();
            if (pid && pid != last)
            {
                std::cout << "OutRun process detected (pid=" << pid << ").\n";
                last = pid;
            }
            if (pid)
            {
                if (HWND hwnd = FindGameWindow(pid))
                {
                    std::cout << "OutRun window detected. Starting true-stereo OpenXR host.\n";
                    return hwnd;
                }
            }
            Sleep(100);
        }
    }

    bool SameLuid(const LUID& a, const LUID& b)
    {
        return a.LowPart == b.LowPart && a.HighPart == b.HighPart;
    }

    IDXGIAdapter1* FindAdapter(const LUID& wanted)
    {
        IDXGIFactory1* f = nullptr;
        CheckHr(CreateDXGIFactory1(__uuidof(IDXGIFactory1), reinterpret_cast<void**>(&f)),
            "CreateDXGIFactory1");
        IDXGIAdapter1* match = nullptr;
        for (UINT i = 0;; ++i)
        {
            IDXGIAdapter1* a = nullptr;
            if (f->EnumAdapters1(i, &a) == DXGI_ERROR_NOT_FOUND) break;
            DXGI_ADAPTER_DESC1 d{};
            a->GetDesc1(&d);
            if (SameLuid(d.AdapterLuid, wanted))
            {
                match = a;
                break;
            }
            a->Release();
        }
        f->Release();
        if (!match) throw std::runtime_error("OpenXR D3D11 adapter not found");
        return match;
    }

    struct D3DObjects
    {
        ID3D11Device* device = nullptr;
        ID3D11DeviceContext* context = nullptr;
        D3DObjects() = default;
        D3DObjects(const D3DObjects&) = delete;
        D3DObjects& operator=(const D3DObjects&) = delete;
        D3DObjects(D3DObjects&& other) noexcept
            : device(std::exchange(other.device, nullptr)),
              context(std::exchange(other.context, nullptr)) {}
        D3DObjects& operator=(D3DObjects&& other) noexcept
        {
            if (this != &other)
            {
                ReleaseCom(context);
                ReleaseCom(device);
                device = std::exchange(other.device, nullptr);
                context = std::exchange(other.context, nullptr);
            }
            return *this;
        }
        ~D3DObjects()
        {
            ReleaseCom(context);
            ReleaseCom(device);
        }
    };

    D3DObjects CreateD3D11Device(const XrGraphicsRequirementsD3D11KHR& req)
    {
        IDXGIAdapter1* adapter = FindAdapter(req.adapterLuid);
        const std::array<D3D_FEATURE_LEVEL, 7> all{
            D3D_FEATURE_LEVEL_12_1, D3D_FEATURE_LEVEL_12_0,
            D3D_FEATURE_LEVEL_11_1, D3D_FEATURE_LEVEL_11_0,
            D3D_FEATURE_LEVEL_10_1, D3D_FEATURE_LEVEL_10_0,
            D3D_FEATURE_LEVEL_9_3
        };
        std::vector<D3D_FEATURE_LEVEL> levels;
        for (auto l : all) if (l >= req.minFeatureLevel) levels.push_back(l);
        if (levels.empty()) levels.push_back(req.minFeatureLevel);

        D3DObjects out;
        D3D_FEATURE_LEVEL selected{};
        const HRESULT hr = D3D11CreateDevice(adapter, D3D_DRIVER_TYPE_UNKNOWN, nullptr,
            D3D11_CREATE_DEVICE_BGRA_SUPPORT, levels.data(), static_cast<UINT>(levels.size()),
            D3D11_SDK_VERSION, &out.device, &selected, &out.context);
        adapter->Release();
        CheckHr(hr, "D3D11CreateDevice");
        return out;
    }

    XrVector3f RotateVector(const XrQuaternionf& q, const XrVector3f& v)
    {
        const XrVector3f u{ q.x, q.y, q.z };
        const XrVector3f t{
            2.f * (u.y * v.z - u.z * v.y),
            2.f * (u.z * v.x - u.x * v.z),
            2.f * (u.x * v.y - u.y * v.x)
        };
        return {
            v.x + q.w * t.x + (u.y * t.z - u.z * t.y),
            v.y + q.w * t.y + (u.z * t.x - u.x * t.z),
            v.z + q.w * t.z + (u.x * t.y - u.y * t.x)
        };
    }

    XrQuaternionf NormalizeQuaternion(XrQuaternionf q){const float l=q.x*q.x+q.y*q.y+q.z*q.z+q.w*q.w;if(!std::isfinite(l)||l<=1e-12f)return{0,0,0,1};const float i=1.0f/std::sqrt(l);q.x*=i;q.y*=i;q.z*=i;q.w*=i;return q;}
    XrQuaternionf ConjugateQuaternion(XrQuaternionf q){q=NormalizeQuaternion(q);return{-q.x,-q.y,-q.z,q.w};}
    XrQuaternionf MultiplyQuaternion(const XrQuaternionf&aIn,const XrQuaternionf&bIn){const auto a=NormalizeQuaternion(aIn),b=NormalizeQuaternion(bIn);return NormalizeQuaternion({a.w*b.x+a.x*b.w+a.y*b.z-a.z*b.y,a.w*b.y-a.x*b.z+a.y*b.w+a.z*b.x,a.w*b.z+a.x*b.y-a.y*b.x+a.z*b.w,a.w*b.w-a.x*b.x-a.y*b.y-a.z*b.z});}

    XrVector3f ToHeadLocal(const XrPosef& head, const XrVector3f& world)
    {
        XrVector3f delta{
            world.x - head.position.x,
            world.y - head.position.y,
            world.z - head.position.z
        };
        return RotateVector(ConjugateQuaternion(head.orientation),delta);
    }
    XrQuaternionf ToHeadLocalOrientation(const XrPosef& head,const XrPosef& eye){return MultiplyQuaternion(ConjugateQuaternion(head.orientation),eye.orientation);}

    std::uint32_t FloatBits(float v)
    {
        std::uint32_t b = 0;
        std::memcpy(&b, &v, sizeof(b));
        return b;
    }

    std::int16_t PackSnorm16(float value)
    {
        const float clamped = std::clamp(value, -1.0f, 1.0f);
        return static_cast<std::int16_t>(std::lround(clamped * 32767.0f));
    }

    void StorePackedEyeOrientations(char runtimeName[64], const XrQuaternionf eyeOrientation[2])
    {
        std::int16_t packed[8]{};
        for (int eye = 0; eye < 2; ++eye)
        {
            const XrQuaternionf q = NormalizeQuaternion(eyeOrientation[eye]);
            packed[eye * 4 + 0] = PackSnorm16(q.x);
            packed[eye * 4 + 1] = PackSnorm16(q.y);
            packed[eye * 4 + 2] = PackSnorm16(q.z);
            packed[eye * 4 + 3] = PackSnorm16(q.w);
        }
        static_assert(sizeof(packed) == OutRunVR::PackedEyeOrientationBytes);
        std::memcpy(runtimeName + OutRunVR::PackedEyeOrientationOffset, packed, sizeof(packed));
    }

    bool IsProcessAlive(DWORD pid)
    {
        if (!pid) return false;
        HANDLE p = OpenProcess(SYNCHRONIZE | PROCESS_QUERY_LIMITED_INFORMATION, FALSE, pid);
        if (!p) return false;
        const bool alive = WaitForSingleObject(p, 0) == WAIT_TIMEOUT;
        CloseHandle(p);
        return alive;
    }

    struct ClientStereoMeta
    {
        bool valid = false;
        std::uint32_t state = OutRunVR::StereoDisabled;
        std::uint32_t frame = 0;
        std::uint32_t poseSequence = 0;
        std::uint32_t presentQpcLow = 0;
    };

    class SharedWriter
    {
    public:
        SharedWriter()
        {
            mapping_ = CreateFileMappingW(INVALID_HANDLE_VALUE, nullptr, PAGE_READWRITE, 0,
                static_cast<DWORD>(sizeof(OutRunVR::SharedPoseState)), OutRunVR::SharedMemoryName);
            if (!mapping_) throw std::runtime_error("CreateFileMappingW failed");
            const bool existed = GetLastError() == ERROR_ALREADY_EXISTS;
            state_ = static_cast<OutRunVR::SharedPoseState*>(MapViewOfFile(mapping_, FILE_MAP_ALL_ACCESS,
                0, 0, sizeof(OutRunVR::SharedPoseState)));
            if (!state_) throw std::runtime_error("MapViewOfFile failed");
            if (!existed)
            {
                std::memset(state_, 0, sizeof(*state_));
                state_->protocolVersion = OutRunVR::SharedProtocolVersion;
                state_->structSize = sizeof(*state_);
                MemoryBarrier();
                state_->magic = OutRunVR::SharedMagic;
            }
            else
            {
                for (int i = 0; i < 200 && !HeaderValid(); ++i) Sleep(10);
                if (!HeaderValid()) throw std::runtime_error("existing VR shared mapping is not ready");
            }
            AcquireOwnership();
        }

        ~SharedWriter()
        {
            if (state_)
            {
                if (owns_ && state_->hostPid == GetCurrentProcessId())
                {
                    Begin();
                    state_->flags = 0;
                    state_->hostPid = 0;
                    End();
                }
                UnmapViewOfFile(state_);
            }
            if (mapping_) CloseHandle(mapping_);
        }

        void ReferenceSpaceChanged()
        {
            if (++referenceGeneration_ == 0) referenceGeneration_ = 1;
        }

        OutRunVR::ClientPresentationMode Presentation() const
        {
            if (!HeaderValid()) return OutRunVR::PresentationTheater;
            return state_->reserved[OutRunVR::ClientPresentationModeIndex] == OutRunVR::PresentationGameplay
                ? OutRunVR::PresentationGameplay : OutRunVR::PresentationTheater;
        }

        ClientStereoMeta ReadStereoMeta() const
        {
            ClientStereoMeta out{};
            if (!HeaderValid()) return out;
            for (int attempt = 0; attempt < 4; ++attempt)
            {
                const std::uint32_t before = state_->reserved[OutRunVR::ClientStereoFrameIndex];
                MemoryBarrier();
                out.state = state_->reserved[OutRunVR::ClientStereoStateIndex];
                out.poseSequence = state_->clientStereoPoseSequence;
                out.presentQpcLow = state_->reserved[OutRunVR::ClientStereoPresentQpcLowIndex];
                MemoryBarrier();
                const std::uint32_t after = state_->reserved[OutRunVR::ClientStereoFrameIndex];
                if (before == after)
                {
                    out.frame = after;
                    out.valid = true;
                    return out;
                }
            }
            return {};
        }

        std::uint32_t Write(const XrSpaceLocation& head,
            const std::array<XrView, 2>& views, std::uint32_t viewCount,
            const std::array<XrViewConfigurationView, 2>& configs,
            XrSessionState sessionState, XrViewStateFlags viewFlags,
            const char* runtime)
        {
            LARGE_INTEGER qpc{};
            QueryPerformanceCounter(&qpc);
            std::uint32_t flags = OutRunVR::HostAlive;
            if (head.locationFlags & XR_SPACE_LOCATION_ORIENTATION_VALID_BIT) flags |= OutRunVR::OrientationValid;
            if (head.locationFlags & XR_SPACE_LOCATION_POSITION_VALID_BIT) flags |= OutRunVR::PositionValid;
            if (sessionState == XR_SESSION_STATE_VISIBLE || sessionState == XR_SESSION_STATE_FOCUSED)
                flags |= OutRunVR::SessionVisible;
            if (sessionState == XR_SESSION_STATE_FOCUSED) flags |= OutRunVR::SessionFocused;

            const XrViewStateFlags required = XR_VIEW_STATE_ORIENTATION_VALID_BIT |
                XR_VIEW_STATE_POSITION_VALID_BIT;
            const bool stereoValid = viewCount >= 2 && (viewFlags & required) == required &&
                (head.locationFlags & (XR_SPACE_LOCATION_ORIENTATION_VALID_BIT |
                    XR_SPACE_LOCATION_POSITION_VALID_BIT)) ==
                (XR_SPACE_LOCATION_ORIENTATION_VALID_BIT | XR_SPACE_LOCATION_POSITION_VALID_BIT);
            if(stereoValid)flags|=OutRunVR::StereoViewsValid|OutRunVR::StereoEyeOrientationValid;

            Begin();
            state_->hostPid = GetCurrentProcessId();
            state_->flags = flags;
            ++state_->heartbeat;
            state_->sampleQpc = qpc.QuadPart;
            state_->orientation[0] = head.pose.orientation.x;
            state_->orientation[1] = head.pose.orientation.y;
            state_->orientation[2] = head.pose.orientation.z;
            state_->orientation[3] = head.pose.orientation.w;
            state_->position[0] = head.pose.position.x;
            state_->position[1] = head.pose.position.y;
            state_->position[2] = head.pose.position.z;
            state_->reserved[OutRunVR::HostReferenceSpaceGenerationIndex] = referenceGeneration_;
            for (std::uint32_t eye = 0; eye < 2; ++eye)
            {
                state_->recommendedWidth[eye] = configs[eye].recommendedImageRectWidth;
                state_->recommendedHeight[eye] = configs[eye].recommendedImageRectHeight;
                if (eye < viewCount)
                {
                    state_->eyeFov[eye] = {
                        views[eye].fov.angleLeft, views[eye].fov.angleRight,
                        views[eye].fov.angleUp, views[eye].fov.angleDown
                    };
                }
            }

            std::memset(state_->runtimeName, 0, sizeof(state_->runtimeName));
            strncpy_s(state_->runtimeName, OutRunVR::PackedEyeOrientationOffset,
                runtime ? runtime : "unknown", _TRUNCATE);
            if (stereoValid)
            {
                const XrVector3f left = ToHeadLocal(head.pose, views[0].pose.position);
                const XrVector3f right = ToHeadLocal(head.pose, views[1].pose.position);
                const XrQuaternionf eyeOrientation[2]{
                    ToHeadLocalOrientation(head.pose, views[0].pose),
                    ToHeadLocalOrientation(head.pose, views[1].pose)
                };
                StorePackedEyeOrientations(state_->runtimeName, eyeOrientation);
                state_->reserved[OutRunVR::HostEyeOffsetLeftXIndex] = FloatBits(left.x);
                state_->reserved[OutRunVR::HostEyeOffsetLeftYIndex] = FloatBits(left.y);
                state_->reserved[OutRunVR::HostEyeOffsetLeftZIndex] = FloatBits(left.z);
                state_->reserved[OutRunVR::HostEyeOffsetRightXIndex] = FloatBits(right.x);
                state_->reserved[OutRunVR::HostEyeOffsetRightYIndex] = FloatBits(right.y);
                state_->reserved[OutRunVR::HostEyeOffsetRightZIndex] = FloatBits(right.z);
            }
            return End();
        }

    private:
        bool HeaderValid() const
        {
            return state_ && state_->magic == OutRunVR::SharedMagic &&
                state_->protocolVersion == OutRunVR::SharedProtocolVersion &&
                state_->structSize == sizeof(*state_);
        }

        void AcquireOwnership()
        {
            const LONG self = static_cast<LONG>(GetCurrentProcessId());
            for (int i = 0; i < 100; ++i)
            {
                const LONG observed = static_cast<LONG>(state_->hostPid);
                if (observed == self) { owns_ = true; return; }
                if (observed != 0 && IsProcessAlive(static_cast<DWORD>(observed)))
                    throw std::runtime_error("another outrun-vr-host already owns the bridge");
                if (InterlockedCompareExchange(reinterpret_cast<volatile LONG*>(&state_->hostPid),
                    self, observed) == observed)
                {
                    owns_ = true;
                    return;
                }
                Sleep(1);
            }
            throw std::runtime_error("failed to acquire host ownership");
        }

        void Begin()
        {
            LONG s = InterlockedIncrement(reinterpret_cast<volatile LONG*>(&state_->sequence));
            if ((s & 1) == 0)
                InterlockedIncrement(reinterpret_cast<volatile LONG*>(&state_->sequence));
            MemoryBarrier();
        }

        std::uint32_t End()
        {
            MemoryBarrier();
            LONG s = InterlockedIncrement(reinterpret_cast<volatile LONG*>(&state_->sequence));
            if (s & 1)
                s = InterlockedIncrement(reinterpret_cast<volatile LONG*>(&state_->sequence));
            return static_cast<std::uint32_t>(s);
        }

        HANDLE mapping_ = nullptr;
        OutRunVR::SharedPoseState* state_ = nullptr;
        bool owns_ = false;
        std::uint32_t referenceGeneration_ = 1;
    };

    class RenderFrameReader
    {
    public:
        RenderFrameReader(){mapping_=CreateFileMappingW(INVALID_HANDLE_VALUE,nullptr,PAGE_READWRITE,0,static_cast<DWORD>(sizeof(OutRunVR::SharedRenderFrameState)),OutRunVR::RenderFrameMemoryName);if(!mapping_)throw std::runtime_error("CreateFileMappingW Frame.v1 failed");const bool existed=GetLastError()==ERROR_ALREADY_EXISTS;state_=static_cast<OutRunVR::SharedRenderFrameState*>(MapViewOfFile(mapping_,FILE_MAP_ALL_ACCESS,0,0,sizeof(OutRunVR::SharedRenderFrameState)));if(!state_)throw std::runtime_error("MapViewOfFile Frame.v1 failed");if(!existed){std::memset(state_,0,sizeof(*state_));state_->protocolVersion=OutRunVR::RenderFrameProtocolVersion;state_->structSize=sizeof(*state_);MemoryBarrier();state_->magic=OutRunVR::RenderFrameMagic;}}
        ~RenderFrameReader(){if(state_)UnmapViewOfFile(state_);if(mapping_)CloseHandle(mapping_);}
        bool Read(OutRunVR::SharedRenderFrameState&out)const{if(!state_||state_->magic!=OutRunVR::RenderFrameMagic||state_->protocolVersion!=OutRunVR::RenderFrameProtocolVersion||state_->structSize!=sizeof(*state_))return false;for(int a=0;a<4;++a){const auto b=state_->sequence;if(b&1u)continue;MemoryBarrier();std::memcpy(&out,state_,sizeof(out));MemoryBarrier();const auto e=state_->sequence;if(b==e&&!(e&1u)&&out.magic==OutRunVR::RenderFrameMagic&&out.protocolVersion==OutRunVR::RenderFrameProtocolVersion&&out.structSize==sizeof(out))return true;}return false;}
    private: HANDLE mapping_=nullptr;OutRunVR::SharedRenderFrameState*state_=nullptr;
    };

    struct ViewHistoryEntry
    {
        bool valid = false;
        std::uint32_t sequence = 0;
        std::array<XrView, 2> views{};
    };

    class ViewHistory
    {
    public:
        void Clear()
        {
            for (auto& e : entries_) e = {};
            cursor_ = 0;
        }

        void Store(std::uint32_t sequence, const std::array<XrView, 2>& views)
        {
            if (!sequence) return;
            auto& e = entries_[cursor_++ % entries_.size()];
            e.valid = true;
            e.sequence = sequence;
            e.views = views;
        }

        bool Find(std::uint32_t sequence, std::array<XrView, 2>& views) const
        {
            if (!sequence) return false;
            for (const auto& e : entries_)
            {
                if (e.valid && e.sequence == sequence)
                {
                    views = e.views;
                    return true;
                }
            }
            return false;
        }

    private:
        std::array<ViewHistoryEntry, ViewHistorySize> entries_{};
        std::size_t cursor_ = 0;
    };

    float QuerySdrWhiteScale(HMONITOR monitor)
    {
        char value[64]{};
        const DWORD n = GetEnvironmentVariableA("OUTRUN_VR_SDR_WHITE_SCALE", value, sizeof(value));
        if (n > 0 && n < sizeof(value))
        {
            char* end = nullptr;
            const float v = std::strtof(value, &end);
            if (end != value && std::isfinite(v) && v >= 0.25f && v <= 8.f) return v;
        }

        MONITORINFOEXW mi{};
        mi.cbSize = sizeof(mi);
        if (!monitor || !GetMonitorInfoW(monitor, &mi)) return 1.f;
        UINT32 pc = 0, mc = 0;
        if (GetDisplayConfigBufferSizes(QDC_ONLY_ACTIVE_PATHS, &pc, &mc) != ERROR_SUCCESS) return 1.f;
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
                _wcsicmp(src.viewGdiDeviceName, mi.szDevice) != 0) continue;

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

    ID3DBlob* CompileShader(const char* entry, const char* target)
    {
        ID3DBlob* code = nullptr;
        ID3DBlob* errors = nullptr;
        const HRESULT hr = D3DCompile(OutRunStereoBlitShader, std::strlen(OutRunStereoBlitShader),
            "OutRunStereoBlit", nullptr, nullptr, entry, target,
            D3DCOMPILE_ENABLE_STRICTNESS | D3DCOMPILE_OPTIMIZATION_LEVEL3,
            0, &code, &errors);
        if (FAILED(hr))
        {
            std::string m = "D3DCompile failed";
            if (errors && errors->GetBufferPointer())
                m += std::string(": ") + static_cast<const char*>(errors->GetBufferPointer());
            ReleaseCom(errors);
            ReleaseCom(code);
            throw std::runtime_error(m);
        }
        ReleaseCom(errors);
        return code;
    }

    struct UvRect { float x = 0, y = 0, w = 1, h = 1; };
    struct BlitParams
    {
        float uvScale[2];
        float uvOffset[2];
        float sdrWhiteScale;
        float sourceIsScRgb;
        float padding[2];
    };

    struct SwapchainSet
    {
        XrSwapchain handle = XR_NULL_HANDLE;
        std::uint32_t width = 0, height = 0, arraySize = 1;
        DXGI_FORMAT format = DXGI_FORMAT_UNKNOWN;
        std::vector<XrSwapchainImageD3D11KHR> images;
        std::vector<std::array<ID3D11RenderTargetView*, 2>> rtvs;

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
                xrDestroySwapchain(handle);
                handle = XR_NULL_HANDLE;
            }
        }

        ~SwapchainSet() { Destroy(); }
    };

    struct CaptureStatus{bool available=false;bool fresh=false;std::int64_t lastPresentQpc=0;std::uint32_t lastPresentQpcLow=0;};

    class StereoCompositor
    {
    public:
        StereoCompositor(XrSession session, ID3D11Device* device, ID3D11DeviceContext* context,
            HWND hwnd, const std::array<XrViewConfigurationView, 2>& configs)
            : session_(session), device_(device), context_(context), hwnd_(hwnd), configs_(configs)
        {
            device_->AddRef();
            context_->AddRef();
            GetWindowThreadProcessId(hwnd_, &gamePid_);
            gameProcess_ = OpenProcess(SYNCHRONIZE | PROCESS_QUERY_LIMITED_INFORMATION, FALSE, gamePid_);
        }

        ~StereoCompositor()
        {
            Reset();
            ReleaseCom(context_);
            ReleaseCom(device_);
            if (gameProcess_) CloseHandle(gameProcess_);
        }

        bool GameAlive() const
        {
            return gameProcess_ ? WaitForSingleObject(gameProcess_, 0) == WAIT_TIMEOUT : IsWindow(hwnd_) != FALSE;
        }

        void ReferenceSpaceChanged()
        {
            theaterAnchorValid_ = false;
            stereoSourceValid_ = false;
        }

        void Shutdown()
        {
            Reset();
            session_ = XR_NULL_HANDLE;
        }

        bool Initialize()
        {
            if(!BindCaptureOutput(true))throw std::runtime_error("failed to bind game capture output");
            CreateShaders();
            ChooseSwapchainFormat();
            CreateProjectionSwapchain();
            CreateTheaterSwapchain();
            std::cout << "OpenXR true stereo ready: projection " << projection_.width << "x" << projection_.height << "x2; theater " << theater_.width << "x" << theater_.height << ".\n";
            return true;
        }

        CaptureStatus Capture(DWORD timeoutMs=0)
        {
            if(!IsWindow(hwnd_)){if(HWND replacement=FindGameWindow(gamePid_))hwnd_=replacement;}
            const HMONITOR monitorNow=IsWindow(hwnd_)?MonitorFromWindow(hwnd_,MONITOR_DEFAULTTONEAREST):nullptr;if(!duplication_||(monitorNow&&monitorNow!=targetMonitor_))BindCaptureOutput(false);
            CaptureStatus status{haveFrame_,false,lastCapturePresentQpc_,lastCapturePresentQpcLow_};
            if (!duplication_ && !RecreateDuplication(false)) return status;

            DXGI_OUTDUPL_FRAME_INFO fi{};
            IDXGIResource* res = nullptr;
            if(!duplication_)return status;const DWORD waitMs=haveFrame_?timeoutMs:std::max<DWORD>(timeoutMs,1000);const HRESULT hr=duplication_->AcquireNextFrame(waitMs,&fi,&res);
            if (hr == DXGI_ERROR_WAIT_TIMEOUT) return status;
            if (FAILED(hr) || !res)
            {
                if (hr == DXGI_ERROR_ACCESS_LOST)
                {
                    haveFrame_=false;stereoSourceValid_=false;BindCaptureOutput(false);
                }
                return {haveFrame_,false,lastCapturePresentQpc_,lastCapturePresentQpcLow_};
            }

            ID3D11Texture2D* tex = nullptr;
            const HRESULT q = res->QueryInterface(__uuidof(ID3D11Texture2D), reinterpret_cast<void**>(&tex));
            res->Release();
            bool copied = false;
            if (SUCCEEDED(q) && tex)
            {
                D3D11_TEXTURE2D_DESC d{};
                tex->GetDesc(&d);
                if ((d.Format == DXGI_FORMAT_B8G8R8A8_UNORM ||
                     d.Format == DXGI_FORMAT_R16G16B16A16_FLOAT) && EnsureSource(d))
                {
                    context_->CopyResource(source_, tex);
                    copied = true;
                }
                tex->Release();
            }
            duplication_->ReleaseFrame();

            if (copied)
            {
                haveFrame_ = true;
                if(fi.LastPresentTime.QuadPart!=0){lastCapturePresentQpc_=fi.LastPresentTime.QuadPart;lastCapturePresentQpcLow_=static_cast<std::uint32_t>(fi.LastPresentTime.QuadPart);}
                status.available=true;status.fresh=fi.AccumulatedFrames>0;status.lastPresentQpc=lastCapturePresentQpc_;status.lastPresentQpcLow=lastCapturePresentQpcLow_;
            }
            return status;
        }

        bool CommitStereoSource()
        {
            if (!source_ || !sourceSrv_ || !sourceWidth_ || !sourceHeight_) return false;
            if (!stereoSource_ || stereoSourceWidth_ != sourceWidth_ ||
                stereoSourceHeight_ != sourceHeight_ || stereoSourceFormat_ != sourceFormat_)
            {
                ReleaseCom(stereoSourceSrv_);
                ReleaseCom(stereoSource_);
                D3D11_TEXTURE2D_DESC desc{};
                desc.Width = sourceWidth_;
                desc.Height = sourceHeight_;
                desc.MipLevels = 1;
                desc.ArraySize = 1;
                desc.Format = sourceFormat_;
                desc.SampleDesc.Count = 1;
                desc.Usage = D3D11_USAGE_DEFAULT;
                desc.BindFlags = D3D11_BIND_SHADER_RESOURCE;
                if (FAILED(device_->CreateTexture2D(&desc, nullptr, &stereoSource_))) return false;
                D3D11_SHADER_RESOURCE_VIEW_DESC view{};
                view.Format = desc.Format;
                view.ViewDimension = D3D11_SRV_DIMENSION_TEXTURE2D;
                view.Texture2D.MipLevels = 1;
                if (FAILED(device_->CreateShaderResourceView(stereoSource_, &view, &stereoSourceSrv_)))
                {
                    ReleaseCom(stereoSource_);
                    return false;
                }
                stereoSourceWidth_ = sourceWidth_;
                stereoSourceHeight_ = sourceHeight_;
                stereoSourceFormat_ = sourceFormat_;
            }
            context_->CopyResource(stereoSource_, source_);
            stereoSourceValid_ = true;
            return true;
        }

        bool HasStereoSource() const { return stereoSourceValid_ && stereoSourceSrv_; }

        bool RenderProjection(const std::array<XrView, 2>& views,
            std::array<XrCompositionLayerProjectionView, 2>& pv)
        {
            if (!HasStereoSource()) return false;
            UvRect whole{};
            if (!GetGameUv(whole)) return false;
            UvRect eyes[2]{
                { whole.x, whole.y, whole.w * 0.5f, whole.h },
                { whole.x + whole.w * 0.5f, whole.y, whole.w * 0.5f, whole.h }
            };

            std::uint32_t image = 0;
            Acquire(projection_, image);
            bool ok = RenderTo(projection_.rtvs[image][0], projection_.width, projection_.height,
                eyes[0], stereoSourceSrv_, stereoSourceFormat_);
            ok = RenderTo(projection_.rtvs[image][1], projection_.width, projection_.height,
                eyes[1], stereoSourceSrv_, stereoSourceFormat_) && ok;
            Release(projection_);
            if (!ok) return false;

            for (int eye = 0; eye < 2; ++eye)
            {
                pv[eye] = { XR_TYPE_COMPOSITION_LAYER_PROJECTION_VIEW };
                pv[eye].pose = views[eye].pose;
                pv[eye].fov = views[eye].fov;
                pv[eye].subImage.swapchain = projection_.handle;
                pv[eye].subImage.imageRect.offset = { 0, 0 };
                pv[eye].subImage.imageRect.extent = {
                    static_cast<int32_t>(projection_.width),
                    static_cast<int32_t>(projection_.height)
                };
                pv[eye].subImage.imageArrayIndex=eye;
            }
            return true;
        }

        bool RenderTheater(XrSpace viewSpace, XrSpace localSpace, XrTime displayTime,
            XrCompositionLayerQuad& quad)
        {
            if (!haveFrame_ || !sourceSrv_) return false;
            UvRect whole{};
            if (!GetGameUv(whole)) return false;
            std::uint32_t image = 0;
            Acquire(theater_, image);
            const bool ok = RenderTo(theater_.rtvs[image][0], theater_.width, theater_.height,
                whole, sourceSrv_, sourceFormat_);
            Release(theater_);
            if (!ok || !EnsureTheaterAnchor(viewSpace, localSpace, displayTime)) return false;

            quad = { XR_TYPE_COMPOSITION_LAYER_QUAD };
            quad.space = localSpace;
            quad.eyeVisibility = XR_EYE_VISIBILITY_BOTH;
            quad.pose = theaterAnchor_;
            quad.subImage.swapchain = theater_.handle;
            quad.subImage.imageRect.offset = { 0, 0 };
            quad.subImage.imageRect.extent = {
                static_cast<int32_t>(theater_.width),
                static_cast<int32_t>(theater_.height)
            };
            RECT cr{};
            GetClientRect(hwnd_, &cr);
            const float aspect = (cr.bottom > cr.top)
                ? static_cast<float>(cr.right - cr.left) / static_cast<float>(cr.bottom - cr.top)
                : 16.f / 9.f;
            quad.size.width = 2.f;
            quad.size.height = 2.f / aspect;
            return true;
        }

    private:
        void Reset()
        {
            projection_.Destroy();
            theater_.Destroy();
            ReleaseCom(stereoSourceSrv_);
            ReleaseCom(stereoSource_);
            ReleaseCom(sourceSrv_);
            ReleaseCom(source_);
            ReleaseCom(constantBuffer_);
            ReleaseCom(sampler_);
            ReleaseCom(ps_);
            ReleaseCom(vs_);
            ReleaseCom(duplication_);
            ReleaseCom(output5_);
            ReleaseCom(output1_);
            haveFrame_ = false;
            stereoSourceValid_ = false;
        }

        void ChooseSwapchainFormat()
        {
            std::uint32_t count = 0;
            CheckXr(xrEnumerateSwapchainFormats(session_, 0, &count, nullptr),
                "xrEnumerateSwapchainFormats(count)");
            std::vector<int64_t> formats(count);
            CheckXr(xrEnumerateSwapchainFormats(session_, count, &count, formats.data()),
                "xrEnumerateSwapchainFormats(list)");
            const DXGI_FORMAT pref[]{
                DXGI_FORMAT_R8G8B8A8_UNORM_SRGB,
                DXGI_FORMAT_B8G8R8A8_UNORM_SRGB,
                DXGI_FORMAT_R8G8B8A8_UNORM,
                DXGI_FORMAT_B8G8R8A8_UNORM
            };
            for (auto p : pref)
            {
                if (std::find(formats.begin(), formats.end(), static_cast<int64_t>(p)) != formats.end())
                {
                    swapFormat_ = p;
                    return;
                }
            }
            throw std::runtime_error("runtime has no supported 8-bit color swapchain");
        }

        void CreateProjectionSwapchain()
        {
            projection_.width = std::max(configs_[0].recommendedImageRectWidth,
                configs_[1].recommendedImageRectWidth);
            projection_.height = std::max(configs_[0].recommendedImageRectHeight,
                configs_[1].recommendedImageRectHeight);
            projection_.arraySize=2;
            projection_.format = swapFormat_;
            CreateSwapchain(projection_);
        }

        void CreateTheaterSwapchain()
        {
            theater_.width = std::max(configs_[0].recommendedImageRectWidth,
                configs_[1].recommendedImageRectWidth);
            theater_.height = std::max(configs_[0].recommendedImageRectHeight,
                configs_[1].recommendedImageRectHeight);
            theater_.arraySize = 1;
            theater_.format = swapFormat_;
            CreateSwapchain(theater_);
        }

        void CreateSwapchain(SwapchainSet& s)
        {
            XrSwapchainCreateInfo ci{ XR_TYPE_SWAPCHAIN_CREATE_INFO };
            ci.usageFlags = XR_SWAPCHAIN_USAGE_COLOR_ATTACHMENT_BIT | XR_SWAPCHAIN_USAGE_SAMPLED_BIT;
            ci.format = static_cast<int64_t>(s.format);
            ci.sampleCount = 1;
            ci.width = s.width;
            ci.height = s.height;
            ci.faceCount = 1;
            ci.arraySize = s.arraySize;
            ci.mipCount = 1;
            CheckXr(xrCreateSwapchain(session_, &ci, &s.handle), "xrCreateSwapchain");

            std::uint32_t n = 0;
            CheckXr(xrEnumerateSwapchainImages(s.handle, 0, &n, nullptr),
                "xrEnumerateSwapchainImages(count)");
            s.images.resize(n);
            for (auto& i : s.images) i = { XR_TYPE_SWAPCHAIN_IMAGE_D3D11_KHR };
            CheckXr(xrEnumerateSwapchainImages(s.handle, n, &n,
                reinterpret_cast<XrSwapchainImageBaseHeader*>(s.images.data())),
                "xrEnumerateSwapchainImages(list)");
            s.rtvs.resize(n);
            for (std::uint32_t i = 0; i < n; ++i)
            {
                for (std::uint32_t slice = 0; slice < s.arraySize; ++slice)
                {
                    D3D11_RENDER_TARGET_VIEW_DESC rd{};
                    rd.Format = s.format;
                    if (s.arraySize > 1)
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
                    CheckHr(device_->CreateRenderTargetView(s.images[i].texture, &rd, &s.rtvs[i][slice]),
                        "CreateRenderTargetView");
                }
            }
        }

        void Acquire(SwapchainSet& s, std::uint32_t& image)
        {
            XrSwapchainImageAcquireInfo ai{ XR_TYPE_SWAPCHAIN_IMAGE_ACQUIRE_INFO };
            CheckXr(xrAcquireSwapchainImage(s.handle, &ai, &image), "xrAcquireSwapchainImage");
            XrSwapchainImageWaitInfo wi{ XR_TYPE_SWAPCHAIN_IMAGE_WAIT_INFO };
            wi.timeout = XR_INFINITE_DURATION;
            CheckXr(xrWaitSwapchainImage(s.handle, &wi), "xrWaitSwapchainImage");
        }

        void Release(SwapchainSet& s)
        {
            XrSwapchainImageReleaseInfo ri{ XR_TYPE_SWAPCHAIN_IMAGE_RELEASE_INFO };
            CheckXr(xrReleaseSwapchainImage(s.handle, &ri), "xrReleaseSwapchainImage");
        }

        void CreateShaders()
        {
            ID3DBlob* v = CompileShader("VSMain", "vs_5_0");
            ID3DBlob* p = CompileShader("PSMain", "ps_5_0");
            CheckHr(device_->CreateVertexShader(v->GetBufferPointer(), v->GetBufferSize(), nullptr, &vs_),
                "CreateVertexShader");
            CheckHr(device_->CreatePixelShader(p->GetBufferPointer(), p->GetBufferSize(), nullptr, &ps_),
                "CreatePixelShader");
            v->Release();
            p->Release();

            D3D11_SAMPLER_DESC sd{};
            sd.Filter = D3D11_FILTER_MIN_MAG_MIP_LINEAR;
            sd.AddressU = sd.AddressV = sd.AddressW = D3D11_TEXTURE_ADDRESS_CLAMP;
            CheckHr(device_->CreateSamplerState(&sd, &sampler_), "CreateSamplerState");

            D3D11_BUFFER_DESC bd{};
            bd.ByteWidth = sizeof(BlitParams);
            bd.Usage = D3D11_USAGE_DYNAMIC;
            bd.BindFlags = D3D11_BIND_CONSTANT_BUFFER;
            bd.CPUAccessFlags = D3D11_CPU_ACCESS_WRITE;
            CheckHr(device_->CreateBuffer(&bd, nullptr, &constantBuffer_), "CreateBuffer");
        }

        bool BindCaptureOutput(bool initial)
        {
            if(HWND replacement=FindGameWindow(gamePid_))hwnd_=replacement;if(!IsWindow(hwnd_))return false;targetMonitor_=MonitorFromWindow(hwnd_,MONITOR_DEFAULTTONEAREST);if(!targetMonitor_)return false;ReleaseCom(duplication_);ReleaseCom(output5_);ReleaseCom(output1_);
            IDXGIDevice*dxgi=nullptr;if(FAILED(device_->QueryInterface(__uuidof(IDXGIDevice),reinterpret_cast<void**>(&dxgi)))||!dxgi)return false;IDXGIAdapter*adapter=nullptr;const HRESULT ah=dxgi->GetAdapter(&adapter);dxgi->Release();if(FAILED(ah)||!adapter)return false;IDXGIOutput*selected=nullptr;DXGI_OUTPUT_DESC desc{};for(UINT i=0;;++i){IDXGIOutput*out=nullptr;if(adapter->EnumOutputs(i,&out)==DXGI_ERROR_NOT_FOUND)break;DXGI_OUTPUT_DESC d{};out->GetDesc(&d);if(d.Monitor==targetMonitor_){selected=out;desc=d;break;}out->Release();}adapter->Release();if(!selected)return false;selected->QueryInterface(__uuidof(IDXGIOutput1),reinterpret_cast<void**>(&output1_));selected->QueryInterface(__uuidof(IDXGIOutput5),reinterpret_cast<void**>(&output5_));selected->Release();if(!output1_)return false;outputDesktop_=desc.DesktopCoordinates;sdrWhiteScale_=QuerySdrWhiteScale(targetMonitor_);haveFrame_=false;stereoSourceValid_=false;lastCapturePresentQpc_=0;lastCapturePresentQpcLow_=0;return RecreateDuplication(initial);
        }

        bool RecreateDuplication(bool initial)
        {
            ReleaseCom(duplication_);
            HRESULT hr = E_FAIL;
            if (output5_)
            {
                const DXGI_FORMAT supported[]{
                    DXGI_FORMAT_R16G16B16A16_FLOAT,
                    DXGI_FORMAT_B8G8R8A8_UNORM
                };
                hr = output5_->DuplicateOutput1(device_, 0, 2, supported, &duplication_);
            }
            if ((FAILED(hr) || !duplication_) && output1_)
            {
                ReleaseCom(duplication_);
                hr = output1_->DuplicateOutput(device_, &duplication_);
            }
            if (FAILED(hr) || !duplication_)
            {
                if (initial) throw std::runtime_error("DuplicateOutput failed");
                return false;
            }
            return true;
        }

        bool EnsureSource(const D3D11_TEXTURE2D_DESC& d)
        {
            if (source_ && d.Width == sourceWidth_ && d.Height == sourceHeight_ && d.Format == sourceFormat_)
                return true;
            ReleaseCom(sourceSrv_);
            ReleaseCom(source_);
            D3D11_TEXTURE2D_DESC s{};
            s.Width = d.Width;
            s.Height = d.Height;
            s.MipLevels = 1;
            s.ArraySize = 1;
            s.Format = d.Format;
            s.SampleDesc.Count = 1;
            s.Usage = D3D11_USAGE_DEFAULT;
            s.BindFlags = D3D11_BIND_SHADER_RESOURCE;
            if (FAILED(device_->CreateTexture2D(&s, nullptr, &source_))) return false;
            D3D11_SHADER_RESOURCE_VIEW_DESC vd{};
            vd.Format = s.Format;
            vd.ViewDimension = D3D11_SRV_DIMENSION_TEXTURE2D;
            vd.Texture2D.MipLevels = 1;
            if (FAILED(device_->CreateShaderResourceView(source_, &vd, &sourceSrv_))) return false;
            sourceWidth_ = d.Width;
            sourceHeight_ = d.Height;
            sourceFormat_ = d.Format;
            return true;
        }

        bool GetGameUv(UvRect& uv)
        {
            if (!sourceWidth_ || !sourceHeight_ || !IsWindow(hwnd_)) return false;
            RECT cr{};
            if (!GetClientRect(hwnd_, &cr)) return false;
            POINT tl{ cr.left, cr.top }, br{ cr.right, cr.bottom };
            if (!ClientToScreen(hwnd_, &tl) || !ClientToScreen(hwnd_, &br)) return false;
            const float l = static_cast<float>(tl.x - outputDesktop_.left) / sourceWidth_;
            const float t = static_cast<float>(tl.y - outputDesktop_.top) / sourceHeight_;
            const float r = static_cast<float>(br.x - outputDesktop_.left) / sourceWidth_;
            const float b = static_cast<float>(br.y - outputDesktop_.top) / sourceHeight_;
            uv.x = std::clamp(l, 0.f, 1.f);
            uv.y = std::clamp(t, 0.f, 1.f);
            const float rr = std::clamp(r, 0.f, 1.f);
            const float bb = std::clamp(b, 0.f, 1.f);
            uv.w = rr - uv.x;
            uv.h = bb - uv.y;
            return uv.w > 0.01f && uv.h > 0.01f;
        }

        bool RenderTo(ID3D11RenderTargetView* rtv, std::uint32_t w, std::uint32_t h,
            const UvRect& uv, ID3D11ShaderResourceView* sourceSrv, DXGI_FORMAT sourceFormat)
        {
            if (!rtv || !sourceSrv || !constantBuffer_) return false;
            D3D11_MAPPED_SUBRESOURCE map{};
            if (FAILED(context_->Map(constantBuffer_, 0, D3D11_MAP_WRITE_DISCARD, 0, &map)))
                return false;
            auto* p = static_cast<BlitParams*>(map.pData);
            p->uvScale[0] = uv.w;
            p->uvScale[1] = uv.h;
            p->uvOffset[0] = uv.x;
            p->uvOffset[1] = uv.y;
            p->sdrWhiteScale = sdrWhiteScale_;
            p->sourceIsScRgb = sourceFormat == DXGI_FORMAT_R16G16B16A16_FLOAT ? 1.f : 0.f;
            p->padding[0] = p->padding[1] = 0;
            context_->Unmap(constantBuffer_, 0);

            D3D11_VIEWPORT vp{};
            vp.Width = static_cast<float>(w);
            vp.Height = static_cast<float>(h);
            vp.MaxDepth = 1.f;
            context_->RSSetViewports(1, &vp);
            context_->OMSetRenderTargets(1, &rtv, nullptr);
            context_->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
            context_->VSSetShader(vs_, nullptr, 0);
            context_->PSSetShader(ps_, nullptr, 0);
            context_->PSSetShaderResources(0, 1, &sourceSrv);
            context_->PSSetSamplers(0, 1, &sampler_);
            context_->PSSetConstantBuffers(0, 1, &constantBuffer_);
            context_->Draw(3, 0);
            ID3D11ShaderResourceView* nullSrv = nullptr;
            context_->PSSetShaderResources(0, 1, &nullSrv);
            ID3D11RenderTargetView* nullRtv = nullptr;
            context_->OMSetRenderTargets(1, &nullRtv, nullptr);
            return true;
        }

        bool EnsureTheaterAnchor(XrSpace viewSpace, XrSpace localSpace, XrTime time)
        {
            if (theaterAnchorValid_) return true;
            XrSpaceLocation loc{ XR_TYPE_SPACE_LOCATION };
            if (XR_FAILED(xrLocateSpace(viewSpace, localSpace, time, &loc))) return false;
            const XrSpaceLocationFlags need = XR_SPACE_LOCATION_ORIENTATION_VALID_BIT |
                XR_SPACE_LOCATION_POSITION_VALID_BIT;
            if ((loc.locationFlags & need) != need) return false;
            theaterAnchor_ = loc.pose;
            const XrVector3f f = RotateVector(loc.pose.orientation, { 0, 0, -1 });
            theaterAnchor_.position.x += f.x;
            theaterAnchor_.position.y += f.y;
            theaterAnchor_.position.z += f.z;
            theaterAnchorValid_ = true;
            return true;
        }

        XrSession session_ = XR_NULL_HANDLE;
        ID3D11Device* device_ = nullptr;
        ID3D11DeviceContext* context_ = nullptr;
        HWND hwnd_ = nullptr;
        DWORD gamePid_ = 0;
        HANDLE gameProcess_ = nullptr;
        HMONITOR targetMonitor_ = nullptr;
        RECT outputDesktop_{};
        IDXGIOutput1* output1_ = nullptr;
        IDXGIOutput5* output5_ = nullptr;
        IDXGIOutputDuplication* duplication_ = nullptr;

        ID3D11Texture2D* source_ = nullptr;
        ID3D11ShaderResourceView* sourceSrv_ = nullptr;
        std::uint32_t sourceWidth_ = 0, sourceHeight_ = 0;
        DXGI_FORMAT sourceFormat_ = DXGI_FORMAT_UNKNOWN;
        bool haveFrame_=false;std::int64_t lastCapturePresentQpc_=0;std::uint32_t lastCapturePresentQpcLow_=0;

        ID3D11Texture2D* stereoSource_ = nullptr;
        ID3D11ShaderResourceView* stereoSourceSrv_ = nullptr;
        std::uint32_t stereoSourceWidth_ = 0, stereoSourceHeight_ = 0;
        DXGI_FORMAT stereoSourceFormat_ = DXGI_FORMAT_UNKNOWN;
        bool stereoSourceValid_ = false;

        ID3D11VertexShader* vs_ = nullptr;
        ID3D11PixelShader* ps_ = nullptr;
        ID3D11SamplerState* sampler_ = nullptr;
        ID3D11Buffer* constantBuffer_ = nullptr;
        DXGI_FORMAT swapFormat_ = DXGI_FORMAT_UNKNOWN;
        SwapchainSet projection_{}, theater_{};
        float sdrWhiteScale_ = 1.f;
        std::array<XrViewConfigurationView, 2> configs_{};
        XrPosef theaterAnchor_{};
        bool theaterAnchorValid_ = false;
    };

    bool QpcAtOrAfter(std::int64_t capture,std::int64_t present){return capture>0&&present>0&&capture>=present;}
    struct TimingSeries{std::array<double,256>samples{};std::size_t count=0,cursor=0;void Add(double ms){samples[cursor++%samples.size()]=ms;if(count<samples.size())++count;}double Percentile(double p)const{if(!count)return 0;auto c=samples;std::sort(c.begin(),c.begin()+count);const std::size_t i=std::min<std::size_t>(count-1,static_cast<std::size_t>(std::ceil(p*count))-1);return c[i];}};
    struct HostTimings{TimingSeries wait,capture,render,end;LARGE_INTEGER f{};ULONGLONG last=0;HostTimings(){QueryPerformanceFrequency(&f);}double Ms(const LARGE_INTEGER&a,const LARGE_INTEGER&b)const{return f.QuadPart?double(b.QuadPart-a.QuadPart)*1000.0/double(f.QuadPart):0;}void MaybeLog(){const auto n=GetTickCount64();if(n-last<5000)return;last=n;std::cout<<"VR host timing ms p95/p99: wait "<<wait.Percentile(.95)<<"/"<<wait.Percentile(.99)<<" capture "<<capture.Percentile(.95)<<"/"<<capture.Percentile(.99)<<" render "<<render.Percentile(.95)<<"/"<<render.Percentile(.99)<<" end "<<end.Percentile(.95)<<"/"<<end.Percentile(.99)<<"\n";}};

    XrEnvironmentBlendMode ChooseBlendMode(XrInstance instance, XrSystemId system)
    {
        std::uint32_t n = 0;
        CheckXr(xrEnumerateEnvironmentBlendModes(instance, system,
            XR_VIEW_CONFIGURATION_TYPE_PRIMARY_STEREO, 0, &n, nullptr),
            "xrEnumerateEnvironmentBlendModes(count)");
        std::vector<XrEnvironmentBlendMode> modes(n);
        CheckXr(xrEnumerateEnvironmentBlendModes(instance, system,
            XR_VIEW_CONFIGURATION_TYPE_PRIMARY_STEREO, n, &n, modes.data()),
            "xrEnumerateEnvironmentBlendModes(list)");
        for (auto m : modes) if (m == XR_ENVIRONMENT_BLEND_MODE_OPAQUE) return m;
        if (modes.empty()) throw std::runtime_error("no blend mode");
        return modes.front();
    }

    void ParseRuntimeOverride(int argc, char** argv)
    {
        for (int i = 1; i + 1 < argc; ++i)
        {
            if (std::strcmp(argv[i], "--runtime-json") == 0)
            {
                SetEnvironmentVariableA("XR_RUNTIME_JSON", argv[i + 1]);
                std::cout << "XR_RUNTIME_JSON=" << argv[i + 1] << "\n";
                return;
            }
        }
    }
}

int main(int argc, char** argv)
{
    XrInstance instance = XR_NULL_HANDLE;
    XrSession session = XR_NULL_HANDLE;
    XrSpace localSpace = XR_NULL_HANDLE;
    XrSpace viewSpace = XR_NULL_HANDLE;

    try
    {
        SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);
        ParseRuntimeOverride(argc, argv);
        HWND gameWindow = WaitForGameWindow();
        DWORD gamePid = 0;
        GetWindowThreadProcessId(gameWindow, &gamePid);

        if (!HasExtension(XR_KHR_D3D11_ENABLE_EXTENSION_NAME))
            throw std::runtime_error("runtime lacks XR_KHR_D3D11_enable");
        const char* extensions[]{ XR_KHR_D3D11_ENABLE_EXTENSION_NAME };
        XrInstanceCreateInfo ii{ XR_TYPE_INSTANCE_CREATE_INFO };
        strncpy_s(ii.applicationInfo.applicationName, sizeof(ii.applicationInfo.applicationName),
            "OutRun 2006 True Stereo VR", _TRUNCATE);
        ii.applicationInfo.applicationVersion = 1;
        strncpy_s(ii.applicationInfo.engineName, sizeof(ii.applicationInfo.engineName),
            "OutRun2006Tweaks", _TRUNCATE);
        ii.applicationInfo.engineVersion = 1;
        ii.applicationInfo.apiVersion = XR_CURRENT_API_VERSION;
        ii.enabledExtensionCount = 1;
        ii.enabledExtensionNames = extensions;
        CheckXr(xrCreateInstance(&ii, &instance), "xrCreateInstance");

        XrInstanceProperties ip{ XR_TYPE_INSTANCE_PROPERTIES };
        CheckXr(xrGetInstanceProperties(instance, &ip), "xrGetInstanceProperties");
        std::cout << "OpenXR runtime: " << ip.runtimeName << " "
            << XR_VERSION_MAJOR(ip.runtimeVersion) << "."
            << XR_VERSION_MINOR(ip.runtimeVersion) << "."
            << XR_VERSION_PATCH(ip.runtimeVersion) << "\n";

        XrSystemGetInfo sgi{ XR_TYPE_SYSTEM_GET_INFO };
        sgi.formFactor = XR_FORM_FACTOR_HEAD_MOUNTED_DISPLAY;
        XrSystemId system = XR_NULL_SYSTEM_ID;
        for (;;)
        {
            const XrResult r = xrGetSystem(instance, &sgi, &system);
            if (r == XR_ERROR_FORM_FACTOR_UNAVAILABLE) { Sleep(1000); continue; }
            CheckXr(r, "xrGetSystem");
            break;
        }

        PFN_xrGetD3D11GraphicsRequirementsKHR getReq = nullptr;
        CheckXr(xrGetInstanceProcAddr(instance, "xrGetD3D11GraphicsRequirementsKHR",
            reinterpret_cast<PFN_xrVoidFunction*>(&getReq)), "xrGetInstanceProcAddr");
        XrGraphicsRequirementsD3D11KHR req{ XR_TYPE_GRAPHICS_REQUIREMENTS_D3D11_KHR };
        CheckXr(getReq(instance, system, &req), "xrGetD3D11GraphicsRequirementsKHR");
        D3DObjects d3d = CreateD3D11Device(req);

        XrGraphicsBindingD3D11KHR binding{ XR_TYPE_GRAPHICS_BINDING_D3D11_KHR };
        binding.device = d3d.device;
        XrSessionCreateInfo si{ XR_TYPE_SESSION_CREATE_INFO };
        si.next = &binding;
        si.systemId = system;
        CheckXr(xrCreateSession(instance, &si, &session), "xrCreateSession");

        XrPosef identity{};
        identity.orientation.w = 1;
        XrReferenceSpaceCreateInfo li{ XR_TYPE_REFERENCE_SPACE_CREATE_INFO };
        li.referenceSpaceType = XR_REFERENCE_SPACE_TYPE_LOCAL;
        li.poseInReferenceSpace = identity;
        CheckXr(xrCreateReferenceSpace(session, &li, &localSpace), "xrCreateReferenceSpace LOCAL");
        XrReferenceSpaceCreateInfo vi{ XR_TYPE_REFERENCE_SPACE_CREATE_INFO };
        vi.referenceSpaceType = XR_REFERENCE_SPACE_TYPE_VIEW;
        vi.poseInReferenceSpace = identity;
        CheckXr(xrCreateReferenceSpace(session, &vi, &viewSpace), "xrCreateReferenceSpace VIEW");

        std::uint32_t cc = 0;
        CheckXr(xrEnumerateViewConfigurationViews(instance, system,
            XR_VIEW_CONFIGURATION_TYPE_PRIMARY_STEREO, 0, &cc, nullptr),
            "xrEnumerateViewConfigurationViews count");
        if (cc < 2) throw std::runtime_error("runtime has fewer than two stereo views");
        std::vector<XrViewConfigurationView> cv(cc);
        for (auto& c : cv) c = { XR_TYPE_VIEW_CONFIGURATION_VIEW };
        CheckXr(xrEnumerateViewConfigurationViews(instance, system,
            XR_VIEW_CONFIGURATION_TYPE_PRIMARY_STEREO, cc, &cc, cv.data()),
            "xrEnumerateViewConfigurationViews list");
        std::array<XrViewConfigurationView, 2> configs{ cv[0], cv[1] };

        SharedWriter shared;RenderFrameReader renderFrames;StereoCompositor compositor(session,d3d.device,d3d.context,gameWindow,configs);compositor.Initialize();ViewHistory viewHistory;HostTimings timings;
        const XrEnvironmentBlendMode blend = ChooseBlendMode(instance, system);

        bool running = false, quit = false, exitRequested = false;
        ULONGLONG exitRequestMs = 0;
        XrSessionState state = XR_SESSION_STATE_UNKNOWN;
        OutRunVR::ClientPresentationMode lastPresentation = OutRunVR::PresentationUnknown;
        std::array<XrView, 2> matchedViews{};
        bool matchedStereoValid = false;
        std::uint32_t lastProcessedStereoFrame = 0;
        ULONGLONG lastStereoMatchMs=0;bool pendingReferenceSpaceChange=false;XrTime pendingReferenceSpaceChangeTime=0;

        while (!quit)
        {
            if (!compositor.GameAlive() && !exitRequested)
            {
                exitRequested = true;
                exitRequestMs = GetTickCount64();
                if (session != XR_NULL_HANDLE) xrRequestExitSession(session);
                std::cout << "OutRun exited; requesting OpenXR shutdown.\n";
            }

            XrEventDataBuffer event{ XR_TYPE_EVENT_DATA_BUFFER };
            while (xrPollEvent(instance, &event) == XR_SUCCESS)
            {
                if (event.type == XR_TYPE_EVENT_DATA_SESSION_STATE_CHANGED)
                {
                    auto* e = reinterpret_cast<XrEventDataSessionStateChanged*>(&event);
                    state = e->state;
                    if (state == XR_SESSION_STATE_READY && !running)
                    {
                        XrSessionBeginInfo bi{ XR_TYPE_SESSION_BEGIN_INFO };
                        bi.primaryViewConfigurationType = XR_VIEW_CONFIGURATION_TYPE_PRIMARY_STEREO;
                        CheckXr(xrBeginSession(session, &bi), "xrBeginSession");
                        running = true;
                    }
                    else if (state == XR_SESSION_STATE_STOPPING && running)
                    {
                        CheckXr(xrEndSession(session), "xrEndSession");
                        running = false;
                    }
                    else if (state == XR_SESSION_STATE_EXITING || state == XR_SESSION_STATE_LOSS_PENDING)
                        quit = true;
                }
                else if(event.type==XR_TYPE_EVENT_DATA_REFERENCE_SPACE_CHANGE_PENDING){const auto*e=reinterpret_cast<XrEventDataReferenceSpaceChangePending*>(&event);if(e->referenceSpaceType==XR_REFERENCE_SPACE_TYPE_LOCAL){pendingReferenceSpaceChange=true;pendingReferenceSpaceChangeTime=e->changeTime;}}
                event = { XR_TYPE_EVENT_DATA_BUFFER };
            }

            if (quit) break;
            if (exitRequested && GetTickCount64() - exitRequestMs > 2000) break;
            if (!running) { Sleep(10); continue; }

            XrFrameWaitInfo wi{ XR_TYPE_FRAME_WAIT_INFO };
            XrFrameState fs{ XR_TYPE_FRAME_STATE };
            LARGE_INTEGER ws{},we{};QueryPerformanceCounter(&ws);CheckXr(xrWaitFrame(session,&wi,&fs),"xrWaitFrame");QueryPerformanceCounter(&we);timings.wait.Add(timings.Ms(ws,we));
            if(pendingReferenceSpaceChange&&(pendingReferenceSpaceChangeTime==0||fs.predictedDisplayTime>=pendingReferenceSpaceChangeTime)){shared.ReferenceSpaceChanged();compositor.ReferenceSpaceChanged();viewHistory.Clear();matchedStereoValid=false;OutRunVR::SharedRenderFrameState rf{};lastProcessedStereoFrame=renderFrames.Read(rf)?rf.frameId:shared.ReadStereoMeta().frame;pendingReferenceSpaceChange=false;pendingReferenceSpaceChangeTime=0;}
            XrFrameBeginInfo bi{ XR_TYPE_FRAME_BEGIN_INFO };
            CheckXr(xrBeginFrame(session, &bi), "xrBeginFrame");

            XrSpaceLocation head{ XR_TYPE_SPACE_LOCATION };
            CheckXr(xrLocateSpace(viewSpace, localSpace, fs.predictedDisplayTime, &head), "xrLocateSpace");
            std::array<XrView, 2> views{};
            for (auto& v : views) v = { XR_TYPE_VIEW };
            XrViewState vs{ XR_TYPE_VIEW_STATE };
            XrViewLocateInfo vl{ XR_TYPE_VIEW_LOCATE_INFO };
            vl.viewConfigurationType = XR_VIEW_CONFIGURATION_TYPE_PRIMARY_STEREO;
            vl.displayTime = fs.predictedDisplayTime;
            vl.space = localSpace;
            std::uint32_t vc = 0;
            CheckXr(xrLocateViews(session, &vl, &vs, 2, &vc, views.data()), "xrLocateViews");

            const std::uint32_t hostSequence = shared.Write(head, views, vc, configs,
                state, vs.viewStateFlags, ip.runtimeName);
            const XrViewStateFlags neededViews = XR_VIEW_STATE_ORIENTATION_VALID_BIT |
                XR_VIEW_STATE_POSITION_VALID_BIT;
            if (vc >= 2 && (vs.viewStateFlags & neededViews) == neededViews)
                viewHistory.Store(hostSequence, views);

            XrFrameEndInfo end{ XR_TYPE_FRAME_END_INFO };
            end.displayTime = fs.predictedDisplayTime;
            end.environmentBlendMode = blend;
            const XrCompositionLayerBaseHeader* layers[1]{};
            std::array<XrCompositionLayerProjectionView, 2> pv{};
            XrCompositionLayerProjection projection{ XR_TYPE_COMPOSITION_LAYER_PROJECTION };
            XrCompositionLayerQuad quad{ XR_TYPE_COMPOSITION_LAYER_QUAD };

            const auto presentation = shared.Presentation();
            if (presentation != lastPresentation)
            {
                compositor.ReferenceSpaceChanged();
                matchedStereoValid=false;OutRunVR::SharedRenderFrameState rf{};lastProcessedStereoFrame=renderFrames.Read(rf)?rf.frameId:shared.ReadStereoMeta().frame;lastPresentation=presentation;
                std::cout << "VR presentation: "
                    << (presentation == OutRunVR::PresentationGameplay
                        ? "true stereo projection" : "LOCAL-fixed theater") << ".\n";
            }

            bool layerReady=false;
            if(fs.shouldRender==XR_TRUE&&vc>=2){
                if(presentation==OutRunVR::PresentationGameplay){OutRunVR::SharedRenderFrameState before{};const bool have=renderFrames.Read(before);const std::uint32_t need=OutRunVR::RenderFrameStereoComplete|OutRunVR::RenderFrameWorldStereo|OutRunVR::RenderFrameDrawDuplicated|OutRunVR::RenderFrameEffectivePoseValid;
                    if(have&&before.state==OutRunVR::StereoSbsActive&&before.frameId&&before.frameId!=lastProcessedStereoFrame&&before.sourcePoseSequence&&(before.flags&need)==need){std::array<XrView,2> history{};if(viewHistory.Find(before.sourcePoseSequence,history)){LARGE_INTEGER cs{},ce{};QueryPerformanceCounter(&cs);const CaptureStatus capture=compositor.Capture(2);QueryPerformanceCounter(&ce);timings.capture.Add(timings.Ms(cs,ce));OutRunVR::SharedRenderFrameState after{};const bool same=renderFrames.Read(after)&&after.state==before.state&&after.frameId==before.frameId&&after.sourcePoseSequence==before.sourcePoseSequence&&after.presentQpc==before.presentQpc;if(capture.available&&QpcAtOrAfter(capture.lastPresentQpc,before.presentQpc)&&same&&compositor.CommitStereoSource()){for(int eye=0;eye<2;++eye){matchedViews[eye]={XR_TYPE_VIEW};matchedViews[eye].pose.orientation={before.eye[eye].orientation[0],before.eye[eye].orientation[1],before.eye[eye].orientation[2],before.eye[eye].orientation[3]};matchedViews[eye].pose.position={before.eye[eye].position[0],before.eye[eye].position[1],before.eye[eye].position[2]};matchedViews[eye].fov={before.eye[eye].fov.angleLeft,before.eye[eye].fov.angleRight,before.eye[eye].fov.angleUp,before.eye[eye].fov.angleDown};}matchedStereoValid=true;lastProcessedStereoFrame=before.frameId;lastStereoMatchMs=GetTickCount64();}}}
                    const bool grace=matchedStereoValid&&compositor.HasStereoSource()&&GetTickCount64()-lastStereoMatchMs<=StereoGraceMs;LARGE_INTEGER rs{},re{};QueryPerformanceCounter(&rs);if(grace&&compositor.RenderProjection(matchedViews,pv)){projection.space=localSpace;projection.viewCount=2;projection.views=pv.data();layers[0]=reinterpret_cast<const XrCompositionLayerBaseHeader*>(&projection);layerReady=true;}QueryPerformanceCounter(&re);timings.render.Add(timings.Ms(rs,re));
                }else{LARGE_INTEGER cs{},ce{};QueryPerformanceCounter(&cs);const CaptureStatus capture=compositor.Capture();QueryPerformanceCounter(&ce);timings.capture.Add(timings.Ms(cs,ce));LARGE_INTEGER rs{},re{};QueryPerformanceCounter(&rs);if(capture.available&&compositor.RenderTheater(viewSpace,localSpace,fs.predictedDisplayTime,quad)){layers[0]=reinterpret_cast<const XrCompositionLayerBaseHeader*>(&quad);layerReady=true;}QueryPerformanceCounter(&re);timings.render.Add(timings.Ms(rs,re));}}
            end.layerCount=layerReady?1:0;end.layers=layerReady?layers:nullptr;LARGE_INTEGER es{},ee{};QueryPerformanceCounter(&es);CheckXr(xrEndFrame(session,&end),"xrEndFrame");QueryPerformanceCounter(&ee);timings.end.Add(timings.Ms(es,ee));timings.MaybeLog();
        }

        compositor.Shutdown();
        if (viewSpace != XR_NULL_HANDLE) xrDestroySpace(viewSpace);
        if (localSpace != XR_NULL_HANDLE) xrDestroySpace(localSpace);
        if (session != XR_NULL_HANDLE) xrDestroySession(session);
        if (instance != XR_NULL_HANDLE) xrDestroyInstance(instance);
        return 0;
    }
    catch (const std::exception& e)
    {
        std::cerr << "OutRun VR host error: " << e.what() << "\n";
        if (viewSpace != XR_NULL_HANDLE) xrDestroySpace(viewSpace);
        if (localSpace != XR_NULL_HANDLE) xrDestroySpace(localSpace);
        if (session != XR_NULL_HANDLE) xrDestroySession(session);
        if (instance != XR_NULL_HANDLE) xrDestroyInstance(instance);
        return 1;
    }
}
