#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>

#include "runtime_census.hpp"
#include "resource_translation.hpp"

#include <array>
#include <atomic>
#include <cstdint>
#include <mutex>
#include <unordered_set>
#include <vector>

#include <spdlog/spdlog.h>

#include "pipeline_translation.hpp"
#include "state_translation.hpp"
#include "vr/core/d3d9_draw_state.hpp"

namespace outrun::vr::dx11
{
    namespace
    {
        constexpr std::uint32_t SampleStride = 64u;
        constexpr std::size_t UnsupportedBitCount = 12;

        std::atomic<int> EnabledCache{-1};
        std::atomic<std::uint64_t> Samples{0};
        std::atomic<std::uint64_t> ExactSamples{0};
        std::atomic<std::uint64_t> FixedFunctionSamples{0};
        std::atomic<std::uint64_t> ProgrammableSamples{0};
        std::atomic<std::uint64_t> UnsupportedTopologySamples{0};
        std::atomic<std::uint64_t> UnsupportedIndexFormatSamples{0};
        std::atomic<std::uint64_t> UnsupportedTextureFormatSamples{0};
        std::atomic<std::uint64_t> UnsupportedColorFormatSamples{0};
        std::atomic<std::uint64_t> UnsupportedDepthFormatSamples{0};
        std::atomic<std::uint64_t> ResourceIntrospectionFailureSamples{0};
        std::atomic<std::uint64_t> ResourceBehaviorUnsupportedSamples{0};
        std::atomic<std::uint64_t> ResourceMutationTelemetryRequiredSamples{0};
        std::atomic<std::uint64_t> ResourceManagedShadowRequiredSamples{0};
        std::atomic<std::uint64_t> UniqueDrawSignatures{0};
        std::atomic<std::uint64_t> VertexDeclarationSamples{0};
        std::atomic<std::uint64_t> IndexedSamples{0};
        std::atomic<std::uint64_t> TexturedSamples{0};
        std::array<std::atomic<std::uint64_t>, UnsupportedBitCount>
            UnsupportedCounts{};
        std::atomic<ULONGLONG> LastLogMs{0};
        std::mutex SignatureMutex;
        std::unordered_set<std::uint64_t> SignatureHashes;

        struct FixedFunctionStageSignature
        {
            DWORD colorOp = D3DTOP_DISABLE;
            DWORD colorArg1 = D3DTA_TEXTURE;
            DWORD colorArg2 = D3DTA_CURRENT;
            DWORD alphaOp = D3DTOP_DISABLE;
            DWORD alphaArg1 = D3DTA_TEXTURE;
            DWORD alphaArg2 = D3DTA_CURRENT;
            DWORD texCoordIndex = 0;
            DWORD textureTransformFlags = D3DTTFF_DISABLE;
        };

        struct SourceSignature
        {
            DWORD fvf{};
            std::uint64_t vertexDeclHash{};
            UINT vertexDeclElements{};
            std::array<D3DVERTEXELEMENT9, MAXD3DDECLLENGTH + 1> vertexDeclElementsData{};
            UINT streamOffset{};
            UINT stride{};
            DWORD vertexUsage{};
            D3DPOOL vertexPool = D3DPOOL_FORCE_DWORD;
            DWORD indexUsage{};
            D3DPOOL indexPool = D3DPOOL_FORCE_DWORD;
            D3DFORMAT indexFormat = D3DFMT_UNKNOWN;
            DWORD renderTargetUsage{};
            D3DPOOL renderTargetPool = D3DPOOL_FORCE_DWORD;
            D3DFORMAT renderTargetFormat = D3DFMT_UNKNOWN;
            DWORD depthUsage{};
            D3DPOOL depthPool = D3DPOOL_FORCE_DWORD;
            D3DFORMAT depthFormat = D3DFMT_UNKNOWN;
            D3DRESOURCETYPE texture0Type = D3DRTYPE_FORCE_DWORD;
            DWORD texture0Usage{};
            D3DPOOL texture0Pool = D3DPOOL_FORCE_DWORD;
            D3DFORMAT texture0Format = D3DFMT_UNKNOWN;
            D3DRESOURCETYPE texture1Type = D3DRTYPE_FORCE_DWORD;
            DWORD texture1Usage{};
            D3DPOOL texture1Pool = D3DPOOL_FORCE_DWORD;
            D3DFORMAT texture1Format = D3DFMT_UNKNOWN;
            std::array<FixedFunctionStageSignature, 4> fixedFunctionStages{};
            DWORD colorOp0 = D3DTOP_DISABLE;
            DWORD alphaOp0 = D3DTOP_DISABLE;
            DWORD colorOp1 = D3DTOP_DISABLE;
            DWORD alphaOp1 = D3DTOP_DISABLE;
            DWORD minFilter = D3DTEXF_NONE;
            DWORD magFilter = D3DTEXF_NONE;
            DWORD mipFilter = D3DTEXF_NONE;
            DWORD addressU = D3DTADDRESS_WRAP;
            DWORD addressV = D3DTADDRESS_WRAP;
            bool vertexDeclaration{};
            bool vertexBufferPresent{};
            bool renderTargetPresent{};
            bool indexed{};
            bool textured{};
            bool texture0Present{};
            bool texture1Present{};
            bool depthPresent{};
            bool resourceIntrospectionComplete{true};
            bool fixedFunction{};
        };

        std::uint64_t hash_mix(std::uint64_t hash, std::uint64_t value) noexcept
        {
            hash ^= value + 0x9e3779b97f4a7c15ull + (hash << 6) + (hash >> 2);
            return hash;
        }

        std::uint64_t hash_signature(
            const SourceSignature& sig,
            D3DPRIMITIVETYPE primitive) noexcept
        {
            std::uint64_t hash = 0xcbf29ce484222325ull;
            hash = hash_mix(hash, static_cast<std::uint32_t>(primitive));
            hash = hash_mix(hash, sig.fvf);
            hash = hash_mix(hash, sig.vertexDeclHash);
            hash = hash_mix(hash, sig.vertexDeclElements);
            hash = hash_mix(hash, sig.streamOffset);
            hash = hash_mix(hash, sig.stride);
            hash = hash_mix(hash, sig.vertexUsage);
            hash = hash_mix(hash, static_cast<std::uint32_t>(sig.vertexPool));
            hash = hash_mix(hash, sig.indexUsage);
            hash = hash_mix(hash, static_cast<std::uint32_t>(sig.indexPool));
            hash = hash_mix(hash, static_cast<std::uint32_t>(sig.indexFormat));
            hash = hash_mix(hash, sig.renderTargetUsage);
            hash = hash_mix(hash, static_cast<std::uint32_t>(sig.renderTargetPool));
            hash = hash_mix(hash, static_cast<std::uint32_t>(sig.renderTargetFormat));
            hash = hash_mix(hash, sig.depthUsage);
            hash = hash_mix(hash, static_cast<std::uint32_t>(sig.depthPool));
            hash = hash_mix(hash, static_cast<std::uint32_t>(sig.depthFormat));
            hash = hash_mix(hash, static_cast<std::uint32_t>(sig.texture0Type));
            hash = hash_mix(hash, sig.texture0Usage);
            hash = hash_mix(hash, static_cast<std::uint32_t>(sig.texture0Pool));
            hash = hash_mix(hash, static_cast<std::uint32_t>(sig.texture0Format));
            hash = hash_mix(hash, static_cast<std::uint32_t>(sig.texture1Type));
            hash = hash_mix(hash, sig.texture1Usage);
            hash = hash_mix(hash, static_cast<std::uint32_t>(sig.texture1Pool));
            hash = hash_mix(hash, static_cast<std::uint32_t>(sig.texture1Format));
            hash = hash_mix(hash, sig.colorOp0);
            hash = hash_mix(hash, sig.alphaOp0);
            hash = hash_mix(hash, sig.colorOp1);
            hash = hash_mix(hash, sig.alphaOp1);
            for (const auto& stage : sig.fixedFunctionStages)
            {
                hash = hash_mix(hash, stage.colorOp);
                hash = hash_mix(hash, stage.colorArg1);
                hash = hash_mix(hash, stage.colorArg2);
                hash = hash_mix(hash, stage.alphaOp);
                hash = hash_mix(hash, stage.alphaArg1);
                hash = hash_mix(hash, stage.alphaArg2);
                hash = hash_mix(hash, stage.texCoordIndex);
                hash = hash_mix(hash, stage.textureTransformFlags);
            }
            hash = hash_mix(hash, sig.minFilter);
            hash = hash_mix(hash, sig.magFilter);
            hash = hash_mix(hash, sig.mipFilter);
            hash = hash_mix(hash, sig.addressU);
            hash = hash_mix(hash, sig.addressV);
            hash = hash_mix(hash, sig.vertexDeclaration ? 1u : 0u);
            hash = hash_mix(hash, sig.vertexBufferPresent ? 1u : 0u);
            hash = hash_mix(hash, sig.renderTargetPresent ? 1u : 0u);
            hash = hash_mix(hash, sig.indexed ? 1u : 0u);
            hash = hash_mix(hash, sig.textured ? 1u : 0u);
            hash = hash_mix(hash, sig.fixedFunction ? 1u : 0u);
            return hash;
        }

        bool inspect_texture(
            IDirect3DDevice9* device,
            DWORD stage,
            D3DRESOURCETYPE& type,
            DWORD& usage,
            D3DPOOL& pool,
            D3DFORMAT& format,
            bool& present) noexcept
        {
            type = D3DRTYPE_FORCE_DWORD;
            usage = 0;
            pool = D3DPOOL_FORCE_DWORD;
            format = D3DFMT_UNKNOWN;
            present = false;

            IDirect3DBaseTexture9* base = nullptr;
            const HRESULT getHr = device->GetTexture(stage, &base);
            if (FAILED(getHr))
                return false;
            if (!base)
                return true;

            present = true;
            type = base->GetType();
            bool descriptorObserved = false;
            if (type == D3DRTYPE_TEXTURE)
            {
                IDirect3DTexture9* texture = nullptr;
                if (SUCCEEDED(base->QueryInterface(
                        __uuidof(IDirect3DTexture9),
                        reinterpret_cast<void**>(&texture))) && texture)
                {
                    D3DSURFACE_DESC desc{};
                    if (SUCCEEDED(texture->GetLevelDesc(0, &desc)))
                    {
                        usage = desc.Usage;
                        pool = desc.Pool;
                        usage = desc.Usage;
                        pool = desc.Pool;
                        usage = desc.Usage;
                        pool = desc.Pool;
                        format = desc.Format;
                        descriptorObserved = true;
                    }
                    texture->Release();
                }
            }
            else if (type == D3DRTYPE_CUBETEXTURE)
            {
                IDirect3DCubeTexture9* texture = nullptr;
                if (SUCCEEDED(base->QueryInterface(
                        __uuidof(IDirect3DCubeTexture9),
                        reinterpret_cast<void**>(&texture))) && texture)
                {
                    D3DSURFACE_DESC desc{};
                    if (SUCCEEDED(texture->GetLevelDesc(0, &desc)))
                    {
                        format = desc.Format;
                        descriptorObserved = true;
                    }
                    texture->Release();
                }
            }
            else if (type == D3DRTYPE_VOLUMETEXTURE)
            {
                IDirect3DVolumeTexture9* texture = nullptr;
                if (SUCCEEDED(base->QueryInterface(
                        __uuidof(IDirect3DVolumeTexture9),
                        reinterpret_cast<void**>(&texture))) && texture)
                {
                    D3DVOLUME_DESC desc{};
                    if (SUCCEEDED(texture->GetLevelDesc(0, &desc)))
                    {
                        format = desc.Format;
                        descriptorObserved = true;
                    }
                    texture->Release();
                }
            }
            base->Release();
            return descriptorObserved;
        }

        SourceSignature inspect_source_signature(
            IDirect3DDevice9* device,
            bool fixedFunction) noexcept
        {
            SourceSignature sig{};
            sig.fixedFunction = fixedFunction;

            device->GetFVF(&sig.fvf);

            IDirect3DVertexDeclaration9* declaration = nullptr;
            if (SUCCEEDED(device->GetVertexDeclaration(&declaration)) &&
                declaration)
            {
                sig.vertexDeclaration = true;

                UINT count = 0;
                if (SUCCEEDED(declaration->GetDeclaration(nullptr, &count)) &&
                    count > 0 && count <= (MAXD3DDECLLENGTH + 1))
                {
                    std::vector<D3DVERTEXELEMENT9> elements(count);
                    UINT actual = count;
                    if (SUCCEEDED(declaration->GetDeclaration(
                            elements.data(), &actual)) &&
                        actual > 0 && actual <= count)
                    {
                        std::uint64_t declHash = 0xcbf29ce484222325ull;
                        for (UINT i = 0; i < actual; ++i)
                        {
                            const auto& element = elements[i];
                            declHash = hash_mix(declHash, element.Stream);
                            declHash = hash_mix(declHash, element.Offset);
                            declHash = hash_mix(declHash, element.Type);
                            declHash = hash_mix(declHash, element.Method);
                            declHash = hash_mix(declHash, element.Usage);
                            declHash = hash_mix(declHash, element.UsageIndex);
                        }
                        sig.vertexDeclHash = declHash;
                        sig.vertexDeclElements = actual;
                        for (UINT i = 0; i < actual; ++i)
                            sig.vertexDeclElementsData[i] = elements[i];
                    }
                }
                declaration->Release();
            }

            IDirect3DVertexBuffer9* vb = nullptr;
            const HRESULT streamHr = device->GetStreamSource(
                0, &vb, &sig.streamOffset, &sig.stride);
            if (FAILED(streamHr))
            {
                sig.resourceIntrospectionComplete = false;
            }
            else if (vb)
            {
                sig.vertexBufferPresent = true;
                D3DVERTEXBUFFER_DESC desc{};
                if (SUCCEEDED(vb->GetDesc(&desc)))
                {
                    sig.vertexUsage = desc.Usage;
                    sig.vertexPool = desc.Pool;
                }
                else
                    sig.resourceIntrospectionComplete = false;
                vb->Release();
            }

            IDirect3DSurface9* rt0 = nullptr;
            const HRESULT rtHr = device->GetRenderTarget(0, &rt0);
            if (FAILED(rtHr) || !rt0)
            {
                sig.resourceIntrospectionComplete = false;
            }
            else
            {
                sig.renderTargetPresent = true;
                D3DSURFACE_DESC desc{};
                if (SUCCEEDED(rt0->GetDesc(&desc)))
                {
                    sig.renderTargetUsage = desc.Usage;
                    sig.renderTargetPool = desc.Pool;
                    sig.renderTargetFormat = desc.Format;
                }
                else
                    sig.resourceIntrospectionComplete = false;
                rt0->Release();
            }

            IDirect3DSurface9* depth = nullptr;
            const HRESULT depthHr = device->GetDepthStencilSurface(&depth);
            if (FAILED(depthHr) && depthHr != D3DERR_NOTFOUND)
            {
                sig.resourceIntrospectionComplete = false;
            }
            else if (depth)
            {
                sig.depthPresent = true;
                D3DSURFACE_DESC desc{};
                if (SUCCEEDED(depth->GetDesc(&desc)))
                {
                    sig.depthUsage = desc.Usage;
                    sig.depthPool = desc.Pool;
                    sig.depthFormat = desc.Format;
                }
                else
                    sig.resourceIntrospectionComplete = false;
                depth->Release();
            }

            IDirect3DIndexBuffer9* ib = nullptr;
            const HRESULT indexHr = device->GetIndices(&ib);
            if (FAILED(indexHr))
            {
                sig.resourceIntrospectionComplete = false;
            }
            else if (ib)
            {
                D3DINDEXBUFFER_DESC desc{};
                if (SUCCEEDED(ib->GetDesc(&desc)))
                {
                    sig.indexUsage = desc.Usage;
                    sig.indexPool = desc.Pool;
                    sig.indexFormat = desc.Format;
                }
                else
                    sig.resourceIntrospectionComplete = false;
                sig.indexed = true;
                ib->Release();
            }

            const bool texture0Observed = inspect_texture(
                device, 0, sig.texture0Type, sig.texture0Usage,
                sig.texture0Pool, sig.texture0Format, sig.texture0Present);
            const bool texture1Observed = inspect_texture(
                device, 1, sig.texture1Type, sig.texture1Usage,
                sig.texture1Pool, sig.texture1Format, sig.texture1Present);
            if (!texture0Observed || !texture1Observed)
                sig.resourceIntrospectionComplete = false;
            sig.textured = sig.texture0Present || sig.texture1Present;

            if (fixedFunction)
            {
                for (DWORD stage = 0;
                     stage < static_cast<DWORD>(sig.fixedFunctionStages.size());
                     ++stage)
                {
                    auto& out = sig.fixedFunctionStages[stage];
                    device->GetTextureStageState(stage, D3DTSS_COLOROP, &out.colorOp);
                    device->GetTextureStageState(stage, D3DTSS_COLORARG1, &out.colorArg1);
                    device->GetTextureStageState(stage, D3DTSS_COLORARG2, &out.colorArg2);
                    device->GetTextureStageState(stage, D3DTSS_ALPHAOP, &out.alphaOp);
                    device->GetTextureStageState(stage, D3DTSS_ALPHAARG1, &out.alphaArg1);
                    device->GetTextureStageState(stage, D3DTSS_ALPHAARG2, &out.alphaArg2);
                    device->GetTextureStageState(stage, D3DTSS_TEXCOORDINDEX, &out.texCoordIndex);
                    device->GetTextureStageState(
                        stage, D3DTSS_TEXTURETRANSFORMFLAGS,
                        &out.textureTransformFlags);
                }
                sig.colorOp0 = sig.fixedFunctionStages[0].colorOp;
                sig.alphaOp0 = sig.fixedFunctionStages[0].alphaOp;
                sig.colorOp1 = sig.fixedFunctionStages[1].colorOp;
                sig.alphaOp1 = sig.fixedFunctionStages[1].alphaOp;
            }

            device->GetSamplerState(0, D3DSAMP_MINFILTER, &sig.minFilter);
            device->GetSamplerState(0, D3DSAMP_MAGFILTER, &sig.magFilter);
            device->GetSamplerState(0, D3DSAMP_MIPFILTER, &sig.mipFilter);
            device->GetSamplerState(0, D3DSAMP_ADDRESSU, &sig.addressU);
            device->GetSamplerState(0, D3DSAMP_ADDRESSV, &sig.addressV);
            return sig;
        }

        void note_signature(
            const SourceSignature& sig,
            D3DPRIMITIVETYPE primitive) noexcept
        {
            const auto hash = hash_signature(sig, primitive);
            bool inserted = false;
            std::uint64_t unique = 0;
            {
                std::lock_guard<std::mutex> lock(SignatureMutex);
                if (SignatureHashes.size() < 512)
                    inserted = SignatureHashes.insert(hash).second;
                unique = SignatureHashes.size();
            }
            UniqueDrawSignatures.store(unique, std::memory_order_relaxed);

            if (sig.vertexDeclaration)
                VertexDeclarationSamples.fetch_add(
                    1, std::memory_order_relaxed);
            if (sig.indexed)
                IndexedSamples.fetch_add(1, std::memory_order_relaxed);
            if (sig.textured)
                TexturedSamples.fetch_add(1, std::memory_order_relaxed);

            if (inserted && unique <= 64)
            {
                spdlog::info(
                    "VR DX11 R73 signature#{}: primitive={} fixedFn={} fvf=0x{:08X} decl={} declHash=0x{:016X} declElems={} stream0[offset={},stride={},present={},pool={},usage=0x{:08X}] ib[present={},pool={},usage=0x{:08X},fmt={}] rt[present={},pool={},usage=0x{:08X},fmt={}] depth[present={},pool={},usage=0x{:08X},fmt={}] tex0[present={},type={},pool={},usage=0x{:08X},fmt={}] tex1[present={},type={},pool={},usage=0x{:08X},fmt={}] tss0[color={},alpha={}] tss1[color={},alpha={}] samp0[min={},mag={},mip={},u={},v={}]",
                    unique,
                    static_cast<int>(primitive),
                    sig.fixedFunction ? 1 : 0,
                    sig.fvf,
                    sig.vertexDeclaration ? 1 : 0,
                    sig.vertexDeclHash,
                    sig.vertexDeclElements,
                    sig.streamOffset,
                    sig.stride,
                    sig.vertexBufferPresent ? 1 : 0,
                    static_cast<int>(sig.vertexPool),
                    sig.vertexUsage,
                    sig.indexed ? 1 : 0,
                    static_cast<int>(sig.indexPool),
                    sig.indexUsage,
                    static_cast<int>(sig.indexFormat),
                    sig.renderTargetPresent ? 1 : 0,
                    static_cast<int>(sig.renderTargetPool),
                    sig.renderTargetUsage,
                    static_cast<int>(sig.renderTargetFormat),
                    sig.depthPresent ? 1 : 0,
                    static_cast<int>(sig.depthPool),
                    sig.depthUsage,
                    static_cast<int>(sig.depthFormat),
                    sig.texture0Present ? 1 : 0,
                    static_cast<int>(sig.texture0Type),
                    static_cast<int>(sig.texture0Pool),
                    sig.texture0Usage,
                    static_cast<int>(sig.texture0Format),
                    sig.texture1Present ? 1 : 0,
                    static_cast<int>(sig.texture1Type),
                    static_cast<int>(sig.texture1Pool),
                    sig.texture1Usage,
                    static_cast<int>(sig.texture1Format),
                    sig.colorOp0,
                    sig.alphaOp0,
                    sig.colorOp1,
                    sig.alphaOp1,
                    sig.minFilter,
                    sig.magFilter,
                    sig.mipFilter,
                    sig.addressU,
                    sig.addressV);

                if (sig.fixedFunction)
                {
                    for (std::size_t stageIndex = 0;
                         stageIndex < sig.fixedFunctionStages.size();
                         ++stageIndex)
                    {
                        const auto& stage = sig.fixedFunctionStages[stageIndex];
                        if (stage.colorOp == D3DTOP_DISABLE &&
                            stage.alphaOp == D3DTOP_DISABLE)
                            continue;

                        spdlog::info(
                            "VR DX11 R72 ffp signature#{} stage#{}: color[op={},arg1=0x{:08X},arg2=0x{:08X}] alpha[op={},arg1=0x{:08X},arg2=0x{:08X}] texCoord=0x{:08X} texTransform=0x{:08X}",
                            unique,
                            stageIndex,
                            stage.colorOp,
                            stage.colorArg1,
                            stage.colorArg2,
                            stage.alphaOp,
                            stage.alphaArg1,
                            stage.alphaArg2,
                            stage.texCoordIndex,
                            stage.textureTransformFlags);
                    }
                }

                if (sig.vertexDeclaration && sig.vertexDeclElements > 0)
                {
                    for (UINT i = 0; i < sig.vertexDeclElements; ++i)
                    {
                        const auto& element = sig.vertexDeclElementsData[i];
                        spdlog::info(
                            "VR DX11 R72 decl signature#{} elem#{}: stream={} offset={} type={} method={} usage={} usageIndex={}",
                            unique,
                            i,
                            element.Stream,
                            element.Offset,
                            element.Type,
                            element.Method,
                            element.Usage,
                            element.UsageIndex);
                    }
                }
            }
        }

        bool census_enabled() noexcept
        {
            int cached = EnabledCache.load(std::memory_order_acquire);
            if (cached >= 0)
                return cached != 0;

            char value[8]{};
            const DWORD length = GetEnvironmentVariableA(
                "OUTRUN_VR_DX11_CENSUS", value,
                static_cast<DWORD>(sizeof(value)));
            const bool enabled =
                length > 0 && length < sizeof(value) && value[0] == '1';
            EnabledCache.store(enabled ? 1 : 0, std::memory_order_release);
            if (enabled)
                spdlog::info(
                    "VR DX11 R73 census ACTIVE: passive 1/{} draw sampling with resource lifetime/mutation gates; native draw routing remains disabled",
                    SampleStride);
            return enabled;
        }

        void maybe_log() noexcept
        {
            const ULONGLONG now = GetTickCount64();
            ULONGLONG last = LastLogMs.load(std::memory_order_acquire);
            if (now - last < 5000)
                return;
            if (!LastLogMs.compare_exchange_strong(
                    last, now, std::memory_order_acq_rel,
                    std::memory_order_acquire))
                return;

            std::array<std::uint64_t, UnsupportedBitCount> unsupported{};
            for (std::size_t i = 0; i < UnsupportedBitCount; ++i)
                unsupported[i] =
                    UnsupportedCounts[i].load(std::memory_order_relaxed);

            spdlog::info(
                "VR DX11 R73 census: samples={} exact={} fixedFn={} programmable={} topologyUnsupported={} signatures={} declSamples={} indexedSamples={} texturedSamples={} resourceExact[introspectionFailure={},behaviorUnsupported={},mutationTelemetryRequired={},managedShadowRequired={},indexUnsupported={},textureUnsupported={},colorUnsupported={},depthUnsupported={}] unsupported[incomplete={},wbuffer={},sepAlpha={},alphaTest={},stencil={},fog={},lighting={},srgb={},fill={},blend={},depthCmp={},cull={}]",
                Samples.load(std::memory_order_relaxed),
                ExactSamples.load(std::memory_order_relaxed),
                FixedFunctionSamples.load(std::memory_order_relaxed),
                ProgrammableSamples.load(std::memory_order_relaxed),
                UnsupportedTopologySamples.load(std::memory_order_relaxed),
                UniqueDrawSignatures.load(std::memory_order_relaxed),
                VertexDeclarationSamples.load(std::memory_order_relaxed),
                IndexedSamples.load(std::memory_order_relaxed),
                TexturedSamples.load(std::memory_order_relaxed),
                ResourceIntrospectionFailureSamples.load(std::memory_order_relaxed),
                ResourceBehaviorUnsupportedSamples.load(std::memory_order_relaxed),
                ResourceMutationTelemetryRequiredSamples.load(std::memory_order_relaxed),
                ResourceManagedShadowRequiredSamples.load(std::memory_order_relaxed),
                UnsupportedIndexFormatSamples.load(std::memory_order_relaxed),
                UnsupportedTextureFormatSamples.load(std::memory_order_relaxed),
                UnsupportedColorFormatSamples.load(std::memory_order_relaxed),
                UnsupportedDepthFormatSamples.load(std::memory_order_relaxed),
                unsupported[0], unsupported[1], unsupported[2], unsupported[3],
                unsupported[4], unsupported[5], unsupported[6], unsupported[7],
                unsupported[8], unsupported[9], unsupported[10], unsupported[11]);
        }

        void note_unsupported(std::uint32_t mask) noexcept
        {
            for (std::size_t bit = 0; bit < UnsupportedBitCount; ++bit)
            {
                if ((mask & (1u << bit)) != 0)
                    UnsupportedCounts[bit].fetch_add(
                        1, std::memory_order_relaxed);
            }
        }
    }

    void observe_source_draw(
        IDirect3DDevice9* device,
        D3DPRIMITIVETYPE primitive) noexcept
    {
        if (!device || !census_enabled())
            return;

        thread_local std::uint32_t stride = 0;
        if ((++stride % SampleStride) != 0)
            return;

        OutRunVR::DrawState::RenderStateSnapshot source{};
        const bool captured =
            OutRunVRStereo::CaptureTrackedRenderStateSnapshot(device, source);
        const auto translated = translate_pipeline(source);
        const auto topology = translate_primitive(primitive);

        Samples.fetch_add(1, std::memory_order_relaxed);
        std::uint32_t unsupported = translated.unsupported;
        if (!captured)
            unsupported |= PipelineUnsupportedIncompleteSnapshot;
        note_unsupported(unsupported);

        if (!topology.exact)
            UnsupportedTopologySamples.fetch_add(1, std::memory_order_relaxed);

        IDirect3DVertexShader9* vs = nullptr;
        IDirect3DPixelShader9* ps = nullptr;
        const bool vsOk = SUCCEEDED(device->GetVertexShader(&vs));
        const bool psOk = SUCCEEDED(device->GetPixelShader(&ps));
        const bool fixedFunction =
            (!vsOk || vs == nullptr) && (!psOk || ps == nullptr);
        if (vs) vs->Release();
        if (ps) ps->Release();

        if (fixedFunction)
            FixedFunctionSamples.fetch_add(1, std::memory_order_relaxed);
        else
            ProgrammableSamples.fetch_add(1, std::memory_order_relaxed);

        const auto signature =
            inspect_source_signature(device, fixedFunction);
        note_signature(signature, primitive);

        bool resourcesExact = signature.resourceIntrospectionComplete;
        if (!signature.resourceIntrospectionComplete)
            ResourceIntrospectionFailureSamples.fetch_add(
                1, std::memory_order_relaxed);

        bool behaviorDescriptorExact = true;
        bool mutationTelemetryRequired = false;
        bool managedShadowRequired = false;
        const auto observeBehavior = [&](bool present, ResourceRole role,
                                         D3DPOOL pool, DWORD usage) noexcept
        {
            if (!present)
                return;
            const auto behavior = translate_resource_behavior(role, pool, usage);
            behaviorDescriptorExact =
                behaviorDescriptorExact && behavior.descriptorExact;
            mutationTelemetryRequired =
                mutationTelemetryRequired || behavior.requiresMutationTelemetry;
            managedShadowRequired =
                managedShadowRequired || behavior.requiresCpuShadow;
        };

        observeBehavior(
            signature.vertexBufferPresent, ResourceRole::Vertex,
            signature.vertexPool, signature.vertexUsage);
        observeBehavior(
            signature.indexed, ResourceRole::Index,
            signature.indexPool, signature.indexUsage);
        observeBehavior(
            signature.texture0Present, ResourceRole::Texture,
            signature.texture0Pool, signature.texture0Usage);
        observeBehavior(
            signature.texture1Present, ResourceRole::Texture,
            signature.texture1Pool, signature.texture1Usage);
        observeBehavior(
            signature.renderTargetPresent, ResourceRole::Color,
            signature.renderTargetPool, signature.renderTargetUsage);
        observeBehavior(
            signature.depthPresent, ResourceRole::DepthStencil,
            signature.depthPool, signature.depthUsage);

        if (!behaviorDescriptorExact)
            ResourceBehaviorUnsupportedSamples.fetch_add(
                1, std::memory_order_relaxed);
        if (mutationTelemetryRequired)
            ResourceMutationTelemetryRequiredSamples.fetch_add(
                1, std::memory_order_relaxed);
        if (managedShadowRequired)
            ResourceManagedShadowRequiredSamples.fetch_add(
                1, std::memory_order_relaxed);
        if (!behaviorDescriptorExact || mutationTelemetryRequired ||
            managedShadowRequired)
            resourcesExact = false;

        if (signature.indexed &&
            !translate_resource_format(
                signature.indexFormat, ResourceRole::Index).exact)
        {
            UnsupportedIndexFormatSamples.fetch_add(1, std::memory_order_relaxed);
            resourcesExact = false;
        }
        if (signature.texture0Present &&
            !translate_resource_format(
                signature.texture0Format, ResourceRole::Texture).exact)
        {
            UnsupportedTextureFormatSamples.fetch_add(
                1, std::memory_order_relaxed);
            resourcesExact = false;
        }
        if (signature.texture1Present &&
            !translate_resource_format(
                signature.texture1Format, ResourceRole::Texture).exact)
        {
            UnsupportedTextureFormatSamples.fetch_add(
                1, std::memory_order_relaxed);
            resourcesExact = false;
        }

        // A bound texture whose descriptor could not be observed leaves
        // D3DFMT_UNKNOWN behind; both the introspection gate and the bound
        // stage format checks above fail closed.
        if (!translate_resource_format(
                signature.renderTargetFormat, ResourceRole::Color).exact)
        {
            UnsupportedColorFormatSamples.fetch_add(1, std::memory_order_relaxed);
            resourcesExact = false;
        }
        if (signature.depthPresent &&
            !translate_resource_format(
                signature.depthFormat, ResourceRole::DepthStencil).exact)
        {
            UnsupportedDepthFormatSamples.fetch_add(1, std::memory_order_relaxed);
            resourcesExact = false;
        }

        if (unsupported == PipelineUnsupportedNone && topology.exact && resourcesExact)
            ExactSamples.fetch_add(1, std::memory_order_relaxed);

        maybe_log();
    }
}