#pragma once

#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>
#include <d3d9.h>
#include <d3d12.h>

#include <algorithm>
#include <array>
#include <atomic>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <mutex>

#include <spdlog/spdlog.h>

#include "d3d9on12_compat.hpp"
#include "../ipc/d3d12_transport.hpp"

namespace OutRunVRD3D12Bridge
{
    namespace Detail
    {
        using namespace OutRunVR::D3D12Transport;

        template <typename T>
        inline void Release(T*& value) noexcept
        {
            if (value)
            {
                value->Release();
                value = nullptr;
            }
        }

        struct ExportSlot
        {
            ID3D12Resource* left = nullptr;
            ID3D12Resource* right = nullptr;
            ID3D12CommandAllocator* allocator = nullptr;
            HANDLE leftHandle = nullptr;
            HANDLE rightHandle = nullptr;
            std::uint64_t lastFenceValue = 0;
            std::uint32_t frameId = 0;

            void Reset() noexcept
            {
                if (leftHandle) CloseHandle(leftHandle);
                if (rightHandle) CloseHandle(rightHandle);
                leftHandle = nullptr;
                rightHandle = nullptr;
                Release(left);
                Release(right);
                Release(allocator);
                lastFenceValue = 0;
                frameId = 0;
            }
        };

        struct BridgeState
        {
            std::mutex mutex;
            IDirect3DDevice9On12* on12 = nullptr;
            ID3D12Device* device = nullptr;
            ID3D12CommandQueue* queue = nullptr;
            ID3D12GraphicsCommandList* commandList = nullptr;
            ID3D12Fence* fence = nullptr;
            HANDLE fenceHandle = nullptr;
            std::array<ExportSlot, RingSize> slots{};

            HANDLE mapping = nullptr;
            SharedState* shared = nullptr;

            LUID adapterLuid{};
            D3D12_VIEW_INSTANCING_TIER viewInstancingTier =
                D3D12_VIEW_INSTANCING_TIER_NOT_SUPPORTED;
            D3D12_RESOURCE_DESC exportDesc{};
            bool exportReady = false;
            std::uint32_t generation = 0;
            std::uint32_t frameCounter = 0;
            std::uint64_t nextFenceValue = 0;
            std::uint32_t lastPublishedFrame = 0;
            bool attached = false;
            bool firstNoHostLogged = false;
            bool firstPublishLogged = false;
            bool firstBackpressureLogged = false;

            void ReleaseExportResources() noexcept
            {
                exportReady = false;
                for (auto& slot : slots)
                    slot.Reset();
                exportDesc = {};
                if (shared && shared->magic == Magic)
                {
                    InterlockedIncrement(&shared->producerSequence);
                    MemoryBarrier();
                    shared->width = 0;
                    shared->height = 0;
                    shared->format = 0;
                    shared->latestFrameId = 0;
                    for (auto& slot : shared->slots)
                    {
                        InterlockedIncrement(&slot.sequence);
                        MemoryBarrier();
                        slot.frameId = 0;
                        slot.poseSequence = 0;
                        slot.generation = 0;
                        slot.fenceValueLow = 0;
                        slot.fenceValueHigh = 0;
                        slot.leftResourceName[0] = L'\0';
                        slot.rightResourceName[0] = L'\0';
                        MemoryBarrier();
                        InterlockedIncrement(&slot.sequence);
                    }
                    MemoryBarrier();
                    InterlockedIncrement(&shared->producerSequence);
                }
            }

            void Reset() noexcept
            {
                ReleaseExportResources();
                if (fenceHandle) CloseHandle(fenceHandle);
                fenceHandle = nullptr;
                Release(commandList);
                Release(fence);
                Release(queue);
                Release(device);
                Release(on12);
                if (shared) UnmapViewOfFile(shared);
                shared = nullptr;
                if (mapping) CloseHandle(mapping);
                mapping = nullptr;
                attached = false;
                generation = 0;
                frameCounter = 0;
                nextFenceValue = 0;
                lastPublishedFrame = 0;
            }
        };

        inline BridgeState G{};

        inline void BeginWrite(volatile LONG* seq) noexcept
        {
            LONG value = InterlockedIncrement(seq);
            if ((value & 1) == 0)
                InterlockedIncrement(seq);
            MemoryBarrier();
        }

        inline void EndWrite(volatile LONG* seq) noexcept
        {
            MemoryBarrier();
            LONG value = InterlockedIncrement(seq);
            if (value & 1)
                InterlockedIncrement(seq);
        }

        inline bool ReadHostSnapshot(
            std::uint32_t& pid,
            std::uint64_t& heartbeat,
            std::uint32_t& consumed,
            std::uint32_t& luidLow,
            std::uint32_t& luidHigh) noexcept
        {
            if (!G.shared || G.shared->magic != Magic ||
                G.shared->version != Version ||
                G.shared->structSize != sizeof(SharedState))
                return false;

            for (int attempt = 0; attempt < 4; ++attempt)
            {
                const LONG before = G.shared->hostSequence;
                if (before & 1) continue;
                MemoryBarrier();
                pid = G.shared->hostPid;
                heartbeat = Join64(
                    G.shared->hostHeartbeatLow,
                    G.shared->hostHeartbeatHigh);
                consumed = G.shared->hostConsumedFrameId;
                luidLow = G.shared->hostAdapterLuidLow;
                luidHigh = G.shared->hostAdapterLuidHigh;
                MemoryBarrier();
                const LONG after = G.shared->hostSequence;
                if (before == after && !(after & 1))
                    return true;
            }
            return false;
        }

        inline bool HostReady() noexcept
        {
            std::uint32_t pid = 0, consumed = 0, low = 0, high = 0;
            std::uint64_t heartbeat = 0;
            if (!ReadHostSnapshot(pid, heartbeat, consumed, low, high) || !pid)
                return false;

            const std::uint64_t now = GetTickCount64();
            if (!heartbeat || now < heartbeat || now - heartbeat > 3000)
                return false;

            if (low != G.adapterLuid.LowPart ||
                high != static_cast<std::uint32_t>(G.adapterLuid.HighPart))
                return false;

            return true;
        }

        inline bool CreateSharedMapping() noexcept
        {
            G.mapping = CreateFileMappingW(
                INVALID_HANDLE_VALUE, nullptr, PAGE_READWRITE,
                0, static_cast<DWORD>(sizeof(SharedState)), MappingName);
            if (!G.mapping)
                return false;

            const bool existing = GetLastError() == ERROR_ALREADY_EXISTS;
            G.shared = static_cast<SharedState*>(MapViewOfFile(
                G.mapping, FILE_MAP_ALL_ACCESS, 0, 0, sizeof(SharedState)));
            if (!G.shared)
                return false;

            std::uint32_t hostPid = 0;
            std::uint32_t hostHeartbeatLow = 0;
            std::uint32_t hostHeartbeatHigh = 0;
            std::uint32_t hostConsumed = 0;
            std::uint32_t hostLuidLow = 0;
            std::uint32_t hostLuidHigh = 0;
            LONG hostSequence = 0;

            if (existing &&
                G.shared->magic == Magic &&
                G.shared->version == Version &&
                G.shared->structSize == sizeof(SharedState))
            {
                hostSequence = G.shared->hostSequence;
                hostPid = G.shared->hostPid;
                hostHeartbeatLow = G.shared->hostHeartbeatLow;
                hostHeartbeatHigh = G.shared->hostHeartbeatHigh;
                hostConsumed = G.shared->hostConsumedFrameId;
                hostLuidLow = G.shared->hostAdapterLuidLow;
                hostLuidHigh = G.shared->hostAdapterLuidHigh;
            }

            std::memset(G.shared, 0, sizeof(SharedState));
            G.shared->magic = Magic;
            G.shared->version = Version;
            G.shared->structSize = sizeof(SharedState);
            G.shared->ringSize = RingSize;
            G.shared->hostSequence = hostSequence;
            G.shared->hostPid = hostPid;
            G.shared->hostHeartbeatLow = hostHeartbeatLow;
            G.shared->hostHeartbeatHigh = hostHeartbeatHigh;
            G.shared->hostConsumedFrameId = hostConsumed;
            G.shared->hostAdapterLuidLow = hostLuidLow;
            G.shared->hostAdapterLuidHigh = hostLuidHigh;
            return true;
        }

        inline bool SameExportDesc(
            const D3D12_RESOURCE_DESC& a,
            const D3D12_RESOURCE_DESC& b) noexcept
        {
            return a.Dimension == b.Dimension &&
                a.Width == b.Width &&
                a.Height == b.Height &&
                a.DepthOrArraySize == b.DepthOrArraySize &&
                a.MipLevels == b.MipLevels &&
                a.Format == b.Format &&
                a.SampleDesc.Count == b.SampleDesc.Count &&
                a.SampleDesc.Quality == b.SampleDesc.Quality;
        }

        inline bool DescribeSurface(
            IDirect3DSurface9* surface,
            D3D12_RESOURCE_DESC& desc) noexcept
        {
            if (!surface || !G.on12 || !G.queue)
                return false;

            ID3D12Resource* resource = nullptr;
            const HRESULT unwrapHr = G.on12->UnwrapUnderlyingResource(
                surface, G.queue, __uuidof(ID3D12Resource),
                reinterpret_cast<void**>(&resource));
            if (FAILED(unwrapHr) || !resource)
                return false;

            desc = resource->GetDesc();
            resource->Release();

            const HRESULT returnHr = G.on12->ReturnUnderlyingResource(
                surface, 0, nullptr, nullptr);
            return SUCCEEDED(returnHr);
        }

        inline void MakeName(
            wchar_t (&buffer)[NameChars],
            const wchar_t* kind,
            std::uint32_t generation,
            std::uint32_t slot) noexcept
        {
            _snwprintf_s(
                buffer, NameChars, _TRUNCATE,
                L"Local\\OutRunVR-DX12-%s-%08X-%08X-%u",
                kind, GetCurrentProcessId(), generation, slot);
        }

        inline bool CreateSharedResource(
            const D3D12_RESOURCE_DESC& sourceDesc,
            const wchar_t* name,
            ID3D12Resource** resource,
            HANDLE* handle) noexcept
        {
            if (!G.device || !resource || !handle)
                return false;

            D3D12_RESOURCE_DESC desc = sourceDesc;
            desc.Alignment = 0;
            desc.MipLevels = 1;
            desc.DepthOrArraySize = 1;
            desc.SampleDesc.Count = 1;
            desc.SampleDesc.Quality = 0;
            desc.Layout = D3D12_TEXTURE_LAYOUT_UNKNOWN;
            desc.Flags = D3D12_RESOURCE_FLAG_NONE;

            D3D12_HEAP_PROPERTIES heap{};
            heap.Type = D3D12_HEAP_TYPE_DEFAULT;
            heap.CPUPageProperty = D3D12_CPU_PAGE_PROPERTY_UNKNOWN;
            heap.MemoryPoolPreference = D3D12_MEMORY_POOL_UNKNOWN;
            heap.CreationNodeMask = 1;
            heap.VisibleNodeMask = 1;

            const HRESULT createHr = G.device->CreateCommittedResource(
                &heap, D3D12_HEAP_FLAG_SHARED, &desc,
                D3D12_RESOURCE_STATE_COMMON, nullptr,
                __uuidof(ID3D12Resource),
                reinterpret_cast<void**>(resource));
            if (FAILED(createHr) || !*resource)
                return false;

            const HRESULT shareHr = G.device->CreateSharedHandle(
                *resource, nullptr, GENERIC_ALL, name, handle);
            if (FAILED(shareHr) || !*handle)
            {
                Release(*resource);
                return false;
            }
            return true;
        }

        inline bool EnsureExportResources(
            IDirect3DSurface9* left,
            IDirect3DSurface9* right) noexcept
        {
            D3D12_RESOURCE_DESC leftDesc{}, rightDesc{};
            if (!DescribeSurface(left, leftDesc) ||
                !DescribeSurface(right, rightDesc))
                return false;

            if (!SameExportDesc(leftDesc, rightDesc) ||
                leftDesc.Dimension != D3D12_RESOURCE_DIMENSION_TEXTURE2D ||
                leftDesc.DepthOrArraySize != 1 ||
                leftDesc.SampleDesc.Count != 1)
            {
                spdlog::warn(
                    "VR DX12 transport: export surfaces are incompatible left={}x{} fmt={} samples={} right={}x{} fmt={} samples={}",
                    static_cast<unsigned long long>(leftDesc.Width),
                    leftDesc.Height,
                    static_cast<int>(leftDesc.Format),
                    leftDesc.SampleDesc.Count,
                    static_cast<unsigned long long>(rightDesc.Width),
                    rightDesc.Height,
                    static_cast<int>(rightDesc.Format),
                    rightDesc.SampleDesc.Count);
                return false;
            }

            if (G.exportReady && SameExportDesc(G.exportDesc, leftDesc))
                return true;

            G.ReleaseExportResources();
            G.exportDesc = leftDesc;
            if (++G.generation == 0) ++G.generation;

            wchar_t fenceName[NameChars]{};
            _snwprintf_s(
                fenceName, NameChars, _TRUNCATE,
                L"Local\\OutRunVR-DX12-Fence-%08X-%08X",
                GetCurrentProcessId(), G.generation);

            if (G.fenceHandle)
            {
                CloseHandle(G.fenceHandle);
                G.fenceHandle = nullptr;
            }
            Release(G.fence);
            if (FAILED(G.device->CreateFence(
                    0, D3D12_FENCE_FLAG_SHARED,
                    __uuidof(ID3D12Fence),
                    reinterpret_cast<void**>(&G.fence))) ||
                !G.fence ||
                FAILED(G.device->CreateSharedHandle(
                    G.fence, nullptr, GENERIC_ALL,
                    fenceName, &G.fenceHandle)) ||
                !G.fenceHandle)
            {
                spdlog::error(
                    "VR DX12 transport: failed to create shared producer fence");
                G.ReleaseExportResources();
                return false;
            }

            for (std::uint32_t i = 0; i < RingSize; ++i)
            {
                auto& slot = G.slots[i];
                wchar_t leftName[NameChars]{};
                wchar_t rightName[NameChars]{};
                MakeName(leftName, L"L", G.generation, i);
                MakeName(rightName, L"R", G.generation, i);

                if (!CreateSharedResource(
                        leftDesc, leftName,
                        &slot.left, &slot.leftHandle) ||
                    !CreateSharedResource(
                        rightDesc, rightName,
                        &slot.right, &slot.rightHandle) ||
                    FAILED(G.device->CreateCommandAllocator(
                        D3D12_COMMAND_LIST_TYPE_DIRECT,
                        __uuidof(ID3D12CommandAllocator),
                        reinterpret_cast<void**>(&slot.allocator))) ||
                    !slot.allocator)
                {
                    spdlog::error(
                        "VR DX12 transport: failed to create ring slot {}",
                        i);
                    G.ReleaseExportResources();
                    return false;
                }

                auto& sharedSlot = G.shared->slots[i];
                BeginWrite(&sharedSlot.sequence);
                sharedSlot.frameId = 0;
                sharedSlot.poseSequence = 0;
                sharedSlot.generation = G.generation;
                sharedSlot.fenceValueLow = 0;
                sharedSlot.fenceValueHigh = 0;
                wcsncpy_s(
                    sharedSlot.leftResourceName,
                    leftName, _TRUNCATE);
                wcsncpy_s(
                    sharedSlot.rightResourceName,
                    rightName, _TRUNCATE);
                EndWrite(&sharedSlot.sequence);
            }

            if (!G.commandList)
            {
                if (FAILED(G.device->CreateCommandList(
                        0, D3D12_COMMAND_LIST_TYPE_DIRECT,
                        G.slots[0].allocator, nullptr,
                        __uuidof(ID3D12GraphicsCommandList),
                        reinterpret_cast<void**>(&G.commandList))) ||
                    !G.commandList)
                {
                    G.ReleaseExportResources();
                    return false;
                }
                G.commandList->Close();
            }

            BeginWrite(&G.shared->producerSequence);
            G.shared->clientPid = GetCurrentProcessId();
            G.shared->generation = G.generation;
            G.shared->adapterLuidLow = G.adapterLuid.LowPart;
            G.shared->adapterLuidHigh =
                static_cast<std::uint32_t>(G.adapterLuid.HighPart);
            G.shared->width = static_cast<std::uint32_t>(leftDesc.Width);
            G.shared->height = leftDesc.Height;
            G.shared->format = static_cast<std::uint32_t>(leftDesc.Format);
            G.shared->viewInstancingTier =
                static_cast<std::uint32_t>(G.viewInstancingTier);
            wcsncpy_s(
                G.shared->producerFenceName,
                fenceName, _TRUNCATE);
            EndWrite(&G.shared->producerSequence);

            G.exportReady = true;
            spdlog::info(
                "VR DX12 transport: native shared ring ready {}x{} fmt={} generation={} slots={} producerFence={} viewInstancingTier={}",
                static_cast<unsigned long long>(leftDesc.Width),
                leftDesc.Height,
                static_cast<int>(leftDesc.Format),
                G.generation,
                RingSize,
                G.nextFenceValue,
                static_cast<unsigned>(G.viewInstancingTier));
            return true;
        }

        inline D3D12_RESOURCE_BARRIER Transition(
            ID3D12Resource* resource,
            D3D12_RESOURCE_STATES before,
            D3D12_RESOURCE_STATES after) noexcept
        {
            D3D12_RESOURCE_BARRIER barrier{};
            barrier.Type = D3D12_RESOURCE_BARRIER_TYPE_TRANSITION;
            barrier.Flags = D3D12_RESOURCE_BARRIER_FLAG_NONE;
            barrier.Transition.pResource = resource;
            barrier.Transition.Subresource =
                D3D12_RESOURCE_BARRIER_ALL_SUBRESOURCES;
            barrier.Transition.StateBefore = before;
            barrier.Transition.StateAfter = after;
            return barrier;
        }
    }

    inline bool Attach(IDirect3DDevice9* device9) noexcept
    {
        using namespace Detail;
        if (!device9)
            return false;

        std::lock_guard<std::mutex> lock(G.mutex);
        if (G.attached)
            return true;

        IDirect3DDevice9On12* on12 = nullptr;
        HRESULT hr = device9->QueryInterface(
            __uuidof(IDirect3DDevice9On12),
            reinterpret_cast<void**>(&on12));
        if (FAILED(hr) || !on12)
        {
            spdlog::error(
                "VR DX12 bridge: IDirect3DDevice9On12 unavailable hr=0x{:08X}",
                static_cast<unsigned>(hr));
            return false;
        }

        ID3D12Device* device12 = nullptr;
        hr = on12->GetD3D12Device(
            __uuidof(ID3D12Device),
            reinterpret_cast<void**>(&device12));
        if (FAILED(hr) || !device12)
        {
            on12->Release();
            spdlog::error(
                "VR DX12 bridge: GetD3D12Device failed hr=0x{:08X}",
                static_cast<unsigned>(hr));
            return false;
        }

        D3D12_COMMAND_QUEUE_DESC queueDesc{};
        queueDesc.Type = D3D12_COMMAND_LIST_TYPE_DIRECT;
        queueDesc.Priority = D3D12_COMMAND_QUEUE_PRIORITY_NORMAL;
        queueDesc.Flags = D3D12_COMMAND_QUEUE_FLAG_NONE;
        queueDesc.NodeMask = 0;

        ID3D12CommandQueue* queue = nullptr;
        hr = device12->CreateCommandQueue(
            &queueDesc, __uuidof(ID3D12CommandQueue),
            reinterpret_cast<void**>(&queue));
        if (FAILED(hr) || !queue)
        {
            device12->Release();
            on12->Release();
            spdlog::error(
                "VR DX12 bridge: CreateCommandQueue failed hr=0x{:08X}",
                static_cast<unsigned>(hr));
            return false;
        }

        G.on12 = on12;
        G.device = device12;
        G.queue = queue;
        G.adapterLuid = device12->GetAdapterLuid();

        D3D12_FEATURE_DATA_D3D12_OPTIONS3 options3{};
        if (SUCCEEDED(device12->CheckFeatureSupport(
                D3D12_FEATURE_D3D12_OPTIONS3,
                &options3, sizeof(options3))))
            G.viewInstancingTier = options3.ViewInstancingTier;

        if (!CreateSharedMapping())
        {
            spdlog::error(
                "VR DX12 bridge: failed to create transport mapping error={}",
                GetLastError());
            G.Reset();
            return false;
        }

        BeginWrite(&G.shared->producerSequence);
        G.shared->clientPid = GetCurrentProcessId();
        G.shared->adapterLuidLow = G.adapterLuid.LowPart;
        G.shared->adapterLuidHigh =
            static_cast<std::uint32_t>(G.adapterLuid.HighPart);
        G.shared->viewInstancingTier =
            static_cast<std::uint32_t>(G.viewInstancingTier);
        EndWrite(&G.shared->producerSequence);

        G.attached = true;
        spdlog::info(
            "VR DX12 bridge: attached D3D9On12 -> ID3D12Device adapterLuid={:08X}:{:08X} viewInstancingTier={}",
            static_cast<std::uint32_t>(G.adapterLuid.HighPart),
            G.adapterLuid.LowPart,
            static_cast<unsigned>(G.viewInstancingTier));
        return true;
    }

    inline bool IsAttached() noexcept
    {
        return Detail::G.attached;
    }

    inline bool HostReady() noexcept
    {
        std::lock_guard<std::mutex> lock(Detail::G.mutex);
        return Detail::G.attached && Detail::HostReady();
    }

    inline std::uint32_t LastPublishedFrame() noexcept
    {
        return Detail::G.lastPublishedFrame;
    }

    inline bool PublishStereo(
        IDirect3DSurface9* left,
        IDirect3DSurface9* right,
        std::uint32_t frameId,
        std::uint32_t poseSequence) noexcept
    {
        using namespace Detail;
        if (!left || !right || !frameId)
            return false;

        std::lock_guard<std::mutex> lock(G.mutex);
        if (!G.attached || !G.on12 || !G.device || !G.queue || !G.shared)
            return false;

        if (!Detail::HostReady())
        {
            if (!G.firstNoHostLogged)
            {
                G.firstNoHostLogged = true;
                spdlog::info(
                    "VR DX12 transport: native host is not connected yet; export work stays dormant");
            }
            return false;
        }

        if (!EnsureExportResources(left, right))
            return false;

        std::uint32_t hostPid = 0, consumed = 0, hostLow = 0, hostHigh = 0;
        std::uint64_t heartbeat = 0;
        ReadHostSnapshot(
            hostPid, heartbeat, consumed, hostLow, hostHigh);

        const std::uint32_t preferred =
            (frameId - 1u) % RingSize;
        std::uint32_t selected = RingSize;
        for (std::uint32_t offset = 0; offset < RingSize; ++offset)
        {
            const std::uint32_t index =
                (preferred + offset) % RingSize;
            auto& slot = G.slots[index];

            if (slot.lastFenceValue &&
                G.fence->GetCompletedValue() < slot.lastFenceValue)
                continue;

            if (slot.frameId &&
                !FrameAtOrAfter(consumed, slot.frameId))
                continue;

            selected = index;
            break;
        }

        if (selected >= RingSize)
        {
            if (!G.firstBackpressureLogged)
            {
                G.firstBackpressureLogged = true;
                spdlog::warn(
                    "VR DX12 transport: four-slot ring is backpressured; frame export drops instead of blocking the game thread");
            }
            return false;
        }

        auto& slot = G.slots[selected];
        if (FAILED(slot.allocator->Reset()) ||
            FAILED(G.commandList->Reset(slot.allocator, nullptr)))
            return false;

        ID3D12Resource* sourceLeft = nullptr;
        ID3D12Resource* sourceRight = nullptr;
        const HRESULT leftUnwrap = G.on12->UnwrapUnderlyingResource(
            left, G.queue, __uuidof(ID3D12Resource),
            reinterpret_cast<void**>(&sourceLeft));
        if (FAILED(leftUnwrap) || !sourceLeft)
            return false;

        const HRESULT rightUnwrap = G.on12->UnwrapUnderlyingResource(
            right, G.queue, __uuidof(ID3D12Resource),
            reinterpret_cast<void**>(&sourceRight));
        if (FAILED(rightUnwrap) || !sourceRight)
        {
            G.on12->ReturnUnderlyingResource(
                left, 0, nullptr, nullptr);
            Release(sourceLeft);
            return false;
        }

        bool commandRecorded = false;
        const auto leftDesc = sourceLeft->GetDesc();
        const auto rightDesc = sourceRight->GetDesc();
        if (SameExportDesc(leftDesc, G.exportDesc) &&
            SameExportDesc(rightDesc, G.exportDesc))
        {
            std::array<D3D12_RESOURCE_BARRIER, 4> begin{
                Transition(sourceLeft,
                    D3D12_RESOURCE_STATE_COMMON,
                    D3D12_RESOURCE_STATE_COPY_SOURCE),
                Transition(sourceRight,
                    D3D12_RESOURCE_STATE_COMMON,
                    D3D12_RESOURCE_STATE_COPY_SOURCE),
                Transition(slot.left,
                    D3D12_RESOURCE_STATE_COMMON,
                    D3D12_RESOURCE_STATE_COPY_DEST),
                Transition(slot.right,
                    D3D12_RESOURCE_STATE_COMMON,
                    D3D12_RESOURCE_STATE_COPY_DEST)
            };
            G.commandList->ResourceBarrier(
                static_cast<UINT>(begin.size()), begin.data());
            G.commandList->CopyResource(slot.left, sourceLeft);
            G.commandList->CopyResource(slot.right, sourceRight);

            std::array<D3D12_RESOURCE_BARRIER, 4> end{
                Transition(sourceLeft,
                    D3D12_RESOURCE_STATE_COPY_SOURCE,
                    D3D12_RESOURCE_STATE_COMMON),
                Transition(sourceRight,
                    D3D12_RESOURCE_STATE_COPY_SOURCE,
                    D3D12_RESOURCE_STATE_COMMON),
                Transition(slot.left,
                    D3D12_RESOURCE_STATE_COPY_DEST,
                    D3D12_RESOURCE_STATE_COMMON),
                Transition(slot.right,
                    D3D12_RESOURCE_STATE_COPY_DEST,
                    D3D12_RESOURCE_STATE_COMMON)
            };
            G.commandList->ResourceBarrier(
                static_cast<UINT>(end.size()), end.data());
            commandRecorded = SUCCEEDED(G.commandList->Close());
        }

        std::uint64_t signalValue = 0;
        HRESULT queueHr = E_FAIL;
        if (commandRecorded)
        {
            ID3D12CommandList* lists[]{ G.commandList };
            G.queue->ExecuteCommandLists(1, lists);
            signalValue = ++G.nextFenceValue;
            queueHr = G.queue->Signal(G.fence, signalValue);
        }

        ID3D12Fence* fences[]{ G.fence };
        UINT64 values[]{ signalValue };
        const UINT syncCount = SUCCEEDED(queueHr) ? 1u : 0u;
        const HRESULT leftReturn = G.on12->ReturnUnderlyingResource(
            left, syncCount,
            syncCount ? values : nullptr,
            syncCount ? fences : nullptr);
        const HRESULT rightReturn = G.on12->ReturnUnderlyingResource(
            right, syncCount,
            syncCount ? values : nullptr,
            syncCount ? fences : nullptr);
        Release(sourceLeft);
        Release(sourceRight);

        if (!commandRecorded || FAILED(queueHr) ||
            FAILED(leftReturn) || FAILED(rightReturn))
        {
            spdlog::warn(
                "VR DX12 transport: publish failed record={} queue=0x{:08X} returnL=0x{:08X} returnR=0x{:08X}",
                commandRecorded,
                static_cast<unsigned>(queueHr),
                static_cast<unsigned>(leftReturn),
                static_cast<unsigned>(rightReturn));
            return false;
        }

        slot.lastFenceValue = signalValue;
        slot.frameId = frameId;

        auto& sharedSlot = G.shared->slots[selected];
        BeginWrite(&sharedSlot.sequence);
        sharedSlot.frameId = frameId;
        sharedSlot.poseSequence = poseSequence;
        sharedSlot.generation = G.generation;
        Split64(signalValue,
            sharedSlot.fenceValueLow,
            sharedSlot.fenceValueHigh);
        EndWrite(&sharedSlot.sequence);

        BeginWrite(&G.shared->publishSequence);
        G.shared->latestSlot = selected;
        G.shared->latestFrameId = frameId;
        EndWrite(&G.shared->publishSequence);

        G.lastPublishedFrame = frameId;
        if (!G.firstPublishLogged)
        {
            G.firstPublishLogged = true;
            spdlog::info(
                "VR DX12 transport: first native shared stereo frame published frame={} pose={} slot={} fence={} (no CPU GPU-wait)",
                frameId, poseSequence, selected, signalValue);
        }
        return true;
    }

    inline void Shutdown() noexcept
    {
        std::lock_guard<std::mutex> lock(Detail::G.mutex);
        Detail::G.Reset();
    }
}
