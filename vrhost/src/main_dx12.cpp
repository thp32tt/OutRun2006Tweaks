#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#define XR_USE_PLATFORM_WIN32
#define XR_USE_GRAPHICS_API_D3D12

#include <Windows.h>
#include <d3d12.h>
#include <dxgi1_6.h>
#include <d3dcompiler.h>
#include <openxr/openxr.h>
#include <openxr/openxr_platform.h>

#include <algorithm>
#include <array>
#include <atomic>
#include <cstdint>
#include <cstring>
#include <deque>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
#include <utility>

#include "dx12_pose_writer.hpp"
#include "dx12_host_log.hpp"
#include "dx12_frame_meta_reader.hpp"
#include "dx12_transport_consumer.hpp"

namespace
{
    template<typename T>
    void Release(T*& p) noexcept
    {
        if(p){p->Release();p=nullptr;}
    }

    void CheckHr(HRESULT hr,const char* what)
    {
        if(FAILED(hr))
        {
            char msg[256]{};
            sprintf_s(msg,"%s failed hr=0x%08X",what,
                static_cast<unsigned>(hr));
            throw std::runtime_error(msg);
        }
    }

    void CheckXr(XrResult result,const char* what)
    {
        if(XR_FAILED(result))
        {
            char msg[256]{};
            sprintf_s(msg,"%s failed XrResult=%d",what,
                static_cast<int>(result));
            throw std::runtime_error(msg);
        }
    }

    bool SameLuid(const LUID&a,const LUID&b) noexcept
    {
        return a.LowPart==b.LowPart&&a.HighPart==b.HighPart;
    }

    IDXGIAdapter1* FindAdapter(const LUID& wanted)
    {
        IDXGIFactory6* factory=nullptr;
        CheckHr(CreateDXGIFactory1(
            __uuidof(IDXGIFactory6),
            reinterpret_cast<void**>(&factory)),
            "CreateDXGIFactory1");

        IDXGIAdapter1* found=nullptr;
        for(UINT i=0;;++i)
        {
            IDXGIAdapter1* adapter=nullptr;
            const HRESULT hr=factory->EnumAdapters1(i,&adapter);
            if(hr==DXGI_ERROR_NOT_FOUND)break;
            if(FAILED(hr))break;
            DXGI_ADAPTER_DESC1 desc{};
            adapter->GetDesc1(&desc);
            if(SameLuid(desc.AdapterLuid,wanted))
            {
                found=adapter;
                break;
            }
            adapter->Release();
        }
        factory->Release();
        if(!found)throw std::runtime_error(
            "OpenXR-required D3D12 adapter LUID was not found");
        return found;
    }

    struct D3D12Objects
    {
        ID3D12Device* device{};
        ID3D12CommandQueue* queue{};
        D3D12_VIEW_INSTANCING_TIER viewInstancingTier{
            D3D12_VIEW_INSTANCING_TIER_NOT_SUPPORTED};
        bool vsRtArrayIndexWithoutGs{};
        D3D_SHADER_MODEL highestShaderModel{D3D_SHADER_MODEL_5_1};
        bool nativeViewInstancingCandidate{};

        D3D12Objects()=default;
        D3D12Objects(const D3D12Objects&)=delete;
        D3D12Objects& operator=(const D3D12Objects&)=delete;
        D3D12Objects(D3D12Objects&& other) noexcept
            : device(std::exchange(other.device,nullptr)),
              queue(std::exchange(other.queue,nullptr)),
              viewInstancingTier(other.viewInstancingTier),
              vsRtArrayIndexWithoutGs(other.vsRtArrayIndexWithoutGs),
              highestShaderModel(other.highestShaderModel),
              nativeViewInstancingCandidate(other.nativeViewInstancingCandidate) {}
        D3D12Objects& operator=(D3D12Objects&& other) noexcept
        {
            if(this!=&other)
            {
                Release(queue);Release(device);
                device=std::exchange(other.device,nullptr);
                queue=std::exchange(other.queue,nullptr);
                viewInstancingTier=other.viewInstancingTier;
                vsRtArrayIndexWithoutGs=other.vsRtArrayIndexWithoutGs;
                highestShaderModel=other.highestShaderModel;
                nativeViewInstancingCandidate=other.nativeViewInstancingCandidate;
            }
            return *this;
        }
        ~D3D12Objects()
        {
            Release(queue);
            Release(device);
        }
    };

    D3D12Objects CreateD3D12(
        const XrGraphicsRequirementsD3D12KHR& req)
    {
        D3D12Objects out;
        IDXGIAdapter1* adapter=FindAdapter(req.adapterLuid);
        CheckHr(D3D12CreateDevice(
            adapter,req.minFeatureLevel,
            __uuidof(ID3D12Device),
            reinterpret_cast<void**>(&out.device)),
            "D3D12CreateDevice");
        adapter->Release();

        D3D12_COMMAND_QUEUE_DESC q{};
        q.Type=D3D12_COMMAND_LIST_TYPE_DIRECT;
        q.Priority=D3D12_COMMAND_QUEUE_PRIORITY_NORMAL;
        q.Flags=D3D12_COMMAND_QUEUE_FLAG_NONE;
        CheckHr(out.device->CreateCommandQueue(
            &q,__uuidof(ID3D12CommandQueue),
            reinterpret_cast<void**>(&out.queue)),
            "CreateCommandQueue");

        D3D12_FEATURE_DATA_D3D12_OPTIONS3 opt3{};
        if(SUCCEEDED(out.device->CheckFeatureSupport(
            D3D12_FEATURE_D3D12_OPTIONS3,
            &opt3,sizeof(opt3))))
            out.viewInstancingTier=opt3.ViewInstancingTier;

        D3D12_FEATURE_DATA_D3D12_OPTIONS opt{};
        if(SUCCEEDED(out.device->CheckFeatureSupport(
            D3D12_FEATURE_D3D12_OPTIONS,
            &opt,sizeof(opt))))
            out.vsRtArrayIndexWithoutGs=
                opt.VPAndRTArrayIndexFromAnyShaderFeedingRasterizerSupportedWithoutGSEmulation!=FALSE;

        D3D12_FEATURE_DATA_SHADER_MODEL shaderModel{
            D3D_SHADER_MODEL_6_1};
        if(SUCCEEDED(out.device->CheckFeatureSupport(
                D3D12_FEATURE_SHADER_MODEL,
                &shaderModel,sizeof(shaderModel))))
            out.highestShaderModel=shaderModel.HighestShaderModel;
        out.nativeViewInstancingCandidate=
            out.viewInstancingTier!=D3D12_VIEW_INSTANCING_TIER_NOT_SUPPORTED&&
            out.highestShaderModel>=D3D_SHADER_MODEL_6_1;

        const LUID luid=out.device->GetAdapterLuid();
        std::cout<<"D3D12 device ready adapterLuid="
            <<std::hex<<static_cast<std::uint32_t>(luid.HighPart)
            <<":"<<luid.LowPart<<std::dec
            <<" featureLevel>=0x"<<std::hex
            <<static_cast<unsigned>(req.minFeatureLevel)<<std::dec
            <<" viewInstancingTier="
            <<static_cast<unsigned>(out.viewInstancingTier)
            <<" VS-RT-array-index="
            <<(out.vsRtArrayIndexWithoutGs?"yes":"no")
            <<" shaderModel=0x"<<std::hex
            <<static_cast<unsigned>(out.highestShaderModel)<<std::dec
            <<" geometryViewInstancingCandidate="
            <<(out.nativeViewInstancingCandidate?"yes":"no")<<"\n";
        return out;
    }

    bool HasExtension(const char* name)
    {
        std::uint32_t count=0;
        CheckXr(xrEnumerateInstanceExtensionProperties(
            nullptr,0,&count,nullptr),
            "xrEnumerateInstanceExtensionProperties(count)");
        std::vector<XrExtensionProperties> props(
            count,{XR_TYPE_EXTENSION_PROPERTIES});
        CheckXr(xrEnumerateInstanceExtensionProperties(
            nullptr,count,&count,props.data()),
            "xrEnumerateInstanceExtensionProperties");
        for(const auto& p:props)
            if(std::strcmp(p.extensionName,name)==0)
                return true;
        return false;
    }

    struct XrObjects
    {
        XrInstance instance{XR_NULL_HANDLE};
        XrSystemId system{0};
        XrSession session{XR_NULL_HANDLE};
        XrSpace localSpace{XR_NULL_HANDLE};
        XrSpace viewSpace{XR_NULL_HANDLE};
        XrSessionState sessionState{XR_SESSION_STATE_UNKNOWN};
        bool sessionRunning{};
        bool exitRequested{};
        std::string runtimeName{"OpenXR-D3D12"};

        XrObjects()=default;
        XrObjects(const XrObjects&)=delete;
        XrObjects& operator=(const XrObjects&)=delete;
        XrObjects(XrObjects&& other) noexcept
            : instance(std::exchange(other.instance,XR_NULL_HANDLE)),
              system(std::exchange(other.system,0)),
              session(std::exchange(other.session,XR_NULL_HANDLE)),
              localSpace(std::exchange(other.localSpace,XR_NULL_HANDLE)),
              viewSpace(std::exchange(other.viewSpace,XR_NULL_HANDLE)),
              sessionState(other.sessionState),
              sessionRunning(other.sessionRunning),
              exitRequested(other.exitRequested),
              runtimeName(std::move(other.runtimeName)) {}
        XrObjects& operator=(XrObjects&& other) noexcept
        {
            if(this!=&other)
            {
                Destroy();
                instance=std::exchange(other.instance,XR_NULL_HANDLE);
                system=std::exchange(other.system,0);
                session=std::exchange(other.session,XR_NULL_HANDLE);
                localSpace=std::exchange(other.localSpace,XR_NULL_HANDLE);
                viewSpace=std::exchange(other.viewSpace,XR_NULL_HANDLE);
                sessionState=other.sessionState;
                sessionRunning=other.sessionRunning;
                exitRequested=other.exitRequested;
                runtimeName=std::move(other.runtimeName);
            }
            return *this;
        }
        ~XrObjects(){Destroy();}

    private:
        void Destroy() noexcept
        {
            if(viewSpace!=XR_NULL_HANDLE){xrDestroySpace(viewSpace);viewSpace=XR_NULL_HANDLE;}
            if(localSpace!=XR_NULL_HANDLE){xrDestroySpace(localSpace);localSpace=XR_NULL_HANDLE;}
            if(session!=XR_NULL_HANDLE){xrDestroySession(session);session=XR_NULL_HANDLE;}
            if(instance!=XR_NULL_HANDLE){xrDestroyInstance(instance);instance=XR_NULL_HANDLE;}
        }
    };

    XrObjects CreateXrBase()
    {
        if(!HasExtension(XR_KHR_D3D12_ENABLE_EXTENSION_NAME))
            throw std::runtime_error(
                "OpenXR runtime does not expose XR_KHR_D3D12_enable");

        XrObjects xr;
        const char* extensions[]{XR_KHR_D3D12_ENABLE_EXTENSION_NAME};
        XrInstanceCreateInfo ci{XR_TYPE_INSTANCE_CREATE_INFO};
        strcpy_s(ci.applicationInfo.applicationName,"OutRun2 VR DX12");
        ci.applicationInfo.applicationVersion=1;
        strcpy_s(ci.applicationInfo.engineName,"OutRun2006Tweaks");
        ci.applicationInfo.engineVersion=1;
        // VDXR and some PC runtimes still expose a 1.0 instance contract even when
        // the app is built with newer 1.1 headers. Request the stable 1.0 core;
        // XR_KHR_D3D12_enable is negotiated independently via extensions.
        ci.applicationInfo.apiVersion=XR_MAKE_VERSION(1,0,0);
        ci.enabledExtensionCount=1;
        ci.enabledExtensionNames=extensions;
        CheckXr(xrCreateInstance(&ci,&xr.instance),"xrCreateInstance");

        XrInstanceProperties ip{XR_TYPE_INSTANCE_PROPERTIES};
        if(XR_SUCCEEDED(xrGetInstanceProperties(xr.instance,&ip)))
            xr.runtimeName=ip.runtimeName;

        XrSystemGetInfo si{XR_TYPE_SYSTEM_GET_INFO};
        si.formFactor=XR_FORM_FACTOR_HEAD_MOUNTED_DISPLAY;
        CheckXr(xrGetSystem(xr.instance,&si,&xr.system),"xrGetSystem");
        return xr;
    }

    XrGraphicsRequirementsD3D12KHR GetRequirements(
        XrInstance instance,XrSystemId system)
    {
        PFN_xrGetD3D12GraphicsRequirementsKHR fn=nullptr;
        CheckXr(xrGetInstanceProcAddr(
            instance,"xrGetD3D12GraphicsRequirementsKHR",
            reinterpret_cast<PFN_xrVoidFunction*>(&fn)),
            "xrGetInstanceProcAddr(D3D12 requirements)");
        if(!fn)throw std::runtime_error(
            "xrGetD3D12GraphicsRequirementsKHR is null");
        XrGraphicsRequirementsD3D12KHR req{
            XR_TYPE_GRAPHICS_REQUIREMENTS_D3D12_KHR};
        CheckXr(fn(instance,system,&req),
            "xrGetD3D12GraphicsRequirementsKHR");
        return req;
    }

    void CreateSessionAndSpaces(XrObjects& xr,D3D12Objects& d3d)
    {
        XrGraphicsBindingD3D12KHR binding{
            XR_TYPE_GRAPHICS_BINDING_D3D12_KHR};
        binding.device=d3d.device;
        binding.queue=d3d.queue;

        XrSessionCreateInfo sci{XR_TYPE_SESSION_CREATE_INFO};
        sci.next=&binding;
        sci.systemId=xr.system;
        CheckXr(xrCreateSession(
            xr.instance,&sci,&xr.session),"xrCreateSession");

        XrReferenceSpaceCreateInfo rs{
            XR_TYPE_REFERENCE_SPACE_CREATE_INFO};
        rs.poseInReferenceSpace.orientation.w=1.0f;
        rs.referenceSpaceType=XR_REFERENCE_SPACE_TYPE_LOCAL;
        CheckXr(xrCreateReferenceSpace(
            xr.session,&rs,&xr.localSpace),
            "xrCreateReferenceSpace(LOCAL)");
        rs.referenceSpaceType=XR_REFERENCE_SPACE_TYPE_VIEW;
        CheckXr(xrCreateReferenceSpace(
            xr.session,&rs,&xr.viewSpace),
            "xrCreateReferenceSpace(VIEW)");
    }

    std::array<XrViewConfigurationView,2>
    GetViewConfig(XrObjects& xr)
    {
        std::uint32_t count=0;
        CheckXr(xrEnumerateViewConfigurationViews(
            xr.instance,xr.system,
            XR_VIEW_CONFIGURATION_TYPE_PRIMARY_STEREO,
            0,&count,nullptr),
            "xrEnumerateViewConfigurationViews(count)");
        if(count<2)throw std::runtime_error(
            "PRIMARY_STEREO returned fewer than two views");
        std::vector<XrViewConfigurationView> all(
            count,{XR_TYPE_VIEW_CONFIGURATION_VIEW});
        CheckXr(xrEnumerateViewConfigurationViews(
            xr.instance,xr.system,
            XR_VIEW_CONFIGURATION_TYPE_PRIMARY_STEREO,
            count,&count,all.data()),
            "xrEnumerateViewConfigurationViews");
        return{all[0],all[1]};
    }

    DXGI_FORMAT ChooseSwapchainFormat(XrSession session)
    {
        std::uint32_t count=0;
        CheckXr(xrEnumerateSwapchainFormats(
            session,0,&count,nullptr),
            "xrEnumerateSwapchainFormats(count)");
        std::vector<std::int64_t> formats(count);
        CheckXr(xrEnumerateSwapchainFormats(
            session,count,&count,formats.data()),
            "xrEnumerateSwapchainFormats");

        const std::array<DXGI_FORMAT,6> preferred{
            DXGI_FORMAT_R16G16B16A16_FLOAT,
            DXGI_FORMAT_R8G8B8A8_UNORM_SRGB,
            DXGI_FORMAT_B8G8R8A8_UNORM_SRGB,
            DXGI_FORMAT_R8G8B8A8_UNORM,
            DXGI_FORMAT_B8G8R8A8_UNORM,
            DXGI_FORMAT_R10G10B10A2_UNORM};
        for(auto wanted:preferred)
            if(std::find(formats.begin(),formats.end(),
                static_cast<std::int64_t>(wanted))!=formats.end())
                return wanted;
        if(formats.empty())throw std::runtime_error(
            "OpenXR returned no D3D12 swapchain formats");
        return static_cast<DXGI_FORMAT>(formats[0]);
    }

    struct Swapchain
    {
        XrSwapchain handle{XR_NULL_HANDLE};
        std::uint32_t width{};
        std::uint32_t height{};
        DXGI_FORMAT format{DXGI_FORMAT_UNKNOWN};
        std::vector<XrSwapchainImageD3D12KHR> images;

        Swapchain()=default;
        Swapchain(const Swapchain&)=delete;
        Swapchain& operator=(const Swapchain&)=delete;
        Swapchain(Swapchain&& other) noexcept
            : handle(std::exchange(other.handle,XR_NULL_HANDLE)),
              width(other.width),height(other.height),format(other.format),
              images(std::move(other.images)) {}
        Swapchain& operator=(Swapchain&& other) noexcept
        {
            if(this!=&other)
            {
                if(handle!=XR_NULL_HANDLE)xrDestroySwapchain(handle);
                handle=std::exchange(other.handle,XR_NULL_HANDLE);
                width=other.width;height=other.height;format=other.format;
                images=std::move(other.images);
            }
            return *this;
        }
        ~Swapchain()
        {
            if(handle!=XR_NULL_HANDLE)xrDestroySwapchain(handle);
        }
    };

    Swapchain CreateSwapchain(
        XrObjects& xr,
        const std::array<XrViewConfigurationView,2>& views)
    {
        Swapchain sc;
        sc.width=std::max(
            views[0].recommendedImageRectWidth,
            views[1].recommendedImageRectWidth);
        sc.height=std::max(
            views[0].recommendedImageRectHeight,
            views[1].recommendedImageRectHeight);
        sc.format=ChooseSwapchainFormat(xr.session);

        XrSwapchainCreateInfo ci{XR_TYPE_SWAPCHAIN_CREATE_INFO};
        ci.createFlags=0;
        ci.usageFlags=XR_SWAPCHAIN_USAGE_COLOR_ATTACHMENT_BIT;
        ci.format=static_cast<std::int64_t>(sc.format);
        ci.sampleCount=1;
        ci.width=sc.width;
        ci.height=sc.height;
        ci.faceCount=1;
        ci.arraySize=2;
        ci.mipCount=1;
        CheckXr(xrCreateSwapchain(
            xr.session,&ci,&sc.handle),"xrCreateSwapchain");

        std::uint32_t count=0;
        CheckXr(xrEnumerateSwapchainImages(
            sc.handle,0,&count,nullptr),
            "xrEnumerateSwapchainImages(count)");
        sc.images.resize(count);
        for(auto& image:sc.images)
            image={XR_TYPE_SWAPCHAIN_IMAGE_D3D12_KHR};
        CheckXr(xrEnumerateSwapchainImages(
            sc.handle,count,&count,
            reinterpret_cast<XrSwapchainImageBaseHeader*>(
                sc.images.data())),
            "xrEnumerateSwapchainImages");

        std::cout<<"OpenXR D3D12 stereo array swapchain "
            <<sc.width<<"x"<<sc.height
            <<" layers=2 format="<<static_cast<int>(sc.format)
            <<" images="<<count<<"\n";
        return sc;
    }

    ID3DBlob* Compile(
        const char* source,const char* entry,const char* target)
    {
        UINT flags=D3DCOMPILE_ENABLE_STRICTNESS|
            D3DCOMPILE_OPTIMIZATION_LEVEL3;
        ID3DBlob* blob=nullptr;
        ID3DBlob* errors=nullptr;
        const HRESULT hr=D3DCompile(
            source,std::strlen(source),
            "OutRun2DX12SingleDrawStereo",nullptr,nullptr,
            entry,target,flags,0,&blob,&errors);
        if(FAILED(hr))
        {
            if(errors)
                std::cerr<<static_cast<const char*>(
                    errors->GetBufferPointer())<<"\n";
            Release(errors);
            CheckHr(hr,"D3DCompile");
        }
        Release(errors);
        return blob;
    }

    constexpr const char* StereoShader=R"HLSL(
Texture2D LeftEye  : register(t0);
Texture2D RightEye : register(t1);
SamplerState LinearClamp : register(s0);

struct VSOut
{
    float4 position : SV_Position;
    float2 uv : TEXCOORD0;
    nointerpolation uint eye : TEXCOORD1;
};

VSOut VSMain(uint vertexId : SV_VertexID, uint instanceId : SV_InstanceID)
{
    VSOut o;
    float2 uv = float2((vertexId << 1) & 2, vertexId & 2);
    o.position = float4(
        uv.x * 2.0f - 1.0f,
        1.0f - uv.y * 2.0f,
        0.0f, 1.0f);
    o.uv = uv;
    o.eye = instanceId;
    return o;
}

struct GSOut
{
    float4 position : SV_Position;
    float2 uv : TEXCOORD0;
    nointerpolation uint eye : TEXCOORD1;
    uint target : SV_RenderTargetArrayIndex;
};

[maxvertexcount(3)]
void GSMain(triangle VSOut input[3],
    inout TriangleStream<GSOut> stream)
{
    const uint eye = input[0].eye;
    [unroll] for(uint i=0;i<3;++i)
    {
        GSOut o;
        o.position=input[i].position;
        o.uv=input[i].uv;
        o.eye=eye;
        o.target=eye;
        stream.Append(o);
    }
}

float4 PSMain(GSOut input) : SV_Target
{
    return input.eye==0
        ? LeftEye.Sample(LinearClamp,input.uv)
        : RightEye.Sample(LinearClamp,input.uv);
}
)HLSL";

    struct PendingAck
    {
        std::uint64_t gpuFenceValue{};
        std::uint32_t frameId{};
    };

    class StereoRenderer
    {
    public:
        StereoRenderer(
            D3D12Objects& d3d,Swapchain& swapchain)
            : d3d_(d3d),sc_(swapchain)
        {
            CreateDescriptors();
            CreatePipeline();
            CreateCommands();
        }

        ~StereoRenderer()
        {
            WaitIdle();
            if(fenceEvent_)CloseHandle(fenceEvent_);
            Release(fence_);
            Release(commandList_);
            for(auto*& a:allocators_)Release(a);
            Release(pipeline_);
            Release(rootSignature_);
            Release(srvHeap_);
            Release(rtvHeap_);
        }

        bool Render(
            std::uint32_t imageIndex,
            const OutRunVRHostDX12::TransportConsumer::Frame& frame,
            std::uint64_t& submittedFence)
        {
            if(imageIndex>=sc_.images.size()||
                imageIndex>=allocators_.size()||
                !frame.left||!frame.right)
                return false;

            EnsureAllocatorAvailable(imageIndex);
            CheckHr(allocators_[imageIndex]->Reset(),
                "DX12 host allocator Reset");
            CheckHr(commandList_->Reset(
                allocators_[imageIndex],pipeline_),
                "DX12 host command list Reset");

            const auto leftDesc=frame.left->GetDesc();
            const auto rightDesc=frame.right->GetDesc();
            if(leftDesc.Dimension!=D3D12_RESOURCE_DIMENSION_TEXTURE2D||
                rightDesc.Dimension!=D3D12_RESOURCE_DIMENSION_TEXTURE2D)
            {
                commandList_->Close();
                return false;
            }

            D3D12_SHADER_RESOURCE_VIEW_DESC srv{};
            srv.Shader4ComponentMapping=
                D3D12_DEFAULT_SHADER_4_COMPONENT_MAPPING;
            srv.ViewDimension=D3D12_SRV_DIMENSION_TEXTURE2D;
            srv.Texture2D.MipLevels=1;
            srv.Format=leftDesc.Format;
            auto cpu=srvHeap_->GetCPUDescriptorHandleForHeapStart();
            d3d_.device->CreateShaderResourceView(
                frame.left,&srv,cpu);
            cpu.ptr+=srvStride_;
            srv.Format=rightDesc.Format;
            d3d_.device->CreateShaderResourceView(
                frame.right,&srv,cpu);

            ID3D12Resource* xrImage=sc_.images[imageIndex].texture;
            std::array<D3D12_RESOURCE_BARRIER,3> begin{
                Transition(frame.left,
                    D3D12_RESOURCE_STATE_COMMON,
                    D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE),
                Transition(frame.right,
                    D3D12_RESOURCE_STATE_COMMON,
                    D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE),
                Transition(xrImage,
                    D3D12_RESOURCE_STATE_COMMON,
                    D3D12_RESOURCE_STATE_RENDER_TARGET)};
            commandList_->ResourceBarrier(
                static_cast<UINT>(begin.size()),begin.data());

            const D3D12_VIEWPORT viewport{
                0.0f,0.0f,
                static_cast<float>(sc_.width),
                static_cast<float>(sc_.height),
                0.0f,1.0f};
            const D3D12_RECT scissor{
                0,0,
                static_cast<LONG>(sc_.width),
                static_cast<LONG>(sc_.height)};
            commandList_->RSSetViewports(1,&viewport);
            commandList_->RSSetScissorRects(1,&scissor);

            auto rtv=rtvHeap_->GetCPUDescriptorHandleForHeapStart();
            rtv.ptr+=static_cast<SIZE_T>(imageIndex)*rtvStride_;
            commandList_->OMSetRenderTargets(
                1,&rtv,FALSE,nullptr);

            ID3D12DescriptorHeap* heaps[]{srvHeap_};
            commandList_->SetDescriptorHeaps(1,heaps);
            commandList_->SetGraphicsRootSignature(rootSignature_);
            commandList_->SetGraphicsRootDescriptorTable(
                0,srvHeap_->GetGPUDescriptorHandleForHeapStart());
            commandList_->IASetPrimitiveTopology(
                D3D_PRIMITIVE_TOPOLOGY_TRIANGLELIST);

            // Single API draw for both eyes. Two hardware instances are routed
            // to the two OpenXR array slices by the geometry shader.
            commandList_->DrawInstanced(3,2,0,0);

            std::array<D3D12_RESOURCE_BARRIER,3> end{
                Transition(frame.left,
                    D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE,
                    D3D12_RESOURCE_STATE_COMMON),
                Transition(frame.right,
                    D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE,
                    D3D12_RESOURCE_STATE_COMMON),
                Transition(xrImage,
                    D3D12_RESOURCE_STATE_RENDER_TARGET,
                    D3D12_RESOURCE_STATE_COMMON)};
            commandList_->ResourceBarrier(
                static_cast<UINT>(end.size()),end.data());
            CheckHr(commandList_->Close(),
                "DX12 host command list Close");

            ID3D12CommandList* lists[]{commandList_};
            d3d_.queue->ExecuteCommandLists(1,lists);
            submittedFence=++nextFenceValue_;
            CheckHr(d3d_.queue->Signal(
                fence_,submittedFence),"DX12 host queue Signal");
            allocatorFence_[imageIndex]=submittedFence;
            return true;
        }

        std::uint64_t CompletedFence() const noexcept
        {
            return fence_?fence_->GetCompletedValue():0;
        }

        void WaitIdle() noexcept
        {
            if(!d3d_.queue||!fence_)return;
            const std::uint64_t value=++nextFenceValue_;
            if(SUCCEEDED(d3d_.queue->Signal(fence_,value))&&
                fence_->GetCompletedValue()<value&&fenceEvent_)
            {
                if(SUCCEEDED(fence_->SetEventOnCompletion(
                    value,fenceEvent_)))
                    WaitForSingleObject(fenceEvent_,2000);
            }
        }

    private:
        static D3D12_RESOURCE_BARRIER Transition(
            ID3D12Resource* resource,
            D3D12_RESOURCE_STATES before,
            D3D12_RESOURCE_STATES after) noexcept
        {
            D3D12_RESOURCE_BARRIER b{};
            b.Type=D3D12_RESOURCE_BARRIER_TYPE_TRANSITION;
            b.Transition.pResource=resource;
            b.Transition.Subresource=
                D3D12_RESOURCE_BARRIER_ALL_SUBRESOURCES;
            b.Transition.StateBefore=before;
            b.Transition.StateAfter=after;
            return b;
        }

        void CreateDescriptors()
        {
            D3D12_DESCRIPTOR_HEAP_DESC rtv{};
            rtv.Type=D3D12_DESCRIPTOR_HEAP_TYPE_RTV;
            rtv.NumDescriptors=
                static_cast<UINT>(sc_.images.size());
            CheckHr(d3d_.device->CreateDescriptorHeap(
                &rtv,__uuidof(ID3D12DescriptorHeap),
                reinterpret_cast<void**>(&rtvHeap_)),
                "Create RTV heap");
            rtvStride_=d3d_.device->GetDescriptorHandleIncrementSize(
                D3D12_DESCRIPTOR_HEAP_TYPE_RTV);

            auto handle=rtvHeap_->GetCPUDescriptorHandleForHeapStart();
            for(const auto& image:sc_.images)
            {
                D3D12_RENDER_TARGET_VIEW_DESC vd{};
                vd.Format=sc_.format;
                vd.ViewDimension=D3D12_RTV_DIMENSION_TEXTURE2DARRAY;
                vd.Texture2DArray.MipSlice=0;
                vd.Texture2DArray.FirstArraySlice=0;
                vd.Texture2DArray.ArraySize=2;
                vd.Texture2DArray.PlaneSlice=0;
                d3d_.device->CreateRenderTargetView(
                    image.texture,&vd,handle);
                handle.ptr+=rtvStride_;
            }

            D3D12_DESCRIPTOR_HEAP_DESC srv{};
            srv.Type=D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV;
            srv.NumDescriptors=2;
            srv.Flags=D3D12_DESCRIPTOR_HEAP_FLAG_SHADER_VISIBLE;
            CheckHr(d3d_.device->CreateDescriptorHeap(
                &srv,__uuidof(ID3D12DescriptorHeap),
                reinterpret_cast<void**>(&srvHeap_)),
                "Create SRV heap");
            srvStride_=d3d_.device->GetDescriptorHandleIncrementSize(
                D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV);
        }

        void CreatePipeline()
        {
            D3D12_DESCRIPTOR_RANGE range{};
            range.RangeType=D3D12_DESCRIPTOR_RANGE_TYPE_SRV;
            range.NumDescriptors=2;
            range.BaseShaderRegister=0;
            range.RegisterSpace=0;
            range.OffsetInDescriptorsFromTableStart=0;

            D3D12_ROOT_PARAMETER param{};
            param.ParameterType=
                D3D12_ROOT_PARAMETER_TYPE_DESCRIPTOR_TABLE;
            param.DescriptorTable.NumDescriptorRanges=1;
            param.DescriptorTable.pDescriptorRanges=&range;
            param.ShaderVisibility=D3D12_SHADER_VISIBILITY_PIXEL;

            D3D12_STATIC_SAMPLER_DESC sampler{};
            sampler.Filter=D3D12_FILTER_MIN_MAG_MIP_LINEAR;
            sampler.AddressU=D3D12_TEXTURE_ADDRESS_MODE_CLAMP;
            sampler.AddressV=D3D12_TEXTURE_ADDRESS_MODE_CLAMP;
            sampler.AddressW=D3D12_TEXTURE_ADDRESS_MODE_CLAMP;
            sampler.MipLODBias=0;
            sampler.MaxAnisotropy=1;
            sampler.ComparisonFunc=D3D12_COMPARISON_FUNC_ALWAYS;
            sampler.BorderColor=
                D3D12_STATIC_BORDER_COLOR_TRANSPARENT_BLACK;
            sampler.MinLOD=0;
            sampler.MaxLOD=D3D12_FLOAT32_MAX;
            sampler.ShaderRegister=0;
            sampler.RegisterSpace=0;
            sampler.ShaderVisibility=D3D12_SHADER_VISIBILITY_PIXEL;

            D3D12_ROOT_SIGNATURE_DESC rs{};
            rs.NumParameters=1;
            rs.pParameters=&param;
            rs.NumStaticSamplers=1;
            rs.pStaticSamplers=&sampler;
            rs.Flags=D3D12_ROOT_SIGNATURE_FLAG_ALLOW_INPUT_ASSEMBLER_INPUT_LAYOUT;

            ID3DBlob* serialized=nullptr;
            ID3DBlob* errors=nullptr;
            const HRESULT rsHr=D3D12SerializeRootSignature(
                &rs,D3D_ROOT_SIGNATURE_VERSION_1,
                &serialized,&errors);
            if(FAILED(rsHr))
            {
                if(errors)
                    std::cerr<<static_cast<const char*>(
                        errors->GetBufferPointer())<<"\n";
                Release(errors);
                CheckHr(rsHr,"D3D12SerializeRootSignature");
            }
            Release(errors);
            CheckHr(d3d_.device->CreateRootSignature(
                0,serialized->GetBufferPointer(),
                serialized->GetBufferSize(),
                __uuidof(ID3D12RootSignature),
                reinterpret_cast<void**>(&rootSignature_)),
                "CreateRootSignature");
            Release(serialized);

            ID3DBlob* vs=Compile(
                StereoShader,"VSMain","vs_5_1");
            ID3DBlob* gs=Compile(
                StereoShader,"GSMain","gs_5_1");
            ID3DBlob* ps=Compile(
                StereoShader,"PSMain","ps_5_1");

            D3D12_GRAPHICS_PIPELINE_STATE_DESC pso{};
            pso.pRootSignature=rootSignature_;
            pso.VS={vs->GetBufferPointer(),vs->GetBufferSize()};
            pso.GS={gs->GetBufferPointer(),gs->GetBufferSize()};
            pso.PS={ps->GetBufferPointer(),ps->GetBufferSize()};
            pso.BlendState.AlphaToCoverageEnable=FALSE;
            pso.BlendState.IndependentBlendEnable=FALSE;
            const D3D12_RENDER_TARGET_BLEND_DESC blend{
                FALSE,FALSE,
                D3D12_BLEND_ONE,D3D12_BLEND_ZERO,
                D3D12_BLEND_OP_ADD,
                D3D12_BLEND_ONE,D3D12_BLEND_ZERO,
                D3D12_BLEND_OP_ADD,
                D3D12_LOGIC_OP_NOOP,
                D3D12_COLOR_WRITE_ENABLE_ALL};
            for(auto& rt:pso.BlendState.RenderTarget)rt=blend;
            pso.SampleMask=UINT_MAX;
            pso.RasterizerState.FillMode=D3D12_FILL_MODE_SOLID;
            pso.RasterizerState.CullMode=D3D12_CULL_MODE_NONE;
            pso.RasterizerState.FrontCounterClockwise=FALSE;
            pso.RasterizerState.DepthBias=D3D12_DEFAULT_DEPTH_BIAS;
            pso.RasterizerState.DepthBiasClamp=
                D3D12_DEFAULT_DEPTH_BIAS_CLAMP;
            pso.RasterizerState.SlopeScaledDepthBias=
                D3D12_DEFAULT_SLOPE_SCALED_DEPTH_BIAS;
            pso.RasterizerState.DepthClipEnable=TRUE;
            pso.RasterizerState.MultisampleEnable=FALSE;
            pso.RasterizerState.AntialiasedLineEnable=FALSE;
            pso.RasterizerState.ForcedSampleCount=0;
            pso.RasterizerState.ConservativeRaster=
                D3D12_CONSERVATIVE_RASTERIZATION_MODE_OFF;
            pso.DepthStencilState.DepthEnable=FALSE;
            pso.DepthStencilState.StencilEnable=FALSE;
            pso.InputLayout={nullptr,0};
            pso.PrimitiveTopologyType=
                D3D12_PRIMITIVE_TOPOLOGY_TYPE_TRIANGLE;
            pso.NumRenderTargets=1;
            pso.RTVFormats[0]=sc_.format;
            pso.SampleDesc.Count=1;
            CheckHr(d3d_.device->CreateGraphicsPipelineState(
                &pso,__uuidof(ID3D12PipelineState),
                reinterpret_cast<void**>(&pipeline_)),
                "CreateGraphicsPipelineState");
            Release(vs);Release(gs);Release(ps);

            std::cout
                <<"DX12 compositor: single DrawInstanced call renders both eyes "
                <<"(2 hardware instances -> OpenXR array slices). "
                <<"Native View Instancing capability tier="
                <<static_cast<unsigned>(d3d_.viewInstancingTier)
                <<"; shaderModel=0x"<<std::hex
                <<static_cast<unsigned>(d3d_.highestShaderModel)<<std::dec
                <<"; geometryCandidate="
                <<(d3d_.nativeViewInstancingCandidate?"yes":"no")
                <<". True game-geometry view-instancing remains gated on "
                <<"translated shader/PSO ownership.\n";
        }

        void CreateCommands()
        {
            allocators_.resize(sc_.images.size(),nullptr);
            allocatorFence_.resize(sc_.images.size(),0);
            for(auto*& allocator:allocators_)
                CheckHr(d3d_.device->CreateCommandAllocator(
                    D3D12_COMMAND_LIST_TYPE_DIRECT,
                    __uuidof(ID3D12CommandAllocator),
                    reinterpret_cast<void**>(&allocator)),
                    "CreateCommandAllocator");

            CheckHr(d3d_.device->CreateCommandList(
                0,D3D12_COMMAND_LIST_TYPE_DIRECT,
                allocators_[0],pipeline_,
                __uuidof(ID3D12GraphicsCommandList),
                reinterpret_cast<void**>(&commandList_)),
                "CreateCommandList");
            CheckHr(commandList_->Close(),
                "Initial command list Close");

            CheckHr(d3d_.device->CreateFence(
                0,D3D12_FENCE_FLAG_NONE,
                __uuidof(ID3D12Fence),
                reinterpret_cast<void**>(&fence_)),
                "Create local fence");
            fenceEvent_=CreateEventW(
                nullptr,FALSE,FALSE,nullptr);
            if(!fenceEvent_)throw std::runtime_error(
                "CreateEvent for DX12 fence failed");
        }

        void EnsureAllocatorAvailable(std::uint32_t imageIndex)
        {
            const auto required=allocatorFence_[imageIndex];
            if(!required||fence_->GetCompletedValue()>=required)
                return;
            CheckHr(fence_->SetEventOnCompletion(
                required,fenceEvent_),
                "SetEventOnCompletion");
            const DWORD wait=WaitForSingleObject(
                fenceEvent_,2000);
            if(wait!=WAIT_OBJECT_0)
                throw std::runtime_error(
                    "DX12 host timed out waiting to recycle command allocator");
        }

        D3D12Objects& d3d_;
        Swapchain& sc_;
        ID3D12DescriptorHeap* rtvHeap_{};
        ID3D12DescriptorHeap* srvHeap_{};
        UINT rtvStride_{};
        UINT srvStride_{};
        ID3D12RootSignature* rootSignature_{};
        ID3D12PipelineState* pipeline_{};
        std::vector<ID3D12CommandAllocator*> allocators_;
        std::vector<std::uint64_t> allocatorFence_;
        ID3D12GraphicsCommandList* commandList_{};
        ID3D12Fence* fence_{};
        HANDLE fenceEvent_{};
        std::uint64_t nextFenceValue_{};
    };

    void PollEvents(XrObjects& xr)
    {
        XrEventDataBuffer event{XR_TYPE_EVENT_DATA_BUFFER};
        while(xrPollEvent(xr.instance,&event)==XR_SUCCESS)
        {
            if(event.type==XR_TYPE_EVENT_DATA_SESSION_STATE_CHANGED)
            {
                const auto* changed=
                    reinterpret_cast<const XrEventDataSessionStateChanged*>(
                        &event);
                xr.sessionState=changed->state;
                std::cout<<"OpenXR session state="
                    <<static_cast<int>(changed->state)<<"\n";
                if(changed->state==XR_SESSION_STATE_READY&&!xr.sessionRunning)
                {
                    XrSessionBeginInfo bi{XR_TYPE_SESSION_BEGIN_INFO};
                    bi.primaryViewConfigurationType=
                        XR_VIEW_CONFIGURATION_TYPE_PRIMARY_STEREO;
                    CheckXr(xrBeginSession(xr.session,&bi),
                        "xrBeginSession");
                    xr.sessionRunning=true;
                }
                else if(changed->state==XR_SESSION_STATE_STOPPING&&
                    xr.sessionRunning)
                {
                    xrEndSession(xr.session);
                    xr.sessionRunning=false;
                }
                else if(changed->state==XR_SESSION_STATE_EXITING||
                    changed->state==XR_SESSION_STATE_LOSS_PENDING)
                    xr.exitRequested=true;
            }
            event={XR_TYPE_EVENT_DATA_BUFFER};
        }
    }
}

int main()
{
    OutRunVRHostDX12::ScopedHostLog hostLog;
    try
    {
        std::cout<<"OutRun2 native OpenXR D3D12 host "
#ifdef OUTRUN_VR_BUILD_SHA
            <<"build="<<OUTRUN_VR_BUILD_SHA
#endif
            <<"\n";

        auto xr=CreateXrBase();
        const auto requirements=
            GetRequirements(xr.instance,xr.system);
        auto d3d=CreateD3D12(requirements);
        CreateSessionAndSpaces(xr,d3d);
        const auto viewConfigs=GetViewConfig(xr);
        auto swapchain=CreateSwapchain(xr,viewConfigs);

        OutRunVRHostDX12::PoseWriter poseWriter(
            requirements.adapterLuid);
        OutRunVRHostDX12::TransportConsumer consumer(
            requirements.adapterLuid);
        OutRunVRHostDX12::RenderFrameMetaReader frameMeta;
        StereoRenderer renderer(d3d,swapchain);

        std::array<XrView,2> views{
            XrView{XR_TYPE_VIEW},
            XrView{XR_TYPE_VIEW}};
        std::deque<PendingAck> pendingAcks;
        OutRunVRHostDX12::TransportConsumer::Frame heldFrame{};
        std::array<XrView,2> heldRenderViews{
            XrView{XR_TYPE_VIEW},XrView{XR_TYPE_VIEW}};
        bool heldRenderViewsValid=false;
        std::uint64_t heldLastUseFence=0;
        OutRunVR::ClientPresentationMode lastPresentation=
            OutRunVR::PresentationUnknown;
        XrPosef theaterAnchor{};
        theaterAnchor.orientation.w=1.0f;
        bool theaterAnchorValid=false;

        std::cout<<"Runtime: "<<xr.runtimeName<<"\n";
        std::cout<<"Waiting for OpenXR session and DX12 game transport. "
            <<"The host may be started before OutRun.\n";

        while(!xr.exitRequested)
        {
            PollEvents(xr);
            if(!xr.sessionRunning)
            {
                Sleep(20);
                continue;
            }
            consumer.Touch();

            const std::uint64_t completed=renderer.CompletedFence();
            while(!pendingAcks.empty()&&
                pendingAcks.front().gpuFenceValue<=completed)
            {
                consumer.Ack(pendingAcks.front().frameId);
                pendingAcks.pop_front();
            }

            XrFrameWaitInfo wi{XR_TYPE_FRAME_WAIT_INFO};
            XrFrameState fs{XR_TYPE_FRAME_STATE};
            CheckXr(xrWaitFrame(xr.session,&wi,&fs),
                "xrWaitFrame");
            XrFrameBeginInfo bi{XR_TYPE_FRAME_BEGIN_INFO};
            CheckXr(xrBeginFrame(xr.session,&bi),
                "xrBeginFrame");

            XrViewLocateInfo li{XR_TYPE_VIEW_LOCATE_INFO};
            li.viewConfigurationType=
                XR_VIEW_CONFIGURATION_TYPE_PRIMARY_STEREO;
            li.displayTime=fs.predictedDisplayTime;
            li.space=xr.localSpace;
            XrViewState viewState{XR_TYPE_VIEW_STATE};
            std::uint32_t viewCount=0;
            CheckXr(xrLocateViews(
                xr.session,&li,&viewState,
                static_cast<std::uint32_t>(views.size()),
                &viewCount,views.data()),
                "xrLocateViews");

            XrSpaceLocation head{XR_TYPE_SPACE_LOCATION};
            xrLocateSpace(
                xr.viewSpace,xr.localSpace,
                fs.predictedDisplayTime,&head);

            poseWriter.Write(
                head,views,viewCount,viewConfigs,
                xr.sessionState,viewState.viewStateFlags,
                fs.shouldRender!=XR_FALSE,
                xr.runtimeName.c_str());

            const auto presentation=poseWriter.Presentation();
            if(poseWriter.ConsumeClientRecenter())
            {
                theaterAnchorValid=false;
                std::cout<<"DX12 host: game VR Recenter edge received; fixed theater anchor will be rebuilt from the current HMD pose.\n";
            }
            const XrSpaceLocationFlags headRequired=
                XR_SPACE_LOCATION_ORIENTATION_VALID_BIT|
                XR_SPACE_LOCATION_POSITION_VALID_BIT;
            const bool headValid=
                (head.locationFlags&headRequired)==headRequired;
            if(presentation!=lastPresentation)
            {
                theaterAnchorValid=false;
                lastPresentation=presentation;
                std::cout<<"DX12 presentation mode="
                    <<(presentation==OutRunVR::PresentationGameplay
                        ?"gameplay true-stereo":"LOCAL fixed theater")
                    <<"\n";
            }
            if(presentation==OutRunVR::PresentationTheater&&
                !theaterAnchorValid&&headValid)
            {
                theaterAnchor=head.pose;
                const XrVector3f forward=
                    OutRunVRHostDX12::RotateVector(
                        head.pose.orientation,{0.0f,0.0f,-1.0f});
                constexpr float TheaterDistanceMeters=1.8f;
                theaterAnchor.position.x+=
                    forward.x*TheaterDistanceMeters;
                theaterAnchor.position.y+=
                    forward.y*TheaterDistanceMeters;
                theaterAnchor.position.z+=
                    forward.z*TheaterDistanceMeters;
                theaterAnchorValid=true;
            }

            std::array<XrCompositionLayerProjectionView,2> projectionViews{
                XrCompositionLayerProjectionView{
                    XR_TYPE_COMPOSITION_LAYER_PROJECTION_VIEW},
                XrCompositionLayerProjectionView{
                    XR_TYPE_COMPOSITION_LAYER_PROJECTION_VIEW}};
            XrCompositionLayerProjection projection{
                XR_TYPE_COMPOSITION_LAYER_PROJECTION};
            XrCompositionLayerQuad theater{
                XR_TYPE_COMPOSITION_LAYER_QUAD};
            std::array<const XrCompositionLayerBaseHeader*,1> layers{};
            std::uint32_t layerCount=0;

            // Keep one producer slot leased until a newer game frame replaces it.
            // This decouples a 60 Hz game from a 72/80/90/120 Hz XR loop without
            // re-reading a slot after ACK (the producer may immediately reuse it).
            OutRunVRHostDX12::TransportConsumer::Frame candidate{};
            if(fs.shouldRender!=XR_FALSE&&
                consumer.AcquireLatest(d3d.device,d3d.queue,candidate)&&
                candidate.frameId&&
                candidate.frameId!=heldFrame.frameId)
            {
                if(heldFrame.frameId)
                {
                    if(heldLastUseFence)
                        pendingAcks.push_back(
                            {heldLastUseFence,heldFrame.frameId});
                    else
                        consumer.Ack(heldFrame.frameId);
                }
                heldFrame=std::move(candidate);
                heldLastUseFence=0;
                heldRenderViewsValid=false;
                if(presentation==OutRunVR::PresentationGameplay&&
                    heldFrame.poseSequence)
                {
                    OutRunVR::SharedRenderFrameState meta{};
                    heldRenderViewsValid=
                        frameMeta.ReadFrame(
                            heldFrame.frameId,
                            heldFrame.poseSequence,
                            meta)&&
                        OutRunVRHostDX12::RenderFrameMetaReader::ToXrViews(
                            meta,heldRenderViews);
                    if(!heldRenderViewsValid)
                    {
                        std::cerr
                            <<"DX12 host: exact rendered-eye metadata unavailable for frame "
                            <<heldFrame.frameId
                            <<"; current XR views will be used for this frame.\n";
                    }
                }
            }

            if(fs.shouldRender!=XR_FALSE&&viewCount>=2&&heldFrame.frameId)
            {
                XrSwapchainImageAcquireInfo ai{
                    XR_TYPE_SWAPCHAIN_IMAGE_ACQUIRE_INFO};
                std::uint32_t imageIndex=0;
                CheckXr(xrAcquireSwapchainImage(
                    swapchain.handle,&ai,&imageIndex),
                    "xrAcquireSwapchainImage");
                XrSwapchainImageWaitInfo swi{
                    XR_TYPE_SWAPCHAIN_IMAGE_WAIT_INFO};
                swi.timeout=XR_INFINITE_DURATION;
                CheckXr(xrWaitSwapchainImage(
                    swapchain.handle,&swi),
                    "xrWaitSwapchainImage");

                std::uint64_t gpuFence=0;
                const bool rendered=renderer.Render(
                    imageIndex,heldFrame,gpuFence);

                XrSwapchainImageReleaseInfo sri{
                    XR_TYPE_SWAPCHAIN_IMAGE_RELEASE_INFO};
                CheckXr(xrReleaseSwapchainImage(
                    swapchain.handle,&sri),
                    "xrReleaseSwapchainImage");

                if(rendered)
                {
                    heldLastUseFence=gpuFence;
                    if(presentation==OutRunVR::PresentationTheater&&
                        theaterAnchorValid)
                    {
                        const float aspect=
                            heldFrame.height
                            ?static_cast<float>(heldFrame.width)/
                                static_cast<float>(heldFrame.height)
                            :16.0f/9.0f;
                        constexpr float TheaterWidthMeters=2.1f;
                        theater.space=xr.localSpace;
                        theater.eyeVisibility=XR_EYE_VISIBILITY_BOTH;
                        theater.pose=theaterAnchor;
                        theater.size={
                            TheaterWidthMeters,
                            TheaterWidthMeters/
                                std::clamp(aspect,0.5f,3.0f)};
                        theater.subImage.swapchain=swapchain.handle;
                        theater.subImage.imageRect.offset={0,0};
                        theater.subImage.imageRect.extent={
                            static_cast<std::int32_t>(swapchain.width),
                            static_cast<std::int32_t>(swapchain.height)};
                        theater.subImage.imageArrayIndex=0;
                        layers[0]=reinterpret_cast<
                            const XrCompositionLayerBaseHeader*>(
                                &theater);
                        layerCount=1;
                    }
                    else if(presentation==OutRunVR::PresentationGameplay)
                    {
                        const auto& submitViews=
                            heldRenderViewsValid?heldRenderViews:views;
                        for(std::uint32_t eye=0;eye<2;++eye)
                        {
                            projectionViews[eye].pose=submitViews[eye].pose;
                            projectionViews[eye].fov=submitViews[eye].fov;
                            projectionViews[eye].subImage.swapchain=
                                swapchain.handle;
                            projectionViews[eye].subImage.imageRect.offset={0,0};
                            projectionViews[eye].subImage.imageRect.extent={
                                static_cast<std::int32_t>(swapchain.width),
                                static_cast<std::int32_t>(swapchain.height)};
                            projectionViews[eye].subImage.imageArrayIndex=eye;
                        }
                        projection.space=xr.localSpace;
                        projection.viewCount=2;
                        projection.views=projectionViews.data();
                        layers[0]=reinterpret_cast<
                            const XrCompositionLayerBaseHeader*>(
                                &projection);
                        layerCount=1;
                    }
                }
            }

            XrFrameEndInfo ei{XR_TYPE_FRAME_END_INFO};
            ei.displayTime=fs.predictedDisplayTime;
            ei.environmentBlendMode=
                XR_ENVIRONMENT_BLEND_MODE_OPAQUE;
            ei.layerCount=layerCount;
            ei.layers=layerCount?layers.data():nullptr;
            CheckXr(xrEndFrame(xr.session,&ei),
                "xrEndFrame");
        }

        renderer.WaitIdle();
        const auto completed=renderer.CompletedFence();
        while(!pendingAcks.empty()&&
            pendingAcks.front().gpuFenceValue<=completed)
        {
            consumer.Ack(pendingAcks.front().frameId);
            pendingAcks.pop_front();
        }
        if(heldFrame.frameId&&
            (!heldLastUseFence||heldLastUseFence<=completed))
            consumer.Ack(heldFrame.frameId);
        return 0;
    }
    catch(const std::exception& e)
    {
        std::cerr<<"DX12 HOST FATAL: "<<e.what()<<"\n";
        return 1;
    }
}
