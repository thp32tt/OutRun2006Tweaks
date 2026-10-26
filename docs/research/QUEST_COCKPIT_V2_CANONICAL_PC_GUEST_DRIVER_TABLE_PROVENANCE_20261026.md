# QuestCockpitV2 — canonical PC guest driver table values, profile-to-bone cross-check and Quest provenance boundary (2026-10-26)

**Research started:** 2026-10-26 22:06:40 KST. **Mode:** REVIEW_ONLY. **Target:** `thp32tt/OutRun2006Tweaks@vr-d3d9ex-focus`, pinned pre-commit HEAD `84b6e1d6d467bab5bdb8d8ef413ed82e6535ace9` (2026-10-26 22:05:24 KST). **Hardware target:** Quest3 PCVR with physical MOZA R3 wheel and existing FFB; no Quest hand tracking, virtual hands or VirtualWheel input. The legacy DriverSeat implementation is **not** modified; a future QuestCockpitV2 will require a separate atomic replacement. No `src/`, DLL, INI, workflow, build or deployment change.

## One distinct new finding: actual six guest-table words in the locally owned *canonical PC EXE*, not yet Quest live memory

The prior research [driver selector/permutation](QUEST_COCKPIT_V2_DRIVER_CHARACTER_PROFILE_PERMUTATION_20261026.md) proved that original Quest ARM64 `race_robot_driver_chara_487ee0` reads guest address `0x6549B0 + 4*perm[profile]` but explicitly left all six table values **UNKNOWN**. The subsequent [signed-byte bone-kind study](QUEST_COCKPIT_V2_DRIVER_CHAR_SIGNED_BYTE_BONE_KIND_20261026.md) proved that `race_robot_set_chara_487c30` narrows that selected character ID and classifies it into a skeleton family, but likewise did not know the six table values.

**New, independently extracted data:** the locally owned **unpacked canonical Windows PC game EXE** `OR2006C2C_CANONICAL_FOR_GLASS.EXE`, SHA256 `68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3`, has image base **`0x400000`**. Its PE `.data` section maps VA **`0x6549B0`** (RVA `0x2549B0`) to on-disk file offset **`0x2539B0`**. Direct, non-heuristic PE section translation yields 24 bytes:

```text
PC EXE VA 0x6549B0: 0b 00 00 00 12 00 00 00 11 00 00 00
                     09 00 00 00 05 00 00 00 13 00 00 00
six little-endian u32 values: [11, 18, 17, 9, 5, 19]
```

The **adjacent PC EXE** table at VA `0x6549C8` (file offset `0x2539C8`) has the **same 24 bytes**. The independent PC reconstruction labels the second address as a passenger-character table, but byte equality does **not** prove driver/passenger ownership, event-slot identity, or actual Quest runtime behavior.

The **original Quest ELF** `liboutrun_quest_core.so`, SHA256 `fa0f9db9b744515a9a1439741bc9806ad007470b621b88d22a0b8cbced6120b6`, independently supplies:
- `race_robot_driver_chara_487ee0` at **ELF VA `0x39F33C`**: mode-3 return `12` at `0x39F37C`; failed provider return `11` at `0x39F424`; otherwise guest `0x7C2400` profile range check at `0x39F3E8`, native permutation lookup at `0x39F3FC`, and guest `0x6549B0 + 4*perm` lookup at **`0x39F3F8..0x39F40C`**.
- Native six-word permutation at **ELF VA `0x1A58D4`**: `[0,1,2,4,3,5]` (direct ELF PT_LOAD bytes).
- `race_robot_set_chara_487c30` at **`0x39ED1C`**: `sxtb w2,w2` at **`0x39ED3C`**, then bone-category rodata at **ELF VA `0x1A58B6`** (17 bytes: `[0,0,1,1,1,1,1,1,2,2,3,3,3,4,2,2,1]`) and SetBone kind selection.
- The selector-to-consumer call chain was independently established at **`0x3A01B0`** and **`0x3A01C0`** in the earlier report; not counted as a new finding here.

**Combined conditional table:** if and **only if** the Quest runtime guest table equals this verified canonical PC EXE data and the original selector's provider-success / mode!=3 route is taken, the six profile slots resolve as follows:

| Active profile slot | Quest native permutation index | Canonical PC guest VA read | Canonical PC character ID | Original Quest bone-kind rule |
|---:|---:|---:|---:|---:|
| 0 | 0 | `0x6549B0` | 11 | 3 |
| 1 | 1 | `0x6549B4` | 18 | 3 |
| 2 | 2 | `0x6549B8` | 17 | 3 |
| 3 | 4 | `0x6549C0` | 5 | 2 |
| 4 | 3 | `0x6549BC` | 9 | 2 |
| 5 | 5 | `0x6549C4` | 19 | 2 |

**Useful refinement of earlier risk:** on this canonical PC table, mistakenly omitting the profile-3/4 permutation exchanges **character IDs 5 and 9**, but both map to **bone kind 2**. Thus the swap can select the wrong **character/model** while leaving the **skeleton family unchanged** for those two profiles. A claim that this specific swap necessarily changes bone kind is unsupported. The split between slots 0–2 (kind 3) and 3–5 (kind 2) is conditional on the PC table and the provider-success branch; mode 3 and provider failure bypass the table.

## Source provenance boundary: do not mislabel PC data as Quest APK runtime truth

The PC EXE is a **separate locally owned source**, not bytes extracted from the original Quest APK. The original Quest ELF proves the **guest address and lookup algorithm**, but its own raw file contains **no contiguous copy** of the 24-byte PC table pattern (bounded exact-byte search), which is not proof the Quest APK lacks it in compressed assets or dynamically loaded memory. **No Quest runtime guest-memory snapshot** at `0x6549B0..0x6549C7` has been acquired.

A second locally owned `original_TestApp.exe` (SHA256 `4876712f501640951d892069db826e431aede3e4ab87686fc1d556e26df9fec1`) is PE32 image-base `0x400000` with only two sections; its VA `0x6549B0` lies inside a virtual `.text` extent **beyond the section's on-disk RawSize**. Therefore **it cannot independently confirm or contradict these six table values by direct on-disk PE read**. No zero-filled or invented table is asserted.

Independent reconstruction `r4dius/outrun2-decomp/src/platform/embedded_exe_ranges.cpp` maps PC range `0x654500..0x654C00` from the **player's EXE image**, and `src/platform/race_robots.cpp` implements the same selector. This cross-check supports the address meaning for the PC port; it does **not** establish the Quest APK's actual live guest table values or character rendering.

## Reproduction and assertions (read-only)

N100-only bounded verification helper (outside the game repository):
`apk/_analysis_focus/quest_20261026_2206_guest_driver_table_native_pe_crossverify.py`.

Run it in the existing authorized N100 environment with Python 3. It:
1. SHA256-checks the original Quest ELF, canonical PC EXE, and separate TestApp EXE.
2. Parses the original **ELF64 PT_LOAD** headers to read native permutation `0x1A58D4` and bone-category `0x1A58B6` by VA.
3. Parses the **PE32** section headers and translates `0x6549B0` and `0x6549C8` to on-disk bytes, checks both 24-byte tables and the six exact words.
4. Computes six profile/character/bone-kind rows, asserts the `original_TestApp.exe` table region is **not file-backed**.
5. Prints `ASSERTIONS_PASS`; it does **not** load or modify a game process, build a DLL, invoke a game runner, or claim a Quest3 visual result.

The run returned all SHA, native rodata, PE section, duplicate-table, profile and non-file-backed assertions **PASS**. The companion read-only `quest_20261026_2206_guest_table_elf_crosscheck.py` found **zero** exact 24-byte pattern occurrences in the Quest ELF and **two** in the canonical PC EXE, matching the two PE table addresses. This is a file-byte observation, not a negative proof about the Quest runtime.

Manual equivalent: verify PE image base `0x400000`; map `0x6549B0-0x400000=0x2549B0` into the `.data` section, yielding file offset `0x2539B0`; unpack six little-endian `u32`; separately use `readelf -lW` for ELF PT_LOAD rodata addresses `0x1A58D4` and `0x1A58B6`, and disassemble Quest `0x39F33C..0x39F410` plus `0x39ED1C..0x39EF54`.

## V2 impact, uncertainty and next independent research

**Implementation risk:** hardcoding the six canonical PC values as if they were proven Quest guest-memory values, ignoring the native `[0,1,2,4,3,5]` permutation, or equating event 362 work-token identity with character ID can select a wrong model. In a future isolated V2, resolve the **actual loaded guest table** and snapshot the resulting character ID, signed-byte normalization, bone-kind and event-owner generation before creating the per-occupant draw. Do not make the selected ID or skeleton kind a global renderer setting.

**Confirmed:** six **canonical PC EXE** u32 values at exact file offset, their duplicate PC table, the native Quest permutation/bone category and selection/consumer addresses, and the conditional six-row mapping. **Not confirmed:** actual Quest APK initialized guest table, whether the Quest table is modified at runtime, active profile during real racing, which PMT/skin resource corresponds to each ID, HMD stereo rendering or frame-rate impact.

**Next:** obtain a trustworthy read-only Quest game guest-memory snapshot of `0x6549B0..0x6549DF` during driver initialization, with version/build identity, and compare all twelve driver/adjacent-table words to the canonical PC bytes. Only after equality is proven may these exact values be called **Quest runtime verified**. Independently trace the character-ID-to-PMT resource mapping and owner lifetime; never add tracked hands or virtual steering.

**NEW_FINDING=PC_GUEST_TABLE_BYTES_AND_CONDITIONAL_BONE_MAPPING | REVIEW_ONLY=YES | ONE_NEW_DOC_ONLY=YES | SRC/DLL/INI/CI/BUILD/DEPLOY=UNCHANGED | MOZA_R3_FFB=UNTOUCHED | QUEST3_HMD=UNTESTED | GAME_RUNTIME=UNTESTED**
