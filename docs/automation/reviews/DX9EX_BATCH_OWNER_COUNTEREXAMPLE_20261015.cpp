#include "../../../src/vr/game/render_semantics.hpp"
#include <iostream>

// A contract counterexample, NOT a D3D9/device/game reproduction.
// ID3DXSprite::Draw may buffer; GPU work can happen after the producer returns.
int main() {
    using namespace OutRunVR::GameSemantic;
    RenderScope registeredScope;
    ProducerToken registeredProducer;
    {
        ScopedExactProducerSemantic owner(RenderScope::ScreenHud, nullptr, true,
                                          ProducerToken::StageExtensionTime);
        registeredScope = EffectiveScope();
        registeredProducer = CurrentRenderProducerToken();
        // Intentionally no device draw while the producer scope is alive.
    }
    const auto delayedScope = ConsumeForDraw();
    const auto delayedProducer = CurrentRenderProducerToken();
    if (registeredScope != RenderScope::ScreenHud ||
        registeredProducer != ProducerToken::StageExtensionTime ||
        delayedScope != RenderScope::None || delayedProducer != ProducerToken::None)
        return 1;
    std::cout << "COUNTEREXAMPLE_REPRODUCED: direct +TIME tag does not survive a deferred GPU submission by itself. Actual game D3DX route remains unproven.\n";
}
