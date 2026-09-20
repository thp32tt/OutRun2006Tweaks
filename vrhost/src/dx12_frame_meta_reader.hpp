#pragma once

#include <Windows.h>
#include <openxr/openxr.h>

#include <array>
#include <cstdint>
#include <cstring>

#include "vr/ipc/protocol.hpp"

namespace OutRunVRHostDX12
{
    class RenderFrameMetaReader
    {
    public:
        RenderFrameMetaReader()
        {
            mapping_=CreateFileMappingW(
                INVALID_HANDLE_VALUE,nullptr,PAGE_READWRITE,0,
                static_cast<DWORD>(sizeof(OutRunVR::SharedRenderFrameRing)),
                OutRunVR::RenderFrameMemoryName);
            if(!mapping_)return;

            const bool existed=GetLastError()==ERROR_ALREADY_EXISTS;
            ring_=static_cast<OutRunVR::SharedRenderFrameRing*>(
                MapViewOfFile(mapping_,FILE_MAP_ALL_ACCESS,0,0,
                    sizeof(OutRunVR::SharedRenderFrameRing)));
            if(!ring_)return;

            if(!existed||!RingValid())
            {
                std::memset(ring_,0,sizeof(*ring_));
                ring_->protocolVersion=OutRunVR::RenderFrameProtocolVersion;
                ring_->structSize=sizeof(*ring_);
                ring_->slotCount=OutRunVR::RenderFrameRingSize;
                for(auto& slot:ring_->slots)
                {
                    slot.protocolVersion=OutRunVR::RenderFrameProtocolVersion;
                    slot.structSize=sizeof(slot);
                    slot.magic=OutRunVR::RenderFrameMagic;
                }
                MemoryBarrier();
                ring_->magic=OutRunVR::RenderFrameMagic;
            }
        }

        RenderFrameMetaReader(const RenderFrameMetaReader&)=delete;
        RenderFrameMetaReader& operator=(const RenderFrameMetaReader&)=delete;

        ~RenderFrameMetaReader()
        {
            if(ring_)UnmapViewOfFile(ring_);
            if(mapping_)CloseHandle(mapping_);
        }

        bool ReadFrame(std::uint32_t frameId,
            std::uint32_t expectedPoseSequence,
            OutRunVR::SharedRenderFrameState& out) const noexcept
        {
            out={};
            if(!frameId||!RingValid())return false;

            for(int ringAttempt=0;ringAttempt<8;++ringAttempt)
            {
                const std::uint32_t publishBefore=ring_->publishSequence;
                if(publishBefore&1u)continue;
                MemoryBarrier();

                for(std::uint32_t i=0;i<OutRunVR::RenderFrameRingSize;++i)
                {
                    OutRunVR::SharedRenderFrameState candidate{};
                    if(!ReadSlot(i,candidate))continue;
                    if(candidate.frameId!=frameId)continue;
                    if(!FrameUsable(candidate,expectedPoseSequence))continue;

                    MemoryBarrier();
                    const std::uint32_t publishAfter=ring_->publishSequence;
                    if(publishBefore==publishAfter&&!(publishAfter&1u))
                    {
                        out=candidate;
                        return true;
                    }
                    break;
                }
            }
            return false;
        }

        static bool ToXrViews(
            const OutRunVR::SharedRenderFrameState& frame,
            std::array<XrView,2>& views) noexcept
        {
            if(!FrameUsable(frame,frame.sourcePoseSequence))
                return false;
            for(int eye=0;eye<2;++eye)
            {
                views[eye]={XR_TYPE_VIEW};
                views[eye].pose.orientation={
                    frame.eye[eye].orientation[0],
                    frame.eye[eye].orientation[1],
                    frame.eye[eye].orientation[2],
                    frame.eye[eye].orientation[3]};
                views[eye].pose.position={
                    frame.eye[eye].position[0],
                    frame.eye[eye].position[1],
                    frame.eye[eye].position[2]};
                views[eye].fov={
                    frame.eye[eye].fov.angleLeft,
                    frame.eye[eye].fov.angleRight,
                    frame.eye[eye].fov.angleUp,
                    frame.eye[eye].fov.angleDown};
            }
            return true;
        }

    private:
        bool RingValid() const noexcept
        {
            return ring_&&
                ring_->magic==OutRunVR::RenderFrameMagic&&
                ring_->protocolVersion==OutRunVR::RenderFrameProtocolVersion&&
                ring_->structSize==sizeof(*ring_)&&
                ring_->slotCount==OutRunVR::RenderFrameRingSize;
        }

        bool ReadSlot(std::uint32_t index,
            OutRunVR::SharedRenderFrameState& out) const noexcept
        {
            if(!RingValid()||index>=OutRunVR::RenderFrameRingSize)
                return false;
            const auto& slot=ring_->slots[index];
            for(int attempt=0;attempt<8;++attempt)
            {
                const std::uint32_t before=slot.sequence;
                if(before&1u)continue;
                MemoryBarrier();
                std::memcpy(&out,&slot,sizeof(out));
                MemoryBarrier();
                const std::uint32_t after=slot.sequence;
                if(before==after&&!(after&1u)&&
                    out.magic==OutRunVR::RenderFrameMagic&&
                    out.protocolVersion==OutRunVR::RenderFrameProtocolVersion&&
                    out.structSize==sizeof(out))
                    return true;
            }
            return false;
        }

        static bool FrameUsable(
            const OutRunVR::SharedRenderFrameState& frame,
            std::uint32_t expectedPoseSequence) noexcept
        {
            const std::uint32_t required=
                OutRunVR::RenderFrameStereoComplete|
                OutRunVR::RenderFrameWorldStereo|
                OutRunVR::RenderFrameDrawDuplicated|
                OutRunVR::RenderFrameEffectivePoseValid;
            if(frame.magic!=OutRunVR::RenderFrameMagic||
                frame.protocolVersion!=OutRunVR::RenderFrameProtocolVersion||
                frame.structSize!=sizeof(frame)||
                frame.state!=OutRunVR::StereoSbsActive||
                (frame.flags&OutRunVR::RenderFramePresentInFlight)!=0||
                (frame.flags&required)!=required||
                !frame.frameId||!frame.sourcePoseSequence)
                return false;
            if(expectedPoseSequence&&
                frame.sourcePoseSequence!=expectedPoseSequence)
                return false;
            return true;
        }

        HANDLE mapping_{};
        OutRunVR::SharedRenderFrameRing* ring_{};
    };
}
