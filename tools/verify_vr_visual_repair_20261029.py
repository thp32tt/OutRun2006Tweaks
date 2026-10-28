#!/usr/bin/env python3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ui=(ROOT/"src/hooks_uiscaling.cpp").read_text(encoding="utf-8")
goal=(ROOT/"src/vr/game/goal_result_parent_provenance.hpp").read_text(encoding="utf-8")
focus=(ROOT/"tools/Run-DX9ExFocusTest.ps1").read_text(encoding="utf-8-sig")
official=(ROOT/"tools/Run-FocusOfficialTest.ps1").read_text(encoding="utf-8-sig")
profiles=(ROOT/"tools/OutRunVR-TestProfiles.ps1").read_text(encoding="utf-8-sig")
for token in ("VR TRACE UNOWNED QUEUE SIGNATURE:","GameState::STATE_GAME","GameState::STATE_GOAL","CurrentQueueProducerToken() ==","ProducerToken::None","unownedSignatures"):
    assert token in ui, token
assert "std::array<std::uintptr_t, 21> OriginalB9200CallReturns" in goal
assert "0x98D37u + 5u" in goal and "0xBE009u + 5u" in goal
assert "-SkyGlowFactor=0" in focus
assert "-SkyGlowFactor=0" in official
assert "-SkyGlowFactor=0" in profiles
print("PASS 20261029 visual repair: bounded producer trace, 21 GOAL B9200 returns, normal VR SkyGlow off")
