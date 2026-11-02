---
name: outrun-vr-mod-wizard
description: Use when diagnosing OutRun 2006 VR launch crashes, loader/host/OpenXR failures, DX9Ex stereo or HUD rendering regressions, cockpit camera problems, HMD-less validation, or packaging a focused Quest 3 test build.
---

# OutRun 2006 VR Mod Wizard (project adaptation)

A focused, advisory adaptation of [VR Mod Vibecoding Wizard](https://github.com/bigbossafman/VR-Mod-Vibecoding-Wizard) (upstream main `40382b390e239f354ea3cecd1f9151c455883d7c`, MIT). This is **not** a new rendering engine, automatic patcher, or proof that any runtime defect is fixed.

## First read and precedence

1. Read repository `AGENTS.md` and `docs/VR_SUPERPOWERS_POLICY.md`; their latest explicit user overrides win.
2. Use GitHub HEAD as the source of truth. Respect the current DX9Ex R26+HUD default, protected HMD-known-good baseline, backend separation, existing task ownership, exact-SHA CI and user-only Quest 3 verification. Do not resurrect stale R84-mainline instructions.
3. Read only relevant existing records: `docs/VR_CRASH_SIGNATURES.json`, `docs/VR_BINARY_CONTRACT.json`, `docs/DX9EX_TEST_LAUNCH_CONTRACT.md`, `docs/VR_HUD_KNOWN_GOOD_RESTORE_RUNBOOK.md`, `docs/VR_TEST_STRATEGY.md`, `docs/VR_HMDLESS_DEBUG.md`, or issue-specific logs.
4. Reuse existing run/issue/regression records. Do **not** create a second wizard setup questionnaire, duplicate score, phase-plan tree, task ID, log framework, or workflow controller.
5. Never equate docs, a successful build, synthetic stereo, or CI with Quest 3/VDXR runtime success. Until a matching user headset test, `RUNTIME_VALIDATION=UNTESTED`.

## Route A: startup crash or legacy builds all failing

When previously working releases now fail on the same PC, treat environment/loader/runtime changes as a **hypothesis**, not a proven cause. Do not repeatedly rebuild or modify the game first.

1. **Establish identities**: exact original `OR2006C2C.EXE` hash/version; selected DLLs (x86 `dinput8.dll` and any proxied DLLs), x64 `outrun-vr-host.exe`; selected 2D/VR launcher, PS1/INI; ZIP or installed payload SHA; Windows, graphics driver, OpenXR runtime, Virtual Desktop/VDXR, other recently installed mods. Compare one verified failing copy with an unchanged previously working package; do not assume file modification.
2. **Construct the four-way isolation matrix**, changing one variable at a time:
   - original 2D game without VR DLL injection;
   - official 2D launcher with packaged mod/FFB and VR disabled;
   - official VR launcher with the exact intended game DLL and x64 host;
   - one independently archived known-good VR build on the same machine.
   Record for each: starts/white screen/exits, process PID and exit code, module exception, host process lifetime, config and whether HMD/OpenXR was reached. Do not use a destructive global DLL cleanup or overwrite evidence.
3. **Capture the earliest failing boundary**: Windows Application Error/WER/Event Viewer (`exe`, `faulting module`, `exception code`, `offset`), loader/proxy DLL chain, VC++ dependencies and bitness, game init, D3D9Ex device creation, x86↔x64 IPC/host spawn, OpenXR instance/session, compositor/presentation. Compare Process Monitor or loader trace only when existing evidence cannot locate the boundary.
4. **Check cross-game contamination cautiously**: a newly tested Model 2/Daytona VR hook, OpenXR API layer, runtime switch, device driver or graphics injector can affect another process, but require a process/module/registry trace before attribution. Certificate-expiry events alone do not prove causation.
5. **Rank falsifiable hypotheses** with distinguishing tests; if the same archived binaries fail only on the original PC, prioritize environment, per-user state and runtime dependencies before source regression. Failure on another PC is not assumed without a matching test.
6. Use `docs/VR_CRASH_SIGNATURES.json` stable keys when a signature actually matches. If evidence is insufficient, report `NEEDS_EVIDENCE` with the exact missing discriminator. No crash-fix claim without reproducing the symptom, changing one causal factor and demonstrating the restored launch.

## Route B: stereo, cockpit, HUD, menu or optical defect

Trace one **physical draw** end to end: original game producer/CALL → SpriteNode/D3DX deferred queue or world object → scope/token → D3D9 Draw/DrawIndexed/FixedFn, FVF/VS/PS/texture/state → c64/WVP and latched pose → left/right GPU RT and host OpenXR presentation. Never classify HUD by alpha, blend, FVF, or a single log line alone.

- Classify distinct owners: world-stereo, vehicle-attached rank/rival, transient +TIME/GOAL, menu/theater 2D, F11 external overlay, lens center versus halo, particles/grass, cockpit/vehicle camera.
- Keep **game source extent**, logical UI coordinates/viewport and **XR eye resolution** independent. No forced game downscale or global 4:3 correction to hide a misplaced overlay.
- For cockpit camera, distinguish car-local transform, driver-seat offset, view/eye pose, frame identity and restoration of original game matrices; a camera transform error must not be patched by an unrelated HUD offset.
- Freeze unaffected routes. Compare same-source controls and known-good semantics; require physical left+right draw evidence for any new routing rule. Never silently replace native stereo with mono/SBS or turn off an effect as a claimed fix.
- Protect head tracking, recenter (F12 in released VR), input/FFB, SkyGlow policy, reset/device-loss, menu, rank, goal and lens regressions.

## Route C: smallest useful verification before the evening HMD test

1. State one observable hypothesis and existing known-good/broken behavior.
2. Add/extend the smallest **negative and positive** deterministic test or contract oracle, preferably fail-before/pass-after for a real source change. Use only affected-area checks during implementation.
3. Validate a single final **exact candidate SHA** with the applicable Win32 x86 game + x64 host + installer/launcher, Domain and changed-area source/CI gates. Never rerun unchanged SHA tests for score.
4. Produce one focused Quest 3/Virtual Desktop/VDXR test matrix covering startup, both eyes, one HUD/menu state, cockpit/recenter if relevant, 2D fallback and exit. Keep playtest artifacts tied to that SHA, config and original EXE identity.
5. Capture only **opt-in bounded diagnostics** needed to separate hypotheses; disable verbose tracing and telemetry in release profiles by default. Do not silently remove the user's ability to report an opt-in crash.
6. Record status explicitly: `SOURCE_INSPECTED`, `BUILD_VERIFIED`, `NEEDS_EVIDENCE`, or `RUNTIME_VALIDATION=UNTESTED` until matching HMD evidence. No inferred FPS claim without measured headset frame-time.
7. Preserve the existing test-launch contract: normal `Start-OutRun.cmd` must select 2D; `Start-OutRun-VR.cmd` / official package VR launcher selects VR. Reproduce real EXE+host PID lifecycle, missing-helper errors, nonzero exit and diagnostics before release. Do not confuse a runnable 2D game with a working VR host.

## When not to use this wizard

Do not restart the 0–10 generic flat-to-VR roadmap, introduce physics hands/holsters/gun mechanics/full-body IK into a racing mod, move GPU work to N100, require the development agent and HMD to be on one computer, or invent a new orchestration/score system. GitHub connector first, local analysis second, N100 only when necessary. New changes remain constrained by current feature owner and active task.

## Source and attribution

Adapted principles: staged verification, no silent fallbacks, batched human playtests, hypothesis-led crash diagnosis, HUD by element, and accountable bug pipeline. Upstream: `bigbossafman/VR-Mod-Vibecoding-Wizard` at `40382b390e239f354ea3cecd1f9151c455883d7c`, [upstream license](https://github.com/bigbossafman/VR-Mod-Vibecoding-Wizard/blob/main/LICENSE) (MIT). The adaptation's project-specific defaults and instructions are not upstream guarantees.
