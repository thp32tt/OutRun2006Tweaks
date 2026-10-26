# QuestCockpitV2 — driver SetChara guest writes precede the nullable service gate (2026-10-26)

**Research run:** 2026-10-26 23:24:35 KST onward. **Unique task:** `QUEST-COCKPIT-V2-20261026-2324-SETCHARA-PREWRITE-NOSERVICE`. **Scope:** independent REVIEW_ONLY, Quest3 PCVR with physical MOZA R3 wheel and existing FFB. Quest hand tracking, tracked hands, Touch steering and VirtualWheel are out of scope. The rejected legacy driver-seat code remains unchanged; future QuestCockpitV2 must be a separate complete cutover.

**Pinned source HEAD before this research commit:** `thp32tt/OutRun2006Tweaks@vr-d3d9ex-focus` = `8767a87c18d32b9e00f95ad80ff077fee5de0b02`. Concurrent unrelated commits can move this branch after this observation. Original **user-owned Quest APK** native ELF `liboutrun_quest_core.so` SHA256 `fa0f9db9b744515a9a1439741bc9806ad007470b621b88d22a0b8cbced6120b6`. ELF addresses below are **AArch64 virtual addresses**, not Windows PC game EXE addresses.

## New independent finding: SetChara publishes two guest writes before it knows the command service is available

Previous reports proved the profile selector, its signed-8-bit character normalization, the 17-entry bone-kind mapping, and the six **canonical PC EXE** guest-table values. They did **not** examine **failure atomicity of the receiving SetChara initialization**.

The original ARM64 function `race_robot_set_chara_487c30(PcRaceContext&, unsigned work, unsigned chara)`, **ELF 0x39ED1C..0x39F1C0**, follows this order:

1. **`0x39ED3C`** `sxtb w2,w2` narrows the incoming character ID. **`0x39ED40`** saves the original work address in `w20`. **`0x39ED50`** computes `work+8`. **`0x39ED5C`** loads `PcRaceMemory` from context, and **`0x39ED64`** calls `PcRaceMemory::put32(work+8, signed8(chara))`. This is the **first guest-memory mutation**.
2. **`0x39ED70`** reads the existing `PcRaceMemory::u32(work)` as **work token/index**. **`0x39ED74..0x39ED84`** constructs `mot = (0x82F5F0 + 0xA4 * index) mod 2^32`. **`0x39ED7C`** preserves the token as the second call's value `w2`. **`0x39ED8C..0x39ED90`** calls **`PcRaceMemory::put32(mot, index)`**. This is the **second guest-memory mutation**. Note that `mot` is a derived **guest motion-record address**, *not* the native event-slot 362/363 array offset, and the index is not assumed to equal event ID.
3. Only **after both calls**, the function loads the nullable command-service pointer **`PcRaceContext+0x30`** at **`0x39EDB0`** (default category), then **`0x39EDD0: cbz x0, 0x39F0C8`** throws a `std::logic_error` if null. The other category-specific first-service gates also occur after the two writes: **`0x39EF6C`**, **`0x39EFBC`**, **`0x39EFFC`**, **`0x39F03C`**, all branching to their own logic-error construction sites.
4. Later service gates for SetBone / display init / osage init / final call are **`0x39EE30`**, **`0x39EE70`**, **`0x39EEB0`**, **`0x39EEE8`**, also checked after the two writes. Native exception construction from **`0x39F058`** through **`0x39F1BC`** does **not** call `PcRaceMemory::put32` to roll either value back.

Therefore, **conditional on both guest writes succeeding and the service pointer being null**, the original function takes an exception exit **after** the guest `work+8` character field and the `mot+0` motion-token field have already been changed. There is no rollback in this function. This is a **static failure-atomicity/lifecycle risk**, not evidence of a real Quest crash or corrupt render. If the values already matched, the writes are not necessarily visibly different; if an upstream owner later resets these fields, that upstream behavior is outside this function and remains unproven.

The independent public PC reverse reconstruction `r4dius/outrun2-decomp/src/platform/race_robots.cpp`, `race_robot_set_chara_487c30`, matches the write-before-`p.call` order, and `Port::call` explicitly throws on `!c.service`. **Primary proof is the original Quest ELF; reconstruction is only a cross-check.**

## Distinction from existing research

- **Not** a new character-ID table or profile permutation: these were proved in `QUEST_COCKPIT_V2_DRIVER_CHARACTER_PROFILE_PERMUTATION_20261026.md` and `QUEST_COCKPIT_V2_CANONICAL_PC_GUEST_DRIVER_TABLE_PROVENANCE_20261026.md`.
- **Not** a new signed-byte/bone-kind mapping: that was proved in `QUEST_COCKPIT_V2_DRIVER_CHAR_SIGNED_BYTE_BONE_KIND_20261026.md`.
- **Not** the unrelated scoped **lighting** restoration issue: that belongs to `race_robot_display_487880` and `QUEST_COCKPIT_V2_ROBOT_LIGHTWORK_SCOPED_SCALE_20261026.md`.
- **New independent concern:** the **order of two guest writes relative to all nullable service gates and the absence of local rollback**, which affects future V2 init/owner lifecycle design.

## Reproduction and bounded static verification

Read-only N100 helper outside the game repository:
`apk/_analysis_focus/quest_20261026_2324_setchara_partial_write_guard_verify.py`.

It:
1. Hash-checks the original Quest ELF (above SHA256).
2. Runs bounded AArch64 GNU objdump on exactly **`0x39ED1C..0x39F1C0`**; checks **26 specific opcode/address assertions** including signed-byte conversion, both `put32` calls, motion-address multiplication, five category-first-service null branches, four later null branches, and exception construction.
3. Enumerates **exactly two `PcRaceMemory::put32` calls** in the symbol, both before the first possible service null test. Checks there is no subsequent `put32` rollback within the symbol. It does not assume external callers never clean up.
4. Computes deterministic illustrative motion-address values for synthetic tokens (e.g. token 0→`0x82F5F0`, token 1→`0x82F694`); **these are arithmetic fixtures, not measured runtime event IDs or actual player work tokens**.

Observed helper result: **ELF SHA PASS, 26/26 opcode assertions PASS, two write sites verified, no in-function `put32` rollback**. No game process was launched, no guest-memory write was performed by this verification, no HMD frame was produced.

Manual reproduction: `aarch64-linux-gnu-objdump -d -C --start-address=0x39ed1c --stop-address=0x39f1c0 liboutrun_quest_core.so`, confirm the exact two calls and that all category/service `cbz` branches occur after them. Inspect `0x39F058..0x39F1BC` for exception handling without restoring either guest address.

## V2 design impact, uncertainty and next research

For a **future separately authorized V2 cutover**, perform an explicit command-service/owner admission check before any new V2-specific guest-state staging. If any new V2 writes are unavoidable, snapshot their old values and use a transaction/RAII rollback guard across failures. **Do not retrofit this speculative guard into the existing game or assume the Quest original already has transactional rollback.** Keep owner generation, event-slot work token, character ID, motion-record address, and bone resource ID as separate typed concepts. Do not interfere with the MOZA R3 steering/FFB path.

**Confirmed:** native instruction ordering, both guest writes, nullable service pointer tests and lack of in-function rollback. **Unknown:** whether a real game ever calls this routine with a null service, whether an upstream exception handler restores state, whether the game maps these guest addresses in every mode, whether any runtime corruption manifests, PMT model visibility or performance impact. The Quest APK's live guest table still has not been captured.

**Next independent task:** inspect `race_robot_driver_init_4884d0`'s caller and exception owner to determine whether a higher-level event reset restores both fields when SetChara throws. Separately trace SetBone/PMT resource ownership after successful initialization. Do not count this same static finding again.

**REVIEW_ONLY=YES | NEW_FINDING=SETCHARA_WRITE_BEFORE_NULL_SERVICE_GUARD | GAME_SRC/DLL/INI/CI/BUILD/DEPLOY=UNCHANGED | MOZA_R3_FFB=UNTOUCHED | HAND_TRACKING=OUT_OF_SCOPE | QUEST3_HMD=UNTESTED | GAME_RUNTIME=UNTESTED**
