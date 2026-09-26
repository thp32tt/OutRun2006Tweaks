#pragma once

#include <d3d9.h>
#include <d3d12.h>
#include <unknwn.h>

#ifndef MAX_D3D9ON12_QUEUES
#define MAX_D3D9ON12_QUEUES 2
#endif

struct D3D9ON12_ARGS
{
    BOOL Enable9On12;
    IUnknown* pD3D12Device;
    IUnknown* ppD3D12Queues[MAX_D3D9ON12_QUEUES];
    UINT NumQueues;
    UINT NodeMask;
};

using PFN_Direct3DCreate9On12Ex = HRESULT (WINAPI*)(
    UINT SDKVersion,
    D3D9ON12_ARGS* pOverrideList,
    UINT NumOverrideEntries,
    IDirect3D9Ex** ppOutputInterface);

MIDL_INTERFACE("e7fda234-b589-4049-940d-8878977531c8")
IDirect3DDevice9On12 : public IUnknown
{
public:
    virtual HRESULT STDMETHODCALLTYPE GetD3D12Device(
        REFIID riid,
        void** ppvDevice) = 0;

    virtual HRESULT STDMETHODCALLTYPE UnwrapUnderlyingResource(
        IDirect3DResource9* pResource,
        ID3D12CommandQueue* pCommandQueue,
        REFIID riid,
        void** ppvResource12) = 0;

    virtual HRESULT STDMETHODCALLTYPE ReturnUnderlyingResource(
        IDirect3DResource9* pResource,
        UINT NumSync,
        UINT64* pSignalValues,
        ID3D12Fence** ppFences) = 0;
};
