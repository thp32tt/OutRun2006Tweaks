# VR Driver Seat V4 (clean branch)

Branch: `vr-driver-seat-v4-clean`

This branch is intentionally isolated from the earlier driver-seat experiments.

## Ownership model

- Native view 1 / raw camera mode 2 owns player-car + passenger rendering.
- Native view 2 / raw camera mode 1 is sampled only as a camera reference because runtime testing showed it stays synchronized to the car.
- Native view 3 / raw camera mode 0 remains unchanged.
- Pressing Change View after native view 3 enters virtual view 4. The game itself wraps back to raw mode 2, so vehicle/passenger render ownership remains identical to native view 1.
- Pressing Change View in virtual view 4 exits to native view 1 without exposing a raw mode 3 to the game.

## Camera

While native view 2 is active, its position/look are captured in player-car `matrix_B0` local space. Virtual view 4 reconstructs that camera from the current `matrix_B0`, then applies the user offsets.

Reference defaults from the 2026-09-23 screenshot:

- Forward: -0.781
- Right: -0.066
- Up: 0.000

All three stay live in F11.

## Characters

Virtual view 4 suppresses only `EVENT_ROB01` (player driver) at the robot display wrapper. `EVENT_ROB02` (passenger/girlfriend) is not altered.

No player-car render-state bits are forced in this implementation.
