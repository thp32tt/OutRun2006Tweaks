# FFB 1000-Cycle Deep Review Ledger

Branch: `ffb-arcade-dd-research`  
Target: 1000 review cycles  
Baseline: `ae2d100dcbb2369402cfec49825f2e142b7173f2`

## Contract

A cycle is counted only after its assigned source/concern has been inspected and its result recorded. Findings are recorded before or together with the correcting commit. Every fix must identify the verifier/test/build evidence. No VR source is permitted. PS2/arcade values are labelled **verified**, **comparative**, or **provisional**; comparative evidence from another title never becomes an OutRun-original value without SLPM/Lindbergh evidence.

## Progress

| Cycle | Scope | Result | Finding / Fix | Validation |
| --- | --- | --- | --- | --- |
| C0001 | PS2 model + F11 model shortcuts + original-effect ownership | COMPLETE | FFB-R0001-F01..F13 fixed before review baseline HEAD `f8c6bc9` | Win32 Release 36031426942 SUCCESS; domain isolation 36031427012 SUCCESS |
| C0002 | Modern DD structural/SAT/math ownership | COMPLETE | No new non-duplicate finding | Existing production math + structural verification at `f8c6bc9` |
| C0003 | Arcade Original effect ownership / Lindbergh-derived behavior | COMPLETE | No new non-duplicate finding | Existing structural verification at `f8c6bc9` |
| C0004 | Arcade Hybrid composition / Modern interaction | COMPLETE | No new non-duplicate finding | Existing production math + structural verification at `f8c6bc9` |
| C0005 | PS2 Original Experimental evidence/translation boundary | COMPLETE | No new non-duplicate finding | SLPM retail evidence kept distinct from comparative liblgdev and provisional C2C mapping |
| C0006 | DirectInput effect lifetime / model transition / capability fallback | COMPLETE | No new non-duplicate finding | Existing Win32 Release + structural verification at `f8c6bc9` |
| C0007 | Device loss / reacquire / focus / safety recovery | COMPLETE | No new non-duplicate finding | Existing Win32 Release + safety paths reviewed at `f8c6bc9` |
| C0008 | Stage/surface/road-texture handling | COMPLETE | No new non-duplicate finding | Stage/surface mapping and model ownership reviewed at `f8c6bc9` |
| C0009 | F11 UI / profile / config / logging | COMPLETE | No new non-duplicate finding | Model-gated controls and profile transition paths reviewed at `f8c6bc9` |
| C0010 | CI / packaging / standalone domain isolation | COMPLETE | No new non-duplicate finding | Win32 Release 36031426942 SUCCESS; domain isolation 36031427012 SUCCESS |
| C0011 | PS2 provisional ConstantForce event lifetime vs collision debounce | COMPLETE | `FFB-R0011-F01`: short PS2 event was not bounded separately from debounce; fixed at `6d34f43`, guarded at `009d589` | Win32 Release 36123822046 SUCCESS; domain isolation 36123821936 SUCCESS |
| C0012 | PS2 compact-map builder/query schema contract | COMPLETE | `FFB-R0012-F01`: query assumed rich-only tables; schema-aware query + deterministic compact DB test + CI gate at `fcd20cc..ffc98ba` | Win32 Release 36123883423 SUCCESS; domain isolation 36123883396 SUCCESS |
| C0013 | PS2 recovered-runtime evidence persistence / machine-queryability | COMPLETE | `FFB-R0013-F01`: recovered retail sites were docs-only; curated semantic records + compact-map import + query test at `dcd6d5b..c1e85be` | Domain isolation 36124035608 SUCCESS; final-source Win32 build started as 36124035692 |
| C0014 | PS2 Type-7/Type-8 condition math, user scaling and hardware/software fallback parity | COMPLETE | No new non-duplicate finding; retail drive factor, spring coefficient/saturation, damper fade and fallback clipping remain separated from Modern SAT | Source/structural review on current tree; PS2 production-math invariants retained |
| C0015 | PS2 Type-4 periodic waveform, period translation, COM lifetime and fallback parity | COMPLETE | No new non-duplicate finding; Triangle hardware/software paths, road-only Original periodic ownership and model-transition recreation are consistent | Structural review + compact PS2 query test on current tree |
| C0016 | Arcade Original Lindbergh-derived spring/event/surface ownership | COMPLETE | No new non-duplicate finding; non-Modern structural ownership, 0x02 / 0x10 / 0x00 / 0x04 / 0x14 reconstruction and short wall window remain isolated | Source review against `LINDBERGH_FFB_MAP.md` evidence boundary |
| C0017 | Arcade Hybrid composition / Modern SAT + arcade event interaction | COMPLETE | No new non-duplicate finding; Hybrid owns Modern structural SAT/headroom while arcade event/surface semantics remain model-bound | Source/math/model-transition review on current tree |
| C0018 | DirectInput focus, menu, device loss/reacquire, reinit, watchdog and panic safety | COMPLETE | No new non-duplicate finding; foreground/menu paths zero torque before unacquire, reacquire checks foreground again, reinit releases effects and PanicStop stops all/actuators | Full safety/lifetime path review on current tree |
| C0019 | Four-wheel stage/surface/water/snow/curb ownership across models | COMPLETE | No new non-duplicate finding; per-wheel water outputs retained, Modern compatibility wrapper remains Modern-only, Arcade/PS2 avoid generic Modern splash | Core + wrapper + stage-map review on current tree |
| C0020 | F11 model UI, profile persistence, config defaults, telemetry/CI/package/domain isolation | COMPLETE | No new non-duplicate finding; model selection is captured/restored and stored in named FFB profiles; Modern remains default; standalone/domain gates remain active | UI/profile/config/workflow/domain review on current tree |
| C0021 | PS2 retail surface-LUT -> Type-4 periodic magnitude dataflow | COMPLETE | `FFB-R0021-F01`: PS2 PC road amplitude reused Modern texture shaping; direct SLPM analysis recovered the steady-state surface/speed/drive/50/threshold-27 chain and production translation was corrected in this batch | Win32 Release 36125477321 SUCCESS; domain isolation 36125477189 SUCCESS |
| C0022 | PS2 wheel-specific 0..10 feedback-level multiplier / Type-4 ownership | COMPLETE | `FFB-R0022-F01`: multiplier at 0x00133340 was mislabeled activation/ramp; retail menu + producer + manager tracing identifies game-state +0xFC as 0..10 wheel feedback strength | SLPM evidence at 0x24DF10, 0x24E8DC, 0x1D7FBC and 0x1332BC..0x133340; helper/test/docs/semantics updated |
| C0023 | PS2 effect-manager category / type ownership | COMPLETE | No new PC defect; categories 1=ConstantForce, 2=Type-8 Damper, 7=Type-7 Spring, 8=periodic are now tied to concrete retail builders/wrappers | SLPM dispatch/call graph at 0x133700, 0x133B20, 0x133DB0, 0x134048, 0x134268, 0x134EB0 |
| C0024 | PS2 ConstantForce source-global caller recovery | COMPLETE | `FFB-R0024-F01`: PC PS2 mode injected C2C collision into a retail transport with no verified non-zero caller; synthetic collision output removed and F11 Collision disabled for PS2 Original | Setter 0x132A28 + direct callers 0x132AF4/0x132DB4; source/UI/verifier/docs updated |
| C0025 | PS2 IOP Logitech module search in supplied assets | COMPLETE / BINARY_BLOCKED | No PC defect; IOPRP ROMDIR has no LGDEV/USBD and DRIVER.PS2 is a packed asset, not an IRX container | IOPRP310.IMG + DRIVER.PS2 binary/signature/string inspection; LGDEV.IRX still required |
| C0026 | PS2 Type-4 remaining surface-envelope writes | COMPLETE | `FFB-R0026-F01`: PC omitted retail roughness*1.25 vehicle-state boost and clipped valid 1.125 envelope to 1.0; helper/runtime/tests/verifier corrected | SLPM 0x1D811C, 0x1D81BC, 0x1D8268 -> consume 0x132E94; exact-head CI pending |
| C0027 | PS2 non-Type-4 transient-channel ownership | COMPLETE | No PC defect; remaining producer channels match controller-rumble logic and pad output is zeroed under wheel ownership, so they must not be imported as steering torque | SLPM 0x1D7F70 producer + 0x102460 pad output compared with Xbox CalcVibrationValues |
| C0028 | PS2 retail road-chain runtime instrumentation | COMPLETE | Validation prep: 10 Hz telemetry now exposes surfaceRough, boosted ps2Surface, ps2RoadRaw and ps2Drive before host scaling | Source + verifier instrumentation; no intended force behavior change |
| C0029 | PS2 ConstantForce hidden-caller/static-pointer audit | COMPLETE | No new PC defect; no extra direct caller, literal setter function-pointer entry, or second absolute writer to the two source globals was recovered | Whole-ELF direct-call/global-reference/literal-pointer audit; dynamic trace still required to exclude computed/indirect callers |
| C0030 | Cross-model periodic transport ownership | COMPLETE | `FFB-R0030-F01`: shared wrapper forced UsePeriodicEffects=false every frame, defeating Arcade Sine / PS2 Triangle ownership and the live F11 switch; per-frame override removed | wrapper/core/UI contract review; source/verifier/docs updated |

Completed cycles: **30 / 1000**

## Findings

- `FFB-R0001-F01` .. `FFB-R0001-F13`: see GitHub Issue #29 for evidence, fixes and validation history.
- `FFB-R0011-F01`: bound the provisional PS2 collision ConstantForce to the short six-tick event window while retaining the longer timer only as debounce.
- `FFB-R0012-F01`: repaired the compact PS2 reverse-map query/schema contract and added deterministic CI coverage.
- `FFB-R0013-F01`: persisted recovered retail runtime sites in the curated PS2 semantic map and imported them into regenerated compact SQLite maps.
- `FFB-R0021-F01`: replaced Modern DD texture shaping in PS2 Original's road periodic with the recovered retail surface-envelope / speed / drive-factor / magnitude-scale / threshold chain.
- `FFB-R0022-F01`: corrected the PS2 Type-4 extra multiplier from an assumed activation ramp to the recovered wheel-specific 0..10 feedback-strength setting.
- `FFB-R0024-F01`: removed the invented C2C collision mapping from PS2 Original after retail source-setter tracing found no verified non-zero caller.
- `FFB-R0026-F01`: restored the verified PS2 Type-4 roughness*1.25 vehicle-state surface boost and valid 1.125 envelope headroom.
- `FFB-R0030-F01`: removed the shared per-frame periodic-disable override so Arcade Sine / PS2 Triangle ownership and the live F11 transport toggle can operate.
- C0002..C0010 and C0014..C0020: no new non-duplicate finding after source/evidence review.

## PS2 evidence discipline

- **Retail SLPM evidence:** `SLPM_666.28` and directly recovered wrapper/caller behavior.
- **Comparative evidence:** liblgdev is used only to interpret the common Logitech ABI/type enum where applicable.
- **Provisional translations:** C2C event/source mappings remain explicitly provisional until a retail PS2 caller/semantic link is recovered.
- Never promote comparative/provisional evidence to an OutRun PS2 original value without direct SLPM evidence.

## Next review

Resume at **C0031** with cross-model Arcade/Modern behavior review. Highest-value remaining work includes Lindbergh periodic/event fidelity, Modern crash/transient validation, hardware telemetry/A-B validation, and dynamic/emulated discovery of any computed PS2 ConstantForce caller.
