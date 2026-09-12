from pathlib import Path


def read(p):
    return Path(p).read_text(encoding="utf-8")


def write(p, s):
    Path(p).write_text(s, encoding="utf-8", newline="\n")


def one(p, old, new):
    s = read(p)
    c = s.count(old)
    if c != 1:
        raise SystemExit(f"{p}: anchor count {c} for {old[:100]!r}")
    write(p, s.replace(old, new, 1))


def many(p, old, new, n):
    s = read(p)
    c = s.count(old)
    if c != n:
        raise SystemExit(f"{p}: anchor count {c}, expected {n}, for {old[:100]!r}")
    write(p, s.replace(old, new))


math = "src/wheel_ffb_math.hpp"
one(math,
    "        out.frequencyHz = 9.0f + 11.0f * out.rpmNorm;\n",
    "        // Keep the texture above the heavy low-frequency pulse region while\n"
    "        // remaining below the 60 Hz FFB loop Nyquist limit.\n"
    "        out.frequencyHz = 13.0f + 11.0f * out.rpmNorm;\n")

core = "src/hooks_wheel_ffb.cpp"
one(core,
'''    Setting<bool> WheelFFBEngineVibration{
        "WheelFFB", "EngineVibration", true,
        "Add a low-amplitude engine-speed haptic through the universal ConstantForce output path."
    };
''',
'''    Setting<bool> WheelFFBEngineVibration{
        "WheelFFB", "EngineVibration", false,
        "Optional low-amplitude engine-speed haptic through the universal ConstantForce output path."
    };
''')
one(core,
'''    Setting<float> WheelFFBEngineIdle{
        "WheelFFB", "EngineIdle", 0.06f,
        "Engine vibration strength (legacy EngineIdle key retained for compatibility).",
        Range<float>{ 0.0f, 0.5f }
    };
''',
'''    Setting<float> WheelFFBEngineIdle{
        "WheelFFB", "EngineIdle", 0.20f,
        "Engine vibration strength (legacy EngineIdle key retained for compatibility).",
        Range<float>{ 0.0f, 1.0f }
    };
''')

one(core,
'''            float engineAmp = 0.0f;
            float engineFreq = 0.0f;
            if (Settings::WheelFFBEngineVibration)
            {
                const auto engineTarget = WheelFFBMath::estimate_engine_haptics(
                    speedNorm, curGear, throttleNorm);
                const float rpmBlend = engineTarget.rpmNorm > smoothedEngineRpm_
                    ? 0.35f : 0.18f;
                smoothedEngineRpm_ +=
                    (engineTarget.rpmNorm - smoothedEngineRpm_) * rpmBlend;
                const float amplitudeScale = std::clamp(
                    0.45f + 0.40f * smoothedEngineRpm_ + 0.15f * throttleNorm,
                    0.0f, 1.0f);
                engineFreq = 9.0f + 11.0f * smoothedEngineRpm_;
                const float configuredEngineStrength =
                    static_cast<float>(Settings::WheelFFBEngineIdle);
                const float engineStrength = std::isfinite(configuredEngineStrength)
                    ? std::clamp(configuredEngineStrength, 0.0f, 0.5f)
                    : 0.0f;
                engineAmp = engineStrength * amplitudeScale * outputStrength;
            }
            else
            {
                smoothedEngineRpm_ = 0.0f;
                enginePhase_ = 0.0f;
            }
''',
'''            float engineAmp = 0.0f;
            float engineFreq = 0.0f;
            if (Settings::WheelFFBEngineVibration)
            {
                const auto engineTarget = WheelFFBMath::estimate_engine_haptics(
                    speedNorm, curGear, throttleNorm);
                const float rpmBlend = engineTarget.rpmNorm > smoothedEngineRpm_
                    ? 0.24f : 0.12f;
                smoothedEngineRpm_ +=
                    (engineTarget.rpmNorm - smoothedEngineRpm_) * rpmBlend;

                const float configuredEngineStrength =
                    static_cast<float>(Settings::WheelFFBEngineIdle);
                const float engineStrength = std::isfinite(configuredEngineStrength)
                    ? std::clamp(configuredEngineStrength, 0.0f, 1.0f)
                    : 0.0f;
                const float amplitudeScale = std::clamp(
                    0.38f + 0.32f * smoothedEngineRpm_ + 0.10f * throttleNorm,
                    0.0f, 1.0f);
                // Strength is a user-friendly 0..1 control, not direct wheel torque.
                // 0.20 therefore remains subtle instead of becoming a 20% torque pulse.
                const float targetEngineAmp =
                    engineStrength * 0.22f * amplitudeScale * outputStrength;
                const float ampBlend = targetEngineAmp > smoothedEngineAmp_ ? 0.16f : 0.08f;
                smoothedEngineAmp_ +=
                    (targetEngineAmp - smoothedEngineAmp_) * ampBlend;
                engineAmp = smoothedEngineAmp_;

                const float targetEngineFreq = 13.0f + 11.0f * smoothedEngineRpm_;
                if (smoothedEngineFreq_ <= 0.0f)
                    smoothedEngineFreq_ = targetEngineFreq;
                else
                    smoothedEngineFreq_ +=
                        (targetEngineFreq - smoothedEngineFreq_) * 0.14f;
                engineFreq = smoothedEngineFreq_;
            }
            else
            {
                smoothedEngineRpm_ = 0.0f;
                smoothedEngineAmp_ = 0.0f;
                smoothedEngineFreq_ = 0.0f;
                enginePhase_ = 0.0f;
            }
''')

one(core,
'''            const LONG baseSteeringLevel = std::clamp(
                structuralLevel + eventLevel,
                -static_cast<LONG>(DI_FFNOMINALMAX),
                static_cast<LONG>(DI_FFNOMINALMAX));
''',
'''            LONG baseSteeringLevel = std::clamp(
                structuralLevel + eventLevel,
                -static_cast<LONG>(DI_FFNOMINALMAX),
                static_cast<LONG>(DI_FFNOMINALMAX));
            if (Settings::WheelFFBEngineVibration && engineAmp > 0.0001f && eventLevel == 0)
            {
                // Reserve at most 2.5% during ordinary driving so the optional
                // engine texture does not abruptly vanish at brief SAT peaks.
                // Collision/gear events keep full priority.
                const LONG requestedReserve = static_cast<LONG>(
                    engineAmp * static_cast<float>(DI_FFNOMINALMAX));
                const LONG engineReserve = std::clamp(
                    std::abs(requestedReserve), 0L, 250L);
                const LONG baseCap = static_cast<LONG>(DI_FFNOMINALMAX) - engineReserve;
                baseSteeringLevel = std::clamp(
                    structuralLevel + eventLevel, -baseCap, baseCap);
            }
''')

one(core,
'''            enginePhase_ = 0.0f;
            smoothedEngineRpm_ = 0.0f;
            splashTimer_ = 0;
''',
'''            enginePhase_ = 0.0f;
            smoothedEngineRpm_ = 0.0f;
            smoothedEngineAmp_ = 0.0f;
            smoothedEngineFreq_ = 0.0f;
            splashTimer_ = 0;
''')
one(core,
'''        float enginePhase_ = 0.0f;
        float smoothedEngineRpm_ = 0.0f;
        float splashAmp_ = 0.0f;
''',
'''        float enginePhase_ = 0.0f;
        float smoothedEngineRpm_ = 0.0f;
        float smoothedEngineAmp_ = 0.0f;
        float smoothedEngineFreq_ = 0.0f;
        float splashAmp_ = 0.0f;
''')

ui = "src/overlay/wheel_setup_ui.cpp"
one(ui, "            bool engineVibration = true;\n", "            bool engineVibration = false;\n")
one(ui, "            float engineIdle = 0.06f;\n", "            float engineIdle = 0.20f;\n")
one(ui,
    '            track_ffb_change(ImGui::SliderFloat("Engine Vibration Strength", Settings::WheelFFBEngineIdle.ptr(), 0.0f, 0.30f, "%.2f"));\n',
    '            track_ffb_change(ImGui::SliderFloat("Engine Vibration Strength", Settings::WheelFFBEngineIdle.ptr(), 0.0f, 1.0f, "%.2f"));\n')
one(ui,
    '                ImGui::SetTooltip("Estimated engine RPM from vehicle speed, current gear and throttle. Uses the same ConstantForce tactile path on every wheel.");\n',
    '                ImGui::SetTooltip("Optional estimated-RPM texture. Default OFF. Strength is normalized and internally limited so 0.20 remains subtle.");\n')

build = "src/hooks_wheel_ffb_build.cpp"
many(build,
'''        Settings::WheelFFBEngineVibration = true;
        Settings::WheelFFBEngineIdle = 0.06f;
''',
'''        Settings::WheelFFBEngineVibration = false;
        Settings::WheelFFBEngineIdle = 0.20f;
''', 2)

ini = "OutRun2006Tweaks.ini"
one(ini,
'''EngineVibration = true
EngineIdle = 0.06
''',
'''EngineVibration = false
EngineIdle = 0.20
''')
one(ini,
'''; Steering-wheel engine haptics. F11 > Force Feedback exposes the live toggle
; and strength control. RPM is currently estimated from speed, gear and throttle.
''',
'''; Optional steering-wheel engine haptics. Default OFF because continuous engine
; texture is preference-dependent. F11 > Force Feedback exposes the live toggle
; and normalized strength control. RPM is estimated from speed, gear and throttle.
''')

tests = "tools/test_wheel_ffb_current.cpp"
one(tests,
    ' require(engineIdle.frequencyHz>=9.0f&&engineIdle.frequencyHz<12.0f,"engine idle haptic frequency");\n',
    ' require(engineIdle.frequencyHz>=13.0f&&engineIdle.frequencyHz<16.0f,"engine idle haptic frequency");\n')
one(tests,
    ' require(engineGear1.frequencyHz<=20.0001f&&engineGear1.amplitudeScale<=1.0001f,"engine haptic bounded");\n',
    ' require(engineGear1.frequencyHz<=24.0001f&&engineGear1.amplitudeScale<=1.0001f,"engine haptic bounded");\n')
one(tests,
    ' require(estimate_engine_haptics(std::numeric_limits<float>::quiet_NaN(),99,std::numeric_limits<float>::quiet_NaN()).frequencyHz>=9.0f,"engine haptic rejects non-finite inputs");\n',
    ' require(estimate_engine_haptics(std::numeric_limits<float>::quiet_NaN(),99,std::numeric_limits<float>::quiet_NaN()).frequencyHz>=13.0f,"engine haptic rejects non-finite inputs");\n')

verify = "tools/verify_wheel_ffb_current.py"
s = read(verify)
marker = "# v01-final-engine-haptic-guards"
if marker not in s:
    s += '''

# v01-final-engine-haptic-guards
req(ffb, '"WheelFFB", "EngineVibration", false', 'engine vibration is opt-in by default')
req(ffb, '"WheelFFB", "EngineIdle", 0.20f', 'engine vibration default strength is 0.20')
req(ffb, 'engineStrength * 0.22f * amplitudeScale * outputStrength', 'engine strength is internally kept subtle')
req(ffb, 'smoothedEngineAmp_', 'engine vibration amplitude is smoothed')
req(ffb, 'smoothedEngineFreq_', 'engine vibration frequency is smoothed')
req(ffb, 'engineReserve = std::clamp(', 'engine haptic gets a small continuity reserve')
req(wheel_ui, 'Engine Vibration Strength', 'engine vibration strength remains user-adjustable')
req(ini, 'EngineVibration = false', 'shipped engine vibration stays disabled')
req(ini, 'EngineIdle = 0.20', 'shipped optional engine strength is 0.20')
'''
    write(verify, s)

print("v0.1 final engine haptic tune applied")
