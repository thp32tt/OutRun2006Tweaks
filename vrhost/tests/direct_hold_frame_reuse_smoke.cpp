#include "runtime/direct_hold_frame_reuse.hpp"

using namespace OutRunVrDirectHoldReuse;

constexpr FrameKey Base{ 100, 2, 17, 9, 4321, 0x1F00, 0x2000, 0xABCD, 0xDCBA };
static_assert(CanReuse(true, Base, Base));
static_assert(!CanReuse(false, Base, Base));
static_assert(!CanReuse(true, Base, FrameKey{101, 2, 17, 9, 4321, 0x1F00, 0x2000, 0xABCD, 0xDCBA}));
static_assert(!CanReuse(true, Base, FrameKey{100, 1, 17, 9, 4321, 0x1F00, 0x2000, 0xABCD, 0xDCBA}));
static_assert(!CanReuse(true, Base, FrameKey{100, 2, 18, 9, 4321, 0x1F00, 0x2000, 0xABCD, 0xDCBA}));
static_assert(!CanReuse(true, Base, FrameKey{100, 2, 17, 10, 4321, 0x1F00, 0x2000, 0xABCD, 0xDCBA}));
static_assert(!CanReuse(true, Base, FrameKey{100, 2, 17, 9, 4322, 0x1F00, 0x2000, 0xABCD, 0xDCBA}));
static_assert(!CanReuse(true, Base, FrameKey{100, 2, 17, 9, 4321, 0x1F01, 0x2000, 0xABCD, 0xDCBA}));
static_assert(!CanReuse(true, Base, FrameKey{100, 2, 17, 9, 4321, 0x1F00, 0x2001, 0xABCD, 0xDCBA}));
static_assert(!CanReuse(true, Base, FrameKey{100, 2, 17, 9, 4321, 0x1F00, 0x2000, 0xABCE, 0xDCBA}));
static_assert(!CanReuse(true, Base, FrameKey{100, 2, 17, 9, 4321, 0x1F00, 0x2000, 0xABCD, 0xDCBB}));
static_assert(!CanReuse(true, Base, FrameKey{}));
static_assert(!CanReuse(true, Base, FrameKey{100, 2, 17, 9, 4321, 0x1F00, 0x2000, 0, 0xDCBA}));
static_assert(!CanReuse(true, Base, FrameKey{100, 2, 17, 9, 4321, 0x1F00, 0x2000, 0xABCD, 0}));
static_assert(!CanReuse(true, Base, FrameKey{100, 2, 0, 9, 4321, 0x1F00, 0x2000, 0xABCD, 0xDCBA}));
static_assert(!CanReuse(true, Base, FrameKey{100, 2, 17, 0, 4321, 0x1F00, 0x2000, 0xABCD, 0xDCBA}));

int main() { return CanReuse(true, Base, Base) && !CanReuse(false, Base, Base) ? 0 : 1; }
