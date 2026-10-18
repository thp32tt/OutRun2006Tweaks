# FFB v0.2 / original OutRun 2006 cross-review (2026-10-18)

Scope: static review of `wheel-ffb-v0.2-dev` (`src/hooks_wheel_ffb.cpp`, `src/hooks_wheel_vehicle_dynamics.hpp`, `src/wheel_ffb_math.hpp`) and 7,237 locally recovered Ghidra functions. No HMD / MOZA R3 runtime validation. Proprietary binary and decompiler output remain on N100, not in this repository.

## Confirmed
- FFB `read_game_steering()` calls original `0x53720` via `Module::fn_ptr` when legacy input is selected; SDL input uses `InputManager_SteeringValue()`. Original `FUN_00453720` selects a player-indexed input channel. Validate calling convention and ADChannel mapping before altering the hook.
- Original `FUN_004a8330` snapshots vehicle current position `+0x14..+0x1c` into `+0x16c..+0x174`, copies gear `+0x208` to `+0x1d8`, and invokes `FUN_004a50f0` followed by `FUN_004a8100`. `FUN_004a8100` invokes `FUN_004a2fa0` and later `FUN_004a4900`. This establishes a useful ordering constraint, not an externally safe read point.
- `FUN_004a50f0` uses speed-like `+0x1c4`, gear `+0x208`, and input channels 1/2. `FUN_004a2fa0` writes bounded `+0xd38` from fields `+0x4e,+0x16a,+0x202,+0x26c` and a parameter table. Physical meaning of `+0xd38` is unproven.
- `WheelVehicleDynamics::update` derives motion from `position_14`, yaw from `matrix_70`, and uses 60 Hz fixed-step math. `spd_mb_20` is currently correlation telemetry only, appropriately.
- `WheelFFBEngine` has device reacquire, foreground checks, zero-force transitions, watchdog, slew limits, sign-reversal release, and fallbacks. These safeguards should remain.

## Review findings / action queue
### P1 — vehicle identity and calibration lifetime (candidate)
`WheelFFBEngine` detects `lastCar_ != car` and calls `reset_signal_state()`, which calls `vehicleDynamics_.reset_dynamic()`. That intentionally preserves `forwardAxis_`, `forwardSign_`, and calibration. Determine whether pointer changes imply different vehicle/matrix basis. If yes, invoke full `vehicleDynamics_.reset()` **only on confirmed vehicle identity change**. Avoid clearing calibration for ordinary overlay/focus transitions. Add regression tests for car switch vs menu resume.

### P1 — fixed-step cadence assumption (requires evidence)
`WheelVehicleDynamics` uses `headingDelta*60`, `(steer-prevSteer)*60`, and FFB synthesized phase uses `frequency/60`. Trace the FFB hook entry against the original 60 Hz simulation tick and detect repeated/missed update calls. Do not blindly switch to wall-clock dt; first establish hook cadence, and prevent duplicate integration per simulation tick if observed.

### P2 — native previous-position snapshot (instrumentation)
Use original `+0x16c..+0x174` as **read-only diagnostic comparison** to the estimator's `position_14` delta; verify both are from the same update phase before relying on it. Never assume original prior-position data are safe to read mid-update.

### P2 — native velocity vector (instrumentation)
Log normalized `spd_mb_20` direction and scale correlation with position deltas, including reversing, stationary, drift, warp, and car transitions. Retain existing estimator as authoritative until tests prove the native vector's coordinate space.

### P2 — steering channel and SAT sign
Original `FUN_00453720` reads player-indexed channel data; inspect x86 disassembly to confirm convention, channel indexing and signed range. Verify SDL vs legacy steering parity and FFB inversion via low-strength direction tests; do not change torque signs based solely on pseudocode.

### P3 — bounded vehicle control `+0xd38`
Trace readers of `+0xd38` and producers of `+0x4e,+0x16a,+0x202,+0x26c` before naming these as physical quantities. Do not connect to SAT until semantics and update phase are established.

## Acceptance criteria
1. Repeatable static call graph and update ordering with assembly-backed convention checks.
2. Diagnostics for tick cadence, vehicle identity, native previous-position, native velocity correlation, with finite-value and transition guards.
3. Automated tests for same-car pause/resume, actual car change, repeated tick, skipped tick, reverse, warp and invalid samples.
4. Exact branch SHA build/CI results; actual MOZA R3 runtime test separately marked `RUNTIME_VALIDATION=UNTESTED` until performed.

## Current status
Review findings only; no FFB gameplay code changed. Not a claim of a confirmed torque bug. Local evidence: N100 `rea-analysis/FFB_ORIGINAL_DECOMP_TRACE_20261018.json` and `rea-analysis/FFB_ORIGINAL_REVERSE_UPDATE_20261018.md`.
