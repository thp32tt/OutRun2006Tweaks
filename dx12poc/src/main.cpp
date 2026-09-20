#include "d3d9on12_compat.hpp"

#include <windows.h>
#include <d3d12.h>
#include <dxgi1_4.h>
#include <wrl/client.h>

#include <cstdint>
#include <iomanip>
#include <iostream>

using Microsoft::WRL::ComPtr;

namespace
{
constexpr const char* kBuildMarker = "OUTRUN_DX12_POC_BUILD_1";

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
    ComPtr<IDirect3DDevice9Ex>& outDevice9)
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

    D3DPRESENT_PARAMETERS pp{};
    pp.BackBufferWidth = 320;
    pp.BackBufferHeight = 240;
    pp.BackBufferFormat = D3DFMT_UNKNOWN;
    pp.BackBufferCount = 1;
    pp.MultiSampleType = D3DMULTISAMPLE_NONE;
    pp.SwapEffect = D3DSWAPEFFECT_DISCARD;
    pp.hDeviceWindow = window;
    pp.Windowed = TRUE;
    pp.EnableAutoDepthStencil = TRUE;
    pp.AutoDepthStencilFormat = D3DFMT_D24S8;
    pp.PresentationInterval = D3DPRESENT_INTERVAL_IMMEDIATE;

    DWORD behavior =
        D3DCREATE_HARDWARE_VERTEXPROCESSING |
        D3DCREATE_FPU_PRESERVE;

    hr = outD3D9->CreateDeviceEx(
        D3DADAPTER_DEFAULT,
        D3DDEVTYPE_HAL,
        window,
        behavior,
        &pp,
        nullptr,
        &outDevice9);

    if (FAILED(hr))
    {
        behavior =
            D3DCREATE_SOFTWARE_VERTEXPROCESSING |
            D3DCREATE_FPU_PRESERVE;

        hr = outD3D9->CreateDeviceEx(
            D3DADAPTER_DEFAULT,
            D3DDEVTYPE_HAL,
            window,
            behavior,
            &pp,
            nullptr,
            &outDevice9);
    }

    return hr;
}

HRESULT ExerciseResourceInterop(
    IDirect3DDevice9Ex* device9,
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
    ComPtr<IDirect3DDevice9Ex> device9;
    hr = CreateD3D9On12(
        device12.Get(),
        queue12.Get(),
        window,
        d3d9,
        device9);
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
    std::cout << "same_adapter=" << (sameAdapter ? 1 : 0) << "\n";
    std::cout << "d3d12_node_count=" << bridgeDevice12->GetNodeCount() << "\n";

    if (!sameAdapter)
    {
        std::cerr << "D3D9On12 returned a different D3D12 adapter.\n";
        DestroyWindow(window);
        return 60;
    }

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
    std::cout << "DX12_POC_RESULT=PASS\n";

    DestroyWindow(window);
    return 0;
}
