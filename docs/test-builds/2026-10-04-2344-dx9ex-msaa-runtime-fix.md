# DX9Ex explicit MSAA runtime test build

- Runtime feedback: current DX9Ex HMD image remained visibly aliased versus the higher-resolution DX11 test.
- Fix: native d3d9 reference backend selects explicit 4x MSAA when supported, falling back to 2x then existing game AA.
- Runtime validation: pending Quest 3 / VDXR retest.
