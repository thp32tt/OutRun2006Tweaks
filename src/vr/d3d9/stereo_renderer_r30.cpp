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
// Needed by independent R30 TU as well as textual R29/R30 owner.
#include "r30_indexed_up_bounds.hpp"
#include "r30_shadow_bytes.hpp"
#include "r30_shadow_scratch.hpp"
#include "stereo_completion_gate.hpp"
#include "lens_centre_source_provenance.hpp"
#include "../core/r29_owner_api.hpp"
#include "../core/r30_support_api.hpp"
#include "../core/stereo_world_scale.hpp"
#include "../game/render_semantics.hpp"
#include "../game/projected_rank_stereo.hpp"
#include <cstring>
#include "../state/state_block_tracker.hpp"
#include "vr_pass_policy.hpp"
#include "pause_menu_eye_affine.hpp"
#include "hud_edge_transition.hpp"
#include "hook_mgr.hpp"
#include "plugin.hpp"
#include "vr_shared.hpp"
#include "game_addrs.hpp"
#include <spdlog/spdlog.h>
#include <d3dcompiler.h>
#include <algorithm>
#include <atomic>
#include <memory>
#include <limits>
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
    extern Setting<float> VRPauseMenuScale;
    extern Setting<float> VRPauseMenuVerticalOffset;
    extern Setting<bool> VRHudResponsiveLayout;
    extern Setting<bool> VRHudEdgeAnchors;
    extern Setting<float> VRStereoDepth;
    extern Setting<int> SkyGlowFactor;
    extern Setting<bool> SkyGlowTwoStep;
}

// Original-game source provenance from the common R23 WVP producer.
namespace OutRunVRRenderer
{
    std::uint64_t GetLastGameWvpLensCentreCallEpoch() noexcept;
    std::uint64_t GetCurrentLatchedPoseEpoch() noexcept;
    std::uint64_t GetLastGameWvpPoseEpoch() noexcept;
    bool GetLastRawGameWvpWrite(float outConstants[16],
        std::uint64_t& writeSerial, std::uint64_t& topLevelDrawSerial,
        std::uintptr_t& shaderIdentity, std::uint64_t& shaderSerial) noexcept;
    bool GetLastGameWvpSemanticProvenance(
        OutRunVR::GameSemantic::RenderScope& semanticScope,
        std::uint64_t& queueNodeEpoch,
        const void*& queueNode,
        OutRunVR::GameSemantic::ProducerToken& producerToken) noexcept;
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

        // R30 owns per-draw stereo decisions independently of instrumentation.
        // Shadow, XYZRHW and sky-glow counters are only read by the optional
        // Present telemetry report. Do not dirty the shared counter cache lines
        // for every draw/Lock/Unlock when the diagnostics toggle is off.
        inline void R30RecordTelemetryCounter(std::uint64_t& counter) noexcept
        {
            if (Settings::VRTelemetry)
                ++counter;
        }

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
            // The direct Calc3D2D flare-ring route already consumed the
            // camera orientation; never cache it as a generic world effect.
            bool directProjected2D = false;
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
            // The protected R26+HUD route already proved that invalid shadow
            // bytes are never consumed. R84 shares that same lazy backing store:
            // every copy remains gated by the independent valid-range map.
            OutRunVR::R30ShadowBytes::LazyUninitializedBuffer bytes;
            std::vector<R30ByteRange> valid;
            // Incremented while holding mutex whenever known shadow contents or
            // coverage change. Draw scratch copies are reusable only for this
            // exact generation and byte range.
            std::uint64_t revision = 1;
            // A single successful non-DISCARD write can refresh an existing
            // per-thread snapshot without copying the untouched VB/IB bytes.
            // Revisions prevent unsafe reuse after multiple writes or loss.
            std::uint64_t lastWriteRevision = 0;
            UINT lastWriteBegin = 0;
            UINT lastWriteEnd = 0;
            bool lastWriteSafe = false;
            void* lockPtr = nullptr;
            UINT lockOffset = 0;
            UINT lockSize = 0;
            DWORD lockFlags = 0;
            bool writeLock = false;
        };

        using R30ShadowPtr = std::shared_ptr<R30BufferShadow>;
        std::mutex R30ShadowRegistryMutex;
        std::mutex R30ShadowHookMutex;
        // Both Create{Vertex,Index}Buffer detours must be committed together.
        // Acquire avoids the installation mutex on a steady-state retry;
        // Reset/rollback clears the publication under the same mutex.
        std::atomic<bool> R30BufferCreationHooksReady{false};
        // Published once all three hooks are installed: steady VB/IB draws
        // need no install mutex, while partial installs still retry under lock.
        std::atomic<bool> R30VertexBufferHooksReady{false};
        std::atomic<bool> R30IndexBufferHooksReady{false};
        std::unordered_map<IDirect3DVertexBuffer9*, R30ShadowPtr>
            R30VertexShadows;
        std::unordered_map<IDirect3DIndexBuffer9*, R30ShadowPtr>
            R30IndexShadows;
        // Generation is advanced under the registry mutex on membership
        // changes, including final COM Release and Reset rollback.
        std::atomic<std::uint64_t> R30ShadowRegistryEpoch{1};
        struct R30ShadowLookupCache
        {
            struct Slot
            {
                const void* buffer = nullptr;
                R30ShadowPtr entry;
            };
            // A four-entry epoch-fenced working set handles interleaved static,
            // dynamic and UI VB/IB streams without repeated registry-mutex
            // contention. Generation fencing still invalidates positive AND
            // negative entries on Release, Reset and pointer reuse.
            Slot slots[4]{};
            std::uint64_t epoch = 0;
            unsigned next = 0;
        };
        thread_local R30ShadowLookupCache R30VertexLookup{};
        thread_local R30ShadowLookupCache R30IndexLookup{};
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

        // The indexed VB decoder's output depends only on an immutable
        // snapshot of the IB byte span, not on the changing base vertex or
        // current vertex-buffer contents. Preserve the rebased indices and
        // referenced-vertex mask for repeated static/same-generation draws.
        struct R30IndexDecodeCache
        {
            R30ShadowPtr entry;
            UINT offset = 0;
            UINT size = 0;
            std::uint64_t revision = 0;
            D3DFORMAT format = D3DFMT_UNKNOWN;
            std::uint32_t minRaw = 0;
            std::uint32_t maxRaw = 0;
            UINT vertexCount = 0;
            UINT knownUsedCount = 0;
            bool valid = false;
        };

        // One-entry depth-classification memo for immutable CPU shadow spans.
        // Only VB draws can use it: UP pointers have no tracked write generation.
        // The IB identity also fences the referenced-index mask for indexed VB.
        struct R30XyzrhwDepthSignatureCache
        {
            bool valid = false;
            R30ShadowCopyCache vertex;
            R30ShadowCopyCache index;
            bool indexed = false;
            UINT vertexCount = 0;
            UINT stride = 0;
            float minZ = 0.0f;
            float maxZ = 0.0f;
            D3DMATRIX projection{};
            bool projectedDepth = false;
        };

        struct R30ScratchBuffers
        {
            R30ShadowCopyCache vertexCopy;
            R30ShadowCopyCache indexCopy;
            R30IndexDecodeCache indexDecode;
            R30XyzrhwDepthSignatureCache depthSignature;
            // Port R26+HUD's 00873 write-only scratch to the R84 chain.
            // Revision and covered-byte checks still gate every shadow copy.
            OutRunVR::R30ScratchBytes::WriteOnlyByteScratch source;
            OutRunVR::R30ScratchBytes::WriteOnlyByteScratch indexSource;
            // Port 00874's independently allocated write-only eye outputs:
            // every draw seeds validated source bytes before per-eye changes;
            // no growth-time vector zero fill. Masks guard sparse untouched slots.
            OutRunVR::R30ScratchBytes::WriteOnlyByteScratch left;
            OutRunVR::R30ScratchBytes::WriteOnlyByteScratch right;
            std::vector<std::uint8_t> used;
            // Cached IB local-index order; only the first references are touched.
            // Reuse it across unchanged IB generations to seed sparse VB stereo
            // without scanning the full min..max vertex span per draw.
            std::vector<std::uint32_t> vbTouched;
            // R30's 513..2048-reference depth classifier needs ascending
            // first-512 order. Reuse scratch memory for both producers; only
            // the VB result can survive across calls, fenced by the decoded
            // IB mask generation. A failed/rebuilt decode must never reuse it.
            std::vector<std::uint32_t> vbSortedDepthTouched;
            std::vector<std::uint32_t> upSortedDepthTouched;
            std::uint64_t vbTouchGeneration = 1;
            std::uint64_t vbDepthSortedGeneration = 0;
            // UP has no validated IB revision and must not mutate VB masks.
            std::vector<std::uint8_t> upUsed;
            std::vector<std::uint32_t> upTouched;
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

            // Streamed dynamic VB/IB Lock ranges normally arrive in increasing
            // offset order. Appending a disjoint range or extending the tail
            // can avoid binary search and vector insertion entirely. The tail
            // is last in the sorted/coalesced interval invariant.
            if (!ranges.empty())
            {
                auto& tail = ranges.back();
                if (begin >= tail.begin)
                {
                    if (begin <= tail.end)
                    {
                        tail.end = (std::max)(tail.end, end);
                        return;
                    }
                    ranges.push_back({begin, end});
                    return;
                }
            }

            // Out-of-order writes still use the full interval merge.
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
            // Most shadow copies read the newest streamed tail. Check it in
            // constant time before the binary search; only earlier ranges
            // require a search through the sorted interval set.
            if (!ranges.empty() && begin >= ranges.back().begin)
                return end <= ranges.back().end;
            // The merge writer maintains ascending, disjoint intervals; avoid
            // a full linear scan on every stereo VB/IB draw-time shadow read.
            const auto first = std::lower_bound(ranges.begin(), ranges.end(), begin,
                [](const R30ByteRange& range, UINT position) noexcept {
                    return range.end < position;
                });
            return first != ranges.end() &&
                first->begin <= begin && first->end >= end;
        }

        template <typename Buffer>
        R30ShadowPtr R30FindShadow(
            Buffer* buffer,
            const std::unordered_map<Buffer*, R30ShadowPtr>& registry,
            R30ShadowLookupCache& cached)
        {
            const auto epoch =
                R30ShadowRegistryEpoch.load(std::memory_order_acquire);
            if (cached.epoch == epoch)
            {
                for (const auto& slot : cached.slots)
                {
                    if (slot.buffer == buffer)
                        return slot.entry;
                }
            }

            // Membership and generation must be read under the same lock.
            // Reset/final Release and recycled COM addresses invalidate both
            // positive and negative cache entries together.
            std::lock_guard<std::mutex> lock(R30ShadowRegistryMutex);
            const auto lockedEpoch =
                R30ShadowRegistryEpoch.load(std::memory_order_relaxed);
            if (cached.epoch != lockedEpoch)
            {
                for (auto& slot : cached.slots)
                    slot = {};
                cached.epoch = lockedEpoch;
                cached.next = 0;
            }

            const auto it = registry.find(buffer);
            auto& slot = cached.slots[cached.next];
            cached.next = (cached.next + 1u) % 4u;
            slot.buffer = buffer;
            slot.entry = it == registry.end() ? nullptr : it->second;
            return slot.entry;
        }

        R30ShadowPtr R30FindVertexShadow(IDirect3DVertexBuffer9* buffer)
        {
            return R30FindShadow(buffer, R30VertexShadows, R30VertexLookup);
        }

        R30ShadowPtr R30FindIndexShadow(IDirect3DIndexBuffer9* buffer)
        {
            return R30FindShadow(buffer, R30IndexShadows, R30IndexLookup);
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
            // XYZRHW needs a shadow; FVF=0 declaration layouts stay eligible.
            if (desc.FVF != 0 &&
                (desc.FVF & D3DFVF_POSITION_MASK) != D3DFVF_XYZRHW)
                return nullptr;
            auto entry = std::make_shared<R30BufferShadow>();
            entry->size = desc.Size;
            entry->usage = desc.Usage;
            entry->pool = desc.Pool;
            std::lock_guard<std::mutex> lock(R30ShadowRegistryMutex);
            auto [it, inserted] = R30VertexShadows.emplace(buffer, entry);
            if (inserted)
                R30ShadowRegistryEpoch.fetch_add(1, std::memory_order_release);
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
            if (inserted)
                R30ShadowRegistryEpoch.fetch_add(1, std::memory_order_release);
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
                R30RecordTelemetryCounter(R30ShadowDiscardInvalidations);
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
                    entry->lastWriteRevision = entry->revision;
                    entry->lastWriteBegin = entry->lockOffset;
                    entry->lastWriteEnd = entry->lockOffset + entry->lockSize;
                    entry->lastWriteSafe =
                        (entry->lockFlags & D3DLOCK_DISCARD) == 0;
                    R30RecordTelemetryCounter(R30ShadowWrites);
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

        // Entry mutex must be held. A cached full-range snapshot can absorb
        // exactly ONE observed non-DISCARD write by copying only its overlap.
        // Do not use this path across DISCARD, failed Unlock, partial coverage,
        // a second write generation or a different buffer/span.
        bool R30TryIncrementalShadowCopy(
            const R30ShadowPtr& entry, UINT offset, UINT size,
            OutRunVR::R30ScratchBytes::WriteOnlyByteScratch& out,
            R30ShadowCopyCache& cache) noexcept
        {
            if (cache.entry != entry ||
                cache.offset != offset || cache.size != size ||
                out.size() != size ||
                cache.revision >= entry->revision ||
                entry->revision - cache.revision != 1u ||
                entry->lastWriteRevision != entry->revision ||
                !entry->lastWriteSafe ||
                offset > entry->size || size > entry->size - offset ||
                entry->bytes.size() != entry->size ||
                !R30RangeValid(entry->valid, offset, offset + size))
                return false;

            const UINT begin = (std::max)(offset, entry->lastWriteBegin);
            const UINT end =
                (std::min)(offset + size, entry->lastWriteEnd);
            if (begin < end)
                std::memcpy(out.data() + (begin - offset),
                    entry->bytes.data() + begin, end - begin);
            // Even a disjoint buffer write changes its revision. Bump the
            // copied snapshot revision so subsequent changes remain fenced.
            cache.revision = entry->revision;
            return true;
        }

        bool R30CopyVertexShadow(const R30ShadowPtr& entry,
            UINT offset, UINT size,
            OutRunVR::R30ScratchBytes::WriteOnlyByteScratch& out,
            R30ShadowCopyCache& cache)
        {
            if (!entry)
            {
                // Drop old scratch ownership if the buffer registry no longer
                // provides a live shadow (e.g. Release/Reset).
                cache.entry.reset();
                R30RecordTelemetryCounter(R30ShadowReadMisses);
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
                R30RecordTelemetryCounter(R30ShadowReadHits);
                return true;
            }
            if (R30TryIncrementalShadowCopy(entry, offset, size, out, cache))
            {
                R30RecordTelemetryCounter(R30ShadowReadHits);
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
                R30RecordTelemetryCounter(R30ShadowReadMisses);
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
            R30RecordTelemetryCounter(R30ShadowReadHits);
            return true;
        }

        bool R30CopyIndexShadow(const R30ShadowPtr& entry,
            UINT offset, UINT size,
            OutRunVR::R30ScratchBytes::WriteOnlyByteScratch& out,
            R30ShadowCopyCache& cache)
        {
            if (!entry)
            {
                // Drop old scratch ownership if the buffer registry no longer
                // provides a live shadow (e.g. Release/Reset).
                cache.entry.reset();
                R30RecordTelemetryCounter(R30ShadowReadMisses);
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
                R30RecordTelemetryCounter(R30ShadowReadHits);
                return true;
            }
            if (R30TryIncrementalShadowCopy(entry, offset, size, out, cache))
            {
                R30RecordTelemetryCounter(R30ShadowReadHits);
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
                R30RecordTelemetryCounter(R30ShadowReadMisses);
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
            R30RecordTelemetryCounter(R30ShadowReadHits);
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
                if (R30VertexShadows.erase(buffer))
                    R30ShadowRegistryEpoch.fetch_add(
                        1, std::memory_order_release);
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
                if (R30IndexShadows.erase(buffer))
                    R30ShadowRegistryEpoch.fetch_add(
                        1, std::memory_order_release);
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
            if (!device ||
                R30BufferCreationHooksReady.load(std::memory_order_acquire))
                return;
            // The R30 async install worker and Reset/rollback can race. Both
            // creation detours, the VB/IB Lock hooks and teardown share this
            // mutex: never publish a half-installed creation hook pair.
            std::lock_guard<std::mutex> creationInstallLock(R30ShadowHookMutex);
            if (R30BufferCreationHooksReady.load(std::memory_order_relaxed))
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
            if (R30CreateVertexBufferHook && R30CreateIndexBufferHook)
            {
                R30BufferCreationHooksReady.store(
                    true, std::memory_order_release);
                return;
            }
            // Leave readiness false on a failed half-install so a later
            // attempt retries only the missing hook rather than losing the
            // VB/IB shadow producer for the remainder of this device life.
            spdlog::warn(
                "VR R30.6 BUFFER SHADOW: creation hook incomplete; existing/dynamic buffers still register lazily on draw/Lock");
        }

        void R30RollbackBufferShadowHooks() noexcept
        {
            // Serialize teardown with the slow install path; a later retry
            // must not observe the previously published ready flags.
            std::lock_guard<std::mutex> hookInstallLock(R30ShadowHookMutex);
            R30BufferCreationHooksReady.store(false, std::memory_order_release);
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
                R30ShadowRegistryEpoch.fetch_add(
                    1, std::memory_order_release);
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
            // Keep the expensive D3DSBT_ALL object across Presents; Capture()
            // refreshes all current game state before each private glow pass.
            // Release before Reset/size changes together with the eye RTs.
            IDirect3DStateBlock9* savedGameState = nullptr;
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
            bool pauseResponsive = false;
            float eyeFov[8]{};
            // XR recommended extents can publish independently of FOV/pose.
            std::uint32_t eyeExtent[4]{};
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
            // StateBlock may hold references to game/eye surfaces. Release
            // before the textures on Reset or SkyGlow resize/reconfiguration.
            R30ReleaseCom(R30SkyGlow.savedGameState);
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

        bool R30GameGlowActive() noexcept
        {
            // Original EXE reducer's render-mode and glow-amount gate.
            return (*Module::exe_ptr<std::uint8_t>(0x39FCD5) & 3) == 2 &&
                *Module::exe_ptr<int>(0x4A8C40) != 0;
        }

        bool R30CaptureSkyGlowSceneBeforeHud(
            IDirect3DDevice9* device)
        {
            if (!device || Settings::SkyGlowFactor <= 0 ||
                !R30GameGlowActive())
                return false;
            // Most HUD draws arrive after the first successful scene copy.
            // Recheck *all* live R29 eligibility flags, not just the epoch:
            // a right-eye failure in this Present must invalidate reuse.
            if (R29OwnerSkyGlowCaptureStillValid(R30SkyGlowSceneCaptureEpoch))
                return true;
            const auto frame = R29OwnerCaptureFrameSnapshot();
            if (!frame.hadWorldStereo || !frame.hadDuplicatedDraw ||
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
            if (!device || Settings::SkyGlowFactor <= 0 ||
                !R30GameGlowActive())
                return true;
            const auto frame = R29OwnerCaptureFrameSnapshot();
            if (!R29OwnerStereoWanted() || !frame.hadWorldStereo ||
                !frame.hadDuplicatedDraw || frame.rightDrawFailed ||
                frame.stereoIncomplete || !frame.backBuffer ||
                !frame.rightEyeSurface)
                return true;

            if (!R30EnsureSkyGlowResources(device))
                return false;

            // Create once per SkyGlow resource epoch, then update the SAME
            // D3DSBT_ALL capture before changing any of the game's state.
            // Calling CreateStateBlock every Present pays the driver's COM
            // allocation/full-state setup cost even in the reduced-resolution
            // path. Capture retains its exact game-state restoration semantics.
            if (!R30SkyGlow.savedGameState)
            {
                if (FAILED(device->CreateStateBlock(
                        D3DSBT_ALL, &R30SkyGlow.savedGameState)) ||
                    !R30SkyGlow.savedGameState)
                {
                    R30ReleaseCom(R30SkyGlow.savedGameState);
                    return false;
                }
            }
            else if (FAILED(R30SkyGlow.savedGameState->Capture()))
            {
                // A failed Capture must not replay an earlier Present's state.
                R30ReleaseCom(R30SkyGlow.savedGameState);
                return false;
            }
            IDirect3DStateBlock9* const stateBlock = R30SkyGlow.savedGameState;
            IDirect3DSurface9* savedRt = nullptr;
            IDirect3DSurface9* savedDepth = nullptr;
            D3DVIEWPORT9 savedViewport{};
            if (FAILED(device->GetRenderTarget(0, &savedRt)) ||
                !savedRt ||
                FAILED(device->GetViewport(&savedViewport)))
            {
                if (savedRt) savedRt->Release();
                return false;
            }
            const HRESULT depthHr =
                device->GetDepthStencilSurface(&savedDepth);
            const bool depthOk =
                SUCCEEDED(depthHr) || depthHr == D3DERR_NOTFOUND;
            if (!depthOk)
            {
                savedRt->Release();
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
            // StateBlock::Apply restored physical shader/effect state,
            // but R29/R31's tracked snapshots predate the private glow pass.
            if (restoreOk)
                R29OwnerResynchronizeShaderEpoch(device);
            else
            {
                R30ReleaseCom(R30SkyGlow.savedGameState);
                R29OwnerInvalidateRendererStateAfterExternalRestore();
            }
            R29OwnerInvalidateEffectStateCache();

            if (ok && restoreOk)
            {
                R30RecordTelemetryCounter(R30SkyGlowFrames);
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

            R30RecordTelemetryCounter(R30SkyGlowFailures);
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
            else
            {
                // If stereo eligibility or SkyGlow is switched off, do not
                // retain an ALL-state snapshot referencing old game RT/depth
                // across indefinitely many mono Presents. The eye resources
                // themselves remain cached for a later stereo re-entry.
                R30ReleaseCom(R30SkyGlow.savedGameState);
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

        // Reuse exactly the same Present source geometry as the HUD cache
        // key. A second R29 snapshot could cross Reset/resize and cache the
        // new aspect ratio under previous-generation width/height.
        float R30HudAspectCompensation(
            const OutRunVRRenderer::LatchedStereoFrame& stereo,
            std::uint32_t sourceWidth, std::uint32_t sourceHeight,
            const std::uint32_t* publishedExtent = nullptr) noexcept
        {
            if (!sourceWidth || !sourceHeight)
                return 1.0f;

            const float sourceAspect =
                static_cast<float>(sourceWidth) /
                static_cast<float>(sourceHeight);

            // R35.4: SharedPoseState already carries the runtime's actual
            // recommended per-eye render-target size. That pixel aspect is the
            // quantity that finally stretches a screen-space HUD sprite in the
            // OpenXR projection swapchain. Using angular FOV aspect was close,
            // but on Quest/VDXR it leaves circular HUD elements slightly tall.
            float targetAspectSum = 0.0f;
            int targetEyes = 0;
            std::uint32_t pixelWidth[2]{}, pixelHeight[2]{};
            float pixelAspect[2]{};
            bool coherentEyePair = true;
            for (std::uint32_t eye = 0; eye < 2; ++eye)
            {
                std::uint32_t w = 0, h = 0;
                if (publishedExtent)
                {
                    w = publishedExtent[eye * 2u];
                    h = publishedExtent[eye * 2u + 1u];
                }
                else
                    R29OwnerRecommendedEyeExtent(eye, w, h);
                if (!w || !h)
                {
                    coherentEyePair = false;
                    continue;
                }
                const float aspect =
                    static_cast<float>(w) / static_cast<float>(h);
                if (!std::isfinite(aspect) ||
                    aspect < 0.25f || aspect > 4.0f)
                {
                    coherentEyePair = false;
                    continue;
                }
                pixelWidth[eye] = w;
                pixelHeight[eye] = h;
                pixelAspect[eye] = aspect;
            }

            // VDXR may publish a new recommended extent for one eye before
            // the other during resize/recenter. Mixing old/new pixel aspects,
            // or using a single valid eye, causes a visible HUD size pulse
            // and caches the wrong scale for the current Present. Accept
            // pixel aspect only from a coherent binocular publication.
            // Real asymmetric eye extents within 10% remain supported.
            if (coherentEyePair &&
                std::fabs(static_cast<float>(pixelWidth[0]) -
                    static_cast<float>(pixelWidth[1])) <= 0.10f *
                    static_cast<float>((std::max)(pixelWidth[0], pixelWidth[1])) &&
                std::fabs(static_cast<float>(pixelHeight[0]) -
                    static_cast<float>(pixelHeight[1])) <= 0.10f *
                    static_cast<float>((std::max)(pixelHeight[0], pixelHeight[1])))
            {
                targetAspectSum = pixelAspect[0] + pixelAspect[1];
                targetEyes = 2;
            }

            // A missing or mixed-generation eye pair falls back to the
            // common FOV geometry for that frame, rather than trusting stale
            // single-eye dimensions. When both eyes converge, pixel aspect
            // takes precedence again without persisting an invalid cache.
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

            // VDXR can transiently publish a finite yet inverted FOV for
            // one eye on recenter/resize. Do not let the surviving eye's
            // aspect resize BOTH HUD projections. A coherent pixel pair
            // already sets targetEyes=2 above; otherwise wait for BOTH
            // valid angular spans and retain neutral containment for now.
            if (targetEyes != 2)
                return 1.0f;

            const float targetAspect =
                targetAspectSum / static_cast<float>(targetEyes);
            const float compensation = sourceAspect / targetAspect;
            if (!std::isfinite(compensation))
                return 1.0f;
            return std::clamp(compensation, 0.75f, 3.50f);
        }

        // F11's ImGui shell is rasterised and sized independently for the
        // published XR eye density. Reapplying the *gameplay* HudScale here
        // double-shrinks its glyphs and window after that expensive rebuild.
        // Scope is explicit, thread-local and lasts only for RenderDrawData:
        // canonical SpriteNode HUD, pause/menu, world and SkyGlow remain on
        // the original contain mapping. The per-eye aspect and FOV affine
        // below are still applied so glyphs keep their original proportions.
        // Signed share of the game viewport height; positive moves ESC menu
        // downward on screen. The old fallback stays exactly zero for all
        // F11, gameplay HUD, world, GOAL/+TIME, title and unknown states.
        // Apply the SAME signed fraction in both XYZRHW and shader HUD paths.
        // The original option arrows/YES-NO are explicit ScreenHud sprites,
        // whereas the pause shell is generic ScreenOverlay2D. Keep both on
        // the SAME per-eye pause transform. This producer is never allowed
        // to promote unrelated ScreenHud or world/GOAL draws.
        bool R30IsPauseMenuExactArrow() noexcept
        {
            // Prefer a selected SpriteNode over any nested caller; when
            // no queue is active accept the exact original ESC E8 owner.
            // R30IsPauseMenuElement still gates the game state and F11.
            return OutRunVrPauseEye::ExactArrowOwner(
                OutRunVR::GameSemantic::EffectiveScope() ==
                    OutRunVR::GameSemantic::RenderScope::ScreenHud,
                OutRunVR::GameSemantic::CurrentRenderProducerToken() ==
                    OutRunVR::GameSemantic::ProducerToken::ExactScreenHudClipSprite);
        }

        // The source game draws the ESC shell as generic overlay and its
        // arrows/YES-NO as exact queued HUD sprites. Both must use one optical
        // correction; F11, ordinary HUD and results remain strictly excluded.
        bool R30IsPauseMenuElement() noexcept
        {
            return OutRunVR::GameSemantic::ExternalOverlaySemanticDepth == 0 &&
                Game::current_mode &&
                *Game::current_mode == GameState::STATE_SMPAUSEMENU &&
                (OutRunVR::GameSemantic::EffectiveScope() ==
                    OutRunVR::GameSemantic::RenderScope::ScreenOverlay2D ||
                 R30IsPauseMenuExactArrow());
        }

        float R30PauseMenuVerticalFraction() noexcept
        {
            if (!R30IsPauseMenuElement())
                return 0.0f;
            const float fraction = Settings::VRPauseMenuVerticalOffset.get();
            if (!std::isfinite(fraction))
                return 0.0f;
            return std::clamp(fraction, -0.25f, 0.25f);
        }

        OutRunVrPauseEye::VerticalAffine R30PauseMenuVerticalAffine(
            const OutRunVRRenderer::LatchedStereoFrame& stereo) noexcept
        {
            if (!R30IsPauseMenuElement())
                return {};
            // Model a head-forward/common vertical tangent interval. Unlike
            // horizontal mapping, the authored ESC shell should be optically
            // centred at tan(vertical angle)=0 even when both XR eyes share
            // the same asymmetric up/down FOV. Reject both eyes together if
            // recenter publishes a partial/invalid FOV.
            return OutRunVrPauseEye::Compute(
                stereo.eyeFov[0].angleDown, stereo.eyeFov[0].angleUp,
                stereo.eyeFov[1].angleDown, stereo.eyeFov[1].angleUp);
        }

        float R30HudScopeScale() noexcept
        {
            // F11 rasterises its atlas independently of gameplay HudScale.
            if (OutRunVR::GameSemantic::ExternalOverlaySemanticDepth != 0 &&
                OutRunVR::GameSemantic::EffectiveScope() ==
                    OutRunVR::GameSemantic::RenderScope::ScreenOverlay2D)
                return 1.0f;

            // Only a genuine original-game ESC/pause state, drawing generic
            // ScreenOverlay2D, gets its own centre-anchored legible scale.
            // Never enlarge gameplay ScreenHud, world, +TIME/GOAL or front-end.
            // A missing game-state pointer retains the baseline HUD setting.
            if (R30IsPauseMenuElement())
            {
                const float requested = Settings::VRPauseMenuScale.get();
                // A nonfinite/disabled pause setting is NOT permission to
                // magnify the generic gameplay HUD optical containment.
                if (!std::isfinite(requested) || requested <= 0.0f)
                    return R30HudScaleValue();
                // The XR portrait contain map consumes Y scale. In
                // responsive mode retain the legible original 1.0 -> 1.25
                // effective default without disabling smaller slider values.
                // External F11, GOAL, world and gameplay HUD remain isolated.
                // R84 visual recovery: user HMD evidence shows that
                // ResponsiveUserScale(1.0)=1.25 followed by an XR portrait
                // sqrt(aspect) boost magnifies ESC roughly twice. The slider
                // is the exact requested optical scale; preserve HUD/F11.
                return std::clamp(requested, 0.55f, 1.50f);
            }
            return R30HudScaleValue();
        }

        void R30HudContainScale(
            const OutRunVRRenderer::LatchedStereoFrame& stereo,
            float& scaleX, float& scaleY) noexcept
        {
            const auto frame = R29OwnerCaptureFrameSnapshot();
            const float userScale = R30HudScopeScale();
            // The exact pause owner is scoped to its native ESC state and
            // screen sprites; never let a generic HUD or F11 borrow its scale.
            const bool pauseResponsive = R30IsPauseMenuElement() &&
                Settings::VRHudResponsiveLayout.get() &&
                std::isfinite(Settings::VRPauseMenuScale.get()) &&
                Settings::VRPauseMenuScale.get() > 0.0f;
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
            // Capture once per HUD draw, reuse on a miss. A late XR host
            // publication must not reuse a stale target pixel aspect even
            // when the Present epoch, pose and FOV have not advanced.
            std::uint32_t eyeExtent[4]{};
            // Reject an in-progress host publication as a whole; never
            // combine the left-eye old size with the right-eye new size.
            // Empty dimensions follow the existing coherent-FOV fallback.
            R29OwnerReadCoherentEyeExtentPair(eyeExtent);
            bool canCache = frame.presentEpoch != 0 &&
                frame.width != 0 && frame.height != 0 &&
                std::isfinite(userScale);
            for (float angle : fov)
                canCache = canCache && std::isfinite(angle);

            bool fovMatches = true;
            for (int i = 0; i < 8; ++i)
                fovMatches = fovMatches &&
                    (R30HudContain.eyeFov[i] == fov[i]);
            bool extentMatches = true;
            for (int i = 0; i < 4; ++i)
                extentMatches = extentMatches &&
                    (R30HudContain.eyeExtent[i] == eyeExtent[i]);
            if (canCache && extentMatches && R30HudContain.valid &&
                R30HudContain.presentEpoch == frame.presentEpoch &&
                R30HudContain.poseSequence == stereo.poseSequence &&
                R30HudContain.sourceWidth == frame.width &&
                R30HudContain.sourceHeight == frame.height &&
                R30HudContain.userScale == userScale &&
                R30HudContain.pauseResponsive == pauseResponsive &&
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
                R30HudAspectCompensation(
                    stereo, frame.width, frame.height, eyeExtent);

            // Preserve the native sprite aspect: apply one shared optical
            // enlargement before the existing X/Y contain split. Only ESC
            // shell and exact arrows receive this correction; all other
            // world, HUD, menu and external overlay paths stay unchanged.
            // Apply only the aspect-preserving contain split, not a second
            // hidden pause enlargement. This is R84-only: the protected R26
            // rollback owner retains its existing independent implementation.
            const float opticalScale = userScale;
            if (sourceOverTarget >= 1.0f)
            {
                scaleX = opticalScale;
                scaleY = opticalScale / sourceOverTarget;
            }
            else
            {
                scaleX = opticalScale * sourceOverTarget;
                scaleY = opticalScale;
            }
            if (!canCache || !std::isfinite(scaleX) ||
                !std::isfinite(scaleY))
                return;

            R30HudContain.presentEpoch = frame.presentEpoch;
            R30HudContain.poseSequence = stereo.poseSequence;
            R30HudContain.sourceWidth = frame.width;
            R30HudContain.sourceHeight = frame.height;
            R30HudContain.userScale = userScale;
            R30HudContain.pauseResponsive = pauseResponsive;
            for (int i = 0; i < 8; ++i)
                R30HudContain.eyeFov[i] = fov[i];
            for (int i = 0; i < 4; ++i)
                R30HudContain.eyeExtent[i] = eyeExtent[i];
            R30HudContain.scaleX = scaleX;
            R30HudContain.scaleY = scaleY;
            R30HudContain.valid = true;
        }


        // Only exact, producer-owned gameplay text may leave the common-centre
        // containment mapping. The A/B setting defaults off and the broad
        // ScreenHud/ScreenOverlay2D classifications are NOT enough evidence.
        struct R30HudEdgeAnchor
        {
            float x = 0.0f, y = 0.0f;
            // Preserve exact-producer bounds from the existing single
            // source walk. No additional VB/IB scan in the hot draw path.
            float minX = 0.0f, maxX = 0.0f;
            float minY = 0.0f, maxY = 0.0f;
            bool hasBounds = false;
            float weight = 0.0f;
        };
        float R30PeripheralAnchor(float ndc, float limit) noexcept
        {
            return OutRunVrHudEdge::PeripheralAnchor(ndc, limit);
        }
        R30HudEdgeAnchor R30GetExactHudEdgeAnchor(
            const void* source, UINT count, UINT stride,
            float x0, float y0, float width, float height,
            const std::vector<std::uint8_t>* usedMask,
            const std::vector<std::uint32_t>* touched,
            UINT knownUsedCount) noexcept
        {
            if ((!Settings::VRHudResponsiveLayout.get() &&
                 !Settings::VRHudEdgeAnchors.get()) ||
                OutRunVR::GameSemantic::EffectiveScope() !=
                    OutRunVR::GameSemantic::RenderScope::ScreenHud ||
                OutRunVR::GameSemantic::CurrentRenderProducerToken() !=
                    OutRunVR::GameSemantic::ProducerToken::OutRunHudPeripheralText ||
                !source || !count || stride < 4u * sizeof(float) ||
                !(width > 0.0f && height > 0.0f))
                return {};
            float minX = x0 + width, maxX = x0;
            float minY = y0 + height, maxY = y0;
            bool seen = false;
            const auto* bytes = static_cast<const std::uint8_t*>(source);
            // The draw decoder has already produced a complete, unique
            // touched-index list for sparse indexed batches. Reuse it for
            // the semantic bounding box instead of scanning all VB entries.
            // Unindexed/uncertain batches keep the original full traversal.
            const bool sparseAnchorTouched = usedMask && touched &&
                knownUsedCount > 0u &&
                knownUsedCount == touched->size() &&
                knownUsedCount <= count / 4u;
            const UINT anchorVisitCount =
                sparseAnchorTouched ? knownUsedCount : count;
            for (UINT visit = 0; visit < anchorVisitCount; ++visit)
            {
                const UINT i =
                    sparseAnchorTouched ? (*touched)[visit] : visit;
                // Bad producer metadata cannot authorize a displaced HUD.
                if (i >= count ||
                    (sparseAnchorTouched && !(*usedMask)[i]))
                    return {};
                if (usedMask && !(*usedMask)[i])
                    continue;
                float xy[2]{};
                std::memcpy(xy, bytes + static_cast<std::size_t>(i) * stride,
                    sizeof(xy));
                // Invalid/outlying sprite coordinates cannot be used to
                // infer position. Retain exactly the baseline centred layout.
                if (!std::isfinite(xy[0]) || !std::isfinite(xy[1]) ||
                    xy[0] < x0 - width * 0.25f ||
                    xy[0] > x0 + width * 1.25f ||
                    xy[1] < y0 - height * 0.25f ||
                    xy[1] > y0 + height * 1.25f)
                    return {};
                minX = (std::min)(minX, xy[0]);
                maxX = (std::max)(maxX, xy[0]);
                minY = (std::min)(minY, xy[1]);
                maxY = (std::max)(maxY, xy[1]);
                seen = true;
            }
            if (!seen)
                return {};
            // Exact text may animate partly outside the source viewport.
            // The later bilateral guard rejects shifting this geometry, so
            // do not enlarge/re-anchor it beforehand: that caused a jump
            // as an incoming HUD glyph crossed the screen edge. Preserve
            // source coordinates/scale in BOTH eyes until entirely visible.
            if (minX < x0 || maxX > x0 + width ||
                minY < y0 || maxY > y0 + height)
                return {};
            // One source-space group anchor for the entire draw: preserve
            // relative glyph locations, colour/UV and per-eye disparity.
            const float cx = minX + 0.5f * (maxX - minX);
            const float cy = minY + 0.5f * (maxY - minY);
            const float rawAnchorX = (cx - x0) * (2.0f / width) - 1.0f;
            const float rawAnchorY = 1.0f - (cy - y0) * (2.0f / height);
            const float transitionWeight = (std::max)(
                OutRunVrHudEdge::PeripheralWeight(rawAnchorX),
                OutRunVrHudEdge::PeripheralWeight(rawAnchorY));
            // Partially offscreen animated HUD text keeps neutral placement.
            // Without an entry envelope, the next fully visible frame
            // suddenly applies the entire peripheral displacement and zoom.
            const float fullyVisibleWeight = OutRunVrHudEdge::FullyVisibleWeight(
                minX - x0, (x0 + width) - maxX,
                minY - y0, (y0 + height) - maxY, width, height);
            return {
                R30PeripheralAnchor(rawAnchorX, 0.82f) * fullyVisibleWeight,
                R30PeripheralAnchor(rawAnchorY, 0.78f) * fullyVisibleWeight,
                minX, maxX, minY, maxY, true,
                transitionWeight * fullyVisibleWeight
            };
        }

        // The anchor keeps an exact peripheral driving HUD group near its original
        // screen edge, but without a size floor HudScale=0.55 still makes
        // speed/time glyphs illegible inside a portrait XR eye. Only the
        // opt-in producer-verified peripheral draw may enlarge to 0.90 of
        // the original source layout. A centred group, F11, menus, world
        // markers and every default-off draw retain their original scale.
        float R30ExactPeripheralHudBoost(
            const R30HudEdgeAnchor& anchor) noexcept
        {
            if ((anchor.x == 0.0f && anchor.y == 0.0f) ||
                !std::isfinite(anchor.x) || !std::isfinite(anchor.y))
                return 1.0f;
            const float baseScale = R30HudScaleValue();
            if (!std::isfinite(baseScale) || baseScale <= 0.0f)
                return 1.0f;
            const float targetBoost =
                std::clamp(0.90f / baseScale, 1.0f, 3.0f);
            return OutRunVrHudEdge::BlendBoost(1.0f, targetBoost, anchor.weight);
        }


        // Issue #119: enlarged peripheral speed/rank/time draws may extend
        // beyond the source viewport, especially at 21:9 -> portrait XR.
        // Fit their exact producer bounds inside a modest source-space safe
        // inset. One SHARED horizontal correction is applied to both eyes:
        // never clamp eyes independently and thereby change stereo disparity.
        // Offscreen animations, centre HUD, unknown producers and oversized
        // groups preserve the previous transform without speculative motion.
        void R30ConstrainHudEdgeToVisibleBounds(
            const R30HudEdgeAnchor& anchor,
            float x0, float y0, float width, float height,
            const float eyeScaleX[2], const float eyeBiasX[2],
            float hudScaleY, float hudBiasY,
            const float eyeScaleY[2], const float eyeBiasY[2],
            float& edgeLeftBias, float& edgeRightBias,
            float& edgeYBias) noexcept
        {
            if (!anchor.hasBounds ||
                (anchor.x == 0.0f && anchor.y == 0.0f) ||
                !(width > 0.0f && height > 0.0f) ||
                !std::isfinite(width) || !std::isfinite(height) ||
                !std::isfinite(hudScaleY) || !std::isfinite(hudBiasY) ||
                !eyeScaleY || !eyeBiasY ||
                !std::isfinite(eyeScaleY[0]) ||
                !std::isfinite(eyeScaleY[1]) ||
                !std::isfinite(eyeBiasY[0]) ||
                !std::isfinite(eyeBiasY[1]) ||
                eyeScaleY[0] <= 0.0f || eyeScaleY[1] <= 0.0f)
                return;
            const float x1 = x0 + width, y1 = y0 + height;
            // Deliberately do not shift partially offscreen transition
            // sprites into view or change the GOAL/results animation.
            if (anchor.minX < x0 || anchor.maxX > x1 ||
                anchor.minY < y0 || anchor.maxY > y1 ||
                anchor.minX > anchor.maxX || anchor.minY > anchor.maxY)
                return;

            constexpr float kSafeInset = 0.025f;
            const float safeLeft = x0 + width * kSafeInset;
            const float safeRight = x1 - width * kSafeInset;
            const float safeTop = y0 + height * kSafeInset;
            const float safeBottom = y1 - height * kSafeInset;
            const float leftMin =
                eyeScaleX[0] * anchor.minX + eyeBiasX[0] + edgeLeftBias;
            const float rightMin =
                eyeScaleX[1] * anchor.minX + eyeBiasX[1] + edgeRightBias;
            const float leftMax =
                eyeScaleX[0] * anchor.maxX + eyeBiasX[0] + edgeLeftBias;
            const float rightMax =
                eyeScaleX[1] * anchor.maxX + eyeBiasX[1] + edgeRightBias;
            const float shiftMin = (std::max)(
                safeLeft - leftMin, safeLeft - rightMin);
            const float shiftMax = (std::min)(
                safeRight - leftMax, safeRight - rightMax);
            if (std::isfinite(shiftMin) && std::isfinite(shiftMax) &&
                shiftMin <= shiftMax)
            {
                const float sharedShift = std::clamp(0.0f, shiftMin, shiftMax);
                edgeLeftBias += sharedShift;
                edgeRightBias += sharedShift;
            }

            // Match the actual paired-eye draw, not the pre-FOV HUD
            // containment. Vertical FOV/optical centres can differ between
            // eyes; a single-eye inset would clip the other eye at 21:9.
            // Preserve one COMMON correction so binocular disparity remains.
            const float leftYMin =
                eyeScaleY[0] * anchor.minY + eyeBiasY[0] + edgeYBias;
            const float rightYMin =
                eyeScaleY[1] * anchor.minY + eyeBiasY[1] + edgeYBias;
            const float leftYMax =
                eyeScaleY[0] * anchor.maxY + eyeBiasY[0] + edgeYBias;
            const float rightYMax =
                eyeScaleY[1] * anchor.maxY + eyeBiasY[1] + edgeYBias;
            const float verticalMin = (std::max)(
                safeTop - leftYMin, safeTop - rightYMin);
            const float verticalMax = (std::min)(
                safeBottom - leftYMax, safeBottom - rightYMax);
            if (std::isfinite(verticalMin) && std::isfinite(verticalMax) &&
                verticalMin <= verticalMax)
                edgeYBias += std::clamp(0.0f, verticalMin, verticalMax);
        }

        // Issue #119: an exact, opt-in driving HUD group can be much too
        // small after ultrawide desktop -> portrait XR containment. Retain
        // the established 0.90 horizontal floor, but let the group approach
        // 0.65 vertical source scale ONLY when its complete exact bounds can
        // still fit both eyes after a single shared displacement. This is a
        // bounded producer-only operation, never a global ScreenHud zoom.
        float R30AdaptivePeripheralHudBoost(
            const R30HudEdgeAnchor& anchor,
            float x0, float y0, float width, float height,
            float hudScaleX, float hudScaleY,
            const float eyeScale[2], const float eyeOffset[2],
            float previousBoost) noexcept
        {
            if (!anchor.hasBounds ||
                (anchor.x == 0.0f && anchor.y == 0.0f) ||
                !(width > 0.0f && height > 0.0f) ||
                !(hudScaleX > 0.0f && hudScaleY > 0.0f) ||
                !std::isfinite(hudScaleX) || !std::isfinite(hudScaleY) ||
                !std::isfinite(previousBoost) || previousBoost < 1.0f ||
                previousBoost > 3.0f ||
                anchor.minX < x0 || anchor.maxX > x0 + width ||
                anchor.minY < y0 || anchor.maxY > y0 + height)
                return previousBoost;

            const float fullDesired = std::clamp(
                0.65f / hudScaleY, previousBoost, 3.0f);
            const float desired = OutRunVrHudEdge::BlendBoost(
                previousBoost, fullDesired, anchor.weight);
            // A bilateral common translation is feasible iff both projected
            // X intervals share an allowed shift and the Y interval fits.
            // Do not discard one eye, clamp the eyes separately, or shrink a
            // previously verified 0.90-horizontal baseline on failure.
            const float halfWidth = width * 0.5f;
            const float halfHeight = height * 0.5f;
            const float centerX = x0 + halfWidth;
            const float centerY = y0 + halfHeight;
            const float safeLeft = x0 + 0.025f * width;
            const float safeRight = x0 + 0.975f * width;
            const float safeTop = y0 + 0.025f * height;
            const float safeBottom = y0 + 0.975f * height;
            auto fitsBothEyes = [&](float boost) noexcept {
                float shiftMin = -std::numeric_limits<float>::infinity();
                float shiftMax = std::numeric_limits<float>::infinity();
                for (int eye = 0; eye < 2; ++eye)
                {
                    const float scale = hudScaleX * boost * eyeScale[eye];
                    const float bias = (1.0f - scale) *
                        (centerX + halfWidth * anchor.x) +
                        eyeOffset[eye] * halfWidth;
                    const float groupMin = scale * anchor.minX + bias;
                    const float groupMax = scale * anchor.maxX + bias;
                    if (!(scale > 0.0f) || !std::isfinite(groupMin) ||
                        !std::isfinite(groupMax))
                        return false;
                    shiftMin = (std::max)(shiftMin, safeLeft - groupMin);
                    shiftMax = (std::min)(shiftMax, safeRight - groupMax);
                }
                const float scaleY = hudScaleY * boost;
                const float biasY = (1.0f - scaleY) *
                    (centerY - halfHeight * anchor.y);
                const float groupTop = scaleY * anchor.minY + biasY;
                const float groupBottom = scaleY * anchor.maxY + biasY;
                return std::isfinite(shiftMin) && std::isfinite(shiftMax) &&
                    shiftMin <= shiftMax && scaleY > 0.0f &&
                    std::isfinite(groupTop) && std::isfinite(groupBottom) &&
                    safeTop - groupTop <= safeBottom - groupBottom;
            };
            if (!fitsBothEyes(previousBoost))
            {
                // The old 0.90x glyph floor can clip one eye when the
                // asymmetric FOV/optical offsets leave no common bilateral
                // shift. Keep the original draw visible instead of keeping
                // a known-unfit enlargement. Never shrink below the ordinary
                // unboosted HUD size; preserve zero-disparity shared motion.
                if (!fitsBothEyes(1.0f))
                    return 1.0f;
                float low = 1.0f, high = previousBoost;
                for (int i = 0; i < 10; ++i)
                {
                    const float mid = low + (high - low) * 0.5f;
                    if (fitsBothEyes(mid))
                        low = mid;
                    else
                        high = mid;
                }
                return low;
            }
            if (desired <= previousBoost)
                return previousBoost;
            if (fitsBothEyes(desired))
                return desired;

            // Issue #119 hot path: for a clipped peripheral group the stereo
            // fit constraints are linear in the common boost. Derive the
            // largest feasible scale from every cross-eye min/max pair and
            // the source-height span. Normally this takes one validation
            // instead of eight bisection probes per exact HUD draw. A failed
            // or nonfinite estimate retains the original conservative search.
            // Both eyes still share ONE shift; no per-eye recentering.
            float cappedBoost = desired;
            const float ySpan = anchor.maxY - anchor.minY;
            if (ySpan > 0.0f)
                cappedBoost = (std::min)(cappedBoost,
                    (safeBottom - safeTop) / (hudScaleY * ySpan));
            const float anchorCenter = centerX + halfWidth * anchor.x;
            for (int minEye = 0; minEye < 2; ++minEye)
            {
                for (int maxEye = 0; maxEye < 2; ++maxEye)
                {
                    const float slope = hudScaleX *
                        (eyeScale[maxEye] *
                            (anchor.maxX - anchorCenter) -
                         eyeScale[minEye] *
                            (anchor.minX - anchorCenter));
                    const float baselineSpan =
                        (eyeOffset[maxEye] - eyeOffset[minEye]) * halfWidth;
                    if (!std::isfinite(slope) ||
                        !std::isfinite(baselineSpan))
                        return previousBoost;
                    if (slope > 0.0f)
                        cappedBoost = (std::min)(cappedBoost,
                            ((safeRight - safeLeft) - baselineSpan) / slope);
                }
            }
            if (std::isfinite(cappedBoost) &&
                cappedBoost > previousBoost &&
                fitsBothEyes(cappedBoost))
                return cappedBoost;

            // Only exact producer groups enter this bounded search. Never
            // permit a boost below the verified baseline; finite eight-step
            // bisection is independent of viewport resolution/eye count.
            float low = previousBoost, high = desired;
            for (int i = 0; i < 8; ++i)
            {
                const float mid = low + (high - low) * 0.5f;
                if (fitsBothEyes(mid))
                    low = mid;
                else
                    high = mid;
            }
            return low;
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
            FlatPerspectiveEffect,
            ExactLensCentreWorld,
            ProjectedWorldMarker2D
        };

        // Strict R84 C993 source proof, ported from the protected R26
        // comparison owner without changing the actual world renderer.
        // A possibly head-injected live D3D9 c64 is NOT original-game WVP.
        bool R30HasExactLensCentreRawWvp(float original[16]) noexcept
        {
            using namespace OutRunVR::GameSemantic;
            if (!original || QueueRenderActive() ||
                EffectiveScope() != RenderScope::WorldBillboard ||
                CurrentRenderProducerToken() != ProducerToken::LensFlareCentre)
                return false;
            std::uint64_t writeSerial = 0, writeDraw = 0;
            std::uintptr_t writeShader = 0, currentShader = 0;
            std::uint64_t writeShaderEpoch = 0, currentShaderEpoch = 0;
            RenderScope sourceScope = RenderScope::None;
            std::uint64_t queueEpoch = 0;
            const void* queueNode = nullptr;
            ProducerToken sourceProducer = ProducerToken::None;
            if (!OutRunVRRenderer::GetLastRawGameWvpWrite(
                    original, writeSerial, writeDraw,
                    writeShader, writeShaderEpoch) ||
                !OutRunVRRenderer::GetLastGameWvpSemanticProvenance(
                    sourceScope, queueEpoch, queueNode, sourceProducer) ||
                !R29OwnerCurrentShaderEpoch(currentShader, currentShaderEpoch))
                return false;
            return OutRunVR::LensCentre::OwnsRawWvp({
                CurrentLensCentreCallEpoch,
                OutRunVRRenderer::GetLastGameWvpLensCentreCallEpoch(),
                OutRunVRRenderer::GetCurrentLatchedPoseEpoch(),
                OutRunVRRenderer::GetLastGameWvpPoseEpoch(),
                R29OwnerTopLevelDrawSerial() + 1u, writeDraw,
                currentShader, writeShader,
                currentShaderEpoch, writeShaderEpoch,
                sourceScope == RenderScope::WorldBillboard,
                sourceProducer == ProducerToken::LensFlareCentre,
                queueNode == nullptr
            });
        }

        // Port the HMD-proven R26+HUD original-c64 admission to R84.
        // A live GPU c64 register can already contain a previous head/eye
        // reprojection. Never feed it into a second HUD world-plane transform.
        bool R30GetRecentOriginalHudWvp(float out[16]) noexcept
        {
            if (!out ||
                !OutRunVR::GameSemantic::CorroboratesHud(
                    OutRunVR::GameSemantic::EffectiveScope()))
                return false;
            std::uint64_t writeSerial = 0, writeDrawSerial = 0;
            std::uintptr_t writeShader = 0, currentShader = 0;
            std::uint64_t writeEpoch = 0, currentEpoch = 0;
            if (!OutRunVRRenderer::GetLastRawGameWvpWrite(
                    out, writeSerial, writeDrawSerial,
                    writeShader, writeEpoch) ||
                !R29OwnerCurrentShaderEpoch(currentShader, currentEpoch) ||
                !writeShader || writeShader != currentShader ||
                !writeEpoch || writeEpoch != currentEpoch ||
                !OutRunVRRenderer::GetCurrentLatchedPoseEpoch() ||
                OutRunVRRenderer::GetCurrentLatchedPoseEpoch() !=
                    OutRunVRRenderer::GetLastGameWvpPoseEpoch())
                return false;
            // R26 used a 12-draw original WVP window for direct and queued
            // HUD glyphs. Longer-lived/stale uploads must keep the lower
            // fail-closed path, never borrow an unrelated world's c64.
            const std::uint64_t nextDraw =
                R29OwnerTopLevelDrawSerial() + 1u;
            return nextDraw > writeDrawSerial &&
                nextDraw - writeDrawSerial <= 12u;
        }

        R30ScreenSpaceKind R30ClassifyScreenSpacePass(
            IDirect3DDevice9* device) noexcept
        {
            if (!device || !R29OwnerTargetIsBackBuffer())
                return R30ScreenSpaceKind::None;

            // This exact car/rival rank SpriteNode carries its own original
            // Calc3D2D view-space anchor; it is not generic screen HUD.
            // A missing anchor must never reuse an earlier vehicle's depth.
            const auto scope = OutRunVR::GameSemantic::EffectiveScope();
            if (OutRunVR::GameSemantic::CorroboratesProjectedWorldMarker(scope))
            {
                const auto* marker =
                    OutRunVR::GameSemantic::CurrentProjectedMarker();
                return marker && marker->valid
                    ? R30ScreenSpaceKind::ProjectedWorldMarker2D
                    : R30ScreenSpaceKind::None;
            }

            // The R26+HUD HMD comparison build requires source semantics in
            // addition to D3D state. In R84 an untagged depth-disabled alpha
            // road/sky/particle draw could be sent through the finite HUD
            // plane, breaking per-eye world projection and leaving black
            // regions. No render-state heuristic can grant HUD ownership.
            const bool ownedHud =
                OutRunVR::GameSemantic::CorroboratesHud(scope);
            const bool ownedOverlay =
                OutRunVR::GameSemantic::CorroboratesScreenOverlay2D(scope);
            const bool ownedEffect =
                scope == OutRunVR::GameSemantic::RenderScope::SceneEffect ||
                OutRunVR::GameSemantic::CorroboratesProjectedScreenEffect(scope);
            const bool ownedLensCentre =
                !OutRunVR::GameSemantic::QueueRenderActive() &&
                scope == OutRunVR::GameSemantic::RenderScope::WorldBillboard &&
                OutRunVR::GameSemantic::CurrentRenderProducerToken() ==
                    OutRunVR::GameSemantic::ProducerToken::LensFlareCentre;
            if (!ownedHud && !ownedOverlay && !ownedEffect &&
                !ownedLensCentre)
                return R30ScreenSpaceKind::None;

            // R84 regression guard: an untagged SpriteNode defaults to
            // ScreenOverlay2D, but that fallback is NOT evidence that a
            // perspective/3D draw is safe to flatten into the HMD HUD plane.
            // R30's verified XYZRHW path still handles generic 2D sprites.
            // ScreenHud is an exact producer-owned semantic, not this fallback.
            // Classify the original game's projection before accepting any
            // shader-based screen pass.
            float m34 = 0.0f;
            float m44 = 0.0f;
            if (!OutRunVRRenderer::GetRendererProjectionSignature(m34, m44))
                return R30ScreenSpaceKind::None;

            const auto projectionClass =
                OutRunVR::PassPolicy::ClassifyProjectionSignature(m34, m44);
            if (projectionClass ==
                OutRunVR::PassPolicy::ProjectionClass::Orthographic2D)
                return (ownedHud || ownedOverlay)
                    ? R30ScreenSpaceKind::Hud2D
                    : R30ScreenSpaceKind::None;

            if (projectionClass !=
                OutRunVR::PassPolicy::ProjectionClass::Perspective3D)
                return R30ScreenSpaceKind::None;

            // A positively identified HUD producer can use its original-game
            // raw c64 and finite view-plane transform even with a perspective
            // projection. A generic ScreenOverlay2D has no equivalent proof:
            // never treat a queue fallback as a perspective HUD/scene effect.
            if (ownedHud)
                return R30ScreenSpaceKind::Hud2D;
            if (ownedOverlay)
                return R30ScreenSpaceKind::None;

            // A source-owned direct C993 centre is a spatial WorldBillboard,
            // not a generic depth-disabled alpha overlay. Its original game
            // may vary Z/alpha states inside the draw; do not let those states
            // veto its per-eye transform after exact call/pose/shader/WVP proof.
            // The original GPU c64 is preserved separately for restoration.
            if (ownedLensCentre)
            {
                float originalGameWvp[16]{};
                const bool owned =
                    R30HasExactLensCentreRawWvp(originalGameWvp);
                if (Settings::VRTelemetry)
                {
                    static thread_local bool reportedOwned = false;
                    static thread_local bool reportedMiss = false;
                    bool& reported = owned ? reportedOwned : reportedMiss;
                    if (!reported)
                    {
                        reported = true;
                        spdlog::info(
                            "VR R84 C993 RAW_WVP_SOURCE: {} "
                            "(same call/pose/shader/draw; "
                            "stereo requires exact owned raw game WVP)",
                            owned ? "EXACT_OWNER" : "MISSING_OR_STALE");
                    }
                }
                if (OutRunVR::LensCentre::SelectWorldRoute(true, owned) ==
                        OutRunVR::LensCentre::WorldRoute::ExactCentreStereo)
                    return R30ScreenSpaceKind::ExactLensCentreWorld;
                // Missing source must not become ScreenHud or borrow a
                // previously head-injected live shader constant.
                return R30ScreenSpaceKind::None;
            }

            // All other tagged overlays/effects retain the conservative
            // alpha/depth heuristic and StateBlock-aware cached state.
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
            {
                // Do not promote any other direct WorldBillboard, including
                // nested projected-effect calls, to flat HUD space.
                if (!OutRunVR::GameSemantic::QueueRenderActive() &&
                    scope == OutRunVR::GameSemantic::RenderScope::WorldBillboard)
                    return R30ScreenSpaceKind::None;
                return R30ScreenSpaceKind::FlatPerspectiveEffect;
            }
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
            bool projectedWorldMarker = false;
            OutRunVR::RankMarker::StereoNdcShift projectedRank{};
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

        // GetFVF is zero for valid declaration-only fixed-function layouts.
        // Accept only an exact float4 POSITIONT header at byte zero: all
        // stereo decoders read the first four floats as X/Y/Z/RHW.
        // Unknown streams, offsets and overlapping attributes fail closed.
        // R84 mainline counterpart of the HMD-tested R26_SAFE R57 route.
        // The point is produced by an exact Calc3D2D game CALL, not inferred
        // from alpha/RHW or another car's most recent shader constants.
        bool R30ProjectRankAnchor(
            const OutRunVR::GameSemantic::ProjectedMarkerInfo& marker,
            const D3DMATRIX& transform, float& x, float& y) noexcept
        {
            if (!marker.valid || !std::isfinite(marker.viewX) ||
                !std::isfinite(marker.viewY) || !std::isfinite(marker.viewZ) ||
                !R29OwnerMatrixFinite(transform))
                return false;
            const float clipX = marker.viewX * transform._11 +
                marker.viewY * transform._21 + marker.viewZ * transform._31 +
                transform._41;
            const float clipY = marker.viewX * transform._12 +
                marker.viewY * transform._22 + marker.viewZ * transform._32 +
                transform._42;
            const float clipW = marker.viewX * transform._14 +
                marker.viewY * transform._24 + marker.viewZ * transform._34 +
                transform._44;
            if (!std::isfinite(clipX) || !std::isfinite(clipY) ||
                !std::isfinite(clipW) || clipW <= 1.0e-6f)
                return false;
            x = clipX / clipW;
            y = clipY / clipW;
            return std::isfinite(x) && std::isfinite(y);
        }

        bool R30BuildProjectedRankDelta(
            const OutRunVRRenderer::LatchedStereoFrame& stereo,
            const D3DMATRIX& baseProjection,
            OutRunVR::RankMarker::StereoNdcShift& shift) noexcept
        {
            const auto* marker =
                OutRunVR::GameSemantic::CurrentProjectedMarker();
            if (!marker || !marker->valid ||
                !R29OwnerMatrixFinite(baseProjection) ||
                !R30ProjectRankAnchor(*marker, baseProjection,
                    shift.baseX, shift.baseY))
                return false;

            float headRaw[16]{};
            std::uint32_t headSequence = 0;
            if (!OutRunVRRenderer::GetLatchedHeadInverse(
                    headRaw, headSequence) ||
                headSequence != stereo.poseSequence)
                return false;
            D3DMATRIX headInverse{};
            std::memcpy(&headInverse, headRaw, sizeof(headInverse));
            if (!R29OwnerMatrixFinite(headInverse))
                return false;

            const float center[3]{
                0.5f * (stereo.eyeOffset[0][0] + stereo.eyeOffset[1][0]),
                0.5f * (stereo.eyeOffset[0][1] + stereo.eyeOffset[1][1]),
                0.5f * (stereo.eyeOffset[0][2] + stereo.eyeOffset[1][2])
            };
            const float identity[4]{0.0f, 0.0f, 0.0f, 1.0f};
            for (int eye = 0; eye < 2; ++eye)
            {
                const float relative[3]{
                    stereo.eyeOffset[eye][0] - center[0],
                    stereo.eyeOffset[eye][1] - center[1],
                    stereo.eyeOffset[eye][2] - center[2]
                };
                const D3DMATRIX eyePose =
                    R29OwnerMatrixFromQuaternionTranslation(
                        identity, relative,
                        Settings::VRWorldScale * Settings::VRStereoDepth);
                const D3DMATRIX eyeTransform = R29OwnerMultiplyMatrix(
                    R29OwnerMultiplyMatrix(
                        headInverse, R29OwnerInverseRigid(eyePose)),
                    R29OwnerProjectionFromFov(
                        baseProjection, stereo.eyeFov[eye]));
                float projectedX = 0.0f, projectedY = 0.0f;
                if (!R30ProjectRankAnchor(
                        *marker, eyeTransform, projectedX, projectedY))
                    return false;
                shift.deltaX[eye] = projectedX - shift.baseX;
                shift.deltaY[eye] = projectedY - shift.baseY;
                if (!std::isfinite(shift.deltaX[eye]) ||
                    !std::isfinite(shift.deltaY[eye]) ||
                    std::fabs(shift.deltaX[eye]) > 2.0f ||
                    std::fabs(shift.deltaY[eye]) > 2.0f)
                    return false;
            }
            return true;
        }

        bool R30HasXyzrhwInputLayout(IDirect3DDevice9* device) noexcept
        {
            DWORD fvf = 0;
            if (!device || FAILED(device->GetFVF(&fvf)))
                return false;
            if (fvf != 0)
                return (fvf & D3DFVF_POSITION_MASK) == D3DFVF_XYZRHW;

            IDirect3DVertexDeclaration9* declaration = nullptr;
            if (FAILED(device->GetVertexDeclaration(&declaration)) ||
                !declaration)
            {
                if (declaration)
                    declaration->Release();
                return false;
            }
            D3DVERTEXELEMENT9 elements[MAXD3DDECLLENGTH]{};
            UINT count = MAXD3DDECLLENGTH;
            const HRESULT hr = declaration->GetDeclaration(elements, &count);
            declaration->Release();
            if (FAILED(hr) || count < 2u || count > MAXD3DDECLLENGTH)
                return false;

            bool positionT = false;
            for (UINT i = 0; i < count; ++i)
            {
                const auto& e = elements[i];
                if (e.Stream == 0xFFu && e.Type == D3DDECLTYPE_UNUSED)
                    return i + 1u == count && positionT;
                if (e.Stream != 0u || e.Method != D3DDECLMETHOD_DEFAULT)
                    return false;
                if (e.Usage == D3DDECLUSAGE_POSITIONT)
                {
                    if (positionT || i != 0u || e.Offset != 0u ||
                        e.Type != D3DDECLTYPE_FLOAT4 ||
                        e.UsageIndex != 0u)
                        return false;
                    positionT = true;
                }
                else if (e.Offset < 4u * sizeof(float) ||
                         e.Usage == D3DDECLUSAGE_POSITION)
                    return false;
            }
            return false;
        }

        bool R30PrepareXyzrhwState(
            IDirect3DDevice9* device, R30XyzrhwState& state) noexcept
        {
            // World VS draws cannot be XYZRHW; skip the expensive stable
            // stereo checks before crossing the per-draw fast-world path.
            if (R29OwnerCurrentVertexShaderIdentity() != 0 ||
                !R29OwnerStableStereoBase(device))
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

            if (!R30HasXyzrhwInputLayout(device))
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

            // This XYZRHW draw needs only the R29-owned pose fence.
            // Zero/unlatched and mismatched-pose decisions stay unchanged.
            const std::uint32_t framePoseSequence =
                R29OwnerFrameStereoPoseSequence();
            if (!OutRunVRRenderer::GetLatchedStereoFrame(state.stereo) ||
                state.stereo.poseSequence == 0 ||
                (framePoseSequence != 0 &&
                 framePoseSequence != state.stereo.poseSequence) ||
                !R30BuildEyeAffine(state.stereo,
                    state.eyeScale, state.eyeOffset))
                return false;

            return true;
        }

        bool R30XyzrhwHasProjectedDepthSignature(
            const void* source, UINT vertexCount, UINT stride,
            const R30XyzrhwState& state, const D3DMATRIX& projection,
            const std::vector<std::uint8_t>* usedMask,
            const std::vector<std::uint32_t>* touched) noexcept
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
            // A frame's smoke/sand VB can contain hundreds of homogeneous
            // projected vertices. The classifier only needs the final two
            // ratios; bound their possible future values and stop once neither
            // HUD nor world classification can change. Count selected vertices
            // only (indexed usedMask may skip holes). Check in 16-sample blocks
            // so the bound arithmetic does not cost more than the depth work.
            const UINT sampleLimit = vertexCount < 512u ? vertexCount : 512u;
            // Indexed-UP/IB producers already supply a unique touched list
            // and a matching mask. On small referenced sets, walking the
            // entire [min,max] vertex span (often thousands of empty slots)
            // costs more than depth math. At <=512 unique references every
            // referenced vertex is considered, irrespective of visit order;
            // the conservative early-exit bounds are order-independent.
            // Larger sets retain the original ascending first-512 sampling
            // to preserve exact HUD/world classification.
            bool fastTouched = usedMask && touched && !touched->empty() &&
                touched->size() <= 512u &&
                touched->size() <= vertexCount &&
                usedMask->size() >= vertexCount;
            // The <=512 direct list skips sorting. Its caller must therefore
            // be the same leased UP or validated IB decoder that guaranteed
            // unique referenced indices. An arbitrary list could duplicate
            // the same vertex and change projected-depth classification.
            // In that case retain the original dense ascending mask walk.
            const bool directHintOwnedByProducer = R30Scratch.busy &&
                ((usedMask == &R30Scratch.upUsed &&
                  touched == &R30Scratch.upTouched) ||
                 (usedMask == &R30Scratch.used &&
                  touched == &R30Scratch.vbTouched &&
                  R30Scratch.indexDecode.valid &&
                  R30Scratch.indexDecode.vertexCount == vertexCount &&
                  R30Scratch.indexDecode.knownUsedCount == touched->size()));
            fastTouched = fastTouched && directHintOwnedByProducer;
            if (fastTouched)
            {
                // Validate the entire bounded list before the first early
                // classification decision; a corrupt hint falls back to the
                // original dense scan, never to a partial sample.
                for (const std::uint32_t index : *touched)
                {
                    if (index >= vertexCount || (*usedMask)[index] == 0)
                    {
                        fastTouched = false;
                        break;
                    }
                }
            }
            // Large, sparse indexed VB ranges previously scanned every
            // unused vertex just to find the first 512 selected depths.
            // Sorting bounded unique references restores the *original*
            // ascending first-512 sample exactly (the <=512 direct path
            // remains untouched). Do not allocate for dense/small draws.
            // The UP list changes on every call but its sort allocation can
            // be reused while holding R30ScratchLease. The VB/IB mask stays
            // immutable over a successful decoder generation; sorting it for
            // every newly written VB or altered projection wasted CPU on the
            // same large sparse index list. Never share scratch with a caller
            // that did not acquire the lease.
            std::vector<std::uint32_t> localSortedTouched;
            const bool trustedVbHint = R30Scratch.busy &&
                usedMask == &R30Scratch.used &&
                touched == &R30Scratch.vbTouched &&
                R30Scratch.indexDecode.valid &&
                R30Scratch.indexDecode.vertexCount == vertexCount &&
                R30Scratch.indexDecode.knownUsedCount == touched->size();
            const bool trustedUpHint = R30Scratch.busy &&
                usedMask == &R30Scratch.upUsed &&
                touched == &R30Scratch.upTouched;
            auto& sortedTouched = trustedVbHint
                ? R30Scratch.vbSortedDepthTouched
                : (trustedUpHint ? R30Scratch.upSortedDepthTouched
                                 : localSortedTouched);
            // Above 2048 sparse references, the old dense fallback visits
            // tens of thousands of empty vertices before the first 512.
            // Only a leased, uniquely decoded UP or VB/IB list may use the
            // bounded larger path; unknown hints retain the old fallback.
            const bool sortedCandidate = !fastTouched && usedMask && touched &&
                touched->size() > 512u &&
                (touched->size() <= 2048u ||
                 (touched->size() <= 16384u &&
                  (trustedVbHint || trustedUpHint))) &&
                touched->size() <= vertexCount &&
                usedMask->size() >= vertexCount &&
                vertexCount / touched->size() >= 8u;
            const bool largeSparseSample = sortedCandidate &&
                touched->size() > 2048u;
            const bool sortedCacheHit = sortedCandidate && trustedVbHint &&
                R30Scratch.vbDepthSortedGeneration ==
                    R30Scratch.vbTouchGeneration &&
                sortedTouched.size() ==
                    (largeSparseSample ? 512u : touched->size());
            if (!sortedCacheHit)
            {
                sortedTouched.clear();
                if (sortedCandidate)
                {
                    try
                    {
                        sortedTouched.assign(touched->begin(), touched->end());
                    }
                    catch (...)
                    {
                        sortedTouched.clear(); // original dense fallback
                    }
                    if (!sortedTouched.empty())
                    {
                        if (largeSparseSample)
                        {
                            // A decoded list is unique, but reject invalid
                            // bounds/membership before quick-select. Sorting
                            // every one of 16K indices defeats the benefit;
                            // nth_element keeps exactly the ascending first
                            // 512 after the final bounded sort.
                            bool membershipValid = true;
                            for (const std::uint32_t index : sortedTouched)
                            {
                                if (index >= vertexCount ||
                                    (*usedMask)[index] == 0)
                                {
                                    membershipValid = false;
                                    break;
                                }
                            }
                            if (!membershipValid)
                                sortedTouched.clear();
                            else
                            {
                                std::nth_element(
                                    sortedTouched.begin(),
                                    sortedTouched.begin() + 512u,
                                    sortedTouched.end());
                                sortedTouched.resize(512u);
                            }
                        }
                    }
                    if (!sortedTouched.empty())
                    {
                        std::sort(sortedTouched.begin(), sortedTouched.end());
                        // Reject a corrupt or duplicate hint. A stale mask
                        // always falls back to the original ascending scan.
                        for (std::size_t n = 0; n < sortedTouched.size(); ++n)
                        {
                            const std::uint32_t index = sortedTouched[n];
                            if (index >= vertexCount ||
                                (*usedMask)[index] == 0 ||
                                (n != 0u && sortedTouched[n - 1u] == index))
                            {
                                sortedTouched.clear();
                                break;
                            }
                        }
                        if (!sortedTouched.empty() && trustedVbHint)
                            R30Scratch.vbDepthSortedGeneration =
                                R30Scratch.vbTouchGeneration;
                    }
                }
            }
            const UINT visitCount = fastTouched
                ? static_cast<UINT>(touched->size()) :
                (sortedTouched.empty() ? vertexCount :
                    static_cast<UINT>(sortedTouched.size()));
            for (UINT visit = 0; visit < visitCount && sampled < 512u; ++visit)
            {
                const UINT i = fastTouched ? (*touched)[visit] :
                    (sortedTouched.empty() ? visit : sortedTouched[visit]);
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

                if ((sampled & 15u) == 0u)
                {
                    // Up to 'remaining' additional selected samples can still
                    // be visited. A guaranteed world result survives the
                    // worst case (all invalid for depth ratio, all valid HUD
                    // for projection ratio). A guaranteed HUD result survives
                    // the best case (all remaining valid/world). The bounds
                    // also hold for sparse indexed masks and early loop end.
                    const UINT remaining = sampleLimit - sampled;
                    if (valid >= 3u &&
                        valid * 2u >= sampled + remaining &&
                        projected * 4u >= (valid + remaining) * 3u)
                        return true;
                    if ((valid + remaining) * 2u < sampled + remaining ||
                        (projected + remaining) * 4u <
                            (valid + remaining) * 3u)
                        return false;
                }
            }

            return sampled >= 3u && valid >= 3u && valid * 2u >= sampled && projected * 4u >= valid * 3u;
        }

        bool R30ConfigureXyzrhwWorldEffect(
            IDirect3DDevice9* device, const void* source,
            UINT vertexCount, UINT stride, R30XyzrhwState& state,
            const std::vector<std::uint8_t>* usedMask = nullptr,
            const R30ShadowCopyCache* vertexCopy = nullptr,
            const R30ShadowCopyCache* indexCopy = nullptr,
            R30XyzrhwDepthSignatureCache* signatureCache = nullptr,
            const std::vector<std::uint32_t>* touched = nullptr) noexcept
        {
            float projectionRaw[16]{};
            D3DMATRIX baseProjection{};
            const bool haveBaseProjection =
                OutRunVRRenderer::GetRendererBaseProjection(projectionRaw);
            if (haveBaseProjection)
                std::memcpy(&baseProjection, projectionRaw, sizeof(baseProjection));

            // Queue-owned exact vehicle markers bypass particle Z/RHW
            // heuristics. Reproject each original view-space car anchor
            // without modifying other HUD, sky, alpha or world geometry.
            if (OutRunVR::GameSemantic::CorroboratesProjectedWorldMarker(
                    OutRunVR::GameSemantic::EffectiveScope()))
            {
                if (!haveBaseProjection ||
                    !R30BuildProjectedRankDelta(
                        state.stereo, baseProjection, state.projectedRank))
                    return false;
                state.projectedWorldMarker = true;
                state.worldEffect = false;
                return true;
            }

            // Smoke/sand can redraw a static VB/IB span many times without a
            // single game write. Copy caches already pin those exact revisions;
            // reuse only the depth classifier, NEVER per-draw stereo/RT state.
            // A changed base projection or viewport depth mapping forces a
            // fresh classification, even when the vertex bytes are unchanged.
            const bool indexed = usedMask != nullptr;
            const bool canMemoize = haveBaseProjection && signatureCache &&
                vertexCopy && vertexCopy->entry &&
                (!indexed || (indexCopy && indexCopy->entry));
            const auto sameCopy = [](const R30ShadowCopyCache& a,
                const R30ShadowCopyCache& b) noexcept {
                return a.entry == b.entry && a.revision == b.revision &&
                    a.offset == b.offset && a.size == b.size;
            };
            const bool memoHit = canMemoize && signatureCache->valid &&
                signatureCache->indexed == indexed &&
                signatureCache->vertexCount == vertexCount &&
                signatureCache->stride == stride &&
                signatureCache->minZ == state.viewport.MinZ &&
                signatureCache->maxZ == state.viewport.MaxZ &&
                sameCopy(signatureCache->vertex, *vertexCopy) &&
                (!indexed || sameCopy(signatureCache->index, *indexCopy)) &&
                std::memcmp(&signatureCache->projection, &baseProjection,
                    sizeof(baseProjection)) == 0;
            if (memoHit)
            {
                state.rhwDepthEvidence = signatureCache->projectedDepth;
            }
            else
            {
                state.rhwDepthEvidence = haveBaseProjection &&
                    R30XyzrhwHasProjectedDepthSignature(
                        source, vertexCount, stride, state,
                        baseProjection, usedMask, touched);
                if (canMemoize)
                {
                    signatureCache->valid = false;
                    signatureCache->vertex = *vertexCopy;
                    signatureCache->index = indexed
                        ? *indexCopy : R30ShadowCopyCache{};
                    signatureCache->indexed = indexed;
                    signatureCache->vertexCount = vertexCount;
                    signatureCache->stride = stride;
                    signatureCache->minZ = state.viewport.MinZ;
                    signatureCache->maxZ = state.viewport.MaxZ;
                    signatureCache->projection = baseProjection;
                    signatureCache->projectedDepth = state.rhwDepthEvidence;
                    signatureCache->valid = true;
                }
            }

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
                OutRunVR::Core::EffectiveStereoWorldScale(
                    Settings::VRWorldScale, Settings::VRStereoDepth);
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
                R30RecordTelemetryCounter(R30XyzrhwRhwWorldPromotions);
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
            // Never treat wrapped primitive counts as a small valid draw.
            // Zero returns E_NOTIMPL to preserve the game's raw draw fallback.
            return OutRunVR::R30IndexedUpBounds::PrimitiveElements(
                static_cast<std::uint32_t>(type), primitiveCount);
        }

        // For unusual world projections with no authoritative per-eye inverse,
        // keep the established affine fallback but visit source XYZRHW ONCE
        // for both eyes. This avoids duplicate finite checks, viewport-to-NDC
        // math and sparse-mask traversal in dense smoke/sand effects.
        // Full eye reprojection and its bilateral rollback are not changed.
        bool R30TransformWorldAffineStereo(
            const void* source, UINT vertexCount, UINT stride,
            const R30XyzrhwState& state,
            OutRunVR::R30ScratchBytes::WriteOnlyByteScratch& left,
            OutRunVR::R30ScratchBytes::WriteOnlyByteScratch& right,
            const std::vector<std::uint8_t>* usedMask,
            UINT knownUsedCount,
            const std::vector<std::uint32_t>* touched) noexcept
        {
            if (!state.worldEffect || state.fullWorldReprojection ||
                !source || !vertexCount || stride < 4u * sizeof(float) ||
                (usedMask && usedMask->size() < vertexCount))
                return false;
            const std::size_t bytes =
                static_cast<std::size_t>(vertexCount) * stride;
            if (!bytes || bytes > 4u * 1024u * 1024u ||
                left.size() != bytes || right.size() != bytes)
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
            // Convert viewport/NDC to per-eye pixel-space affine coefficients
            // ONCE per draw. The rare affine-only world particle route used
            // to do two viewport conversions and two eye corrections per
            // selected vertex. Preserve the same RHW-only parallax guard.
            const float halfWidth = width * 0.5f;
            const float halfHeight = height * 0.5f;
            const float centerX = x0 + halfWidth;
            const float centerY = y0 + halfHeight;
            float affineScaleX[2]{};
            float affineScaleY[2]{};
            float affineBiasX[2]{};
            float affineBiasY[2]{};
            float affineRhwX[2]{};
            float affineRhwY[2]{};
            for (int eye = 0; eye < 2; ++eye)
            {
                affineScaleX[eye] = state.worldScaleX[eye];
                affineScaleY[eye] = state.worldScaleY[eye];
                affineBiasX[eye] =
                    (1.0f - affineScaleX[eye]) * centerX +
                    state.worldOffsetX[eye] * halfWidth;
                affineBiasY[eye] =
                    (1.0f - affineScaleY[eye]) * centerY -
                    state.worldOffsetY[eye] * halfHeight;
                affineRhwX[eye] = state.parallaxPerRhwX[eye] * halfWidth;
                affineRhwY[eye] = -state.parallaxPerRhwY[eye] * halfHeight;
                if (!std::isfinite(affineScaleX[eye]) ||
                    !std::isfinite(affineScaleY[eye]) ||
                    !std::isfinite(affineBiasX[eye]) ||
                    !std::isfinite(affineBiasY[eye]) ||
                    !std::isfinite(affineRhwX[eye]) ||
                    !std::isfinite(affineRhwY[eye]))
                    return false;
            }
            std::uint8_t* eyeData[2]{ left.data(), right.data() };
            const auto* sourceBytes = static_cast<const std::uint8_t*>(source);
            // The indexed producer owns a unique, mask-complete touched list.
            // For 12.5-25% sparse world smoke/sand, avoid scanning unused
            // vertex slots after the shared two-eye seed. Unknown/denser
            // producers keep the original full walk and mask filtering.
            const bool sparseAffineTouched = usedMask && touched &&
                knownUsedCount > 0u &&
                knownUsedCount == touched->size() &&
                knownUsedCount <= vertexCount / 4u;
            const UINT affineVisitCount = sparseAffineTouched
                ? knownUsedCount : vertexCount;
            for (UINT visit = 0; visit < affineVisitCount; ++visit)
            {
                const UINT i = sparseAffineTouched ? (*touched)[visit] : visit;
                if (i >= vertexCount ||
                    (sparseAffineTouched && !(*usedMask)[i]))
                    return false;
                if (usedMask && !(*usedMask)[i])
                    continue;
                const std::size_t offset = static_cast<std::size_t>(i) * stride;
                const auto* p =
                    reinterpret_cast<const float*>(sourceBytes + offset);
                const float x = p[0];
                const float y = p[1];
                const float z = p[2];
                const float rhw = p[3];
                if (!std::isfinite(x) || !std::isfinite(y) ||
                    !std::isfinite(z) || !std::isfinite(rhw))
                    return false;
                const bool parallax = rhw > 0.0f && rhw < 1000.0f;
                for (int eye = 0; eye < 2; ++eye)
                {
                    float transformedX =
                        affineScaleX[eye] * x + affineBiasX[eye];
                    float transformedY =
                        affineScaleY[eye] * y + affineBiasY[eye];
                    if (parallax)
                    {
                        transformedX += affineRhwX[eye] * rhw;
                        transformedY += affineRhwY[eye] * rhw;
                    }
                    if (!std::isfinite(transformedX) ||
                        !std::isfinite(transformedY))
                        return false;
                    auto* dst = reinterpret_cast<float*>(
                        eyeData[eye] + offset);
                    dst[0] = transformedX;
                    dst[1] = transformedY;
                    // Preserve game Z/RHW, packed colour and UV bytes.
                }
            }
            return true;
        }

        // Seed the two world-particle eyes in ONE referenced-span walk. Both
        // draws consume the same validated source indices, but eye reprojection
        // modifies different XYZRHW values after this copy. A rare bilateral
        // fallback can also reseed just its successful eye independently.

        // Indexed UP calls already own a unique, verified touched list.
        // On very sparse spans copy only referenced vertices rather than
        // walking up to the largest index looking for a run. This is never
        // used by the revision-cached VB/IB path or by unknown mask owners.
        bool R30SeedTouchedXyzrhwVertices(
            const std::uint8_t* source, UINT vertexCount, UINT stride,
            OutRunVR::R30ScratchBytes::WriteOnlyByteScratch& left,
            OutRunVR::R30ScratchBytes::WriteOnlyByteScratch* right,
            const std::vector<std::uint8_t>& usedMask,
            const std::vector<std::uint32_t>* touched,
            std::size_t selectedCount) noexcept
        {
            if (!touched || touched->size() != selectedCount ||
                selectedCount * 4u > vertexCount)
                return false;
            // Reject a corrupt/out-of-span producer list before any writes.
            // The UP builder guarantees uniqueness and 1:1 mask coverage.
            for (const std::uint32_t index : *touched)
                if (index >= vertexCount || !usedMask[index])
                    return false;
            for (const std::uint32_t index : *touched)
            {
                const std::size_t offset =
                    static_cast<std::size_t>(index) * stride;
                std::memcpy(left.data() + offset,
                    source + offset, stride);
                if (right)
                    std::memcpy(right->data() + offset,
                        source + offset, stride);
            }
            return true;
        }

        bool R30SeedWorldXyzrhwBuffers(
            const void* source, UINT vertexCount, UINT stride,
            OutRunVR::R30ScratchBytes::WriteOnlyByteScratch& left,
            OutRunVR::R30ScratchBytes::WriteOnlyByteScratch* right,
            const std::vector<std::uint8_t>* usedMask,
            UINT knownUsedCount = UINT_MAX,
            const std::vector<std::uint32_t>* touched = nullptr) noexcept
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
                // Indexed callers already counted distinct references while
                // building this mask. Avoid a second full VB-span pass
                // for sparse particle geometry; retain the original scan
                // for callers without an authoritative cardinality.
                const std::size_t selectedCount = knownUsedCount <= vertexCount
                    ? static_cast<std::size_t>(knownUsedCount)
                    : static_cast<std::size_t>(std::count_if(
                        usedMask->begin(), usedMask->begin() + vertexCount,
                        [](std::uint8_t used) noexcept { return used != 0; }));
                if (static_cast<std::size_t>(selectedCount) * 4u <= vertexCount)
                {
                    if (!R30SeedTouchedXyzrhwVertices(
                            src, vertexCount, stride, left, right,
                            *usedMask, touched, selectedCount))
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
            OutRunVR::R30ScratchBytes::WriteOnlyByteScratch& out,
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
                        R30RecordTelemetryCounter(R30XyzrhwDepthPreserveFallbacks);
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

                R30RecordTelemetryCounter(R30XyzrhwAtomicFallbacks);
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

            // The generic XYZRHW fallback is used after a rejected fused
            // stereo draw (e.g. a device reset or unsupported vertex batch).
            // Keep ESC/pause vertical placement identical to the paired-eye
            // fast path and the HUD vertex-shader path; only the original
            // paused game's generic ScreenOverlay2D may supply a nonzero
            // fraction. Do not move world particles, game HUD or external F11.
            // Calculate once per draw rather than once per HUD vertex.
            const float pauseNdcOffset =
                state.worldEffect ? 0.0f :
                2.0f * R30PauseMenuVerticalFraction();
            const auto pauseVertical = state.worldEffect
                ? OutRunVrPauseEye::VerticalAffine{}
                : R30PauseMenuVerticalAffine(state.stereo);
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
                    correctedY =
                        hudScaleY * pauseVertical.scale[eye] * ndcY +
                        pauseVertical.offset[eye] - pauseNdcOffset;
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

        // R30 high-frequency world smoke/sand path: the original game-space
        // unprojection is identical for both eyes. Reconstruct it ONCE per
        // referenced vertex and apply the two already-verified eye tails.
        // Fall back to the existing independent-eye path for nonstandard
        // projections, a rejected vertex or an empty index selection.
        bool R30TryFusedWorldXyzrhwProjection(
            const void* source, UINT vertexCount, UINT stride,
            const R30XyzrhwState& state,
            OutRunVR::R30ScratchBytes::WriteOnlyByteScratch& left,
            OutRunVR::R30ScratchBytes::WriteOnlyByteScratch& right,
            const std::vector<std::uint8_t>* usedMask,
            UINT knownUsedCount,
            const std::vector<std::uint32_t>* touched) noexcept
        {
            if (!state.worldEffect || !state.fullWorldReprojection)
                return false;
            const D3DMATRIX& bp = state.baseProjection;
            const float det = bp._11 * bp._22 - bp._21 * bp._12;
            if (std::fabs(bp._14) > 1.0e-5f ||
                std::fabs(bp._24) > 1.0e-5f ||
                std::fabs(bp._34) <= 1.0e-5f ||
                !std::isfinite(det) || std::fabs(det) <= 1.0e-6f)
                return false;

            const float x0 = static_cast<float>(state.viewport.X);
            const float y0 = static_cast<float>(state.viewport.Y);
            const float width = static_cast<float>(state.viewport.Width);
            const float height = static_cast<float>(state.viewport.Height);
            const float minZ = state.viewport.MinZ;
            const float depthSpan = state.viewport.MaxZ - minZ;
            if (width <= 0.0f || height <= 0.0f ||
                !std::isfinite(depthSpan) || depthSpan <= 1.0e-6f)
                return false;
            const float ndcScaleX = 2.0f / width;
            const float ndcScaleY = 2.0f / height;
            // Do not multiply by 0.5f for every eye and vertex.
            const float halfWidth = width * 0.5f;
            const float halfHeight = height * 0.5f;
            const float inv34 = 1.0f / bp._34;
            const float invDet = 1.0f / det;
            // Every restored game-view position has W=1. Hoist both eye-tail
            // translation rows outside the smoke/sand vertex loop; per eye
            // this removes four constant multiplies per referenced vertex.
            float eyeTailOrigin[2][4]{};
            for (int eye = 0; eye < 2; ++eye)
                for (int col = 0; col < 4; ++col)
                    eyeTailOrigin[eye][col] = state.eyeTail[eye].m[3][col];
            const auto* bytes = static_cast<const std::uint8_t*>(source);
            UINT modifiedVertexEnd = 0;
            UINT referenced = 0;
            std::uint64_t depthPreserves = 0;
            bool allValid = true;
            // Indexed UP and revision-fenced VB decoders already produce an
            // ordered, unique list of exactly the selected mask bits. On
            // sparse smoke/sand batches, skip the potentially huge untouched
            // min..max vertex span in the fused two-eye projection itself.
            // Moderate 12.5-25% sparse indexed sources now share the same
            // touched-list cutoff as their dual-eye seed; dense/untrusted
            // sources retain the original full walk.
            const bool sparseTouched = usedMask && touched &&
                knownUsedCount > 0u && knownUsedCount == touched->size() &&
                knownUsedCount <= vertexCount / 4u;
            const UINT visitCount = sparseTouched ? knownUsedCount : vertexCount;
            for (UINT visit = 0; visit < visitCount; ++visit)
            {
                const UINT i = sparseTouched ? (*touched)[visit] : visit;
                if (i >= vertexCount ||
                    (sparseTouched && !(*usedMask)[i]))
                {
                    allValid = false;
                    break;
                }
                if (usedMask && !(*usedMask)[i])
                    continue;
                const std::size_t offset = static_cast<std::size_t>(i) * stride;
                const auto* src = reinterpret_cast<const float*>(bytes + offset);
                const float x = src[0];
                const float y = src[1];
                const float z = src[2];
                const float rhw = src[3];
                if (!std::isfinite(x) || !std::isfinite(y) ||
                    !std::isfinite(z) || !std::isfinite(rhw) ||
                    rhw <= 1.0e-6f || rhw >= 1000.0f)
                {
                    allValid = false;
                    break;
                }

                const float ndcX = (x - x0) * ndcScaleX - 1.0f;
                const float ndcY = 1.0f - (y - y0) * ndcScaleY;
                const float clipW = 1.0f / rhw;
                const float clipX = ndcX * clipW;
                const float clipY = ndcY * clipW;
                const float viewZ = (clipW - bp._44) * inv34;
                const float rhsX = clipX - viewZ * bp._31 - bp._41;
                const float rhsY = clipY - viewZ * bp._32 - bp._42;
                const float viewX =
                    (rhsX * bp._22 - bp._21 * rhsY) * invDet;
                const float viewY =
                    (bp._11 * rhsY - rhsX * bp._12) * invDet;
                if (!std::isfinite(viewX) || !std::isfinite(viewY) ||
                    !std::isfinite(viewZ) || !std::isfinite(rhsX) ||
                    !std::isfinite(rhsY))
                {
                    allValid = false;
                    break;
                }
                const float restoredView[4]{viewX, viewY, viewZ, 1.0f};
                float projected[2][4]{};
                std::uint32_t depthPreservesThisVertex = 0;
                for (int eye = 0; eye < 2; ++eye)
                {
                    float clipEye[4]{};
                    for (int col = 0; col < 4; ++col)
                    {
                        for (int row = 0; row < 3; ++row)
                            clipEye[col] += restoredView[row] *
                                state.eyeTail[eye].m[row][col];
                        clipEye[col] += eyeTailOrigin[eye][col];
                    }
                    if (!std::isfinite(clipEye[0]) ||
                        !std::isfinite(clipEye[1]) ||
                        !std::isfinite(clipEye[2]) ||
                        !std::isfinite(clipEye[3]) ||
                        clipEye[3] <= 1.0e-6f)
                    {
                        allValid = false;
                        break;
                    }
                    const float invEyeW = 1.0f / clipEye[3];
                    const float fullX = clipEye[0] * invEyeW;
                    const float fullY = clipEye[1] * invEyeW;
                    const float fullZ = clipEye[2] * invEyeW;
                    if (!std::isfinite(fullX) || !std::isfinite(fullY) ||
                        !std::isfinite(fullZ))
                    {
                        allValid = false;
                        break;
                    }
                    projected[eye][0] = x0 + (fullX + 1.0f) * halfWidth;
                    projected[eye][1] = y0 + (1.0f - fullY) * halfHeight;
                    projected[eye][2] = z;
                    if (fullZ >= 0.0f && fullZ <= 1.0f)
                        projected[eye][2] = minZ + fullZ * depthSpan;
                    else
                        ++depthPreservesThisVertex;
                    projected[eye][3] = invEyeW;
                    if (!std::isfinite(projected[eye][0]) ||
                        !std::isfinite(projected[eye][1]) ||
                        !std::isfinite(projected[eye][2]))
                    {
                        allValid = false;
                        break;
                    }
                }
                if (!allValid)
                    break;

                std::memcpy(left.data() + offset, projected[0],
                    4u * sizeof(float));
                std::memcpy(right.data() + offset, projected[1],
                    4u * sizeof(float));
                depthPreserves += depthPreservesThisVertex;
                modifiedVertexEnd = i + 1u;
                ++referenced;
            }

            if (allValid && referenced != 0)
            {
                R30XyzrhwDepthPreserveFallbacks += depthPreserves;
                return true;
            }
            // A partial fast candidate must be fully undone before the
            // original per-eye inverse-projection/affine fallback runs. Only
            // XYZRHW headers were written; UV/color and sparse holes remain.
            // Sparse indices arrive in arbitrary draw order: a last-visited
            // index is NOT the highest mutated index, so walk that same list
            // rather than using modifiedVertexEnd as a rollback boundary.
            if (sparseTouched)
            {
                for (const std::uint32_t i : *touched)
                {
                    if (i >= vertexCount || !(*usedMask)[i])
                        break;
                    const std::size_t offset =
                        static_cast<std::size_t>(i) * stride;
                    std::memcpy(left.data() + offset, bytes + offset,
                        4u * sizeof(float));
                    std::memcpy(right.data() + offset, bytes + offset,
                        4u * sizeof(float));
                }
            }
            else
            {
                for (UINT i = 0; i < modifiedVertexEnd; ++i)
                {
                    if (usedMask && !(*usedMask)[i])
                        continue;
                    const std::size_t offset =
                        static_cast<std::size_t>(i) * stride;
                    std::memcpy(left.data() + offset, bytes + offset,
                        4u * sizeof(float));
                    std::memcpy(right.data() + offset, bytes + offset,
                        4u * sizeof(float));
                }
            }
            return false;
        }

            // Per-vehicle Calc3D2D quad: preserve original Z/RHW, UV,
        // alpha, animation offsets and sprite ordering, moving only XY
        // by its own view-space anchor's exact two-eye delta.
    bool R30TransformProjectedRankXyzrhwStereo(
        const void* source, UINT vertexCount, UINT stride,
        const R30XyzrhwState& state,
        OutRunVR::R30ScratchBytes::WriteOnlyByteScratch& left,
        OutRunVR::R30ScratchBytes::WriteOnlyByteScratch& right,
        const std::vector<std::uint8_t>* usedMask) noexcept
        {
            if (!source || !vertexCount || stride < 4u * sizeof(float) ||
                (usedMask && usedMask->size() < vertexCount))
                return false;
            const std::size_t bytes =
                static_cast<std::size_t>(vertexCount) * stride;
            if (!bytes || bytes > 4u * 1024u * 1024u)
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
            std::memcpy(left.data(), source, bytes);
            std::memcpy(right.data(), source, bytes);
            const auto& vp = state.viewport;
            const float requestedScale = Settings::VRHudScale.get();
            if (!std::isfinite(requestedScale))
                return false;
            const float scale = std::clamp(
                requestedScale, 0.30f, 1.20f);
            for (UINT i = 0; i < vertexCount; ++i)
            {
                if (usedMask && !(*usedMask)[i])
                    continue;
                const auto off = static_cast<std::size_t>(i) * stride;
                const auto* src = reinterpret_cast<const float*>(
                    static_cast<const std::uint8_t*>(source) + off);
                if (!std::isfinite(src[2]) || !std::isfinite(src[3]))
                    return false;
                for (int eye = 0; eye < 2; ++eye)
                {
                    float x = 0.0f, y = 0.0f;
                    if (!OutRunVR::RankMarker::RemapScreenPoint(
                            src[0], src[1],
                            static_cast<float>(vp.X),
                            static_cast<float>(vp.Y),
                            static_cast<float>(vp.Width),
                            static_cast<float>(vp.Height),
                            scale, state.projectedRank, eye, x, y))
                        return false;
                    auto* dst = reinterpret_cast<float*>(
                        (eye == 0 ? left.data() : right.data()) + off);
                    dst[0] = x;
                    dst[1] = y;
                }
            }
            return true;
        }


        bool R30TransformXyzrhwStereo(
            const void* source, UINT vertexCount, UINT stride,
            const R30XyzrhwState& state,
            OutRunVR::R30ScratchBytes::WriteOnlyByteScratch& left,
            OutRunVR::R30ScratchBytes::WriteOnlyByteScratch& right,
            const std::vector<std::uint8_t>* usedMask = nullptr,
            UINT knownUsedCount = UINT_MAX,
            const std::vector<std::uint32_t>* touched = nullptr) noexcept
        {
            if (state.projectedWorldMarker)
                return R30TransformProjectedRankXyzrhwStereo(
                    source, vertexCount, stride, state,
                    left, right, usedMask);

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
                    const std::size_t selectedCount = knownUsedCount <= vertexCount
                        ? static_cast<std::size_t>(knownUsedCount)
                        : static_cast<std::size_t>(std::count_if(
                            usedMask->begin(), usedMask->begin() + vertexCount,
                            [](std::uint8_t selected) noexcept {
                                return selected != 0;
                            }));
                    if (static_cast<std::size_t>(selectedCount) * 4u <= vertexCount)
                    {
                        const auto* srcBytes =
                            static_cast<const std::uint8_t*>(source);
                        if (!R30SeedTouchedXyzrhwVertices(
                                srcBytes, vertexCount, stride, left, &right,
                                *usedMask, touched, selectedCount))
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
                                    srcBytes + offset, runBytes);
                                std::memcpy(right.data() + offset,
                                    srcBytes + offset, runBytes);
                            }
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
                // Compose viewport, HUD containment and asymmetric eye FOV
                // once per draw. This skips repeated NDC conversions and an
                // eye-conditional branch for every indexed/UP HUD vertex.
                // Z/RHW, UV, color and sparse source coverage stay unchanged.
                const R30HudEdgeAnchor exactHudAnchor =
                    R30GetExactHudEdgeAnchor(source, vertexCount, stride,
                        x0, y0, width, height, usedMask, touched, knownUsedCount);
                // Per-draw only: keep both eyes' sprite aspect and FOV bias
                // paired, without touching a shared/cached gameplay scale.
                float peripheralBoost =
                    R30ExactPeripheralHudBoost(exactHudAnchor);
                peripheralBoost = R30AdaptivePeripheralHudBoost(
                    exactHudAnchor, x0, y0, width, height,
                    hudScaleX, hudScaleY, state.eyeScale, state.eyeOffset,
                    peripheralBoost);
                hudScaleX *= peripheralBoost;
                hudScaleY *= peripheralBoost;
                const float halfWidth = width * 0.5f;
                const float halfHeight = height * 0.5f;
                const float eyeScaleX[2]{
                    hudScaleX * state.eyeScale[0],
                    hudScaleX * state.eyeScale[1]
                };
                const float eyeBiasX[2]{
                    (1.0f - eyeScaleX[0]) * (x0 + halfWidth) +
                        state.eyeOffset[0] * halfWidth,
                    (1.0f - eyeScaleX[1]) * (x0 + halfWidth) +
                        state.eyeOffset[1] * halfWidth
                };
                const auto pauseVertical =
                    R30PauseMenuVerticalAffine(state.stereo);
                const float pauseShiftY =
                    height * R30PauseMenuVerticalFraction();
                const float hudBiasY =
                    (1.0f - hudScaleY) * (y0 + halfHeight) + pauseShiftY;
                const float eyeScaleY[2]{
                    hudScaleY * pauseVertical.scale[0],
                    hudScaleY * pauseVertical.scale[1]
                };
                const float eyeBiasY[2]{
                    (1.0f - eyeScaleY[0]) * (y0 + halfHeight) -
                        pauseVertical.offset[0] * halfHeight + pauseShiftY,
                    (1.0f - eyeScaleY[1]) * (y0 + halfHeight) -
                        pauseVertical.offset[1] * halfHeight + pauseShiftY
                };
                // Bias computed once per draw. A zero (default-off) anchor
                // reproduces the existing centre-convergent mapping.
                float edgeLeftBias =
                    (1.0f - eyeScaleX[0]) * halfWidth * exactHudAnchor.x;
                float edgeRightBias =
                    (1.0f - eyeScaleX[1]) * halfWidth * exactHudAnchor.x;
                float edgeYBias =
                    -(1.0f - hudScaleY) * halfHeight * exactHudAnchor.y;
                R30ConstrainHudEdgeToVisibleBounds(
                    exactHudAnchor, x0, y0, width, height,
                    eyeScaleX, eyeBiasX, hudScaleY, hudBiasY,
                    eyeScaleY, eyeBiasY,
                    edgeLeftBias, edgeRightBias, edgeYBias);
                // Indexed-UP and revision-fenced VB/IB builders supply a
                // unique, mask-complete touched list. On very sparse HUD
                // spans, visit those references rather than walking every
                // unused vertex between min and max indices. Unindexed,
                // dense and unknown-mask draws keep the original full walk.
                const bool sparseHudTouched = usedMask && touched &&
                    knownUsedCount > 0u &&
                    knownUsedCount == touched->size() &&
                    knownUsedCount <= vertexCount / 4u;
                const UINT hudVisitCount =
                    sparseHudTouched ? knownUsedCount : vertexCount;
                for (UINT visit = 0; visit < hudVisitCount; ++visit)
                {
                    const UINT i = sparseHudTouched ? (*touched)[visit] : visit;
                    // Never dereference an out-of-span list index. The mask
                    // remains the authority even for a supposedly valid list.
                    if (i >= vertexCount ||
                        (sparseHudTouched && !(*usedMask)[i]))
                        return false;
                    if (usedMask && !(*usedMask)[i])
                        continue;
                    const std::size_t offset =
                        static_cast<std::size_t>(i) * stride;
                    const auto* src = reinterpret_cast<const float*>(
                        static_cast<const std::uint8_t*>(source) + offset);
                    if (!std::isfinite(src[0]) || !std::isfinite(src[1]) ||
                        !std::isfinite(src[2]) || !std::isfinite(src[3]))
                        return false;
                    const float transformedLeftY =
                        eyeScaleY[0] * src[1] + eyeBiasY[0] + edgeYBias;
                    const float transformedRightY =
                        eyeScaleY[1] * src[1] + eyeBiasY[1] + edgeYBias;
                    const float transformedLeftX =
                        eyeScaleX[0] * src[0] + eyeBiasX[0] + edgeLeftBias;
                    const float transformedRightX =
                        eyeScaleX[1] * src[0] + eyeBiasX[1] + edgeRightBias;
                    if (!std::isfinite(transformedLeftY) ||
                        !std::isfinite(transformedRightY) ||
                        !std::isfinite(transformedLeftX) ||
                        !std::isfinite(transformedRightX))
                        return false;
                    auto* leftDst =
                        reinterpret_cast<float*>(left.data() + offset);
                    auto* rightDst =
                        reinterpret_cast<float*>(right.data() + offset);
                    leftDst[0] = transformedLeftX;
                    leftDst[1] = transformedLeftY;
                    rightDst[0] = transformedRightX;
                    rightDst[1] = transformedRightY;
                }
                return true;
            }

            // This is the high-frequency indexed smoke/sand/decal path:
            // one sparse-mask population count and one contiguous-run scan
            // seeds both eye scratch buffers before per-eye projection work.
            if (!R30SeedWorldXyzrhwBuffers(
                    source, vertexCount, stride, left, &right,
                    usedMask, knownUsedCount, touched))
                return false;

            // The conservative affine-only world route can share input math
            // between eyes; perspective worlds keep their full reprojection
            // and existing independent-eye safety fallback untouched.
            if (!state.fullWorldReprojection)
                return R30TransformWorldAffineStereo(
                    source, vertexCount, stride, state, left, right,
                    usedMask, knownUsedCount, touched);

            // Common perspective world draws need only one game-space
            // reconstruction pass. Unusual/rejected input still takes the
            // original independent-eye route and bilateral safety fallback.
            if (R30TryFusedWorldXyzrhwProjection(
                    source, vertexCount, stride, state, left, right,
                    usedMask, knownUsedCount, touched))
                return true;

            bool leftFull = false;
            bool rightFull = false;
            if (!R30TransformXyzrhwVertices(source, vertexCount, stride,
                    state, 0, left, usedMask, true, leftFull, true) ||
                !R30TransformXyzrhwVertices(source, vertexCount, stride,
                    state, 1, right, usedMask, true, rightFull, true))
                return false;

            if (leftFull != rightFull)
            {
                R30RecordTelemetryCounter(R30XyzrhwBilateralFallbacks);
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

        // Mirror R9's exact RT/viewport/WVP restore order while omitting only
        // the provably redundant null-depth setter. On any uncertain state,
        // callers use the original complete R29/R9 restoration unchanged.
        inline bool R30RestoreDepthlessRightPassState(
            IDirect3DDevice9* device, IDirect3DSurface9* savedRt,
            const D3DVIEWPORT9& savedViewport,
            const float* originalConstants, bool restoreWvp) noexcept
        {
            bool ok = true;
            if (savedRt && FAILED(R29OwnerCallOriginalSetRenderTarget(
                    device, 0u, savedRt)))
                ok = false;
            if (FAILED(device->SetViewport(&savedViewport)))
                ok = false;
            if (restoreWvp &&
                !R29OwnerSetWvpOneRegisterAtATime(device, originalConstants))
                ok = false;
            return ok;
        }

        template <typename LeftDraw, typename RightDraw>
        HRESULT R30ExecuteXyzrhwStereo(
            IDirect3DDevice9* device, const R30XyzrhwState& state,
            LeftDraw&& leftDraw, RightDraw&& rightDraw,
            const char* site)
        {
            // R26+HUD protected the lens centre from prematurely freezing
            // the pre-HUD SkyGlow source. The independent R84 renderer must
            // obey the same exact producer boundary rather than inferring UI
            // from alpha/depth or XYZRHW shape alone.
            if (!state.worldEffect &&
                OutRunVR::GameSemantic::IsSkyGlowPreHudBoundary(
                    OutRunVR::GameSemantic::EffectiveScope()))
                R30CaptureSkyGlowSceneBeforeHud(device);

            R29OwnerNoteStereoDrawWithoutMonoBackup();
            if (R29OwnerLeftDrawMayWriteDepth(device) ||
                R29OwnerLeftDrawMayWriteStencil(device))
                R29OwnerNoteMainDepthContentWrite();

            const HRESULT leftHr = leftDraw();
            if (FAILED(leftHr))
            {
                // The left draw was already submitted but did not complete.
                // There is no valid same-frame right eye to publish at Present,
                // even if the following fallback/recovery path is successful.
                R29OwnerMarkRightDrawFailed();
                R29OwnerInvalidateRightDepthStencilIfLeftMayWrite(device);
                R29OwnerReportStereoFailure(OutRunVR::StereoFailureLeftDrawFailed,
                    site, leftHr);
                R29OwnerArmMonoSafety();
                return leftHr;
            }

            // Capture after the left-eye draw; reuse one coherent R29 owner view.
            const auto frame = R29OwnerCaptureFrameSnapshot();
            IDirect3DSurface9* savedRt = R29OwnerBorrowTrackedRenderTarget();
            IDirect3DSurface9* savedDepth = frame.trackedDepthStencil;
            // R33's proven depthless guard also applies to this R30-owned
            // stereo draw: live setter/StateBlock coverage and a null tracked
            // depth attachment must both hold. Unknown state never bypasses.
            const bool depthlessPass = savedDepth == nullptr &&
                OutRunVR::State::StateBlockTracker::Reliable();
            HRESULT rightHr = D3D_OK;
            OutRunVR::StereoFailureReason rightFailure =
                OutRunVR::StereoFailureRightStateFailed;
            bool restoreOk = true;
            {
                R30ScopedInternalPass guard;
                rightHr = R29OwnerCallOriginalSetRenderTarget(
                    device, 0u, frame.rightEyeSurface);
                if (SUCCEEDED(rightHr) && !depthlessPass)
                    rightHr = R29OwnerCallOriginalSetDepthStencilSurface(
                        device, savedDepth ? frame.rightEyeDepth : nullptr);
                if (SUCCEEDED(rightHr))
                    rightHr = device->SetViewport(&state.viewport);
                if (SUCCEEDED(rightHr))
                {
                    rightFailure =
                        OutRunVR::StereoFailureRightDrawFailed;
                    rightHr = rightDraw();
                }
                restoreOk = depthlessPass
                    ? R30RestoreDepthlessRightPassState(
                        device, savedRt, state.viewport, nullptr, false)
                    : R29OwnerRestoreRightPassState(
                        device, savedRt, savedDepth, state.viewport, nullptr, false);
            }

            // Never publish a completed stereo draw or its pose metadata
            // before BOTH physical eyes and the game render state are valid.
            if (OutRunVR::StereoCompletion::CanPublishStereoDraw(
                    SUCCEEDED(leftHr), SUCCEEDED(rightHr), restoreOk))
            {
                R29OwnerNoteStableTwoEyeDraw();
                if (state.worldEffect)
                {
                    R30RecordTelemetryCounter(R30XyzrhwWorldEffectDraws);
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
                    R30RecordTelemetryCounter(R30XyzrhwHudDraws);
                    if (!R30FirstXyzrhwHudLogged)
                    {
                        R30FirstXyzrhwHudLogged = true;
                        spdlog::info(
                            "VR R30.8 XYZRHW HUD: pre-transformed fixed-function HUD applies source-aspect/eye-FOV X compensation before SBS/DirectGPU projection; circular gauges preserve final HMD aspect ratio");
                    }
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
                // A restore failure poisons the CURRENT right-eye frame, not
                // only future stereo eligibility. Present/SkyGlow must never
                // publish a partially restored eye as binocularly complete.
                R29OwnerMarkRightDrawFailed();
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
                R30RecordTelemetryCounter(R30XyzrhwFallbacks);
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
                R30RecordTelemetryCounter(R30XyzrhwFallbacks);
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
                indexCount > OutRunVR::R30IndexedUpBounds::MaxIndices ||
                (indexFormat != D3DFMT_INDEX16 &&
                 indexFormat != D3DFMT_INDEX32))
                return E_NOTIMPL;

            // D3D9 supplies a legal [minVertexIndex, minVertexIndex+numVertices)
            // window for UP indices. R30 used to preserve that absolute base in
            // both eye scratch buffers, so a large non-zero minimum inflated the
            // transformed/uploaded vertex span even though the prefix could never
            // be referenced. Rebase only that declared window to zero. The common
            // min==0 path keeps the caller's index array without an extra copy.
            const std::uint64_t declaredEnd =
                static_cast<std::uint64_t>(minVertexIndex) + numVertices;
            if (numVertices == 0 || declaredEnd > 262144u)
                return E_NOTIMPL;
            const std::uint64_t firstVertexByte =
                static_cast<std::uint64_t>(minVertexIndex) * stride;
            if (firstVertexByte >
                static_cast<std::uint64_t>(
                    (std::numeric_limits<std::size_t>::max)()))
                return E_NOTIMPL;
            const auto* windowVertexData =
                static_cast<const std::uint8_t*>(vertexData) +
                static_cast<std::size_t>(firstVertexByte);
            const UINT vertexCount = numVertices;

            R30ScratchLease lease;
            if (!lease)
                return E_NOTIMPL;
            auto& scratch = *lease.buffers;
            // Reuse a UP-only local mask. Clearing only last draw's referenced
            // vertices avoids zero-filling the whole declared window.
            scratch.indexDecode.valid = false;
            for (const std::uint32_t previous : scratch.upTouched)
                scratch.upUsed[previous] = 0;
            scratch.upTouched.clear();
            try
            {
                if (scratch.upUsed.size() < vertexCount)
                    scratch.upUsed.resize(vertexCount, 0);
            }
            catch (...)
            {
                return E_NOTIMPL;
            }

            UINT knownUsedCount = 0;
            const auto collectUsed = [&](const auto* typedIndices) {
                for (UINT i = 0; i < indexCount; ++i)
                {
                    const std::uint32_t raw = typedIndices[i];
                    if (raw < minVertexIndex || raw >= declaredEnd)
                        return false;
                    const std::uint32_t local = raw - minVertexIndex;
                    if (local >= vertexCount)
                        return false;
                    if (!scratch.upUsed[local])
                    {
                        // Append first: failed allocation cannot strand a dirty
                        // mask bit outside the next draw's sparse clear list.
                        try
                        {
                            scratch.upTouched.push_back(local);
                        }
                        catch (...)
                        {
                            return false;
                        }
                        scratch.upUsed[local] = 1;
                        ++knownUsedCount;
                    }
                }
                return true;
            };
            const bool validIndices = indexFormat == D3DFMT_INDEX16
                ? collectUsed(static_cast<const std::uint16_t*>(indexData))
                : collectUsed(static_cast<const std::uint32_t*>(indexData));
            if (!validIndices)
                return E_NOTIMPL;

            const void* drawIndexData = indexData;
            if (minVertexIndex != 0)
            {
                // Only the non-zero-base path pays this second compact index
                // walk. It removes minVertexIndex vertices from each eye's
                // scratch/upload span, which dominates the extra index copy for
                // the particle/decal batches this path targets.
                try
                {
                    if (indexFormat == D3DFMT_INDEX16)
                    {
                        scratch.indices16.resize(indexCount);
                        const auto* source =
                            static_cast<const std::uint16_t*>(indexData);
                        for (UINT i = 0; i < indexCount; ++i)
                            scratch.indices16[i] =
                                static_cast<std::uint16_t>(
                                    source[i] - minVertexIndex);
                        drawIndexData = scratch.indices16.data();
                    }
                    else
                    {
                        scratch.indices32.resize(indexCount);
                        const auto* source =
                            static_cast<const std::uint32_t*>(indexData);
                        for (UINT i = 0; i < indexCount; ++i)
                            scratch.indices32[i] =
                                source[i] - minVertexIndex;
                        drawIndexData = scratch.indices32.data();
                    }
                }
                catch (...)
                {
                    return E_NOTIMPL;
                }
            }

            if (!R30ConfigureXyzrhwWorldEffect(
                    device, windowVertexData, vertexCount, stride, state,
                    &scratch.upUsed, nullptr, nullptr, nullptr,
                    &scratch.upTouched))
            {
                R30RecordTelemetryCounter(R30XyzrhwFallbacks);
                return E_NOTIMPL;
            }

            if (!R30TransformXyzrhwStereo(
                    windowVertexData, vertexCount, stride, state,
                    scratch.left, scratch.right,
                    &scratch.upUsed, knownUsedCount, &scratch.upTouched))
            {
                R30RecordTelemetryCounter(R30XyzrhwFallbacks);
                return E_NOTIMPL;
            }

            auto leftDraw = [&]() {
                return R29OwnerCallRawDrawIndexedPrimitiveUP(
                    device, type, 0u, numVertices,
                    primitiveCount, drawIndexData, indexFormat,
                    scratch.left.data(), stride);
            };
            auto rightDraw = [&]() {
                return R29OwnerCallRawDrawIndexedPrimitiveUP(
                    device, type, 0u, numVertices,
                    primitiveCount, drawIndexData, indexFormat,
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
                R30RecordTelemetryCounter(R30XyzrhwFallbacks);
                return E_NOTIMPL;
            }

            if (!R30ConfigureXyzrhwWorldEffect(
                    device, scratch.source.data(), vertexCount,
                    stride, state, nullptr, &scratch.vertexCopy,
                    nullptr, &scratch.depthSignature) ||
                !R30TransformXyzrhwStereo(
                    scratch.source.data(), vertexCount, stride, state,
                    scratch.left, scratch.right))
            {
                vb->Release();
                R30RecordTelemetryCounter(R30XyzrhwFallbacks);
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
                R30RecordTelemetryCounter(R30XyzrhwFallbacks);
                return E_NOTIMPL;
            }

            // The already-shadowed index source needs no intermediate
            // physical-index vector. The signed base offset is monotonic:
            // proving both 64-bit endpoints validates every physical index.
            const bool index16 = ibShadow->indexFormat == D3DFMT_INDEX16;
            const auto* raw16 = index16
                ? reinterpret_cast<const std::uint16_t*>(
                    scratch.indexSource.data()) : nullptr;
            const auto* raw32 = !index16
                ? reinterpret_cast<const std::uint32_t*>(
                    scratch.indexSource.data()) : nullptr;
            const auto& decoded = scratch.indexDecode;
            // R30CopyIndexShadow is generation-validated under the IB lock.
            // Its exact revision and copied byte span fence this decoded
            // index cache, including DISCARD, Release and address reuse.
            // A different VB, base vertex or stream offset may reuse the
            // local indices, but physical bounds are rechecked below.
            const bool cachedDecode =
                decoded.valid && decoded.entry == ibShadow &&
                decoded.revision == scratch.indexCopy.revision &&
                decoded.offset == static_cast<UINT>(firstIndexByte) &&
                decoded.size == static_cast<UINT>(indexBytes) &&
                decoded.format == ibShadow->indexFormat &&
                scratch.used.size() == decoded.vertexCount &&
                scratch.vbTouched.size() == decoded.knownUsedCount &&
                (index16 ? scratch.indices16.size() == indexCount
                         : scratch.indices32.size() == indexCount);
            std::uint32_t minRaw = cachedDecode ? decoded.minRaw : UINT_MAX;
            std::uint32_t maxRaw = cachedDecode ? decoded.maxRaw : 0;
            if (!cachedDecode)
            {
                for (UINT i = 0; i < indexCount; ++i)
                {
                    const std::uint32_t raw = index16 ? raw16[i] : raw32[i];
                    minRaw = (std::min)(minRaw, raw);
                    maxRaw = (std::max)(maxRaw, raw);
                }
            }
            const std::int64_t minPhysical =
                static_cast<std::int64_t>(baseVertexIndex) + minRaw;
            const std::int64_t maxPhysical =
                static_cast<std::int64_t>(baseVertexIndex) + maxRaw;
            if (minPhysical < 0 || maxPhysical > UINT_MAX)
            {
                ib->Release();
                vb->Release();
                return E_NOTIMPL;
            }

            const std::uint64_t vertexCount64 =
                static_cast<std::uint64_t>(maxRaw) - minRaw + 1u;
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
                R30RecordTelemetryCounter(R30XyzrhwFallbacks);
                return E_NOTIMPL;
            }

            // The first index pass has already validated physical addresses
            // and discovered the contiguous source-vertex span. On unchanged
            // IB draws both expensive scans, memset and rebase are skipped.
            // A miss invalidates the old decoder *before* mutating its mask.
            UINT knownUsedCount = cachedDecode ? decoded.knownUsedCount : 0;
            if (!cachedDecode)
            {
                scratch.indexDecode.valid = false;
                // A new IB span/revision/local vertex range retires the
                // previous sorted first-512 classifier hint before touching
                // any mask bits. Wrap is fail-closed rather than matching an
                // ancient generation after a theoretically long session.
                if (++scratch.vbTouchGeneration == 0)
                {
                    scratch.vbTouchGeneration = 1;
                    scratch.vbDepthSortedGeneration = 0;
                }
                // Only prior referenced mask bits can be nonzero. Clear them
                // before resizing: shrink/grow must never revive stale bits.
                // A failed partial decode still lists every marked index.
                for (const std::uint32_t previous : scratch.vbTouched)
                {
                    if (previous < scratch.used.size())
                        scratch.used[previous] = 0;
                }
                scratch.vbTouched.clear();
                try
                {
                    scratch.used.resize(vertexCount, 0);
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

                for (UINT i = 0; i < indexCount; ++i)
                {
                    // The signed base cancels when converting to the local
                    // vertex span, so subtract the minimum raw index directly.
                    const std::uint32_t raw = index16 ? raw16[i] : raw32[i];
                    const std::uint64_t local =
                        static_cast<std::uint64_t>(raw) - minRaw;
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
                    if (!scratch.used[static_cast<std::size_t>(local)])
                    {
                        // Publish the mask bit only after a successful append.
                        // A failed allocation returns with the decode cache invalid,
                        // so no incomplete referenced-vertex list can be replayed.
                        try
                        {
                            scratch.vbTouched.push_back(
                                static_cast<std::uint32_t>(local));
                        }
                        catch (...)
                        {
                            ib->Release();
                            vb->Release();
                            return E_NOTIMPL;
                        }
                        ++knownUsedCount;
                        scratch.used[static_cast<std::size_t>(local)] = 1;
                    }
                    if (index16)
                        scratch.indices16[i] = static_cast<std::uint16_t>(local);
                    else
                        scratch.indices32[i] = static_cast<std::uint32_t>(local);
                }
                auto& next = scratch.indexDecode;
                next.entry = ibShadow;
                next.revision = scratch.indexCopy.revision;
                next.offset = static_cast<UINT>(firstIndexByte);
                next.size = static_cast<UINT>(indexBytes);
                next.format = ibShadow->indexFormat;
                next.minRaw = minRaw;
                next.maxRaw = maxRaw;
                next.vertexCount = vertexCount;
                next.knownUsedCount = knownUsedCount;
                next.valid = true;
            }
            const void* rebased = index16
                ? static_cast<const void*>(scratch.indices16.data())
                : static_cast<const void*>(scratch.indices32.data());

            if (!R30ConfigureXyzrhwWorldEffect(
                    device, scratch.source.data(), vertexCount,
                    stride, state, &scratch.used, &scratch.vertexCopy,
                    &scratch.indexCopy, &scratch.depthSignature,
                    &scratch.vbTouched) ||
                !R30TransformXyzrhwStereo(
                    scratch.source.data(), vertexCount, stride, state,
                    scratch.left, scratch.right,
                    &scratch.used, knownUsedCount, &scratch.vbTouched))
            {
                ib->Release();
                vb->Release();
                R30RecordTelemetryCounter(R30XyzrhwFallbacks);
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
            const D3DMATRIX& headInverse,
            bool directProjected2D) noexcept
        {
            auto& cache = R30FlatEffectGeometry;
            const float worldScale =
                Settings::VRWorldScale * Settings::VRStereoDepth;
            if (cache.valid && cache.poseSequence == stereo.poseSequence &&
                cache.directProjected2D == directProjected2D &&
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
            next.directProjected2D = directProjected2D;
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

            // The direct 0xCABE rings are already CPU-projected by
            // Calc3D2D using the game camera. Reapplying the full HMD
            // orientation would rotate the same screen-space source twice.
            // Retain only each eye's translation relative to the centre.
            const float eyeCentre[3]{
                0.5f * (stereo.eyeOffset[0][0] + stereo.eyeOffset[1][0]),
                0.5f * (stereo.eyeOffset[0][1] + stereo.eyeOffset[1][1]),
                0.5f * (stereo.eyeOffset[0][2] + stereo.eyeOffset[1][2])
            };
            const float identityOrientation[4]{0.0f, 0.0f, 0.0f, 1.0f};
            for (int eye = 0; eye < 2; ++eye)
            {
                const float relativeEye[3]{
                    stereo.eyeOffset[eye][0] - eyeCentre[0],
                    stereo.eyeOffset[eye][1] - eyeCentre[1],
                    stereo.eyeOffset[eye][2] - eyeCentre[2]
                };
                const D3DMATRIX eyePose =
                    R29OwnerMatrixFromQuaternionTranslation(
                        directProjected2D ? identityOrientation
                                          : stereo.eyeOrientation[eye],
                        directProjected2D ? relativeEye : stereo.eyeOffset[eye],
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

            if (screenKind == R30ScreenSpaceKind::ProjectedWorldMarker2D)
            {
                float baseRaw[16]{};
                if (!OutRunVRRenderer::GetRendererBaseProjection(baseRaw))
                    return false;
                D3DMATRIX baseProjection{};
                std::memcpy(&baseProjection, baseRaw, sizeof(baseProjection));
                OutRunVR::RankMarker::StereoNdcShift shift{};
                if (!R30BuildProjectedRankDelta(
                        stereo, baseProjection, shift))
                    return false;
                const float requestedScale = Settings::VRHudScale.get();
                if (!std::isfinite(requestedScale))
                    return false;
                const float markerScale =
                    std::clamp(requestedScale, 0.30f, 1.20f);
                for (int eye = 0; eye < 2; ++eye)
                {
                    D3DMATRIX clipShift = R29OwnerIdentityMatrix();
                    clipShift._11 = markerScale;
                    clipShift._22 = markerScale;
                    clipShift._41 = shift.deltaX[eye] +
                        (1.0f - markerScale) * shift.baseX;
                    clipShift._42 = shift.deltaY[eye] +
                        (1.0f - markerScale) * shift.baseY;
                    const D3DMATRIX corrected =
                        R29OwnerMultiplyMatrix(stockWvp, clipShift);
                    if (!R29OwnerMatrixFinite(corrected))
                        return false;
                    const D3DMATRIX t = R29OwnerTransposeMatrix(corrected);
                    std::memcpy(eyeConstants[eye], &t, sizeof(t));
                }
                return true;
            }

            const bool exactHud =
                OutRunVR::GameSemantic::CorroboratesHud(
                    OutRunVR::GameSemantic::EffectiveScope()) &&
                (screenKind == R30ScreenSpaceKind::Hud2D ||
                 screenKind == R30ScreenSpaceKind::FlatPerspectiveEffect);
            if (exactHud)
            {
                // R26 screen HUD is world-locked at a finite, recentered
                // view-plane depth. R84's clip-only Hud2D route followed
                // headset yaw and its live c64 could double-inject pose.
                float rawGameWvp[16]{};
                float baseRaw[16]{};
                float headRaw[16]{};
                std::uint32_t headPoseSequence = 0;
                if (!R30GetRecentOriginalHudWvp(rawGameWvp) ||
                    !OutRunVRRenderer::GetRendererBaseProjection(baseRaw) ||
                    !OutRunVRRenderer::GetLatchedHeadInverse(
                        headRaw, headPoseSequence) ||
                    headPoseSequence != stereo.poseSequence)
                    return false;

                D3DMATRIX rawUploadedT{}, baseProjection{}, headInverse{};
                std::memcpy(&rawUploadedT, rawGameWvp, sizeof(rawUploadedT));
                std::memcpy(&baseProjection, baseRaw, sizeof(baseProjection));
                std::memcpy(&headInverse, headRaw, sizeof(headInverse));
                const D3DMATRIX hudWvp =
                    R29OwnerTransposeMatrix(rawUploadedT);
                D3DMATRIX inverseBase{};
                if (!R29OwnerMatrixFinite(hudWvp) ||
                    !R29OwnerMatrixFinite(baseProjection) ||
                    !R29OwnerMatrixFinite(headInverse) ||
                    !R29OwnerInvertMatrix(baseProjection, inverseBase))
                    return false;

                // The original HMD-proven R26 HUD used a uniform requested
                // optical scale. Do not apply a second source/portrait
                // aspect compensation to text/gauges on this world plane.
                D3DMATRIX hudScale = R29OwnerIdentityMatrix();
                const float userScale = R30HudScaleValue();
                hudScale._11 = userScale;
                hudScale._22 = userScale;
                const D3DMATRIX scaledClip =
                    R29OwnerMultiplyMatrix(hudWvp, hudScale);
                constexpr float HudPlaneZ = -2.50f;
                const float planeW =
                    HudPlaneZ * baseProjection._34 + baseProjection._44;
                const float planeZ =
                    HudPlaneZ * baseProjection._33 + baseProjection._43;
                if (!std::isfinite(planeW) || !std::isfinite(planeZ) ||
                    std::fabs(planeW) <= 1.0e-4f)
                    return false;
                D3DMATRIX depthReset = R29OwnerIdentityMatrix();
                depthReset._33 = 0.0f;
                depthReset._43 = planeZ / planeW;
                const D3DMATRIX commonPlane =
                    R29OwnerMultiplyMatrix(
                        R29OwnerMultiplyMatrix(scaledClip, depthReset),
                        inverseBase);
                if (!R29OwnerMatrixFinite(commonPlane))
                    return false;

                const float centre[3]{
                    0.5f * (stereo.eyeOffset[0][0] + stereo.eyeOffset[1][0]),
                    0.5f * (stereo.eyeOffset[0][1] + stereo.eyeOffset[1][1]),
                    0.5f * (stereo.eyeOffset[0][2] + stereo.eyeOffset[1][2])
                };
                const float identity[4]{0.0f, 0.0f, 0.0f, 1.0f};
                for (int eye = 0; eye < 2; ++eye)
                {
                    const float relative[3]{
                        stereo.eyeOffset[eye][0] - centre[0],
                        stereo.eyeOffset[eye][1] - centre[1],
                        stereo.eyeOffset[eye][2] - centre[2]
                    };
                    const D3DMATRIX eyePose =
                        R29OwnerMatrixFromQuaternionTranslation(
                            identity, relative,
                            Settings::VRWorldScale *
                                Settings::VRStereoDepth);
                    const D3DMATRIX eyeInverse =
                        R29OwnerInverseRigid(eyePose);
                    const D3DMATRIX eyeProjection =
                        R29OwnerProjectionFromFov(
                            baseProjection, stereo.eyeFov[eye]);
                    const D3DMATRIX corrected =
                        R29OwnerMultiplyMatrix(
                            R29OwnerMultiplyMatrix(
                                R29OwnerMultiplyMatrix(
                                    commonPlane, headInverse),
                                eyeInverse),
                            eyeProjection);
                    if (!R29OwnerMatrixFinite(corrected))
                        return false;
                    const D3DMATRIX correctedT =
                        R29OwnerTransposeMatrix(corrected);
                    std::memcpy(eyeConstants[eye], &correctedT,
                        sizeof(correctedT));
                }
                return true;
            }

            if (screenKind == R30ScreenSpaceKind::ExactLensCentreWorld)
            {
                // Original GPU c64 was saved in `original` for exact state
                // restore. It is NOT source-owned game WVP and might already
                // be head-injected. Keep those values completely separate.
                float rawGameWvp[16]{};
                if (!R30HasExactLensCentreRawWvp(rawGameWvp))
                    return false;
                D3DMATRIX rawUploadedT{};
                std::memcpy(&rawUploadedT, rawGameWvp, sizeof(rawUploadedT));
                const D3DMATRIX stockRawWvp =
                    R29OwnerTransposeMatrix(rawUploadedT);
                float baseRaw[16]{};
                float headRaw[16]{};
                std::uint32_t headPoseSequence = 0;
                if (!R29OwnerMatrixFinite(stockRawWvp) ||
                    !OutRunVRRenderer::GetRendererBaseProjection(baseRaw) ||
                    !OutRunVRRenderer::GetLatchedHeadInverse(
                        headRaw, headPoseSequence) ||
                    headPoseSequence != stereo.poseSequence)
                    return false;
                D3DMATRIX baseProjection{}, headInverse{};
                std::memcpy(&baseProjection, baseRaw,
                    sizeof(baseProjection));
                std::memcpy(&headInverse, headRaw, sizeof(headInverse));
                D3DMATRIX inverseBaseProjection{};
                if (!R29OwnerMatrixFinite(baseProjection) ||
                    !R29OwnerMatrixFinite(headInverse) ||
                    !R29OwnerInvertMatrix(baseProjection,
                        inverseBaseProjection))
                    return false;
                // Preserve the proven R26 spatial billboard association:
                // stock WVP -> world view -> head inverse -> eye inverse ->
                // asymmetric eye projection. No depth flattening/alpha edit.
                const D3DMATRIX worldView =
                    R29OwnerMultiplyMatrix(stockRawWvp,
                        inverseBaseProjection);
                if (!R29OwnerMatrixFinite(worldView))
                    return false;
                // R26 R44's proven 3D-affine billboard admission. A tagged
                // sun alone does not prove the game source is a spatial WVP:
                // reject flat screen/near-clip shapes instead of applying a
                // second head/eye transform to projected 2D geometry.
                const float affineError =
                    std::fabs(worldView._14) +
                    std::fabs(worldView._24) +
                    std::fabs(worldView._34) +
                    std::fabs(worldView._44 - 1.0f);
                const float viewDepth = std::fabs(worldView._43);
                const float clipW =
                    worldView._43 * baseProjection._34 + baseProjection._44;
                if (!std::isfinite(affineError) ||
                    !std::isfinite(viewDepth) || !std::isfinite(clipW) ||
                    affineError > 0.02f ||
                    viewDepth < 1.25f || viewDepth >= 1000000.0f ||
                    clipW <= 0.05f)
                    return false;
                const D3DMATRIX headRelative =
                    R29OwnerMultiplyMatrix(worldView, headInverse);
                if (!R29OwnerMatrixFinite(headRelative))
                    return false;
                for (int eye = 0; eye < 2; ++eye)
                {
                    const D3DMATRIX eyePose =
                        R29OwnerMatrixFromQuaternionTranslation(
                            stereo.eyeOrientation[eye],
                            stereo.eyeOffset[eye],
                            Settings::VRWorldScale *
                                Settings::VRStereoDepth);
                    const D3DMATRIX eyeInverse =
                        R29OwnerInverseRigid(eyePose);
                    const D3DMATRIX eyeProjection =
                        R29OwnerProjectionFromFov(baseProjection,
                            stereo.eyeFov[eye]);
                    if (!R29OwnerMatrixFinite(eyeInverse) ||
                        !R29OwnerMatrixFinite(eyeProjection))
                        return false;
                    const D3DMATRIX corrected =
                        R29OwnerMultiplyMatrix(
                            R29OwnerMultiplyMatrix(
                                headRelative, eyeInverse),
                            eyeProjection);
                    if (!R29OwnerMatrixFinite(corrected))
                        return false;
                    const D3DMATRIX correctedT =
                        R29OwnerTransposeMatrix(corrected);
                    std::memcpy(eyeConstants[eye], &correctedT,
                        sizeof(correctedT));
                }
                return true;
            }

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
                // The direct 0xCABE flare-ring producer is already
                // camera-projected. Other queued/scene effects still need
                // the original full HMD world-lock transformation.
                const bool directProjected2D =
                    !OutRunVR::GameSemantic::QueueRenderActive() &&
                    OutRunVR::GameSemantic::EffectiveScope() ==
                        OutRunVR::GameSemantic::RenderScope::ProjectedScreenEffect2D;
                const auto* geometry = R30PrepareFlatEffectGeometry(
                    stereo, baseProjection, headInverse, directProjected2D);
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
                    directProjected2D ? commonViewPlane
                        : R29OwnerMultiplyMatrix(commonViewPlane, headInverse);
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
            const auto pauseVertical = R30PauseMenuVerticalAffine(stereo);
            const bool pauseOwned = R30IsPauseMenuElement();
            for (int eye = 0; eye < 2; ++eye)
            {
                D3DMATRIX clipCorrection{};
                // Keep the already-verified ordinary HUD mapping unchanged.
                // Only FlatPerspectiveEffect uses the finite 3D plane above.
                // The paused shell can use the VS path while its original
                // option arrows use XYZRHW; match XYZRHW eyeScaleX in each
                // eye, including asymmetric FOV. Non-pause HUD remains exact.
                clipCorrection._11 = OutRunVrPauseEye::ShaderHorizontalScale(
                    hudScaleX, eyeScale[eye], pauseOwned);
                clipCorrection._22 =
                    hudScaleY * pauseVertical.scale[eye];
                clipCorrection._33 = 1.0f;
                clipCorrection._44 = 1.0f;
                clipCorrection._41 = eyeOffset[eye];
                // Row-vector post-projection translation: positive viewport
                // fraction must move pixels down (negative clip-space Y).
                clipCorrection._42 = pauseVertical.offset[eye] -
                    2.0f * R30PauseMenuVerticalFraction();

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
                R30RecordTelemetryCounter(R30ScreenSpaceBuildFailures);
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

            // Capture only before an actual tagged HUD/2D overlay. A
            // depth-disabled scene effect or world lens billboard is not a
            // valid bloom cutoff even when it looks screen-space in D3D9.
            // The shared semantic predicate is already used by R26+HUD.
            if (OutRunVR::GameSemantic::IsSkyGlowPreHudBoundary(
                    OutRunVR::GameSemantic::EffectiveScope()))
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
                    // No HUD primitive was drawn yet, but failed c64 rollback
                    // still leaves the current eye submission unusable.
                    R29OwnerMarkRightDrawFailed();
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
                // A failed left-eye HUD draw must veto THIS frame's right-eye
                // publication; future-only mono safety cannot repair a stale
                // binocular pair. Invalidate any left-written depth/stencil.
                R29OwnerMarkRightDrawFailed();
                R29OwnerInvalidateRightDepthStencilIfLeftMayWrite(device);
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
            // R33's proven depthless guard also applies to this R30-owned
            // stereo draw: live setter/StateBlock coverage and a null tracked
            // depth attachment must both hold. Unknown state never bypasses.
            const bool depthlessPass = savedDepth == nullptr &&
                OutRunVR::State::StateBlockTracker::Reliable();
            HRESULT rightHr = D3D_OK;
            OutRunVR::StereoFailureReason rightFailure =
                OutRunVR::StereoFailureRightStateFailed;
            bool restoreOk = true;
            {
                R30ScopedInternalPass guard;
                rightHr = R29OwnerCallOriginalSetRenderTarget(
                    device, 0u, frame.rightEyeSurface);
                if (SUCCEEDED(rightHr) && !depthlessPass)
                {
                    rightHr = R29OwnerCallOriginalSetDepthStencilSurface(
                        device, savedDepth ? frame.rightEyeDepth : nullptr);
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
                restoreOk = depthlessPass
                    ? R30RestoreDepthlessRightPassState(
                        device, savedRt, savedViewport, original, true)
                    : R29OwnerRestoreRightPassState(
                        device, savedRt, savedDepth, savedViewport, original, true);
            }

            // Never publish a completed stereo draw or its pose metadata
            // before BOTH physical eyes and the game render state are valid.
            if (OutRunVR::StereoCompletion::CanPublishStereoDraw(
                    SUCCEEDED(leftHr), SUCCEEDED(rightHr), restoreOk))
            {
                R29OwnerRecordHudStereoDuplicate();
                R29OwnerNoteStableTwoEyeDraw();
                R30RecordTelemetryCounter(R30ScreenSpaceFovDraws);
    
                if (!R30FirstScreenSpaceLogged)
                {
                    R30FirstScreenSpaceLogged = true;
                    spdlog::info(
                        "VR R30 HUD: asymmetric-FOV convergence correction ACTIVE; common-centre offset[L/R]={:.4f}/{:.4f} hudScale={:.2f} sourceOverTarget={:.3f}",
                        eyeOffset[0], eyeOffset[1], R30HudScaleValue(),
                        R30HudAspectCompensation(
                            stereo, frame.width, frame.height));
                }
                if (screenKind == R30ScreenSpaceKind::FlatPerspectiveEffect &&
                    !R30FirstFlatPerspectiveLogged)
                {
                    R30FirstFlatPerspectiveLogged = true;
                    spdlog::info(
                        "VR R30 FLAT EFFECT: depth-disabled alpha perspective overlay is world-locked on a finite virtual plane with real head/IPD/FOV transform (no HudScale)");
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
                // A restore failure poisons the CURRENT right-eye frame, not
                // only future stereo eligibility. Present/SkyGlow must never
                // publish a partially restored eye as binocularly complete.
                R29OwnerMarkRightDrawFailed();
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
            R30RecordTelemetryCounter(R30ScreenSpaceFallbacks);
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
        R30RecordTelemetryCounter(R30ScreenSpaceFovDraws);
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
        case R30ScreenSpaceKind::ExactLensCentreWorld:
            return R30SupportScreenSpaceKind::ExactLensCentreWorld;
        case R30ScreenSpaceKind::ProjectedWorldMarker2D:
            return R30SupportScreenSpaceKind::ProjectedWorldMarker2D;
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
        case R30SupportScreenSpaceKind::ExactLensCentreWorld:
            lower = R30ScreenSpaceKind::ExactLensCentreWorld;
            break;
        case R30SupportScreenSpaceKind::ProjectedWorldMarker2D:
            lower = R30ScreenSpaceKind::ProjectedWorldMarker2D;
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
        // R33 checks this on every fast-world/HUD draw; avoid collecting
        // thirteen unrelated frame fields through the R29 snapshot path.
        // Reading the same R29-owned scalar preserves zero/unlatched and
        // mismatched-pose fail-closed decisions exactly.
        return R29OwnerFrameStereoPoseSequence();
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
        // R31's FastWorld eye-tail cache consumes this scale. Match R30's
        // billboard/particle and flat-effect translation, including stereo
        // depth; otherwise cars/road and effects diverge when depth != 1.
        return OutRunVR::Core::EffectiveStereoWorldScale(
            Settings::VRWorldScale, Settings::VRStereoDepth);
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