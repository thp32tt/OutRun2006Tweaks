#!/usr/bin/env python3
"""R26+HUD mono shadow gap regression gates."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
s=(root/"src/vr/d3d9/stereo_renderer.cpp").read_text()
r30=(root/"src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp").read_text()
def section(start,end):
    assert s.count(start)==1
    return s.split(start,1)[1].split(end,1)[0]
d=section("HRESULT R9ExecuteDraw(","HRESULT __stdcall DrawPrimitiveDestR9(")
c=section("HRESULT __stdcall ClearDestR9(","template <typename ActualDraw, typename LegacyDraw>")
p=section("HRESULT __stdcall PresentDestR9(","HRESULT __stdcall ResetDestR9(")
skipped=d.split("if (R9MonoBackupGap)",1)[1].split("else",1)[0]
assert "++R9MonoGapSkippedDraws;" in skipped
assert "R9ReplayMonoDraw(" not in skipped
assert d.index("if (R9MonoBackupGap)")<d.index("R9EnsureMonoResources(device)")
assert "R9ReplayMonoDraw(device, actualDraw, monoHr)" in d
assert "hr = legacyDraw();" in d and "if (FrameStereoIncomplete)" in d
assert "const bool monoCanReseed = full &&" in c
assert "(flags & D3DCLEAR_TARGET) != 0 && !FrameStereoIncomplete;" in c
assert c.index("if (R9MonoBackupGap && !monoCanReseed)")<c.index("R9EnsureMonoResources(device)")
assert "++R9MonoGapSkippedClears;" in c
assert "monoOk = R9ReplayMonoClear(" in c
assert "R9MonoBackupGap = false;" in c
assert "if (R9MonoSeeded && !R9MonoBackupGap &&" in p
assert "R9RestoreMonoBeforePresent(" in p
assert "R9NoteStereoDrawWithoutMonoBackup();" in r30
assert "R9MonoElisionArmed" not in s
print("PASS R26 gap-only third mono Draw and partial Clear removal")
print("PASS full Clear reseed, original stereo and guarded mono restore retained")
print("Quest HMD rendering and FPS UNTESTED")
