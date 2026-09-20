#pragma once

#include <Windows.h>
#include <d3d12.h>

#include <array>
#include <cstdint>
#include <cstring>
#include <cwchar>
#include <iostream>
#include <stdexcept>

#include "vr/ipc/d3d12_transport.hpp"

namespace OutRunVRHostDX12
{
    class TransportConsumer
    {
    public:
        struct Frame
        {
            std::uint32_t frameId{};
            std::uint32_t poseSequence{};
            std::uint32_t generation{};
            std::uint32_t slot{};
            std::uint32_t width{};
            std::uint32_t height{};
            DXGI_FORMAT format{DXGI_FORMAT_UNKNOWN};
            std::uint64_t producerFenceValue{};
            ID3D12Resource* left{};
            ID3D12Resource* right{};
            ID3D12Fence* producerFence{};
        };

        explicit TransportConsumer(const LUID& hostLuid)
            : hostLuid_(hostLuid)
        {
            using namespace OutRunVR::D3D12Transport;
            mapping_=CreateFileMappingW(
                INVALID_HANDLE_VALUE,nullptr,PAGE_READWRITE,0,
                static_cast<DWORD>(sizeof(SharedState)),MappingName);
            if(!mapping_)throw std::runtime_error(
                "DX12 host: CreateFileMappingW transport failed");

            const bool existed=GetLastError()==ERROR_ALREADY_EXISTS;
            state_=static_cast<SharedState*>(
                MapViewOfFile(mapping_,FILE_MAP_ALL_ACCESS,0,0,
                    sizeof(SharedState)));
            if(!state_)throw std::runtime_error(
                "DX12 host: MapViewOfFile transport failed");

            if(!existed||state_->magic!=Magic||
                state_->version!=Version||
                state_->structSize!=sizeof(SharedState))
            {
                std::memset(state_,0,sizeof(*state_));
                state_->magic=Magic;
                state_->version=Version;
                state_->structSize=sizeof(SharedState);
                state_->ringSize=RingSize;
            }
            Touch();
        }

        TransportConsumer(const TransportConsumer&)=delete;
        TransportConsumer& operator=(const TransportConsumer&)=delete;

        ~TransportConsumer()
        {
            ResetObjects();
            if(state_)
            {
                if(state_->hostPid==GetCurrentProcessId())
                {
                    BeginHost();
                    state_->hostPid=0;
                    state_->hostHeartbeatLow=0;
                    state_->hostHeartbeatHigh=0;
                    EndHost();
                }
                UnmapViewOfFile(state_);
            }
            if(mapping_)CloseHandle(mapping_);
        }

        void Touch() noexcept
        {
            if(!state_)return;
            const std::uint64_t now=GetTickCount64();
            BeginHost();
            state_->hostPid=GetCurrentProcessId();
            state_->hostAdapterLuidLow=hostLuid_.LowPart;
            state_->hostAdapterLuidHigh=
                static_cast<std::uint32_t>(hostLuid_.HighPart);
            OutRunVR::D3D12Transport::Split64(
                now,state_->hostHeartbeatLow,state_->hostHeartbeatHigh);
            EndHost();
        }

        bool ProducerReady() const noexcept
        {
            using namespace OutRunVR::D3D12Transport;
            if(!state_||state_->magic!=Magic||state_->version!=Version||
                state_->structSize!=sizeof(SharedState)||!state_->clientPid)
                return false;
            return state_->adapterLuidLow==hostLuid_.LowPart&&
                state_->adapterLuidHigh==
                    static_cast<std::uint32_t>(hostLuid_.HighPart)&&
                state_->generation!=0&&state_->width&&state_->height&&
                state_->producerFenceName[0]!=L'\0';
        }

        bool AcquireLatest(
            ID3D12Device* device,ID3D12CommandQueue* queue,Frame& out)
        {
            using namespace OutRunVR::D3D12Transport;
            out={};
            Touch();
            if(!device||!queue||!ProducerReady())return false;

            std::uint32_t latestSlot=0;
            std::uint32_t latestFrame=0;
            std::uint32_t generation=0;
            std::uint32_t width=0,height=0,format=0;
            wchar_t fenceName[NameChars]{};

            bool headerRead=false;
            for(int attempt=0;attempt<6;++attempt)
            {
                const LONG before=state_->publishSequence;
                if(before&1)continue;
                const LONG producerBefore=state_->producerSequence;
                if(producerBefore&1)continue;
                MemoryBarrier();
                latestSlot=state_->latestSlot;
                latestFrame=state_->latestFrameId;
                generation=state_->generation;
                width=state_->width;
                height=state_->height;
                format=state_->format;
                wcsncpy_s(fenceName,state_->producerFenceName,_TRUNCATE);
                MemoryBarrier();
                const LONG producerAfter=state_->producerSequence;
                const LONG after=state_->publishSequence;
                if(before==after&&!(after&1)&&
                    producerBefore==producerAfter&&!(producerAfter&1))
                {
                    headerRead=true;
                    break;
                }
            }
            if(!headerRead||latestSlot>=RingSize||!latestFrame||
                !generation||!width||!height||!fenceName[0])
                return false;

            if(!EnsureGeneration(device,generation,fenceName))
                return false;

            auto& sharedSlot=state_->slots[latestSlot];
            std::uint32_t frameId=0,pose=0,slotGeneration=0;
            std::uint64_t producerFenceValue=0;
            wchar_t leftName[NameChars]{};
            wchar_t rightName[NameChars]{};
            bool slotRead=false;
            for(int attempt=0;attempt<6;++attempt)
            {
                const LONG before=sharedSlot.sequence;
                if(before&1)continue;
                MemoryBarrier();
                frameId=sharedSlot.frameId;
                pose=sharedSlot.poseSequence;
                slotGeneration=sharedSlot.generation;
                producerFenceValue=Join64(
                    sharedSlot.fenceValueLow,
                    sharedSlot.fenceValueHigh);
                wcsncpy_s(leftName,sharedSlot.leftResourceName,_TRUNCATE);
                wcsncpy_s(rightName,sharedSlot.rightResourceName,_TRUNCATE);
                MemoryBarrier();
                const LONG after=sharedSlot.sequence;
                if(before==after&&!(after&1))
                {
                    slotRead=true;
                    break;
                }
            }
            if(!slotRead||frameId!=latestFrame||
                slotGeneration!=generation||!producerFenceValue||
                !leftName[0]||!rightName[0])
                return false;

            auto& cache=slots_[latestSlot];
            if(cache.generation!=generation||
                std::wcscmp(cache.leftName,leftName)!=0||
                std::wcscmp(cache.rightName,rightName)!=0)
            {
                cache.Reset();
                if(!OpenNamed<ID3D12Resource>(
                        device,leftName,&cache.left)||
                    !OpenNamed<ID3D12Resource>(
                        device,rightName,&cache.right))
                {
                    cache.Reset();
                    return false;
                }
                cache.generation=generation;
                wcsncpy_s(cache.leftName,leftName,_TRUNCATE);
                wcsncpy_s(cache.rightName,rightName,_TRUNCATE);
            }

            if(FAILED(queue->Wait(producerFence_,producerFenceValue)))
                return false;

            out.frameId=frameId;
            out.poseSequence=pose;
            out.generation=generation;
            out.slot=latestSlot;
            out.width=width;
            out.height=height;
            out.format=static_cast<DXGI_FORMAT>(format);
            out.producerFenceValue=producerFenceValue;
            out.left=cache.left;
            out.right=cache.right;
            out.producerFence=producerFence_;
            return true;
        }

        void Ack(std::uint32_t frameId) noexcept
        {
            if(!state_||!frameId)return;
            const std::uint64_t now=GetTickCount64();
            BeginHost();
            if(OutRunVR::D3D12Transport::FrameAtOrAfter(
                    frameId,state_->hostConsumedFrameId))
                state_->hostConsumedFrameId=frameId;
            state_->hostPid=GetCurrentProcessId();
            state_->hostAdapterLuidLow=hostLuid_.LowPart;
            state_->hostAdapterLuidHigh=
                static_cast<std::uint32_t>(hostLuid_.HighPart);
            OutRunVR::D3D12Transport::Split64(
                now,state_->hostHeartbeatLow,state_->hostHeartbeatHigh);
            EndHost();
        }

        std::uint32_t ConsumedFrame() const noexcept
        {
            return state_?state_->hostConsumedFrameId:0;
        }

    private:
        template<typename T>
        static void Release(T*& p) noexcept
        {
            if(p){p->Release();p=nullptr;}
        }

        struct SlotCache
        {
            ID3D12Resource* left{};
            ID3D12Resource* right{};
            std::uint32_t generation{};
            wchar_t leftName[OutRunVR::D3D12Transport::NameChars]{};
            wchar_t rightName[OutRunVR::D3D12Transport::NameChars]{};
            void Reset() noexcept
            {
                Release(left);Release(right);
                generation=0;
                leftName[0]=L'\0';rightName[0]=L'\0';
            }
        };

        template<typename T>
        static bool OpenNamed(
            ID3D12Device* device,const wchar_t* name,T** out)
        {
            if(!device||!name||!*name||!out)return false;
            *out=nullptr;
            HANDLE handle=nullptr;
            HRESULT hr=device->OpenSharedHandleByName(
                name,GENERIC_ALL,&handle);
            if(FAILED(hr)||!handle)return false;
            hr=device->OpenSharedHandle(
                handle,__uuidof(T),
                reinterpret_cast<void**>(out));
            CloseHandle(handle);
            return SUCCEEDED(hr)&&*out;
        }

        bool EnsureGeneration(
            ID3D12Device* device,std::uint32_t generation,
            const wchar_t* fenceName)
        {
            if(openGeneration_==generation&&producerFence_&&
                std::wcscmp(openFenceName_,fenceName)==0)
                return true;
            ResetObjects();
            if(!OpenNamed<ID3D12Fence>(
                    device,fenceName,&producerFence_))
                return false;
            openGeneration_=generation;
            wcsncpy_s(openFenceName_,fenceName,_TRUNCATE);
            std::cout<<"DX12 transport generation "<<generation
                <<" opened (named resources + shared fence).\\n";
            return true;
        }

        void ResetObjects() noexcept
        {
            for(auto& slot:slots_)slot.Reset();
            Release(producerFence_);
            openGeneration_=0;
            openFenceName_[0]=L'\0';
        }

        void BeginHost() noexcept
        {
            LONG s=InterlockedIncrement(&state_->hostSequence);
            if((s&1)==0)InterlockedIncrement(&state_->hostSequence);
            MemoryBarrier();
        }

        void EndHost() noexcept
        {
            MemoryBarrier();
            LONG s=InterlockedIncrement(&state_->hostSequence);
            if(s&1)InterlockedIncrement(&state_->hostSequence);
        }

        HANDLE mapping_{};
        OutRunVR::D3D12Transport::SharedState* state_{};
        LUID hostLuid_{};
        ID3D12Fence* producerFence_{};
        std::uint32_t openGeneration_{};
        wchar_t openFenceName_[
            OutRunVR::D3D12Transport::NameChars]{};
        std::array<SlotCache,
            OutRunVR::D3D12Transport::RingSize> slots_{};
    };
}
