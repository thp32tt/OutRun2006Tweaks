// R84/desktop original car selector: a repeated XST slot is not an
// ordinal reset until the *game* restarts the pack's DDS load cursor.
#include "../../src/vr/game/texture_pack_cursor.hpp"
#include <cassert>
#include <cstring>

int main()
{
    using OutRunVR::TexturePacks::Cursor;
    Cursor ui;
    char mutableName[32] = "spr_selector.xst";
    assert(ui.Select(mutableName, 3));
    assert(ui.NextIndexForGameTexture(0) == 0);
    assert(ui.NextIndexForGameTexture(1) == 1);
    assert(ui.NextIndexForGameTexture(2) == 2);

    // The same pack/source can be reentered per item. Native index 2 is not
    // a new pass, and a mid-pass seek must not corrupt the DDS sequence.
    assert(!ui.Select(mutableName, 3));
    assert(ui.NextIndexForGameTexture(2) == 3);
    assert(ui.NextIndexForGameTexture(4) == 4);
    assert(ui.NextIndexForGameTexture(3) == 5);

    // Opening car selection again reloads texture 0 of the SAME pack.
    assert(ui.NextIndexForGameTexture(0) == 0);
    assert(ui.NextIndexForGameTexture(1) == 1);
    assert(ui.NextIndexForGameTexture(2) == 2);

    // The next pack restart may use a native 1-based starting index.
    assert(ui.NextIndexForGameTexture(1) == 0);
    assert(ui.NextIndexForGameTexture(2) == 1);

    // A reused mutable filename buffer does not alias the stored identity.
    std::strcpy(mutableName, "spr_game.xst");
    assert(ui.Select(mutableName, 3));
    assert(ui.Name() == "spr_game.xst");
    assert(ui.NextIndexForGameTexture(0) == 0);
    assert(ui.NextIndexForGameTexture(1) == 1);
    assert(ui.Select(mutableName, 4));  // same text, different slot
    assert(ui.NextIndexForGameTexture(0) == 0);
    assert(!ui.Select(mutableName, 4));
    assert(ui.NextIndexForGameTexture(-1) == 1);
    assert(ui.NextIndexForGameTexture(1) == 2);

    // The independent scene-XMT cursor retains unobserved counter behavior.
    Cursor scene;
    assert(scene.Select("stage.xmt", 0));
    assert(scene.NextIndex() == 0 && scene.NextIndex() == 1);
    assert(!scene.Select("stage.xmt", 0));
    assert(scene.NextIndex() == 2);
    assert(scene.Select("newstage.xmt", 0));
    assert(scene.NextIndex() == 0);
    return 0;
}
