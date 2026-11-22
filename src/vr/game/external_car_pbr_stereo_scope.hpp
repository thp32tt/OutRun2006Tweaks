#pragma once
// Exact one-DIP ownership of the external PBR shader pair.
// Only the physical R7 stereo renderer may consume this scope, after COM
// shader identity and the active external mesh receipt have been verified.
#include <d3d9.h>

namespace OutRunVR::DinoSidecar {
struct ExternalPbrStereoOwner final {
    IDirect3DVertexShader9* vertex=nullptr;
    IDirect3DPixelShader9* pixel=nullptr;
};
inline thread_local const ExternalPbrStereoOwner* ActiveExternalPbrStereo=nullptr;

class ScopedExternalPbrStereo final {
    ExternalPbrStereoOwner current_{};
    const ExternalPbrStereoOwner* previous_=nullptr;
public:
    ScopedExternalPbrStereo(IDirect3DVertexShader9* vertex,
                            IDirect3DPixelShader9* pixel) noexcept
        : current_{vertex,pixel},previous_(ActiveExternalPbrStereo) {
        if(vertex && pixel)ActiveExternalPbrStereo=&current_;
    }
    ~ScopedExternalPbrStereo() noexcept {
        ActiveExternalPbrStereo=previous_;
    }
    ScopedExternalPbrStereo(const ScopedExternalPbrStereo&)=delete;
    ScopedExternalPbrStereo& operator=(const ScopedExternalPbrStereo&)=delete;
};
} // namespace OutRunVR::DinoSidecar
