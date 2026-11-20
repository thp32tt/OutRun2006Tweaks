#include "../src/vr/state/game_reset_events.hpp"
#include <cassert>

static int calls=0;
static void OnReset() noexcept { ++calls; }

int main() {
    using namespace OutRunVR::GameResetEvents;
    Clear();
    NotifyBeforeReset();
    assert(calls==0);

    Configure(&OnReset);
    NotifyBeforeReset();
    assert(calls==1);
    NotifyBeforeReset();
    assert(calls==2);

    Clear();
    NotifyBeforeReset();
    assert(calls==2);
    return 0;
}
