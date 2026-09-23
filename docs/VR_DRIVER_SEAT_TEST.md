# Clean driver-seat test branch

Branch: `vr-driver-seat-clean`

This branch was rebuilt from the clean pre-driver-seat integration point
`4dec95cd07ca1c0907c1ba8b36caccbb0370f6e5`, then only the latest runtime
test-profile safety policy was carried forward. None of the previous
driver-seat WVP experiments are inherited.

## Scope

- Native bumper/in-car camera remains the synchronization owner.
- Camera position is offset immediately before the game's native
  `CalcCameraMatrix`, then the camera work values are restored.
- Player-car render-state bits are isolated in the driver-seat module.
- `DriverSeatCarRenderState=-1` learns the render state used by native
  camera mode 0 and reuses it in the driver-seat camera. 0/1/2 can be selected
  manually from F11 for diagnosis.
- Driver suppression is based on the game's live driver chrset table.
  Heroine/passenger chrsets are explicitly preserved.
- No late-WVP driver-seat transform is present.

## Initial test

1. Start with native third-person once so AUTO can learn its player-car state.
2. Switch to native camera mode 1.
3. Confirm the car is present.
4. Change DriverSeatForward/Right/Up by a large amount in F11 and confirm
   immediate movement.
5. Confirm driver is hidden and heroine/passenger remains.
6. Upload the generated log ZIP; the log includes camera mode, car render state,
   and robot driver/heroine classification.
