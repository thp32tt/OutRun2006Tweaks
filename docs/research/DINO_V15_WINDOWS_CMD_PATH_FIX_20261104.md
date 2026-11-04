# Dino v15 R1 — Windows command argument path fix

Observed failure in `I:\game\OutRun_vr`: Windows C-runtime argument parser treated a quoted path ending in `\` as escaping the closing quotation mark, merging `--payload` and `--textures-dir` into `--game`.

Prior default: `set "GAME_ROOT=%~dp0"` followed by `--game "%GAME_ROOT%"`.

Corrected default: `set "GAME_ROOT=%~dp0."`, so the quoted value ends in a dot (e.g. `I:\game\OutRun_vr\.`), not a backslash. Corrected override: `set "GAME_ROOT=%~1\."`. Texture directory is similarly `--textures-dir "%~dp0."`. Restore receives the same fix.

The R1 ZIP preserves exactly the previous `DinoCockpitV15.exe`, V15 mesh payload, DDS textures, and VR runtime binaries. Only INSTALL/RESTORE CMD and README changed; R1 diagnostic file added.

Regression verification: native Windows C argument parsing conventions simulated for `I:\game\OutRun_vr\` and `I:\game\OutRun vr\`; all options are split correctly; old default repros merged arguments. R1 ZIP CRC PASS and binary-file byte comparison PASS.

No Windows HMD runtime validation has been reported, and previously installed game backup must be preserved.
