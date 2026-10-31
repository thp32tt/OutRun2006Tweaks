#!/usr/bin/env python3
"""Source structural gate: remove the steady-state third mono draw without a cold-start white screen."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
s = (root / 'src/vr/d3d9/stereo_renderer.cpp').read_text()
r13 = (root / 'src/vr/d3d9/stereo_renderer_r13.cpp').read_text()
quiet = (root / 'src/vr/settings.cpp').read_text()
launcher = (root / 'tools/vr_perf_quiet/Run-VRPerfQuiet.ps1').read_text()
def block(start,stop):
 assert s.count(start) == 1, start
 return s.split(start,1)[1].split(stop,1)[0]
clear = block('HRESULT __stdcall ClearDestR9(', 'template <typename ActualDraw, typename LegacyDraw>')
draw = block('HRESULT R9ExecuteDraw(', 'HRESULT __stdcall DrawPrimitiveDestR9(')
present = block('HRESULT __stdcall PresentDestR9(', 'HRESULT __stdcall ResetDestR9(')
reset = block('HRESULT __stdcall ResetDestR9(', 'void R9RollbackCallbackPolicy()')
assert 'if (R9MonoElisionArmed)' in clear
assert clear.index('if (R9MonoElisionArmed)') < clear.index('R9EnsureMonoResources(device)')
assert clear.index('R9EnsureMonoResources(device)') < clear.index('R9ReplayMonoClear(')
assert 'R9MonoSeeded = !R9MonoElisionArmed;' in clear
assert 'R9MonoBackupGap = R9MonoElisionArmed;' in clear
assert 'if (R9MonoElisionArmed)' in draw
assert draw.index('++R9MonoElidedDraws;') < draw.index('R9EnsureMonoResources(device)')
assert draw.index('R9EnsureMonoResources(device)') < draw.index('R9ReplayMonoDraw(')
assert 'hr = legacyDraw();' in draw # left/right stereo path remains intact
assert 'if (FrameStereoIncomplete)' in draw and 'return actualDraw();' in draw
assert 'if (directTransport && HostDirectTransportReady() && !R9MonoElisionArmed)' in present
assert 'if ((!composedStereo || FrameStereoIncomplete) && !R9MonoElisionArmed)' in present
assert 'const bool holdVerifiedStereo =' in present
assert 'if (stereoRequested && !holdVerifiedStereo &&' in present
assert 'if (!holdVerifiedStereo)' in present
assert 'if (!holdVerifiedStereo && (!directOnly || !stereoRequested || directTransport))' in present
assert '++R9MonoElisionFailureStreak >= 3u' in present
assert 'R9MonoElisionArmed = false;' in reset
assert 'R9MonoElisionFailureStreak = 0;' in reset
assert 'R13DrawMonoShadowOnce' in r13 and 'if (R9MonoSeeded && !R9MonoBackupGap' in r13
assert 'Setting<bool> VRTelemetry{ "VR", "Telemetry", false,' in quiet
assert "OUTRUN_VR_FULL_TRACE = '0'" in launcher
assert "OUTRUN_VR_R23_PIXEL_PROBE = '0'" in launcher
print('PASS cold-start safe mono -> live verified DirectGPU -> zero extra mono Draw/Clear')
print('PASS incomplete-frame last-good projection hold, recovery after 3 failures, reset disarms')
print('PASS legacy R13 fallback preserved, telemetry quiet and full-trace off')
print('HMD_RUNTIME=UNTESTED')
