# OutRun2006Tweaks Wheel FFB v0.1

Unofficial wheel / force-feedback fork for **OutRun 2006: Coast 2 Coast**, based on [emoose/OutRun2006Tweaks](https://github.com/emoose/OutRun2006Tweaks).

This release is focused on modern multi-device driving setups and native wheel force feedback. It was developed and hardware-tested primarily with a **MOZA R3**. Other DirectInput wheels may work, but v0.1 should be treated as unverified on hardware that has not been reported by users.

This is not an official SEGA, MOZA, or upstream OutRun2006Tweaks release.

## v0.1 highlights

- SDL3 raw multi-device input for wheel, separate pedals, shifter, button box and gamepad.
- One canonical **Input Bindings** path for steering, pedals and buttons.
- Axis calibration for steering / accelerator / brake.
- Native Windows DirectInput COM force feedback; no vJoy or external FFB mapper required.
- Physics SAT with Natural SAT fallback, mechanical/caster trail, grip-loss unloading and dynamic damping.
- Low-speed centering spring kept intentionally light so it does not hide SAT.
- Road / curb tactile feedback, including MOZA R3 ConstantForce fallback and snow-stage curb handling.
- Gear-shift and collision feedback.
- Exact DirectInput FFB device identity, reconnect handling, focus-loss cleanup and 20% safe direction tests.
- MOZA R3 automatic DirectInput name matching on a clean setup.

## Install

1. Back up your game folder and save data.
2. Extract **OutRun2006Tweaks-Wheel-FFB-v0.1.zip** into the `OutRun 2006 Coast 2 Coast` game directory.
3. Replace files when prompted. The package includes the replacement `OR2006C2C.exe` distributed by the upstream OutRun2006Tweaks v0.1 release.
4. Connect and power on the wheel and pedals before starting the game.
5. Open the in-game overlay with **F11**.
6. Configure steering, pedals, shifter and buttons in **Input Bindings**. After manual edits, use **Save & Return to game** to persist the bindings before leaving the screen.
7. Open **Force Feedback**. On MOZA R3 the FFB interface should normally auto-match; otherwise use **Refresh Devices** and select the actual FFB device.
8. Use the 20% left/right direction tests before raising wheel-base torque. If the steering force is reversed, change `Reverse SAT / ConstantForce`. Change `Reverse Spring` only when the spring itself pushes away from center.

## MOZA R3 notes

The tested R3 path deliberately favors the game's SAT over artificial centering. The v0.1 R3 compatibility layer uses the ConstantForce fallback for road texture because the driver can report sine-effect support without producing useful physical road detail on the tested wheel.

The F11 Force Feedback page still provides `Load MOZA R3 Physics SAT` and `Load MOZA R3 Natural SAT` as starting profiles. The live R3 compatibility layer then applies the R3-specific road-output handling used by this release.

For curb / shoulder contact, the code compares all four wheel-surface samples. A mixed surface is detected while only part of the car is on the curb, and a fully rough surface remains tactile after the car crosses completely onto it. Snow stages receive additional compensation so curb detail is not lost under the snow-road attenuation.

The exact feel still depends on wheel-base firmware and MOZA Pit House settings. Keep base-side centering, damping, inertia and friction conservative while evaluating game-side FFB.

## Troubleshooting

- **No steering/pedal input:** check the live device values under F11 and rebind in **Input Bindings**.
- **No FFB:** open **Force Feedback**, Refresh Devices, then select the actual DirectInput FFB interface.
- **R3 not selected automatically:** select `R3 Racing Wheel and Pedals` manually once; the exact DirectInput GUID is saved afterward.
- **Pedal direction/range wrong:** recalibrate that axis in Input Bindings.
- **Force pushes away from center:** verify `Reverse SAT / ConstantForce` with the 20% direction test.
- **Need diagnostics:** attach `OutRun2006Tweaks.log` and include wheel model, driver and firmware version.

## Package contents

The public v0.1 ZIP is intentionally kept small:

- `dinput8.dll`
- `OutRun2006Tweaks.ini`
- `OutRun2006Tweaks.lods.ini`
- `OR2006C2C.exe`
- `README.md`
- `LICENSES.txt`

`LICENSES.txt` is the only additional legal-notice file in the ZIP. It is generated from the actual source/dependency trees used by the build so required open-source notices are not dropped while keeping the package uncluttered.

## Credits and license

This fork is based on **emoose/OutRun2006Tweaks** and also benefited from public work and design references from **hyp36rmax/multi-device-input** and **d-b-c-e/OutRun2006Tweaks-FFB**.

The upstream project is MIT licensed. The original notice is preserved in this repository's `LICENSE.md`, and the binary package contains the applicable bundled dependency notices in `LICENSES.txt`.

OutRun, OutRun 2006: Coast 2 Coast and related game assets belong to their respective rights holders. MOZA and other vendor names are used only to describe hardware compatibility.

## Building

The branch targets **Win32 Release** with Visual Studio 2022 and CMake. CI validates the consolidated wheel FFB source and production FFB math before building the release DLL.

See [WHEEL_FFB.md](WHEEL_FFB.md) for architecture and tuning details.
