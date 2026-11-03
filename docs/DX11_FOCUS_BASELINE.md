# DX11 Focus baseline

Default stable runtime: exact published DX9Ex Focus v0.01 release, source SHA `5d68d900deeccc003c4c8bf0e5eb46614eaa3302`, ZIP SHA256 `66e6b8cfdea6bbe28d45778d9663466ba0d212c0e6027b518ec3800db9f50959`.

The Focus launcher and conservative runtime profile are mirrored here. The existing DX11 native source under `src/vr/d3d11/` stays unchanged. Do not assume that the existing DX11-built DLL is identical to the Focus release DLL: for a real Focus baseline use the exact published Focus binaries. DX11 native rendering remains an opt-in experiment controlled by the environment variable `OUTRUN_DX11_FIRST_GAME_FRAME=1` and is not HMD-runtime verified. Do not replace the DX11 renderer sources with DX9Ex sources blindly.

Run `Start-OutRun.cmd` for 2D/VR choice or `Start-OutRun-VR.cmd` for Focus-profile VR. Use `Start-OutRun-DX11-Experimental.cmd` to explicitly enable bounded DX11 first-game-frame diagnostics without changing your fallback configuration. For a binary-identical Focus baseline, install the v0.01 Focus release ZIP. Source graph and all DX11 translation units are preserved.
