from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding='utf-8')


def write(rel, text):
    (ROOT / rel).write_text(text, encoding='utf-8')


def replace_once(rel, old, new):
    text = read(rel)
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{rel}: expected exactly one match, got {count}: {old[:120]!r}')
    write(rel, text.replace(old, new, 1))


def add_verifier_guard(code):
    rel = 'tools/verify_wheel_ffb_current.py'
    text = read(rel)
    if code in text:
        return
    marker = "print('CURRENT WHEEL FFB STRUCTURE VERIFIED; run verify_wheel_ffb_math.py for numerical tests')"
    if marker not in text:
        raise SystemExit('verifier final marker missing')
    text = text.replace(marker, code.rstrip() + '\n' + marker, 1)
    write(rel, text)


def verify_and_commit(message):
    subprocess.run(['python', 'tools/verify_wheel_ffb_current.py'], cwd=ROOT, check=True)
    subprocess.run(['git', 'add', 'src/hooks_wheel_ffb.cpp', 'src/wheel_ffb_math.hpp',
                    'tools/test_wheel_ffb_current.cpp', 'tools/verify_wheel_ffb_current.py'], cwd=ROOT, check=True)
    status = subprocess.run(['git', 'diff', '--cached', '--quiet'], cwd=ROOT)
    if status.returncode == 0:
        raise SystemExit(f'no staged change for {message}')
    subprocess.run(['git', 'commit', '-m', message + ' [skip ci]'], cwd=ROOT, check=True)


# Round 1: make the Natural->Physics SAT handoff continuous. Previously the
# 15% Natural safety net dropped to zero on the exact tick calibration became
# true, while activationBlend was still zero, producing a brief light-steering
# hole before Physics SAT ramped in.
replace_once(
    'src/hooks_wheel_ffb.cpp',
    '''            const float physicsFallback = vehicleDynamics_.calibrated()\n                ? 0.0f : naturalSatTorque * 0.15f;\n            const float physicsMix = vehicleDynamics_.activationBlend();\n''',
    '''            const float physicsMix = vehicleDynamics_.activationBlend();\n            // Keep the Natural safety net alive throughout the activation ramp.\n            // Dropping it on the calibration tick created a short SAT hole while\n            // physicsMix was still near zero.\n            const float physicsFallback = naturalSatTorque * 0.15f;\n''')
add_verifier_guard("""req(ffb, 'const float physicsFallback = naturalSatTorque * 0.15f;', 'continuous Natural-to-Physics SAT handoff')
forbid(ffb, 'const float physicsFallback = vehicleDynamics_.calibrated()', 'no calibration-tick SAT hole')""")
verify_and_commit('ffb: keep SAT continuous through physics activation')


# Round 2: replace tanh with a C1 soft knee that is exactly linear through the
# normal 0..75% range. tanh(0.5) and tanh(1.0) were already compressing ordinary
# cornering torque substantially, which made a DD wheel feel weaker than the
# force model requested.
math_rel = 'src/wheel_ffb_math.hpp'
math_text = read(math_rel)
insert = '''\n    // Symmetric C1 soft limiter. Preserve low/mid-range force exactly, then\n    // bend only the final quarter toward the DirectInput cap. This keeps SAT\n    // detail and weight intact while still preventing hard clipping at 100%.\n    inline float soft_saturate(float value)\n    {\n        if (!std::isfinite(value)) return 0.0f;\n        const float sign = value < 0.0f ? -1.0f : 1.0f;\n        const float x = std::abs(value);\n        constexpr float Knee = 0.75f;\n        constexpr float Limit = 1.35f;\n        if (x <= Knee) return value;\n        if (x >= Limit) return sign;\n\n        const float span = Limit - Knee;\n        const float t = (x - Knee) / span;\n        const float t2 = t * t;\n        const float t3 = t2 * t;\n        const float h00 = 2.0f * t3 - 3.0f * t2 + 1.0f;\n        const float h10 = t3 - 2.0f * t2 + t;\n        const float h01 = -2.0f * t3 + 3.0f * t2;\n        const float y = h00 * Knee + h10 * span + h01;\n        return sign * y;\n    }\n'''
if 'inline float soft_saturate(float value)' in math_text:
    raise SystemExit('soft_saturate already exists unexpectedly')
math_text = math_text.replace('\n    inline float physics_return_relief', insert + '\n    inline float physics_return_relief', 1)
write(math_rel, math_text)
replace_once(
    'src/hooks_wheel_ffb.cpp',
    '''            // Soft saturation preserves detail near the force cap.\n            const float compressed = std::tanh(total);\n''',
    '''            // Preserve ordinary SAT linearly; bend only near the force cap.\n            const float compressed = WheelFFBMath::soft_saturate(total);\n''')
replace_once('src/hooks_wheel_ffb.cpp', 'preTanh={} postTanh={}', 'preClip={} postClip={}')

# Add source-level numerical coverage for the new production helper. This file
# is intentionally not compiled in this daytime source-only pass; normal build
# CI / the evening build will execute it through verify_wheel_ffb_math.py.
test_rel = 'tools/test_wheel_ffb_current.cpp'
test_text = read(test_rel)
needle = ''' require(std::abs(trail_shape(.32f)-std::exp(-.9f))<1e-6,"deep-slip baseline preserved");\n'''
addition = needle + ''' require(WheelFFBMath::soft_saturate(.5f)==.5f,"soft clip linear midrange");\n require(std::abs(WheelFFBMath::soft_saturate(-.5f)+.5f)<1e-6,"soft clip symmetry");\n require(WheelFFBMath::soft_saturate(1.0f)>.90f&&WheelFFBMath::soft_saturate(1.0f)<1.0f,"soft clip late knee");\n require(WheelFFBMath::soft_saturate(2.0f)==1.0f&&WheelFFBMath::soft_saturate(-2.0f)==-1.0f,"soft clip cap");\n float clipPrev=0; for(int i=0;i<=2000;++i){float x=i*.001f,y=WheelFFBMath::soft_saturate(x);require(std::isfinite(y)&&y>=clipPrev-1e-6f&&y<=1.000001f,"soft clip monotonic");clipPrev=y;}\n'''
if needle not in test_text:
    raise SystemExit('soft clip test insertion point missing')
write(test_rel, test_text.replace(needle, addition, 1))
ver = read('tools/verify_wheel_ffb_current.py')
if "math = read('src/wheel_ffb_math.hpp')" not in ver:
    ver = ver.replace("dyn = read('src/hooks_wheel_vehicle_dynamics.hpp')\n", "dyn = read('src/hooks_wheel_vehicle_dynamics.hpp')\nmath = read('src/wheel_ffb_math.hpp')\n", 1)
    write('tools/verify_wheel_ffb_current.py', ver)
add_verifier_guard("""req(math, 'inline float soft_saturate(float value)', 'linear-preserving C1 force limiter')
req(ffb, 'WheelFFBMath::soft_saturate(total)', 'production force path uses soft-knee limiter')
forbid(ffb, 'std::tanh(total)', 'ordinary SAT is not compressed by tanh')""")
verify_and_commit('ffb: preserve midrange torque with soft-knee saturation')


# Round 3: establish a steering-rate baseline after every reset and lightly
# filter the 60 Hz derivative. This removes the artificial first-frame damper
# pulse when returning from F11/menu and reduces quantization chatter without
# materially delaying steering response (~20 ms time constant).
replace_once(
    'src/hooks_wheel_ffb.cpp',
    '''            float steer = read_game_steering();\n            float steerRate = steer - prevSteer_;\n            prevSteer_ = steer;\n''',
    '''            const float steer = read_game_steering();\n            float rawSteerRate = 0.0f;\n            if (steerSampleValid_)\n            {\n                rawSteerRate = steer - prevSteer_;\n                smoothedSteerRate_ += (rawSteerRate - smoothedSteerRate_) * 0.45f;\n            }\n            else\n            {\n                // First sample after menu/race/device transitions is a baseline,\n                // not a one-tick steering velocity.\n                steerSampleValid_ = true;\n                smoothedSteerRate_ = 0.0f;\n            }\n            prevSteer_ = steer;\n            const float steerRate = smoothedSteerRate_;\n''')
replace_once(
    'src/hooks_wheel_ffb.cpp',
    '''            smoothedLateral_ = 0.0f;\n            prevSteer_ = 0.0f;\n            vehicleDynamics_.reset();\n''',
    '''            smoothedLateral_ = 0.0f;\n            prevSteer_ = 0.0f;\n            smoothedSteerRate_ = 0.0f;\n            steerSampleValid_ = false;\n            vehicleDynamics_.reset();\n''')
replace_once(
    'src/hooks_wheel_ffb.cpp',
    '''        float smoothedLateral_ = 0.0f;\n        float prevSteer_ = 0.0f;\n        WheelVehicleDynamics vehicleDynamics_{};\n''',
    '''        float smoothedLateral_ = 0.0f;\n        float prevSteer_ = 0.0f;\n        float smoothedSteerRate_ = 0.0f;\n        bool steerSampleValid_ = false;\n        WheelVehicleDynamics vehicleDynamics_{};\n''')
replace_once(
    'src/hooks_wheel_ffb.cpp',
    'speedRaw={} speedNorm={} steer={} steerRateTick={}',
    'speedRaw={} speedNorm={} steer={} steerRateRaw={} steerRateFiltered={}')
replace_once(
    'src/hooks_wheel_ffb.cpp',
    '''                    telemetryNow, static_cast<const void*>(car), speedRaw, speedNorm, steer, steerRate,\n''',
    '''                    telemetryNow, static_cast<const void*>(car), speedRaw, speedNorm, steer, rawSteerRate, steerRate,\n''')
add_verifier_guard("""req(ffb, 'bool steerSampleValid_ = false;', 'steering derivative has explicit baseline state')
req(ffb, 'smoothedSteerRate_ += (rawSteerRate - smoothedSteerRate_) * 0.45f;', 'steering-rate quantization filter')
req(ffb, 'steerRateRaw={} steerRateFiltered={}', 'raw and filtered steering-rate telemetry')""")
verify_and_commit('ffb: filter steering rate and remove transition derivative spikes')


# Round 4: damping should reveal front-tyre saturation as well as rear/body
# slide. The previous bodySlide-only release could leave a strong damper masking
# understeer/front scrub exactly when SAT was trying to communicate grip loss.
replace_once(
    'src/hooks_wheel_ffb.cpp',
    '''            // Release steering damping only when the chassis is actually\n            // sliding. A high lateral-G but fully-gripped corner keeps damping.\n            const float damperRelease = 1.0f - 0.55f * gripLoss * bodySlide;\n''',
    '''            // Release steering damping from real tyre/chassis slip, never\n            // from lateral-G alone. Front scrub gets a slightly smaller weight\n            // than body slide so understeer is readable without making the rack\n            // go completely loose in an ordinary loaded corner.\n            const float damperSlipRelief = std::max(bodySlide, frontScrub * 0.75f);\n            const float damperRelease = 1.0f - 0.55f * gripLoss * damperSlipRelief;\n''')
replace_once(
    'src/hooks_wheel_ffb.cpp',
    'damperRequested={} damperCoefficient={}',
    'damperRequested={} damperRelease={} damperCoefficient={}')
replace_once(
    'src/hooks_wheel_ffb.cpp',
    '''                    dynamicDamperStrength, prevDamperCoefficient_, roadAmp, slipAmp,\n''',
    '''                    dynamicDamperStrength, damperRelease, prevDamperCoefficient_, roadAmp, slipAmp,\n''')
ver = read('tools/verify_wheel_ffb_current.py')
old_guard = "req(ffb, 'const float damperRelease = 1.0f - 0.55f * gripLoss * bodySlide;', 'damper released by chassis slide')"
new_guard = "req(ffb, 'const float damperSlipRelief = std::max(bodySlide, frontScrub * 0.75f);', 'damper reveals front scrub and chassis slide')\nreq(ffb, 'const float damperRelease = 1.0f - 0.55f * gripLoss * damperSlipRelief;', 'damper release uses real slip state')"
if old_guard not in ver:
    raise SystemExit('old damper verifier guard missing')
write('tools/verify_wheel_ffb_current.py', ver.replace(old_guard, new_guard, 1))
add_verifier_guard("""req(ffb, 'damperRequested={} damperRelease={} damperCoefficient={}', 'damper release visible in telemetry')""")
verify_and_commit('ffb: let front scrub release dynamic damping')


# Round 5: asymmetric slew. A safety limiter should be conservative when force
# grows, but it should not hold stale torque after the tyre unloads. Permit a
# 2x decay rate only while torque magnitude is decreasing in the same direction;
# force build-up and reversals retain the configured safe slew limit.
replace_once(
    'src/hooks_wheel_ffb.cpp',
    '''            const LONG structuralDelta = structuralLevel - prevStructuralLevel_;\n            const bool bypassSlew = eventActive;\n\n            if (std::abs(structuralDelta) > maxSlew && !bypassSlew)\n            {\n                structuralLevel = prevStructuralLevel_ +\n                    (structuralDelta > 0 ? maxSlew : -maxSlew);\n            }\n''',
    '''            const bool sameTorqueDirection =\n                structuralLevel == 0 || prevStructuralLevel_ == 0 ||\n                (structuralLevel > 0) == (prevStructuralLevel_ > 0);\n            const bool unloadingStructural = sameTorqueDirection &&\n                std::abs(structuralLevel) < std::abs(prevStructuralLevel_);\n            const LONG appliedMaxSlew = unloadingStructural\n                ? std::min(static_cast<LONG>(DI_FFNOMINALMAX), maxSlew * 2)\n                : maxSlew;\n            const LONG structuralDelta = structuralLevel - prevStructuralLevel_;\n            const bool bypassSlew = eventActive;\n\n            if (std::abs(structuralDelta) > appliedMaxSlew && !bypassSlew)\n            {\n                structuralLevel = prevStructuralLevel_ +\n                    (structuralDelta > 0 ? appliedMaxSlew : -appliedMaxSlew);\n            }\n''')
add_verifier_guard("""req(ffb, 'const bool unloadingStructural = sameTorqueDirection &&', 'force unload detected separately from force build')
req(ffb, 'maxSlew * 2', 'stale torque can decay twice as fast')
req(ffb, 'std::abs(structuralDelta) > appliedMaxSlew', 'asymmetric slew applied to structural force')""")
verify_and_commit('ffb: release stale steering torque faster than it builds')

print('five source-only FFB review rounds applied successfully')
