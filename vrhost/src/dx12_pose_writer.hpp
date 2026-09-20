#pragma once

#include <Windows.h>
#include <openxr/openxr.h>

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <stdexcept>

#include "vr/ipc/protocol.hpp"

namespace OutRunVRHostDX12
{
    inline XrQuaternionf NormalizeQuaternion(XrQuaternionf q) noexcept
    {
        const float l=q.x*q.x+q.y*q.y+q.z*q.z+q.w*q.w;
        if(!std::isfinite(l)||l<=1e-12f)return{0,0,0,1};
        const float i=1.0f/std::sqrt(l);
        q.x*=i;q.y*=i;q.z*=i;q.w*=i;
        return q;
    }

    inline XrQuaternionf ConjugateQuaternion(XrQuaternionf q) noexcept
    {
        q=NormalizeQuaternion(q);
        return{-q.x,-q.y,-q.z,q.w};
    }

    inline XrQuaternionf MultiplyQuaternion(
        const XrQuaternionf&aIn,const XrQuaternionf&bIn) noexcept
    {
        const auto a=NormalizeQuaternion(aIn),b=NormalizeQuaternion(bIn);
        return NormalizeQuaternion({
            a.w*b.x+a.x*b.w+a.y*b.z-a.z*b.y,
            a.w*b.y-a.x*b.z+a.y*b.w+a.z*b.x,
            a.w*b.z+a.x*b.y-a.y*b.x+a.z*b.w,
            a.w*b.w-a.x*b.x-a.y*b.y-a.z*b.z});
    }

    inline XrVector3f RotateVector(
        const XrQuaternionf& q,const XrVector3f& v) noexcept
    {
        const XrVector3f u{q.x,q.y,q.z};
        const XrVector3f t{
            2.f*(u.y*v.z-u.z*v.y),
            2.f*(u.z*v.x-u.x*v.z),
            2.f*(u.x*v.y-u.y*v.x)};
        return{
            v.x+q.w*t.x+(u.y*t.z-u.z*t.y),
            v.y+q.w*t.y+(u.z*t.x-u.x*t.z),
            v.z+q.w*t.z+(u.x*t.y-u.y*t.x)};
    }

    inline XrVector3f ToHeadLocal(
        const XrPosef& head,const XrVector3f& world) noexcept
    {
        const XrVector3f delta{
            world.x-head.position.x,
            world.y-head.position.y,
            world.z-head.position.z};
        return RotateVector(ConjugateQuaternion(head.orientation),delta);
    }

    inline XrQuaternionf ToHeadLocalOrientation(
        const XrPosef& head,const XrPosef& eye) noexcept
    {
        return MultiplyQuaternion(
            ConjugateQuaternion(head.orientation),eye.orientation);
    }

    inline std::uint32_t FloatBits(float value) noexcept
    {
        std::uint32_t out{};
        std::memcpy(&out,&value,sizeof(out));
        return out;
    }

    inline std::int16_t PackSnorm16(float value) noexcept
    {
        const float c=std::clamp(value,-1.0f,1.0f);
        return static_cast<std::int16_t>(std::lround(c*32767.0f));
    }

    inline void StorePackedEyeOrientations(
        char runtimeName[64],const XrQuaternionf eyeOrientation[2]) noexcept
    {
        std::int16_t packed[8]{};
        for(int eye=0;eye<2;++eye)
        {
            const auto q=NormalizeQuaternion(eyeOrientation[eye]);
            packed[eye*4+0]=PackSnorm16(q.x);
            packed[eye*4+1]=PackSnorm16(q.y);
            packed[eye*4+2]=PackSnorm16(q.z);
            packed[eye*4+3]=PackSnorm16(q.w);
        }
        std::memcpy(
            runtimeName+OutRunVR::PackedEyeOrientationOffset,
            packed,sizeof(packed));
    }

    class PoseWriter
    {
    public:
        explicit PoseWriter(const LUID& adapterLuid)
            : adapterLuid_(adapterLuid)
        {
            mapping_=CreateFileMappingW(
                INVALID_HANDLE_VALUE,nullptr,PAGE_READWRITE,0,
                static_cast<DWORD>(sizeof(OutRunVR::SharedPoseState)),
                OutRunVR::SharedMemoryName);
            if(!mapping_)throw std::runtime_error(
                "DX12 host: CreateFileMappingW pose failed");
            const bool existed=GetLastError()==ERROR_ALREADY_EXISTS;
            state_=static_cast<OutRunVR::SharedPoseState*>(
                MapViewOfFile(mapping_,FILE_MAP_ALL_ACCESS,0,0,
                    sizeof(OutRunVR::SharedPoseState)));
            if(!state_)throw std::runtime_error(
                "DX12 host: MapViewOfFile pose failed");

            if(!existed||state_->magic!=OutRunVR::SharedMagic||
                state_->protocolVersion!=OutRunVR::SharedProtocolVersion||
                state_->structSize!=sizeof(*state_))
            {
                std::memset(state_,0,sizeof(*state_));
                state_->protocolVersion=OutRunVR::SharedProtocolVersion;
                state_->structSize=sizeof(*state_);
                MemoryBarrier();
                state_->magic=OutRunVR::SharedMagic;
            }

            Begin();
            state_->hostPid=GetCurrentProcessId();
            state_->hostAdapterLuidLow=adapterLuid_.LowPart;
            state_->hostAdapterLuidHigh=
                static_cast<std::uint32_t>(adapterLuid_.HighPart);
            End();
        }

        PoseWriter(const PoseWriter&)=delete;
        PoseWriter& operator=(const PoseWriter&)=delete;

        ~PoseWriter()
        {
            if(state_)
            {
                if(state_->hostPid==GetCurrentProcessId())
                {
                    Begin();
                    state_->flags=0;
                    state_->hostPid=0;
                    End();
                }
                UnmapViewOfFile(state_);
            }
            if(mapping_)CloseHandle(mapping_);
        }

        std::uint32_t Write(
            const XrSpaceLocation& head,
            const std::array<XrView,2>& views,
            std::uint32_t viewCount,
            const std::array<XrViewConfigurationView,2>& configs,
            XrSessionState sessionState,
            XrViewStateFlags viewFlags,
            bool shouldRender,
            const char* runtimeName)
        {
            LARGE_INTEGER qpc{};
            QueryPerformanceCounter(&qpc);

            std::uint32_t flags=OutRunVR::HostAlive|
                OutRunVR::HostAdapterLuidValid|
                OutRunVR::HostDirectGpuTransport;
            if(head.locationFlags&XR_SPACE_LOCATION_ORIENTATION_VALID_BIT)
                flags|=OutRunVR::OrientationValid;
            if(head.locationFlags&XR_SPACE_LOCATION_POSITION_VALID_BIT)
                flags|=OutRunVR::PositionValid;
            if(sessionState==XR_SESSION_STATE_VISIBLE||
               sessionState==XR_SESSION_STATE_FOCUSED)
                flags|=OutRunVR::SessionVisible;
            if(sessionState==XR_SESSION_STATE_FOCUSED)
                flags|=OutRunVR::SessionFocused;
            if(shouldRender)flags|=OutRunVR::HostShouldRender;

            const XrViewStateFlags required=
                XR_VIEW_STATE_ORIENTATION_VALID_BIT|
                XR_VIEW_STATE_POSITION_VALID_BIT;
            const bool stereoValid=viewCount>=2&&
                (viewFlags&required)==required;
            if(stereoValid)
                flags|=OutRunVR::StereoViewsValid|
                    OutRunVR::StereoEyeOrientationValid|
                    OutRunVR::HostDirectGpuReady;

            Begin();
            state_->hostPid=GetCurrentProcessId();
            state_->flags=flags;
            ++state_->heartbeat;
            state_->sampleQpc=qpc.QuadPart;
            state_->orientation[0]=head.pose.orientation.x;
            state_->orientation[1]=head.pose.orientation.y;
            state_->orientation[2]=head.pose.orientation.z;
            state_->orientation[3]=head.pose.orientation.w;
            state_->position[0]=head.pose.position.x;
            state_->position[1]=head.pose.position.y;
            state_->position[2]=head.pose.position.z;
            state_->reserved[OutRunVR::HostReferenceSpaceGenerationIndex]=
                referenceGeneration_;

            for(std::uint32_t eye=0;eye<2;++eye)
            {
                state_->recommendedWidth[eye]=
                    configs[eye].recommendedImageRectWidth;
                state_->recommendedHeight[eye]=
                    configs[eye].recommendedImageRectHeight;
                if(eye<viewCount)
                {
                    state_->eyeFov[eye]={
                        views[eye].fov.angleLeft,
                        views[eye].fov.angleRight,
                        views[eye].fov.angleUp,
                        views[eye].fov.angleDown};
                }
            }

            std::memset(state_->runtimeName,0,sizeof(state_->runtimeName));
            strncpy_s(
                state_->runtimeName,
                OutRunVR::PackedEyeOrientationOffset,
                runtimeName?runtimeName:"OpenXR-D3D12",
                _TRUNCATE);

            if(stereoValid)
            {
                const XrVector3f left=ToHeadLocal(
                    head.pose,views[0].pose.position);
                const XrVector3f right=ToHeadLocal(
                    head.pose,views[1].pose.position);
                const XrQuaternionf eyeOrientation[2]{
                    ToHeadLocalOrientation(head.pose,views[0].pose),
                    ToHeadLocalOrientation(head.pose,views[1].pose)};
                StorePackedEyeOrientations(
                    state_->runtimeName,eyeOrientation);

                state_->reserved[OutRunVR::HostEyeOffsetLeftXIndex]=FloatBits(left.x);
                state_->reserved[OutRunVR::HostEyeOffsetLeftYIndex]=FloatBits(left.y);
                state_->reserved[OutRunVR::HostEyeOffsetLeftZIndex]=FloatBits(left.z);
                state_->reserved[OutRunVR::HostEyeOffsetRightXIndex]=FloatBits(right.x);
                state_->reserved[OutRunVR::HostEyeOffsetRightYIndex]=FloatBits(right.y);
                state_->reserved[OutRunVR::HostEyeOffsetRightZIndex]=FloatBits(right.z);
            }

            return End();
        }

        void ReferenceSpaceChanged() noexcept
        {
            if(++referenceGeneration_==0)referenceGeneration_=1;
        }

    private:
        void Begin() noexcept
        {
            LONG s=InterlockedIncrement(
                reinterpret_cast<volatile LONG*>(&state_->sequence));
            if((s&1)==0)
                InterlockedIncrement(
                    reinterpret_cast<volatile LONG*>(&state_->sequence));
            MemoryBarrier();
        }

        std::uint32_t End() noexcept
        {
            MemoryBarrier();
            LONG s=InterlockedIncrement(
                reinterpret_cast<volatile LONG*>(&state_->sequence));
            if(s&1)
                s=InterlockedIncrement(
                    reinterpret_cast<volatile LONG*>(&state_->sequence));
            return static_cast<std::uint32_t>(s);
        }

        HANDLE mapping_{};
        OutRunVR::SharedPoseState* state_{};
        LUID adapterLuid_{};
        std::uint32_t referenceGeneration_{1};
    };
}
