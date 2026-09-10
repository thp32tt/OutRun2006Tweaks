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
phys = read('src/hooks_wheel_physics_sat.hpp')
input_cpp = read('src/input_manager.cpp')
bind_ui = read('src/overlay/input_bindings_ui.cpp')
wheel_ui = read('src/overlay/wheel_setup_ui.cpp')
ini = read('OutRun2006Tweaks.ini')

for rel, text in [
    ('src/hooks_wheel_ffb.cpp', ffb),
    ('src/hooks_forcefeedback.cpp', vib),
    ('src/hooks_wheel_physics_sat.hpp', phys),
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

req(ffb, '#include "hooks_wheel_physics_sat.hpp"', 'Physics SAT helper included')
req(ffb, 'Setting<bool> WheelFFBPhysicsSat', 'Physics SAT selectable')
req(ffb, 'const float physicsMix = physicsSat_.activationBlend();', 'Physics SAT activation crossfade')
forbid(ffb, 'physicsSat_.ready() ?', 'old ready/fallback switching removed')
req(phys, 'bool calibrated() const', 'calibration state separated')
req(phys, 'bool sampleValid() const', 'sample validity separated')
req(phys, 'bool torqueActive() const', 'torque activity separated')
req(phys, 'constexpr int CalibrationSamplesRequired = 12;', 'multi-sample basis calibration')
req(phys, 'bestScore >= 0.85f && calibrationConfidence_ >= 0.25f', 'basis confidence gate')
req(phys, 'activationBlend_ = std::min(1.0f, activationBlend_ + (1.0f / 24.0f));', '24-tick Physics SAT blend')
req(phys, 'motionScale > motionScaleEma_ * 5.0f', 'restart/warp discontinuity guard')
req(phys, 'if (speedNorm <= 0.04f)', 'stopped-car dynamic state reset')
req(phys, 'headingDelta * 60.0f', 'fixed 60 Hz yaw-rate derivative')
req(phys, 'roadWheelAngle - bodySlip_ - yawRate_ * yawLeadSeconds', 'front-slip proxy')
req(phys, '(frontSlip_ > 0.0f ? -1.0f : 1.0f)', 'SAT direction follows front slip')
req(phys, 'car->spd_mb_20.x', 'spd_mb telemetry retained')

req(wheel_ui, 'Test Left (20%)', 'safe left test')
req(wheel_ui, 'Test Right (20%)', 'safe right test')
req(ffb, 'DI_FFNOMINALMAX', 'nominal DirectInput device gain')
req(ffb, 'WheelFFB: scheduling DirectInput device reinitialization', 'device recovery path')
req(ffb, 'SnowIceRoadTextureScale = 0.04f', 'snow/ice periodic attenuation')
req(ffb, 'std::isfinite', 'non-finite input/output guards')

req(wheel_ui, 'Load MOZA R3 Physics SAT v1', 'Physics SAT preset')
req(wheel_ui, 'Load MOZA R3 Natural SAT', 'Natural SAT A/B preset')
req(wheel_ui, 'Settings::WheelFFBInvertForce = true;', 'R3 ConstantForce direction baseline')
req(wheel_ui, 'Settings::WheelFFBInvertSpring = false;', 'R3 Spring direction baseline')
req(wheel_ui, 'Settings::VibrationMode = 0;', 'R3 preset disables gamepad rumble')
req(ffb, 'phys={} basis=M70r{} cal={:.2f} mix={:.2f}', 'Physics SAT diagnostic telemetry')
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
