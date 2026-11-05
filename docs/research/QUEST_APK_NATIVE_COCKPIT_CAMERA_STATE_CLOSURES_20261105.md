# Quest APK cockpit camera source and scope re-audit (2026-11-05 KST)

## Original APK ARM64 control/dataflow; independently re-read exact code

Original user-owned Quest ELF under the N100 private/home input (never redistributed): `liboutrun_quest_core.so`. The entries are the actual ARM64 instructions and symbol addresses, not generated guesses.

1. Original `android_main` `0x2DBAA4..0x2DBB10` allocates a **120-byte** `run_game::$_2` PadSnapshot lambda, vtable pointer `0x1237FD8+16=0x1237FE8`. At `0x2DBAE4`, `x8=sp+0x350`; `0x2DBAEC a9042408` captures `[lambda+0x40]=sp+0x350` and `[lambda+0x48]=sp+0x60`. These two captures must not be confused with the *next* 80-byte `run_game::$_3` NativeInputState callback at `0x2DBB50`, which captures `sp+0x64` for its own input path.
2. The actual `run_game::$_2` `0x2E14E8` reads guest-profile output pointer `x12=[lambda+0x40]`, therefore the original destination is `sp+0x350`. The 30-record guest pointer `0x5B2F68[selector]` is checked before X/Y/Z copies `0x2E1598` (`[x12]`), `0x2E1650` (`[x12+4]`), `0x2E16C4` (`[x12+8]`).
3. `0x2E17F4..0x2E1808` reads/stores the **same** `[lambda+0x40]` Y/Z doubleword, adding the verified ELF data `+0.319999993/+0.550000012`. The earlier contradictory hypothesis that this was another controller-only vector is refuted by the exact closure capture, not just by similar constant values. The original guest's 30×0x128 record input remains distinct from the 30×36 legacy PC view1 table.
4. Independently the original `run_game::$_5` at `0x2E3664..0x2E36C8` consumes the **same sp+0x350** as the XYZ source. `android_main` `0x2DC03C/0x2DC054` stages it in the callback capture, and `0x2DC0F0` stores it at `[lambda+80]`. `0x2E3690` reads the captured toggle, `0x2E369C..0x2E36B4` checks guest current-state integer exactly `0x10`, and `0x2E36BC..0x2E36C8` copies the 12-byte XYZ into `PcRaceCameraInputs[4..15]`. Another upstream boolean callback must succeed.
5. `src/game.hpp` on this PC branch maps `STATE_START=0x0D`, `STATE_GAME=0x10`, `STATE_GOAL=0x13`. The earlier PC implementation patched *all* 30 camera anchors whenever the cockpit option was enabled, including START/GOAL. Source fix at commit `db36005dcd92800e20077d1aa7704b0e9bdab7e5` restores original camera anchors when the current guest state is not `STATE_GAME`, and gates the game-side native HMD view to the same state. Source helper `OriginalQuestGameCameraState` is regression-tested for 0x0d/0x10/0x13/0x1b. This is a **necessary** admission condition, not a claim that the additional native PadSnapshot toggle has been recovered.

## Outstanding dynamic renderer and optics parity

- `run_game::$_2` `0x2E1B00..0x2E1D18` contains two per-eye angle-dependent branches with `sincosf`, `atan2f` and `inverse(XrPosef)`/`view_matrix` calls. Their full angular composition is not yet ported. Hard-coding the old +0.04 angular term as a global eye translation is forbidden.
- The PC game renderer's yaw-relative view and OpenXR host's `projection.space=localSpace` must remain distinct; mixing their coordinate spaces previously caused counter-rotation/parallax risk. Retain the verified local-space Frame.v2 patch from `8a28fe3a`.
- F0 vehicle body/suspension presentation still differs: the original Quest's body-local staging is not yet proven equivalent to PC's disabled-by-default scoped F0 A/B path. Do not enable the potentially crash-prone scope for the default build.
- Original APK exact guest memory contents, PadSnapshot toggle, and live Quest HMD visual output remain unverified. Build/test CI is not proof of visual identity.

## Copy-run user packaging

The branch's new `QuestCockpit-CopyRun.ps1` + `RUN-QUEST-APK-COCKPIT.cmd` are a completely install-free front end: extract into the existing `OR2006C2C.EXE` directory, double-click the launcher; first run checks source identity & x86 DLL/x64 host SHA256 and backs original DLL/host/DXVK/config/scripts/sessions before activation. No top-level pre-existing binaries or INI are in the dedicated ZIP; the game's original executable, PMT/texture/car models and `OutRun2006Tweaks.user.ini` are never modified on extraction.
