#!/usr/bin/env python3
"""DX9Ex texture-pack source identity, indexed DDS isolation and mutations."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
hdr = (ROOT / "src/vr/game/texture_pack_cursor.hpp").read_text(encoding="utf-8")
src = (ROOT / "src/hooks_textures.cpp").read_text(encoding="utf-8")

def require(value, reason):
    if not value:
        raise AssertionError(reason)

def check(text, head=hdr):
    require("SameSource(name_, slot_, incoming, slot)" in head,
            "pack identity must use persisted name AND slot")
    require("name_.assign(incoming.data(), incoming.size());" in head,
            "mutable caller path must be snapshotted, not kept as pointer")
    # The cursor's member default is also "next_ = 0"; assert the actual
    # pack-switch reset after slot assignment, not merely that default.
    require(re.search(r"slot_\s*=\s*slot;\s*next_\s*=\s*0;\s*lastGameTextureIndex_\s*=\s*-1;\s*selected_\s*=\s*true;", head) is not None
            and "return next_++;" in head,
            "pack switching must reset the ordinal before selecting; sequential loads increment")
    require("if (!name)" in head and "return false;" in head,
            "null pack path must not poison the cursor")
    require("UiTextureCursor;" in text and "SceneTextureCursor;" in text,
            "UI and scene require separate indexed-DDS cursors")
    require("UiTextureCursor.Select(xstsetFilename, static_cast<int>(ctx.eax))" in text,
            "xstset slot and name must both participate in source selection")
    require("SceneTextureCursor.Select(XmtFileName, 0)" in text,
            "xmt object index must not reset the pack cursor")
    require(re.search(
            r"UiTextureCursor\.NextIndexForGameTexture\(\s*\*Module::exe_ptr<int>\(0x55B25C\)\s*\)\s*:\s*SceneTextureCursor\.NextIndex\(\);",
            text) is not None,
            "game native XST index must drive UI DDS ordinal; scene XMT keeps its own cursor")
    require(re.search(r"if \(lastGameTextureIndex_ > gameTextureIndex &&\s*gameTextureIndex <= 1\)\s*next_\s*=\s*0;", head) is not None
            and "lastGameTextureIndex_ = gameTextureIndex;" in head,
            "same-pack native index rewind must reset the ordinal and track last seen index")
    require("CurrentXmtsetFilename = SceneTextureCursor.Name()" in text,
            "scene texture path must copy the selected filename contents")
    require("CurrentXstsetFilename = UiTextureCursor.Name()" in text,
            "UI texture path must copy the selected filename contents")
    require("CurrentTextureIdx" not in text and "PrevXmtName" not in text,
            "shared ordinal and raw-name pointer ownership have returned")

check(src)
mutations = (
    (src.replace(": SceneTextureCursor.NextIndex();",
                 ": UiTextureCursor.NextIndex();", 1), hdr),
    (src.replace("SceneTextureCursor.Select(XmtFileName, 0)",
                 "SceneTextureCursor.Select(XmtFileName, XmtIndex)", 1), hdr),
    (src.replace("UiTextureCursor.Select(xstsetFilename, static_cast<int>(ctx.eax))",
                 "UiTextureCursor.Select(xstsetFilename, 0)", 1), hdr),
    (src, hdr.replace("SameSource(name_, slot_, incoming, slot)",
                      "name_.data() == incoming.data()")),
    # Mutate Select's per-pack reset, not the separate member initializer.
    (src, hdr.replace("slot_ = slot;\n            next_ = 0;\n            lastGameTextureIndex_ = -1;\n            selected_ = true;",
                      "slot_ = slot;\n            next_ = 1;\n            lastGameTextureIndex_ = -1;\n            selected_ = true;", 1)),
    (src, hdr.replace("gameTextureIndex <= 1", "gameTextureIndex < 0", 1)),
    (src, hdr.replace("lastGameTextureIndex_ > gameTextureIndex",
                      "lastGameTextureIndex_ < gameTextureIndex", 1)),
    (src.replace("*Module::exe_ptr<int>(0x55B25C)",
                 "*Module::exe_ptr<int>(0x55B218)", 1), hdr),
)
for n, (bad_src, bad_hdr) in enumerate(mutations, 1):
    require(bad_src != src or bad_hdr != hdr,
            f"destructive texture-pack mutation {n} was never injected")
    try:
        check(bad_src, bad_hdr)
    except AssertionError:
        continue
    raise AssertionError(f"destructive texture-pack mutation {n} escaped")
print(f"Texture-pack identity PASS: UI/scene isolation; {len(mutations)} mutation failures rejected; HMD UNTESTED")
