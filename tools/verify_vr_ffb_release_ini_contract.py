#!/usr/bin/env python3
"""Guard VR's shipped wheel defaults against the pinned v0.2 FFB release.

The complete v0.2 FFB model is imported; its VR installer INI must expose
the released Modern DD / Arcade / PS2 model and tuned countersteer defaults.
This contract never modifies the immutable original release files.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INI = ROOT / "OutRun2006Tweaks.ini"
EXPECTED = {
    "Model": "0",
    "PS2HostGain": "1.00",
    "CountersteerStrength": "0.72",
    "MechanicalTrail": "0.25",
    "TrailResponseLead": "0.25",
    "ResponseCorrection": "false",
    "MaxTorqueNm": "0.0",
    "EngineVibration": "false",
    "EngineIdle": "0.20",
}


def violations(source: str) -> list[str]:
    lines = source.splitlines()
    section = [i for i, line in enumerate(lines) if line.strip() == "[WheelFFB]"]
    if len(section) != 1:
        return ["expected exactly one WheelFFB section"]
    start = section[0] + 1
    stop = next((i for i in range(start, len(lines)) if lines[i].startswith("[")), len(lines))
    body = "\n".join(lines[start:stop])
    errors: list[str] = []
    if "; 2 = retired legacy Hybrid (automatically migrates to Modern DD)" not in body:
        errors.append("release v0.2 retired Hybrid migration not documented")
    if "; 3 = PS2 Original topology (Experimental)" not in body:
        errors.append("release v0.2 PS2 model not documented")
    if "; 2 = Arcade + Modern Hybrid" in body:
        errors.append("obsolete model 2 advertised")
    mapping: dict[str, str] = {}
    for line in lines[start:stop]:
        entry = line.split(";", 1)[0].strip()
        if not entry or "=" not in entry:
            continue
        key, value = (part.strip() for part in entry.split("=", 1))
        if key in mapping:
            errors.append("duplicate setting: " + key)
        mapping[key] = value
    for key, value in EXPECTED.items():
        if mapping.get(key) != value:
            errors.append(f"{key} expected {value}, got {mapping.get(key)!r}")
    return errors


def main() -> None:
    source = INI.read_text(encoding="utf-8")
    errors = violations(source)
    if errors:
        raise SystemExit("VR FFB v0.2 INI FAIL: " + "; ".join(errors))
    mutations = (
        ("Model = 0", "Model = 2"),
        ("PS2HostGain = 1.00", "PS2HostGain = 1.50"),
        ("CountersteerStrength = 0.72", "CountersteerStrength = 1.00"),
        ("; 2 = retired legacy Hybrid (automatically migrates to Modern DD)", "; 2 = Arcade + Modern Hybrid"),
        ("; 3 = PS2 Original topology (Experimental)", "; 3 = undocumented"),
        ("Model = 0", "Model = 0\nModel = 0"),
    )
    for before, after in mutations:
        if source.count(before) != 1 or not violations(source.replace(before, after, 1)):
            raise SystemExit("VR FFB v0.2 INI mutation escaped: " + before)
    print(f"VR FFB v0.2 INI PASS: {len(EXPECTED)} released defaults, {len(mutations)} negative mutations")


if __name__ == "__main__":
    main()
