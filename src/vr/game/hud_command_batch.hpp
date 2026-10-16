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
        }

        void forget() noexcept
        {
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