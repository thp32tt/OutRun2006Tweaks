#!/usr/bin/env python3
"""Verify safe bootstrap + gap-skip + verified DirectGPU full mono elision."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
s = (root / 'src/vr/d3d9/stereo_renderer.cpp').read_text()
r13 = (root / 'src/vr/d3d9/stereo_renderer_r13.cpp').read_text()
launcher = (root / 'tools/vr_perf_quiet/Run-VRPerfQuiet.ps1').read_text()
ini = (root / 'OutRun2006Tweaks.ini').read_text()
def block(start, stop):
    assert s.count(start) == 1, start
    return s.split(start,1)[1].split(stop,1)[0]
clear = block('HRESULT __stdcall ClearDestR9(', 'template <typename ActualDraw, typename LegacyDraw>')
draw = block('HRESULT R9ExecuteDraw(', 'HRESULT __stdcall DrawPrimitiveDestR9(')
present = block('HRESULT __stdcall PresentDestR9(', 'HRESULT __stdcall ResetDestR9(')
reset = block('HRESULT __stdcall ResetDestR9(', 'void R9RollbackCallbackPolicy()')
assert 'if (R9MonoElisionArmed)' in clear
assert clear.index('if (R9MonoElisionArmed)') < clear.index('else if (R9MonoBackupGap && !monoCanReseed)')
assert clear.index('else if (R9MonoBackupGap && !monoCanReseed)') < clear.index('R9EnsureMonoResources(device)')
assert 'R9MonoSeeded = !R9MonoElisionArmed;' in clear
assert 'R9MonoBackupGap = R9MonoElisionArmed;' in clear
assert 'if (R9MonoElisionArmed)' in draw
assert draw.index('++R9MonoElidedDraws;') < draw.index('else if (R9MonoBackupGap)')
assert draw.index('else if (R9MonoBackupGap)') < draw.index('R9EnsureMonoResources(device)')
assert 'hr = legacyDraw();' in draw
assert 'if (FrameStereoIncomplete)' in draw and 'return actualDraw();' in draw
assert 'if (directTransport && HostDirectTransportReady() && !R9MonoElisionArmed)' in present
assert 'const bool holdVerifiedStereo =' in present
assert 'if ((!composedStereo || FrameStereoIncomplete) && !R9MonoElisionArmed)' in present
assert 'if (stereoRequested && !holdVerifiedStereo &&' in present
assert 'if (!holdVerifiedStereo)' in present
assert '++R9MonoElisionFailureStreak >= 3u' in present
assert 'R9MonoElisionArmed = false;' in reset
assert 'R9MonoElisionFailureStreak = 0;' in reset
assert 'R13DrawMonoShadowOnce' in r13 and 'if (R9MonoSeeded && !R9MonoBackupGap' in r13
assert "OUTRUN_VR_FULL_TRACE = '0'" in launcher
assert "OUTRUN_VR_R23_PIXEL_PROBE = '0'" in launcher
assert "'-DirectGpuOnly=true'" in launcher
assert "'-Graphics.ReflectionResolution=512'" in launcher
assert "'-Graphics.ReflectionUpdateRate=0.25'" in launcher
assert "'-Graphics.DisableVehicleLODs=true'" in launcher
assert 'ReflectionResolution = 512' in ini
assert 'ReflectionUpdateRate = 0.25' in ini
assert 'DisableVehicleLODs = true' in ini
assert 'VR R26 MONO-ELIDE SAMPLE:' in s
print('PASS bootstrap mono + warmup gap skip -> verified DirectGPU -> zero steady-state center-mono Draw/Clear')
print('PASS last-good stereo hold, 3-failure safety rearm, reset disarm')
print('PASS quality profile 512 / reflection rate 0.25 / vehicle LOD disabled')
print('HMD_RUNTIME=USER_VALIDATION_REQUIRED')
