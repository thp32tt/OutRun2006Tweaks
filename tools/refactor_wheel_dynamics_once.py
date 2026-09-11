from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
FFB = ROOT / 'src/hooks_wheel_ffb.cpp'
OLD_DYN = ROOT / 'src/hooks_wheel_physics_sat.hpp'
NEW_DYN = ROOT / 'src/hooks_wheel_vehicle_dynamics.hpp'
UI = ROOT / 'src/overlay/wheel_setup_ui.cpp'
VERIFY = ROOT / 'tools/verify_wheel_ffb_current.py'


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected exactly one match, got {count}')
    return text.replace(old, new, 1)


def regex_once(text: str, pattern: str, repl: str, label: str) -> str:
    out, count = re.subn(pattern, repl, text, count=1, flags=re.S)
    if count != 1:
        raise SystemExit(f'{label}: expected exactly one regex match, got {count}')
    return out


NEW_DYNAMICS_HEADER = r'''#pragma once

// OutRun vehicle-dynamics estimator for steering FFB.
//
// This class deliberately owns no DirectInput effects and computes no FFB
// torque. Its only job is to estimate reusable vehicle state from the game:
// body slip (beta), yaw rate, front-slip proxy and local motion. WheelFFBEngine
// decides how those signals affect SAT, damping and tire scrub.
class WheelVehicleDynamics
{
public:
    void reset()
    {
        positionValid_ = false;
        headingValid_ = false;
        calibrated_ = false;
        sampleValid_ = false;
        forwardAxis_ = 0;
        forwardSign_ = 1.0f;
        calibrationSamples_ = 0;
        calibrationScoreX_ = 0.0f;
        calibrationScoreZ_ = 0.0f;
        calibrationSignedX_ = 0.0f;
        calibrationSignedZ_ = 0.0f;
        calibrationConfidence_ = 0.0f;
        activationBlend_ = 0.0f;
        invalidTicks_ = 0;
        discontinuityCount_ = 0;
        prevPosition_ = D3DVECTOR{};
        prevHeading_ = 0.0f;
        bodySlip_ = 0.0f;
        yawRate_ = 0.0f;
        frontSlip_ = 0.0f;
        vLong_ = 0.0f;
        vLat_ = 0.0f;
        positionStep_ = 0.0f;
        motionScaleEma_ = 0.0f;
        motionScaleSamples_ = 0;
        spdLen_ = 0.0f;
        spdCorrelation_ = 0.0f;
    }

    void update(
        EVWORK_CAR* car,
        float steer,
        float speedNorm,
        float lateralLoadSmooth)
    {
        sampleValid_ = false;
        vLong_ = 0.0f;
        vLat_ = 0.0f;
        positionStep_ = 0.0f;
        spdLen_ = 0.0f;
        spdCorrelation_ = 0.0f;

        if (!car)
        {
            decay_invalid_sample();
            return;
        }

        const D3DVECTOR current = car->position_14;
        if (!std::isfinite(current.x) || !std::isfinite(current.z))
        {
            decay_invalid_sample();
            return;
        }

        if (!positionValid_)
        {
            prevPosition_ = current;
            positionValid_ = true;
            return;
        }

        const float dx = current.x - prevPosition_.x;
        const float dz = current.z - prevPosition_.z;
        prevPosition_ = current;
        const float motionLen = std::sqrt(dx * dx + dz * dz);
        positionStep_ = std::isfinite(motionLen) ? motionLen : 0.0f;

        // A stop/restart must not inherit the previous corner's beta/yaw/front
        // slip. Keep the proven matrix basis but restart only dynamic state.
        if (speedNorm <= 0.04f)
        {
            clear_dynamic_state();
            sampleValid_ = calibrated_;
            return;
        }

        if (!std::isfinite(motionLen) || motionLen <= 0.00001f)
        {
            decay_invalid_sample();
            return;
        }

        // Detect restart/warp discontinuities without assuming OutRun world
        // units. Compare normalized step length with its rolling scale.
        const float motionScale = motionLen / std::max(speedNorm, 0.05f);
        if (motionScaleSamples_ >= 12 &&
            motionScaleEma_ > 0.00001f &&
            motionScale > motionScaleEma_ * 5.0f)
        {
            ++discontinuityCount_;
            clear_dynamic_state();
            return;
        }
        if (std::isfinite(motionScale))
        {
            if (motionScaleSamples_ == 0)
                motionScaleEma_ = motionScale;
            else
                motionScaleEma_ += (motionScale - motionScaleEma_) * 0.05f;
            ++motionScaleSamples_;
        }

        const float motionX = dx / motionLen;
        const float motionZ = dz / motionLen;
        const D3DMATRIX& body = car->matrix_70;

        // OutRun uses row-vector transforms, but whether local X or Z is the
        // vehicle-forward basis is verified from several straight rolling ticks
        // rather than guessed from one frame.
        if (!calibrated_ &&
            speedNorm > 0.12f &&
            std::abs(steer) < 0.08f &&
            lateralLoadSmooth < 0.12f)
        {
            const float xLen = std::sqrt(body._11 * body._11 + body._13 * body._13);
            const float zLen = std::sqrt(body._31 * body._31 + body._33 * body._33);
            if (std::isfinite(xLen) && std::isfinite(zLen) &&
                xLen > 0.0001f && zLen > 0.0001f)
            {
                const float xDot =
                    (body._11 / xLen) * motionX + (body._13 / xLen) * motionZ;
                const float zDot =
                    (body._31 / zLen) * motionX + (body._33 / zLen) * motionZ;
                calibrationScoreX_ += std::abs(xDot);
                calibrationScoreZ_ += std::abs(zDot);
                calibrationSignedX_ += xDot;
                calibrationSignedZ_ += zDot;
                ++calibrationSamples_;

                constexpr int CalibrationSamplesRequired = 12;
                if (calibrationSamples_ >= CalibrationSamplesRequired)
                {
                    const float invSamples = 1.0f / static_cast<float>(calibrationSamples_);
                    const float xScore = calibrationScoreX_ * invSamples;
                    const float zScore = calibrationScoreZ_ * invSamples;
                    const float bestScore = std::max(xScore, zScore);
                    const float secondScore = std::min(xScore, zScore);
                    calibrationConfidence_ = bestScore - secondScore;

                    if (bestScore >= 0.85f && calibrationConfidence_ >= 0.25f)
                    {
                        forwardAxis_ = zScore >= xScore ? 3 : 1;
                        const float signedScore = forwardAxis_ == 3
                            ? calibrationSignedZ_
                            : calibrationSignedX_;
                        forwardSign_ = signedScore >= 0.0f ? 1.0f : -1.0f;
                        calibrated_ = true;
                        clear_dynamic_state();
                    }
                }
            }
        }

        if (!calibrated_)
            return;

        float forwardX = forwardAxis_ == 3 ? body._31 : body._11;
        float forwardZ = forwardAxis_ == 3 ? body._33 : body._13;
        forwardX *= forwardSign_;
        forwardZ *= forwardSign_;
        const float forwardLen = std::sqrt(forwardX * forwardX + forwardZ * forwardZ);
        if (!std::isfinite(forwardLen) || forwardLen <= 0.0001f)
        {
            decay_invalid_sample();
            return;
        }
        forwardX /= forwardLen;
        forwardZ /= forwardLen;

        // Right-positive local motion. Position delta remains authoritative until
        // spd_mb_20's coordinate space/scale is proven by real-lap telemetry.
        const float rightX = forwardZ;
        const float rightZ = -forwardX;
        vLong_ = dx * forwardX + dz * forwardZ;
        vLat_ = dx * rightX + dz * rightZ;
        const float rawBodySlip = std::clamp(
            std::atan2(vLat_, std::max(std::abs(vLong_), 0.00001f)),
            -0.70f, 0.70f);
        bodySlip_ += (rawBodySlip - bodySlip_) * 0.18f;

        const float heading = std::atan2(forwardX, forwardZ);
        if (!headingValid_)
        {
            prevHeading_ = heading;
            headingValid_ = true;
            return;
        }

        constexpr float Pi = 3.14159265359f;
        constexpr float TwoPi = 6.28318530718f;
        float headingDelta = heading - prevHeading_;
        prevHeading_ = heading;
        while (headingDelta > Pi)
            headingDelta -= TwoPi;
        while (headingDelta < -Pi)
            headingDelta += TwoPi;
        if (std::abs(headingDelta) >= 0.35f)
        {
            ++discontinuityCount_;
            clear_dynamic_state();
            return;
        }

        // Called once per fixed OutRun simulation tick, independent of render FPS.
        const float rawYawRate = std::clamp(headingDelta * 60.0f, -3.5f, 3.5f);
        yawRate_ += (rawYawRate - yawRate_) * 0.20f;

        // Bicycle-model-inspired front-slip proxy:
        // alpha_f ~= road-wheel-angle - beta - a*r/v.
        constexpr float RoadWheelLockRad = 0.52f;
        const float roadWheelAngle = steer * RoadWheelLockRad;
        const float yawLeadSeconds = 0.10f - 0.045f * speedNorm;
        const float rawFrontSlip = std::clamp(
            roadWheelAngle - bodySlip_ - yawRate_ * yawLeadSeconds,
            -0.70f, 0.70f);
        frontSlip_ += (rawFrontSlip - frontSlip_) * 0.22f;

        // Telemetry-only validation for the game's native speed vector.
        const float spdX = car->spd_mb_20.x;
        const float spdZ = car->spd_mb_20.z;
        const float spdLen = std::sqrt(spdX * spdX + spdZ * spdZ);
        if (std::isfinite(spdLen) && spdLen > 0.0001f)
        {
            spdLen_ = spdLen;
            spdCorrelation_ =
                (spdX / spdLen) * motionX + (spdZ / spdLen) * motionZ;
        }

        sampleValid_ = true;
        invalidTicks_ = 0;
        activationBlend_ = std::min(1.0f, activationBlend_ + (1.0f / 24.0f));
    }

    bool calibrated() const { return calibrated_; }
    bool sampleValid() const { return sampleValid_; }
    int forwardAxis() const { return forwardAxis_; }
    int discontinuityCount() const { return discontinuityCount_; }
    float calibrationConfidence() const { return calibrationConfidence_; }
    float activationBlend() const { return activationBlend_; }
    float bodySlip() const { return bodySlip_; }
    float yawRate() const { return yawRate_; }
    float frontSlip() const { return frontSlip_; }
    float vLong() const { return vLong_; }
    float vLat() const { return vLat_; }
    float positionStep() const { return positionStep_; }
    float motionScale() const { return motionScaleEma_; }
    float spdLen() const { return spdLen_; }
    float spdCorrelation() const { return spdCorrelation_; }

private:
    void clear_dynamic_state()
    {
        headingValid_ = false;
        sampleValid_ = false;
        prevHeading_ = 0.0f;
        bodySlip_ = 0.0f;
        yawRate_ = 0.0f;
        frontSlip_ = 0.0f;
        vLong_ = 0.0f;
        vLat_ = 0.0f;
        activationBlend_ = 0.0f;
        invalidTicks_ = 0;
    }

    void decay_invalid_sample()
    {
        sampleValid_ = false;
        if (!calibrated_)
            return;

        ++invalidTicks_;
        bodySlip_ *= 0.55f;
        yawRate_ *= 0.55f;
        frontSlip_ *= 0.55f;
        activationBlend_ *= 0.85f;

        // Once telemetry has been invalid for several ticks, clear all dynamic
        // slip/yaw state. Calibration/basis remains valid so recovery is quick.
        if (invalidTicks_ > 4)
            clear_dynamic_state();
    }

    bool positionValid_ = false;
    bool headingValid_ = false;
    bool calibrated_ = false;
    bool sampleValid_ = false;
    int forwardAxis_ = 0;
    float forwardSign_ = 1.0f;
    int calibrationSamples_ = 0;
    float calibrationScoreX_ = 0.0f;
    float calibrationScoreZ_ = 0.0f;
    float calibrationSignedX_ = 0.0f;
    float calibrationSignedZ_ = 0.0f;
    float calibrationConfidence_ = 0.0f;
    float activationBlend_ = 0.0f;
    int invalidTicks_ = 0;
    int discontinuityCount_ = 0;
    D3DVECTOR prevPosition_{};
    float prevHeading_ = 0.0f;
    float bodySlip_ = 0.0f;
    float yawRate_ = 0.0f;
    float frontSlip_ = 0.0f;
    float vLong_ = 0.0f;
    float vLat_ = 0.0f;
    float positionStep_ = 0.0f;
    float motionScaleEma_ = 0.0f;
    int motionScaleSamples_ = 0;
    float spdLen_ = 0.0f;
    float spdCorrelation_ = 0.0f;
};
'''

NEW_VERIFIER = r'''from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent

def read(rel):
    p = ROOT / rel
    if not p.exists():
        raise SystemExit(f'CURRENT VERIFY FAILED [missing file]: {rel}')
    return p.read_text(encoding='utf-8')

def req(text, needle, label):
    if needle not in text:
        raise SystemExit(f'CURRENT VERIFY FAILED [{label}]: {needle!r}')
    print(f'OK [{label}]')

def forbid(text, needle, label):
    if needle in text:
        raise SystemExit(f'CURRENT VERIFY FAILED [{label}]: forbidden {needle!r}')
    print(f'OK [{label}]')

ffb = read('src/hooks_wheel_ffb.cpp')
vib = read('src/hooks_forcefeedback.cpp')
dyn = read('src/hooks_wheel_vehicle_dynamics.hpp')
input_cpp = read('src/input_manager.cpp')
bind_ui = read('src/overlay/input_bindings_ui.cpp')
wheel_ui = read('src/overlay/wheel_setup_ui.cpp')
ini = read('OutRun2006Tweaks.ini')

if (ROOT / 'src/hooks_wheel_physics_sat.hpp').exists():
    raise SystemExit('CURRENT VERIFY FAILED [obsolete Physics SAT helper still active]')

for rel, text in [
    ('src/hooks_wheel_ffb.cpp', ffb),
    ('src/hooks_forcefeedback.cpp', vib),
    ('src/hooks_wheel_vehicle_dynamics.hpp', dyn),
    ('src/input_manager.cpp', input_cpp),
    ('src/overlay/input_bindings_ui.cpp', bind_ui),
    ('src/overlay/wheel_setup_ui.cpp', wheel_ui),
]:
    if text.count('{') != text.count('}'):
        raise SystemExit(f'CURRENT VERIFY FAILED [brace balance]: {rel}')
    print(f'OK [brace balance {rel}]')

req(ini, 'UseNewInput = true', 'shipped SDL multi-device input default')
req(input_cpp, 'InputManager_SteeringValue()', 'SAT reads active InputManager steering')
req(input_cpp, 'SDL_GetJoysticks', 'SDL raw joystick enumeration')
req(bind_ui, 'Input Bindings', 'single input-binding UI')
req(wheel_ui, 'Force Feedback', 'dedicated FFB UI')
req(wheel_ui, 'Legacy Wheel Setup', 'legacy input kept behind compatibility mode')

req(ffb, 'GUID_ConstantForce', 'DirectInput ConstantForce effect')
req(ffb, 'GUID_Spring', 'DirectInput Spring effect')
req(ffb, 'GUID_Damper', 'DirectInput Damper effect')
req(ffb, 'WheelFFB_UpdateAfterPhysics(EVWORK_CAR* car)', 'post-physics FFB entry point')
forbid(ffb, 'CalcVibrationHook_', 'no competing CalcVibrationValues FFB hook')
req(vib, 'if (Settings::UseNewInput && Settings::WheelFFBEnable)', 'SDL rumble suppressed under wheel FFB')
req(ffb, 'setting->hidden(true);', 'generic WheelFFB settings hidden')
req(vib, 'GamePlCar_Ctrl.call(car);\n        WheelFFB_UpdateAfterPhysics(car);', 'post-physics execution order')

calc = vib.find('CalcVibrationValues(car);')
ctrl = vib.find('GamePlCar_Ctrl.call(car);')
wheel = vib.find('WheelFFB_UpdateAfterPhysics(car);')
if not (0 <= calc < ctrl < wheel):
    raise SystemExit('CURRENT VERIFY FAILED [vibration/physics/FFB ordering]')
print('OK [vibration before physics; wheel FFB after physics]')

# Vehicle dynamics is now estimation-only; the main FFB engine owns force shaping.
req(ffb, '#include "hooks_wheel_vehicle_dynamics.hpp"', 'vehicle dynamics helper included')
req(dyn, 'class WheelVehicleDynamics', 'estimator separated from FFB torque')
forbid(dyn, 'satStrength', 'estimator owns no SAT strength')
forbid(dyn, 'gripLoss', 'estimator owns no grip tuning')
forbid(dyn, 'trailShape', 'estimator owns no tire-force curve')
req(dyn, 'roadWheelAngle - bodySlip_ - yawRate_ * yawLeadSeconds', 'front-slip proxy')
req(dyn, 'constexpr int CalibrationSamplesRequired = 12;', 'multi-sample basis calibration')
req(dyn, 'bestScore >= 0.85f && calibrationConfidence_ >= 0.25f', 'basis confidence gate')
req(dyn, 'motionScale > motionScaleEma_ * 5.0f', 'restart/warp discontinuity guard')
req(dyn, 'if (speedNorm <= 0.04f)', 'stopped-car dynamic state reset')
req(dyn, 'headingDelta * 60.0f', 'fixed 60 Hz yaw-rate derivative')
req(dyn, 'car->spd_mb_20.x', 'spd_mb telemetry retained')
req(dyn, 'if (invalidTicks_ > 4)\n            clear_dynamic_state();', 'stale dynamics cleared after invalid telemetry')

# field_264/268 are lateral load only. Slip/grip must come from dynamics.
req(ffb, 'const float lateralSum = car->field_264 + car->field_268;', 'OutRun lateral-G source retained')
req(ffb, 'const float lateralLoad = std::clamp(std::abs(latNorm), 0.0f, 1.0f);', 'lateral signal used as load magnitude')
req(ffb, 'vehicleDynamics_.update(car, steer, speedNorm, lateralLoadSmooth);', 'dynamics updated independently')
forbid(ffb, 'driftAmt', 'lateral-G drift detector removed')
forbid(ffb, 'gripFactor', 'shared lateral-G grip factor removed')
req(ffb, 'const float bodySlideT = std::clamp(', 'body slip drives chassis slide')
req(ffb, 'const float frontScrubT = std::clamp(', 'front slip drives tire scrub')
req(ffb, 'const float springStrength = std::clamp(\n                static_cast<float>(Settings::WheelFFBSpringStrength) * springSpeed,', 'spring independent of grip/slip')
req(ffb, 'const float damperRelease = 1.0f - 0.55f * gripLoss * bodySlide;', 'damper released by chassis slide')
req(ffb, 'frontScrub * (0.50f + 0.50f * lateralLoadSmooth) +\n                    bodySlide * 0.20f', 'tire slip driven mainly by front scrub')
req(ffb, 'const float naturalSlideRelief = 1.0f - 0.25f * gripLoss * bodySlide;', 'Natural SAT unloads from real slide')
req(ffb, 'const float rearSlideRelief = 1.0f - 0.15f * gripLoss * bodySlide;', 'Physics SAT avoids body-slip double unload')
req(ffb, 'const float slipX = frontSlipAbs / 0.16f;', 'Physics SAT pneumatic-trail curve lives in FFB engine')
req(ffb, '(frontSlip > 0.0f ? -1.0f : 1.0f)', 'Physics SAT direction follows front slip')
forbid(ffb, 'physicsGrip', 'old strong body-slip SAT double-unload removed')

req(wheel_ui, 'Physics SAT (body slip + yaw)', 'versionless Physics SAT UI')
req(wheel_ui, 'Load MOZA R3 Physics SAT', 'versionless Physics SAT preset')
req(wheel_ui, 'Grip-loss Response', 'grip-loss UI reflects broader role')
req(wheel_ui, 'Test Left (20%)', 'safe left test')
req(wheel_ui, 'Test Right (20%)', 'safe right test')
req(ffb, 'DI_FFNOMINALMAX', 'nominal DirectInput device gain')
req(ffb, 'WheelFFB: scheduling DirectInput device reinitialization', 'device recovery path')
req(ffb, 'SnowIceRoadTextureScale = 0.04f', 'snow/ice periodic attenuation')
req(ffb, 'std::isfinite', 'non-finite input/output guards')
req(wheel_ui, 'Settings::WheelFFBInvertForce = true;', 'R3 ConstantForce direction baseline')
req(wheel_ui, 'Settings::WheelFFBInvertSpring = false;', 'R3 Spring direction baseline')
req(wheel_ui, 'Settings::VibrationMode = 0;', 'R3 preset disables gamepad rumble')
req(ffb, 'load={:.2f} slide={:.2f} scrub={:.2f}', 'separated load/slide/scrub diagnostics')
req(ffb, 'step={:.5f} spdLen={:.5f} spdCorr={:.2f}', 'velocity diagnostic telemetry')

for pattern, label in [
    (r'(?m)^SteeringDeadZone\s*=\s*0\.0\s*$', 'zero steering deadzone'),
    (r'(?m)^WheelAccelerationInvert\s*=\s*false\s*$', 'accelerator normal polarity'),
    (r'(?m)^WheelBrakeInvert\s*=\s*false\s*$', 'brake normal polarity'),
]:
    if not re.search(pattern, ini):
        raise SystemExit(f'CURRENT VERIFY FAILED [{label}]')
    print(f'OK [{label}]')

print('CURRENT WHEEL FFB BASELINE VERIFIED')
'''

ffb = FFB.read_text(encoding='utf-8')
ui = UI.read_text(encoding='utf-8')

ffb = replace_once(
    ffb,
    '#include "hooks_wheel_physics_sat.hpp"',
    '#include "hooks_wheel_vehicle_dynamics.hpp"',
    'replace dynamics include')

ffb = replace_once(
    ffb,
    '"Self-aligning torque strength. Physics SAT uses body slip, yaw rate and lateral load; Natural SAT remains available for comparison."',
    '"Self-aligning torque strength. Physics SAT direction/trail comes from front slip; field_264/268 only scale lateral load."',
    'update SAT description')
ffb = replace_once(
    ffb,
    '"How much cornering load and hardware spring unload as the car enters a deep drift."',
    '"How strongly real chassis/front-slip signals release damping and unload SAT. Lateral G is load only, never a drift detector."',
    'update grip description')
ffb = replace_once(
    ffb,
    '"Subtractive noise floor for the game\'s lateral force signal."',
    '"Subtractive noise floor for the game\'s lateral-G/load signal."',
    'update lateral description')
ffb = replace_once(
    ffb,
    '"Hardware sine chatter as drift depth increases."',
    '"Hardware sine chatter driven mainly by estimated front-tire scrub, with a small chassis-slide contribution."',
    'update tire slip description')

old_lateral = '''            const float latNorm = std::clamp(lateralDz / 24.0f, -1.0f, 1.0f);\n            const float driftAmt =\n                std::clamp((std::abs(smoothedLateral_) - 12.0f) / 12.0f, 0.0f, 1.0f);\n            const float gripFactor =\n                1.0f - static_cast<float>(Settings::WheelFFBGripLoss) * driftAmt;\n'''
new_lateral = '''            // field_264 + field_268 is treated strictly as lateral acceleration/load.\n            // It must never decide whether the tyres are sliding; that comes from\n            // bodySlip/frontSlip estimated from actual vehicle motion.\n            const float latNorm = std::clamp(lateralDz / 24.0f, -1.0f, 1.0f);\n            const float lateralLoad = std::clamp(std::abs(latNorm), 0.0f, 1.0f);\n            const float lateralLoadSmooth =\n                lateralLoad * lateralLoad * (3.0f - 2.0f * lateralLoad);\n\n            vehicleDynamics_.update(car, steer, speedNorm, lateralLoadSmooth);\n\n            const float bodySlideT = std::clamp(\n                (std::abs(vehicleDynamics_.bodySlip()) - 0.10f) / 0.22f,\n                0.0f, 1.0f);\n            const float bodySlide =\n                bodySlideT * bodySlideT * (3.0f - 2.0f * bodySlideT);\n            const float frontScrubT = std::clamp(\n                (std::abs(vehicleDynamics_.frontSlip()) - 0.04f) / 0.14f,\n                0.0f, 1.0f);\n            const float frontScrub =\n                frontScrubT * frontScrubT * (3.0f - 2.0f * frontScrubT);\n            const float configuredGripLoss =\n                static_cast<float>(Settings::WheelFFBGripLoss);\n            const float gripLoss = std::isfinite(configuredGripLoss)\n                ? std::clamp(configuredGripLoss, 0.0f, 1.0f)\n                : 0.0f;\n'''
ffb = replace_once(ffb, old_lateral, new_lateral, 'replace lateral drift detector')

old_slip = '''            float slipAmp = 0.0f;\n            float slipFreq = 40.0f;\n            if (driftAmt > 0.15f && speedNorm > 0.05f)\n            {\n                slipAmp = driftAmt * static_cast<float>(Settings::WheelFFBTireSlip) * outputStrength;\n                slipFreq = 40.0f - 12.0f * driftAmt;\n            }\n            else if (speedNorm < 0.03f && car->pedal_amount_34 > 0)\n'''
new_slip = '''            float slipAmp = 0.0f;\n            float slipFreq = 40.0f;\n            const float slipSeverity = std::clamp(\n                frontScrub * (0.50f + 0.50f * lateralLoadSmooth) +\n                    bodySlide * 0.20f,\n                0.0f, 1.0f);\n            if (slipSeverity > 0.08f && speedNorm > 0.05f)\n            {\n                slipAmp =\n                    slipSeverity * static_cast<float>(Settings::WheelFFBTireSlip) *\n                    outputStrength;\n                slipFreq = 40.0f - 12.0f * slipSeverity;\n            }\n            else if (speedNorm < 0.03f && car->pedal_amount_34 > 0)\n'''
ffb = replace_once(ffb, old_slip, new_slip, 'replace tire slip source')

# The old cornerLoad declaration is now redundant because lateralLoad is created
# immediately after field_264/268 filtering.
ffb = replace_once(
    ffb,
    '            const float cornerLoad = std::clamp(std::abs(latNorm), 0.0f, 1.0f);\n\n',
    '',
    'remove duplicate corner load')

old_spring = '''            const float springSpeed = 1.0f - 0.88f * springFade;\n            const float springGrip = 0.80f + 0.20f * gripFactor;\n            const float springStrength = std::clamp(\n                static_cast<float>(Settings::WheelFFBSpringStrength) *\n                    springSpeed * springGrip,\n                0.0f, 1.0f);\n'''
new_spring = '''            const float springSpeed = 1.0f - 0.88f * springFade;\n            // Centering Spring is an artificial low-speed stabilizer, not a tyre\n            // grip estimator. Do not modulate it with lateral-G or slide state.\n            const float springStrength = std::clamp(\n                static_cast<float>(Settings::WheelFFBSpringStrength) * springSpeed,\n                0.0f, 1.0f);\n'''
ffb = replace_once(ffb, old_spring, new_spring, 'decouple spring from grip')

old_damper = '''            const float dampingSpeed =\n                0.10f + 0.90f * std::pow(speedNorm, 1.30f);\n            const float dampingGrip = 0.25f + 0.75f * gripFactor;\n            const float dynamicDamperStrength = std::clamp(\n                static_cast<float>(Settings::WheelFFBDamperStrength) *\n                    dampingSpeed * dampingGrip,\n                0.0f, 1.0f);\n'''
new_damper = '''            const float dampingSpeed =\n                0.10f + 0.90f * std::pow(speedNorm, 1.30f);\n            // Release steering damping only when the chassis is actually\n            // sliding. A high lateral-G but fully-gripped corner keeps damping.\n            const float damperRelease = 1.0f - 0.55f * gripLoss * bodySlide;\n            const float dynamicDamperStrength = std::clamp(\n                static_cast<float>(Settings::WheelFFBDamperStrength) *\n                    dampingSpeed * damperRelease,\n                0.0f, 1.0f);\n'''
ffb = replace_once(ffb, old_damper, new_damper, 'body-slip damper release')

# Replace the old lateral-G pseudo-slip block with real slide relief. Also rename
# corner-load smoothing to its physical meaning.
ffb = replace_once(
    ffb,
    '''            const float cornerLoadSmooth =\n                cornerLoad * cornerLoad * (3.0f - 2.0f * cornerLoad);\n            const float satLoadBoost = 0.72f + 0.38f * cornerLoadSmooth;\n\n            // Lateral magnitude is only a proxy for actual slip. Unload late and\n            // smoothly so an ordinary loaded corner cannot repeatedly lose and\n            // regain SAT as the Xbox vibration signal crosses a threshold.\n            const float satSlipT = std::clamp(\n                (driftAmt - 0.60f) / 0.35f, 0.0f, 1.0f);\n            const float satSlip =\n                satSlipT * satSlipT * (3.0f - 2.0f * satSlipT);\n            const float satGrip = 1.0f -\n                0.65f * static_cast<float>(Settings::WheelFFBGripLoss) * satSlip;\n''',
    '''            const float satLoadBoost = 0.72f + 0.38f * lateralLoadSmooth;\n\n            // Natural SAT remains an A/B fallback, but even it now unloads from\n            // actual chassis slide instead of mistaking high lateral-G for drift.\n            const float naturalSlideRelief =\n                1.0f - 0.25f * gripLoss * bodySlide;\n''',
    'replace Natural SAT drift proxy')
ffb = replace_once(
    ffb,
    '''                steerForSat * satSpeed * satLoadBoost * satGrip *\n                satReturnRelief * satStrength;''',
    '''                steerForSat * satSpeed * satLoadBoost * naturalSlideRelief *\n                satReturnRelief * satStrength;''',
    'Natural SAT uses body slide')

old_physics = '''            // Physics SAT derives force direction from estimated front slip,\n            // not merely from steering sign. During initial basis calibration\n            // retain only a small Natural SAT safety net, then crossfade over\n            // 24 valid physics ticks. Once active, a valid zero Physics SAT is\n            // truly zero; Natural SAT never leaks back in around wheel centre.\n            const float physicsSatTorque = physicsSat_.update(\n                car, steer, speedNorm, cornerLoadSmooth, returnRateSmooth,\n                static_cast<float>(Settings::WheelFFBGripLoss),\n                satStrength, satSpeed);\n            const float physicsFallback = naturalSatTorque * 0.15f;\n            const float physicsMix = physicsSat_.activationBlend();\n            const float selfAligningTorque = Settings::WheelFFBPhysicsSat\n                ? physicsFallback + (physicsSatTorque - physicsFallback) * physicsMix\n                : naturalSatTorque;\n'''
new_physics = '''            // Physics SAT force shaping lives here, separate from the vehicle\n            // estimator. Front slip determines both direction and the pneumatic-\n            // trail-like rise/fall. Body slide only applies a mild rear-slide\n            // relief so counter-steer SAT is not double-unloaded.\n            const float frontSlip = vehicleDynamics_.frontSlip();\n            const float frontSlipAbs = std::abs(frontSlip);\n            float physicsSatTorque = 0.0f;\n            if (vehicleDynamics_.calibrated() && frontSlipAbs > 0.004f)\n            {\n                const float slipX = frontSlipAbs / 0.16f;\n                const float trailShape = slipX <= 1.0f\n                    ? std::sin(slipX * HalfPi)\n                    : std::exp(-(slipX - 1.0f) * 0.90f);\n                const float physicsLoad = 0.62f + 0.48f * lateralLoadSmooth;\n                const float rearSlideRelief =\n                    1.0f - 0.15f * gripLoss * bodySlide;\n                const float physicsReturnRelief =\n                    1.0f - 0.15f * returnRateSmooth;\n\n                physicsSatTorque =\n                    (frontSlip > 0.0f ? -1.0f : 1.0f) *\n                    trailShape * satSpeed * physicsLoad * rearSlideRelief *\n                    physicsReturnRelief * satStrength;\n                if (!std::isfinite(physicsSatTorque))\n                    physicsSatTorque = 0.0f;\n            }\n\n            // During basis calibration retain only a small Natural SAT safety\n            // net, then crossfade over valid dynamics ticks. Invalid telemetry\n            // decays/clears dynamics state instead of leaking stale slide values.\n            const float physicsFallback = naturalSatTorque * 0.15f;\n            const float physicsMix = vehicleDynamics_.activationBlend();\n            const float selfAligningTorque = Settings::WheelFFBPhysicsSat\n                ? physicsFallback + (physicsSatTorque - physicsFallback) * physicsMix\n                : naturalSatTorque;\n'''
ffb = replace_once(ffb, old_physics, new_physics, 'move Physics SAT shaping into engine')

ffb = replace_once(
    ffb,
    '            maybe_log(speedNorm, steer, steerRate, driftAmt, roughness, selfAligningTorque, level);',
    '            maybe_log(speedNorm, steer, steerRate, lateralLoadSmooth, bodySlide, frontScrub, roughness, selfAligningTorque, level);',
    'update diagnostic call')
ffb = replace_once(ffb, '            physicsSat_.reset();', '            vehicleDynamics_.reset();', 'reset estimator')
ffb = replace_once(ffb, '        WheelPhysicsSatV1 physicsSat_{};', '        WheelVehicleDynamics vehicleDynamics_{};', 'replace estimator member')

ffb = regex_once(
    ffb,
    r'''        void maybe_log\(\n.*?\n        \}\n\n        IDirectInput8A\* directInput_''',
    '''        void maybe_log(\n            float speedNorm,\n            float steer,\n            float steerRate,\n            float lateralLoad,\n            float bodySlide,\n            float frontScrub,\n            float roughness,\n            float satTorque,\n            LONG level)\n        {\n            if (!Settings::WheelFFBDebugLog)\n                return;\n\n            const DWORD now = GetTickCount();\n            if (now - lastLogTick_ < 2000)\n                return;\n\n            lastLogTick_ = now;\n            spdlog::info(\n                "WheelFFB DIAG: spd={:.2f} steer={:.3f} rate={:.4f} lat={:.2f} load={:.2f} slide={:.2f} scrub={:.2f} rough={:.2f} sat={:.3f} phys={} basis=M70r{} cal={:.2f} mix={:.2f} beta={:.3f} yaw={:.3f} fslip={:.3f} vLat={:.5f} vLong={:.5f} step={:.5f} spdLen={:.5f} spdCorr={:.2f} steerSrc={} out={} invCF={} spring={} invSpring={} coeff={} damper={} dcoeff={} periodic={}",\n                speedNorm,\n                steer,\n                steerRate,\n                smoothedLateral_,\n                lateralLoad,\n                bodySlide,\n                frontScrub,\n                roughness,\n                satTorque,\n                Settings::WheelFFBPhysicsSat\n                    ? (vehicleDynamics_.calibrated()\n                        ? (vehicleDynamics_.sampleValid() ? "ACTIVE" : "HOLD")\n                        : "CAL")\n                    : "OFF",\n                vehicleDynamics_.forwardAxis(),\n                vehicleDynamics_.calibrationConfidence(),\n                vehicleDynamics_.activationBlend(),\n                vehicleDynamics_.bodySlip(),\n                vehicleDynamics_.yawRate(),\n                vehicleDynamics_.frontSlip(),\n                vehicleDynamics_.vLat(),\n                vehicleDynamics_.vLong(),\n                vehicleDynamics_.positionStep(),\n                vehicleDynamics_.spdLen(),\n                vehicleDynamics_.spdCorrelation(),\n                Settings::UseNewInput ? "SDL" : "legacy",\n                static_cast<int>(level),\n                bool(Settings::WheelFFBInvertForce),\n                springEffect_ ? "HW" : "SW",\n                bool(Settings::WheelFFBInvertSpring),\n                static_cast<int>(prevSpringCoefficient_),\n                damperEffect_ ? "HW" : "SW",\n                static_cast<int>(prevDamperCoefficient_),\n                periodicsActive_);\n        }\n\n        IDirectInput8A* directInput_''',
    'replace diagnostics')

if 'physicsSat_' in ffb or 'WheelPhysicsSatV1' in ffb:
    raise SystemExit('stale PhysicsSatV1 references remain in hooks_wheel_ffb.cpp')
if 'driftAmt' in ffb or 'gripFactor' in ffb or 'physicsGrip' in ffb:
    raise SystemExit('stale lateral-G-as-slip variables remain in hooks_wheel_ffb.cpp')

ui = replace_once(
    ui,
    'Physics SAT v1 (body slip + yaw)',
    'Physics SAT (body slip + yaw)',
    'rename Physics SAT checkbox')
ui = replace_once(
    ui,
    'Uses post-physics OutRun car motion/body heading to estimate front slip. Disable for the Round-16 Natural SAT comparison.',
    'Uses post-physics OutRun car motion/body heading to estimate front slip. Disable for the Natural SAT comparison.',
    'update Physics SAT tooltip')
ui = replace_once(ui, 'Grip-loss Unload', 'Grip-loss Response', 'rename grip-loss slider')
ui = replace_once(ui, 'Load MOZA R3 Physics SAT v1', 'Load MOZA R3 Physics SAT', 'rename Physics SAT preset')
ui = replace_once(
    ui,
    'Loaded MOZA R3 Physics SAT v1: post-physics body-slip/yaw SAT with diagnostic logging. Saved to user.ini.',
    'Loaded MOZA R3 Physics SAT: lateral load, body slide and front scrub are separated; diagnostic logging enabled. Saved to user.ini.',
    'update Physics SAT preset status')
ui = replace_once(
    ui,
    'Single-owner wheel FFB: DirectInput COM only. SAT now rises smoothly from centre, builds with speed/corner load and unloads only in a deep slide. Centering Spring is mainly a low-speed stabilizer, so it no longer stacks a second strong high-speed return force.',
    'Single-owner wheel FFB: DirectInput COM only. field_264/268 are lateral load only; body slip releases damping, while front slip drives Physics SAT and tire scrub. Centering Spring remains a low-speed stabilizer.',
    'update FFB architecture text')

# Write the new estimator and active sources. The old SAT helper is removed after
# all transformations have succeeded.
NEW_DYN.write_text(NEW_DYNAMICS_HEADER, encoding='utf-8')
FFB.write_text(ffb, encoding='utf-8')
UI.write_text(ui, encoding='utf-8')
VERIFY.write_text(NEW_VERIFIER, encoding='utf-8')
if OLD_DYN.exists():
    OLD_DYN.unlink()

# Final local invariants before the workflow invokes the independent verifier.
for path in (FFB, NEW_DYN, UI):
    text = path.read_text(encoding='utf-8')
    if text.count('{') != text.count('}'):
        raise SystemExit(f'brace imbalance after refactor: {path}')

print('Applied consolidated wheel dynamics / grip-role refactor')
