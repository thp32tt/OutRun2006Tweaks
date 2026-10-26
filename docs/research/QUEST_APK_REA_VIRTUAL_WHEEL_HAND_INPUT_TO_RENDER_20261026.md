# Quest APK Cockpit: REA VirtualWheel/hand render / predicted XR time recovery (2026-10-26 KST)

## Scope
Authorized offline inspection of user's OutRun Quest APK only, `liboutrun_quest_core.so` SHA256 `fa0f9db9b744515a9a1439741bc9806ad007470b621b88d22a0b8cbced6120b6`. PCVR target `thp32tt/OutRun2006Tweaks` `vr-d3d9ex-focus` R26+HUD. **RESEARCH ONLY**: no `src/` changes, no Windows or PC runner, no GitHub Actions build and no Quest3 visual test. Native AArch64 ELF virtual addresses, not disassembler image-base-adjusted values.

This report extends `QUEST_APK_REA_CAMERA_OVERRIDE_HAND_TLSDESC_20261026.md`, and does not re-score previous achievements.

## A. NEW: Full XR clock and controller-input call chronology, original native bytes

Quest's `outrun::quest::XrSessionHost::begin` `0x2D9B18`, original disassembly near:
- `0x2D9C40`: `xrWaitFrame` produces the predicted display time.
- `0x2D9C68`: `xrBeginFrame`.
- `0x2D9CA0`: `XrRig::input(bool)` (action state).
- `0x2D9CCC`: loads **`XrSessionHost+0x1F8`** (504 decimal) predicted time into `x1`.
- `0x2D9CDC`: calls `XrRig::locate(predictedTime, recenterFlag, StereoFrame&)`.
- `0x2D9CE0..0x2D9CE8`: records success and branches on failure.
- **Only if stereo locate succeeds:** `0x2D9CEC` reloads **the same host `+0x1F8` predicted time** and `0x2D9CF8` calls `XrRig::locate_hands(predictedTime,TouchFrame&)` with that exact timestamp.
- `0x2D9D00+`: gameplay rendering continues. The call to `VirtualWheel::update` occurs in the game's PadSnapshot producer, described below.

This establishes **temporal alignment of hand tracking and both eyes in the original Quest design**. The same timestamp is input to both location routines; it does not by itself prove that later gameplay and display callbacks receive an immutable snapshot.

## B. NEW: VirtualWheel native steering path, precise signed game-axis conversion

The original game input callback `run_game::$_2::operator()() → PadSnapshot` at `0x2E13AC`:
- `0x2E19D4..0x2E1A04` computes VirtualWheel activation from gameplay `guestState+0x9954==0x10`, camera view 1 at guest (+0x94C5A), session and controller gating.
- `0x2E1A0C..0x2E1A2C` calls `VirtualWheel::update(bool, array<WheelPoint,2> const&, array<bool,2> const&, array<float,2> const&, float, float)` by the PLT at `0x1221BC0`.
- The input frame pointer at closure `+0x10` is the Quest `TouchFrame` producer, and the call directly passes **`TouchFrame+0x74`** (two hand-valid booleans) and **`TouchFrame+0x78`** (two floats, semantics need direct naming proof). It passes wheel-angle/tuning floats from separate captured pointers; it does *not* pass the rendering hand TLS pointer.
- `0x2E1A30` branches if VirtualWheel update returned false, **without writing a new game-steering axis**.
- When update returned true, `0x2E1A34..0x2E1A84` reads `VirtualWheel+0x04` steering angle, divides by native constant **−1.3089970350265503f**, clamps result to `[-1,1]`, multiplies by **32767.0f**, does AArch64 **FCVTZS (truncate toward zero)** and writes the 32-bit result to **`PadSnapshot+0x20`**.
- Thus a compact independent reference expression:
  `guestSteer = trunc(32767.0f * clamp(wheelAngle/-1.308997035f,-1,1))`.
- The native angle range is ±1.308997 rad ≈ ±75°, and its **sign is inverted** at the game-input mapping. The transform is only active if VirtualWheel actually accepted the frame.

A research-only N100 Python float32 fixture `apk/_analysis_focus/quest_20261026_virtualwheel_steer_fixtures.py` checked center, half-lock, full-lock, over-lock and the failure/no-write path:
- Wheel angle (0) -> guest 0;
- (+)full-lock -> **−32767**, (−)full-lock -> **+32767**;
- (+)half-lock -> **−16383**, (−)half-lock -> **+16383** (float32 truncation);
- angles beyond ±75° saturate.
**These are arithmetic fixtures, not a working Quest3 steering test.**

Native `VirtualWheel::update` ELF **`0x2E1E18`**, symbol size 1248 bytes:
- REA 6.5.0/Ghidra 12.1.4 was executed now, evidence `ev_baa70ecce97e329628fc78178effec1da63c7ec44e44882ec8cf86d8f77c9868`, 4346 pseudocode chars, **one type-propagation warning**, relationship coverage partial. Native code contains `sincosf`, `atan2f`, `hypotf`, `remainderf`.
- Two per-hand state bytes are written at `VirtualWheel+0/+1`; two hand-arming flags at `+0x10/+0x11`; accumulated game wheel angle is `+0x04`; last per-hand angles at `+0x08/+0x0C`.
- REA indicates approximate acquire/release thresholds 0.13/0.30 in wheel-plane distance, 0.65 for hand grip, angular ±0.1/0.25 and wrapped incremental angular delta `<0.5`. These thresholds' **exact phase semantics require full control-flow revalidation**, since the partial recovered pseudocode has a type-propagation warning and merged branches.
- ***Do not enable hand steering automatically in the PCVR port***. The user's existing MOZA wheel axis and FFB must remain authoritative unless an explicitly selected virtual-controller mode is in force.

## C. NEW: independent two-slot render path plus exact guest hand call arguments

Quest rendering uses a **separate** path from VirtualWheel:
- Native `run_game::$_0` `0x2E315C` enables the TLS pointer `cockpit_hand_tracking` only for qualified driver callback scope `0x4879B0`, game state and camera mode.
- `Draw::disp_514c30` `0xD61D28..0xD61E18` updates tracking-context `+0x10C,+0x110,+0x114,+0x118` indexed guest hand-object state, checks flags `trackingCtx+0x102/+0x103`, and prepares two calls to `Draw::hand_513e40`.
- Native **`0xD61E3C` explicitly passes `w4=0`** into the first `Draw::hand_513e40` invocation at `0xD61E40`; native **`0xD61E60` explicitly passes `w4=1`** into the second at `0xD61E64`.
- In `Draw::hand_513e40` ELF `0xD62F5C`, `0xD6300C..0xD63018` tests `trackingCtx[0x100 + w4]`. This **independently proves slot 0/1 corresponds to the two actual hand calls**. Do not conflate the tracking context with the much smaller `TouchFrame`, whose two validity bytes are at +0x74/+0x75.
- Native `Draw::hand_513e40` also multiplies a 64-byte guest bone matrix and base model transform. It is **not** a direct copy of the OpenXR pose into an actor's world matrix; original mesh/bone calibration remains missing.
- The public reverse-engineered PC implementation `r4dius/outrun2-decomp/src/platform/rob_disp.cpp` has a three-argument `hand_513e40(mot,b,obj)` and calls it twice with guest motion/bone/object values. The Quest version has an **additional fourth integer argument** (fifth AArch64 method parameter, `w4=0/1`) to select the tracked hand slot. This difference is important for a behaviorally equivalent port.
- `Draw::disp_514c30` invokes an additional lambda at ELF `0xD62DD0` twice to resolve `HandEntry` guest indices/objects. The separate lambda was now run through REA; Evidence ID `ev_013976bd60a1e0c29040a2441fd031d26fd4dc91b52bd984e241bb3f97e75e82`, 2273 pseudo chars, **three warnings**, so do not claim complete object/bone index recovery.
- Hand input path and rendering hand-matrix path have **different owners and acceptance gates**. The actual bridge from TouchFrame to rendering `trackingCtx` remains a separate tracing task.

## D. Clean-room C++ contract, intentionally not production-included

Added research-only `docs/research/quest_virtual_wheel_input_contract_20261026.hpp`:
- `GuestSteerFromVirtualWheel(updateSuccess, angle)` returns optional signed game-axis integer and preserves existing joystick/wheel axis when empty.
- separate named TouchFrame validity offsets +0x74/+0x75 and render-hand TLS slot flags +0x100/+0x101;
- zero writing to any live game memory, no DLL hook, no setter for MOZA FFB;
- retains strict `std::isfinite` and clamped input handling for a safe C++ reference.

No new PCVR joystick changes or headset claims. No `src/` edits.

## E. Remaining prioritized recovery tasks

1. Resolve precise Quest `VirtualWheel::update` branch / hand-grab acceptance and its two wheel points' coordinate frame from guest `run_game::$_2`.
2. Identify the owner, allocation and producer of `trackingCtx+0x100/+0x101` validity values and `+0x10C..+0x118` guest hand indices: prove or disprove whether `TouchFrame` is mapped 1:1 into tracked model state.
3. Complete tracked controller grip to steering wheel and virtual hand bone matrices, with car-specific axis calibration; no HMD hardware test yet.
4. Keep the previously recovered vehicle `matrix_B0/F0` correction and real camera mode1 original table separate from headset XR eye/hand transforms; unify predicted display time and per-frame generation.
5. Confirm exact per-player windshield PMT material ownership before any alpha/opacity runtime patch.

`SOURCE_CHANGE=NO`; `RESEARCH_ONLY=YES`; `CI_BUILD=NOT_RUN`; `HMD_RUNTIME_VALIDATION=UNTESTED`.
