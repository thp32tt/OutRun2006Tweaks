from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def write(path, text):
    (ROOT / path).write_text(text, encoding="utf-8", newline="\n")


def replace_once(path, old, new):
    text = read(path)
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected exactly one match, found {count}: {old[:100]!r}")
    write(path, text.replace(old, new, 1))


# 1) Model mechanical trail as part of total trail instead of a fallback that
# only wakes up after pneumatic SAT has already faded. Keep SteeringWeight's
# established peak authority by normalizing the combined pseudo-trail model.
replace_once(
    "src/wheel_ffb_math.hpp",
    '''    // Fy * pneumatic trail. Normalize the empirically-known peak of the two
    // analytic curves so SteeringWeight keeps roughly the same normal-corner
    // authority as the previous single trail_shape() implementation.
    inline float pneumatic_sat_shape(float alpha)
    {
        if (!std::isfinite(alpha)) return 0.0f;
        constexpr float RawPeak = 0.838899081f;
        const float raw = lateral_force_shape(alpha) * pneumatic_trail_factor(alpha);
        return std::clamp(raw / RawPeak, 0.0f, 1.0f);
    }

    // Add a bounded mechanical/caster-trail component without turning it into
    // an artificial steering-centre spring. It is driven by the same front Fy
    // proxy and becomes relatively important only as pneumatic trail fades.
    inline float combined_sat_shape(float alpha, float mechanicalTrailMix)
    {
        const float pneumatic = pneumatic_sat_shape(alpha);
        const float fy = lateral_force_shape(alpha);
        const float mix = std::clamp(mechanicalTrailMix, 0.0f, 0.60f);
        const float mechanical = mix * fy * (1.0f - pneumatic);
        return std::clamp(pneumatic + mechanical, 0.0f, 1.0f);
    }
''',
    '''    // Reference peak of Fy * pneumatic trail. The absolute units are not
    // available from OutRun, so this keeps SteeringWeight near its established
    // scale while the relative trail terms shape the torque curve.
    inline constexpr float PneumaticReferencePeak = 0.838899081f;

    // Lateral force and pneumatic trail have different transient behaviour.
    // forceAlpha is the filtered tyre-force slip, while trailAlpha may be a
    // modest phase-led version used only by the pneumatic lever arm.
    inline float pneumatic_sat_shape(float forceAlpha, float trailAlpha)
    {
        if (!std::isfinite(forceAlpha) || !std::isfinite(trailAlpha)) return 0.0f;
        const float raw =
            lateral_force_shape(forceAlpha) * pneumatic_trail_factor(trailAlpha);
        return std::clamp(raw / PneumaticReferencePeak, 0.0f, 1.0f);
    }

    inline float pneumatic_sat_shape(float alpha)
    {
        return pneumatic_sat_shape(alpha, alpha);
    }

    // Mechanical/caster trail contributes whenever front lateral force exists;
    // it is not a substitute that appears only after pneumatic trail collapses.
    // The setting is a normalized pseudo-trail ratio, not a physical distance.
    inline float mechanical_sat_shape(float forceAlpha, float mechanicalTrailRatio)
    {
        if (!std::isfinite(forceAlpha)) return 0.0f;
        const float ratio = std::clamp(mechanicalTrailRatio, 0.0f, 0.60f);
        const float denominator = PneumaticReferencePeak + ratio;
        return denominator > 0.0f
            ? std::clamp(lateral_force_shape(forceAlpha) * ratio / denominator, 0.0f, 1.0f)
            : 0.0f;
    }

    // Total aligning moment follows Fy * (pneumatic trail + mechanical trail).
    // Normalize the total pseudo-trail so enabling mechanical trail reshapes
    // the SAT curve without silently turning SteeringWeight into a second gain.
    inline float combined_sat_shape(
        float forceAlpha, float trailAlpha, float mechanicalTrailRatio)
    {
        if (!std::isfinite(forceAlpha) || !std::isfinite(trailAlpha)) return 0.0f;
        const float ratio = std::clamp(mechanicalTrailRatio, 0.0f, 0.60f);
        const float denominator = PneumaticReferencePeak + ratio;
        if (denominator <= 0.0f)
            return 0.0f;
        const float raw = lateral_force_shape(forceAlpha) *
            (pneumatic_trail_factor(trailAlpha) + ratio);
        return std::clamp(raw / denominator, 0.0f, 1.0f);
    }

    inline float combined_sat_shape(float alpha, float mechanicalTrailRatio)
    {
        return combined_sat_shape(alpha, alpha, mechanicalTrailRatio);
    }
''')

# 2) Add a conservative, bounded phase lead to pneumatic trail only. The force
# proxy and torque direction remain on filtered front slip, avoiding raw-signal
# steering chatter while reducing aligning-moment lag.
replace_once(
    "src/hooks_wheel_ffb.cpp",
    '''    Setting<float> WheelFFBMechanicalTrail{
        "WheelFFB", "MechanicalTrail", 0.25f,
        "Physics SAT mechanical/caster-trail contribution after pneumatic trail begins to fade. Not a centre spring.",
        Range<float>{ 0.0f, 0.60f }
    };

    Setting<bool> WheelFFBPhysicsSat{
''',
    '''    Setting<float> WheelFFBMechanicalTrail{
        "WheelFFB", "MechanicalTrail", 0.25f,
        "Normalized mechanical/caster-trail ratio in Physics SAT. Acts with front lateral force across the corner; not a centre spring.",
        Range<float>{ 0.0f, 0.60f }
    };

    Setting<float> WheelFFBTrailResponseLead{
        "WheelFFB", "TrailResponseLead", 0.25f,
        "Pneumatic-trail transient phase lead toward raw front slip. Lateral force and torque direction remain filtered.",
        Range<float>{ 0.0f, 0.60f }
    };

    Setting<bool> WheelFFBPhysicsSat{
''')

replace_once(
    "src/hooks_wheel_ffb.cpp",
    '''            const float frontSlip = vehicleDynamics_.frontSlip();
            float physicsSatTorque = 0.0f;
            const float lateralForceShape = WheelFFBMath::lateral_force_shape(frontSlip);
            const float pneumaticTrail = WheelFFBMath::pneumatic_trail_factor(frontSlip);
            const float pneumaticSatShape = WheelFFBMath::pneumatic_sat_shape(frontSlip);
            const float configuredMechanicalTrail =
                static_cast<float>(Settings::WheelFFBMechanicalTrail);
            const float mechanicalTrailMix = std::isfinite(configuredMechanicalTrail)
                ? std::clamp(configuredMechanicalTrail, 0.0f, 0.60f)
                : 0.25f;
            const float mechanicalContribution =
                mechanicalTrailMix * lateralForceShape * (1.0f - pneumaticSatShape);
            const float physicsShape =
                WheelFFBMath::combined_sat_shape(frontSlip, mechanicalTrailMix);
''',
    '''            const float frontSlip = vehicleDynamics_.frontSlip();
            const float rawFrontSlip = vehicleDynamics_.rawFrontSlip();
            float physicsSatTorque = 0.0f;
            const float configuredTrailResponseLead =
                static_cast<float>(Settings::WheelFFBTrailResponseLead);
            const float trailResponseLead = std::isfinite(configuredTrailResponseLead)
                ? std::clamp(configuredTrailResponseLead, 0.0f, 0.60f)
                : 0.25f;
            const float trailResponseSlip = std::clamp(
                frontSlip + (rawFrontSlip - frontSlip) * trailResponseLead,
                -0.70f, 0.70f);
            const float lateralForceShape = WheelFFBMath::lateral_force_shape(frontSlip);
            const float pneumaticTrail = WheelFFBMath::pneumatic_trail_factor(trailResponseSlip);
            const float pneumaticSatShape =
                WheelFFBMath::pneumatic_sat_shape(frontSlip, trailResponseSlip);
            const float configuredMechanicalTrail =
                static_cast<float>(Settings::WheelFFBMechanicalTrail);
            const float mechanicalTrailMix = std::isfinite(configuredMechanicalTrail)
                ? std::clamp(configuredMechanicalTrail, 0.0f, 0.60f)
                : 0.25f;
            const float mechanicalContribution =
                WheelFFBMath::mechanical_sat_shape(frontSlip, mechanicalTrailMix);
            const float physicsShape = WheelFFBMath::combined_sat_shape(
                frontSlip, trailResponseSlip, mechanicalTrailMix);
''')

replace_once(
    "src/hooks_wheel_ffb.cpp",
    '''                    "WheelFFB SATMODEL t={} rawBodySlip={} bodySlip={} bodyBlend={} rawYawRate={} yawRate={} yawBlend={} rawFrontSlip={} frontSlip={} frontBlend={} fyShape={} pneumaticTrail={} pneumaticShape={} mechanicalMix={} mechanicalContribution={} combinedShape={} diPreResponse={} diCorrected={} responseCorrection={}",
                    telemetryNow,
                    vehicleDynamics_.rawBodySlip(), vehicleDynamics_.bodySlip(), vehicleDynamics_.bodySlipBlend(),
                    vehicleDynamics_.rawYawRate(), vehicleDynamics_.yawRate(), vehicleDynamics_.yawRateBlend(),
                    vehicleDynamics_.rawFrontSlip(), vehicleDynamics_.frontSlip(), vehicleDynamics_.frontSlipBlend(),
                    lateralForceShape, pneumaticTrail, pneumaticSatShape, mechanicalTrailMix,
                    mechanicalContribution, physicsShape, levelBeforeResponse, level,
                    bool(Settings::WheelFFBResponseCorrection));
''',
    '''                    "WheelFFB SATMODEL t={} rawBodySlip={} bodySlip={} bodyBlend={} rawYawRate={} yawRate={} yawBlend={} rawFrontSlip={} frontSlip={} frontBlend={} trailResponseSlip={} trailResponseLead={} fyShape={} pneumaticTrail={} pneumaticShape={} mechanicalMix={} mechanicalContribution={} combinedShape={} diPreResponse={} diCorrected={} responseCorrection={}",
                    telemetryNow,
                    vehicleDynamics_.rawBodySlip(), vehicleDynamics_.bodySlip(), vehicleDynamics_.bodySlipBlend(),
                    vehicleDynamics_.rawYawRate(), vehicleDynamics_.yawRate(), vehicleDynamics_.yawRateBlend(),
                    vehicleDynamics_.rawFrontSlip(), vehicleDynamics_.frontSlip(), vehicleDynamics_.frontSlipBlend(),
                    trailResponseSlip, trailResponseLead, lateralForceShape, pneumaticTrail,
                    pneumaticSatShape, mechanicalTrailMix, mechanicalContribution, physicsShape,
                    levelBeforeResponse, level, bool(Settings::WheelFFBResponseCorrection));
''')

# 3) Expose the transient tuning without crowding the main Physics controls.
replace_once(
    "src/overlay/wheel_setup_ui.cpp",
    '''    extern Setting<float> WheelFFBMechanicalTrail;
    extern Setting<bool> WheelFFBPhysicsSat;
''',
    '''    extern Setting<float> WheelFFBMechanicalTrail;
    extern Setting<float> WheelFFBTrailResponseLead;
    extern Setting<bool> WheelFFBPhysicsSat;
''')

replace_once(
    "src/overlay/wheel_setup_ui.cpp",
    '''                if (ImGui::IsItemHovered())
                    ImGui::SetTooltip("Adds bounded front-lateral-force restoring torque as pneumatic trail fades. This is not a centre spring; 0 disables the mechanical/caster contribution.");
            }
            track_ffb_change(ImGui::SliderFloat("Grip-loss Response", Settings::WheelFFBGripLoss.ptr(), 0.0f, 1.0f, "%.2f"));

            ImGui::SeparatorText("Steering Feel");
''',
    '''                if (ImGui::IsItemHovered())
                    ImGui::SetTooltip("Normalized mechanical/caster trail acts with front lateral force throughout a corner. 0 disables it; this is not a centre spring.");
            }
            track_ffb_change(ImGui::SliderFloat("Grip-loss Response", Settings::WheelFFBGripLoss.ptr(), 0.0f, 1.0f, "%.2f"));

            ImGui::SeparatorText("Steering Feel");
''')

replace_once(
    "src/overlay/wheel_setup_ui.cpp",
    '''                track_ffb_change(ImGui::SliderFloat("Force Slew Rate", Settings::WheelFFBSlewRate.ptr(), 0.01f, 1.0f, "%.3f"));
                if (ImGui::IsItemHovered())
                    ImGui::SetTooltip("Maximum structural-force change per 60 Hz tick. Lower is smoother/slower; higher responds faster.");

                ImGui::SeparatorText("Wheel hardware calibration");
''',
    '''                track_ffb_change(ImGui::SliderFloat("Force Slew Rate", Settings::WheelFFBSlewRate.ptr(), 0.01f, 1.0f, "%.3f"));
                if (ImGui::IsItemHovered())
                    ImGui::SetTooltip("Maximum structural-force change per 60 Hz tick. Lower is smoother/slower; higher responds faster.");
                if (Settings::WheelFFBPhysicsSat)
                {
                    ImGui::SeparatorText("Physics SAT transient");
                    track_ffb_change(ImGui::SliderFloat("Pneumatic Trail Response Lead", Settings::WheelFFBTrailResponseLead.ptr(), 0.0f, 0.60f, "%.2f"));
                    if (ImGui::IsItemHovered())
                        ImGui::SetTooltip("Lets pneumatic trail react part-way toward raw front slip while lateral force and torque direction stay filtered. Higher reduces SAT lag but can expose more telemetry noise.");
                }

                ImGui::SeparatorText("Wheel hardware calibration");
''')

replace_once(
    "src/overlay/wheel_setup_ui.cpp",
    '''            track_ffb_change(ImGui::Checkbox("Hardware GUID_Spring", Settings::WheelFFBUseHardwareSpring.ptr()));
            ImGui::SameLine();
            track_ffb_change(ImGui::Checkbox("Hardware GUID_Damper", Settings::WheelFFBUseHardwareDamper.ptr()));

            ImGui::SeparatorText("Effects");
''',
    '''            track_ffb_change(ImGui::Checkbox("Hardware GUID_Spring", Settings::WheelFFBUseHardwareSpring.ptr()));
            ImGui::SameLine();
            track_ffb_change(ImGui::Checkbox("Hardware GUID_Damper", Settings::WheelFFBUseHardwareDamper.ptr()));
            ImGui::TextDisabled("Wheelbase/driver-side spring, damping, inertia or friction are additional forces; keep them conservative while tuning game-side feel.");

            ImGui::SeparatorText("Effects");
''')

# Put the conservative phase-lead value explicitly in both R3 starting points.
text = read("src/overlay/wheel_setup_ui.cpp")
needle = '''                Settings::WheelFFBMechanicalTrail = 0.25f;\n                Settings::WheelFFBGripLoss = 0.65f;'''
if text.count(needle) != 2:
    raise SystemExit(f"wheel_setup_ui.cpp: expected two R3 preset mechanical-trail blocks, found {text.count(needle)}")
text = text.replace(
    needle,
    '''                Settings::WheelFFBMechanicalTrail = 0.25f;\n                Settings::WheelFFBTrailResponseLead = 0.25f;\n                Settings::WheelFFBGripLoss = 0.65f;''')
write("src/overlay/wheel_setup_ui.cpp", text)

# 4) Production-header tests: verify additive total-trail semantics and phase lead.
replace_once(
    "tools/test_wheel_ffb_current.cpp",
    ''' require(combined_sat_shape(.16f,.25f)<=1.000001f,"combined SAT bounded");
 require(combined_sat_shape(.32f,.25f)>pneumatic_sat_shape(.32f),"mechanical trail preserves deep-slip torque");
 require(combined_sat_shape(.32f,0.0f)==pneumatic_sat_shape(.32f),"mechanical trail zero is pure pneumatic");
 require(std::abs(combined_sat_shape(.32f,.25f)-combined_sat_shape(-.32f,.25f))<1e-6f,"SAT shape symmetry");
''',
    ''' require(combined_sat_shape(.16f,.25f)<=1.000001f,"combined SAT bounded");
 require(mechanical_sat_shape(.12f,.25f)>0.10f,"mechanical trail acts in normal loaded corner");
 require(mechanical_sat_shape(.32f,.25f)>mechanical_sat_shape(.12f,.25f),"mechanical term follows front lateral force");
 require(combined_sat_shape(.32f,.25f)>pneumatic_sat_shape(.32f),"total trail preserves deep-slip torque");
 require(combined_sat_shape(.32f,0.0f)==pneumatic_sat_shape(.32f),"mechanical trail zero is pure pneumatic");
 require(std::abs(combined_sat_shape(.32f,.25f)-combined_sat_shape(-.32f,.25f))<1e-6f,"SAT shape symmetry");
 require(pneumatic_sat_shape(.20f,.28f)<pneumatic_sat_shape(.20f,.20f),"phase-led growing slip drops pneumatic trail sooner");
 require(pneumatic_sat_shape(.20f,.12f)>pneumatic_sat_shape(.20f,.20f),"phase-led recovering slip restores pneumatic trail sooner");
''')

# 5) Static invariants guard the new physics distinction and tuning reachability.
replace_once(
    "tools/verify_wheel_ffb_current.py",
    '''req(math, 'combined_sat_shape(float alpha, float mechanicalTrailMix)', 'mechanical/caster trail separated')
req(ffb, 'WheelFFBMechanicalTrail', 'mechanical trail setting')
req(ffb, 'WheelFFB SATMODEL', 'raw/filtered and decomposed SAT telemetry')
''',
    '''req(math, 'mechanical_sat_shape(float forceAlpha, float mechanicalTrailRatio)', 'mechanical trail is an explicit lateral-force term')
req(math, 'float forceAlpha, float trailAlpha, float mechanicalTrailRatio', 'combined SAT separates force and trail transients')
forbid(math, 'mix * fy * (1.0f - pneumatic)', 'mechanical trail is never gated as a pneumatic fallback')
req(ffb, 'WheelFFBMechanicalTrail', 'mechanical trail setting')
req(ffb, 'WheelFFBTrailResponseLead', 'pneumatic trail phase-lead setting')
req(ffb, 'trailResponseSlip = std::clamp(', 'pneumatic trail uses bounded phase-led slip')
req(ffb, 'WheelFFBMath::pneumatic_sat_shape(frontSlip, trailResponseSlip)', 'lateral force remains filtered while trail response can lead')
req(ffb, 'trailResponseSlip={} trailResponseLead={}', 'phase-lead state is visible in telemetry')
req(wheel_ui, 'Pneumatic Trail Response Lead', 'phase-lead tuning is reachable in FFB UI')
req(ffb, 'WheelFFB SATMODEL', 'raw/filtered and decomposed SAT telemetry')
''')

replace_once(
    "tools/verify_wheel_ffb_current.py",
    '''req(ini, 'MechanicalTrail = 0.25', 'shipped mechanical trail default')
req(ini, 'ResponseCorrection = false', 'shipped response correction disabled')
''',
    '''req(ini, 'MechanicalTrail = 0.25', 'shipped mechanical trail default')
req(ini, 'TrailResponseLead = 0.25', 'shipped pneumatic trail phase-lead default')
req(ini, 'ResponseCorrection = false', 'shipped response correction disabled')
''')

# Existing UI already resets headroom stats on live FFB changes. Lock that in so
# stale statistics cannot survive a gain/model edit.
replace_once(
    "tools/verify_wheel_ffb_current.py",
    '''req(wheel_ui, 'Suggested Overall Strength', 'headroom gain recommendation exposed')
''',
    '''req(wheel_ui, 'Suggested Overall Strength', 'headroom gain recommendation exposed')
req(wheel_ui, 'ffbDirty_ = true;\\n                    WheelFFB_ResetHeadroomStats();', 'live FFB edits reset stale headroom statistics')
''')

# 6) Shipped config and docs explain the model and DD/base-side interaction.
replace_once(
    "OutRun2006Tweaks.ini",
    '''; Physics SAT retains pneumatic-trail falloff while a bounded mechanical/caster
; contribution keeps useful steering torque through deeper front slip.
MechanicalTrail = 0.25

; Optional wheel-specific response correction.''',
    '''; Physics SAT uses front lateral force times total pseudo-trail:
; pneumatic trail + a bounded mechanical/caster trail ratio. Mechanical trail
; acts throughout a loaded corner rather than appearing only after pneumatic
; trail fades. TrailResponseLead lets pneumatic trail react modestly ahead of
; filtered lateral force, reducing aligning-moment lag without using raw force direction.
MechanicalTrail = 0.25
TrailResponseLead = 0.25

; Optional wheel-specific response correction.''')

replace_once(
    "WHEEL_FFB.md",
    '''Physics SAT now separates a **pneumatic-trail** component from a bounded **mechanical/caster-trail** component. Both are driven by the estimated front-slip/lateral-force proxy; mechanical trail is not a centre spring. Pneumatic SAT peaks around the normal loaded-corner region and falls first as front slip grows, while the mechanical contribution preserves some steering authority through deeper understeer instead of letting the wheel go artificially dead.

The vehicle estimator keeps the existing bicycle-model-inspired `roadWheelAngle - bodySlip - yawRate * yawLeadSeconds` relation, but its body-slip/yaw/front-slip filters are now speed-adaptive. This is a relaxation-length-inspired approximation: at higher vehicle speed the same fixed time low-pass created too much countersteer/SAT lag. Telemetry records both raw and filtered states plus the active blend values (`WheelFFB SATMODEL`).
''',
    '''Physics SAT separates a **pneumatic-trail** component from a bounded **mechanical/caster-trail** component. The combined proxy follows the standard aligning-moment structure `Fy * (pneumatic trail + mechanical trail)`: mechanical trail therefore acts whenever front lateral force exists instead of behaving like a fallback that only appears after pneumatic trail collapses. The total is normalized so `SteeringWeight` remains the primary gain, and mechanical trail is still not a centre spring.

The vehicle estimator keeps the existing bicycle-model-inspired `roadWheelAngle - bodySlip - yawRate * yawLeadSeconds` relation, but its body-slip/yaw/front-slip filters are speed-adaptive. This is a relaxation-length-inspired approximation: at higher vehicle speed the same fixed time low-pass created too much countersteer/SAT lag. Aligning moment has different transient behaviour from lateral force, so **Pneumatic Trail Response Lead** lets only the pneumatic lever arm move part-way toward raw front slip while lateral force and torque direction remain on the filtered signal. The default 0.25 is deliberately conservative and telemetry records `trailResponseSlip` / `trailResponseLead` for hardware validation.
''')

replace_once(
    "WHEEL_FFB.md",
    '''`Load MOZA R3 Natural SAT` keeps the same overall/effect baseline but disables Physics SAT and uses Steering Weight 1.75, Dynamic Damping 0.30, Weight Transfer 0.20 and Slew 0.045. Treat both as starting points: verify ConstantForce and Spring direction with the 20% safe tests before increasing hardware torque.
''',
    '''`Load MOZA R3 Natural SAT` keeps the same overall/effect baseline but disables Physics SAT and uses Steering Weight 1.75, Dynamic Damping 0.30, Weight Transfer 0.20 and Slew 0.045. Treat both as starting points: verify ConstantForce and Spring direction with the 20% safe tests before increasing hardware torque.

For the R3, MOZA specifies a 3.9 Nm peak-torque direct-drive base with a 1000 Hz USB refresh capability. That USB figure does **not** create new OutRun physics samples: the game logic remains 60 Hz, so this fork deliberately does not synthesize a separate 1000/2000 Hz ConstantForce thread. While validating the game's SAT model, keep the Pit House **Base FFB Curve linear** and remember that Pit House mechanical centering, damping, inertia and friction are independent base-side forces that can stack with the game's Spring/Damper/SAT. Response correction remains off unless a measured wheel-response curve justifies it.
''')

replace_once(
    "README.md",
    '''Physics SAT uses a split pneumatic + mechanical/caster trail model instead of one all-purpose falloff curve. Front-slip filtering accelerates with vehicle speed to reduce countersteer lag, while the existing Natural SAT remains the full fallback whenever Physics SAT telemetry is not valid. F11 also includes structural FFB headroom/P95/P99 diagnostics and an optional per-wheel response LUT; hardware correction is disabled by default and should only be enabled from measured wheel behavior.''',
    '''Physics SAT uses front lateral force times a split pneumatic + mechanical/caster total-trail model instead of one all-purpose falloff curve. Front-slip filtering accelerates with vehicle speed to reduce countersteer lag, and a conservative pneumatic-trail phase lead reduces aligning-moment delay without putting raw/noisy slip directly into force direction. The existing Natural SAT remains the full fallback whenever Physics SAT telemetry is not valid. F11 also includes structural FFB headroom/P95/P99 diagnostics and an optional per-wheel response LUT; hardware correction is disabled by default and should only be enabled from measured wheel behavior.''')

print("second external FFB review source patch applied")
