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
        std::uint64_t generation = 0;
        // Every native Begin/Draw/Flush/End transition must be tied to the
        // batch that was active BEFORE the D3DX call. The original D3DX
        // implementation may reenter a hooked callback or start a fresh
        // texture batch. A stale outer return must not erase that new owner.
        std::uint64_t mutationSerial = 0;
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
                                Producer drawProducer) noexcept
        {
            if (!sameGeneration(previous))
                return false;
            if (!unchanged(previous) || !succeeded)
            {
                onFlushFailure();
                return false;
            }
            recordDraw(drawScope, drawProducer);
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
        void recordDraw(Scope newScope, Producer newProducer) noexcept
        {
            if (!active)
                return;
            if (drawCount == 0)
            {
                scope = newScope;
                producer = newProducer;
                homogeneous = true;
            }
            else if (scope != newScope || producer != newProducer)
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
        }

        // Successful physical Flush leaves Begin active for the next batch.
        void onFlushSuccess() noexcept
        {
            forget();
            boundaryReady = false;
        }

        // Failed GPU draw/Flush cannot prove that pending commands survived.
        // Preserve HRESULT handling and make the current batch ineligible.
        void onFlushFailure() noexcept
        {
            active = false;
            boundaryReady = false;
            // A failed GPU batch cannot retain the previous +TIME/GOAL
            // source, even in subsequent diagnostics or recovery callbacks.
            forget();
        }

        void end() noexcept
        {
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

        bool exactUniformOwner() const noexcept
        {
            return active && homogeneous && drawCount != 0 &&
                scope != Scope::None && producer != Producer::None;
        }
    };
}