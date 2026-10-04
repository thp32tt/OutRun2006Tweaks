# DX11 Fixed Function Negative Fixture R199

## Purpose

Document the next static probe contract after R198. This fixture keeps unsupported fixed-function argument selectors fail-closed while the DX11 conversion lane remains dormant until full evidence gates pass.

## Contract

- Backend: DX11 native conversion lane
- NativeDrawPathActive: unchanged disabled
- Runtime validation: UNTESTED
- Scope: static probe expectation only

## Negative cases

1. A stage argument selector that cannot be represented by the DX11 fixed-function translator must produce `FixedFunctionUnsupportedArgument`.
2. Missing resource provenance must not be converted into a valid shader-ready state.
3. A fixture must not use a negative selector case as proof of runtime rendering correctness.

## Validation expectation

The corresponding probe should assert the unsupported mask before any future promotion of a fixed-function state into a draw candidate.
