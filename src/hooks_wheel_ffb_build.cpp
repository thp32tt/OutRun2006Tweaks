// Build shim for the experimental WheelFFB implementation.
// Windows.h defines min/max macros by default; they collide with std::max/std::clamp
// used by hooks_wheel_ffb.cpp. Keep NOMINMAX local to this translation unit so the
// rest of OutRun2006Tweaks can continue using the Win32 macros where it already does.
#define NOMINMAX
#include "hooks_wheel_ffb.cpp"
