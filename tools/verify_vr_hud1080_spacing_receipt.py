#!/usr/bin/env python3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ui=(ROOT/"src/hooks_uiscaling.cpp").read_text(encoding="utf-8")
start=ui.index("template <typename T>\n\tstatic void AddSpriteSpacing")
end=ui.index("static void put_scroll_AdjustPositionRight", start)
body=ui[start:end]
for token in (
    "mode != ScalingMode::OnlineArcade",
    "Settings::VREnabled && Settings::VRHud1080pReference",
    "? 80.0f",
    "const float before = float(*value);",
    "VR TRACE HUD1080 SPACING:",
    "hit <= 16 || (hit & (hit - 1u)) == 0",
    "screenScale={:.9g},{:.9g}",
    "screenRes={:.9g},{:.9g}",
):
    assert token in body, token
assert body.count("*value = T(") == 2
print("PASS HUD1080 side spacing remains 80 logical px with bounded runtime receipts")
