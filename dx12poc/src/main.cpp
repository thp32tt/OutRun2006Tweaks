#include "d3d9on12_compat.hpp"

#include <windows.h>
#include <d3d12.h>
#include <dxgi1_4.h>
#include <wrl/client.h>

#include <cstdint>
#include <cstring>
#include <iomanip>
#include <iostream>

using Microsoft::WRL::ComPtr;

namespace
{
constexpr const char* kBuildMarker = "OUTRUN_DX12_POC_BUILD_2_R56";

void PrintHr(const char* what, HRESULT hr)
{
    std::cerr << what << " failed, hr=0x"
              << std::hex << std::uppercase
              << static_cast<std::uint32_t>(hr)
              << std::dec << std::nouppercase << "\n";
}

bool SameLuid(const LUID& a, const LUID& b)
{
    return a.HighPart == b.HighPart && a.LowPart == b.LowPart;
}

HWND CreateProbeWindow()
{
    const HINSTANCE instance = GetModuleHandleW(nullptr);
    const wchar_t* className = L"OutRunD3D9On12ProbeWindow";

    WNDCLASSW wc{};
    wc.lpfnWndProc = DefWindowProcW;
    wc.hInstance = instance;
    wc.lpszClassName = className;

    if (!RegisterClassW(&wc) && GetLastError() != ERROR_CLASS_ALREADY_EXISTS)
        return nullptr;

    return CreateWindowExW(
        0,
        className,
        L"OutRun D3D9On12 Probe",
        WS_OVERLAPPEDWINDOW,
        CW_USEDEFAULT,
        CW_USEDEFAULT,
        320,
        240,
        nullptr,
        nullptr,
        instance,
        nullptr);
}

HRESULT CreateHardwareD3D12(
    ComPtr<IDXGIAdapter1>& outAdapter,
    ComPtr<ID3D12Device>& outDevice,
    ComPtr<ID3D12CommandQueue>& outQueue)
{
    ComPtr<IDXGIFactory4> factory;
    HRESULT hr = CreateDXGIFactory1(IID_PPV_ARGS(&factory));
    if (FAILED(hr))
        return hr;

    for (UINT index = 0;; ++index)
    {
        ComPtr<IDXGIAdapter1> adapter;
        hr = factory->EnumAdapters1(index, &adapter);
        if (hr == DXGI_ERROR_NOT_FOUND)
            break;
        if (FAILED(hr))
            return hr;

        DXGI_ADAPTER_DESC1 desc{};
        adapter->GetDesc1(&desc);
        if (desc.Flags & DXGI_ADAPTER_FLAG_SOFTWARE)
            continue;

        ComPtr<ID3D12Device> candidate;
        hr = D3D12CreateDevice(
            adapter.Get(),
            D3D_FEATURE_LEVEL_11_0,
            IID_PPV_ARGS(&candidate));
        if (FAILED(hr))
            continue;

        D3D12_COMMAND_QUEUE_DESC queueDesc{};
        queueDesc.Type = D3D12_COMMAND_LIST_TYPE_DIRECT;
        queueDesc.Priority = D3D12_COMMAND_QUEUE_PRIORITY_NORMAL;
        queueDesc.Flags = D3D12_COMMAND_QUEUE_FLAG_NONE;
        queueDesc.NodeMask = 0;

        ComPtr<ID3D12CommandQueue> queue;
        hr = candidate->CreateCommandQueue(&queueDesc, IID_PPV_ARGS(&queue));
        if (FAILED(hr))
            continue;

        outAdapter = adapter;
        outDevice = candidate;
        outQueue = queue;
        return S_OK;
    }

    return DXGI_ERROR_NOT_FOUND;
}

HRESULT CreateD3D9On12(
    ID3D12Device* device12,
    ID3D12CommandQueue* queue12,
    HWND window,
    ComPtr<IDirect3D9Ex>& outD3D9,
    ComPtr<IDirect3DDevice9>& outDevice9,
    D3DPRESENT_PARAMETERS& outAcceptedParams,
    bool& outNormalized)
{
    HMODULE d3d9 = LoadLibraryExW(
        L"d3d9.dll",
        nullptr,
        LOAD_LIBRARY_SEARCH_SYSTEM32);
    if (!d3d9)
        return HRESULT_FROM_WIN32(GetLastError());

    auto create9On12Ex =
        reinterpret_cast<PFN_Direct3DCreate9On12Ex>(
            GetProcAddress(d3d9, "Direct3DCreate9On12Ex"));
    if (!create9On12Ex)
        return HRESULT_FROM_WIN32(GetLastError());

    D3D9ON12_ARGS args{};
    args.Enable9On12 = TRUE;
    args.pD3D12Device = device12;
    args.ppD3D12Queues[0] = queue12;
    args.NumQueues = 1;
    args.NodeMask = 0;

    HRESULT hr = create9On12Ex(
        D3D_SDK_VERSION,
        &args,
        1,
        &outD3D9);
    if (FAILED(hr))
        return hr;

    // Match OutRun's legacy API contract first: the game calls
    // IDirect3D9::CreateDevice, not CreateDeviceEx. Keep a slightly more
    // demanding two-buffer request so the probe also exercises the same
    // compatibility boundary seen in the game.
    D3DPRESENT_PARAMETERS requested{};
    requested.BackBufferWidth = 320;
    requested.BackBufferHeight = 240;
    requested.BackBufferFormat = D3DFMT_UNKNOWN;
    requested.BackBufferCount = 2;
    requested.MultiSampleType = D3DMULTISAMPLE_NONE;
    requested.SwapEffect = D3DSWAPEFFECT_DISCARD;
    requested.hDeviceWindow = window;
    requested.Windowed = TRUE;
    requested.EnableAutoDepthStencil = TRUE;
    requested.AutoDepthStencilFormat = D3DFMT_D24S8;
    requested.FullScreen_RefreshRateInHz = 0;
    requested.PresentationInterval = D3DPRESENT_INTERVAL_IMMEDIATE;

    auto tryCreate = [&](DWORD behavior, D3DPRESENT_PARAMETERS& pp) -> HRESULT {
        outDevice9.Reset();
        return outD3D9->CreateDevice(
            D3DADAPTER_DEFAULT,
            D3DDEVTYPE_HAL,
            window,
            behavior,
            &pp,
            &outDevice9);
    };

    const DWORD hardware =
        D3DCREATE_HARDWARE_VERTEXPROCESSING |
        D3DCREATE_FPU_PRESERVE;
    const DWORD software =
        D3DCREATE_SOFTWARE_VERTEXPROCESSING |
        D3DCREATE_FPU_PRESERVE;

    D3DPRESENT_PARAMETERS attempted = requested;
    outNormalized = false;
    hr = tryCreate(hardware, attempted);
    if (FAILED(hr))
        hr = tryCreate(software, attempted);

    if (FAILED(hr) || !outDevice9)
    {
        // Bounded normalization copied from the proven DX12 compatibility
        // candidate: stay on D3D9On12, never fall back to native D3D9.
        D3DPRESENT_PARAMETERS safe = requested;
        if (safe.Windowed)
        {
            safe.FullScreen_RefreshRateInHz = 0;
            if (!safe.hDeviceWindow)
                safe.hDeviceWindow = window;
        }
        if (safe.BackBufferCount > 1)
            safe.BackBufferCount = 1;
        safe.PresentationInterval = D3DPRESENT_INTERVAL_DEFAULT;

        hr = tryCreate(hardware, safe);
        if (FAILED(hr))
            hr = tryCreate(software, safe);
        if (SUCCEEDED(hr) && outDevice9)
        {
            attempted = safe;
            outNormalized = true;
        }
    }

    if (SUCCEEDED(hr) && outDevice9)
        outAcceptedParams = attempted;
    return hr;
}

struct ManagedResourceProbe
{
    ComPtr<IDirect3DTexture9> texture;
    ComPtr<IDirect3DVertexBuffer9> vertexBuffer;
};

HRESULT CreateManagedResourceProbe(
    IDirect3DDevice9* device9,
    ManagedResourceProbe& out)
{
    if (!device9)
        return E_POINTER;

    HRESULT hr = device9->CreateTexture(
        32, 32, 1, 0, D3DFMT_A8R8G8B8,
        D3DPOOL_MANAGED, &out.texture, nullptr);
    if (FAILED(hr))
        return hr;

    D3DLOCKED_RECT locked{};
    hr = out.texture->LockRect(0, &locked, nullptr, 0);
    if (FAILED(hr))
        return hr;
    if (locked.pBits && locked.Pitch > 0)
        std::memset(locked.pBits, 0x5a,
            static_cast<std::size_t>(locked.Pitch) * 32u);
    out.texture->UnlockRect(0);

    hr = device9->CreateVertexBuffer(
        256, 0, D3DFVF_XYZ, D3DPOOL_MANAGED,
        &out.vertexBuffer, nullptr);
    if (FAILED(hr))
        return hr;

    void* vb = nullptr;
    hr = out.vertexBuffer->Lock(0, 0, &vb, 0);
    if (FAILED(hr))
        return hr;
    if (vb)
        std::memset(vb, 0x3c, 256);
    out.vertexBuffer->Unlock();

    return S_OK;
}

HRESULT ValidateManagedResourceProbeAfterReset(
    ManagedResourceProbe& probe)
{
    if (!probe.texture || !probe.vertexBuffer)
        return E_POINTER;

    D3DLOCKED_RECT locked{};
    HRESULT hr = probe.texture->LockRect(0, &locked, nullptr, 0);
    if (FAILED(hr))
        return hr;
    probe.texture->UnlockRect(0);

    void* vb = nullptr;
    hr = probe.vertexBuffer->Lock(0, 0, &vb, 0);
    if (FAILED(hr))
        return hr;
    probe.vertexBuffer->Unlock();
    return S_OK;
}

HRESULT ExerciseResourceInterop(
    IDirect3DDevice9* device9,
    IDirect3DDevice9On12* bridge,
    ID3D12Device* device12,
    ID3D12CommandQueue* queue12)
{
    ComPtr<IDirect3DTexture9> texture9;
    HRESULT hr = device9->CreateTexture(
        64,
        64,
        1,
        D3DUSAGE_RENDERTARGET,
        D3DFMT_A8R8G8B8,
        D3DPOOL_DEFAULT,
        &texture9,
        nullptr);
    if (FAILED(hr))
        return hr;

    // Schedule real D3D9 work before checkout so UnwrapUnderlyingResource must
    // honor translation-layer ownership and queue synchronization.
    ComPtr<IDirect3DSurface9> originalRt;
    ComPtr<IDirect3DSurface9> textureRt;
    hr = device9->GetRenderTarget(0, &originalRt);
    if (FAILED(hr))
        return hr;

    hr = texture9->GetSurfaceLevel(0, &textureRt);
    if (FAILED(hr))
        return hr;

    hr = device9->SetRenderTarget(0, textureRt.Get());
    if (FAILED(hr))
        return hr;

    hr = device9->Clear(
        0,
        nullptr,
        D3DCLEAR_TARGET,
        D3DCOLOR_ARGB(255, 12, 34, 56),
        1.0f,
        0);

    const HRESULT restoreHr =
        device9->SetRenderTarget(0, originalRt.Get());
    if (FAILED(hr))
        return hr;
    if (FAILED(restoreHr))
        return restoreHr;

    ComPtr<ID3D12Resource> resource12;
    hr = bridge->UnwrapUnderlyingResource(
        texture9.Get(),
        queue12,
        IID_PPV_ARGS(&resource12));
    if (FAILED(hr))
        return hr;

    const D3D12_RESOURCE_DESC desc = resource12->GetDesc();
    std::cout << "unwrapped_resource="
              << desc.Width << "x" << desc.Height
              << " format=" << static_cast<unsigned>(desc.Format)
              << "\n";

    ComPtr<ID3D12Fence> fence;
    hr = device12->CreateFence(
        0,
        D3D12_FENCE_FLAG_NONE,
        IID_PPV_ARGS(&fence));
    if (FAILED(hr))
        return hr;

    constexpr UINT64 signalValue = 1;
    hr = queue12->Signal(fence.Get(), signalValue);
    if (FAILED(hr))
        return hr;

    UINT64 values[] = { signalValue };
    ID3D12Fence* fences[] = { fence.Get() };
    hr = bridge->ReturnUnderlyingResource(
        texture9.Get(),
        1,
        values,
        fences);
    if (FAILED(hr))
        return hr;

    if (fence->GetCompletedValue() < signalValue)
    {
        HANDLE eventHandle = CreateEventW(nullptr, FALSE, FALSE, nullptr);
        if (!eventHandle)
            return HRESULT_FROM_WIN32(GetLastError());

        hr = fence->SetEventOnCompletion(signalValue, eventHandle);
        if (SUCCEEDED(hr))
            WaitForSingleObject(eventHandle, 5000);
        CloseHandle(eventHandle);
        if (FAILED(hr))
            return hr;
    }

    return S_OK;
}
} // namespace

int wmain()
{
    std::cout << kBuildMarker << "\n";

    HWND window = CreateProbeWindow();
    if (!window)
    {
        std::cerr << "probe_window=FAIL\n";
        return 10;
    }

    ComPtr<IDXGIAdapter1> adapter12;
    ComPtr<ID3D12Device> device12;
    ComPtr<ID3D12CommandQueue> queue12;

    HRESULT hr = CreateHardwareD3D12(adapter12, device12, queue12);
    if (FAILED(hr))
    {
        PrintHr("CreateHardwareD3D12", hr);
        DestroyWindow(window);
        return 20;
    }

    DXGI_ADAPTER_DESC1 adapterDesc{};
    adapter12->GetDesc1(&adapterDesc);
    std::wcout << L"adapter=" << adapterDesc.Description << L"\n";

    ComPtr<IDirect3D9Ex> d3d9;
    ComPtr<IDirect3DDevice9> device9;
    D3DPRESENT_PARAMETERS acceptedParams{};
    bool normalizedCreate = false;
    hr = CreateD3D9On12(
        device12.Get(),
        queue12.Get(),
        window,
        d3d9,
        device9,
        acceptedParams,
        normalizedCreate);
    if (FAILED(hr))
    {
        PrintHr("CreateD3D9On12", hr);
        DestroyWindow(window);
        return 30;
    }

    ComPtr<IDirect3DDevice9On12> bridge;
    hr = device9->QueryInterface(IID_PPV_ARGS(&bridge));
    if (FAILED(hr))
    {
        PrintHr("QueryInterface(IDirect3DDevice9On12)", hr);
        DestroyWindow(window);
        return 40;
    }

    ComPtr<ID3D12Device> bridgeDevice12;
    hr = bridge->GetD3D12Device(IID_PPV_ARGS(&bridgeDevice12));
    if (FAILED(hr))
    {
        PrintHr("GetD3D12Device", hr);
        DestroyWindow(window);
        return 50;
    }

    const LUID requestedLuid = device12->GetAdapterLuid();
    const LUID bridgeLuid = bridgeDevice12->GetAdapterLuid();
    const bool sameAdapter = SameLuid(requestedLuid, bridgeLuid);

    std::cout << "d3d9on12_bridge=PASS\n";
    std::cout << "legacy_create_device=PASS\n";
    std::cout << "create_normalized=" << (normalizedCreate ? 1 : 0) << "\n";
    std::cout << "accepted_backbuffer_count=" << acceptedParams.BackBufferCount << "\n";
    std::cout << "accepted_interval=" << acceptedParams.PresentationInterval << "\n";
    std::cout << "same_adapter=" << (sameAdapter ? 1 : 0) << "\n";
    std::cout << "d3d12_node_count=" << bridgeDevice12->GetNodeCount() << "\n";

    if (!sameAdapter)
    {
        std::cerr << "D3D9On12 returned a different D3D12 adapter.\n";
        DestroyWindow(window);
        return 60;
    }

    ManagedResourceProbe managed{};
    hr = CreateManagedResourceProbe(device9.Get(), managed);
    if (FAILED(hr))
    {
        PrintHr("CreateManagedResourceProbe", hr);
        DestroyWindow(window);
        return 65;
    }
    std::cout << "managed_resources_create=PASS\n";

    hr = ExerciseResourceInterop(
        device9.Get(),
        bridge.Get(),
        bridgeDevice12.Get(),
        queue12.Get());
    if (FAILED(hr))
    {
        PrintHr("ExerciseResourceInterop", hr);
        DestroyWindow(window);
        return 70;
    }

    std::cout << "resource_interop=PASS\n";

    // Resource interop objects are out of scope now. Validate the legacy
    // Reset contract on the same D3D9On12 device before declaring the current
    // R56 base suitable for game interception work.
    D3DPRESENT_PARAMETERS resetParams = acceptedParams;
    resetParams.hDeviceWindow = window;
    const HRESULT resetHr = device9->Reset(&resetParams);
    if (FAILED(resetHr))
    {
        PrintHr("IDirect3DDevice9::Reset(D3D9On12)", resetHr);
        DestroyWindow(window);
        return 80;
    }
    std::cout << "legacy_reset=PASS\n";

    hr = ValidateManagedResourceProbeAfterReset(managed);
    if (FAILED(hr))
    {
        PrintHr("ValidateManagedResourceProbeAfterReset", hr);
        DestroyWindow(window);
        return 90;
    }
    std::cout << "managed_resources_survive_reset=PASS\n";
    std::cout << "DX12_POC_RESULT=PASS\n";

    DestroyWindow(window);
    return 0;
}
