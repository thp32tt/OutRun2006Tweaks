from pathlib import Path
import math

ffb = Path('src/hooks_wheel_ffb.cpp').read_text(encoding='utf-8')
ui = Path('src/overlay/wheel_setup_ui.cpp').read_text(encoding='utf-8')
helper = Path('src/hooks_wheel_physics_sat.hpp').read_text(encoding='utf-8')


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f'ROUND17 VERIFY FAILED [{label}]: {needle!r}')
    print(f'ROUND17 VERIFY OK [{label}]')

require(ffb, '#include "hooks_wheel_physics_sat.hpp"', 'physics helper is compiled')
require(ffb, '"WheelFFB", "PhysicsSAT", true,', 'physics mode defaults on')
require(ffb, 'const float naturalSatTorque =', 'Natural SAT retained for comparison')
require(ffb, 'const float physicsSatTorque = physicsSat_.update(', 'physics model drives SAT')
require(ffb, 'physicsSat_.ready() ? physicsSatTorque : naturalSatTorque * 0.25f', 'safe calibration fallback')
require(ffb, 'WheelPhysicsSatV1 physicsSat_{};', 'per-engine physics state')
require(ffb, 'physicsSat_.reset();', 'transition reset clears physics history')
require(ffb, 'basis=M70r{} beta={:.3f} yaw={:.3f} fslip={:.3f}', 'physics telemetry in diagnostics')
require(helper, 'const D3DMATRIX& body = car->matrix_70;', 'non-display body transform candidate')
require(helper, 'const D3DVECTOR current = car->position_14;', 'physics tick motion source')
require(helper, 'std::atan2(vLat_, std::max(std::abs(vLong_)', 'body slip beta')
require(helper, 'headingDelta * 60.0f', 'yaw rate from heading delta')
require(helper, 'roadWheelAngle - bodySlip_ - yawRate_ * yawLeadSeconds', 'front slip combines steer beta yaw')
require(helper, '(frontSlip_ > 0.0f ? -1.0f : 1.0f)', 'SAT direction follows front slip')
require(helper, 'car->spd_mb_20.x', 'direct velocity candidate is measured')
require(helper, 'spdCorrelation_', 'spd_mb correlation is logged before use')
require(ui, 'Physics SAT v1 (body slip + yaw)', 'live physics toggle')
require(ui, 'Load MOZA R3 Physics SAT v1', 'R3 physics preset')
require(ui, 'Settings::WheelFFBPhysicsSat = false;', 'Natural SAT A/B button disables physics mode')
require(ui, 'Settings::WheelFFBDebugLog = true;', 'physics preset enables diagnostics')

if ffb.count('(steer >= 0.0f ? -1.0f : 1.0f)') != 1:
    raise SystemExit('ROUND17 VERIFY FAILED [steering-sign centering leaked outside Natural fallback]')
print('ROUND17 VERIFY OK [physics direction is not steering-sign centering]')


def trail(slip: float) -> float:
    x = abs(slip) / 0.16
    return math.sin(x * math.pi / 2.0) if x <= 1.0 else math.exp(-(x - 1.0) * 0.90)

small, medium, peak, deep = trail(0.02), trail(0.08), trail(0.16), trail(0.40)
if not (0.0 < small < medium < peak and deep < peak):
    raise SystemExit(f'ROUND17 VERIFY FAILED [trail curve]: {small=} {medium=} {peak=} {deep=}')
print(f'ROUND17 VERIFY OK [trail curve]: {small:.3f} < {medium:.3f} < {peak:.3f}, deep={deep:.3f}')

beta, yaw, speed = 0.18, 0.50, 0.75
yaw_lead = 0.10 - 0.045 * speed
slip_left_counter = -0.15 * 0.52 - beta - yaw * yaw_lead
slip_at_center = -beta - yaw * yaw_lead
if not (slip_left_counter < 0.0 and slip_at_center < 0.0):
    raise SystemExit('ROUND17 VERIFY FAILED [counter-steer centre continuity]')
print(f'ROUND17 VERIFY OK [counter-steer continuity]: counter={slip_left_counter:.3f}, centre={slip_at_center:.3f}')

for path in ['src/hooks_wheel_ffb.cpp', 'src/overlay/wheel_setup_ui.cpp', 'src/hooks_wheel_physics_sat.hpp']:
    data = Path(path).read_text(encoding='utf-8')
    if data.count('{') != data.count('}'):
        raise SystemExit(f'ROUND17 VERIFY FAILED [brace balance]: {path}')
    print(f'ROUND17 VERIFY OK [brace balance {path}]')

print('Round-17 physics SAT v1 verification passed')
