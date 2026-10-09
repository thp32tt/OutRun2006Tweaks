# 2026-10-10 Quest3 DX9Ex P0 — canonical original EXE disassembly vs upstream mod, exact target fixes

## Authority, artifacts and acceptance

- Source authority: connected GitHub `thp32tt/OutRun2006Tweaks:vr-d3d9ex-focus`; upstream mod `emoose/OutRun2006Tweaks`; original official replacement `OR2006C2C.EXE` SHA256 `68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3`.
- Machine-generated, capstone x86, SHA-pinned original producer disassembly: `tools/disasm_outrun_goal_flare_p0.py` + `.github/workflows/outrun-exe-hud-inspector.yml`. Complete reviewed original assembly from successful Inspector `37958649895` static artifact `11631140967`: `DX9EX_CANONICAL_GOAL_TIME_LENS_P0.asm.md`. Inspector also retains original exact E8 bytes and call targets in `OR2006C2C_EXE_ANALYSIS.json`.
- **User HMD acceptance** (earlier exact `a6f8497c...`): GOAL result when percentage rises, e.g. 93% screenshot with large `1'05"283`, stage map/name and time doubled and head-following; fully completed result name/time normal. OutRun extension transient `+TIME` separately doubled/headlocked. Lens flare 4–5 discs: **central only** doubled/headlocked, outer 3–4 normal. All newer fixes `RUNTIME_VALIDATION=UNTESTED`. Never claim CI success implies HMD pass, do not retest same SHA.
- Protect original two GOAL name/time helpers `0xBEA5A -> 0xBE020`, `0xBEA5F -> 0xBE150` and final result; preserve the original 0.05m near plane reset and camera matrix restoration in upstream `FixZBufferPrecision::Clr_SceneEffect_dest`.

## Failure 1 — result progress 0–99% displays record digits detached/headlocked, 100% correct

**Original x86 source evidence**: original result-progress percentage sprites `0x97BB7`/`0x97DA7 ->0x2D280` and `0x97BE4`/`0x97DEC ->0x2D200` are **distinct** from nineteen original direct E8 calls `0x97xxx -> 0xB9200` which draw the large record/time/stage presentation. The old fork only wrapped the bar and a few glyph/GOAL calls, leaving `B9200` parents without an exact ScreenHud owner; this is consistent with generic ScreenOverlay2D observation in earlier GOAL 19 trace.

**Proven original `B9200` E8 site list**: `973AF,97422,974D0,97544,97664,97675,9769E,976B2,976F4,9784F,9787D,9788E,978B4,978C8,978EC,97C31,97C57,97E47,97E6D`. All are original EXE RVAs, not absolute virtual addresses.

**Material fix**: `src/hooks_uiscaling.cpp` snapshots/propagates semantic to *all* new SpriteNode siblings across priorities with exact E8 begin and +5 end `ResultTextEnter/ResultTextLeave`, `ProducerToken::ResultTextB9200` as `ScreenHud`; atomic rollback on partial install. No HUD suppression, no altered game original CALL, no generic overlay heuristic. Commits `b1d957ce3ad6`, `6bae69e536b8`. Negative source tests `167a934ba45d`; original EXE E8 target fingerprints `45b999b3fc98`.

## Failure 2 — OutRun course-change transient +TIME

**Original source hypothesis**: in adjacent `0x98800..0x98F00` original stage/animation function, exact distinct `0x9898E,0x98A36,0x98AC6 -> 0x29530 sprani_play_ae_auth` with E8-adjacent sprite IDs `0x2C00B4,0x2C00B5,0x2C006C`; do not conflate with `0x97xxx` final GOAL print. These three may be components of OutRun stage extension; original HUD trace was bounded, so a **complete optical ID-to-string proof still needs the extended disassembly/one later user HMD session**. New source disassembly window `0x98000..0x99000` added to inspect full parent animation.

**Material candidate**: exact three E8 parent begin/end wrappers `StageExtensionEnter/StageExtensionLeave` only; original `sprani` calls run unchanged, appended nodes become explicit ScreenHud `ProducerToken::StageExtensionTime`, atomic rollback on partial attach. No game timer/logic override, no impact on 100% final GOAL. Commits `96a3c8bcc922`, `bdad05098bcf`; tests `36fe4f117213`, original target inspector `0146799d5093`. **HMD UNTESTED**.

## Failure 3 — centre ONLY of lens flare; other discs are already PASS

**Original upstream mod**: `src/hooks_graphics.cpp::FixZBufferPrecision::Clr_SceneEffect_dest` temporarily restores camera z-near to `0.05`, calls `CalcCameraMatrix`, then restores prior znear after original Clr_SceneEffect. This changes lens world projection and must be kept.
**Original disassembly** proves two *different* render families:
1. Main `sub_40CAE0` calls `0xCF4E -> Calc3D2D`, builds camera/matrix and at `0xD3A0` loads constant object `0x570002` (main central disc); `0xD3A5 -> sub_40C980`, whose `0xC993` directly calls `DrawObjectAlpha_Internal`. Source call ends at `0xD3AA` before the next draw.
2. Outer halo discs use original `sub_40C9A0`, with E8 calls at `0xD5F5,0xD624,...,0xD796`; the existing `0xCABE -> DrawObjectAlpha_Internal` VR scope interceptor belongs to this other function. The old implementation **never explicitly owned central object 0x570002**, although it logged successful lens scope interception for the outer discs.
**Material candidate**: only `0xD3A5..0xD3AA` wraps primary object with original-game `RenderScope::WorldBillboard` during its actual 3D world draw, restores semantic immediately afterward, using atomic fail-soft hook install. Existing outer disc `0xCABE` projected scope never changes. No alpha/pixels deleted; no global screen heuristic. `src/hooks_graphics.cpp` `9f9d7f469281`, exact xrefs `tools/analyze_outrun_exe.py` `171c36534ecf`, negative `tools/verify_vr_visual_composition_p0.py` `518af96c3cd4`. **HMD UNTESTED**.

## Exact validation and risks

- `tools/verify_vr_visual_composition_p0.py`: 3 negative mutations guarding 19 result original E8/child owner, 2 for stage E8 and sibling owner, 3 for centre-only lens (no widening to outer 0xD5F5, no missing semantic restoration).
- `tools/analyze_outrun_exe.py`: original CALL E8 target/byte verification, new producer windows (`0x97000...`, `0x98800...`, `0xD300...`); `tools/disasm_outrun_goal_flare_p0.py` exact EXE SHA and Capstone disassembly.
- CI (latest **material** SHA `36fe4f117213f77863abdf5a061dc6cc5b7bf754`): DX9Ex Active `37959849499`, Inspector `37959849553`, Full Source Impact `37959849548`, Domain `37959849483`. **Do not treat an earlier passing 646c244 CI as proving this new material**. Check exact SHA status before packaging.
- Stage extension three E8 and central 3D effect routing are **candidates**, not visually verified. Risk: central WorldBillboard may be rejected by strict WVP gate; result progressive text may also take another shader/fixedfn path. No broad fallback changes are permitted without exact evidence.
- If all jobs PASS: package once for a **single combined later headset test**: normal completed result and outer discs protected, GOAL 93% large record+map/time single and head stable, mid-course +TIME single/head stable, central lens single/head stable, rank 1–5 attach, skyglow load reduction. No repeated same-SHA test; do not count a source CI as optical PASS.

### 2026-10-10 additional original +TIME numeric renderer gap (material SHA `18ab73948c989628486579a527d8ff8d1dfdd965`)

Capstone disassembly from exact original EXE on updated HUD Inspector `37959849553` adds a critical missing detail beyond three `sprani` frames. In the **same** original 0x989xx extension transition, the program directly calls `0x989AD -> 0x4973C0`, `0x98A10 -> 0x4974E0`, `0x98A89 -> 0x4973C0` immediately after/among the decorated sprites. These are **other 2D text/number printing functions**, so only tagging the original `0x29530` sprite shapes did not cover all of +TIME. The original disassembler `tools/analyze_outrun_exe.py` now verifies SIX exact original E8 edges: three `sprani` and three print helpers. Actual `src/hooks_uiscaling.cpp` in `ed17a5ea33235b33ce51f4b282b0fdf9a45a0482` installs six original parent begin/end hooks and rolls back ALL SIX if any fail, so the number text and original sprite share the existing exact `StageExtensionTime` ScreenHud owner. `tools/verify_vr_visual_composition_p0.py` `18ab7394...` adds six-edge target tests and independent negative mutation for the numeric E8 source. No original stage timer `0x43FA00` or scene/world animation code is altered, and the change is HMD UNTESTED. Avoid widening the hook to additional `0x98C09/98DCC/98E93` drawing unrelated sprite IDs until confirmed per-screen.
