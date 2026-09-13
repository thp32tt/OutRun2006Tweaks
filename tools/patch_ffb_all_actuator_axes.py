from pathlib import Path

p = Path('src/hooks_wheel_ffb.cpp')
t = p.read_text(encoding='utf-8')
old = '''            const DWORD detectedAxis = primary_actuator_axis();
            if (detectedAxis != DIJOFS_X)
            {
                axes[0] = detectedAxis;
                hr = device_->CreateEffect(
                    GUID_ConstantForce, &effect, &constantEffect_, nullptr);
                if (SUCCEEDED(hr) && constantEffect_)
                {
                    const HRESULT probeHr = accept_candidate("detected actuator one-axis CARTESIAN descriptor", false);
                    if (SUCCEEDED(probeHr))
                    {
                        spdlog::info(
                            "WheelFFB: ConstantForce is using detected actuator offset {} instead of DIJOFS_X",
                            (unsigned)detectedAxis);
                        return true;
                    }
                    hr = probeHr;
                }
                safe_release_effect(constantEffect_, "failed detected-axis CARTESIAN constant probe");
            }
'''
new = '''            // A device may expose more than one FFB actuator object. X was
            // already tried above; probe every other reported actuator offset
            // once so enumeration order cannot hide the steering actuator.
            std::vector<DWORD> triedActuatorAxes{ DIJOFS_X };
            for (const DWORD detectedAxis : actuatorAxes_)
            {
                if (std::find(triedActuatorAxes.begin(), triedActuatorAxes.end(), detectedAxis) !=
                    triedActuatorAxes.end())
                    continue;
                triedActuatorAxes.push_back(detectedAxis);

                axes[0] = detectedAxis;
                hr = device_->CreateEffect(
                    GUID_ConstantForce, &effect, &constantEffect_, nullptr);
                if (SUCCEEDED(hr) && constantEffect_)
                {
                    const HRESULT probeHr = accept_candidate("detected actuator one-axis CARTESIAN descriptor", false);
                    if (SUCCEEDED(probeHr))
                    {
                        spdlog::info(
                            "WheelFFB: ConstantForce is using detected actuator offset {} instead of DIJOFS_X",
                            (unsigned)detectedAxis);
                        return true;
                    }
                    hr = probeHr;
                }
                safe_release_effect(constantEffect_, "failed detected-axis CARTESIAN constant probe");
            }
'''
if t.count(old) != 1:
    raise SystemExit(f'expected one detected-axis block, found {t.count(old)}')
t = t.replace(old, new, 1)
p.write_bytes(t.replace('\n', '\r\n').encode('utf-8'))

v = Path('tools/verify_wheel_ffb_current.py')
s = v.read_text(encoding='utf-8')
needle = "req(ffb, 'detected actuator one-axis CARTESIAN descriptor', 'ConstantForce can fall back to the actual enumerated actuator axis')\n"
extra = needle + "req(ffb, 'for (const DWORD detectedAxis : actuatorAxes_)', 'ConstantForce probes every enumerated actuator axis after canonical X')\n"
if s.count(needle) != 1:
    raise SystemExit('actuator verifier marker missing')
s = s.replace(needle, extra, 1)
v.write_bytes(s.replace('\n', '\r\n').encode('utf-8'))
print('Patched all reported actuator-axis probing')
