#pragma once
// Game-side opt-in native D3D9Ex render-buffer sizing. Must be evaluated at
// CreateDevice or a GAME-INITIATED ResetEx, never from Present or inside a scene.
#include <Windows.h>
#include <d3d9.h>
#include "vr/ipc/protocol.hpp"
#include "vr/ipc/native_geometry_backbuffer.hpp"
namespace OutRunVR::NativeGeometry
{
    struct Decision
    {
        bool applied{};
        EyeExtent::Size requested{}, allocated{}, xrEye{};
    };
    inline bool OptIn() noexcept
    {
        char value[8]{};
        return GetEnvironmentVariableA("OUTRUN_VR_NATIVE_EYE_GEOMETRY",
            value, sizeof(value)) == 1 && value[0] == '1';
    }
    inline EyeExtent::Size ReadHostAllocatedEyeSize() noexcept
    {
        // READ ONLY: pose mapping belongs to OpenXR x64 host. The game must not
        // create/own/overwrite this mapping from a D3D9 device hook.
        HANDLE mapping = OpenFileMappingW(FILE_MAP_READ, FALSE,
            OutRunVR::SharedMemoryName);
        if (!mapping) return {};
        auto* state = static_cast<const OutRunVR::SharedPoseState*>(
            MapViewOfFile(mapping, FILE_MAP_READ, 0, 0,
                sizeof(OutRunVR::SharedPoseState)));
        EyeExtent::Size size{};
        if (state && state->magic == OutRunVR::SharedMagic &&
            state->protocolVersion == OutRunVR::SharedProtocolVersion &&
            state->structSize == sizeof(OutRunVR::SharedPoseState))
        {
            for (int i=0; i<4; ++i)
            {
                auto before = state->sequence;
                if (before & 1u) continue;
                MemoryBarrier();
                auto flags=state->flags, pid=state->hostPid;
                auto w0=state->recommendedWidth[0],w1=state->recommendedWidth[1];
                auto h0=state->recommendedHeight[0],h1=state->recommendedHeight[1];
                MemoryBarrier();
                auto after=state->sequence;
                if (before == after && !(after & 1u))
                {
                    if (pid && (flags & OutRunVR::HostAlive) &&
                        (flags & OutRunVR::HostDirectGpuTransport) &&
                        w0==w1 && h0==h1) size={w0,h0};
                    break;
                }
            }
        }
        if (state) UnmapViewOfFile(state);
        CloseHandle(mapping);
        return size;
    }
    inline Decision TryApplyPresentation(D3DPRESENT_PARAMETERS* params,
        const D3DCAPS9& caps) noexcept
    {
        Decision out{};
        if (!params || !OptIn() || !params->Windowed ||
            !params->BackBufferWidth || !params->BackBufferHeight)
            return out;
        out.requested={params->BackBufferWidth,params->BackBufferHeight};
        out.xrEye=ReadHostAllocatedEyeSize();
        auto computed=OutRunVR::EyeExtent::ResolveNativeBackbuffer(
            out.requested,out.xrEye,
            {caps.MaxTextureWidth,caps.MaxTextureHeight},true);
        if (!computed.changed) return out;
        params->BackBufferWidth=computed.dimensions.width;
        params->BackBufferHeight=computed.dimensions.height;
        out.allocated=computed.dimensions;
        out.applied=true;
        return out;
    }
}
