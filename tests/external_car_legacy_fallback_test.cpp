#include "../src/vr/game/external_car_legacy_fallback.hpp"
#include <cassert>
#include <initializer_list>
using namespace OutRunVR::DinoSidecar;
int main() {
    // Canonical OVC absent: exact fixed GTO/F40 legacy route is permitted.
    assert(LegacyFallbackForMissingCanonical(false,2u));
    assert(LegacyFallbackForMissingCanonical(false,3u));
    // A real canonical file or directory exists: no legacy substitution,
    // regardless of stale GetLastError carried from another API.
    assert(!LegacyFallbackForMissingCanonical(true,0u));
    assert(!LegacyFallbackForMissingCanonical(true,2u));
    assert(!LegacyFallbackForMissingCanonical(true,5u));
    // Access denied, sharing/invalid device, CRC, I/O and other errors must
    // keep the canonical slot identity. The normal renderer will fall back.
    for(unsigned code:{0u,1u,5u,21u,32u,87u,1117u})
        assert(!LegacyFallbackForMissingCanonical(false,code));
}
