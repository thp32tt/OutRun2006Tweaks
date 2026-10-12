#include "runtime/desktop_capture_descriptor_cache.hpp"
#include <cassert>
#include <cstdint>

using OutRunVrDesktopCaptureDescriptor::Cache;
using OutRunVrDesktopCaptureDescriptor::Key;
int main()
{
    Cache cache{};
    constexpr Key original{0x1000, 3440, 1440, 87};
    constexpr Key anotherOutput{0x2000, 3440, 1440, 87};
    constexpr Key newExtent{0x1000, 2560, 1440, 87};
    constexpr Key hdrFormat{0x1000, 3440, 1440, 10};
    assert(!cache.CanReuse(true, true, true, original));
    cache.Record(original);
    assert(cache.CanReuse(true, true, true, original));
    // 90/120-Hz frames within one duplication avoid repeated GetDesc.
    for (int i = 0; i < 4096; ++i)
        assert(cache.CanReuse(true, true, true, original));

    // Recreated duplication, first frame, texture/SRV loss or monitor switch
    // must re-validate the actual acquired texture before any CopyResource.
    assert(!cache.CanReuse(false, true, true, original));
    assert(!cache.CanReuse(true, false, true, original));
    assert(!cache.CanReuse(true, true, false, original));
    assert(!cache.CanReuse(true, true, true, anotherOutput));
    assert(!cache.CanReuse(true, true, true, newExtent));
    assert(!cache.CanReuse(true, true, true, hdrFormat));
    assert(!cache.CanReuse(true, true, true, Key{}));
    cache.Record(anotherOutput);
    assert(!cache.CanReuse(true, true, true, original));
    assert(cache.CanReuse(true, true, true, anotherOutput));
    cache.Invalidate();
    assert(!cache.CanReuse(true, true, true, anotherOutput));
    cache.Record(Key{});
    assert(!cache.CanReuse(true, true, true, Key{}));
}
