// R30 screen-space asymmetric-FOV correction overlay.
//
// R29 restores conservative world/effect classification and removes the steady-
// state third mono draw. R30 fixes the remaining HUD convergence problem without
// moving the world image: only main-backbuffer orthographic/ScreenSpace2D draws
// receive an eye-specific clip-space X affine. The affine maps one common
// head-relative tangent-angle interval into each eye's actual asymmetric OpenXR
// FOV, so the same HUD feature lands on the same visual ray in both eyes.
//
// This is intentionally an interim projection-layer HUD solution. It does not
// pretend to be XrCompositionLayerQuad: perspective world draws and fragile
// perspective effects remain entirely owned by R29/R13.

// Allow R29 to be built as an independent translation unit when the
// R30/R29 compile-ownership seam is enabled by the build graph.
// Default behavior retains the validated textual chain until link verification.
#ifndef OUTRUN_VR_REFACTOR_SPLIT_R30_R29
#include "stereo_renderer_r29.cpp"
#endif
#include "../core/r29_owner_api.hpp"
#include "../core/r30_support_api.hpp"
#include "../state/state_block_tracker.hpp"
#include "vr_pass_policy.hpp"
#include "hook_mgr.hpp"
#include "plugin.hpp"
#include "vr_shared.hpp"
#include <spdlog/spdlog.h>
#include <d3dcompiler.h>
#include <algorithm>
#include <atomic>
#include <memory>
#include <mutex>
#include <unordered_map>
#include <vector>

// Do not inherit these guards from the lower R29 textual implementation.
#ifdef min
#undef min
#endif
#ifdef max
#undef max
#endif

namespace Settings
{
    extern Setting<bool> VRTelemetry;
    extern Setting<float> VRWorldScale;
    extern Setting<float> VRHudScale;
    extern Setting<float> VRStereoDepth;
    extern Setting<int> SkyGlowFactor;
    extern Setting<bool> SkyGlowTwoStep;
}

namespace OutRunVRStereo
{

    template <typename T>
    void R30ReleaseCom(T*& value) noexcept
    {
        if (value)
        {
            value->Release();
            value = nullptr;
        }
    }

    class R30ScopedInternalPass final
    {
    public:
        R30ScopedInternalPass() noexcept
            : previous_(R29OwnerExchangeInternalStereoPass(true)) {}
        ~R30ScopedInternalPass()
        {
            R29OwnerExchangeInternalStereoPass(previous_);
        }
        R30ScopedInternalPass(const R30ScopedInternalPass&) = delete;
        R30ScopedInternalPass& operator=(const R30ScopedInternalPass&) = delete;
    private:
        bool previous_ = false;
    };
    namespace
    {
        SafetyHookInline R30DrawPrimitiveR29Hook{};
        SafetyHookInline R30DrawIndexedPrimitiveR29Hook{};
        SafetyHookInline R30DrawPrimitiveUPR29Hook{};
        SafetyHookInline R30DrawIndexedPrimitiveUPR29Hook{};

        std::atomic<OutRunVR::RuntimeEligibility::InstallState> R30InstallState{
            OutRunVR::RuntimeEligibility::InstallState::Pending };

        std::uint64_t R30ScreenSpaceFovDraws = 0;
        std::uint64_t R30ScreenSpaceFallbacks = 0;
        std::uint64_t R30ScreenSpaceBuildFailures = 0;
        bool R30FirstScreenSpaceLogged = false;
        bool R30FirstFlatPerspectiveLogged = false;

        std::uint64_t R30XyzrhwHudDraws = 0;
        std::uint64_t R30XyzrhwWorldEffectDraws = 0;
        std::uint64_t R30XyzrhwRhwWorldPromotions = 0;
        std::uint64_t R30XyzrhwFallbacks = 0;
        bool R30FirstXyzrhwHudLogged = false;
        bool R30FirstXyzrhwWorldLogged = false;
        bool R30FirstXyzrhwRhwPromotionLogged = false;
        std::uint64_t R30XyzrhwAtomicFallbacks = 0;
        std::uint64_t R30XyzrhwDepthPreserveFallbacks = 0;
        bool R30FirstXyzrhwAtomicFallbackLogged = false;
        std::uint64_t R30XyzrhwBilateralFallbacks = 0;
        bool R30FirstXyzrhwBilateralFallbackLogged = false;


        // Reset occurs before the XYZRHW geometry owner is defined in this TU.
        // Dispatch through a forward-declared helper, not a later TLS object.
        void R30InvalidateXyzrhwWorldGeometry() noexcept;

        // Flat perspective screen-space effects reuse the same headset/base
        // projection and head pose for many particle/overlay draws. The per-
        // draw stock WVP is still unique, so cache only the independent geometry.
        // Preserve the original matrix multiplication order (and its rounding).
        struct R30FlatEffectGeometryCache
        {
            bool valid = false;
            std::uint32_t poseSequence = 0;
            float worldScale = 0.0f;
            D3DMATRIX baseProjection{};
            D3DMATRIX headInverse{};
            decltype(OutRunVRRenderer::LatchedStereoFrame::eyeOrientation) eyeOrientation{};
            decltype(OutRunVRRenderer::LatchedStereoFrame::eyeOffset) eyeOffset{};
            decltype(OutRunVRRenderer::LatchedStereoFrame::eyeFov) eyeFov{};
            D3DMATRIX inverseBaseProjection{};
            D3DMATRIX eyeInverse[2]{};
            D3DMATRIX eyeProjection[2]{};
            float planeNdcZ = 0.0f;
        };
        thread_local R30FlatEffectGeometryCache R30FlatEffectGeometry{};

        // R30.6 CPU shadows for XYZRHW vertex/index buffers.
        //
        // The old VB/IB conversion path called Lock(READONLY) from inside Draw,
        // which can block behind the GPU and also fails for WRITEONLY buffers.
        // Observe the game's own Lock/Unlock writes instead and keep the exact
        // CPU byte ranges that are known current. Draw then consumes only this
        // shadow and fails open to R29 when a range was never observed.
        constexpr std::size_t R30CreateVertexBufferVtableIndex = 26;
        constexpr std::size_t R30CreateIndexBufferVtableIndex = 27;
        constexpr std::size_t R30BufferReleaseVtableIndex = 2;
        constexpr std::size_t R30BufferLockVtableIndex = 11;
        constexpr std::size_t R30BufferUnlockVtableIndex = 12;
        constexpr UINT R30MaxShadowBytes = 16u * 1024u * 1024u;

        SafetyHookInline R30CreateVertexBufferHook{};
        SafetyHookInline R30CreateIndexBufferHook{};
        SafetyHookInline R30VertexBufferReleaseHook{};
        SafetyHookInline R30VertexBufferLockHook{};
        SafetyHookInline R30VertexBufferUnlockHook{};
        SafetyHookInline R30IndexBufferReleaseHook{};
        SafetyHookInline R30IndexBufferLockHook{};
        SafetyHookInline R30IndexBufferUnlockHook{};

        struct R30ByteRange
        {
            UINT begin = 0;
            UINT end = 0; // exclusive
        };

        struct R30BufferShadow
        {
            std::mutex mutex;
            UINT size = 0;
            DWORD usage = 0;
            D3DPOOL pool = D3DPOOL_DEFAULT;
            D3DFORMAT indexFormat = D3DFMT_UNKNOWN;
            std::vector<std::uint8_t> bytes;
            std::vector<R30ByteRange> valid;
            // Incremented while holding mutex whenever known shadow contents or
            // coverage change. Draw scratch copies are reusable only for this
            // exact generation and byte range.
            std::uint64_t revision = 1;
            void* lockPtr = nullptr;
            UINT lockOffset = 0;
            UINT lockSize = 0;
            DWORD lockFlags = 0;
            bool writeLock = false;
        };

        using R30ShadowPtr = std::shared_ptr<R30BufferShadow>;
        std::mutex R30ShadowRegistryMutex;
        std::mutex R30ShadowHookMutex;
        // Published once all three hooks are installed: steady VB/IB draws
        // need no install mutex, while partial installs still retry under lock.
        std::atomic<bool> R30VertexBufferHooksReady{false};
        std::atomic<bool> R30IndexBufferHooksReady{false};
        std::unordered_map<IDirect3DVertexBuffer9*, R30ShadowPtr>
            R30VertexShadows;
        std::unordered_map<IDirect3DIndexBuffer9*, R30ShadowPtr>
            R30IndexShadows;
        std::uint64_t R30ShadowWrites = 0;
        std::uint64_t R30ShadowReadHits = 0;
        std::uint64_t R30ShadowReadMisses = 0;
        std::uint64_t R30ShadowDiscardInvalidations = 0;
        bool R30FirstShadowMissLogged = false;

        struct R30ShadowCopyCache
        {
            // Hold the entry alive: a released COM buffer can recycle its raw
            // pointer; a new registry entry must never match an old copy.
            R30ShadowPtr entry;
            UINT offset = 0;
            UINT size = 0;
            std::uint64_t revision = 0;
        };

        struct R30ScratchBuffers
        {
            R30ShadowCopyCache vertexCopy;
            R30ShadowCopyCache indexCopy;
            std::vector<std::uint8_t> source;
            std::vector<std::uint8_t> indexSource;
            std::vector<std::uint8_t> left;
            std::vector<std::uint8_t> right;
            std::vector<std::uint8_t> used;
            std::vector<std::uint32_t> physical;
            std::vector<std::uint16_t> indices16;
            std::vector<std::uint32_t> indices32;
            bool busy = false;
        };
        thread_local R30ScratchBuffers R30Scratch;

        struct R30ScratchLease
        {
            R30ScratchBuffers* buffers = nullptr;
            R30ScratchLease() noexcept
            {
                if (!R30Scratch.busy)
                {
                    R30Scratch.busy = true;
                    buffers = &R30Scratch;
                }
            }
            ~R30ScratchLease()
            {
                if (buffers)
                    buffers->busy = false;
            }
            explicit operator bool() const noexcept { return buffers != nullptr; }
        };

        void R30MergeValidRange(std::vector<R30ByteRange>& ranges,
            UINT begin, UINT end)
        {
            if (begin >= end)
                return;

            // Partial dynamic VB/IB locks can generate many disjoint ranges.
            // Locate the first touching interval in O(log n) and merge the
            // entire overlapping span in place. The old erase-per-interval
            // loop repeatedly shifted the vector tail for every range it
            // consumed, producing quadratic work on heavily streamed buffers.
            auto first = std::lower_bound(ranges.begin(), ranges.end(), begin,
                [](const R30ByteRange& range, UINT position) noexcept {
                    return range.end < position;
                });
            if (first == ranges.end() || first->begin > end)
            {
                ranges.insert(first, { begin, end });
                return;
            }

            first->begin = (std::min)(first->begin, begin);
            first->end = (std::max)(first->end, end);
            auto last = first + 1;
            while (last != ranges.end() && last->begin <= first->end)
            {
                first->end = (std::max)(first->end, last->end);
                ++last;
            }
            // Erase one contiguous tail, not each overlapping interval.
            ranges.erase(first + 1, last);
        }

        bool R30RangeValid(const std::vector<R30ByteRange>& ranges,
            UINT begin, UINT end) noexcept
        {
            if (begin >= end)
                return false;
            // The merge writer maintains ascending, disjoint intervals; avoid
            // a full linear scan on every stereo VB/IB draw-time shadow read.
            const auto first = std::lower_bound(ranges.begin(), ranges.end(), begin,
                [](const R30ByteRange& range, UINT position) noexcept {
                    return range.end < position;
                });
            return first != ranges.end() &&
                first->begin <= begin && first->end >= end;
        }

        R30ShadowPtr R30FindVertexShadow(IDirect3DVertexBuffer9* buffer)
        {
            std::lock_guard<std::mutex> lock(R30ShadowRegistryMutex);
            const auto it = R30VertexShadows.find(buffer);
            return it == R30VertexShadows.end() ? nullptr : it->second;
        }

        R30ShadowPtr R30FindIndexShadow(IDirect3DIndexBuffer9* buffer)
        {
            std::lock_guard<std::mutex> lock(R30ShadowRegistryMutex);
            const auto it = R30IndexShadows.find(buffer);
            return it == R30IndexShadows.end() ? nullptr : it->second;
        }

        R30ShadowPtr R30EnsureVertexShadow(IDirect3DVertexBuffer9* buffer)
        {
            if (!buffer)
                return nullptr;
            if (auto existing = R30FindVertexShadow(buffer))
                return existing;
            D3DVERTEXBUFFER_DESC desc{};
            if (FAILED(buffer->GetDesc(&desc)) || !desc.Size ||
                desc.Size > R30MaxShadowBytes)
                return nullptr;
            auto entry = std::make_shared<R30BufferShadow>();
            entry->size = desc.Size;
            entry->usage = desc.Usage;
            entry->pool = desc.Pool;
            std::lock_guard<std::mutex> lock(R30ShadowRegistryMutex);
            auto [it, inserted] = R30VertexShadows.emplace(buffer, entry);
            return inserted ? entry : it->second;
        }

        R30ShadowPtr R30EnsureIndexShadow(IDirect3DIndexBuffer9* buffer)
        {
            if (!buffer)
                return nullptr;
            if (auto existing = R30FindIndexShadow(buffer))
                return existing;
            D3DINDEXBUFFER_DESC desc{};
            if (FAILED(buffer->GetDesc(&desc)) || !desc.Size ||
                desc.Size > R30MaxShadowBytes ||
                (desc.Format != D3DFMT_INDEX16 &&
                 desc.Format != D3DFMT_INDEX32))
                return nullptr;
            auto entry = std::make_shared<R30BufferShadow>();
            entry->size = desc.Size;
            entry->usage = desc.Usage;
            entry->pool = desc.Pool;
            entry->indexFormat = desc.Format;
            std::lock_guard<std::mutex> lock(R30ShadowRegistryMutex);
            auto [it, inserted] = R30IndexShadows.emplace(buffer, entry);
            return inserted ? entry : it->second;
        }

        void R30BeginObservedLock(const R30ShadowPtr& entry,
            UINT offset, UINT size, void* data, DWORD flags)
        {
            if (!entry || !data)
                return;
            std::lock_guard<std::mutex> lock(entry->mutex);
            if (offset > entry->size)
                return;
            const UINT effectiveSize =
                size == 0 ? entry->size - offset : size;
            if (!effectiveSize || effectiveSize > entry->size - offset)
                return;
            entry->lockPtr = data;
            entry->lockOffset = offset;
            entry->lockSize = effectiveSize;
            entry->lockFlags = flags;
            entry->writeLock = (flags & D3DLOCK_READONLY) == 0;
            if (entry->writeLock && (flags & D3DLOCK_DISCARD))
            {
                entry->valid.clear();
                ++entry->revision;
                ++R30ShadowDiscardInvalidations;
            }
        }

        void R30FinishObservedLock(const R30ShadowPtr& entry,
            bool unlockSucceeded)
        {
            if (!entry)
                return;
            std::lock_guard<std::mutex> lock(entry->mutex);
            if (unlockSucceeded && entry->writeLock && entry->lockPtr &&
                entry->lockSize && entry->lockOffset <= entry->size &&
                entry->lockSize <= entry->size - entry->lockOffset)
            {
                try
                {
                    if (entry->bytes.size() != entry->size)
                        entry->bytes.resize(entry->size);
                    std::memcpy(entry->bytes.data() + entry->lockOffset,
                        entry->lockPtr, entry->lockSize);
                    R30MergeValidRange(entry->valid, entry->lockOffset,
                        entry->lockOffset + entry->lockSize);
                    ++entry->revision;
                    ++R30ShadowWrites;
                }
                catch (...)
                {
                    entry->bytes.clear();
                    entry->valid.clear();
                    ++entry->revision;
                }
            }
            else if (!unlockSucceeded && entry->writeLock)
            {
                entry->valid.clear();
                ++entry->revision;
            }
            entry->lockPtr = nullptr;
            entry->lockOffset = 0;
            entry->lockSize = 0;
            entry->lockFlags = 0;
            entry->writeLock = false;
        }

        bool R30CopyVertexShadow(const R30ShadowPtr& entry,
            UINT offset, UINT size, std::vector<std::uint8_t>& out,
            R30ShadowCopyCache& cache)
        {
            if (!entry)
            {
                // Drop old scratch ownership if the buffer registry no longer
                // provides a live shadow (e.g. Release/Reset).
                cache.entry.reset();
                ++R30ShadowReadMisses;
                return false;
            }
            std::lock_guard<std::mutex> lock(entry->mutex);
            // Repeated fixed-geometry draws used to copy the same complete VB/IB
            // byte span again, even if its observed Lock/Unlock generation had
            // not changed. A matching generation and byte range were validated on
            // the cache fill; every write/DISCARD/failed Unlock increments the
            // revision under this same mutex. Test the hit before the binary
            // interval search while keeping full range validation on misses.
            if (cache.entry == entry &&
                cache.offset == offset && cache.size == size &&
                cache.revision == entry->revision && out.size() == size)
            {
                ++R30ShadowReadHits;
                return true;
            }
            // A cache miss must prove current coverage before reading bytes.
            if (offset > entry->size || size > entry->size - offset ||
                entry->bytes.size() != entry->size ||
                !R30RangeValid(entry->valid, offset, offset + size))
            {
                // A DISCARD or failed Unlock must not pin stale shadow bytes
                // in the thread-local scratch until some later valid draw.
                cache.entry.reset();
                ++R30ShadowReadMisses;
                if (!R30FirstShadowMissLogged)
                {
                    R30FirstShadowMissLogged = true;
                    spdlog::info(
                        "VR R30.6 BUFFER SHADOW: draw-time GPU Lock removed; an unobserved VB/IB range will fail open until the game's next write Lock/Unlock supplies CPU bytes");
                }
                return false;
            }
            try
            {
                out.resize(size);
                std::memcpy(out.data(), entry->bytes.data() + offset, size);
            }
            catch (...)
            {
                cache.entry.reset();
                return false;
            }
            cache.entry = entry;
            cache.offset = offset;
            cache.size = size;
            cache.revision = entry->revision;
            ++R30ShadowReadHits;
            return true;
        }

        bool R30CopyIndexShadow(const R30ShadowPtr& entry,
            UINT offset, UINT size, std::vector<std::uint8_t>& out,
            R30ShadowCopyCache& cache)
        {
            if (!entry)
            {
                // Drop old scratch ownership if the buffer registry no longer
                // provides a live shadow (e.g. Release/Reset).
                cache.entry.reset();
                ++R30ShadowReadMisses;
                return false;
            }
            std::lock_guard<std::mutex> lock(entry->mutex);
            // Repeated fixed-geometry draws used to copy the same complete VB/IB
            // byte span again, even if its observed Lock/Unlock generation had
            // not changed. A matching generation and byte range were validated on
            // the cache fill; every write/DISCARD/failed Unlock increments the
            // revision under this same mutex. Test the hit before the binary
            // interval search while keeping full range validation on misses.
            if (cache.entry == entry &&
                cache.offset == offset && cache.size == size &&
                cache.revision == entry->revision && out.size() == size)
            {
                ++R30ShadowReadHits;
                return true;
            }
            // A cache miss must prove current coverage before reading bytes.
            if (offset > entry->size || size > entry->size - offset ||
                entry->bytes.size() != entry->size ||
                !R30RangeValid(entry->valid, offset, offset + size))
            {
                // A DISCARD or failed Unlock must not pin stale shadow bytes
                // in the thread-local scratch until some later valid draw.
                cache.entry.reset();
                ++R30ShadowReadMisses;
                return false;
            }
            try
            {
                out.resize(size);
                std::memcpy(out.data(), entry->bytes.data() + offset, size);
            }
            catch (...)
            {
                cache.entry.reset();
                return false;
            }
            cache.entry = entry;
            cache.offset = offset;
            cache.size = size;
            cache.revision = entry->revision;
            ++R30ShadowReadHits;
            return true;
        }

        HRESULT __stdcall R30VertexBufferLockDest(
            IDirect3DVertexBuffer9* buffer, UINT offset, UINT size,
            void** data, DWORD flags)
        {
            const HRESULT hr = R30VertexBufferLockHook.stdcall<HRESULT>(
                buffer, offset, size, data, flags);
            if (SUCCEEDED(hr) && data && *data)
                R30BeginObservedLock(
                    R30EnsureVertexShadow(buffer), offset, size, *data, flags);
            return hr;
        }

        HRESULT __stdcall R30VertexBufferUnlockDest(
            IDirect3DVertexBuffer9* buffer)
        {
            const auto entry = R30FindVertexShadow(buffer);
            // The pointer returned by Lock is guaranteed valid until Unlock,
            // so snapshot bytes before forwarding the real Unlock.
            if (entry)
                R30FinishObservedLock(entry, true);
            const HRESULT hr =
                R30VertexBufferUnlockHook.stdcall<HRESULT>(buffer);
            if (FAILED(hr) && entry)
            {
                std::lock_guard<std::mutex> lock(entry->mutex);
                entry->valid.clear();
                ++entry->revision;
            }
            return hr;
        }

        ULONG __stdcall R30VertexBufferReleaseDest(
            IDirect3DVertexBuffer9* buffer)
        {
            const ULONG refs =
                R30VertexBufferReleaseHook.stdcall<ULONG>(buffer);
            if (refs == 0)
            {
                std::lock_guard<std::mutex> lock(R30ShadowRegistryMutex);
                R30VertexShadows.erase(buffer);
            }
            return refs;
        }

        HRESULT __stdcall R30IndexBufferLockDest(
            IDirect3DIndexBuffer9* buffer, UINT offset, UINT size,
            void** data, DWORD flags)
        {
            const HRESULT hr = R30IndexBufferLockHook.stdcall<HRESULT>(
                buffer, offset, size, data, flags);
            if (SUCCEEDED(hr) && data && *data)
                R30BeginObservedLock(
                    R30EnsureIndexShadow(buffer), offset, size, *data, flags);
            return hr;
        }

        HRESULT __stdcall R30IndexBufferUnlockDest(
            IDirect3DIndexBuffer9* buffer)
        {
            const auto entry = R30FindIndexShadow(buffer);
            if (entry)
                R30FinishObservedLock(entry, true);
            const HRESULT hr =
                R30IndexBufferUnlockHook.stdcall<HRESULT>(buffer);
            if (FAILED(hr) && entry)
            {
                std::lock_guard<std::mutex> lock(entry->mutex);
                entry->valid.clear();
                ++entry->revision;
            }
            return hr;
        }

        ULONG __stdcall R30IndexBufferReleaseDest(
            IDirect3DIndexBuffer9* buffer)
        {
            const ULONG refs =
                R30IndexBufferReleaseHook.stdcall<ULONG>(buffer);
            if (refs == 0)
            {
                std::lock_guard<std::mutex> lock(R30ShadowRegistryMutex);
                R30IndexShadows.erase(buffer);
            }
            return refs;
        }

        bool R30EnsureVertexBufferHooks(IDirect3DVertexBuffer9* buffer)
        {
            if (!buffer)
                return false;
            // acquire observes fully initialized hook objects, never a
            // partially installed group; failure paths retain locked retry.
            if (R30VertexBufferHooksReady.load(std::memory_order_acquire))
                return true;
            std::lock_guard<std::mutex> lock(R30ShadowHookMutex);
            if (R30VertexBufferHooksReady.load(std::memory_order_relaxed))
                return true;
            auto** vtable = *reinterpret_cast<void***>(buffer);
            if (!R30VertexBufferLockHook)
                R30VertexBufferLockHook = safetyhook::create_inline(
                    vtable[R30BufferLockVtableIndex],
                    R30VertexBufferLockDest);
            if (!R30VertexBufferUnlockHook)
                R30VertexBufferUnlockHook = safetyhook::create_inline(
                    vtable[R30BufferUnlockVtableIndex],
                    R30VertexBufferUnlockDest);
            if (!R30VertexBufferReleaseHook)
                R30VertexBufferReleaseHook = safetyhook::create_inline(
                    vtable[R30BufferReleaseVtableIndex],
                    R30VertexBufferReleaseDest);
            const bool installed = R30VertexBufferLockHook &&
                R30VertexBufferUnlockHook && R30VertexBufferReleaseHook;
            if (installed)
                R30VertexBufferHooksReady.store(true, std::memory_order_release);
            return installed;
        }

        bool R30EnsureIndexBufferHooks(IDirect3DIndexBuffer9* buffer)
        {
            if (!buffer)
                return false;
            // acquire observes fully initialized hook objects, never a
            // partially installed group; failure paths retain locked retry.
            if (R30IndexBufferHooksReady.load(std::memory_order_acquire))
                return true;
            std::lock_guard<std::mutex> lock(R30ShadowHookMutex);
            if (R30IndexBufferHooksReady.load(std::memory_order_relaxed))
                return true;
            auto** vtable = *reinterpret_cast<void***>(buffer);
            if (!R30IndexBufferLockHook)
                R30IndexBufferLockHook = safetyhook::create_inline(
                    vtable[R30BufferLockVtableIndex],
                    R30IndexBufferLockDest);
            if (!R30IndexBufferUnlockHook)
                R30IndexBufferUnlockHook = safetyhook::create_inline(
                    vtable[R30BufferUnlockVtableIndex],
                    R30IndexBufferUnlockDest);
            if (!R30IndexBufferReleaseHook)
                R30IndexBufferReleaseHook = safetyhook::create_inline(
                    vtable[R30BufferReleaseVtableIndex],
                    R30IndexBufferReleaseDest);
            const bool installed = R30IndexBufferLockHook &&
                R30IndexBufferUnlockHook && R30IndexBufferReleaseHook;
            if (installed)
                R30IndexBufferHooksReady.store(true, std::memory_order_release);
            return installed;
        }

        HRESULT __stdcall R30CreateVertexBufferDest(
            IDirect3DDevice9* device, UINT length, DWORD usage, DWORD fvf,
            D3DPOOL pool, IDirect3DVertexBuffer9** out, HANDLE* shared)
        {
            const HRESULT hr = R30CreateVertexBufferHook.stdcall<HRESULT>(
                device, length, usage, fvf, pool, out, shared);
            if (SUCCEEDED(hr) && out && *out)
            {
                R30EnsureVertexBufferHooks(*out);
                R30EnsureVertexShadow(*out);
            }
            return hr;
        }

        HRESULT __stdcall R30CreateIndexBufferDest(
            IDirect3DDevice9* device, UINT length, DWORD usage,
            D3DFORMAT format, D3DPOOL pool,
            IDirect3DIndexBuffer9** out, HANDLE* shared)
        {
            const HRESULT hr = R30CreateIndexBufferHook.stdcall<HRESULT>(
                device, length, usage, format, pool, out, shared);
            if (SUCCEEDED(hr) && out && *out)
            {
                R30EnsureIndexBufferHooks(*out);
                R30EnsureIndexShadow(*out);
            }
            return hr;
        }

        void R30InstallBufferCreationHooks(IDirect3DDevice9* device)
        {
            if (!device)
                return;
            auto** vtable = *reinterpret_cast<void***>(device);
            if (!R30CreateVertexBufferHook)
                R30CreateVertexBufferHook = safetyhook::create_inline(
                    vtable[R30CreateVertexBufferVtableIndex],
                    R30CreateVertexBufferDest);
            if (!R30CreateIndexBufferHook)
                R30CreateIndexBufferHook = safetyhook::create_inline(
                    vtable[R30CreateIndexBufferVtableIndex],
                    R30CreateIndexBufferDest);
            if (!R30CreateVertexBufferHook || !R30CreateIndexBufferHook)
                spdlog::warn(
                    "VR R30.6 BUFFER SHADOW: creation hook incomplete; existing/dynamic buffers still register lazily on draw/Lock");
        }

        void R30RollbackBufferShadowHooks() noexcept
        {
            // Serialize teardown with the slow install path; a later retry
            // must not observe the previously published ready flags.
            std::lock_guard<std::mutex> hookInstallLock(R30ShadowHookMutex);
            R30VertexBufferHooksReady.store(false, std::memory_order_release);
            R30IndexBufferHooksReady.store(false, std::memory_order_release);
            // Unhook entry points before dropping registry ownership. Any draw
            // holding a COM reference also holds a shared_ptr acquired from the
            // registry, so clearing the maps cannot invalidate an in-flight
            // shadow object.
            R30CreateIndexBufferHook = {};
            R30CreateVertexBufferHook = {};
            R30IndexBufferUnlockHook = {};
            R30IndexBufferLockHook = {};
            R30IndexBufferReleaseHook = {};
            R30VertexBufferUnlockHook = {};
            R30VertexBufferLockHook = {};
            R30VertexBufferReleaseHook = {};
            {
                std::lock_guard<std::mutex> lock(
                    R30ShadowRegistryMutex);
                R30IndexShadows.clear();
                R30VertexShadows.clear();
            }
        }


        // R30.6 stereo sky glow.
        //
        // The original game samples D3DBACKBUFFER_TYPE_MONO and owns only one
        // glow chain. In true stereo that is necessarily the left eye. Keep the
        // original mono post-process disabled and run a completely separate
        // reduced/blurred chain for each completed eye immediately before the
        // renderer composes/publishes the stereo frame.
        SafetyHookInline R30PresentR29Hook{};
        SafetyHookInline R30ResetR29Hook{};

        struct R30SkyGlowResources
        {
            IDirect3DTexture9* reduced[2]{};
            IDirect3DTexture9* temp[2]{};
            // Keep level-zero render-target interfaces for the resource lifetime;
            // GetSurfaceLevel on both eyes every Present adds avoidable COM calls.
            IDirect3DSurface9* reducedSurface[2]{};
            IDirect3DSurface9* tempSurface[2]{};
            IDirect3DPixelShader9* bright = nullptr;
            IDirect3DPixelShader9* blur = nullptr;
            IDirect3DPixelShader9* composite = nullptr;
            UINT eyeWidth = 0;
            UINT eyeHeight = 0;
            UINT glowWidth = 0;
            UINT glowHeight = 0;
            int factor = 0;
        };
        // Per-Present CPU cache: a latched OpenXR eye aspect is invariant
        // across many HUD draw calls, not just across their vertices.
        struct R30HudContainCache
        {
            bool valid = false;
            std::uint64_t presentEpoch = 0;
            std::uint32_t poseSequence = 0;
            UINT sourceWidth = 0;
            UINT sourceHeight = 0;
            float userScale = 0.0f;
            float eyeFov[8]{};
            float scaleX = 1.0f;
            float scaleY = 1.0f;
        };
        thread_local R30HudContainCache R30HudContain{};

        R30SkyGlowResources R30SkyGlow{};
        std::uint64_t R30SkyGlowFrames = 0;
        std::uint64_t R30SkyGlowFailures = 0;
        std::uint64_t R30SkyGlowSceneCaptureEpoch = 0;
        bool R30FirstSkyGlowLogged = false;
        bool R30FirstSkyGlowFailureLogged = false;

        void R30ReleaseSkyGlowResources() noexcept
        {
            for (int eye = 0; eye < 2; ++eye)
            {
                // Release borrowed level-zero surfaces before their textures.
                R30ReleaseCom(R30SkyGlow.reducedSurface[eye]);
                R30ReleaseCom(R30SkyGlow.tempSurface[eye]);
                R30ReleaseCom(R30SkyGlow.reduced[eye]);
                R30ReleaseCom(R30SkyGlow.temp[eye]);
            }
            R30ReleaseCom(R30SkyGlow.bright);
            R30ReleaseCom(R30SkyGlow.blur);
            R30ReleaseCom(R30SkyGlow.composite);
            R30SkyGlow.eyeWidth = 0;
            R30SkyGlow.eyeHeight = 0;
            R30SkyGlow.glowWidth = 0;
            R30SkyGlow.glowHeight = 0;
            R30SkyGlow.factor = 0;
        }

        bool R30CompilePixelShader(IDirect3DDevice9* device,
            const char* source, const char* entry,
            IDirect3DPixelShader9** shader)
        {
            if (!device || !source || !entry || !shader)
                return false;
            ID3DBlob* bytecode = nullptr;
            ID3DBlob* errors = nullptr;
            const HRESULT compile = D3DCompile(
                source, std::strlen(source),
                "OutRunVR-StereoSkyGlow", nullptr, nullptr,
                entry, "ps_2_0",
                D3DCOMPILE_OPTIMIZATION_LEVEL3,
                0, &bytecode, &errors);
            if (FAILED(compile) || !bytecode)
            {
                if (errors && errors->GetBufferPointer())
                    spdlog::warn(
                        "VR SKY GLOW: pixel shader compile failed: {}",
                        static_cast<const char*>(
                            errors->GetBufferPointer()));
                R30ReleaseCom(errors);
                R30ReleaseCom(bytecode);
                return false;
            }
            const HRESULT create = device->CreatePixelShader(
                static_cast<const DWORD*>(bytecode->GetBufferPointer()),
                shader);
            R30ReleaseCom(errors);
            R30ReleaseCom(bytecode);
            return SUCCEEDED(create) && *shader;
        }

        bool R30EnsureSkyGlowResources(IDirect3DDevice9* device)
        {
            const auto frame = R29OwnerCaptureFrameSnapshot();
            if (!device || !frame.width || !frame.height)
                return false;
            const int factor =
                std::clamp(Settings::SkyGlowFactor.get(), 1, 16);
            const UINT glowWidth = std::max<UINT>(
                160u, frame.width /
                    static_cast<UINT>(factor));
            const UINT glowHeight = std::max<UINT>(
                120u, frame.height /
                    static_cast<UINT>(factor));

            if (R30SkyGlow.reduced[0] && R30SkyGlow.reduced[1] &&
                R30SkyGlow.temp[0] && R30SkyGlow.temp[1] &&
                R30SkyGlow.reducedSurface[0] && R30SkyGlow.reducedSurface[1] &&
                R30SkyGlow.tempSurface[0] && R30SkyGlow.tempSurface[1] &&
                R30SkyGlow.bright && R30SkyGlow.blur &&
                R30SkyGlow.composite &&
                R30SkyGlow.eyeWidth == frame.width &&
                R30SkyGlow.eyeHeight == frame.height &&
                R30SkyGlow.glowWidth == glowWidth &&
                R30SkyGlow.glowHeight == glowHeight &&
                R30SkyGlow.factor == factor)
                return true;

            R30ReleaseSkyGlowResources();

            for (int eye = 0; eye < 2; ++eye)
            {
                if (FAILED(device->CreateTexture(
                        glowWidth, glowHeight, 1,
                        D3DUSAGE_RENDERTARGET,
                        D3DFMT_A8R8G8B8, D3DPOOL_DEFAULT,
                        &R30SkyGlow.reduced[eye], nullptr)) ||
                    FAILED(device->CreateTexture(
                        glowWidth, glowHeight, 1,
                        D3DUSAGE_RENDERTARGET,
                        D3DFMT_A8R8G8B8, D3DPOOL_DEFAULT,
                        &R30SkyGlow.temp[eye], nullptr)))
                {
                    R30ReleaseSkyGlowResources();
                    return false;
                }
            }

            static constexpr char BrightPs[] = R"(
                sampler Scene : register(s0);
                float4 Bright(float2 uv : TEXCOORD0) : COLOR0
                {
                    float4 c = tex2D(Scene, uv);
                    float peak = max(c.r, max(c.g, c.b));
                    float bright = saturate((peak - 0.58) * 2.75);
                    // World HDR/exposure draws normally leave useful alpha below
                    // one, while most fixed HUD art is opaque. This is not used
                    // for eye identity; it only suppresses UI contamination.
                    float worldMask = max(0.15,
                        saturate((1.0 - c.a) * 2.0));
                    float m = bright * worldMask;
                    return float4(c.rgb * m, m);
                })";
            static constexpr char BlurPs[] = R"(
                sampler Source : register(s0);
                float4 Texel : register(c0);
                float4 Blur(float2 uv : TEXCOORD0) : COLOR0
                {
                    float2 d = Texel.xy;
                    float4 c = tex2D(Source, uv) * 0.40;
                    c += tex2D(Source, uv + d * 1.5) * 0.24;
                    c += tex2D(Source, uv - d * 1.5) * 0.24;
                    c += tex2D(Source, uv + d * 3.5) * 0.06;
                    c += tex2D(Source, uv - d * 3.5) * 0.06;
                    return c;
                })";
            static constexpr char CompositePs[] = R"(
                sampler Glow : register(s0);
                float4 Params : register(c0);
                float4 Composite(float2 uv : TEXCOORD0) : COLOR0
                {
                    float4 g = tex2D(Glow, uv);
                    return float4(g.rgb * Params.x, 0.0);
                })";

            if (!R30CompilePixelShader(
                    device, BrightPs, "Bright",
                    &R30SkyGlow.bright) ||
                !R30CompilePixelShader(
                    device, BlurPs, "Blur",
                    &R30SkyGlow.blur) ||
                !R30CompilePixelShader(
                    device, CompositePs, "Composite",
                    &R30SkyGlow.composite))
            {
                R30ReleaseSkyGlowResources();
                return false;
            }

            // Resolve the 4 level-zero COM surfaces only on allocation/resize.
            // The same interfaces are valid until ReleaseSkyGlowResources/Reset.
            for (int eye = 0; eye < 2; ++eye)
            {
                if (FAILED(R30SkyGlow.reduced[eye]->GetSurfaceLevel(
                        0, &R30SkyGlow.reducedSurface[eye])) ||
                    !R30SkyGlow.reducedSurface[eye] ||
                    FAILED(R30SkyGlow.temp[eye]->GetSurfaceLevel(
                        0, &R30SkyGlow.tempSurface[eye])) ||
                    !R30SkyGlow.tempSurface[eye])
                {
                    R30ReleaseSkyGlowResources();
                    return false;
                }
            }

            R30SkyGlow.eyeWidth = frame.width;
            R30SkyGlow.eyeHeight = frame.height;
            R30SkyGlow.glowWidth = glowWidth;
            R30SkyGlow.glowHeight = glowHeight;
            R30SkyGlow.factor = factor;
            return true;
        }

        struct R30GlowVertex
        {
            float x, y, z, rhw;
            float u, v;
        };

        struct R30SkyGlowPassState
        {
            // Scoped to a single Present under R30ScopedInternalPass; no game
            // draw/state block runs between our private fullscreen passes.
            bool fixedConfigured = false;
            bool blendConfigured = false;
            bool additive = false;
            // The private eye passes are consecutive inside one Present;
            // neither the game nor a StateBlock::Apply can interleave.
            bool depthDetached = false;
            IDirect3DPixelShader9* activePixelShader = nullptr;
        };

        bool R30DrawSkyGlowPass(IDirect3DDevice9* device,
            R30SkyGlowPassState& passState,
            IDirect3DSurface9* target, UINT width, UINT height,
            IDirect3DTexture9* source,
            IDirect3DPixelShader9* shader,
            const float constant[4],
            bool additive)
        {
            if (!device || !target || !source || !shader ||
                !width || !height)
                return false;

            if (FAILED(device->SetRenderTarget(0, target)))
                return false;
            // Each private pass changes the RT, not the depth binding. Detach
            // once per Present instead of repeating a driver call for every
            // bright/blur/composite pass. The caller restores game depth last.
            if (!passState.depthDetached)
            {
                if (FAILED(device->SetDepthStencilSurface(nullptr)))
                    return false;
                passState.depthDetached = true;
            }

            // D3D9 SetRenderTarget resets the viewport to the full target.
            // These cached reduced/temporary surfaces have the exact extent
            // requested by the blur/bright passes, so their explicit viewport
            // setter was a redundant driver call on every eye and every frame.
            // Keep the original explicit viewport for eye composites/unknown
            // surfaces, which may not have the same dimensions as the caller.
            const bool knownReducedTarget =
                (target == R30SkyGlow.reducedSurface[0] ||
                 target == R30SkyGlow.reducedSurface[1] ||
                 target == R30SkyGlow.tempSurface[0] ||
                 target == R30SkyGlow.tempSurface[1]) &&
                width == R30SkyGlow.glowWidth &&
                height == R30SkyGlow.glowHeight;
            if (!knownReducedTarget)
            {
                D3DVIEWPORT9 viewport{};
                viewport.Width = width;
                viewport.Height = height;
                viewport.MinZ = 0.0f;
                viewport.MaxZ = 1.0f;
                if (FAILED(device->SetViewport(&viewport)))
                    return false;
            }

            const R30GlowVertex v[4]{
                { -0.5f, -0.5f, 0.0f, 1.0f, 0.0f, 0.0f },
                { static_cast<float>(width) - 0.5f, -0.5f,
                    0.0f, 1.0f, 1.0f, 0.0f },
                { -0.5f, static_cast<float>(height) - 0.5f,
                    0.0f, 1.0f, 0.0f, 1.0f },
                { static_cast<float>(width) - 0.5f,
                    static_cast<float>(height) - 0.5f,
                    0.0f, 1.0f, 1.0f, 1.0f }
            };

            // Eight or more stereo post passes share the same fixed sampler,
            // FVF and depth state. Only target/viewport, shader, texture,
            // constants and blend mode vary. Never cache across Presents.
            if (!passState.fixedConfigured)
            {
                device->SetVertexShader(nullptr);
                device->SetFVF(D3DFVF_XYZRHW | D3DFVF_TEX1);
                device->SetSamplerState(0, D3DSAMP_MINFILTER, D3DTEXF_LINEAR);
                device->SetSamplerState(0, D3DSAMP_MAGFILTER, D3DTEXF_LINEAR);
                device->SetSamplerState(0, D3DSAMP_MIPFILTER, D3DTEXF_NONE);
                device->SetSamplerState(0, D3DSAMP_ADDRESSU, D3DTADDRESS_CLAMP);
                device->SetSamplerState(0, D3DSAMP_ADDRESSV, D3DTADDRESS_CLAMP);
                device->SetRenderState(D3DRS_ZENABLE, D3DZB_FALSE);
                device->SetRenderState(D3DRS_ZWRITEENABLE, FALSE);
                device->SetRenderState(D3DRS_STENCILENABLE, FALSE);
                device->SetRenderState(D3DRS_ALPHATESTENABLE, FALSE);
                passState.fixedConfigured = true;
            }
            // Horizontal and optional vertical blur use the same shader.
            // Keep shader identity only until the caller applies the saved
            // game StateBlock; never cache across Present/Reset.
            if (passState.activePixelShader != shader)
            {
                if (FAILED(device->SetPixelShader(shader)))
                    return false;
                passState.activePixelShader = shader;
            }
            device->SetTexture(0, source);
            if (!passState.blendConfigured || passState.additive != additive)
            {
                device->SetRenderState(D3DRS_ALPHABLENDENABLE,
                    additive ? TRUE : FALSE);
                if (additive)
                {
                    device->SetRenderState(D3DRS_SRCBLEND, D3DBLEND_ONE);
                    device->SetRenderState(D3DRS_DESTBLEND, D3DBLEND_ONE);
                    device->SetRenderState(D3DRS_BLENDOP, D3DBLENDOP_ADD);
                    device->SetRenderState(D3DRS_COLORWRITEENABLE,
                        D3DCOLORWRITEENABLE_RED |
                        D3DCOLORWRITEENABLE_GREEN |
                        D3DCOLORWRITEENABLE_BLUE);
                }
                else
                {
                    device->SetRenderState(D3DRS_COLORWRITEENABLE,
                        D3DCOLORWRITEENABLE_RED |
                        D3DCOLORWRITEENABLE_GREEN |
                        D3DCOLORWRITEENABLE_BLUE |
                        D3DCOLORWRITEENABLE_ALPHA);
                }
                passState.additive = additive;
                passState.blendConfigured = true;
            }
            device->SetPixelShaderConstantF(0, constant, 1);
            const HRESULT hr = device->DrawPrimitiveUP(
                D3DPT_TRIANGLESTRIP, 2, v, sizeof(R30GlowVertex));
            device->SetTexture(0, nullptr);
            return SUCCEEDED(hr);
        }

        bool R30CaptureSkyGlowSceneBeforeHud(
            IDirect3DDevice9* device)
        {
            const auto frame = R29OwnerCaptureFrameSnapshot();
            if (!device || Settings::SkyGlowFactor <= 0 ||
                !frame.hadWorldStereo || !frame.hadDuplicatedDraw ||
                frame.rightDrawFailed || frame.stereoIncomplete ||
                !frame.backBuffer || !frame.rightEyeSurface)
                return false;

            if (R30SkyGlowSceneCaptureEpoch == frame.presentEpoch)
                return true;
            if (!R30EnsureSkyGlowResources(device))
                return false;

            IDirect3DSurface9* eyeSurface[2]{
                frame.backBuffer, frame.rightEyeSurface
            };
            bool ok = true;
            for (int eye = 0; eye < 2 && ok; ++eye)
            {
                if (!R30SkyGlow.reducedSurface[eye])
                    return false;
                ok = SUCCEEDED(device->StretchRect(
                    eyeSurface[eye], nullptr, R30SkyGlow.reducedSurface[eye],
                    nullptr, D3DTEXF_LINEAR));
            }
            if (ok)
                R30SkyGlowSceneCaptureEpoch = frame.presentEpoch;
            return ok;
        }

        bool R30ApplyStereoSkyGlow(IDirect3DDevice9* device)
        {
            const auto frame = R29OwnerCaptureFrameSnapshot();
            if (!device || Settings::SkyGlowFactor <= 0 ||
                !R29OwnerStereoWanted() || !frame.hadWorldStereo ||
                !frame.hadDuplicatedDraw || frame.rightDrawFailed ||
                frame.stereoIncomplete || !frame.backBuffer ||
                !frame.rightEyeSurface)
                return true;

            if (!R30EnsureSkyGlowResources(device))
                return false;

            IDirect3DStateBlock9* stateBlock = nullptr;
            IDirect3DSurface9* savedRt = nullptr;
            IDirect3DSurface9* savedDepth = nullptr;
            D3DVIEWPORT9 savedViewport{};
            if (FAILED(device->CreateStateBlock(
                    D3DSBT_ALL, &stateBlock)) ||
                !stateBlock ||
                FAILED(device->GetRenderTarget(0, &savedRt)) ||
                !savedRt ||
                FAILED(device->GetViewport(&savedViewport)))
            {
                if (savedRt) savedRt->Release();
                if (stateBlock) stateBlock->Release();
                return false;
            }
            const HRESULT depthHr =
                device->GetDepthStencilSurface(&savedDepth);
            const bool depthOk =
                SUCCEEDED(depthHr) || depthHr == D3DERR_NOTFOUND;
            if (!depthOk)
            {
                savedRt->Release();
                stateBlock->Release();
                return false;
            }

            bool ok = true;
            // The cache is private to this single Present, so no stale game
            // render state can be reused after StateBlock::Apply/Reset.
            R30SkyGlowPassState passState{};
            IDirect3DSurface9* eyeSurface[2]{
                frame.backBuffer, frame.rightEyeSurface
            };
            for (int eye = 0; eye < 2 && ok; ++eye)
            {
                IDirect3DSurface9* reduced = R30SkyGlow.reducedSurface[eye];
                IDirect3DSurface9* temp = R30SkyGlow.tempSurface[eye];
                if (!reduced || !temp)
                {
                    ok = false;
                    break;
                }

                if (R30SkyGlowSceneCaptureEpoch != frame.presentEpoch)
                {
                    ok = SUCCEEDED(device->StretchRect(
                        eyeSurface[eye], nullptr, reduced, nullptr,
                        D3DTEXF_LINEAR));
                }
                const float zero[4]{ 0, 0, 0, 0 };
                if (ok)
                {
                    // Bright pass overwrites the entire reduced target, so no
                    // Clear is needed. Clearing here before rebinding the RT
                    // would clear the game's current eye backbuffer.
                    ok = R30DrawSkyGlowPass(
                        device, passState, temp,
                        R30SkyGlow.glowWidth,
                        R30SkyGlow.glowHeight,
                        R30SkyGlow.reduced[eye],
                        R30SkyGlow.bright, zero, false);
                }

                const float horizontal[4]{
                    1.0f /
                        static_cast<float>(R30SkyGlow.glowWidth),
                    0.0f, 0.0f, 0.0f
                };
                if (ok)
                    ok = R30DrawSkyGlowPass(
                        device, passState, reduced,
                        R30SkyGlow.glowWidth,
                        R30SkyGlow.glowHeight,
                        R30SkyGlow.temp[eye],
                        R30SkyGlow.blur, horizontal, false);

                // TwoStep exists to reduce aliasing after a downsample.
                // At factor=1 there is no downsample, so a second full-resolution
                // blur only doubles bandwidth. Also make sure the vertical pass,
                // when requested for factor>1, is actually the composite source.
                const bool effectiveTwoStep =
                    Settings::SkyGlowTwoStep.get() &&
                    R30SkyGlow.factor > 1;
                // Horizontal blur writes reduced from temp. If the optional
                // vertical pass runs, it writes temp from reduced. Composite
                // exactly the texture most recently produced.
                IDirect3DTexture9* compositeSource =
                    R30SkyGlow.reduced[eye];
                if (effectiveTwoStep)
                {
                    const float vertical[4]{
                        0.0f,
                        1.0f /
                            static_cast<float>(R30SkyGlow.glowHeight),
                        0.0f, 0.0f
                    };
                    if (ok)
                        ok = R30DrawSkyGlowPass(
                            device, passState, temp,
                            R30SkyGlow.glowWidth,
                            R30SkyGlow.glowHeight,
                            R30SkyGlow.reduced[eye],
                            R30SkyGlow.blur, vertical, false);
                    if (ok)
                        compositeSource = R30SkyGlow.temp[eye];
                }

                const float composite[4]{ 0.38f, 0, 0, 0 };
                if (ok)
                    ok = R30DrawSkyGlowPass(
                        device, passState, eyeSurface[eye],
                        frame.width,
                        frame.height,
                        compositeSource,
                        R30SkyGlow.composite, composite, true);

            }

            // Apply the captured pipeline state first, then explicitly restore
            // RT/depth/viewport last. This guarantees the game bindings win even
            // if a driver/state-block implementation restores more state than
            // the code path historically relied on.
            bool restoreOk = SUCCEEDED(stateBlock->Apply());
            restoreOk =
                SUCCEEDED(device->SetRenderTarget(0, savedRt)) &&
                restoreOk;
            const HRESULT restoreDepth =
                device->SetDepthStencilSurface(savedDepth);
            restoreOk =
                (SUCCEEDED(restoreDepth) ||
                 (!savedDepth && restoreDepth == D3D_OK)) &&
                restoreOk;
            restoreOk =
                SUCCEEDED(device->SetViewport(&savedViewport)) &&
                restoreOk;
            savedRt->Release();
            if (savedDepth) savedDepth->Release();
            stateBlock->Release();

            if (ok && restoreOk)
            {
                ++R30SkyGlowFrames;
                if (!R30FirstSkyGlowLogged)
                {
                    R30FirstSkyGlowLogged = true;
                    spdlog::info(
                        "VR SKY GLOW: independent L/R extract + stereo blur + additive composite ACTIVE factor={} requestedTwoStep={} effectiveTwoStep={} buffer={}x{}",
                        R30SkyGlow.factor,
                        Settings::SkyGlowTwoStep.get() ? 1 : 0,
                        (Settings::SkyGlowTwoStep.get() && R30SkyGlow.factor > 1) ? 1 : 0,
                        R30SkyGlow.glowWidth,
                        R30SkyGlow.glowHeight);
                }
                return true;
            }

            ++R30SkyGlowFailures;
            if (!R30FirstSkyGlowFailureLogged)
            {
                R30FirstSkyGlowFailureLogged = true;
                spdlog::warn(
                    "VR SKY GLOW: stereo eye post-process failed; frame continues without enabling the stock mono glow chain");
            }
            return false;
        }

        ULONGLONG R30LastTelemetryMs = 0;

        void R30MaybeLogTelemetry()
        {
            if (!Settings::VRTelemetry)
                return;
            const ULONGLONG now = GetTickCount64();
            if (now - R30LastTelemetryMs < 5000)
                return;
            R30LastTelemetryMs = now;
            spdlog::info(
                "VR R30.9: bufferShadow[writes={},hits={},misses={},discardInvalid={},drawReadLocks=0] xyzrhw[world={},hud={},rhwPromote={},atomicFallback={},depthPreserve={},bilateralFallback={}] skyGlow[frames={},failures={},factor={},buffer={}x{}]",
                R30ShadowWrites, R30ShadowReadHits, R30ShadowReadMisses,
                R30ShadowDiscardInvalidations,
                R30XyzrhwWorldEffectDraws, R30XyzrhwHudDraws,
                R30XyzrhwRhwWorldPromotions,
                R30XyzrhwAtomicFallbacks,
                R30XyzrhwDepthPreserveFallbacks,
                R30XyzrhwBilateralFallbacks,
                R30SkyGlowFrames, R30SkyGlowFailures,
                R30SkyGlow.factor, R30SkyGlow.glowWidth,
                R30SkyGlow.glowHeight);
        }

        HRESULT __stdcall PresentDestR30(
            IDirect3DDevice9* device, const RECT* sourceRect,
            const RECT* destRect, HWND destWindowOverride,
            const RGNDATA* dirtyRegion)
        {
            // One phase-stable R29 view avoids redundant cross-TU POD assembly.
            const auto frame = R29OwnerCaptureFrameSnapshot();
            R30MaybeLogTelemetry();
            if (Settings::SkyGlowFactor > 0 &&
                R29OwnerStereoWanted() && frame.hadWorldStereo &&
                frame.hadDuplicatedDraw &&
                !frame.rightDrawFailed && !frame.stereoIncomplete)
            {
                R30ScopedInternalPass guard;
                R30ApplyStereoSkyGlow(device);
            }
            return R30PresentR29Hook.stdcall<HRESULT>(
                device, sourceRect, destRect,
                destWindowOverride, dirtyRegion);
        }

        HRESULT __stdcall ResetDestR30(
            IDirect3DDevice9* device,
            D3DPRESENT_PARAMETERS* params)
        {
            R30ReleaseSkyGlowResources();
            R30SkyGlowSceneCaptureEpoch = 0;
            R30FlatEffectGeometry = {};
            R30InvalidateXyzrhwWorldGeometry();
            R30HudContain = {};
            return R30ResetR29Hook.stdcall<HRESULT>(device, params);
        }

        // User-adjustable projection-space HUD scale. The per-eye FOV affine
        // remains automatic; this value is only a common-centre size trim after
        // the headset-specific mapping.
        float R30HudScaleValue() noexcept
        {
            return std::clamp(Settings::VRHudScale.get(), 0.30f, 1.20f);
        }

        float R30HudAspectCompensation(
            const OutRunVRRenderer::LatchedStereoFrame& stereo) noexcept
        {
            const auto frame = R29OwnerCaptureFrameSnapshot();
            if (!frame.width || !frame.height)
                return 1.0f;

            const float sourceAspect =
                static_cast<float>(frame.width) /
                static_cast<float>(frame.height);

            // R35.4: SharedPoseState already carries the runtime's actual
            // recommended per-eye render-target size. That pixel aspect is the
            // quantity that finally stretches a screen-space HUD sprite in the
            // OpenXR projection swapchain. Using angular FOV aspect was close,
            // but on Quest/VDXR it leaves circular HUD elements slightly tall.
            float targetAspectSum = 0.0f;
            int targetEyes = 0;
            for (std::uint32_t eye = 0; eye < 2; ++eye)
            {
                std::uint32_t w = 0, h = 0;
                if (!R29OwnerRecommendedEyeExtent(eye, w, h))
                    continue;
                const float aspect =
                    static_cast<float>(w) / static_cast<float>(h);
                if (!std::isfinite(aspect) ||
                    aspect < 0.25f || aspect > 4.0f)
                    continue;
                targetAspectSum += aspect;
                ++targetEyes;
            }

            // Fall back to the old angular estimate only if the host has not
            // published swapchain dimensions yet (startup/recovery).
            if (!targetEyes)
            {
                for (int eye = 0; eye < 2; ++eye)
                {
                    const float left =
                        std::tan(stereo.eyeFov[eye].angleLeft);
                    const float right =
                        std::tan(stereo.eyeFov[eye].angleRight);
                    const float up =
                        std::tan(stereo.eyeFov[eye].angleUp);
                    const float down =
                        std::tan(stereo.eyeFov[eye].angleDown);
                    const float horizontal = right - left;
                    const float vertical = up - down;
                    if (!std::isfinite(horizontal) ||
                        !std::isfinite(vertical) ||
                        horizontal <= 0.05f || vertical <= 0.05f)
                        continue;
                    const float aspect = horizontal / vertical;
                    if (!std::isfinite(aspect) ||
                        aspect < 0.25f || aspect > 4.0f)
                        continue;
                    targetAspectSum += aspect;
                    ++targetEyes;
                }
            }

            if (!targetEyes)
                return 1.0f;

            const float targetAspect =
                targetAspectSum / static_cast<float>(targetEyes);
            const float compensation = sourceAspect / targetAspect;
            if (!std::isfinite(compensation))
                return 1.0f;
            return std::clamp(compensation, 0.75f, 3.50f);
        }

        void R30HudContainScale(
            const OutRunVRRenderer::LatchedStereoFrame& stereo,
            float& scaleX, float& scaleY) noexcept
        {
            const auto frame = R29OwnerCaptureFrameSnapshot();
            const float userScale = R30HudScaleValue();
            const float fov[8]{
                stereo.eyeFov[0].angleLeft,
                stereo.eyeFov[0].angleRight,
                stereo.eyeFov[0].angleUp,
                stereo.eyeFov[0].angleDown,
                stereo.eyeFov[1].angleLeft,
                stereo.eyeFov[1].angleRight,
                stereo.eyeFov[1].angleUp,
                stereo.eyeFov[1].angleDown
            };
            bool canCache = frame.presentEpoch != 0 &&
                frame.width != 0 && frame.height != 0 &&
                std::isfinite(userScale);
            for (float angle : fov)
                canCache = canCache && std::isfinite(angle);

            bool fovMatches = true;
            for (int i = 0; i < 8; ++i)
                fovMatches = fovMatches &&
                    (R30HudContain.eyeFov[i] == fov[i]);
            if (canCache && R30HudContain.valid &&
                R30HudContain.presentEpoch == frame.presentEpoch &&
                R30HudContain.poseSequence == stereo.poseSequence &&
                R30HudContain.sourceWidth == frame.width &&
                R30HudContain.sourceHeight == frame.height &&
                R30HudContain.userScale == userScale &&
                fovMatches)
            {
                scaleX = R30HudContain.scaleX;
                scaleY = R30HudContain.scaleY;
                return;
            }

            // Untrusted startup, nonfinite FOV or resized frame cannot reuse
            // previous eye extent. The next Present always samples XR again.
            R30HudContain.valid = false;
            const float sourceOverTarget =
                R30HudAspectCompensation(stereo);

            // The existing contain math is unchanged: eye offset, Z/RHW,
            // source HUD geometry and SkyGlow are outside this CPU fastpath.
            if (sourceOverTarget >= 1.0f)
            {
                scaleX = userScale;
                scaleY = userScale / sourceOverTarget;
            }
            else
            {
                scaleX = userScale * sourceOverTarget;
                scaleY = userScale;
            }
            if (!canCache || !std::isfinite(scaleX) ||
                !std::isfinite(scaleY))
                return;

            R30HudContain.presentEpoch = frame.presentEpoch;
            R30HudContain.poseSequence = stereo.poseSequence;
            R30HudContain.sourceWidth = frame.width;
            R30HudContain.sourceHeight = frame.height;
            R30HudContain.userScale = userScale;
            for (int i = 0; i < 8; ++i)
                R30HudContain.eyeFov[i] = fov[i];
            R30HudContain.scaleX = scaleX;
            R30HudContain.scaleY = scaleY;
            R30HudContain.valid = true;
        }

        bool R30TransformHudScissor(
            const RECT& source, const D3DVIEWPORT9& viewport,
            float scaleX, float scaleY, float offsetX,
            RECT& transformed) noexcept
        {
            if (!std::isfinite(scaleX) || !std::isfinite(scaleY) ||
                !std::isfinite(offsetX) ||
                scaleX <= 0.0f || scaleY <= 0.0f ||
                viewport.Width == 0 || viewport.Height == 0)
                return false;

            const float leftBound = static_cast<float>(viewport.X);
            const float topBound = static_cast<float>(viewport.Y);
            const float rightBound =
                leftBound + static_cast<float>(viewport.Width);
            const float bottomBound =
                topBound + static_cast<float>(viewport.Height);
            const float centerX = 0.5f * (leftBound + rightBound);
            const float centerY = 0.5f * (topBound + bottomBound);
            const float pixelOffsetX =
                offsetX * static_cast<float>(viewport.Width) * 0.5f;

            auto mapX = [&](LONG x) {
                return centerX +
                    (static_cast<float>(x) - centerX) * scaleX +
                    pixelOffsetX;
            };
            auto mapY = [&](LONG y) {
                return centerY +
                    (static_cast<float>(y) - centerY) * scaleY;
            };

            const float l = std::clamp(mapX(source.left),
                leftBound, rightBound);
            const float r = std::clamp(mapX(source.right),
                leftBound, rightBound);
            const float t = std::clamp(mapY(source.top),
                topBound, bottomBound);
            const float b = std::clamp(mapY(source.bottom),
                topBound, bottomBound);

            transformed.left = static_cast<LONG>(std::floor((std::min)(l, r)));
            transformed.right = static_cast<LONG>(std::ceil((std::max)(l, r)));
            transformed.top = static_cast<LONG>(std::floor((std::min)(t, b)));
            transformed.bottom = static_cast<LONG>(std::ceil((std::max)(t, b)));
            return transformed.right > transformed.left &&
                transformed.bottom > transformed.top;
        }

        enum class R30ScreenSpaceKind : std::uint8_t
        {
            None,
            Hud2D,
            FlatPerspectiveEffect
        };

        R30ScreenSpaceKind R30ClassifyScreenSpacePass(
            IDirect3DDevice9* device) noexcept
        {
            if (!device || !R29OwnerTargetIsBackBuffer())
                return R30ScreenSpaceKind::None;

            float projection[16]{};
            if (!OutRunVRRenderer::GetRendererBaseProjection(projection))
                return R30ScreenSpaceKind::None;

            const auto projectionClass =
                OutRunVR::PassPolicy::ClassifyProjectionSignature(
                    projection[11], projection[15]);
            if (projectionClass ==
                OutRunVR::PassPolicy::ProjectionClass::Orthographic2D)
                return R30ScreenSpaceKind::Hud2D;

            if (projectionClass !=
                OutRunVR::PassPolicy::ProjectionClass::Perspective3D)
                return R30ScreenSpaceKind::None;

            // R29 already snapshots these exact game render states under
            // proven StateBlock Apply/recording coverage. Avoid repeating three
            // synchronous D3D9 driver queries for every perspective UI draw.
            // A stale/unreliable cache deliberately falls back to live state.
            R29OwnerEffectTelemetrySnapshot effect{};
            const bool haveCachedEffect =
                R29OwnerTryGetEffectTelemetrySnapshot(effect);
            DWORD zEnable = haveCachedEffect ? effect.zEnable : D3DZB_TRUE;
            DWORD alphaBlend = haveCachedEffect ? effect.alphaBlend : FALSE;
            DWORD alphaTest = haveCachedEffect ? effect.alphaTest : FALSE;
            if (!haveCachedEffect &&
                (FAILED(device->GetRenderState(D3DRS_ZENABLE, &zEnable)) ||
                 FAILED(device->GetRenderState(
                     D3DRS_ALPHABLENDENABLE, &alphaBlend)) ||
                 FAILED(device->GetRenderState(
                     D3DRS_ALPHATESTENABLE, &alphaTest))))
                return R30ScreenSpaceKind::None;

            if (zEnable == D3DZB_FALSE &&
                (alphaBlend != FALSE || alphaTest != FALSE))
                return R30ScreenSpaceKind::FlatPerspectiveEffect;
            return R30ScreenSpaceKind::None;
        }

        // Only the OpenXR pose/FOV signature affects this affine. Hundreds of
        // UI/XYZRHW draws in one frame otherwise repeat four tan() calls each.
        // Exact float-key comparison deliberately misses on NaN/FOV changes.
        struct R30EyeAffineCache
        {
            bool valid = false;
            std::uint32_t poseSequence = 0;
            float angleLeft[2]{};
            float angleRight[2]{};
            float eyeScale[2]{};
            float eyeOffset[2]{};
        };

        bool R30BuildEyeAffine(
            const OutRunVRRenderer::LatchedStereoFrame& stereo,
            float eyeScale[2], float eyeOffset[2]) noexcept
        {
            static thread_local R30EyeAffineCache cache{};
            if (cache.valid && cache.poseSequence == stereo.poseSequence &&
                cache.angleLeft[0] == stereo.eyeFov[0].angleLeft &&
                cache.angleRight[0] == stereo.eyeFov[0].angleRight &&
                cache.angleLeft[1] == stereo.eyeFov[1].angleLeft &&
                cache.angleRight[1] == stereo.eyeFov[1].angleRight)
            {
                eyeScale[0] = cache.eyeScale[0];
                eyeScale[1] = cache.eyeScale[1];
                eyeOffset[0] = cache.eyeOffset[0];
                eyeOffset[1] = cache.eyeOffset[1];
                return true;
            }

            // Do not retain an old success after an invalid/nonfinite packet.
            cache.valid = false;
            float tanLeft[2]{};
            float tanRight[2]{};
            float width[2]{};
            for (int eye = 0; eye < 2; ++eye)
            {
                tanLeft[eye] = std::tan(stereo.eyeFov[eye].angleLeft);
                tanRight[eye] = std::tan(stereo.eyeFov[eye].angleRight);
                width[eye] = tanRight[eye] - tanLeft[eye];
                if (!std::isfinite(tanLeft[eye]) ||
                    !std::isfinite(tanRight[eye]) ||
                    !std::isfinite(width[eye]) || width[eye] <= 0.05f)
                    return false;
            }

            const float commonLeft = 0.5f * (tanLeft[0] + tanLeft[1]);
            const float commonRight = 0.5f * (tanRight[0] + tanRight[1]);
            const float commonWidth = commonRight - commonLeft;
            const float commonSum = commonRight + commonLeft;
            if (!std::isfinite(commonWidth) || commonWidth <= 0.05f)
                return false;

            for (int eye = 0; eye < 2; ++eye)
            {
                const float eyeSum = tanRight[eye] + tanLeft[eye];
                const float scale = commonWidth / width[eye];
                const float offset = (commonSum - eyeSum) / width[eye];
                if (!std::isfinite(scale) || !std::isfinite(offset) ||
                    scale < 0.50f || scale > 1.50f ||
                    std::fabs(offset) > 0.50f)
                    return false;
                eyeScale[eye] = scale;
                eyeOffset[eye] = offset;
            }

            cache.poseSequence = stereo.poseSequence;
            for (int eye = 0; eye < 2; ++eye)
            {
                cache.angleLeft[eye] = stereo.eyeFov[eye].angleLeft;
                cache.angleRight[eye] = stereo.eyeFov[eye].angleRight;
                cache.eyeScale[eye] = eyeScale[eye];
                cache.eyeOffset[eye] = eyeOffset[eye];
            }
            cache.valid = true; // publish only after BOTH eyes pass all gates
            return true;
        }

        struct R30XyzrhwState
        {
            OutRunVRRenderer::LatchedStereoFrame stereo{};
            D3DVIEWPORT9 viewport{};
            float eyeScale[2]{};
            float eyeOffset[2]{};
            float worldScaleX[2]{};
            float worldOffsetX[2]{};
            float worldScaleY[2]{};
            float worldOffsetY[2]{};
            float parallaxPerRhwX[2]{};
            float parallaxPerRhwY[2]{};
            D3DMATRIX baseProjection{};
            D3DMATRIX inverseBaseProjection{};
            D3DMATRIX eyeProjection[2]{};
            D3DMATRIX eyeInverse[2]{};
            // OutRun's CPU-projected smoke/decal vertices use the same
            // eyeInverse * eyeProjection for every referenced vertex. Cache
            // that complete row-vector tail once per draw/eye.
            D3DMATRIX eyeTail[2]{};
            bool fullWorldReprojection = false;
            bool depthTestEnabled = false;
            bool rhwDepthEvidence = false;
            bool worldEffect = false;
        };

        // R30 XYZRHW world smoke/decal geometry has a latched pose and a
        // fixed game projection across multiple CPU-projected draws.  Cache
        // only projection-derived math, never per-draw evidence/viewport data.
        struct R30XyzrhwWorldGeometryCache
        {
            bool valid = false;
            float worldScale = 0.0f;
            R30XyzrhwState geometry{};
        };
        thread_local R30XyzrhwWorldGeometryCache R30XyzrhwWorldGeometry{};

        void R30InvalidateXyzrhwWorldGeometry() noexcept
        {
            R30XyzrhwWorldGeometry = {};
        }

        bool R30PrepareXyzrhwState(
            IDirect3DDevice9* device, R30XyzrhwState& state) noexcept
        {
            if (!R29OwnerStableStereoBase(device) ||
                R29OwnerCurrentVertexShaderIdentity() != 0)
                return false;

            // R33's final dispatcher and R29's setter/StateBlock shader
            // epoch agree when StateBlock coverage is reliable. Re-querying
            // GetVertexShader on every XYZRHW HUD/particle draw then stalls
            // the D3D9 driver without adding evidence. On coverage loss,
            // keep the original live null-shader check and fail closed.
            if (!OutRunVR::State::StateBlockTracker::Reliable())
            {
                IDirect3DVertexShader9* shader = nullptr;
                if (FAILED(device->GetVertexShader(&shader)))
                    return false;
                if (shader)
                {
                    shader->Release();
                    return false;
                }
            }

            DWORD fvf = 0;
            if (FAILED(device->GetFVF(&fvf)) ||
                (fvf & D3DFVF_POSITION_MASK) != D3DFVF_XYZRHW)
                return false;

            if (!R29OwnerEnsureStereoResources(device) ||
                // The tracked viewport is maintained by the same R23/R31
                // setter+StateBlock recovery owner as the R30 screen-space
                // replay guard. Query D3D9 only when that shadow is unavailable.
                (!R29OwnerTryGetTrackedViewport(state.viewport) &&
                 FAILED(device->GetViewport(&state.viewport))) ||
                state.viewport.Width == 0 || state.viewport.Height == 0 ||
                !std::isfinite(state.viewport.MinZ) ||
                !std::isfinite(state.viewport.MaxZ) ||
                state.viewport.MaxZ <= state.viewport.MinZ)
                return false;

            // R29's verified setter/StateBlock effect snapshot is the same
            // state used by stereo depth guards. Avoid one synchronous D3D9
            // driver read per XYZRHW draw while that snapshot is coherent.
            // On any cache-coverage/generation loss, preserve the live read.
            R29OwnerEffectTelemetrySnapshot depthEffect{};
            const bool haveCachedDepth =
                R29OwnerTryGetEffectTelemetrySnapshot(depthEffect);
            DWORD zEnable = haveCachedDepth
                ? depthEffect.zEnable : D3DZB_FALSE;
            if (!haveCachedDepth &&
                FAILED(device->GetRenderState(D3DRS_ZENABLE, &zEnable)))
                return false;
            state.depthTestEnabled = zEnable != D3DZB_FALSE;

            // One phase-stable R29 view avoids redundant cross-TU POD assembly.
            const auto frame = R29OwnerCaptureFrameSnapshot();
            if (!OutRunVRRenderer::GetLatchedStereoFrame(state.stereo) ||
                state.stereo.poseSequence == 0 ||
                (frame.poseSequence != 0 &&
                 frame.poseSequence != state.stereo.poseSequence) ||
                !R30BuildEyeAffine(state.stereo,
                    state.eyeScale, state.eyeOffset))
                return false;

            return true;
        }

        bool R30XyzrhwHasProjectedDepthSignature(
            const void* source, UINT vertexCount, UINT stride,
            const R30XyzrhwState& state, const D3DMATRIX& projection,
            const std::vector<std::uint8_t>* usedMask) noexcept
        {
            if (!source || vertexCount == 0 || stride < sizeof(float) * 4)
                return false;

            const float depthSpan =
                state.viewport.MaxZ - state.viewport.MinZ;
            if (!std::isfinite(depthSpan) || depthSpan <= 1.0e-6f ||
                std::fabs(projection._34) <= 1.0e-5f ||
                std::fabs(projection._13) > 1.0e-4f ||
                std::fabs(projection._23) > 1.0e-4f)
                return false;

            // Hoist the perspective-Z relation once per draw: 
            // ( (1/rhw - P44) / P34 * P33 + P43 ) * rhw
            // = P33/P34 + rhw * (P43 - P44 * P33/P34).
            // Projected smoke/sand may touch 512 vertices per draw; avoid
            // two floating-point divisions for each selected vertex.
            const float projectionDepthScale =
                projection._33 / projection._34;
            const float projectionDepthOffset =
                projection._43 - projection._44 * projectionDepthScale;
            const float inverseDepthSpan = 1.0f / depthSpan;
            const bool projectionDepthFast =
                std::isfinite(projectionDepthScale) &&
                std::isfinite(projectionDepthOffset) &&
                std::isfinite(inverseDepthSpan);

            UINT sampled = 0;
            UINT valid = 0;
            UINT projected = 0;
            for (UINT i = 0; i < vertexCount && sampled < 512u; ++i)
            {
                if (usedMask &&
                    (i >= usedMask->size() || (*usedMask)[i] == 0))
                    continue;
                ++sampled;
                const float* p = reinterpret_cast<const float*>(
                    static_cast<const std::uint8_t*>(source) +
                    static_cast<std::size_t>(i) * stride);
                const float z = p[2];
                const float rhw = p[3];
                if (!std::isfinite(z) || !std::isfinite(rhw) ||
                    rhw <= 1.0e-6f || rhw >= 1000.0f)
                    continue;

                float expectedNdcZ = projectionDepthScale +
                    projectionDepthOffset * rhw;
                float actualNdcZ =
                    (z - state.viewport.MinZ) * inverseDepthSpan;
                float depthDelta = std::fabs(expectedNdcZ - actualNdcZ);
                // Preserve the original division order on non-finite
                // projections or near the HUD/world decision boundary.
                // A small float-roundoff shift must not turn a score glyph
                // into a stereo world particle (or reject valid geometry).
                if (!projectionDepthFast || !std::isfinite(depthDelta) ||
                    std::fabs(depthDelta - 0.10f) <= 0.0005f)
                {
                    const float clipW = 1.0f / rhw;
                    const float viewZ =
                        (clipW - projection._44) / projection._34;
                    const float clipZ =
                        viewZ * projection._33 + projection._43;
                    expectedNdcZ = clipZ / clipW;
                    actualNdcZ =
                        (z - state.viewport.MinZ) / depthSpan;
                    depthDelta = std::fabs(expectedNdcZ - actualNdcZ);
                }
                if (!std::isfinite(expectedNdcZ) ||
                    !std::isfinite(actualNdcZ))
                    continue;

                ++valid;
                // True pre-transformed world particles have a coherent
                // projection relation between screen-Z and RHW. HUD glyphs can
                // use arbitrary RHW for sorting/scaling, which was the reason
                // the white position text was incorrectly promoted to 3D.
                if (std::fabs(rhw - 1.0f) > 0.02f && depthDelta <= 0.10f)
                    ++projected;
            }

            return sampled >= 3u && valid >= 3u && valid * 2u >= sampled && projected * 4u >= valid * 3u;
        }

        bool R30ConfigureXyzrhwWorldEffect(
            IDirect3DDevice9* device, const void* source,
            UINT vertexCount, UINT stride, R30XyzrhwState& state,
            const std::vector<std::uint8_t>* usedMask = nullptr) noexcept
        {
            float projectionRaw[16]{};
            D3DMATRIX baseProjection{};
            const bool haveBaseProjection =
                OutRunVRRenderer::GetRendererBaseProjection(projectionRaw);
            if (haveBaseProjection)
                std::memcpy(&baseProjection, projectionRaw, sizeof(baseProjection));

            state.rhwDepthEvidence =
                haveBaseProjection &&
                R30XyzrhwHasProjectedDepthSignature(
                    source, vertexCount, stride, state,
                    baseProjection, usedMask);

            // OutRun can disable Z after CPU-projecting smoke/skid/decal
            // billboards. The strengthened Z/RHW relation is the world-space
            // discriminator; white rank/score HUD glyphs fail this relation.
            if (state.depthTestEnabled && !state.rhwDepthEvidence)
                return false;
            state.worldEffect = state.rhwDepthEvidence;
            if (!state.worldEffect)
                return true;

            auto frame = R29OwnerCaptureFrameSnapshot();
            if (frame.trackedDepthStencil &&
                (!frame.rightDepthSynchronized || !frame.rightStencilSynchronized))
            {
                R29OwnerTryBootstrapRightDepth(device);
                // Resample synchronization bits after bootstrap.
                frame = R29OwnerCaptureFrameSnapshot();
            }
            if (frame.trackedDepthStencil &&
                !frame.rightDepthSynchronized && R29OwnerDepthTestActive(device))
                return false;
            if (frame.trackedDepthStencil &&
                !frame.rightStencilSynchronized && R29OwnerStencilTestActive(device))
                return false;

            if (!haveBaseProjection)
                return false;
            state.baseProjection = baseProjection;
            auto& geometryCache = R30XyzrhwWorldGeometry;
            const float worldScale =
                Settings::VRWorldScale * Settings::VRStereoDepth;
            const bool geometryCacheHit = geometryCache.valid &&
                geometryCache.worldScale == worldScale &&
                geometryCache.geometry.stereo.poseSequence == state.stereo.poseSequence &&
                std::memcmp(&geometryCache.geometry.baseProjection,
                    &state.baseProjection, sizeof(state.baseProjection)) == 0 &&
                std::memcmp(geometryCache.geometry.stereo.eyeOffset,
                    state.stereo.eyeOffset, sizeof(state.stereo.eyeOffset)) == 0 &&
                std::memcmp(geometryCache.geometry.stereo.eyeFov,
                    state.stereo.eyeFov, sizeof(state.stereo.eyeFov)) == 0;
            if (geometryCacheHit)
            {
                // Replay only the validated invariant geometry. Never reuse
                // the previous draw's RHW signature, depth-test, eye-affine,
                // viewport or stereo/frame ownership state.
                const auto& previous = geometryCache.geometry;
                state.inverseBaseProjection = previous.inverseBaseProjection;
                std::memcpy(state.eyeProjection, previous.eyeProjection,
                    sizeof(state.eyeProjection));
                std::memcpy(state.eyeInverse, previous.eyeInverse,
                    sizeof(state.eyeInverse));
                std::memcpy(state.eyeTail, previous.eyeTail,
                    sizeof(state.eyeTail));
                std::memcpy(state.worldScaleX, previous.worldScaleX,
                    sizeof(state.worldScaleX));
                std::memcpy(state.worldOffsetX, previous.worldOffsetX,
                    sizeof(state.worldOffsetX));
                std::memcpy(state.worldScaleY, previous.worldScaleY,
                    sizeof(state.worldScaleY));
                std::memcpy(state.worldOffsetY, previous.worldOffsetY,
                    sizeof(state.worldOffsetY));
                std::memcpy(state.parallaxPerRhwX, previous.parallaxPerRhwX,
                    sizeof(state.parallaxPerRhwX));
                std::memcpy(state.parallaxPerRhwY, previous.parallaxPerRhwY,
                    sizeof(state.parallaxPerRhwY));
                state.fullWorldReprojection = true;
            }
            else
            {
                // No stale optics after pose/recenter/projection/scale change;
                // publish only when both complete eye tails pass finite checks.
                geometryCache.valid = false;
            if (!R29OwnerMatrixFinite(baseProjection) ||
                std::fabs(baseProjection._11) < 0.01f ||
                std::fabs(baseProjection._22) < 0.01f ||
                std::fabs(baseProjection._34) < 0.25f ||
                !R29OwnerInvertMatrix(baseProjection, state.inverseBaseProjection) ||
                !R29OwnerMatrixFinite(state.inverseBaseProjection))
                return false;
            state.fullWorldReprojection = true;

            const float center[3]{
                0.5f * (state.stereo.eyeOffset[0][0] +
                        state.stereo.eyeOffset[1][0]),
                0.5f * (state.stereo.eyeOffset[0][1] +
                        state.stereo.eyeOffset[1][1]),
                0.5f * (state.stereo.eyeOffset[0][2] +
                        state.stereo.eyeOffset[1][2])
            };
            const float zero[3]{};

            for (int eye = 0; eye < 2; ++eye)
            {
                // Use the exact same per-eye rigid transform convention as the
                // normal fixed-function/world path: view * eyeInverse *
                // eyeProjection. The reconstructed CPU-projected point is
                // already in game view space, so only eyeInverse is applied
                // here; common head/camera motion must not be applied twice.
                // CPU-projected XYZRHW effects were generated from OutRun's
                // already head-synchronised camera. Reapplying the absolute HMD
                // eye orientation here rotates them twice and shifts smoke/skid
                // away from the road. Apply only the eye pose relative to the
                // common head centre; the asymmetric eye projection still owns
                // the final FOV.
                const float relativeEye[3]{
                    state.stereo.eyeOffset[eye][0] - center[0],
                    state.stereo.eyeOffset[eye][1] - center[1],
                    state.stereo.eyeOffset[eye][2] - center[2]
                };
                const float identityOrientation[4]{
                    0.0f, 0.0f, 0.0f, 1.0f
                };
                const D3DMATRIX eyePose =
                    R29OwnerMatrixFromQuaternionTranslation(
                        identityOrientation, relativeEye,
                        Settings::VRWorldScale * Settings::VRStereoDepth);
                state.eyeInverse[eye] = R29OwnerInverseRigid(eyePose);
                state.eyeProjection[eye] =
                    R29OwnerProjectionFromFov(baseProjection,
                        state.stereo.eyeFov[eye]);
                // Precompose the two eye-space matrices outside both vertex
                // loops. Row-vector order must remain inverse then projection.
                state.eyeTail[eye] = R29OwnerMultiplyMatrix(
                    state.eyeInverse[eye], state.eyeProjection[eye]);

                // Preserve a conservative affine fallback for vertices whose
                // clip reconstruction is unsafe. Its parallax uses the old
                // centered IPD estimate, but both eyes are forced to choose the
                // same fallback mode by R30TransformXyzrhwStereo().
                const float rel[3]{
                    state.stereo.eyeOffset[eye][0] - center[0],
                    state.stereo.eyeOffset[eye][1] - center[1],
                    state.stereo.eyeOffset[eye][2] - center[2]
                };
                // The source camera already owns common head rotation, so the
                // conservative affine fallback also uses head-relative IPD only.
                const float localX = rel[0];
                const float localY = rel[1];

                const D3DMATRIX& eyeProjection = state.eyeProjection[eye];
                state.worldScaleX[eye] =
                    eyeProjection._11 / baseProjection._11;
                state.worldOffsetX[eye] =
                    (eyeProjection._31 -
                     baseProjection._31 * state.worldScaleX[eye]) /
                    baseProjection._34;
                state.worldScaleY[eye] =
                    eyeProjection._22 / baseProjection._22;
                state.worldOffsetY[eye] =
                    (eyeProjection._32 -
                     baseProjection._32 * state.worldScaleY[eye]) /
                    baseProjection._34;
                state.parallaxPerRhwX[eye] =
                    -localX * Settings::VRWorldScale * Settings::VRStereoDepth *
                    eyeProjection._11;
                state.parallaxPerRhwY[eye] =
                    -localY * Settings::VRWorldScale * Settings::VRStereoDepth *
                    eyeProjection._22;

                if (!std::isfinite(state.worldScaleX[eye]) ||
                    !std::isfinite(state.worldOffsetX[eye]) ||
                    !std::isfinite(state.worldScaleY[eye]) ||
                    !std::isfinite(state.worldOffsetY[eye]) ||
                    !std::isfinite(state.parallaxPerRhwX[eye]) ||
                    !std::isfinite(state.parallaxPerRhwY[eye]) ||
                    !R29OwnerMatrixFinite(state.eyeProjection[eye]) ||
                    !R29OwnerMatrixFinite(state.eyeInverse[eye]) ||
                    !R29OwnerMatrixFinite(state.eyeTail[eye]) ||
                    state.worldScaleX[eye] < 0.20f ||
                    state.worldScaleX[eye] > 5.0f ||
                    state.worldScaleY[eye] < 0.20f ||
                    state.worldScaleY[eye] > 5.0f)
                    return false;
            }

                geometryCache.geometry = state;
                geometryCache.worldScale = worldScale;
                geometryCache.valid = true;
            }

            if (state.rhwDepthEvidence && !state.depthTestEnabled)
            {
                ++R30XyzrhwRhwWorldPromotions;
                if (!R30FirstXyzrhwRhwPromotionLogged)
                {
                    R30FirstXyzrhwRhwPromotionLogged = true;
                    spdlog::info(
                        "VR R30.6 XYZRHW WORLD: referenced RHW/depth signature promoted a depth-disabled particle/decal; normal-world eyeInverse/projection transform is shared");
                }
            }
            return true;
        }

        UINT R30PrimitiveElementCount(
            D3DPRIMITIVETYPE type, UINT primitiveCount) noexcept
        {
            switch (type)
            {
            case D3DPT_POINTLIST: return primitiveCount;
            case D3DPT_LINELIST: return primitiveCount * 2u;
            case D3DPT_LINESTRIP: return primitiveCount + 1u;
            case D3DPT_TRIANGLELIST: return primitiveCount * 3u;
            case D3DPT_TRIANGLESTRIP:
            case D3DPT_TRIANGLEFAN: return primitiveCount + 2u;
            default: return 0;
            }
        }

        // Seed the two world-particle eyes in ONE referenced-span walk. Both
        // draws consume the same validated source indices, but eye reprojection
        // modifies different XYZRHW values after this copy. A rare bilateral
        // fallback can also reseed just its successful eye independently.
        bool R30SeedWorldXyzrhwBuffers(
            const void* source, UINT vertexCount, UINT stride,
            std::vector<std::uint8_t>& left,
            std::vector<std::uint8_t>* right,
            const std::vector<std::uint8_t>* usedMask) noexcept
        {
            if (!source || !vertexCount || stride < sizeof(float) * 4)
                return false;
            const std::size_t bytes =
                static_cast<std::size_t>(vertexCount) * stride;
            if (!bytes || bytes > 4u * 1024u * 1024u ||
                (usedMask && usedMask->size() < vertexCount))
                return false;
            try
            {
                left.resize(bytes);
                if (right)
                    right->resize(bytes);
            }
            catch (...)
            {
                return false;
            }

            const auto* src = static_cast<const std::uint8_t*>(source);
            bool sparseCopied = false;
            if (usedMask && vertexCount >= 64u)
            {
                const auto selectedCount = std::count_if(
                    usedMask->begin(), usedMask->begin() + vertexCount,
                    [](std::uint8_t used) noexcept { return used != 0; });
                if (static_cast<std::size_t>(selectedCount) * 4u <= vertexCount)
                {
                    UINT cursor = 0;
                    while (cursor < vertexCount)
                    {
                        while (cursor < vertexCount && !(*usedMask)[cursor])
                            ++cursor;
                        const UINT begin = cursor;
                        while (cursor < vertexCount && (*usedMask)[cursor])
                            ++cursor;
                        if (begin != cursor)
                        {
                            const std::size_t offset =
                                static_cast<std::size_t>(begin) * stride;
                            const std::size_t runBytes =
                                static_cast<std::size_t>(cursor - begin) * stride;
                            std::memcpy(left.data() + offset,
                                src + offset, runBytes);
                            if (right)
                                std::memcpy(right->data() + offset,
                                    src + offset, runBytes);
                        }
                    }
                    sparseCopied = true;
                }
            }
            if (!sparseCopied)
            {
                std::memcpy(left.data(), source, bytes);
                if (right)
                    std::memcpy(right->data(), source, bytes);
            }
            return true;
        }

        bool R30TransformXyzrhwVertices(
            const void* source, UINT vertexCount, UINT stride,
            const R30XyzrhwState& state, int eye,
            std::vector<std::uint8_t>& out,
            const std::vector<std::uint8_t>* usedMask,
            bool allowFullReprojection, bool& usedFullReprojection,
            bool preseeded) noexcept
        {
            usedFullReprojection = false;
            if (!source || vertexCount == 0 || stride < sizeof(float) * 4 ||
                eye < 0 || eye > 1)
                return false;
            const std::size_t bytes =
                static_cast<std::size_t>(vertexCount) * stride;
            if (bytes == 0 || bytes > 4u * 1024u * 1024u)
                return false;
            if (usedMask && usedMask->size() < vertexCount)
                return false;

            // The shared world-particle prepass has already seeded both eye
            // buffers. On bilateral fallback, only the successful full eye
            // is reseeded from the original source before affine reprojection.
            if (preseeded)
            {
                if (out.size() != bytes)
                    return false;
            }
            else if (!R30SeedWorldXyzrhwBuffers(
                    source, vertexCount, stride, out, nullptr, usedMask))
                return false;

            const float x0 = static_cast<float>(state.viewport.X);
            const float y0 = static_cast<float>(state.viewport.Y);
            const float width = static_cast<float>(state.viewport.Width);
            const float height = static_cast<float>(state.viewport.Height);
            const float minZ = state.viewport.MinZ;
            const float maxZ = state.viewport.MaxZ;
            const float depthSpan = maxZ - minZ;
            if (width <= 0.0f || height <= 0.0f ||
                !std::isfinite(depthSpan) || depthSpan <= 1.0e-6f)
                return false;

            // Viewport extent is constant for this draw; avoid two floating-point
            // divides per XYZRHW vertex on both eye paths (smoke/sand/HUD).
            // The existing dimension/depth guards above remain authoritative.
            const float ndcScaleX = 2.0f / width;
            const float ndcScaleY = 2.0f / height;

            // The base-projection shape and XY determinant are invariant for
            // this draw (and for both eyes). Particle-heavy scenes used to
            // recompute all five guards and the determinant per vertex.
            // Preserve the inverse-projection fallback on unusual matrices.
            const D3DMATRIX& rhwBase = state.baseProjection;
            const float rhwDet =
                rhwBase._11 * rhwBase._22 - rhwBase._21 * rhwBase._12;
            const bool rhwPerspectiveFastPath =
                state.worldEffect && state.fullWorldReprojection &&
                allowFullReprojection &&
                std::fabs(rhwBase._14) <= 1.0e-5f &&
                std::fabs(rhwBase._24) <= 1.0e-5f &&
                std::fabs(rhwBase._34) > 1.0e-5f &&
                std::isfinite(rhwDet) &&
                std::fabs(rhwDet) > 1.0e-6f;

            // Projection ratios and viewport depth span remain invariant across
            // this draw's referenced smoke/sand/decal vertices. Preserve the
            // perspective-shape/finite guards and unusual-matrix fallback.
            const float invRhw34 = rhwPerspectiveFastPath
                ? 1.0f / rhwBase._34 : 0.0f;
            const float invRhwDet = rhwPerspectiveFastPath
                ? 1.0f / rhwDet : 0.0f;
            const float invDepthSpan = 1.0f / depthSpan;

            auto selected = [&](UINT i) noexcept
            {
                return !usedMask || (*usedMask)[i] != 0;
            };
            auto sourceVertex = [&](UINT i) noexcept -> const float*
            {
                return reinterpret_cast<const float*>(
                    static_cast<const std::uint8_t*>(source) +
                    static_cast<std::size_t>(i) * stride);
            };
            auto outputVertex = [&](UINT i) noexcept -> float*
            {
                return reinterpret_cast<float*>(
                    out.data() + static_cast<std::size_t>(i) * stride);
            };

            // The HUD contain calculation can read eye extent and fall back
            // to multiple FOV tan() calls. It is invariant across all vertices
            // in this latched draw; calculate it once, not per HUD vertex.
            float hudScaleX = 1.0f;
            float hudScaleY = 1.0f;
            if (!state.worldEffect)
                R30HudContainScale(state.stereo, hudScaleX, hudScaleY);

            if (state.worldEffect && state.fullWorldReprojection &&
                allowFullReprojection)
            {
                bool fullDrawOk = true;
                UINT selectedVertices = 0;
                // A rejected full projection needs to restore only the
                // XYZRHW headers already overwritten, not the entire VB span.
                UINT modifiedVertexEnd = 0;
                for (UINT i = 0; i < vertexCount; ++i)
                {
                    if (!selected(i))
                        continue;
                    ++selectedVertices;

                    const float* src = sourceVertex(i);
                    float* dst = outputVertex(i);
                    const float x = src[0];
                    const float y = src[1];
                    const float screenZ = src[2];
                    const float rhw = src[3];
                    if (!std::isfinite(x) || !std::isfinite(y) ||
                        !std::isfinite(screenZ) || !std::isfinite(rhw) ||
                        rhw <= 1.0e-6f || rhw >= 1000.0f)
                    {
                        fullDrawOk = false;
                        break;
                    }

                    const float ndcX = (x - x0) * ndcScaleX - 1.0f;
                    const float ndcY = 1.0f - (y - y0) * ndcScaleY;
                    const float clipW = 1.0f / rhw;
                    const float clipX = ndcX * clipW;
                    const float clipY = ndcY * clipW;

                    float restoredView[4]{};
                    bool restored = false;

                    // Pre-transformed D3D9 particles carry RHW = 1/clipW.
                    // For the normal OutRun perspective matrix, clipW gives
                    // view-Z directly and X/Y can then be solved from clip X/Y.
                    // This avoids depending on the particle's biased/clamped
                    // screen Z, which is exactly what caused smoke/decal draws
                    // to fall back to the approximate affine path.
                    const D3DMATRIX& bp = rhwBase;
                    if (rhwPerspectiveFastPath)
                    {
                        const float viewZ =
                            (clipW - bp._44) * invRhw34;
                        const float rhsX =
                            clipX - viewZ * bp._31 - bp._41;
                        const float rhsY =
                            clipY - viewZ * bp._32 - bp._42;
                        if (std::isfinite(viewZ) &&
                            std::isfinite(rhsX) &&
                            std::isfinite(rhsY))
                        {
                            const float viewX =
                                (rhsX * bp._22 -
                                 bp._21 * rhsY) * invRhwDet;
                            const float viewY =
                                (bp._11 * rhsY -
                                 rhsX * bp._12) * invRhwDet;
                            if (std::isfinite(viewX) &&
                                std::isfinite(viewY))
                            {
                                restoredView[0] = viewX;
                                restoredView[1] = viewY;
                                restoredView[2] = viewZ;
                                restoredView[3] = 1.0f;
                                restored = true;
                            }
                        }
                    }

                    // Compatibility fallback for an unusual projection shape:
                    // retain the previous inverse-projection reconstruction.
                    if (!restored)
                    {
                        const float ndcZ =
                            (screenZ - minZ) * invDepthSpan;
                        if (!std::isfinite(ndcZ) ||
                            ndcZ < -0.25f || ndcZ > 1.25f)
                        {
                            fullDrawOk = false;
                            break;
                        }
                        const float clip[4]{
                            clipX, clipY, ndcZ * clipW, clipW
                        };
                        float restoredViewH[4]{};
                        for (int col = 0; col < 4; ++col)
                            for (int row = 0; row < 4; ++row)
                                restoredViewH[col] += clip[row] *
                                    state.inverseBaseProjection.m[row][col];

                        if (!std::isfinite(restoredViewH[0]) ||
                            !std::isfinite(restoredViewH[1]) ||
                            !std::isfinite(restoredViewH[2]) ||
                            !std::isfinite(restoredViewH[3]) ||
                            std::fabs(restoredViewH[3]) <= 1.0e-6f)
                        {
                            fullDrawOk = false;
                            break;
                        }

                        const float invRestoredW =
                            1.0f / restoredViewH[3];
                        restoredView[0] =
                            restoredViewH[0] * invRestoredW;
                        restoredView[1] =
                            restoredViewH[1] * invRestoredW;
                        restoredView[2] =
                            restoredViewH[2] * invRestoredW;
                        restoredView[3] = 1.0f;
                    }

                    // Both eyes use the exact row-vector composition:
                    // game-view * eyeInverse * eyeProjection. Precomposing
                    // the matrix per draw removes one full 4x4 multiply for
                    // every particle vertex, while retaining all clip-W,
                    // Z/RHW, atomic and bilateral fallback checks below.
                    float clipEye[4]{};
                    for (int col = 0; col < 4; ++col)
                        for (int row = 0; row < 4; ++row)
                            clipEye[col] += restoredView[row] *
                                state.eyeTail[eye].m[row][col];

                    // D3D9 perspective clip-W must stay in front of the eye.
                    // abs(W) would accept a point behind the camera and mirror
                    // it back into the visible image.
                    if (!std::isfinite(clipEye[0]) ||
                        !std::isfinite(clipEye[1]) ||
                        !std::isfinite(clipEye[2]) ||
                        !std::isfinite(clipEye[3]) ||
                        clipEye[3] <= 1.0e-6f)
                    {
                        fullDrawOk = false;
                        break;
                    }

                    const float invEyeW = 1.0f / clipEye[3];
                    const float fullX = clipEye[0] * invEyeW;
                    const float fullY = clipEye[1] * invEyeW;
                    const float fullZ = clipEye[2] * invEyeW;
                    if (!std::isfinite(fullX) ||
                        !std::isfinite(fullY) ||
                        !std::isfinite(fullZ))
                    {
                        fullDrawOk = false;
                        break;
                    }

                    const float transformedX =
                        x0 + (fullX + 1.0f) * 0.5f * width;
                    const float transformedY =
                        y0 + (1.0f - fullY) * 0.5f * height;

                    // Decals/particles can intentionally bias screen Z beyond
                    // the strict viewport interval. Preserve the game's Z in
                    // that case, while still using the accurately reprojected
                    // eye X/Y and RHW. Falling the whole quad back to an affine
                    // shift was the visible left/right smoke/skid offset.
                    float transformedZ = screenZ;
                    if (fullZ >= 0.0f && fullZ <= 1.0f)
                    {
                        transformedZ = minZ + fullZ * depthSpan;
                    }
                    else
                    {
                        ++R30XyzrhwDepthPreserveFallbacks;
                    }
                    if (!std::isfinite(transformedX) ||
                        !std::isfinite(transformedY) ||
                        !std::isfinite(transformedZ))
                    {
                        fullDrawOk = false;
                        break;
                    }

                    dst[0] = transformedX;
                    dst[1] = transformedY;
                    dst[2] = transformedZ;
                    dst[3] = invEyeW;
                    modifiedVertexEnd = i + 1u;
                }

                if (fullDrawOk && selectedVertices != 0)
                {
                    usedFullReprojection = true;
                    return true;
                }

                ++R30XyzrhwAtomicFallbacks;
                if (!R30FirstXyzrhwAtomicFallbackLogged)
                {
                    R30FirstXyzrhwAtomicFallbackLogged = true;
                    spdlog::info(
                        "VR R30.6 XYZRHW WORLD: full reprojection rejected for a referenced vertex; this eye candidate is discarded before bilateral fallback selection");
                }
                // The initial full or sparse copy already preserved all
                // colour/UV/other vertex attributes. Full reprojection only
                // modified the four XYZRHW floats of referenced vertices;
                // restore that prefix up to the last successful write, then
                // run the original affine fallback on both eyes as before.
                for (UINT i = 0; i < modifiedVertexEnd; ++i)
                {
                    if (selected(i))
                        std::memcpy(outputVertex(i), sourceVertex(i),
                            4u * sizeof(float));
                }
            }

            for (UINT i = 0; i < vertexCount; ++i)
            {
                if (!selected(i))
                    continue;

                float* p = outputVertex(i);
                const float x = p[0];
                const float y = p[1];
                const float z = p[2];
                const float rhw = p[3];
                if (!std::isfinite(x) || !std::isfinite(y) ||
                    !std::isfinite(z) || !std::isfinite(rhw))
                    return false;

                const float ndcX = (x - x0) * ndcScaleX - 1.0f;
                const float ndcY = 1.0f - (y - y0) * ndcScaleY;

                float correctedX = 0.0f;
                float correctedY = 0.0f;
                if (state.worldEffect)
                {
                    correctedX =
                        state.worldScaleX[eye] * ndcX +
                        state.worldOffsetX[eye];
                    correctedY =
                        state.worldScaleY[eye] * ndcY +
                        state.worldOffsetY[eye];
                    if (rhw > 0.0f && rhw < 1000.0f)
                    {
                        correctedX +=
                            state.parallaxPerRhwX[eye] * rhw;
                        correctedY +=
                            state.parallaxPerRhwY[eye] * rhw;
                    }
                    // Fallback keeps the game's original Z/RHW pair intact.
                }
                else
                {
                    // Screen-locked HUD must preserve its pixel aspect ratio.
                    // Applying the horizontal OpenXR FOV scale only to X made
                    // circular gauges vertically elongated on both SBS and HMD.
                    // Keep one uniform user scale on X/Y and retain only the
                    // per-eye asymmetric-FOV centre offset for convergence.
                    correctedX =
                        hudScaleX * state.eyeScale[eye] * ndcX + state.eyeOffset[eye];
                    correctedY = hudScaleY * ndcY;
                }

                const float transformedX =
                    x0 + (correctedX + 1.0f) * 0.5f * width;
                const float transformedY =
                    y0 + (1.0f - correctedY) * 0.5f * height;
                if (!std::isfinite(transformedX) ||
                    !std::isfinite(transformedY))
                    return false;
                p[0] = transformedX;
                p[1] = transformedY;
            }
            return true;
        }

        bool R30TransformXyzrhwStereo(
            const void* source, UINT vertexCount, UINT stride,
            const R30XyzrhwState& state,
            std::vector<std::uint8_t>& left,
            std::vector<std::uint8_t>& right,
            const std::vector<std::uint8_t>* usedMask = nullptr) noexcept
        {
            // Fuse both non-indexed and indexed ScreenHud eyes in one CPU walk.
            // Preserve Z/RHW, UV, color and the original asymmetric FOV math;
            // world/particle reprojection stays on the bilateral fallback.
            if (!state.worldEffect)
            {
                if (!source || !vertexCount || stride < sizeof(float) * 4)
                    return false;
                const std::size_t bytes =
                    static_cast<std::size_t>(vertexCount) * stride;
                if (!bytes || bytes > 4u * 1024u * 1024u ||
                    (usedMask && usedMask->size() < vertexCount))
                    return false;
                const float x0 = static_cast<float>(state.viewport.X);
                const float y0 = static_cast<float>(state.viewport.Y);
                const float width = static_cast<float>(state.viewport.Width);
                const float height = static_cast<float>(state.viewport.Height);
                const float depthSpan =
                    state.viewport.MaxZ - state.viewport.MinZ;
                if (width <= 0.0f || height <= 0.0f ||
                    !std::isfinite(depthSpan) || depthSpan <= 1.0e-6f)
                    return false;
                try
                {
                    left.resize(bytes);
                    right.resize(bytes);
                }
                catch (...)
                {
                    return false;
                }
                // Sparse indexed HUD reads only referenced vertices. Avoid
                // two full-span copies on lightly used VB/IB regions; both
                // eyes share one reference mask and one contiguous-run scan.
                bool sparseCopied = false;
                if (usedMask && vertexCount >= 64u)
                {
                    const auto selectedCount = std::count_if(
                        usedMask->begin(), usedMask->begin() + vertexCount,
                        [](std::uint8_t selected) noexcept {
                            return selected != 0;
                        });
                    if (static_cast<std::size_t>(selectedCount) * 4u <= vertexCount)
                    {
                        const auto* srcBytes =
                            static_cast<const std::uint8_t*>(source);
                        UINT cursor = 0;
                        while (cursor < vertexCount)
                        {
                            while (cursor < vertexCount && !(*usedMask)[cursor])
                                ++cursor;
                            const UINT begin = cursor;
                            while (cursor < vertexCount && (*usedMask)[cursor])
                                ++cursor;
                            if (begin != cursor)
                            {
                                const std::size_t offset =
                                    static_cast<std::size_t>(begin) * stride;
                                const std::size_t runBytes =
                                    static_cast<std::size_t>(cursor - begin) * stride;
                                std::memcpy(left.data() + offset,
                                    srcBytes + offset, runBytes);
                                std::memcpy(right.data() + offset,
                                    srcBytes + offset, runBytes);
                            }
                        }
                        sparseCopied = true;
                    }
                }
                if (!sparseCopied)
                {
                    std::memcpy(left.data(), source, bytes);
                    std::memcpy(right.data(), source, bytes);
                }
                float hudScaleX = 1.0f;
                float hudScaleY = 1.0f;
                R30HudContainScale(state.stereo, hudScaleX, hudScaleY);
                const float ndcScaleX = 2.0f / width;
                const float ndcScaleY = 2.0f / height;
                const float eyeScaleX[2]{
                    hudScaleX * state.eyeScale[0],
                    hudScaleX * state.eyeScale[1]
                };
                for (UINT i = 0; i < vertexCount; ++i)
                {
                    if (usedMask && !(*usedMask)[i])
                        continue;
                    const std::size_t offset =
                        static_cast<std::size_t>(i) * stride;
                    const auto* src = reinterpret_cast<const float*>(
                        static_cast<const std::uint8_t*>(source) + offset);
                    if (!std::isfinite(src[0]) || !std::isfinite(src[1]) ||
                        !std::isfinite(src[2]) || !std::isfinite(src[3]))
                        return false;
                    const float ndcX = (src[0] - x0) * ndcScaleX - 1.0f;
                    const float ndcY = 1.0f - (src[1] - y0) * ndcScaleY;
                    const float correctedY = hudScaleY * ndcY;
                    const float transformedY =
                        y0 + (1.0f - correctedY) * 0.5f * height;
                    if (!std::isfinite(transformedY))
                        return false;
                    for (int eye = 0; eye < 2; ++eye)
                    {
                        const float correctedX =
                            eyeScaleX[eye] * ndcX + state.eyeOffset[eye];
                        const float transformedX =
                            x0 + (correctedX + 1.0f) * 0.5f * width;
                        if (!std::isfinite(transformedX))
                            return false;
                        auto* dst = reinterpret_cast<float*>(
                            (eye == 0 ? left.data() : right.data()) + offset);
                        dst[0] = transformedX;
                        dst[1] = transformedY;
                    }
                }
                return true;
            }

            // This is the high-frequency indexed smoke/sand/decal path:
            // one sparse-mask population count and one contiguous-run scan
            // seeds both eye scratch buffers before per-eye projection work.
            if (!R30SeedWorldXyzrhwBuffers(
                    source, vertexCount, stride, left, &right, usedMask))
                return false;

            bool leftFull = false;
            bool rightFull = false;
            if (!R30TransformXyzrhwVertices(source, vertexCount, stride,
                    state, 0, left, usedMask, true, leftFull, true) ||
                !R30TransformXyzrhwVertices(source, vertexCount, stride,
                    state, 1, right, usedMask, true, rightFull, true))
                return false;

            if (leftFull != rightFull)
            {
                ++R30XyzrhwBilateralFallbacks;
                if (!R30FirstXyzrhwBilateralFallbackLogged)
                {
                    R30FirstXyzrhwBilateralFallbackLogged = true;
                    spdlog::info(
                        "VR R30.6 XYZRHW WORLD: one eye rejected full reprojection; both eyes are forced onto the same affine fallback policy");
                }
                // A rejected eye has already completed its own affine
                // fallback inside R30TransformXyzrhwVertices. Only rerun the
                // eye that *succeeded* at full reprojection: both outputs then
                // share the same conservative affine policy without a third
                // traversal/copy of the eye that already fell back.
                bool ignored = false;
                if (leftFull &&
                    !R30TransformXyzrhwVertices(source, vertexCount, stride,
                        state, 0, left, usedMask, false, ignored, false))
                    return false;
                if (rightFull &&
                    !R30TransformXyzrhwVertices(source, vertexCount, stride,
                        state, 1, right, usedMask, false, ignored, false))
                    return false;
            }
            return true;
        }

        template <typename LeftDraw, typename RightDraw>
        HRESULT R30ExecuteXyzrhwStereo(
            IDirect3DDevice9* device, const R30XyzrhwState& state,
            LeftDraw&& leftDraw, RightDraw&& rightDraw,
            const char* site)
        {
            if (!state.worldEffect)
                R30CaptureSkyGlowSceneBeforeHud(device);

            R29OwnerNoteStereoDrawWithoutMonoBackup();
            if (R29OwnerLeftDrawMayWriteDepth(device) ||
                R29OwnerLeftDrawMayWriteStencil(device))
                R29OwnerNoteMainDepthContentWrite();

            const HRESULT leftHr = leftDraw();
            if (FAILED(leftHr))
            {
                R29OwnerReportStereoFailure(OutRunVR::StereoFailureLeftDrawFailed,
                    site, leftHr);
                R29OwnerArmMonoSafety();
                return leftHr;
            }

            // Capture after the left-eye draw; reuse one coherent R29 owner view.
            const auto frame = R29OwnerCaptureFrameSnapshot();
            IDirect3DSurface9* savedRt = R29OwnerBorrowTrackedRenderTarget();
            IDirect3DSurface9* savedDepth = frame.trackedDepthStencil;
            HRESULT rightHr = D3D_OK;
            OutRunVR::StereoFailureReason rightFailure =
                OutRunVR::StereoFailureRightStateFailed;
            bool restoreOk = true;
            {
                R30ScopedInternalPass guard;
                rightHr = R29OwnerCallOriginalSetRenderTarget(
                    device, 0u, frame.rightEyeSurface);
                if (SUCCEEDED(rightHr))
                    rightHr = R29OwnerCallOriginalSetDepthStencilSurface(
                        device, frame.trackedDepthStencil ? frame.rightEyeDepth : nullptr);
                if (SUCCEEDED(rightHr))
                    rightHr = device->SetViewport(&state.viewport);
                if (SUCCEEDED(rightHr))
                {
                    rightFailure =
                        OutRunVR::StereoFailureRightDrawFailed;
                    rightHr = rightDraw();
                }
                restoreOk = R29OwnerRestoreRightPassState(device,
                    savedRt, savedDepth, state.viewport, nullptr, false);
            }

            R29OwnerNoteStableTwoEyeDraw();
            if (state.worldEffect)
            {
                ++R30XyzrhwWorldEffectDraws;
                R29OwnerRecordXyzrhwWorldStereoDuplicate(
                    state.stereo.poseSequence, state.stereo);
                if (!R30FirstXyzrhwWorldLogged)
                {
                    R30FirstXyzrhwWorldLogged = true;
                    spdlog::info(
                        "VR R30.4 XYZRHW WORLD: pre-transformed particle/billboard/decal draws reconstruct clip X/Y/Z/RHW, unproject through the game projection, then reproject into each OpenXR eye; affine RHW fallback retained for unsafe vertices");
                }
            }
            else
            {
                R29OwnerRecordHudStereoDuplicate();
                ++R30XyzrhwHudDraws;
                if (!R30FirstXyzrhwHudLogged)
                {
                    R30FirstXyzrhwHudLogged = true;
                    spdlog::info(
                        "VR R30.8 XYZRHW HUD: pre-transformed fixed-function HUD applies source-aspect/eye-FOV X compensation before SBS/DirectGPU projection; circular gauges preserve final HMD aspect ratio");
                }
            }

            if (FAILED(rightHr))
            {
                R29OwnerMarkRightDrawFailed();
                R29OwnerInvalidateRightDepthStencilIfLeftMayWrite(device);
                R29OwnerReportStereoFailure(rightFailure, site, rightHr);
                R29OwnerArmMonoSafety();
            }
            if (!restoreOk)
            {
                R29OwnerInvalidateRightDepthStencilIfLeftMayWrite(device);
                R29OwnerNoteRestoreFailure("R30.2 XYZRHW right-eye draw");
                R29OwnerArmMonoSafety();
            }
            return leftHr;
        }

        HRESULT R30TryXyzrhwPrimitiveUP(
            IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
            UINT primitiveCount, const void* data, UINT stride)
        {
            R30XyzrhwState state{};
            if (!R30PrepareXyzrhwState(device, state))
                return E_NOTIMPL;
            const UINT vertexCount =
                R30PrimitiveElementCount(type, primitiveCount);
            if (!vertexCount || vertexCount > 262144u)
                return E_NOTIMPL;
            if (!R30ConfigureXyzrhwWorldEffect(
                    device, data, vertexCount, stride, state))
            {
                ++R30XyzrhwFallbacks;
                return E_NOTIMPL;
            }

            R30ScratchLease lease;
            if (!lease)
                return E_NOTIMPL;
            auto& scratch = *lease.buffers;
            if (!R30TransformXyzrhwStereo(
                    data, vertexCount, stride, state,
                    scratch.left, scratch.right))
            {
                ++R30XyzrhwFallbacks;
                return E_NOTIMPL;
            }

            auto leftDraw = [&]() {
                return R29OwnerCallRawDrawPrimitiveUP(
                    device, type, primitiveCount,
                    scratch.left.data(), stride);
            };
            auto rightDraw = [&]() {
                return R29OwnerCallRawDrawPrimitiveUP(
                    device, type, primitiveCount,
                    scratch.right.data(), stride);
            };
            return R30ExecuteXyzrhwStereo(
                device, state, leftDraw, rightDraw,
                "R30.6/DrawPrimitiveUP-XYZRHW");
        }

        HRESULT R30TryXyzrhwIndexedPrimitiveUP(
            IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
            UINT minVertexIndex, UINT numVertices, UINT primitiveCount,
            const void* indexData, D3DFORMAT indexFormat,
            const void* vertexData, UINT stride)
        {
            R30XyzrhwState state{};
            if (!R30PrepareXyzrhwState(device, state))
                return E_NOTIMPL;

            const UINT indexCount =
                R30PrimitiveElementCount(type, primitiveCount);
            if (!indexData || !vertexData || indexCount == 0 ||
                (indexFormat != D3DFMT_INDEX16 &&
                 indexFormat != D3DFMT_INDEX32))
                return E_NOTIMPL;

            UINT maxIndex = 0;
            if (indexFormat == D3DFMT_INDEX16)
            {
                const auto* indices =
                    static_cast<const std::uint16_t*>(indexData);
                for (UINT i = 0; i < indexCount; ++i)
                    maxIndex = std::max<UINT>(maxIndex, indices[i]);
            }
            else
            {
                const auto* indices =
                    static_cast<const std::uint32_t*>(indexData);
                for (UINT i = 0; i < indexCount; ++i)
                    maxIndex = std::max(maxIndex, indices[i]);
            }

            const UINT vertexCount =
                std::max<UINT>(minVertexIndex + numVertices,
                    maxIndex + 1u);
            if (vertexCount == 0 || vertexCount > 262144u)
                return E_NOTIMPL;

            R30ScratchLease lease;
            if (!lease)
                return E_NOTIMPL;
            auto& scratch = *lease.buffers;
            try
            {
                scratch.used.assign(vertexCount, 0);
            }
            catch (...)
            {
                return E_NOTIMPL;
            }
            for (UINT i = 0; i < indexCount; ++i)
            {
                const std::uint32_t raw =
                    indexFormat == D3DFMT_INDEX16
                    ? static_cast<const std::uint16_t*>(indexData)[i]
                    : static_cast<const std::uint32_t*>(indexData)[i];
                if (raw >= vertexCount)
                    return E_NOTIMPL;
                scratch.used[raw] = 1;
            }

            if (!R30ConfigureXyzrhwWorldEffect(
                    device, vertexData, vertexCount, stride, state,
                    &scratch.used))
            {
                ++R30XyzrhwFallbacks;
                return E_NOTIMPL;
            }

            if (!R30TransformXyzrhwStereo(
                    vertexData, vertexCount, stride, state,
                    scratch.left, scratch.right, &scratch.used))
            {
                ++R30XyzrhwFallbacks;
                return E_NOTIMPL;
            }

            auto leftDraw = [&]() {
                return R29OwnerCallRawDrawIndexedPrimitiveUP(
                    device, type, minVertexIndex, numVertices,
                    primitiveCount, indexData, indexFormat,
                    scratch.left.data(), stride);
            };
            auto rightDraw = [&]() {
                return R29OwnerCallRawDrawIndexedPrimitiveUP(
                    device, type, minVertexIndex, numVertices,
                    primitiveCount, indexData, indexFormat,
                    scratch.right.data(), stride);
            };
            return R30ExecuteXyzrhwStereo(
                device, state, leftDraw, rightDraw,
                "R30.6/DrawIndexedPrimitiveUP-XYZRHW");
        }


        HRESULT R30TryXyzrhwPrimitiveVB(
            IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
            UINT startVertex, UINT primitiveCount)
        {
            R30XyzrhwState state{};
            if (!R30PrepareXyzrhwState(device, state))
                return E_NOTIMPL;

            const UINT vertexCount =
                R30PrimitiveElementCount(type, primitiveCount);
            if (!vertexCount || vertexCount > 262144u)
                return E_NOTIMPL;

            IDirect3DVertexBuffer9* vb = nullptr;
            UINT streamOffset = 0;
            UINT stride = 0;
            if (FAILED(device->GetStreamSource(
                    0, &vb, &streamOffset, &stride)) ||
                !vb || stride < sizeof(float) * 4)
            {
                if (vb) vb->Release();
                return E_NOTIMPL;
            }

            R30EnsureVertexBufferHooks(vb);
            // D3D9 buffer descriptors are immutable while their COM objects live.
            // Reuse the registered shadow metadata instead of a GetDesc per draw.
            const auto vbShadow = R30EnsureVertexShadow(vb);
            if (!vbShadow)
            {
                vb->Release();
                return E_NOTIMPL;
            }
            const std::uint64_t firstByte =
                static_cast<std::uint64_t>(streamOffset) +
                static_cast<std::uint64_t>(startVertex) * stride;
            const std::uint64_t byteCount =
                static_cast<std::uint64_t>(vertexCount) * stride;
            if (firstByte > vbShadow->size ||
                byteCount > vbShadow->size - firstByte ||
                firstByte > UINT_MAX || byteCount > UINT_MAX)
            {
                vb->Release();
                return E_NOTIMPL;
            }

            R30ScratchLease lease;
            if (!lease)
            {
                vb->Release();
                return E_NOTIMPL;
            }
            auto& scratch = *lease.buffers;
            if (!R30CopyVertexShadow(vbShadow,
                    static_cast<UINT>(firstByte),
                    static_cast<UINT>(byteCount), scratch.source,
                    scratch.vertexCopy))
            {
                vb->Release();
                ++R30XyzrhwFallbacks;
                return E_NOTIMPL;
            }

            if (!R30ConfigureXyzrhwWorldEffect(
                    device, scratch.source.data(), vertexCount,
                    stride, state) ||
                !R30TransformXyzrhwStereo(
                    scratch.source.data(), vertexCount, stride, state,
                    scratch.left, scratch.right))
            {
                vb->Release();
                ++R30XyzrhwFallbacks;
                return E_NOTIMPL;
            }

            auto leftDraw = [&]() {
                return R29OwnerCallRawDrawPrimitiveUP(
                    device, type, primitiveCount,
                    scratch.left.data(), stride);
            };
            auto rightDraw = [&]() {
                return R29OwnerCallRawDrawPrimitiveUP(
                    device, type, primitiveCount,
                    scratch.right.data(), stride);
            };
            const HRESULT hr = R30ExecuteXyzrhwStereo(
                device, state, leftDraw, rightDraw,
                "R30.6/DrawPrimitiveVB-ShadowXYZRHW");

            {
                R30ScopedInternalPass guard;
                if (FAILED(device->SetStreamSource(
                        0, vb, streamOffset, stride)))
                {
                    R29OwnerNoteRestoreFailure("R30.6 VB stream restore");
                    R29OwnerArmMonoSafety();
                }
            }
            vb->Release();
            return hr;
        }

        HRESULT R30TryXyzrhwIndexedPrimitiveVB(
            IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
            INT baseVertexIndex, UINT minVertexIndex, UINT numVertices,
            UINT startIndex, UINT primitiveCount)
        {
            R30XyzrhwState state{};
            if (!R30PrepareXyzrhwState(device, state))
                return E_NOTIMPL;

            const UINT indexCount =
                R30PrimitiveElementCount(type, primitiveCount);
            if (!indexCount || !numVertices || indexCount > 524288u)
                return E_NOTIMPL;

            IDirect3DVertexBuffer9* vb = nullptr;
            IDirect3DIndexBuffer9* ib = nullptr;
            UINT streamOffset = 0;
            UINT stride = 0;
            if (FAILED(device->GetStreamSource(
                    0, &vb, &streamOffset, &stride)) ||
                !vb || stride < sizeof(float) * 4 ||
                FAILED(device->GetIndices(&ib)) || !ib)
            {
                if (ib) ib->Release();
                if (vb) vb->Release();
                return E_NOTIMPL;
            }

            R30EnsureVertexBufferHooks(vb);
            R30EnsureIndexBufferHooks(ib);
            const auto vbShadow = R30EnsureVertexShadow(vb);
            const auto ibShadow = R30EnsureIndexShadow(ib);
            if (!vbShadow || !ibShadow ||
                (ibShadow->indexFormat != D3DFMT_INDEX16 &&
                 ibShadow->indexFormat != D3DFMT_INDEX32))
            {
                ib->Release();
                vb->Release();
                return E_NOTIMPL;
            }
            const UINT indexSize =
                ibShadow->indexFormat == D3DFMT_INDEX16 ? 2u : 4u;
            const std::uint64_t firstIndexByte =
                static_cast<std::uint64_t>(startIndex) * indexSize;
            const std::uint64_t indexBytes =
                static_cast<std::uint64_t>(indexCount) * indexSize;
            if (firstIndexByte > ibShadow->size ||
                indexBytes > ibShadow->size - firstIndexByte ||
                firstIndexByte > UINT_MAX || indexBytes > UINT_MAX)
            {
                ib->Release();
                vb->Release();
                return E_NOTIMPL;
            }

            R30ScratchLease lease;
            if (!lease)
            {
                ib->Release();
                vb->Release();
                return E_NOTIMPL;
            }
            auto& scratch = *lease.buffers;
            if (!R30CopyIndexShadow(ibShadow,
                    static_cast<UINT>(firstIndexByte),
                    static_cast<UINT>(indexBytes), scratch.indexSource,
                    scratch.indexCopy))
            {
                ib->Release();
                vb->Release();
                ++R30XyzrhwFallbacks;
                return E_NOTIMPL;
            }

            try
            {
                scratch.physical.resize(indexCount);
            }
            catch (...)
            {
                ib->Release();
                vb->Release();
                return E_NOTIMPL;
            }

            std::int64_t minPhysical = INT64_MAX;
            std::int64_t maxPhysical = INT64_MIN;
            for (UINT i = 0; i < indexCount; ++i)
            {
                const std::uint32_t raw =
                    ibShadow->indexFormat == D3DFMT_INDEX16
                    ? static_cast<const std::uint16_t*>(
                        static_cast<const void*>(scratch.indexSource.data()))[i]
                    : static_cast<const std::uint32_t*>(
                        static_cast<const void*>(scratch.indexSource.data()))[i];
                const std::int64_t p =
                    static_cast<std::int64_t>(baseVertexIndex) + raw;
                if (p < 0 || p > UINT_MAX)
                {
                    ib->Release();
                    vb->Release();
                    return E_NOTIMPL;
                }
                scratch.physical[i] = static_cast<std::uint32_t>(p);
                minPhysical = std::min(minPhysical, p);
                maxPhysical = std::max(maxPhysical, p);
            }

            if (minPhysical == INT64_MAX || maxPhysical < minPhysical)
            {
                ib->Release();
                vb->Release();
                return E_NOTIMPL;
            }

            const std::uint64_t vertexCount64 =
                static_cast<std::uint64_t>(maxPhysical - minPhysical) + 1u;
            if (!vertexCount64 || vertexCount64 > 262144u)
            {
                ib->Release();
                vb->Release();
                return E_NOTIMPL;
            }
            const UINT vertexCount = static_cast<UINT>(vertexCount64);

            const std::uint64_t firstVertexByte =
                static_cast<std::uint64_t>(streamOffset) +
                static_cast<std::uint64_t>(minPhysical) * stride;
            const std::uint64_t vertexBytes =
                static_cast<std::uint64_t>(vertexCount) * stride;
            if (firstVertexByte > vbShadow->size ||
                vertexBytes > vbShadow->size - firstVertexByte ||
                firstVertexByte > UINT_MAX || vertexBytes > UINT_MAX)
            {
                ib->Release();
                vb->Release();
                return E_NOTIMPL;
            }

            if (!R30CopyVertexShadow(vbShadow,
                    static_cast<UINT>(firstVertexByte),
                    static_cast<UINT>(vertexBytes), scratch.source,
                    scratch.vertexCopy))
            {
                ib->Release();
                vb->Release();
                ++R30XyzrhwFallbacks;
                return E_NOTIMPL;
            }

            // The first index pass has already validated physical addresses
            // and discovered the contiguous source-vertex span. Mark used
            // vertices and rebase both index formats in the same second pass:
            // the old separate rebasing loop walked every particle index a
            // third time and touched the same scratch.physical cache lines.
            const bool index16 = ibShadow->indexFormat == D3DFMT_INDEX16;
            try
            {
                scratch.used.assign(vertexCount, 0);
                if (index16)
                    scratch.indices16.resize(indexCount);
                else
                    scratch.indices32.resize(indexCount);
            }
            catch (...)
            {
                ib->Release();
                vb->Release();
                return E_NOTIMPL;
            }

            const void* rebased = index16
                ? static_cast<const void*>(scratch.indices16.data())
                : static_cast<const void*>(scratch.indices32.data());
            for (UINT i = 0; i < indexCount; ++i)
            {
                const std::uint64_t local =
                    scratch.physical[i] -
                    static_cast<std::uint64_t>(minPhysical);
                // Reject unsafe 16-bit rebasing *before* attempting either
                // stereo eye. Never truncate when the physical span is wider
                // than a UINT16 index can describe.
                if (local >= vertexCount ||
                    (index16 && local > 0xFFFFu))
                {
                    ib->Release();
                    vb->Release();
                    return E_NOTIMPL;
                }
                scratch.used[static_cast<std::size_t>(local)] = 1;
                if (index16)
                    scratch.indices16[i] = static_cast<std::uint16_t>(local);
                else
                    scratch.indices32[i] = static_cast<std::uint32_t>(local);
            }

            if (!R30ConfigureXyzrhwWorldEffect(
                    device, scratch.source.data(), vertexCount,
                    stride, state, &scratch.used) ||
                !R30TransformXyzrhwStereo(
                    scratch.source.data(), vertexCount, stride, state,
                    scratch.left, scratch.right, &scratch.used))
            {
                ib->Release();
                vb->Release();
                ++R30XyzrhwFallbacks;
                return E_NOTIMPL;
            }

            auto leftDraw = [&]() {
                return R29OwnerCallRawDrawIndexedPrimitiveUP(
                    device, type, 0u, vertexCount, primitiveCount,
                    rebased, ibShadow->indexFormat, scratch.left.data(), stride);
            };
            auto rightDraw = [&]() {
                return R29OwnerCallRawDrawIndexedPrimitiveUP(
                    device, type, 0u, vertexCount, primitiveCount,
                    rebased, ibShadow->indexFormat, scratch.right.data(), stride);
            };
            const HRESULT hr = R30ExecuteXyzrhwStereo(
                device, state, leftDraw, rightDraw,
                "R30.6/DrawIndexedPrimitiveVB-ShadowXYZRHW");

            {
                R30ScopedInternalPass guard;
                bool restoreOk = SUCCEEDED(device->SetStreamSource(
                    0, vb, streamOffset, stride));
                restoreOk = SUCCEEDED(device->SetIndices(ib)) && restoreOk;
                if (!restoreOk)
                {
                    R29OwnerNoteRestoreFailure("R30.6 VB/IB restore");
                    R29OwnerArmMonoSafety();
                }
            }
            ib->Release();
            vb->Release();
            return hr;
        }

        // Called on every eligible FlatPerspectiveEffect draw. The cache key
        // includes pose, full per-eye geometry, world scale/depth and both actual
        // projection matrices, so a recenter or reset cannot reuse stale optics.
        // A failed/NaN packet invalidates prior results rather than replaying them.
        const R30FlatEffectGeometryCache* R30PrepareFlatEffectGeometry(
            const OutRunVRRenderer::LatchedStereoFrame& stereo,
            const D3DMATRIX& baseProjection,
            const D3DMATRIX& headInverse) noexcept
        {
            auto& cache = R30FlatEffectGeometry;
            const float worldScale =
                Settings::VRWorldScale * Settings::VRStereoDepth;
            if (cache.valid && cache.poseSequence == stereo.poseSequence &&
                cache.worldScale == worldScale &&
                std::memcmp(&cache.baseProjection, &baseProjection,
                    sizeof(baseProjection)) == 0 &&
                std::memcmp(&cache.headInverse, &headInverse,
                    sizeof(headInverse)) == 0 &&
                std::memcmp(cache.eyeOrientation, stereo.eyeOrientation,
                    sizeof(stereo.eyeOrientation)) == 0 &&
                std::memcmp(cache.eyeOffset, stereo.eyeOffset,
                    sizeof(stereo.eyeOffset)) == 0 &&
                std::memcmp(cache.eyeFov, stereo.eyeFov,
                    sizeof(stereo.eyeFov)) == 0)
                return &cache;

            cache.valid = false;
            if (!R29OwnerMatrixFinite(baseProjection) ||
                !R29OwnerMatrixFinite(headInverse) ||
                !std::isfinite(worldScale))
                return nullptr;

            R30FlatEffectGeometryCache next{};
            next.poseSequence = stereo.poseSequence;
            next.worldScale = worldScale;
            next.baseProjection = baseProjection;
            next.headInverse = headInverse;
            std::memcpy(next.eyeOrientation, stereo.eyeOrientation,
                sizeof(stereo.eyeOrientation));
            std::memcpy(next.eyeOffset, stereo.eyeOffset,
                sizeof(stereo.eyeOffset));
            std::memcpy(next.eyeFov, stereo.eyeFov, sizeof(stereo.eyeFov));
            if (!R29OwnerInvertMatrix(baseProjection, next.inverseBaseProjection))
                return nullptr;

            constexpr float OverlayPlaneViewZ = -2.50f;
            const float planeClipW =
                OverlayPlaneViewZ * baseProjection._34 + baseProjection._44;
            const float planeClipZ =
                OverlayPlaneViewZ * baseProjection._33 + baseProjection._43;
            if (!std::isfinite(planeClipW) || !std::isfinite(planeClipZ) ||
                planeClipW <= 1.0e-4f)
                return nullptr;
            next.planeNdcZ = planeClipZ / planeClipW;
            if (!std::isfinite(next.planeNdcZ))
                return nullptr;

            for (int eye = 0; eye < 2; ++eye)
            {
                const D3DMATRIX eyePose =
                    R29OwnerMatrixFromQuaternionTranslation(
                        stereo.eyeOrientation[eye], stereo.eyeOffset[eye],
                        worldScale);
                next.eyeInverse[eye] = R29OwnerInverseRigid(eyePose);
                next.eyeProjection[eye] = R29OwnerProjectionFromFov(
                    baseProjection, stereo.eyeFov[eye]);
                if (!R29OwnerMatrixFinite(next.eyeInverse[eye]) ||
                    !R29OwnerMatrixFinite(next.eyeProjection[eye]))
                    return nullptr;
            }

            next.valid = true; // publish only after both eyes are valid
            cache = next;
            return &cache;
        }

        bool R30BuildScreenSpaceEyeConstants(
            IDirect3DDevice9* device,
            const OutRunVRRenderer::LatchedStereoFrame& stereo,
            R30ScreenSpaceKind screenKind,
            float original[16], float eyeConstants[2][16],
            float eyeScale[2], float eyeOffset[2]) noexcept
        {
            if (!device ||
                R29OwnerCurrentVertexShaderIdentity() == 0)
                return false;

            if (FAILED(device->GetVertexShaderConstantF(
                    R30SupportWvpFirstRegister, original, R30SupportWvpRegisterCount)))
                return false;

            if (!R30BuildEyeAffine(stereo, eyeScale, eyeOffset))
                return false;

            D3DMATRIX uploadedT{};
            std::memcpy(&uploadedT, original, sizeof(uploadedT));
            const D3DMATRIX stockWvp = R29OwnerTransposeMatrix(uploadedT);
            if (!R29OwnerMatrixFinite(stockWvp))
                return false;

            if (screenKind == R30ScreenSpaceKind::FlatPerspectiveEffect)
            {
                float baseRaw[16]{};
                float headRaw[16]{};
                std::uint32_t headPoseSequence = 0;
                D3DMATRIX baseProjection{};
                D3DMATRIX headInverse{};
                if (!OutRunVRRenderer::GetRendererBaseProjection(baseRaw) ||
                    !OutRunVRRenderer::GetLatchedHeadInverse(
                        headRaw, headPoseSequence) ||
                    headPoseSequence != stereo.poseSequence)
                    return false;
                std::memcpy(&baseProjection, baseRaw, sizeof(baseProjection));
                std::memcpy(&headInverse, headRaw, sizeof(headInverse));
                const auto* geometry = R30PrepareFlatEffectGeometry(
                    stereo, baseProjection, headInverse);
                if (!geometry)
                    return false;

                // Preserve the game's x/w, y/w and original multiply order.
                // Only input-independent inverse, eye pose and FOV work move to
                // cache misses; every draw still uses its own live stock WVP.
                D3DMATRIX depthReset = R29OwnerIdentityMatrix();
                depthReset._33 = 0.0f;
                depthReset._43 = geometry->planeNdcZ;
                const D3DMATRIX commonViewPlane =
                    R29OwnerMultiplyMatrix(
                        R29OwnerMultiplyMatrix(stockWvp, depthReset),
                        geometry->inverseBaseProjection);
                if (!R29OwnerMatrixFinite(commonViewPlane))
                    return false;

                // Head inverse is identical for both eyes. Hoist the shared
                // multiply out of the two-eye loop without reassociating any
                // matrix products (preserves the previous FP order/optics).
                const D3DMATRIX headRelativePlane =
                    R29OwnerMultiplyMatrix(commonViewPlane, headInverse);
                for (int eye = 0; eye < 2; ++eye)
                {
                    const D3DMATRIX corrected =
                        R29OwnerMultiplyMatrix(
                            R29OwnerMultiplyMatrix(
                                headRelativePlane, geometry->eyeInverse[eye]),
                            geometry->eyeProjection[eye]);
                    if (!R29OwnerMatrixFinite(corrected))
                        return false;
                    const D3DMATRIX correctedT =
                        R29OwnerTransposeMatrix(corrected);
                    std::memcpy(eyeConstants[eye], &correctedT,
                        sizeof(correctedT));
                }
                return true;
            }

            if (screenKind != R30ScreenSpaceKind::Hud2D)
                return false;

            // HUD containment depends on this draw's latched stereo packet,
            // not on the eye index. Avoid a duplicate FOV/aspect cache probe.
            float hudScaleX = 1.0f;
            float hudScaleY = 1.0f;
            R30HudContainScale(stereo, hudScaleX, hudScaleY);
            for (int eye = 0; eye < 2; ++eye)
            {
                D3DMATRIX clipCorrection{};
                // Keep the already-verified ordinary HUD mapping unchanged.
                // Only FlatPerspectiveEffect uses the finite 3D plane above.
                clipCorrection._11 = hudScaleX;
                clipCorrection._22 = hudScaleY;
                clipCorrection._33 = 1.0f;
                clipCorrection._44 = 1.0f;
                clipCorrection._41 = eyeOffset[eye];

                const D3DMATRIX corrected =
                    R29OwnerMultiplyMatrix(stockWvp, clipCorrection);
                if (!R29OwnerMatrixFinite(corrected))
                    return false;

                const D3DMATRIX correctedT = R29OwnerTransposeMatrix(corrected);
                std::memcpy(eyeConstants[eye], &correctedT,
                    sizeof(correctedT));
            }
            return true;
        }

        template <typename ActualDraw>
        HRESULT R30TryScreenSpaceFovDraw(
            IDirect3DDevice9* device, ActualDraw&& actualDraw,
            const char* site)
        {
            if (!R29OwnerStableStereoBase(device))
                return E_NOTIMPL;

            const R30ScreenSpaceKind screenKind =
                R30ClassifyScreenSpacePass(device);
            if (screenKind == R30ScreenSpaceKind::None)
                return E_NOTIMPL;

            if (!R29OwnerEnsureStereoResources(device))
                return E_NOTIMPL;

            auto frame = R29OwnerCaptureFrameSnapshot();
            if (frame.trackedDepthStencil &&
                (!frame.rightDepthSynchronized || !frame.rightStencilSynchronized))
            {
                R29OwnerTryBootstrapRightDepth(device);
                // Resample synchronization bits after bootstrap.
                frame = R29OwnerCaptureFrameSnapshot();
            }
            if (frame.trackedDepthStencil && !frame.rightDepthSynchronized &&
                R29OwnerDepthTestActive(device))
                return E_NOTIMPL;
            if (frame.trackedDepthStencil && !frame.rightStencilSynchronized &&
                R29OwnerStencilTestActive(device))
                return E_NOTIMPL;

            OutRunVRRenderer::LatchedStereoFrame stereo{};
            if (!OutRunVRRenderer::GetLatchedStereoFrame(stereo) ||
                stereo.poseSequence == 0)
                return E_NOTIMPL;

            // If perspective world geometry already established this Present's
            // pose sequence, screen-space correction must use that exact packet.
            if (frame.poseSequence != 0 &&
                frame.poseSequence != stereo.poseSequence)
                return E_NOTIMPL;

            float original[16]{};
            float eyeConstants[2][16]{};
            float eyeScale[2]{};
            float eyeOffset[2]{};
            if (!R30BuildScreenSpaceEyeConstants(device, stereo,
                    screenKind, original, eyeConstants,
                    eyeScale, eyeOffset))
            {
                ++R30ScreenSpaceBuildFailures;
                return E_NOTIMPL;
            }

            D3DVIEWPORT9 savedViewport{};
            if (!R29OwnerTryGetTrackedViewport(savedViewport) &&
                FAILED(device->GetViewport(&savedViewport)))
                return E_NOTIMPL;

            // Runtime evidence on 7081b389 ruled out per-eye scissor
            // remapping. Keep the original game's scissor state untouched:
            // reading it on every HUD draw causes unnecessary D3D9 driver
            // queries. No SetScissorRect is performed by this path.

            // Capture the completed world eyes before the first recognized HUD
            // draw. Present then extracts glow from this snapshot, so bright HUD
            // text/icons are never themselves bloom sources.
            R30CaptureSkyGlowSceneBeforeHud(device);

            // From this point the draw is owned by R30. The steady-state frame
            // intentionally has no complete independent mono history.
            R29OwnerNoteStereoDrawWithoutMonoBackup();
            if (R29OwnerLeftDrawMayWriteDepth(device) ||
                R29OwnerLeftDrawMayWriteStencil(device))
                R29OwnerNoteMainDepthContentWrite();

            bool leftWvpOk = false;
            {
                R30ScopedInternalPass guard;
                leftWvpOk = R29OwnerSetWvpOneRegisterAtATime(
                    device, eyeConstants[0]);
            }
            if (!leftWvpOk)
            {
                bool restored = false;
                {
                    R30ScopedInternalPass guard;
                    restored = R29OwnerSetWvpOneRegisterAtATime(device, original);
                }
                if (!restored)
                {
                    R29OwnerReportStereoFailure(OutRunVR::StereoFailureRestoreFailed,
                        "R30/HUD-left-WVP-rollback", E_FAIL);
                    R29OwnerArmMonoSafety();
                    return E_FAIL;
                }
                R29OwnerUndoStereoDrawCount();
                return E_NOTIMPL;
            }

            const HRESULT leftHr = actualDraw();

            if (FAILED(leftHr))
            {
                bool restored = false;
                {
                    R30ScopedInternalPass guard;
                    restored = R29OwnerSetWvpOneRegisterAtATime(device, original);
                }
                R29OwnerReportStereoFailure(OutRunVR::StereoFailureLeftDrawFailed,
                    site, leftHr);
                if (!restored)
                    R29OwnerNoteRestoreFailure("R30 HUD left draw c64");
                R29OwnerArmMonoSafety();
                return leftHr;
            }

            // Game left-eye draw may update tracked surfaces.
            frame = R29OwnerCaptureFrameSnapshot();
            IDirect3DSurface9* savedRt = R29OwnerBorrowTrackedRenderTarget();
            IDirect3DSurface9* savedDepth = frame.trackedDepthStencil;
            HRESULT rightHr = D3D_OK;
            OutRunVR::StereoFailureReason rightFailure =
                OutRunVR::StereoFailureRightStateFailed;
            bool restoreOk = true;
            {
                R30ScopedInternalPass guard;
                rightHr = R29OwnerCallOriginalSetRenderTarget(
                    device, 0u, frame.rightEyeSurface);
                if (SUCCEEDED(rightHr))
                {
                    rightHr = R29OwnerCallOriginalSetDepthStencilSurface(
                        device, frame.trackedDepthStencil ? frame.rightEyeDepth : nullptr);
                }
                if (SUCCEEDED(rightHr))
                    rightHr = device->SetViewport(&savedViewport);
                if (SUCCEEDED(rightHr) &&
                    !R29OwnerSetWvpOneRegisterAtATime(device, eyeConstants[1]))
                {
                    rightFailure =
                        OutRunVR::StereoFailureRightWvpUploadFailed;
                    rightHr = E_FAIL;
                }
                if (SUCCEEDED(rightHr))
                {
                    rightFailure = OutRunVR::StereoFailureRightDrawFailed;
                    rightHr = actualDraw();
                }
                restoreOk = R29OwnerRestoreRightPassState(device, savedRt, savedDepth,
                    savedViewport, original, true);
            }

            R29OwnerRecordHudStereoDuplicate();
            R29OwnerNoteStableTwoEyeDraw();
            ++R30ScreenSpaceFovDraws;

            if (!R30FirstScreenSpaceLogged)
            {
                R30FirstScreenSpaceLogged = true;
                spdlog::info(
                    "VR R30 HUD: asymmetric-FOV convergence correction ACTIVE; common-centre offset[L/R]={:.4f}/{:.4f} hudScale={:.2f} sourceOverTarget={:.3f}",
                    eyeOffset[0], eyeOffset[1], R30HudScaleValue(),
                    R30HudAspectCompensation(stereo));
            }
            if (screenKind == R30ScreenSpaceKind::FlatPerspectiveEffect &&
                !R30FirstFlatPerspectiveLogged)
            {
                R30FirstFlatPerspectiveLogged = true;
                spdlog::info(
                    "VR R30 FLAT EFFECT: depth-disabled alpha perspective overlay is world-locked on a finite virtual plane with real head/IPD/FOV transform (no HudScale)");
            }

            if (FAILED(rightHr))
            {
                R29OwnerMarkRightDrawFailed();
                R29OwnerInvalidateRightDepthStencilIfLeftMayWrite(device);
                R29OwnerReportStereoFailure(rightFailure, site, rightHr);
                R29OwnerArmMonoSafety();
            }
            if (!restoreOk)
            {
                R29OwnerInvalidateRightDepthStencilIfLeftMayWrite(device);
                R29OwnerNoteRestoreFailure("R30 HUD right-eye draw");
                R29OwnerArmMonoSafety();
            }
            return leftHr;
        }

        template <typename ActualDraw, typename R29Draw>
        HRESULT R30GuardScreenSpace(IDirect3DDevice9* device,
            ActualDraw&& actualDraw, R29Draw&& r29Draw,
            const char* site)
        {
            const HRESULT hr = R30TryScreenSpaceFovDraw(
                device, std::forward<ActualDraw>(actualDraw), site);
            if (hr != E_NOTIMPL)
                return hr;
            ++R30ScreenSpaceFallbacks;
            return r29Draw();
        }

        HRESULT __stdcall DrawPrimitiveDestR30(IDirect3DDevice9* device,
            D3DPRIMITIVETYPE type, UINT startVertex, UINT primitiveCount)
        {
            const HRESULT xyzrhw = R30TryXyzrhwPrimitiveVB(
                device, type, startVertex, primitiveCount);
            if (xyzrhw != E_NOTIMPL)
                return xyzrhw;

            auto actual = [&]() {
                return R29OwnerCallRawDrawPrimitive(
                    device, type, startVertex, primitiveCount);
            };
            auto r29 = [&]() {
                return R30DrawPrimitiveR29Hook.stdcall<HRESULT>(
                    device, type, startVertex, primitiveCount);
            };
            return R30GuardScreenSpace(
                device, actual, r29, "R30/DrawPrimitive");
        }

        HRESULT __stdcall DrawIndexedPrimitiveDestR30(
            IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
            INT baseVertexIndex, UINT minVertexIndex, UINT numVertices,
            UINT startIndex, UINT primitiveCount)
        {
            const HRESULT xyzrhw = R30TryXyzrhwIndexedPrimitiveVB(
                device, type, baseVertexIndex, minVertexIndex, numVertices,
                startIndex, primitiveCount);
            if (xyzrhw != E_NOTIMPL)
                return xyzrhw;

            auto actual = [&]() {
                return R29OwnerCallRawDrawIndexedPrimitive(device, type,
                    baseVertexIndex, minVertexIndex, numVertices, startIndex,
                    primitiveCount);
            };
            auto r29 = [&]() {
                return R30DrawIndexedPrimitiveR29Hook.stdcall<HRESULT>(device, type,
                    baseVertexIndex, minVertexIndex, numVertices, startIndex,
                    primitiveCount);
            };
            return R30GuardScreenSpace(
                device, actual, r29, "R30/DrawIndexedPrimitive");
        }

        HRESULT __stdcall DrawPrimitiveUPDestR30(
            IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
            UINT primitiveCount, const void* data, UINT stride)
        {
            const HRESULT xyzrhw = R30TryXyzrhwPrimitiveUP(
                device, type, primitiveCount, data, stride);
            if (xyzrhw != E_NOTIMPL)
                return xyzrhw;

            auto actual = [&]() {
                return R29OwnerCallRawDrawPrimitiveUP(
                    device, type, primitiveCount, data, stride);
            };
            auto r29 = [&]() {
                return R30DrawPrimitiveUPR29Hook.stdcall<HRESULT>(
                    device, type, primitiveCount, data, stride);
            };
            return R30GuardScreenSpace(
                device, actual, r29, "R30/DrawPrimitiveUP");
        }

        HRESULT __stdcall DrawIndexedPrimitiveUPDestR30(
            IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
            UINT minVertexIndex, UINT numVertices, UINT primitiveCount,
            const void* indexData, D3DFORMAT indexFormat,
            const void* vertexData, UINT stride)
        {
            const HRESULT xyzrhw = R30TryXyzrhwIndexedPrimitiveUP(
                device, type, minVertexIndex, numVertices, primitiveCount,
                indexData, indexFormat, vertexData, stride);
            if (xyzrhw != E_NOTIMPL)
                return xyzrhw;

            auto actual = [&]() {
                return R29OwnerCallRawDrawIndexedPrimitiveUP(device, type,
                    minVertexIndex, numVertices, primitiveCount, indexData,
                    indexFormat, vertexData, stride);
            };
            auto r29 = [&]() {
                return R30DrawIndexedPrimitiveUPR29Hook.stdcall<HRESULT>(device,
                    type, minVertexIndex, numVertices, primitiveCount,
                    indexData, indexFormat, vertexData, stride);
            };
            return R30GuardScreenSpace(
                device, actual, r29, "R30/DrawIndexedPrimitiveUP");
        }

        void R30RollbackHooks() noexcept
        {
            R30ResetR29Hook = {};
            R30PresentR29Hook = {};
            R30DrawIndexedPrimitiveUPR29Hook = {};
            R30DrawPrimitiveUPR29Hook = {};
            R30DrawIndexedPrimitiveR29Hook = {};
            R30DrawPrimitiveR29Hook = {};
        }

        bool R30EnableHooks() noexcept
        {
            SafetyHookInline* hooks[]{
                &R30PresentR29Hook,
                &R30ResetR29Hook,
                &R30DrawPrimitiveR29Hook,
                &R30DrawIndexedPrimitiveR29Hook,
                &R30DrawPrimitiveUPR29Hook,
                &R30DrawIndexedPrimitiveUPR29Hook
            };
            for (auto* hook : hooks)
            {
                if (!*hook || !hook->enable().has_value())
                    return false;
            }
            return true;
        }

        DWORD WINAPI R30InstallThread(void*)
        {
            using State = OutRunVR::RuntimeEligibility::InstallState;
            R30InstallState.store(State::Pending, std::memory_order_release);

            for (int attempt = 0; attempt < 4800; ++attempt)
            {
                if (IDirect3DDevice9* gameDevice = R29OwnerGameDevice())
                    R30InstallBufferCreationHooks(gameDevice);

                const auto r29 = R29OwnerInstallStatus();
                if (r29 == State::Failed)
                {
                    R30RollbackBufferShadowHooks();
                    R30InstallState.store(State::Failed,
                        std::memory_order_release);
                    HookManager::ReportAsyncResult("OpenXRVRStereoR30HUD", false);
                    spdlog::error(
                        "VR R30 HUD: R29 prerequisite failed; R29 remains active without screen-space FOV correction");
                    return 0;
                }

                if (r29 == State::Ready)
                {
                    const auto disabled = safetyhook::InlineHook::StartDisabled;
                    R30PresentR29Hook = safetyhook::create_inline(
                        R29OwnerPresentTarget(),
                        PresentDestR30, disabled);
                    R30ResetR29Hook = safetyhook::create_inline(
                        R29OwnerResetTarget(),
                        ResetDestR30, disabled);
                    R30DrawPrimitiveR29Hook = safetyhook::create_inline(
                        R29OwnerDrawPrimitiveTarget(),
                        DrawPrimitiveDestR30, disabled);
                    R30DrawIndexedPrimitiveR29Hook = safetyhook::create_inline(
                        R29OwnerDrawIndexedPrimitiveTarget(),
                        DrawIndexedPrimitiveDestR30, disabled);
                    R30DrawPrimitiveUPR29Hook = safetyhook::create_inline(
                        R29OwnerDrawPrimitiveUPTarget(),
                        DrawPrimitiveUPDestR30, disabled);
                    R30DrawIndexedPrimitiveUPR29Hook = safetyhook::create_inline(
                        R29OwnerDrawIndexedPrimitiveUPTarget(),
                        DrawIndexedPrimitiveUPDestR30, disabled);

                    if (!R30EnableHooks())
                    {
                        R30RollbackHooks();
                        R30RollbackBufferShadowHooks();
                        R30InstallState.store(State::Failed,
                            std::memory_order_release);
                        HookManager::ReportAsyncResult(
                            "OpenXRVRStereoR30HUD", false);
                        spdlog::error(
                            "VR R30 HUD: disabled-first hook transaction failed; R29 remains active");
                        return 0;
                    }

                    R30InstallState.store(State::Ready,
                        std::memory_order_release);
                    HookManager::ReportAsyncResult(
                        "OpenXRVRStereoR30HUD", true);
                    spdlog::info(
                        "VR R30 HUD: ScreenSpace2D correction READY with configurable common-center HUD scale current={:.2f}; R36 contain-fit + depth-disabled overlay zero-disparity + head-relative XYZRHW reprojection active",
                        R30HudScaleValue());
                    return 0;
                }
                Sleep(25);
            }

            R30RollbackBufferShadowHooks();
            R30InstallState.store(State::Failed, std::memory_order_release);
            HookManager::ReportAsyncResult("OpenXRVRStereoR30HUD", false);
            spdlog::error(
                "VR R30 HUD: timed out waiting for R29; R29 remains active");
            return 0;
        }

        class VRStereoR30HudHook final : public Hook
        {
        public:
            std::string_view description() override
            {
                return "OpenXRVRStereoR30HUD";
            }
            bool validate() override { return true; }
            bool apply() override
            {
                using State = OutRunVR::RuntimeEligibility::InstallState;
                R30InstallState.store(State::Pending,
                    std::memory_order_release);
                HANDLE thread = CreateThread(nullptr, 0,
                    R30InstallThread, nullptr, 0, nullptr);
                if (!thread)
                {
                    R30InstallState.store(State::Failed,
                        std::memory_order_release);
                    return false;
                }
                CloseHandle(thread);
                return true;
            }
            static VRStereoR30HudHook instance;
        };

        VRStereoR30HudHook VRStereoR30HudHook::instance;
    }

    OutRunVR::RuntimeEligibility::InstallState
    R30InstallStatus() noexcept
    {
        return R30InstallState.load(std::memory_order_acquire);
    }

    inline HRESULT R30CallLowerDrawPrimitive(
        IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
        UINT startVertex, UINT primitiveCount) noexcept
    {
        return R30DrawPrimitiveR29Hook.stdcall<HRESULT>(
            device, type, startVertex, primitiveCount);
    }

    inline HRESULT R30CallLowerDrawIndexedPrimitive(
        IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
        INT baseVertexIndex, UINT minVertexIndex, UINT numVertices,
        UINT startIndex, UINT primitiveCount) noexcept
    {
        return R30DrawIndexedPrimitiveR29Hook.stdcall<HRESULT>(
            device, type, baseVertexIndex, minVertexIndex, numVertices,
            startIndex, primitiveCount);
    }

    inline HRESULT R30CallLowerDrawPrimitiveUP(
        IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
        UINT primitiveCount, const void* data, UINT stride) noexcept
    {
        return R30DrawPrimitiveUPR29Hook.stdcall<HRESULT>(
            device, type, primitiveCount, data, stride);
    }

    inline HRESULT R30CallLowerDrawIndexedPrimitiveUP(
        IDirect3DDevice9* device, D3DPRIMITIVETYPE type,
        UINT minVertexIndex, UINT numVertices, UINT primitiveCount,
        const void* indexData, D3DFORMAT indexFormat,
        const void* vertexData, UINT stride) noexcept
    {
        return R30DrawIndexedPrimitiveUPR29Hook.stdcall<HRESULT>(
            device, type, minVertexIndex, numVertices, primitiveCount,
            indexData, indexFormat, vertexData, stride);
    }

    inline void R30TelemetryNoteScreenSpaceFovDraw() noexcept
    {
        ++R30ScreenSpaceFovDraws;
    }


    // R32-to-R30 structural seam: preserve the current live lower-owner
    // classification, XYZRHW fallback and hook dispatch without transferring
    // any physical hook or shadow device state into R32.
    R30SupportScreenSpaceKind R30SupportClassifyScreenSpacePass(
        IDirect3DDevice9* device) noexcept
    {
        switch (R30ClassifyScreenSpacePass(device))
        {
        case R30ScreenSpaceKind::Hud2D:
            return R30SupportScreenSpaceKind::Hud2D;
        case R30ScreenSpaceKind::FlatPerspectiveEffect:
            return R30SupportScreenSpaceKind::FlatPerspectiveEffect;
        default:
            return R30SupportScreenSpaceKind::None;
        }
    }

    bool R30SupportBuildScreenSpaceEyeConstants(
        IDirect3DDevice9* device,
        const OutRunVRRenderer::LatchedStereoFrame& stereo,
        R30SupportScreenSpaceKind kind,
        float original[16], float eyeConstants[2][16],
        float eyeScale[2], float eyeOffset[2]) noexcept
    {
        R30ScreenSpaceKind lower = R30ScreenSpaceKind::None;
        switch (kind)
        {
        case R30SupportScreenSpaceKind::Hud2D:
            lower = R30ScreenSpaceKind::Hud2D;
            break;
        case R30SupportScreenSpaceKind::FlatPerspectiveEffect:
            lower = R30ScreenSpaceKind::FlatPerspectiveEffect;
            break;
        default:
            return false;
        }
        return R30BuildScreenSpaceEyeConstants(
            device, stereo, lower, original, eyeConstants, eyeScale, eyeOffset);
    }

    void R30SupportNoteScreenSpaceFovDraw() noexcept
    {
        R30TelemetryNoteScreenSpaceFovDraw();
    }

    HRESULT R30SupportTryXyzrhwPrimitiveVB(
        IDirect3DDevice9* d, D3DPRIMITIVETYPE t, UINT s, UINT p) noexcept
    {
        return R30TryXyzrhwPrimitiveVB(d,t,s,p);
    }
    HRESULT R30SupportTryXyzrhwIndexedPrimitiveVB(
        IDirect3DDevice9* d, D3DPRIMITIVETYPE t,
        INT b, UINT m, UINT n, UINT s, UINT p) noexcept
    {
        return R30TryXyzrhwIndexedPrimitiveVB(d,t,b,m,n,s,p);
    }
    HRESULT R30SupportTryXyzrhwPrimitiveUP(
        IDirect3DDevice9* d, D3DPRIMITIVETYPE t, UINT p,
        const void* data, UINT st) noexcept
    {
        return R30TryXyzrhwPrimitiveUP(d,t,p,data,st);
    }
    HRESULT R30SupportTryXyzrhwIndexedPrimitiveUP(
        IDirect3DDevice9* d, D3DPRIMITIVETYPE t,
        UINT m, UINT n, UINT p, const void* idx,
        D3DFORMAT f, const void* v, UINT st) noexcept
    {
        return R30TryXyzrhwIndexedPrimitiveUP(d,t,m,n,p,idx,f,v,st);
    }

    HRESULT R30SupportCallLowerDrawPrimitive(
        IDirect3DDevice9* d, D3DPRIMITIVETYPE t, UINT s, UINT p) noexcept
    {
        return R30CallLowerDrawPrimitive(d,t,s,p);
    }
    HRESULT R30SupportCallLowerDrawIndexedPrimitive(
        IDirect3DDevice9* d, D3DPRIMITIVETYPE t,
        INT b, UINT m, UINT n, UINT s, UINT p) noexcept
    {
        return R30CallLowerDrawIndexedPrimitive(d,t,b,m,n,s,p);
    }
    HRESULT R30SupportCallLowerDrawPrimitiveUP(
        IDirect3DDevice9* d, D3DPRIMITIVETYPE t, UINT p,
        const void* data, UINT st) noexcept
    {
        return R30CallLowerDrawPrimitiveUP(d,t,p,data,st);
    }
    HRESULT R30SupportCallLowerDrawIndexedPrimitiveUP(
        IDirect3DDevice9* d, D3DPRIMITIVETYPE t,
        UINT m, UINT n, UINT p, const void* idx,
        D3DFORMAT f, const void* v, UINT st) noexcept
    {
        return R30CallLowerDrawIndexedPrimitiveUP(d,t,m,n,p,idx,f,v,st);
    }

    HRESULT R30SupportRunRasterReplayGuardCallback(
        IDirect3DDevice9* device, const char* site,
        R30SupportVoidCallback active, void* activeContext,
        R30SupportHResultCallback draw, void* drawContext) noexcept
    {
        return R29OwnerRunRasterReplayGuardCallback(
            device, site, active, activeContext, draw, drawContext);
    }

    OutRunVR::RuntimeEligibility::InstallState
    R30SupportLowerPrerequisiteStatus() noexcept
    {
        return R29OwnerLowerPrerequisiteStatus();
    }

    void* R30SupportDrawPrimitiveTarget() noexcept
    {
        return reinterpret_cast<void*>(&DrawPrimitiveDestR30);
    }
    void* R30SupportDrawIndexedPrimitiveTarget() noexcept
    {
        return reinterpret_cast<void*>(&DrawIndexedPrimitiveDestR30);
    }
    void* R30SupportDrawPrimitiveUPTarget() noexcept
    {
        return reinterpret_cast<void*>(&DrawPrimitiveUPDestR30);
    }
    void* R30SupportDrawIndexedPrimitiveUPTarget() noexcept
    {
        return reinterpret_cast<void*>(&DrawIndexedPrimitiveUPDestR30);
    }

    bool R30SupportTelemetryEnabled() noexcept
    {
        return Settings::VRTelemetry;
    }

    bool R30SupportIsGameDevice(IDirect3DDevice9* device) noexcept
    {
        return R29OwnerIsGameDevice(device);
    }

    bool R30SupportInternalStereoPassActive() noexcept
    {
        return R29OwnerInternalStereoPassActive();
    }

    bool R30SupportExchangeInternalStereoPass(bool active) noexcept
    {
        return R29OwnerExchangeInternalStereoPass(active);
    }

    std::uint64_t R30SupportPresentEpoch() noexcept
    {
        return R29OwnerCaptureFrameSnapshot().presentEpoch;
    }

    bool R30SupportStereoWanted() noexcept
    {
        return R29OwnerStereoWanted();
    }

    bool R30SupportStereoBaselineSeeded() noexcept
    {
        return R29OwnerStereoBaselineSeeded();
    }

    std::uint64_t R30SupportMainDepthGeneration() noexcept
    {
        return R29OwnerMainDepthGeneration();
    }

    bool R30SupportMainDepthHasStencil() noexcept
    {
        return R29OwnerMainDepthHasStencil();
    }

    bool R30SupportLeftDrawMayWriteDepth(IDirect3DDevice9* device) noexcept
    {
        return R29OwnerLeftDrawMayWriteDepth(device);
    }

    bool R30SupportLeftDrawMayWriteStencil(IDirect3DDevice9* device) noexcept
    {
        return R29OwnerLeftDrawMayWriteStencil(device);
    }

    void R30SupportNoteMainDepthContentWrite() noexcept
    {
        R29OwnerNoteMainDepthContentWrite();
    }

    HRESULT R30SupportCallRawDrawPrimitive(
        IDirect3DDevice9* d, D3DPRIMITIVETYPE t, UINT s, UINT p) noexcept
    {
        return R29OwnerCallRawDrawPrimitive(d,t,s,p);
    }

    HRESULT R30SupportCallRawDrawIndexedPrimitive(
        IDirect3DDevice9* d, D3DPRIMITIVETYPE t, INT b,
        UINT m, UINT n, UINT s, UINT p) noexcept
    {
        return R29OwnerCallRawDrawIndexedPrimitive(d,t,b,m,n,s,p);
    }

    HRESULT R30SupportCallRawDrawPrimitiveUP(
        IDirect3DDevice9* d, D3DPRIMITIVETYPE t, UINT p,
        const void* data, UINT st) noexcept
    {
        return R29OwnerCallRawDrawPrimitiveUP(d,t,p,data,st);
    }

    HRESULT R30SupportCallRawDrawIndexedPrimitiveUP(
        IDirect3DDevice9* d, D3DPRIMITIVETYPE t,
        UINT m, UINT n, UINT p, const void* idx,
        D3DFORMAT f, const void* v, UINT st) noexcept
    {
        return R29OwnerCallRawDrawIndexedPrimitiveUP(
            d,t,m,n,p,idx,f,v,st);
    }

    HRESULT R30SupportCallRawPresent(
        IDirect3DDevice9* d, const RECT* s, const RECT* dst,
        HWND w, const RGNDATA* r) noexcept
    {
        return R29OwnerCallRawPresent(d,s,dst,w,r);
    }

    void R30SupportNoteStereoDrawWithoutMonoBackup() noexcept
    {
        R29OwnerNoteStereoDrawWithoutMonoBackup();
    }

    void R30SupportReportStereoFailure(
        OutRunVR::StereoFailureReason reason,
        const char* site, HRESULT hr) noexcept
    {
        R29OwnerReportStereoFailure(reason, site, hr);
    }

    void R30SupportInvalidateRightDepthStencilSync(
        bool invalidateDepth, bool invalidateStencil) noexcept
    {
        R29OwnerInvalidateRightDepthStencilSync(invalidateDepth, invalidateStencil);
    }

    bool R30SupportRightDepthInSync() noexcept
    {
        return R29OwnerRightDepthInSync();
    }

    bool R30SupportRightStencilInSync() noexcept
    {
        return R29OwnerRightStencilInSync();
    }

    bool R30SupportTargetIsBackBuffer() noexcept
    {
        return R29OwnerTargetIsBackBuffer();
    }

    bool R30SupportAnyAuxRenderTargetActive() noexcept
    {
        return R29OwnerAnyAuxRenderTargetActive();
    }

    bool R30SupportTryGetTrackedViewport(D3DVIEWPORT9& viewport) noexcept
    {
        return R29OwnerTryGetTrackedViewport(viewport);
    }

    bool R30SupportTryGetEffectTelemetrySnapshot(
        R30SupportEffectTelemetrySnapshot& out) noexcept
    {
        R29OwnerEffectTelemetrySnapshot lower{};
        if (!R29OwnerTryGetEffectTelemetrySnapshot(lower))
        {
            out = {};
            return false;
        }
        out.alphaBlend = lower.alphaBlend;
        out.alphaTest = lower.alphaTest;
        out.zWrite = lower.zWrite;
        return true;
    }

    bool R30SupportStableStereoBase(IDirect3DDevice9* device) noexcept
    {
        return R29OwnerStableStereoBase(device);
    }

    bool R30SupportFragileEffectCached(IDirect3DDevice9* device,
        bool& fragile) noexcept
    {
        return R29OwnerFragileEffectCached(device, fragile);
    }

    void R30SupportNoteStableTwoEyeDraw() noexcept
    {
        R29OwnerNoteStableTwoEyeDraw();
    }

    bool R30SupportOverlayReadyForTransport() noexcept
    {
        return R29OwnerOverlayReadyForTransport();
    }

    void R30SupportNoteSafeAckBackpressure() noexcept
    {
        R29OwnerNoteSafeAckBackpressure();
    }

    void R30SupportNoteDirectTransportRingBackpressure() noexcept
    {
        R29OwnerNoteDirectTransportRingBackpressure();
    }

    std::uint64_t R30SupportDirectTransportRingBackpressureCount() noexcept
    {
        return R29OwnerDirectTransportRingBackpressureCount();
    }

    void R30SupportSetActiveDirectTransportSlot(std::uint32_t slot) noexcept
    {
        R29OwnerSetActiveDirectTransportSlot(slot);
    }

    void R30SupportMarkDirectTransportSlotPending(
        std::uint32_t slot, std::uint32_t frameId) noexcept
    {
        R29OwnerMarkDirectTransportSlotPending(slot, frameId);
    }

    R30SupportDirectTransportSlotPublication
    R30SupportGetDirectTransportSlotPublication(
        std::uint32_t slot) noexcept
    {
        const auto pub = R29OwnerGetDirectTransportSlotPublication(slot);
        return {pub.published, pub.frameId};
    }

    HRESULT R30SupportPollDirectTransportSlotProducer(
        std::uint32_t slot) noexcept
    {
        return R29OwnerPollDirectTransportSlotProducer(slot);
    }

    void R30SupportRetireDirectTransportSlotPublication(
        std::uint32_t slot) noexcept
    {
        R29OwnerRetireDirectTransportSlotPublication(slot);
    }

    bool R30SupportTryGetGpuCompletionSnapshot(
        R30SupportGpuCompletionSnapshot& out) noexcept
    {
        out = {};
        return R29OwnerTryGetGpuCompletionSnapshot(out.completedFrameId);
    }

    bool R30SupportDirectTransportResourcesReady() noexcept
    {
        return R29OwnerDirectTransportResourcesReady();
    }

    bool R30SupportEnsureDirectTransportResources(
        IDirect3DDevice9* device) noexcept
    {
        return R29OwnerEnsureDirectTransportResources(device);
    }

    bool R30SupportTryGetDirectTransportSourceSurfaces(
        R30SupportDirectTransportSourceSurfaces& out) noexcept
    {
        // Publish one coherent owner view instead of assembling two separate
        // frame snapshots while resolving a DirectGPU transport slot.
        const auto frame = R29OwnerCaptureFrameSnapshot();
        out.left = frame.backBuffer;
        out.right = frame.rightEyeSurface;
        return out.left != nullptr && out.right != nullptr;
    }

    R30SupportDirectTransportCopyResult
    R30SupportCopyDirectTransportEyesAndIssueFence(
        IDirect3DDevice9* device, std::uint32_t index,
        const R30SupportDirectTransportSourceSurfaces& source) noexcept
    {
        R30ScopedInternalPass guard;
        const auto result = R29OwnerCopyDirectTransportEyesAndIssueFence(
            device, index, source.left, source.right);
        return {result.hr, result.copyFailed};
    }

    IDirect3DSurface9* R30SupportBorrowedTrackedRenderTarget() noexcept
    {
        return R29OwnerBorrowTrackedRenderTarget();
    }

    IDirect3DSurface9* R30SupportBorrowedTrackedDepthStencil() noexcept
    {
        return R29OwnerBorrowTrackedDepthStencil();
    }

    IDirect3DSurface9* R30SupportBorrowedRightEyeSurface() noexcept
    {
        return R29OwnerBorrowRightEyeSurface();
    }

    IDirect3DSurface9* R30SupportBorrowedRightEyeDepth() noexcept
    {
        return R29OwnerBorrowRightEyeDepth();
    }

    bool R30SupportEnsureStereoResources(IDirect3DDevice9* device) noexcept
    {
        return R29OwnerEnsureStereoResources(device);
    }

    bool R30SupportTryBootstrapRightDepth(IDirect3DDevice9* device) noexcept
    {
        return R29OwnerTryBootstrapRightDepth(device);
    }

    bool R30SupportDepthTestActive(IDirect3DDevice9* device) noexcept
    {
        return R29OwnerDepthTestActive(device);
    }

    bool R30SupportStencilTestActive(IDirect3DDevice9* device) noexcept
    {
        return R29OwnerStencilTestActive(device);
    }

    HRESULT R30SupportCallOriginalSetRenderTarget(
        IDirect3DDevice9* device, DWORD index,
        IDirect3DSurface9* surface) noexcept
    {
        return R29OwnerCallOriginalSetRenderTarget(device, index, surface);
    }

    HRESULT R30SupportCallOriginalSetDepthStencilSurface(
        IDirect3DDevice9* device,
        IDirect3DSurface9* surface) noexcept
    {
        return R29OwnerCallOriginalSetDepthStencilSurface(device, surface);
    }

    void R30SupportRecordWorldStereoDuplicate(
        std::uint32_t poseSequence,
        const OutRunVRRenderer::LatchedStereoFrame& stereo) noexcept
    {
        R29OwnerRecordWorldStereoDuplicate(poseSequence, stereo);
    }

    void R30SupportRecordHudStereoDuplicate() noexcept
    {
        R29OwnerRecordHudStereoDuplicate();
    }

    void R30SupportMarkFrameRightDrawFailed() noexcept
    {
        R29OwnerMarkRightDrawFailed();
    }

    void* R30SupportResetTarget() noexcept
    {
        return R29OwnerResetR22Target();
    }

    void* R30SupportPresentTarget() noexcept
    {
        return R29OwnerPresentR13Target();
    }

    void* R30SupportDirectTransportTarget() noexcept
    {
        return R29OwnerDirectTransportR13Target();
    }

    void* R30SupportSetRenderStateTarget() noexcept
    {
        return R29OwnerSetRenderStateR29Target();
    }

    IDirect3DDevice9* R30SupportInstalledDevice() noexcept
    {
        return R29OwnerInstalledDevice();
    }

    std::uint32_t R30SupportFrameStereoPoseSequence() noexcept
    {
        return R29OwnerCaptureFrameSnapshot().poseSequence;
    }

    void R30SupportReleaseDirectAckState() noexcept
    {
        R29OwnerReleaseDirectAckState();
    }

    void R30SupportReleaseDirectTransportInterop() noexcept
    {
        R29OwnerReleaseDirectTransportInterop();
    }

    bool R30SupportTryGetDirectTransportIdentity(
        R30SupportDirectTransportIdentity& out) noexcept
    {
        out = {};
        R29OwnerTransportIdentity identity{};
        if (!R29OwnerTryGetDirectTransportIdentity(identity))
            return false;

        out.hostPid = identity.hostPid;
        out.hostAdapterLuidLow = identity.hostAdapterLuidLow;
        out.hostAdapterLuidHigh = identity.hostAdapterLuidHigh;
        return true;
    }

    void R30SupportInvalidateEffectStateCache() noexcept
    {
        R29OwnerInvalidateEffectStateCache();
    }

    void R30SupportInvalidateTrackedRasterShadow() noexcept
    {
        R29OwnerInvalidateTrackedRasterShadow();
    }

    void R30SupportInvalidateLiveStateSample() noexcept
    {
        R29OwnerInvalidateLiveStateSample();
    }

    std::uintptr_t R30SupportCurrentVertexShaderIdentity() noexcept
    {
        return R29OwnerCurrentVertexShaderIdentity();
    }

    std::uintptr_t R30SupportExchangeVertexShaderIdentity(
        std::uintptr_t identity) noexcept
    {
        return R29OwnerExchangeVertexShaderIdentity(identity);
    }

    void R30SupportRestoreVertexShaderIdentityIfEmpty(
        std::uintptr_t identity) noexcept
    {
        R29OwnerRestoreVertexShaderIdentityIfEmpty(identity);
    }

    float R30SupportWorldScale() noexcept
    {
        return Settings::VRWorldScale;
    }

    D3DMATRIX R30SupportMatrixFromQuaternionTranslation(
        const float orientation[4], const float position[3],
        float positionScale) noexcept
    {
        return R29OwnerMatrixFromQuaternionTranslation(
            orientation, position, positionScale);
    }

    D3DMATRIX R30SupportInverseRigid(const D3DMATRIX& matrix) noexcept
    {
        return R29OwnerInverseRigid(matrix);
    }

    D3DMATRIX R30SupportProjectionFromFov(
        const D3DMATRIX& base, const OutRunVR::SharedFov& fov) noexcept
    {
        return R29OwnerProjectionFromFov(base, fov);
    }

    D3DMATRIX R30SupportMultiplyMatrix(
        const D3DMATRIX& a, const D3DMATRIX& b) noexcept
    {
        return R29OwnerMultiplyMatrix(a, b);
    }

    D3DMATRIX R30SupportTransposeMatrix(const D3DMATRIX& matrix) noexcept
    {
        return R29OwnerTransposeMatrix(matrix);
    }

    bool R30SupportMatrixFinite(const D3DMATRIX& matrix) noexcept
    {
        return R29OwnerMatrixFinite(matrix);
    }

    bool R30SupportGetInverseProjection(
        const D3DMATRIX& projection, D3DMATRIX& inverse) noexcept
    {
        return R29OwnerGetInverseProjection(projection, inverse);
    }

    bool R30SupportValidateVerifiedWvp(
        IDirect3DDevice9* device, const float verified[16],
        float live[16]) noexcept
    {
        return R29OwnerValidateVerifiedWvp(device, verified, live);
    }

    bool R30SupportGetVerifiedProjection(
        float outProjection[16], std::uint32_t& generation,
        std::uint32_t& poseSequence) noexcept
    {
        return R29OwnerGetR28VerifiedProjection(
            outProjection, generation, poseSequence);
    }

    bool R30SupportCurrentShaderEpoch(
        std::uintptr_t& identity, std::uint64_t& serial) noexcept
    {
        return R29OwnerCurrentShaderEpoch(identity, serial);
    }

    void R30SupportResynchronizeShaderEpoch(
        IDirect3DDevice9* device) noexcept
    {
        R29OwnerResynchronizeShaderEpoch(device);
    }

    void R30SupportInvalidateRendererStateAfterExternalRestore() noexcept
    {
        R29OwnerInvalidateRendererStateAfterExternalRestore();
    }

    OutRunVR::RuntimeEligibility::InstallState
    R30SupportRendererInstallStatus() noexcept
    {
        return R29OwnerRendererInstallStatus();
    }

    bool R30SupportPrimeTrackedRasterShadow(
        IDirect3DDevice9* device) noexcept
    {
        return R29OwnerPrimeTrackedRasterShadow(device);
    }

    void R30SupportSetStereoRecoverySafetyThroughEpoch(
        std::uint64_t throughEpoch) noexcept
    {
        R29OwnerSetStereoRecoverySafetyThroughEpoch(throughEpoch);
    }
    bool R30SupportFrameIdAtOrAfter(
        std::uint32_t candidate, std::uint32_t reference) noexcept
    {
        return R29OwnerFrameIdAtOrAfter(candidate, reference);
    }
    void R30SupportFailClosedResetBaselineState() noexcept
    {
        R29OwnerFailClosedResetBaselineState();
    }
    void R30SupportArmStereoRecoverySafety(
        std::uint64_t extraPresents) noexcept
    {
        R29OwnerArmStereoRecoverySafety(extraPresents);
    }
    void R30SupportNoteRestoreFailure(const char* what) noexcept
    {
        R29OwnerNoteRestoreFailure(what);
    }
}