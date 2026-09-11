from pathlib import Path
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
input_hpp = read('src/input_manager.hpp')
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
req(wheel_ui, 'draw_device_combo("FFB Output", true', 'FFB selector filters to FFB-capable interfaces')
req(wheel_ui, 'draw_device_combo("Legacy Input Wheel", false', 'legacy input identity selected separately')
req(input_hpp, 'Path is only a duplicate-device tie-breaker/fallback', 'USB path is not hard binding identity')
compat_v2 = read('src/hooks_wheel_input_compat_v2.hpp')
req(compat_v2, 'return Settings::WheelInputCompatibility &&\n                !Settings::UseNewInput &&\n                !Settings::WheelUniversalSetupEnable;', 'legacy V2 hook install gate is mutually exclusive')
req(wheel_ui, '!Settings::UseNewInput && Settings::WheelUniversalSetupEnable', 'universal legacy hook has exclusive install gate')

req(ffb, 'GUID_ConstantForce', 'DirectInput ConstantForce effect')
req(ffb, 'GUID_Spring', 'DirectInput Spring effect')
req(ffb, 'GUID_Damper', 'DirectInput Damper effect')
req(ffb, 'WheelFFB_UpdateAfterPhysics(EVWORK_CAR* car)', 'post-physics FFB entry point')
forbid(ffb, 'CalcVibrationHook_', 'no competing CalcVibrationValues FFB hook')
req(vib, 'if (WheelFFB_IsOutputOwnerActive())', 'rumble suppression follows actual FFB ownership')
req(ffb, 'bool WheelFFB_IsOutputOwnerActive()', 'FFB ownership query exported')
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
req(ffb, 'const float naturalSlideRelief =\n                1.0f - 0.25f * gripLoss * bodySlide;', 'Natural SAT unloads from real slide')
req(ffb, 'const float rearSlideRelief = 1.0f - 0.15f * gripLoss * bodySlide;', 'Physics SAT avoids body-slip double unload')
req(ffb, 'WheelFFBMath::trail_shape(frontSlip)', 'production SAT curve shared with compiled tests')
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

# These are structural guards, not a substitute for the compiled numeric tests.
cmake = read('CMakeLists.txt')
toml = read('cmake.toml')
for text in (cmake, toml):
    req(text, 'set_source_files_properties(src/hooks_wheel_ffb.cpp PROPERTIES HEADER_FILE_ONLY TRUE)', 'shim implementation is not a second TU')
for path in ('CMakeLists.txt', 'cmake.toml', '.github/workflows/build.yml'):
    forbid(read(path), 'tools/archive/rounds/', 'archive outside build graph')
    forbid(read(path), 'patch_wheel_round', 'no round patch invocation')
forbid(bind_ui, 'draw_force_feedback', 'no dead alternate FFB page')
forbid(ffb, 'WheelFFBLowSpeedSpring', 'unused low-speed setting removed')
forbid(ffb, 'WheelFFBSpringLoadBoost', 'unused load setting removed')
forbid(ffb, 'effect.dwDuration = INFINITE', 'effects have driver-side leases')
req(ffb, 'FFB_EFFECT_LEASE_US = 250000', '250ms driver lease')
req(ffb, 'FFB_EFFECT_REFRESH_MS = 100', '100ms lease renewal')
req(ffb, 'params.dwFlags = DIEFF_POLAR | DIEFF_OBJECTOFFSETS', 'explicit polar update descriptor')
req(read('src/hooks_framerate.cpp'), 'WheelFFB_ServiceSafety();', 'safety is serviced outside player-car callback')
req(wheel_ui, 'Save Force Feedback', 'dedicated FFB save action')
forbid(ffb, 'trying first attached non-virtual FFB device', 'no unrelated device fallback')
req(ffb, 'DIPROP_FFGAIN', 'device gain configured separately from effect gain')
forbid(ffb, 'apply_live_effect_gain', 'dead live effect-gain updater removed')
forbid(ffb, 'configured_effect_gain', 'effect gain fixed nominal at creation')
forbid(ffb, 'lastEffectGain_', 'dead live-gain state removed')
req(ffb, 'WheelFFB SAMPLE', '10Hz telemetry output')
req(dyn, 'headingValid_ = false; // The next heading', 'missing samples break derivative baseline')
print('CURRENT WHEEL FFB STRUCTURE VERIFIED; run verify_wheel_ffb_math.py for numerical tests')
