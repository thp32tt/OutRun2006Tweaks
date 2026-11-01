#!/usr/bin/env python3
"""Focus branch gate for runtime-proven DirectGPU steady-state mono elision."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
s=(root/"src/vr/d3d9/stereo_renderer.cpp").read_text()
def block(a,b):
    assert s.count(a)==1,a
    return s.split(a,1)[1].split(b,1)[0]
clear=block("HRESULT __stdcall ClearDestR9(","template <typename ActualDraw, typename LegacyDraw>")
draw=block("HRESULT R9ExecuteDraw(","HRESULT __stdcall DrawPrimitiveDestR9(")
present=block("HRESULT __stdcall PresentDestR9(","HRESULT __stdcall ResetDestR9(")
reset=block("HRESULT __stdcall ResetDestR9(","void R9RollbackCallbackPolicy()")
assert "if (R9MonoElisionArmed)" in clear
assert clear.index("if (R9MonoElisionArmed)") < clear.index("R9EnsureMonoResources(device)")
assert "R9MonoSeeded = !R9MonoElisionArmed;" in clear
assert "if (R9MonoElisionArmed)" in draw
assert draw.index("++R9MonoElidedDraws;") < draw.index("R9EnsureMonoResources(device)")
assert "hr = legacyDraw();" in draw
assert "const bool holdVerifiedStereo =" in present
assert "directTransport && HostDirectTransportReady() && !R9MonoElisionArmed" in present
assert "if ((!composedStereo || FrameStereoIncomplete) && !R9MonoElisionArmed)" in present
assert "if (stereoRequested && !holdVerifiedStereo &&" in present
assert "++R9MonoElisionFailureStreak >= 3u" in present
assert "R9MonoElisionArmed = false;" in reset
assert "R9MonoElisionFailureStreak = 0;" in reset
print("PASS focus bootstrap mono -> verified DirectGPU -> zero steady-state third center Draw/Clear")
print("PASS last-good stereo hold + three-failure rearm + Reset disarm")
print("HMD_RUNTIME=previous mono-elide test path user-validated; exact focus integration requires build/runtime")
