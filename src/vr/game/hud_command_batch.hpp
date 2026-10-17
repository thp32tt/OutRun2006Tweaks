#pragma once

#include <cstdint>
#include <limits>
#include "render_semantics.hpp"

// Quest-inspired command staging without importing GLES/Quest object code.
// R84 still uses the original ID3DXSprite and its Begin/Draw/Flush/End,
// and stereo ownership is granted only by the existing exact-source policy.
namespace OutRunVR::HudCommandBatch
{
    struct Ledger final
    {
        using Scope = GameSemantic::RenderScope;
        using Producer = GameSemantic::ProducerToken;
        void* sprite = nullptr;
        bool active = false;
        bool homogeneous = true;
        bool boundaryReady = false;
        unsigned drawCount = 0;
        Scope scope = Scope::None;
        Producer producer = Producer::None;
        // A queued SpriteNode is a distinct physical producer even when
        // two nodes (or a direct glyph and a node) share +TIME's token.
        // Never mix them into a homogeneous delayed native D3DX batch.
        bool queued = false;
        const void* queueNode = nullptr;
        std::uint64_t queueEpoch = 0;
        std::uint64_t generation = 0;
        // Every native Begin/Draw/Flush/End transition must be tied to the
        // batch that was active BEFORE the D3DX call. The original D3DX
        // implementation may reenter a hooked callback or start a fresh
        // texture batch. A stale outer return must not erase that new owner.
        std::uint64_t mutationSerial = 0;
        // A successful native Flush may be invoked INSIDE D3DXSprite::Draw
        // on a texture transition. Its new, empty batch is still live; the
        // returning Draw owns the first command in that new batch.
        // Other reentrant mutations must never inherit this permission.
        std::uint64_t lastSuccessfulFlushMutationSerial = 0;
        struct NativeSnapshot final
        {
            void* sprite;
            std::uint64_t generation;
            std::uint64_t mutationSerial;
        };

        NativeSnapshot snapshot() const noexcept
        {
            return { sprite, generation, mutationSerial };
        }

        bool sameGeneration(const NativeSnapshot& previous) const noexcept
        {
            return previous.sprite != nullptr &&
                sprite == previous.sprite &&
                generation == previous.generation;
        }

        bool unchanged(const NativeSnapshot& previous) const noexcept
        {
            return sameGeneration(previous) &&
                mutationSerial == previous.mutationSerial;
        }

        void touch() noexcept
        {
            if (++mutationSerial == 0)
                ++mutationSerial;
        }

        // Preserve a reentrant NEW Begin; a mutation within the SAME Begin
        // makes the submission's original-source ownership ambiguous.
        // Fail closed rather than promoting partially submitted glyphs.
        bool completeNativeFlush(const NativeSnapshot& previous,
                                 bool succeeded) noexcept
        {
            if (!sameGeneration(previous))
                return false;
            if (!unchanged(previous) || !succeeded)
            {
                onFlushFailure();
                return false;
            }
            onFlushSuccess();
            return true;
        }

        bool completeNativeEnd(const NativeSnapshot& previous) noexcept
        {
            if (!sameGeneration(previous))
                return false;
            end();
            return true;
        }

        bool completeNativeDraw(const NativeSnapshot& previous,
                                bool succeeded, Scope drawScope,
                                Producer drawProducer,
                                bool sourceStillMatches = true,
                                bool drawQueued = false,
                                const void* drawQueueNode = nullptr,
                                std::uint64_t drawQueueEpoch = 0) noexcept
        {
            if (!sameGeneration(previous))
                return false;
            if (!succeeded || !sourceStillMatches)
            {
                // Native D3DX Draw can replace its original producer without
                // another hooked batch mutation. Never assign foreign GPU
                // triangles to the previously captured +TIME/GOAL eye plane.
                // Native Draw HRESULT and GPU submission remain unchanged.
                onFlushFailure();
                return false;
            }
            if (!unchanged(previous))
            {
                // Native Draw can internally Flush the previous texture and
                // then enqueue its own new texture. The Flush hook has reset
                // drawCount and stamped the exact final mutation. Admit only
                // this completed transition: never reattribute reentrant
                // Draw/Begin, mixed commands, failed Flush or changed source.
                const bool cleanInternalFlush =
                    active && drawCount == 0 &&
                    homogeneous && scope == Scope::None &&
                    producer == Producer::None &&
                    lastSuccessfulFlushMutationSerial != 0 &&
                    lastSuccessfulFlushMutationSerial == mutationSerial;
                if (!cleanInternalFlush)
                {
                    onFlushFailure();
                    return false;
                }
            }
            recordDraw(drawScope, drawProducer,
                drawQueued, drawQueueNode, drawQueueEpoch);
            return true;
        }

        // Only an actual Begin or Reset alters the batch generation.
        // An invalid/reentrant Begin is handled by the hook's original
        // HRESULT policy; it must not discard the prior live batch.
        void begin(void* exactSprite, bool succeeded) noexcept
        {
            sprite = exactSprite;
            active = succeeded;
            boundaryReady = false;
            lastSuccessfulFlushMutationSerial = 0;
            forget();
            if (succeeded && generation != UINT64_MAX)
                ++generation;
        }

        // Nested Begin on the exact same object may fail with INVALIDCALL
        // while the original Draw batch remains live. Other failed Begin
        // results (including DEVICELOST) cannot prove that the pending GPU
        // batch or its +TIME/GOAL semantic survived. Revoke BOTH object
        // identity and provenance, without changing native HRESULT handling.
        void onBeginResult(void* exactSprite, bool succeeded,
                           bool reentrantInvalidCall) noexcept
        {
            if (succeeded)
            {
                begin(exactSprite, true);
                return;
            }
            if (reentrantInvalidCall && active && exactSprite != nullptr &&
                sprite == exactSprite)
                return;
            invalidate();
        }

        // CPU-side Draw only records commands; no GPU submission occurs here.
        // Unknown or mixed producer batches must never be promoted to HUD.
        void recordDraw(Scope newScope, Producer newProducer,
                        bool drawQueued = false,
                        const void* drawQueueNode = nullptr,
                        std::uint64_t drawQueueEpoch = 0) noexcept
        {
            if (!active)
                return;
            lastSuccessfulFlushMutationSerial = 0;
            const bool validQueue = !drawQueued ||
                (drawQueueNode != nullptr && drawQueueEpoch != 0);
            if (drawCount == 0)
            {
                scope = newScope;
                producer = newProducer;
                queued = drawQueued;
                queueNode = drawQueued ? drawQueueNode : nullptr;
                queueEpoch = drawQueued ? drawQueueEpoch : 0;
                homogeneous = validQueue;
            }
            else if (!validQueue || scope != newScope ||
                     producer != newProducer || queued != drawQueued ||
                     (drawQueued && (queueNode != drawQueueNode ||
                                     queueEpoch != drawQueueEpoch)))
            {
                homogeneous = false;
            }
            if (drawCount != (std::numeric_limits<unsigned>::max)())
                ++drawCount;
            // Even a saturated draw count is a new native GPU registration.
            touch();
        }

        void forget() noexcept
        {
            touch();
            drawCount = 0;
            homogeneous = true;
            scope = Scope::None;
            producer = Producer::None;
            queued = false;
            queueNode = nullptr;
            queueEpoch = 0;
        }

        // Successful physical Flush leaves Begin active for the next batch.
        void onFlushSuccess() noexcept
        {
            forget();
            boundaryReady = false;
            // Mark this exact mutation only. A later Draw, End or Begin
            // revokes recovery of an outer native Draw return.
            lastSuccessfulFlushMutationSerial = mutationSerial;
        }

        // Failed GPU draw/Flush cannot prove that pending commands survived.
        // Preserve HRESULT handling and make the current batch ineligible.
        void onFlushFailure() noexcept
        {
            lastSuccessfulFlushMutationSerial = 0;
            active = false;
            boundaryReady = false;
            // A failed GPU batch cannot retain the previous +TIME/GOAL
            // source, even in subsequent diagnostics or recovery callbacks.
            forget();
        }

        void end() noexcept
        {
            lastSuccessfulFlushMutationSerial = 0;
            active = false;
            boundaryReady = false;
            forget();
        }

        // Old D3DXSprite object may be gone after Lost/Reset.
        void invalidate() noexcept
        {
            end();
            sprite = nullptr;
        }

        // A queued GPU batch cannot become a direct HUD batch after
        // its SpriteNode leaves. Match node identity AND selection epoch.
        bool matchesGpuOwner(bool queueActive, const void* node,
                             std::uint64_t epoch) const noexcept
        {
            if (!queued)
                return !queueActive && queueNode == nullptr && queueEpoch == 0;
            return queueActive && queueNode != nullptr && queueEpoch != 0 &&
                queueNode == node && queueEpoch == epoch;
        }

        bool exactUniformOwner() const noexcept
        {
            return active && homogeneous && drawCount != 0 &&
                scope != Scope::None && producer != Producer::None;
        }
    };
}