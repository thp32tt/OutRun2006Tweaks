#include "../src/vr/d3d11/native_game_eye_pair_sources.hpp"
using outrun::vr::dx11::native_game_eye_copy_cancelable;
static_assert(native_game_eye_copy_cancelable(false),
              "Unsubmitted native eye reservation must remain cancelable");
static_assert(!native_game_eye_copy_cancelable(true),
              "Submitted eye copy may not be cancelled before EVENT completion");
int main() { return native_game_eye_copy_cancelable(true) ? 1 : 0; }
