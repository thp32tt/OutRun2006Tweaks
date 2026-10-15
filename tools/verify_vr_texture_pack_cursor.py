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
    require("next_ = 0;" in head and "return next_++;" in head,
            "a different pack must reset its ordinal and sequential loads must increment")
    require("if (!name)" in head and "return false;" in head,
            "null pack path must not poison the cursor")
    require("UiTextureCursor;" in text and "SceneTextureCursor;" in text,
            "UI and scene require separate indexed-DDS cursors")
    require("UiTextureCursor.Select(xstsetFilename, static_cast<int>(ctx.eax))" in text,
            "xstset slot and name must both participate in source selection")
    require("SceneTextureCursor.Select(XmtFileName, 0)" in text,
            "xmt object index must not reset the pack cursor")
    require("UiTextureCursor.NextIndex() : SceneTextureCursor.NextIndex()" in text,
            "indexed DDS must use the correct stream counter")
    require("CurrentXmtsetFilename = SceneTextureCursor.Name()" in text,
            "scene texture path must copy the selected filename contents")
    require("CurrentXstsetFilename = UiTextureCursor.Name()" in text,
            "UI texture path must copy the selected filename contents")
    require("CurrentTextureIdx" not in text and "PrevXmtName" not in text,
            "shared ordinal and raw-name pointer ownership have returned")

check(src)
mutations = (
    (src.replace("UiTextureCursor.NextIndex() : SceneTextureCursor.NextIndex()",
                 "UiTextureCursor.NextIndex() : UiTextureCursor.NextIndex()", 1), hdr),
    (src.replace("SceneTextureCursor.Select(XmtFileName, 0)",
                 "SceneTextureCursor.Select(XmtFileName, XmtIndex)", 1), hdr),
    (src.replace("UiTextureCursor.Select(xstsetFilename, static_cast<int>(ctx.eax))",
                 "UiTextureCursor.Select(xstsetFilename, 0)", 1), hdr),
    (src, hdr.replace("SameSource(name_, slot_, incoming, slot)",
                      "name_.data() == incoming.data()")),
    (src, hdr.replace("next_ = 0;", "next_ = 1;", 1)),
)
for n, (bad_src, bad_hdr) in enumerate(mutations, 1):
    try:
        check(bad_src, bad_hdr)
    except AssertionError:
        continue
    raise AssertionError(f"destructive texture-pack mutation {n} escaped")
print(f"Texture-pack identity PASS: UI/scene isolation; {len(mutations)} mutation failures rejected; HMD UNTESTED")
