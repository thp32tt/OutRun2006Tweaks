# OutRun2006Tweaks Wheel FFB v0.1

First public release of the `wheel-ffb` branch.

## What this release adds

- SDL3 raw multi-device input for modern wheel setups.
- One Input Bindings path for steering, pedals, shifter and buttons.
- Native Windows DirectInput COM wheel FFB.
- Physics SAT with Natural SAT fallback and mechanical/caster trail.
- Dynamic damping and grip-loss unloading.
- Low-speed centering spring kept light so it does not dominate SAT.
- Road, curb, tire, gear and collision tactile effects.
- MOZA R3 DirectInput auto-match and exact GUID persistence.
- MOZA R3 ConstantForce road-texture fallback.
- Snow-stage curb compensation and four-wheel mixed/full-rough surface detection.
- Focus/device-loss cleanup, reconnect handling and 20% safe direction tests.

## Tested hardware

Primary hardware validation for v0.1 was performed with **MOZA R3**. Other DirectInput wheels may work but are not considered verified by this release unless separately reported.

## Install

Extract `OutRun2006Tweaks-Wheel-FFB-v0.1.zip` into the OutRun 2006: Coast 2 Coast game directory and replace files when prompted.

The ZIP intentionally contains only the runtime files, the upstream replacement `OR2006C2C.exe`, one README and one consolidated open-source notice file.

## Package contents

- `dinput8.dll`
- `OutRun2006Tweaks.ini`
- `OutRun2006Tweaks.lods.ini`
- `OR2006C2C.exe`
- `README.md`
- `LICENSES.txt`

`LICENSES.txt` is generated from the actual dependency source trees used by CI so required notices are preserved without filling the release ZIP with separate license/readme files.

## Notes

- `DISCORD_SHARE_v0.1.md` is not part of the repository or release package anymore.
- Use F11 → Input Bindings for input setup.
- Use F11 → Force Feedback for output-device selection and tuning.
- On MOZA R3, road/slip texture uses the ConstantForce fallback because the hardware sine path was not physically useful in testing.
- The release is built only after the consolidated source verifier and production FFB math tests pass.

## Credits

Based on `emoose/OutRun2006Tweaks`, with public design/reference work from `hyp36rmax/multi-device-input`, `d-b-c-e/OutRun2006Tweaks-FFB`, and OutRun community hardware reports.

This is an unofficial community fork and is not affiliated with SEGA or MOZA.
