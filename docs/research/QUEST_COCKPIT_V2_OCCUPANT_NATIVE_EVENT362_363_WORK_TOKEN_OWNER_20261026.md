# QuestCockpitV2 — occupant TLS work IDs are native event-slot 362/363 work tokens, **not guest addresses** (2026-10-26)

**Research:** 2026-10-26 19:04:49 KST onward. **Mode:** REVIEW_ONLY. Target: Quest3 PCVR, physical **MOZA R3** wheel and unchanged FFB; Quest tracked hands, virtual hands and VirtualWheel steering are excluded. The existing legacy DriverSeat implementation will only be removed/replaced in a separately authorized future atomic cutover. No source, DLL, INI, CI, build or deployment changes here.

**Repository:** `thp32tt/OutRun2006Tweaks`, `vr-d3d9ex-focus`; pinned pre-research-commit HEAD `456642108a4c0bd86c337bc14ead561b3c376cdc` (2026-10-26 18:23:29 KST). Concurrent writers may move the branch after this observation.

**Original Quest evidence:** user-owned `liboutrun_quest_core.so`, SHA256 `fa0f9db9b744515a9a1439741bc9806ad007470b621b88d22a0b8cbced6120b6`; ELF virtual addresses below are **not Windows EXE RVAs**. All instruction assertions were checked against the original binary with bounded GNU AArch64 objdump on the N100.

## 1. Independent finding and correction of a previous report

The 18:15 report `QUEST_COCKPIT_V2_OCCUPANT_TLS_TWO_SLOT_EVENT_SCOPE_20261026.md` correctly found two distinct work-index comparisons at offsets `0x5A8C` and `0x5ACC`, but **incorrectly described those offsets as guest `u32[...]` addresses and left the slot identities unresolved**. The newly traced **pointer provenance** establishes that they are **byte offsets in the native `NativeRuntimeContext::event_state` event-slot array**, specifically the **`work_token` fields of event IDs 362 and 363**. This is a different and consequential ownership conclusion, not a duplicate TLS gate finding.

### Native event callback pointer chain — ELF `0x2E315C..0x2E33E8`

- `0x2E31EC`: `x21=x19+72`, where `x19` is the lambda closure. `0x2E31F0`: `x8=*[x21]`; `0x2E31F4`: `w9=*[x8+0x5A8C]`. The preceding `0x2E31E8` loads the literal `0x5A8C`. **No `PcRaceMemory::u32` call occurs on this path.**
- The separate occupant admission loads `x8=*[x21]` at `0x2E32A8`, then `x8=*[x8]` at `0x2E32AC`. At `0x2E32B0`, `x8+=0x5000`, then `0x2E32B4` reads `w9=[x8+2700]`. Since `0x5000+2700=0x5A8C`, this reads the **first native slot work token**; `0x2E32B8` compares it with callback work token `w24`.
- On mismatch, `0x2E3374` reads `w8=[x8+2764]`; `0x5000+2764=0x5ACC`; `0x2E3378` compares this **second native slot work token** with `w24`.
- This does **not** mean work tokens themselves are always valid or that a slot is currently active. It means the comparison inputs come from the host-owned event array rather than a mapped guest byte address.

### Independent native stride proof — ELF `map_memory` at `0x3AEC30`

- `0x3AEC88`: loads constant `0x5A8C`; `0x3AEC9C`: `x27=x0+0x5A8C`, with `x0` being `NativeRuntimeContext&`. `0x3AED50`: reads `w8=[x27]` and `0x3AED5C` stores that token into the robot module's staging cell. This is a **second native function** independently accessing the same native event-slot work field.
- `0x3AEE80`: `lsl x9,x8,#6`; `0x3AEE8C`: reads `ldrb [x19,x9]`; `0x3AEE90`: increments by `0x40`. This establishes the native event-slot **stride = 64 bytes** in the runtime event array (here reading flags from the first byte of each slot).
- Exact offsets:
  ```text
  362 * 0x40 + 0x0C = 0x5A8C
  363 * 0x40 + 0x0C = 0x5ACC
  ```
  Thus both work-index comparisons address the **same +0x0C field of adjacent native event slots**. It is incorrect to read guest address `0x5A8C` or `0x5ACC` through the PC game's memory accessor to emulate this condition.

### Independent PC reconstruction cross-check (secondary evidence, not original Quest code)

The separate public `r4dius/outrun2-decomp` reconstruction provides a matching explicit structure:
- `src/driving/pc_common_control.hpp`: `PcEventSlot` begins with `flags`, followed after padding by `descriptor_token`, `event_id`, **`work_token` at +0x0C**, and has 0x40-byte stride; `PcEventControlState` begins with `slots[410]`.
- `src/platform/native_runtime.hpp`: `NativeRuntimeContext` begins with `event_state`, consistent with the native base pointer provenance.
- `src/platform/race_robots_runtime.cpp`: the robot module's `cell_79f010` is populated explicitly from **`slots[362].work_token`**, consistent with the original `map_memory` second access above.
- `src/platform/race_robots.hpp` labels event **362 / ROB01** as **RobDriver**. The adjacent **363 / 0x16B** is a distinct event slot, **not automatically a passenger**.
- `src/platform/native_runtime.cpp` initializes event 362 with function 0x37 during stage60 phase0; event 363 with function 0x39 is **conditional** on `include_16b` during phase1 (via `0x4962D0`, `0x4999A0` and suppression probes). This conditional event setup is **PC reconstruction evidence only**, not a proof that the Quest APK runtime takes every one of those branches identically.

## 2. Consequence for a future clean QuestCockpitV2

**New independent failure mode:** a V2 port that translates the two native offsets into **guest-memory reads** may select unrelated data or an unmapped address, causing the near-seat occupant's original forced-visible/LOD0 condition to be missed or spuriously admitted. A port that hardcodes the two work IDs rather than resolving the current native event slots can also use stale tokens after event close/reopen. Event 363 must not be assumed always open or assumed to be the passenger without independent runtime evidence.

**Review-only contract:**
1. Capture the event dispatcher’s **actual work token and event ID** from the same frame/owner, and compare it to current `event_state.slots[362].work_token` or `event_state.slots[363].work_token` only when the corresponding event slot is valid/open. Avoid hardcoded guest `0x5A8C/0x5ACC` reads.
2. Keep the earlier original TLS eligibility gates (host-enabled, `(flags|2)==0x12`, native camera mode1) separate from slot identity. Do not import the first hand-specific `0x4879B0` restriction into occupant admission.
3. Treat the two event slots as **distinct lifecycle owners**. On slot close, reinitialize or owner generation change, invalidate any saved token. Preserve scoped TLS cleanup on normal and exceptional exits.
4. Do not touch MOZA R3 input, FFB, Quest hands, VirtualWheel, global PMT culling, player camera, glass, vehicle F0 or the production R26+HUD renderer.

## 3. Reproduction and evidence quality

N100 read-only helper: `apk/_analysis_focus/quest_20261026_1905_event362_363_native_offset_verify.py`. It verifies the exact original ELF SHA256, bounded AArch64 instructions, and 16 specific opcode/address anchors for the two native accesses, 64-byte event stride and robot-map source. **16/16 opcode anchors PASS; 3 layout assertions PASS (19 total).** No game or HMD was executed.

Equivalent direct disassembly:
```sh
aarch64-linux-gnu-objdump -d -C --start-address=0x2e31e8 --stop-address=0x2e33a0 liboutrun_quest_core.so
aarch64-linux-gnu-objdump -d -C --start-address=0x3aec80 --stop-address=0x3aeea4 liboutrun_quest_core.so
```
Recalculate `362*64+12`, `363*64+12`, `0x5000+2700`, and `0x5000+2764`; independently inspect the reconstruction's `PcEventSlot` fields and `slots[362].work_token` mapping. Do not infer a Windows memory RVA from these native struct offsets.

**Confidence:** native pointer chain, offset arithmetic and 64-byte stride **BINARY VERIFIED**; work-token field identity and event 362 driver label **BINARY/INDEPENDENT-PC CROSS-CHECKED**. Event 363 character/mesh identity, Quest event open/close timing, actual force-visible mesh set, reentrancy, frame-level owner equality and Quest3 visual effect **UNKNOWN/UNTESTED**. The independent PC source is a reconstruction, not a substitute for Quest runtime validation.

## 4. Next research task

Trace the original Quest event-slot 363 initialization/close writer and the work-token generation changes; identify the event function 0x39 callback and the PMT nodes actually drawn under that owner. Separately trace the writer of `view/service+0x35` before deciding whether a forced-visible LOD0 override belongs in the future PCVR renderer.

**CHANGESET=ONE_NEW_DOC_ONLY | SRC/DLL/INI/BUILD/DEPLOY=UNCHANGED | QUEST3_HMD=UNTESTED | R26+HUD=UNCHANGED**
