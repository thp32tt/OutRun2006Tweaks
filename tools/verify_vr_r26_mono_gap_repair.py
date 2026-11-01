#!/usr/bin/env python3
"""R26+HUD bootstrap mono-gap regression gates under verified DirectGPU full elision."""
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

# Full mono elision owns steady state; the older gap skip remains a bootstrap
# optimization for a shadow already made unrestorable by an R30/R29 two-eye draw.
assert "if (R9MonoElisionArmed)" in d
assert "else if (R9MonoBackupGap)" in d
skipped=d.split("else if (R9MonoBackupGap)",1)[1].split("else",1)[0]
assert "++R9MonoGapSkippedDraws;" in skipped
assert "R9ReplayMonoDraw(" not in skipped
assert d.index("if (R9MonoElisionArmed)") < d.index("else if (R9MonoBackupGap)")
assert d.index("else if (R9MonoBackupGap)") < d.index("R9EnsureMonoResources(device)")
assert "R9ReplayMonoDraw(device, actualDraw, monoHr)" in d
assert "hr = legacyDraw();" in d and "if (FrameStereoIncomplete)" in d

# Partial clears of an unrestorable bootstrap shadow remain skipped; a full
# clear can reseed only before elision. Once armed, no mono clear is issued.
assert "const bool monoCanReseed = full &&" in c
assert "(flags & D3DCLEAR_TARGET) != 0 && !FrameStereoIncomplete;" in c
assert "if (R9MonoElisionArmed)" in c
assert "else if (R9MonoBackupGap && !monoCanReseed)" in c
assert c.index("if (R9MonoElisionArmed)") < c.index("else if (R9MonoBackupGap && !monoCanReseed)")
assert c.index("else if (R9MonoBackupGap && !monoCanReseed)") < c.index("R9EnsureMonoResources(device)")
assert "++R9MonoGapSkippedClears;" in c
assert "monoOk = R9ReplayMonoClear(" in c
assert "R9MonoSeeded = !R9MonoElisionArmed;" in c
assert "R9MonoBackupGap = R9MonoElisionArmed;" in c

# Mono restore is bootstrap-only; steady state holds the last verified stereo.
assert "const bool holdVerifiedStereo =" in p
assert "if ((!composedStereo || FrameStereoIncomplete) && !R9MonoElisionArmed)" in p
assert "if (R9MonoSeeded && !R9MonoBackupGap &&" in p
assert "R9RestoreMonoBeforePresent(" in p
assert "R9NoteStereoDrawWithoutMonoBackup();" in r30
assert "R9MonoElisionArmed" in s
print("PASS bootstrap gap-only third mono Draw/partial Clear removal retained under full elision")
print("PASS full Clear bootstrap reseed, stereo path and guarded bootstrap mono restore retained")

# Quiet probe now reports both narrow gap skip and steady-state full elision.
assert "void R9MaybeLogQuietGapEfficiency(bool stereoRequested)" in s
assert "R9MaybeLogQuietGapEfficiency(stereoRequested);" in p
assert "VR R26 MONO-ELIDE SAMPLE:" in s
assert "monoElidedDraw={}" in s
assert "gapFramesWithoutLaterSkip=" in s
assert "candidateSkipSharePct={:.2f}" in s
assert "now - R9GapProbeLastMs < 10000" in s
assert "if (!stereoRequested)" in s
print("PASS quiet 10s combined gap/full-elision efficiency probe")
print("Quest HMD rendering and FPS USER_VALIDATION_REQUIRED")
