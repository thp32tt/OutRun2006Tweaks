# QuestCockpitV2 — original occupant TLS producer selects TWO robot-work slots and has a broader event admission than the separate hand flag

**Research:** 2026-10-26, 18:15 KST. **Mode:** REVIEW_ONLY. User target is Quest3 PCVR + **MOZA R3 physical wheel**; Quest hand tracking and VirtualWheel inputs are **out of scope**. Future legacy DriverSeatView deletion and atomic V2 replacement require a separate implementation decision. No `src/`, game DLL, INI, build, CI, release or runtime change was made in this task.

**GitHub:** `thp32tt/OutRun2006Tweaks`, `vr-d3d9ex-focus`. Pinned observed source HEAD immediately before this report: `d4d90794cff63745737df5618740d9b5b30a6ce4` (concurrent focus-branch commits may advance HEAD). This report adds **one new research MD file only**.

**Original evidence:** user's authorized Quest `liboutrun_quest_core.so` SHA256 `fa0f9db9b744515a9a1439741bc9806ad007470b621b88d22a0b8cbced6120b6`. Native ELF symbol `std::__ndk1::__function::__func<(anonymous namespace)::run_game(android_app*)::$_0,...,bool(unsigned int,unsigned int)>::operator()` at ELF VADDR **`0x2E315C..0x2E33E8`**. Bounded AArch64 GNU objdump disassembly, exact instruction assertions and a separate synthetic predicate fixture were executed on N100. All addresses below are **Quest ELF VADDR**, not PC EXE addresses.

## Newly verified finding: `cockpit_occupant_draw` is NOT a one-slot player flag and is NOT gated by the event function ID in its own admission block

The previous `QUEST_COCKPIT_V2_OCCUPANT_FORCE_VISIBLE_LOD0_GATE_20261026.md` proved the **consumer**: when view/service byte `+0x35` and `cockpit_occupant_draw` TLS are nonzero, `node_visible` at `0x10AA410/414` forces `lod=0, visible=true`. The previous report explicitly left the **TLS producer and lifetime** unresolved.

This run resolves that producer for the original `run_game` event-dispatch callback:

1. **Event and work arguments:** at `0x2E3190`, `w23 = *(uint32_t*)x1`; at `0x2E3194`, `w24 = *(uint32_t*)x2`. At `0x2E32DC`, `stp w24,w23,[sp]` forwards the values as two separate arguments to the original event callback at `0x2E3314..0x2E3324`. The first value is compared against event code `0x4879B0` **only in the separate first gate** (`0x2E31C0..0x2E31CC`).
2. **Common eligibility:** the second gate at `0x2E3268..0x2E32A4` checks the host-enabled byte, then guest word at `0x9954` with **`(word | 0x2)==0x12`**, then guest byte at `0x94C5A` equals 1. The latter address matches the known original camera buffer base `0x94910` + camera mode byte offset `0x34A`; this is a structural address correlation, not proof that all PC camera states map identically.
3. **TWO eligible work indices:** `0x2E32A8..0x2E32B8` loads the first guest index from **`0x5A8C`** and compares it to `w24`. If equal, `0x2E32C0` selects 1 and `0x2E32E0` writes **`cockpit_occupant_draw=1`**. If not equal, `0x2E3374..0x2E339C` compares `w24` against a **second** guest index from **`0x5ACC`**, then writes the equality result to the same TLS byte. If neither matches, `0x2E32EC..0x2E330C` writes TLS zero. These are two distinct original guest words, 64 bytes apart; their exact semantic names and which robot/person each represents remain UNKNOWN.
4. **Event-ID asymmetry:** the **first** gate at `0x2E31C0..0x2E31CC` explicitly requires `w23==0x4879B0`, but the **second/occupant** gate `0x2E3268..0x2E33A4` has **no compare/branch against w23**. It forwards w23 to the original callback instead. Thus the callback's occupant-TLS admission is based on host/mode/work slot and can be true **without checking that particular event code in this block**. Whether the higher-level dispatcher ever invokes it with other codes for those work indices is NOT YET PROVEN.
5. **Tightly scoped cleanup:** the normal callback return clears the first temporary byte at `0x2E332C` and clears **`cockpit_occupant_draw` at `0x2E333C`**. The C++ exception handler likewise clears the temporary byte at `0x2E33BC` and **`cockpit_occupant_draw` at `0x2E33CC`** before `_Unwind_Resume` at `0x2E33E4`. The native implementation clears TLS to zero, not to a saved previous value; a reentrant/nested dispatcher remains an untested case.

### Native control-flow truth table (static)

Let `H` = host enabled, `F` = guest `u32[0x9954]`, `M` = guest `u8[0x94C5A]`, `I` = callback work index, `A=u32[0x5A8C]`, `B=u32[0x5ACC]`.

```text
occupant_tls_during_original_event_callback =
    H && ((F | 0x2) == 0x12) && (M == 1) && ((I == A) || (I == B));

original_callback(I, event_code);
occupant_tls = 0;   // normal return AND exception cleanup
```

The separate **first** gate for another temporary flag requires event code `0x4879B0` and only matches `I==A`. It must not be conflated with the **two-slot occupant** TLS. That other flag is **not part of the requested MOZA R3/physical wheel implementation** and must not be used to reintroduce Quest hands or virtual steering.

| Host/mode valid? | I==A | I==B | Original occupant TLS during callback |
|---|---:|---:|---|
| no | any | any | 0 |
| yes | yes | no | 1 |
| yes | no | yes | 1 |
| yes | no | no | 0 |
| yes | yes | yes (slots alias) | 1 |

## Why this is an independent V2 risk

A PC port that treats the occupant flag as a **single player work ID**, or applies the first gate's **`0x4879B0` event-code restriction** to the second gate, can fail to mark a second original robot-work slot. The original `node_visible` then may apply normal frustum/LOD to a near-seat mesh that Quest forces visible/LOD0. Conversely, a port that globally forces all robot nodes visible would admit unrelated NPC geometry. The original control flow also makes a nested event dispatch with zero-on-exit a possible scope hazard; nested events and real mesh selection have not been observed.

**Proposed review-only design contract:** in a future V2 cutover, carry an explicit **scoped occupant owner and original work index** at event production; distinguish both eligible work slots, preserve per-view owner qualification (`view+0x35`) and clear/restore state with explicit nesting semantics. Never promote this flag to a global culling or HMD-pose toggle. Do not alter MOZA R3 wheel input, FFB, VirtualWheel or hand tracking.

## Reproduction and validation

On the user's N100 (read-only ELF):
- `apk/_analysis_focus/quest_20261026_1815_occupant_tls_owner_probe.py` disassembles the exact `run_game` callback and original `Draw::disp_514c30` consumer, and checks original ELF SHA256 and TLS relocation symbols. Original TLS symbol relocation `cockpit_occupant_draw` at GOT/TLSDESC `0x12588B8` is referenced by callback `0x2E32C4..0x2E32D0`, `0x2E32F0..0x2E32FC` and the consumer `0xD610E8..0xD610F4`.
- `apk/_analysis_focus/quest_20261026_1815_occupant_tls_two_slot_contract.py` reads **164 bounded ARM64 instructions** from `0x2E315C..0x2E33E8`, verifies **20 exact address/opcode anchors**, verifies the second gate has no w23 comparison and does forward the two original arguments, and runs **24 synthetic predicate cases** (4 expected admitted, 20 rejected). Result **PASS**. The initial test expected count was corrected from 8 to 4 before the successful run; no game or repository source was changed.
- Equivalent command: `aarch64-linux-gnu-objdump -d -C --start-address=0x2e315c --stop-address=0x2e33ec liboutrun_quest_core.so`.
- Recheck key addresses `0x2E32B4`, `0x2E3374`, `0x2E32E0`, `0x2E339C`, `0x2E333C`, `0x2E33CC`. Verify the TLS descriptor `R_AARCH64_TLSDESC` for `cockpit_occupant_draw` at `0x12588B8` using `readelf -rW`.

**Evidence quality:** ELF hash, AArch64 instructions, TLS descriptor, dual-slot branch and both cleanup paths **BINARY VERIFIED**. The synthetic fixture checks predicates only, not actual event invocation. Whether `A` and `B` correspond to driver/passenger, which exact PMT meshes are admitted, event-code diversity, nesting behavior, Quest3 image pixels and FPS are **UNKNOWN / UNTESTED**.

## Next independent tasks

1. Trace **writers and lifecycle** of guest `0x5A8C` and `0x5ACC` to assign stable robot-work identity and determine whether slots can alias or change mid-frame.
2. Identify the **writer and exact semantics** of the view/service byte `+0x35` (the remaining half of the forced-visible LOD0 admission) and confirm its per-eye owner.
3. Verify whether event dispatch can actually invoke this callback with work index A/B and event code other than `0x4879B0`; do not treat the broader static predicate as a reproduced runtime bug.
4. During a later separately authorized integration, log event/work ID, active TLS, view owner, selected PMT node/LOD and GPU queue admission without changing the stable R26+HUD visuals.

**CODE_CHANGE=NO | RESEARCH_MD_ONLY=YES | BUILD/CI=NOT_RUN | R26+HUD=UNCHANGED | MOZA_R3_FFB=UNTOUCHED | QUEST3_HMD=UNTESTED**.
