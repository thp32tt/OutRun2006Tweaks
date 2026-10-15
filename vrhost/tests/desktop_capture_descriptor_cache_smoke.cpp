#include "runtime/desktop_capture_descriptor_cache.hpp"
#include <cstdint>

using OutRunVrDesktopCaptureDescriptor::Cache;
using OutRunVrDesktopCaptureDescriptor::Key;

// Compile-time checks remain active in MSVC Release, unlike assert() which
// NDEBUG removes. The DX9Ex Gate's x64 Release build must prove all cases.
constexpr bool VerifyCaptureDescriptorCache() noexcept
{
    Cache cache{};
    constexpr Key original{0x1000, 3440, 1440, 87};
    constexpr Key anotherOutput{0x2000, 3440, 1440, 87};
    constexpr Key newExtent{0x1000, 2560, 1440, 87};
    constexpr Key hdrFormat{0x1000, 3440, 1440, 10};
    if (cache.CanReuse(true, true, true, original)) return false;
    cache.Record(original);
    if (!cache.CanReuse(true, true, true, original)) return false;
    // 72/90/120-Hz captures on one duplication reuse the same descriptor.
    for (int i = 0; i < 4096; ++i)
        if (!cache.CanReuse(true, true, true, original)) return false;

    // The first frame, a lost source/SRV, a switch, a resize or HDR change
    // must call the actual acquired texture's GetDesc before any copy.
    if (cache.CanReuse(false, true, true, original)) return false;
    if (cache.CanReuse(true, false, true, original)) return false;
    if (cache.CanReuse(true, true, false, original)) return false;
    if (cache.CanReuse(true, true, true, anotherOutput)) return false;
    if (cache.CanReuse(true, true, true, newExtent)) return false;
    if (cache.CanReuse(true, true, true, hdrFormat)) return false;
    if (cache.CanReuse(true, true, true, Key{})) return false;
    cache.Record(anotherOutput);
    if (cache.CanReuse(true, true, true, original)) return false;
    if (!cache.CanReuse(true, true, true, anotherOutput)) return false;
    cache.Invalidate();
    if (cache.CanReuse(true, true, true, anotherOutput)) return false;
    cache.Record(Key{});
    return !cache.CanReuse(true, true, true, Key{});
}
static_assert(VerifyCaptureDescriptorCache(),
    "DXGI output descriptor cache must fail closed across each output epoch");

int main()
{
    return VerifyCaptureDescriptorCache() ? 0 : 1;
}
