# OutRun VR custom DXVK overlay

This directory turns the official **DXVK v3.1.1** source tree into the OutRun VR
experimental provider without requiring the application repository to vendor the
entire DXVK source history.

## Why this is an overlay first

The connected GitHub automation can edit this repository but cannot create a
new GitHub repository/fork. The transformation in `apply_out_run_vr.py` is
therefore kept deterministic and pinned to the official v3.1.1 tag. A later
standalone DXVK fork can apply the same changes as normal commits.

## Milestone 1: capability handshake

The first provider implements the private
`ID3D9OutRunVRInterop` protocol-v1 COM interface.

It intentionally returns `S_FALSE` from `ArmStereoDraw`. This is not a stub
that pretends stereo succeeded: it is a fail-closed compatibility milestone.
The game-side bridge only skips its second D3D9 draw when the provider returns
exactly `S_OK`. Therefore this milestone can be installed and diagnosed
without risking a one-eye frame.

The provider also exposes counters so later milestones can prove that draw
ownership is actually being consumed.

## Build

The GitHub workflow clones official DXVK v3.1.1 recursively, runs:

```sh
python3 dxvk-fork/apply_out_run_vr.py dxvk-src
```

and then uses the same Arch Linux MinGW build approach as upstream DXVK's own
artifact workflow. The resulting **x86 `d3d9.dll`** is the file OutRun 2006
needs beside the game executable.

## Next provider milestone

Returning `S_OK` is allowed only when all of these are true:

1. the incoming D3D9 draw is consumed exactly once;
2. the left/right WVP values select the correct eye in the translated vertex
   shader;
3. left and right color/depth output are written by that consumed draw;
4. query, state-block, depth/stencil and Reset semantics remain unchanged;
5. the provider can reject any unsupported route before consuming it.

The open upstream DXVK D3D11 NVAPI multiview work is useful architectural
reference for shader/pipeline state handling, but it is not copied directly:
OutRun is D3D9 and needs eye-specific c64-c67 replacement.
