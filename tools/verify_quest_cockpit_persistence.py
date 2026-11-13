#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parents[1]
launcher = (root / "Start-OutRun.cmd").read_text(encoding="utf-8")
ini = (root / "OutRun2006Tweaks.ini").read_text(encoding="utf-8")
ui = (root / "src/overlay/settings_ui.cpp").read_text(encoding="utf-8")
plugin = (root / "src/plugin.hpp").read_text(encoding="utf-8")
vr = (root / "src/vr/settings.cpp").read_text(encoding="utf-8")

for forced in ("-VR.QuestCockpitV2SeatBack=", "-VR.QuestCockpitV2SeatDown=", "-VR.QuestCockpitV2SeatRight="):
    assert forced not in launcher, forced

for default in ("QuestCockpitV2SeatBack = -0.08", "QuestCockpitV2SeatDown = 0.8", "QuestCockpitV2SeatRight = 0.0"):
    assert default in ini, default

assert "VRQuestCockpitV2ReleaseSeatBackDefault = -0.08f" in plugin
assert "VRQuestCockpitV2ReleaseSeatDownDefault = 0.80f" in plugin
assert "VRQuestCockpitV2ReleaseSeatRightDefault = 0.0f" in plugin
assert "VRQuestCockpitV2ReleaseSeatBackDefault," in vr
assert "VRQuestCockpitV2ReleaseSeatDownDefault," in vr
assert "VRQuestCockpitV2ReleaseSeatRightDefault," in vr
assert 'ImGui::Button("Save Cockpit View")' in ui
assert 'ImGui::Button("Reset Cockpit View")' in ui
assert "Settings::write(Module::UserIniPath)" in ui
assert "VRQuestCockpitV2SeatBack = Settings::VRQuestCockpitV2ReleaseSeatBackDefault" in ui
assert "VRQuestCockpitV2SeatDown = Settings::VRQuestCockpitV2ReleaseSeatDownDefault" in ui
assert "VRQuestCockpitV2SeatRight = Settings::VRQuestCockpitV2ReleaseSeatRightDefault" in ui
print("PASS: v0.02 cockpit seat defaults persist and F11 save/reset controls are wired")