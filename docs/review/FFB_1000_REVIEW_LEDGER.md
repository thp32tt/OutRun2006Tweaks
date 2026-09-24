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

Completed cycles: **10 / 1000**

## Findings

- `FFB-R0001-F01` .. `FFB-R0001-F13`: see GitHub Issue #29 for evidence, fixes and validation history.
- C0002..C0010: no new finding after duplicate check against Issue #29.

## PS2 evidence discipline

- **Retail SLPM evidence:** `SLPM_666.28` and directly recovered wrapper/caller behavior.
- **Comparative evidence:** liblgdev is used only to interpret the common Logitech ABI/type enum where applicable.
- **Provisional translations:** C2C event/source mappings remain explicitly provisional until a retail PS2 caller/semantic link is recovered.
- Never promote comparative/provisional evidence to an OutRun PS2 original value without direct SLPM evidence.

## Next review

Resume at **C0011**. Continue distinct source/behavior slices and record a cycle only after inspection plus ledger/Issue documentation.
