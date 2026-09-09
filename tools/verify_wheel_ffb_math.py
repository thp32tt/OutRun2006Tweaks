from pathlib import Path
import math

src = Path("src/hooks_wheel_ffb.cpp").read_text(encoding="utf-8")

# Keep this numeric audit tied to the actual formulas compiled by the wheel
# branch.  If the C++ formula changes, this verifier must be intentionally
# updated rather than silently testing an obsolete model.
required_fragments = [
    "std::pow(speedNorm, 1.60f)",
    "cornerLoad * static_cast<float>(Settings::WheelFFBSpringLoadBoost)",
    "dampingSpeed =",
    "0.10f + 0.90f * std::pow(speedNorm, 1.30f)",
    "0.25f + 0.75f * gripFactor",
    "std::clamp((roughness - 0.30f) / 0.55f, 0.0f, 1.0f)",
    "std::tanh(total)",
]
for fragment in required_fragments:
    if fragment not in src:
        raise SystemExit(f"MATH VERIFY FAILED: C++ formula fragment missing: {fragment}")


def speed_curve(speed: float, low_speed: float = 0.08) -> float:
    return max(0.0, min(1.0, low_speed + (1.0 - low_speed) * speed ** 1.60))


def spring(speed: float, lat: float, grip: float,
           strength: float = 0.45, low_speed: float = 0.08,
           load_boost_setting: float = 0.35) -> float:
    curve = speed_curve(speed, low_speed)
    corner_load = max(0.0, min(1.0, abs(lat)))
    boost = 1.0 + corner_load * load_boost_setting
    return max(0.0, min(1.0, strength * curve * boost * grip))


def damper(speed: float, grip: float, strength: float = 0.35) -> float:
    damping_speed = 0.10 + 0.90 * speed ** 1.30
    damping_grip = 0.25 + 0.75 * grip
    return max(0.0, min(1.0, strength * damping_speed * damping_grip))


def texture(roughness: float) -> float:
    return max(0.0, min(1.0, (roughness - 0.30) / 0.55))


# 1. Speed-based aligning force must be monotonic for a fixed load/grip.
speeds = [i / 100.0 for i in range(101)]
curves = [speed_curve(s) for s in speeds]
if any(b + 1e-9 < a for a, b in zip(curves, curves[1:])):
    raise SystemExit("MATH VERIFY FAILED: aligning speed curve is not monotonic")

springs = [spring(s, lat=0.5, grip=1.0) for s in speeds]
if any(b + 1e-9 < a for a, b in zip(springs, springs[1:])):
    raise SystemExit("MATH VERIFY FAILED: spring output decreases with speed at fixed grip")

# 2. Corner load may strengthen aligning torque, while grip loss must unload it.
loaded = spring(0.8, lat=1.0, grip=1.0)
straight = spring(0.8, lat=0.0, grip=1.0)
drifting = spring(0.8, lat=1.0, grip=0.35)
if not (loaded > straight > 0.0):
    raise SystemExit("MATH VERIFY FAILED: corner-load spring boost is ineffective")
if not (0.0 <= drifting < loaded):
    raise SystemExit("MATH VERIFY FAILED: deep drift does not unload spring")

# 3. Dynamic damper must grow with speed and relax with grip loss.
if not (damper(1.0, 1.0) > damper(0.0, 1.0) > 0.0):
    raise SystemExit("MATH VERIFY FAILED: damper speed scaling is invalid")
if not (damper(1.0, 0.35) < damper(1.0, 1.0)):
    raise SystemExit("MATH VERIFY FAILED: drift does not relax damper")

# 4. Normal asphalt baseline (~0.25) must not create constant road buzz.
for r in (0.0, 0.10, 0.25, 0.30):
    if texture(r) != 0.0:
        raise SystemExit(f"MATH VERIFY FAILED: asphalt roughness {r} produces vibration")
if not (0.0 < texture(0.50) < texture(0.85) <= 1.0):
    raise SystemExit("MATH VERIFY FAILED: rough-surface texture ramp is invalid")

# 5. Exhaustive coarse-domain check: all condition strengths stay finite/in range.
for speed in [i / 20.0 for i in range(21)]:
    for lat in [i / 10.0 for i in range(-10, 11)]:
        for grip in [i / 20.0 for i in range(21)]:
            s = spring(speed, lat, grip)
            d = damper(speed, grip)
            if not (math.isfinite(s) and 0.0 <= s <= 1.0):
                raise SystemExit("MATH VERIFY FAILED: spring out of bounds")
            if not (math.isfinite(d) and 0.0 <= d <= 1.0):
                raise SystemExit("MATH VERIFY FAILED: damper out of bounds")

# 6. 270-degree R3 sanity: 20% would be +/-27 degrees; the branch default is 0%.
rotation = 270.0
half_rotation = rotation / 2.0
angle_by_percent = {p: half_rotation * p / 100.0 for p in (0, 1, 2, 5, 20)}
if abs(angle_by_percent[20] - 27.0) > 1e-9:
    raise SystemExit("MATH VERIFY FAILED: 270-degree deadzone sanity check")

print("Wheel FFB numeric invariants passed")
print(f"speed curve: low={curves[0]:.4f}, mid={speed_curve(0.5):.4f}, high={curves[-1]:.4f}")
print(f"spring @80% speed: straight={straight:.4f}, loaded={loaded:.4f}, deep-drift={drifting:.4f}")
print(f"damper: stopped={damper(0.0, 1.0):.4f}, high-speed={damper(1.0, 1.0):.4f}, drift={damper(1.0, 0.35):.4f}")
print("270deg center deadzone half-angle:", ", ".join(f"{p}%={a:.2f}deg" for p, a in angle_by_percent.items()))
