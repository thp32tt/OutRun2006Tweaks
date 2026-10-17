// R84/desktop original car selector: a repeated XST slot is not an
// ordinal reset until the *game* restarts the pack's DDS load cursor.
#include "../../src/vr/game/texture_pack_cursor.hpp"
#include <cstdio>
#include <cstdlib>
#include <cstring>

// Always evaluate the cursor transitions in Release/NDEBUG CI builds.
// <cassert> would discard both checks AND side-effectful index calls.
#define CHECK(expr) do { \
    if (!(expr)) { \
        std::fprintf(stderr, "texture_pack_cursor_smoke:%d: %s failed\\n", __LINE__, #expr); \
        return EXIT_FAILURE; \
    } \
} while (false)

int main()
{
    using OutRunVR::TexturePacks::Cursor;
    using OutRunVR::TexturePacks::SessionPadFamily;
    constexpr int none = -1, pc = 0, xbox = 1, playstation = 2;

    // First-known-family decisions must protect complete replacement packs:
    // None is undecided; PC is a genuine family without an extra directory.
    SessionPadFamily desktop;
    desktop.Observe(none, none, none);
    CHECK(!desktop.Locked());
    desktop.Observe(pc, none, none);
    CHECK(desktop.Locked() && desktop.Type() == pc);
    desktop.Observe(xbox, none, none); // reconnect after PC input
    desktop.Observe(playstation, xbox, none);
    CHECK(desktop.Type() == pc);

    SessionPadFamily console;
    console.Observe(none, none, none);
    console.Observe(xbox, none, none);
    console.Observe(pc, none, none);
    CHECK(console.Locked() && console.Type() == xbox);

    SessionPadFamily forced;
    forced.Observe(xbox, playstation, none);
    CHECK(forced.Locked() && forced.Type() == playstation);
    forced.Observe(pc, pc, none);
    CHECK(forced.Type() == playstation);
    SessionPadFamily delayed;
    delayed.Observe(none, none, none);
    delayed.Observe(playstation, pc, none);
    CHECK(delayed.Locked() && delayed.Type() == pc);

    Cursor ui;
    char mutableName[32] = "spr_selector.xst";
    CHECK(ui.Select(mutableName, 3));
    CHECK(ui.NextIndexForGameTexture(0) == 0);
    CHECK(ui.NextIndexForGameTexture(1) == 1);
    CHECK(ui.NextIndexForGameTexture(2) == 2);

    // The same pack/source can be reentered per item. Native index 2 is not
    // a new pass, and a mid-pass seek must not corrupt the DDS sequence.
    CHECK(!ui.Select(mutableName, 3));
    CHECK(ui.NextIndexForGameTexture(2) == 3);
    CHECK(ui.NextIndexForGameTexture(4) == 4);
    CHECK(ui.NextIndexForGameTexture(3) == 5);

    // Opening car selection again reloads texture 0 of the SAME pack.
    CHECK(ui.NextIndexForGameTexture(0) == 0);
    CHECK(ui.NextIndexForGameTexture(1) == 1);
    CHECK(ui.NextIndexForGameTexture(2) == 2);

    // The next pack restart may use a native 1-based starting index.
    CHECK(ui.NextIndexForGameTexture(1) == 0);
    CHECK(ui.NextIndexForGameTexture(2) == 1);

    // A reused mutable filename buffer does not alias the stored identity.
    std::strcpy(mutableName, "spr_game.xst");
    CHECK(ui.Select(mutableName, 3));
    CHECK(ui.Name() == "spr_game.xst");
    CHECK(ui.NextIndexForGameTexture(0) == 0);
    CHECK(ui.NextIndexForGameTexture(1) == 1);
    CHECK(ui.Select(mutableName, 4));  // same text, different slot
    CHECK(ui.NextIndexForGameTexture(0) == 0);
    CHECK(!ui.Select(mutableName, 4));
    CHECK(ui.NextIndexForGameTexture(-1) == 1);
    CHECK(ui.NextIndexForGameTexture(1) == 2);

    // The independent scene-XMT cursor retains unobserved counter behavior.
    Cursor scene;
    CHECK(scene.Select("stage.xmt", 0));
    CHECK(scene.NextIndex() == 0 && scene.NextIndex() == 1);
    CHECK(!scene.Select("stage.xmt", 0));
    CHECK(scene.NextIndex() == 2);
    CHECK(scene.Select("newstage.xmt", 0));
    CHECK(scene.NextIndex() == 0);
    return 0;
}
