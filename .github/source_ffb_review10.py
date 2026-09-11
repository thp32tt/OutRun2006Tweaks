from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
VERIFY = 'tools/verify_wheel_ffb_current.py'
FFB = 'src/hooks_wheel_ffb.cpp'
DYN = 'src/hooks_wheel_vehicle_dynamics.hpp'


def read(rel):
    return (ROOT / rel).read_text(encoding='utf-8')


def write(rel, text):
    (ROOT / rel).write_text(text, encoding='utf-8')


def replace_once(rel, old, new):
    text = read(rel)
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{rel}: expected exactly one match, got {count}: {old[:160]!r}')
    write(rel, text.replace(old, new, 1))


def add_verify(line):
    marker = "print('CURRENT WHEEL FFB STRUCTURE VERIFIED; run verify_wheel_ffb_math.py for numerical tests')"
    text = read(VERIFY)
    if line in text:
        return
    if marker not in text:
        raise SystemExit('verifier final marker not found')
    write(VERIFY, text.replace(marker, line + '\n' + marker, 1))


def must(rel, needle):
    if needle not in read(rel):
        raise SystemExit(f'{rel}: missing expected post-review marker: {needle!r}')


def verify():
    # Deliberately source-only: do not invoke CMake, MSBuild, cl.exe, or the
    # compiled numerical harness during daytime review rounds.
    subprocess.run([sys.executable, VERIFY], cwd=ROOT, check=True)


def commit(message, *paths):
    subprocess.run(['git', 'add', *paths], cwd=ROOT, check=True)
    subprocess.run(['git', 'commit', '-m', message + ' [skip ci]'], cwd=ROOT, check=True)


# Review 1: Physics mode must never collapse to a 15% steering fallback when
# basis calibration is delayed or impossible on a particular game state/car.
replace_once(
    FFB,
    '            const float physicsFallback = naturalSatTorque * 0.15f;\n',
    '            const float physicsFallback = naturalSatTorque;\n')
replace_once(
    VERIFY,
    "req(ffb, 'const float physicsFallback = naturalSatTorque * 0.15f;', 'continuous Natural-to-Physics SAT handoff')",
    "req(ffb, 'const float physicsFallback = naturalSatTorque;', 'full Natural SAT fallback until Physics SAT is ready')")
add_verify("forbid(ffb, 'naturalSatTorque * 0.15f', 'Physics mode never falls back to weak 15 percent steering')")
verify()
commit('ffb review 01: keep full Natural SAT fallback', FFB, VERIFY)


# Review 2: stale/invalid motion samples must not remain authoritative merely
# because calibration succeeded earlier. Fall back to Natural SAT immediately.
replace_once(
    FFB,
    '            if (vehicleDynamics_.calibrated())\n            {\n',
    '            if (vehicleDynamics_.calibrated() && vehicleDynamics_.sampleValid())\n            {\n')
replace_once(
    FFB,
    '            const float physicsMix = vehicleDynamics_.activationBlend();\n',
    '            const float physicsMix = vehicleDynamics_.sampleValid()\n                ? vehicleDynamics_.activationBlend()\n                : 0.0f;\n')
add_verify("req(ffb, 'vehicleDynamics_.calibrated() && vehicleDynamics_.sampleValid()', 'Physics SAT requires a current valid motion sample')")
add_verify("req(ffb, 'const float physicsMix = vehicleDynamics_.sampleValid()', 'invalid dynamics falls back to Natural SAT immediately')")
verify()
commit('ffb review 02: reject stale Physics SAT samples', FFB, VERIFY)


# Review 3: ordinary F11/menu/focus transitions should clear derivatives but
# preserve the already-proven matrix basis. Recalibrating mid-corner can leave
# Physics SAT unavailable for too long.
replace_once(
    DYN,
    '    void update(\n',
    '''    void reset_dynamic()\n    {\n        // Preserve the proven matrix basis while dropping every time-domain\n        // sample. Menu/focus/F11 transitions must not force another straight-\n        // line calibration before Physics SAT can return.\n        positionValid_ = false;\n        headingValid_ = false;\n        prevPosition_ = D3DVECTOR{};\n        positionStep_ = 0.0f;\n        spdLen_ = 0.0f;\n        spdCorrelation_ = 0.0f;\n        clear_dynamic_state();\n    }\n\n    void update(\n''')
replace_once(FFB, '            vehicleDynamics_.reset();\n', '            vehicleDynamics_.reset_dynamic();\n')
add_verify("req(dyn, 'void reset_dynamic()', 'dynamic reset preserves calibrated vehicle basis')")
add_verify("req(ffb, 'vehicleDynamics_.reset_dynamic();', 'engine transitions preserve dynamics calibration')")
verify()
commit('ffb review 03: preserve Physics SAT calibration across menus', FFB, DYN, VERIFY)


# Review 4: if early straight-line samples are ambiguous/noisy, an ever-growing
# average can poison calibration for the whole session. Retry with a fresh window.
replace_once(
    DYN,
    '''                    if (bestScore >= 0.85f && calibrationConfidence_ >= 0.25f)\n                    {\n                        forwardAxis_ = zScore >= xScore ? 3 : 1;\n                        const float signedScore = forwardAxis_ == 3\n                            ? calibrationSignedZ_\n                            : calibrationSignedX_;\n                        forwardSign_ = signedScore >= 0.0f ? 1.0f : -1.0f;\n                        calibrated_ = true;\n                        clear_dynamic_state();\n                    }\n''',
    '''                    if (bestScore >= 0.85f && calibrationConfidence_ >= 0.25f)\n                    {\n                        forwardAxis_ = zScore >= xScore ? 3 : 1;\n                        const float signedScore = forwardAxis_ == 3\n                            ? calibrationSignedZ_\n                            : calibrationSignedX_;\n                        forwardSign_ = signedScore >= 0.0f ? 1.0f : -1.0f;\n                        calibrated_ = true;\n                        clear_dynamic_state();\n                    }\n                    else if (calibrationSamples_ >= CalibrationSamplesRequired * 4)\n                    {\n                        // Do not let a noisy launch poison the basis average for\n                        // the rest of the race. Retry from a fresh straight-line\n                        // window while Natural SAT remains fully available.\n                        calibrationSamples_ = 0;\n                        calibrationScoreX_ = 0.0f;\n                        calibrationScoreZ_ = 0.0f;\n                        calibrationSignedX_ = 0.0f;\n                        calibrationSignedZ_ = 0.0f;\n                        calibrationConfidence_ = 0.0f;\n                    }\n''')
add_verify("req(dyn, 'calibrationSamples_ >= CalibrationSamplesRequired * 4', 'ambiguous basis calibration retries with a fresh window')")
verify()
commit('ffb review 04: retry ambiguous vehicle basis calibration', DYN, VERIFY)


# Review 5: collision/gear events may be immediate, but they must not make the
# entire sustained steering force bypass its DD-wheel slew limiter.
replace_once(
    FFB,
    '''            const bool eventActive =\n                crashImpulseTimer_ > CrashCooldownFrames || gearShiftTimer_ > 0;\n            float events = update_event_force();\n\n            // d-b-c-e toolkit v0.8.0 ordering: gain/invert are part of the\n            // signal before soft saturation and slew. This prevents high gain\n            // or inversion from disagreeing with the slew limiter's last value.\n            float total = (structural + events) * outputStrength;\n            if (Settings::WheelFFBInvertForce)\n                total = -total;\n\n            total *= warmupScale * recreateScale;\n            if (!std::isfinite(total))\n                total = 0.0f;\n\n            // Preserve ordinary SAT linearly; bend only near the force cap.\n            const float compressed = WheelFFBMath::soft_saturate(total);\n\n            LONG structuralLevel =\n                static_cast<LONG>(compressed * static_cast<float>(DI_FFNOMINALMAX));\n''',
    '''            float events = update_event_force();\n\n            // Sustained steering and short events have different timing needs.\n            // Keep SAT/spring/damper on the DD-safe slew path while allowing a\n            // crash or gear thunk to arrive promptly without releasing that\n            // slew limiter for the whole steering signal.\n            const float forceDirection = Settings::WheelFFBInvertForce ? -1.0f : 1.0f;\n            const float outputRamp = warmupScale * recreateScale;\n            float total = structural * outputStrength * forceDirection * outputRamp;\n            float eventOutput = events * outputStrength * forceDirection * outputRamp;\n            if (!std::isfinite(total))\n                total = 0.0f;\n            if (!std::isfinite(eventOutput))\n                eventOutput = 0.0f;\n\n            // Preserve ordinary SAT linearly; bend only near the force cap.\n            const float compressed = WheelFFBMath::soft_saturate(total);\n            const float eventCompressed = WheelFFBMath::soft_saturate(eventOutput);\n\n            LONG structuralLevel =\n                static_cast<LONG>(compressed * static_cast<float>(DI_FFNOMINALMAX));\n            const LONG eventLevel = static_cast<LONG>(\n                eventCompressed * static_cast<float>(DI_FFNOMINALMAX));\n''')
replace_once(
    FFB,
    '''            const LONG structuralDelta = structuralLevel - prevStructuralLevel_;\n            const bool bypassSlew = eventActive;\n\n            if (std::abs(structuralDelta) > appliedMaxSlew && !bypassSlew)\n''',
    '''            const LONG structuralDelta = structuralLevel - prevStructuralLevel_;\n\n            if (std::abs(structuralDelta) > appliedMaxSlew)\n''')
replace_once(
    FFB,
    '''            const LONG level = std::clamp(\n                structuralLevel +\n                    static_cast<LONG>(fallbackVibration * static_cast<float>(DI_FFNOMINALMAX)),\n                -static_cast<LONG>(DI_FFNOMINALMAX),\n                static_cast<LONG>(DI_FFNOMINALMAX));\n\n            if (std::abs(level - prevConstantLevel_) > 15 || bypassSlew ||\n''',
    '''            const LONG level = std::clamp(\n                structuralLevel + eventLevel +\n                    static_cast<LONG>(fallbackVibration * static_cast<float>(DI_FFNOMINALMAX)),\n                -static_cast<LONG>(DI_FFNOMINALMAX),\n                static_cast<LONG>(DI_FFNOMINALMAX));\n\n            if (std::abs(level - prevConstantLevel_) > 15 || eventLevel != 0 ||\n''')
replace_once(
    FFB,
    'structural={} event={} preClip={} postClip={} postSlew={} diRequested={}',
    'structural={} event={} structuralPreClip={} structuralPostClip={} eventPostClip={} postSlew={} diRequested={}')
replace_once(
    FFB,
    '                    structural, events, total, compressed, structuralLevel, level, prevConstantLevel_,\n',
    '                    structural, events, total, compressed, eventCompressed, structuralLevel, level, prevConstantLevel_,\n')
add_verify("forbid(ffb, 'bypassSlew', 'events never bypass sustained steering slew')")
add_verify("req(ffb, 'const LONG eventLevel = static_cast<LONG>', 'events have an independent immediate output path')")
verify()
commit('ffb review 05: separate event impulses from steering slew', FFB, VERIFY)


# Review 6: Reverse Spring must work identically when GUID_Spring is unavailable
# and the engine falls back to software spring torque through ConstantForce.
replace_once(
    FFB,
    '''            const float softwareSpring =\n                springEffect_\n                    ? 0.0f\n                    : -steer * springStrength;\n''',
    '''            const float softwareSpringSign = Settings::WheelFFBInvertSpring\n                ? 1.0f : -1.0f;\n            const float softwareSpring =\n                springEffect_\n                    ? 0.0f\n                    : steer * softwareSpringSign * springStrength;\n''')
add_verify("req(ffb, 'const float softwareSpringSign = Settings::WheelFFBInvertSpring', 'Reverse Spring also controls software fallback')")
verify()
commit('ffb review 06: align software spring inversion semantics', FFB, VERIFY)


# Review 7: never disable the wheel driver's autocenter unless its previous value
# was successfully captured. Otherwise a failed GetProperty could leave the base
# altered after exit because there is no trustworthy value to restore.
replace_once(
    FFB,
    '''            autocenterRestoreKnown_ = SUCCEEDED(device_->GetProperty(DIPROP_AUTOCENTER, &autocenter.diph));\n            if (autocenterRestoreKnown_) originalAutocenter_ = autocenter.dwData;\n            autocenter.dwData = DIPROPAUTOCENTER_OFF;\n            hr = device_->SetProperty(DIPROP_AUTOCENTER, &autocenter.diph);\n            if (FAILED(hr))\n                spdlog::warn("WheelFFB: disabling driver autocenter failed (0x{:08X})", (unsigned)hr);\n            else\n                driverAutocenterDisabled_ = true;\n''',
    '''            autocenterRestoreKnown_ = SUCCEEDED(\n                device_->GetProperty(DIPROP_AUTOCENTER, &autocenter.diph));\n            if (autocenterRestoreKnown_)\n            {\n                originalAutocenter_ = autocenter.dwData;\n                autocenter.dwData = DIPROPAUTOCENTER_OFF;\n                hr = device_->SetProperty(DIPROP_AUTOCENTER, &autocenter.diph);\n                if (FAILED(hr))\n                    spdlog::warn("WheelFFB: disabling driver autocenter failed (0x{:08X})", (unsigned)hr);\n                else\n                    driverAutocenterDisabled_ = true;\n            }\n            else\n            {\n                spdlog::warn(\n                    "WheelFFB: driver autocenter state could not be read; leaving it unchanged for safe restoration semantics");\n            }\n''')
add_verify("req(ffb, 'driver autocenter state could not be read; leaving it unchanged', 'unknown driver autocenter state is never mutated')")
verify()
commit('ffb review 07: preserve unknown driver autocenter state', FFB, VERIFY)


# Review 8: weight transfer currently uses a delayed raw speed difference. Filter
# that acceleration sample so braking/acceleration load feels like weight transfer
# instead of one-frame speed quantization in SAT magnitude.
replace_once(
    FFB,
    '''            float loadMod = 1.0f;\n            if (speedHistoryIndex_ > 6)\n            {\n                const float oldSpeed =\n                    speedHistory_[(speedHistoryIndex_ - 6) % SpeedHistoryCount];\n                const float longAccel = (speed - oldSpeed) * 5.0f;\n                loadMod = 1.0f + std::clamp(\n                    -longAccel * static_cast<float>(Settings::WheelFFBWeightTransfer),\n                    -0.06f, 0.08f);\n            }\n''',
    '''            float loadMod = 1.0f;\n            if (speedHistoryIndex_ > 6)\n            {\n                const float oldSpeed =\n                    speedHistory_[(speedHistoryIndex_ - 6) % SpeedHistoryCount];\n                const float longAccelSample = (speed - oldSpeed) * 5.0f;\n                if (std::isfinite(longAccelSample))\n                    smoothedLongAccel_ +=\n                        (longAccelSample - smoothedLongAccel_) * 0.25f;\n                const float configuredWeightTransfer =\n                    static_cast<float>(Settings::WheelFFBWeightTransfer);\n                const float weightTransfer = std::isfinite(configuredWeightTransfer)\n                    ? std::clamp(configuredWeightTransfer, 0.0f, 1.5f)\n                    : 0.0f;\n                loadMod = 1.0f + std::clamp(\n                    -smoothedLongAccel_ * weightTransfer, -0.06f, 0.08f);\n            }\n''')
replace_once(
    FFB,
    '        float smoothedLateral_ = 0.0f;\n        float prevSteer_ = 0.0f;\n',
    '        float smoothedLateral_ = 0.0f;\n        float smoothedLongAccel_ = 0.0f;\n        float prevSteer_ = 0.0f;\n')
replace_once(
    FFB,
    '            smoothedLateral_ = 0.0f;\n            prevSteer_ = 0.0f;\n',
    '            smoothedLateral_ = 0.0f;\n            smoothedLongAccel_ = 0.0f;\n            prevSteer_ = 0.0f;\n')
add_verify("req(ffb, 'smoothedLongAccel_ +=', 'weight-transfer acceleration is filtered')")
add_verify("req(ffb, 'std::clamp(configuredWeightTransfer, 0.0f, 1.5f)', 'weight-transfer setting is finite and bounded')")
verify()
commit('ffb review 08: smooth longitudinal weight transfer', FFB, VERIFY)


# Review 9: software road/slip vibration is an optional fallback and must never
# hard-clip away steering/event torque. Limit fallback vibration to remaining
# DirectInput headroom after the steering+event base is formed.
replace_once(
    FFB,
    '''            const LONG level = std::clamp(\n                structuralLevel + eventLevel +\n                    static_cast<LONG>(fallbackVibration * static_cast<float>(DI_FFNOMINALMAX)),\n                -static_cast<LONG>(DI_FFNOMINALMAX),\n                static_cast<LONG>(DI_FFNOMINALMAX));\n''',
    '''            const LONG baseSteeringLevel = std::clamp(\n                structuralLevel + eventLevel,\n                -static_cast<LONG>(DI_FFNOMINALMAX),\n                static_cast<LONG>(DI_FFNOMINALMAX));\n            const LONG vibrationRequested = static_cast<LONG>(\n                fallbackVibration * static_cast<float>(DI_FFNOMINALMAX));\n            const LONG vibrationHeadroom =\n                static_cast<LONG>(DI_FFNOMINALMAX) - std::abs(baseSteeringLevel);\n            const LONG vibrationLevel = std::clamp(\n                vibrationRequested, -vibrationHeadroom, vibrationHeadroom);\n            const LONG level = baseSteeringLevel + vibrationLevel;\n''')
add_verify("req(ffb, 'const LONG vibrationHeadroom =', 'software vibration cannot clip steering torque')")
add_verify("req(ffb, 'const LONG level = baseSteeringLevel + vibrationLevel;', 'fallback vibration uses only remaining output headroom')")
verify()
commit('ffb review 09: protect steering headroom from fallback vibration', FFB, VERIFY)


# Review 10: hardware sine frequency is generated by the wheel, but its envelope
# only refreshed at ~15 Hz. Sample the envelope at ~30 Hz for quicker surface and
# tire-scrub onset/release while remaining far inside the 250 ms effect lease.
replace_once(
    FFB,
    '            if (periodicsActive_ && (updateCounter_ % 4) == 0)\n',
    '            if (periodicsActive_ && (updateCounter_ % 2) == 0)\n')
add_verify("req(ffb, 'periodicsActive_ && (updateCounter_ % 2) == 0', 'hardware periodic envelopes update at about 30 Hz')")
verify()
commit('ffb review 10: improve periodic envelope response', FFB, VERIFY)

print('TEN SOURCE-ONLY FFB REVIEW ROUNDS COMPLETED')
