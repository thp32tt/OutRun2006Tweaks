from pathlib import Path


def read(path):
    return Path(path).read_text(encoding="utf-8")


def write(path, text):
    Path(path).write_text(text, encoding="utf-8", newline="\n")


def replace_once(path, old, new):
    text = read(path)
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one anchor, found {count}: {old[:100]!r}")
    write(path, text.replace(old, new, 1))


def replace_count(path, old, new, expected):
    text = read(path)
    count = text.count(old)
    if count != expected:
        raise SystemExit(f"{path}: expected {expected} anchors, found {count}: {old[:100]!r}")
    write(path, text.replace(old, new))


# Pure engine-speed estimator lives in production math so host tests can execute it.
math_path = "src/wheel_ffb_math.hpp"
math_marker = """    // Saturating proxy for front-tyre lateral force. OutRun does not expose
"""
math_insert = """    struct EngineHapticEstimate
    {
        float rpmNorm = 0.0f;
        float frequencyHz = 0.0f;
        float amplitudeScale = 0.0f;
    };

    // OutRun does not expose a verified engine-RPM field in EVWORK_CAR yet.
    // Estimate normalized RPM from vehicle speed, current gear and throttle so
    // the haptic can be swapped to a real RPM source later without changing the
    // output path or UI. Frequencies stay below 20 Hz for a stable 60 Hz FFB loop.
    inline EngineHapticEstimate estimate_engine_haptics(
        float speedNorm, unsigned int gear, float throttleNorm)
    {
        speedNorm = std::isfinite(speedNorm)
            ? std::clamp(speedNorm, 0.0f, 1.0f) : 0.0f;
        throttleNorm = std::isfinite(throttleNorm)
            ? std::clamp(throttleNorm, 0.0f, 1.0f) : 0.0f;

        // Approximate normalized road speed at redline for gears 1..6.
        // Only the relative drop/rise matters for tactile frequency shaping.
        static constexpr std::array<float, 6> GearRedlineSpeed = {
            0.17f, 0.30f, 0.44f, 0.60f, 0.78f, 1.00f
        };
        const unsigned int forwardGear = std::clamp(gear, 1u, 6u);
        const float coupledRpm =
            speedNorm / GearRedlineSpeed[forwardGear - 1u];
        const float idleFloor = 0.10f + 0.05f * throttleNorm;
        const float freeRev = (gear == 0 || speedNorm < 0.025f)
            ? 0.10f + 0.55f * throttleNorm
            : 0.0f;

        EngineHapticEstimate out{};
        out.rpmNorm = std::clamp(
            std::max({ coupledRpm, idleFloor, freeRev }), 0.08f, 1.0f);
        out.frequencyHz = 9.0f + 11.0f * out.rpmNorm;
        out.amplitudeScale = std::clamp(
            0.45f + 0.40f * out.rpmNorm + 0.15f * throttleNorm,
            0.0f, 1.0f);
        return out;
    }

""" + math_marker
replace_once(math_path, math_marker, math_insert)

core = "src/hooks_wheel_ffb.cpp"
replace_once(
    core,
    """    Setting<float> WheelFFBEngineIdle{
        \"WheelFFB\", \"EngineIdle\", 0.04f,
        \"Low-speed launch/idle vibration.\", Range<float>{ 0.0f, 0.5f }
    };
""",
    """    Setting<bool> WheelFFBEngineVibration{
        \"WheelFFB\", \"EngineVibration\", true,
        \"Add a low-amplitude engine-speed haptic through the universal ConstantForce output path.\"
    };

    // Keep the legacy EngineIdle key for INI/profile compatibility. It now owns
    // the complete engine-vibration strength rather than only launch/idle rumble.
    Setting<float> WheelFFBEngineIdle{
        \"WheelFFB\", \"EngineIdle\", 0.06f,
        \"Engine vibration strength (legacy EngineIdle key retained for compatibility).\",
        Range<float>{ 0.0f, 0.5f }
    };
""",
)

replace_once(
    core,
    """            const uint32_t stateFlags = car->field_8;
            const uint32_t curGear = car->cur_gear_208;
            const float lateralSum = car->field_264 + car->field_268;
""",
    """            const uint32_t stateFlags = car->field_8;
            const uint32_t curGear = car->cur_gear_208;
            const float throttleNorm = std::clamp(
                static_cast<float>(car->pedal_amount_34) / 255.0f, 0.0f, 1.0f);

            float engineAmp = 0.0f;
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

            const float lateralSum = car->field_264 + car->field_268;
""",
)

replace_once(
    core,
    """            if (slipSeverity > 0.08f && speedNorm > 0.05f)
            {
                slipAmp =
                    slipSeverity * static_cast<float>(Settings::WheelFFBTireSlip) *
                    outputStrength;
                slipFreq = 40.0f - 12.0f * slipSeverity;
            }
            else if (speedNorm < 0.03f && car->pedal_amount_34 > 0)
            {
                const float throttleNorm =
                    std::clamp(static_cast<float>(car->pedal_amount_34) / 255.0f, 0.0f, 1.0f);
                slipAmp =
                    static_cast<float>(Settings::WheelFFBEngineIdle) * throttleNorm * outputStrength;
                slipFreq = 15.0f + 7.0f * throttleNorm;
            }
""",
    """            if (slipSeverity > 0.08f && speedNorm > 0.05f)
            {
                slipAmp =
                    slipSeverity * static_cast<float>(Settings::WheelFFBTireSlip) *
                    outputStrength;
                slipFreq = 40.0f - 12.0f * slipSeverity;
            }
""",
)

replace_once(
    core,
    """            float fallbackVibration = 0.0f;
            if (!periodicsActive_)
            {
                fallbackVibration += synth_fallback(
                    roadPhase_, roadAmp * effectRampScale, std::min(roadFreq, 15.0f));
                fallbackVibration += synth_fallback(
                    slipPhase_, slipAmp * effectRampScale, std::min(slipFreq, 15.0f));
            }
""",
    """            float fallbackVibration = 0.0f;
            if (!periodicsActive_)
            {
                fallbackVibration += synth_fallback(
                    roadPhase_, roadAmp * effectRampScale, std::min(roadFreq, 15.0f));
                fallbackVibration += synth_fallback(
                    slipPhase_, slipAmp * effectRampScale, std::min(slipFreq, 15.0f));
            }

            // Engine haptics always use the normalized ConstantForce tactile
            // transport so wheel brand / GUID_Sine support cannot change the feel.
            // The existing vibration-headroom clamp below guarantees SAT/events
            // always have priority over this cosmetic engine texture.
            if (Settings::WheelFFBEngineVibration)
            {
                fallbackVibration += synth_fallback(
                    enginePhase_, engineAmp * effectRampScale, engineFreq);
            }
""",
)

replace_once(
    core,
    """            roadPhase_ = 0.0f;
            slipPhase_ = 0.0f;
            splashTimer_ = 0;
""",
    """            roadPhase_ = 0.0f;
            slipPhase_ = 0.0f;
            enginePhase_ = 0.0f;
            smoothedEngineRpm_ = 0.0f;
            splashTimer_ = 0;
""",
)

replace_once(
    core,
    """        float crashImpulseForce_ = 0.0f;
        float roadPhase_ = 0.0f;
        float slipPhase_ = 0.0f;
        float splashAmp_ = 0.0f;
""",
    """        float crashImpulseForce_ = 0.0f;
        float roadPhase_ = 0.0f;
        float slipPhase_ = 0.0f;
        float enginePhase_ = 0.0f;
        float smoothedEngineRpm_ = 0.0f;
        float splashAmp_ = 0.0f;
""",
)

ui = "src/overlay/wheel_setup_ui.cpp"
replace_once(
    ui,
    """    extern Setting<float> WheelFFBGearShift;
    extern Setting<float> WheelFFBEngineIdle;
""",
    """    extern Setting<float> WheelFFBGearShift;
    extern Setting<bool> WheelFFBEngineVibration;
    extern Setting<float> WheelFFBEngineIdle;
""",
)
replace_once(
    ui,
    """            bool telemetry = false;
            float global = 0.70f;
""",
    """            bool telemetry = false;
            bool engineVibration = true;
            float global = 0.70f;
""",
)
replace_once(
    ui,
    """            float gearShift = 0.18f;
            float engineIdle = 0.04f;
""",
    """            float gearShift = 0.18f;
            float engineIdle = 0.06f;
""",
)
replace_once(
    ui,
    """            savedFfb_.gearShift = Settings::WheelFFBGearShift;
            savedFfb_.engineIdle = Settings::WheelFFBEngineIdle;
""",
    """            savedFfb_.gearShift = Settings::WheelFFBGearShift;
            savedFfb_.engineVibration = Settings::WheelFFBEngineVibration;
            savedFfb_.engineIdle = Settings::WheelFFBEngineIdle;
""",
)
replace_once(
    ui,
    """            Settings::WheelFFBGearShift = savedFfb_.gearShift;
            Settings::WheelFFBEngineIdle = savedFfb_.engineIdle;
""",
    """            Settings::WheelFFBGearShift = savedFfb_.gearShift;
            Settings::WheelFFBEngineVibration = savedFfb_.engineVibration;
            Settings::WheelFFBEngineIdle = savedFfb_.engineIdle;
""",
)

replace_once(
    ui,
    """            ImGui::SeparatorText(\"Effects\");
            track_ffb_change(ImGui::SliderFloat(\"Road Detail\", Settings::WheelFFBRoadTexture.ptr(), 0.0f, 0.50f, \"%.2f\"));
            track_ffb_change(ImGui::SliderFloat(\"Tire Slip\", Settings::WheelFFBTireSlip.ptr(), 0.0f, 0.50f, \"%.2f\"));
            track_ffb_change(ImGui::SliderFloat(\"Collision\", Settings::WheelFFBWallImpact.ptr(), 0.0f, 1.0f, \"%.2f\"));
            track_ffb_change(ImGui::Checkbox(\"Hardware road/slip sine effects\", Settings::WheelFFBUsePeriodicEffects.ptr()));
""",
    """            ImGui::SeparatorText(\"Effects\");
            track_ffb_change(ImGui::SliderFloat(\"Road Detail\", Settings::WheelFFBRoadTexture.ptr(), 0.0f, 1.0f, \"%.2f\"));
            track_ffb_change(ImGui::SliderFloat(\"Tire Slip\", Settings::WheelFFBTireSlip.ptr(), 0.0f, 0.50f, \"%.2f\"));
            track_ffb_change(ImGui::SliderFloat(\"Collision\", Settings::WheelFFBWallImpact.ptr(), 0.0f, 1.0f, \"%.2f\"));
            track_ffb_change(ImGui::Checkbox(\"Engine Vibration\", Settings::WheelFFBEngineVibration.ptr()));
            if (!Settings::WheelFFBEngineVibration) ImGui::BeginDisabled();
            track_ffb_change(ImGui::SliderFloat(\"Engine Vibration Strength\", Settings::WheelFFBEngineIdle.ptr(), 0.0f, 0.30f, \"%.2f\"));
            if (ImGui::IsItemHovered())
                ImGui::SetTooltip(\"Estimated engine RPM from vehicle speed, current gear and throttle. Uses the same ConstantForce tactile path on every wheel.\");
            if (!Settings::WheelFFBEngineVibration) ImGui::EndDisabled();
            track_ffb_change(ImGui::Checkbox(\"Hardware road/slip sine effects\", Settings::WheelFFBUsePeriodicEffects.ptr()));
""",
)
replace_once(
    ui,
    """                track_ffb_change(ImGui::SliderFloat(\"Gear Shift\", Settings::WheelFFBGearShift.ptr(), 0.0f, 1.0f, \"%.2f\"));
                track_ffb_change(ImGui::SliderFloat(\"Engine Idle\", Settings::WheelFFBEngineIdle.ptr(), 0.0f, 0.50f, \"%.2f\"));
                track_ffb_change(ImGui::SliderFloat(\"Force Build Slew Rate\", Settings::WheelFFBSlewRate.ptr(), 0.01f, 1.0f, \"%.3f\"));
""",
    """                track_ffb_change(ImGui::SliderFloat(\"Gear Shift\", Settings::WheelFFBGearShift.ptr(), 0.0f, 1.0f, \"%.2f\"));
                track_ffb_change(ImGui::SliderFloat(\"Force Build Slew Rate\", Settings::WheelFFBSlewRate.ptr(), 0.01f, 1.0f, \"%.3f\"));
""",
)

build = "src/hooks_wheel_ffb_build.cpp"
replace_count(
    build,
    """        Settings::WheelFFBEngineIdle = 0.04f;
""",
    """        Settings::WheelFFBEngineVibration = true;
        Settings::WheelFFBEngineIdle = 0.06f;
""",
    2,
)

ini = "OutRun2006Tweaks.ini"
replace_once(
    ini,
    """MaxTorqueNm = 0.0

; Opt-in 10 Hz diagnostics. Force Feedback > Save Force Feedback persists changes.
""",
    """MaxTorqueNm = 0.0

; Steering-wheel engine haptics. F11 > Force Feedback exposes the live toggle
; and strength control. RPM is currently estimated from speed, gear and throttle.
EngineVibration = true
EngineIdle = 0.06

; Opt-in 10 Hz diagnostics. Force Feedback > Save Force Feedback persists changes.
""",
)

tests = "tools/test_wheel_ffb_current.cpp"
replace_once(
    tests,
    ' require(pneumatic_sat_shape(0)==0,"SAT zero");\n',
    ''' auto engineIdle=estimate_engine_haptics(0.0f,0,0.0f);
 require(engineIdle.rpmNorm>=.08f&&engineIdle.rpmNorm<.20f,"engine idle RPM estimate");
 require(engineIdle.frequencyHz>=9.0f&&engineIdle.frequencyHz<12.0f,"engine idle haptic frequency");
 auto engineFree=estimate_engine_haptics(0.0f,0,1.0f);
 require(engineFree.rpmNorm>engineIdle.rpmNorm&&engineFree.frequencyHz>engineIdle.frequencyHz,"free-rev haptic rises with throttle");
 auto engineGear1=estimate_engine_haptics(.15f,1,.5f);
 auto engineGear2=estimate_engine_haptics(.15f,2,.5f);
 require(engineGear1.rpmNorm>engineGear2.rpmNorm,"upshift lowers estimated RPM at equal road speed");
 require(engineGear1.frequencyHz<=20.0001f&&engineGear1.amplitudeScale<=1.0001f,"engine haptic bounded");
 require(estimate_engine_haptics(std::numeric_limits<float>::quiet_NaN(),99,std::numeric_limits<float>::quiet_NaN()).frequencyHz>=9.0f,"engine haptic rejects non-finite inputs");
 require(pneumatic_sat_shape(0)==0,"SAT zero");
''',
)

verify = "tools/verify_wheel_ffb_current.py"
verify_text = read(verify)
guard = "# engine-vibration-v02-regression-guards"
if guard in verify_text:
    raise SystemExit("engine vibration verifier guards already exist")
verify_text += '''

# engine-vibration-v02-regression-guards
req(ffb, 'Setting<bool> WheelFFBEngineVibration', 'engine vibration has an independent live toggle')
req(math, 'EngineHapticEstimate estimate_engine_haptics(', 'engine RPM estimator is production math')
req(ffb, 'WheelFFBMath::estimate_engine_haptics(', 'FFB core consumes the common engine estimator')
req(ffb, 'enginePhase_, engineAmp * effectRampScale, engineFreq', 'engine haptic uses ConstantForce fallback layer')
req(ffb, 'smoothedEngineRpm_ = 0.0f;', 'engine haptic state resets on transitions/off')
forbid(ffb, 'else if (speedNorm < 0.03f && car->pedal_amount_34 > 0)', 'legacy low-speed-only engine rumble removed')
req(wheel_ui, 'Checkbox("Engine Vibration", Settings::WheelFFBEngineVibration.ptr())', 'F11 exposes engine vibration toggle')
req(wheel_ui, 'SliderFloat("Engine Vibration Strength", Settings::WheelFFBEngineIdle.ptr()', 'F11 exposes engine vibration strength')
forbid(wheel_ui, 'SliderFloat("Engine Idle"', 'old duplicate Engine Idle slider removed')
req(wheel_ui, 'WheelFFBRoadTexture.ptr(), 0.0f, 1.0f', 'Road Detail UI covers the 0.60 universal preset')
req(ini, 'EngineVibration = true', 'shipped config enables engine vibration')
req(ini, 'EngineIdle = 0.06', 'shipped engine haptic strength')
'''
write(verify, verify_text)

print("Engine vibration source patch applied successfully")
