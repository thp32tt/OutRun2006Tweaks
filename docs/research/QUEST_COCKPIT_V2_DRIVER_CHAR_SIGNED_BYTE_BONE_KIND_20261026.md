# QuestCockpitV2 — driver character ID narrowing changes skeleton/bone-kind selection (2026-10-26)

**Research run started:** 2026-10-26 **21:06:11 KST**. **Scope:** REVIEW_ONLY, one new independent finding. Owner: user-owned Quest APK / `thp32tt/OutRun2006Tweaks@vr-d3d9ex-focus`. Latest observed GitHub source HEAD before this commit: **`0b47cc10aca75f8c8c41692b0e0e31b50a9f947a`**. Existing R26+HUD and MOZA R3 physical wheel/FFB unchanged. No tracked hands, hand tracking, or VirtualWheel steering. No Windows game source, DLL, INI, workflow, build, or deployment modification.

## Distinct new issue — the selected driver character ID is NOT passed unchanged to its skeleton class

The earlier [profile-selection study](QUEST_COCKPIT_V2_DRIVER_CHARACTER_PROFILE_PERMUTATION_20261026.md) proved the `race_robot_driver_chara_487ee0` mode/provider/profile selector, including permutation `{0,1,2,4,3,5}`, and its call from driver initialization. It did **not** analyze the receiving function's narrowing or how character ID selects bone resources.

The original Quest ARM64 ELF `liboutrun_quest_core.so` (SHA256 **`fa0f9db9b744515a9a1439741bc9806ad007470b621b88d22a0b8cbced6120b6`**) has symbol `race_robot_set_chara_487c30` at **ELF VA `0x39ED1C`, size `0x4A4`**. The function first executes **`0x39ED3C: sxtb w2,w2`**: the incoming 32-bit character ID is **truncated to its low 8 bits and sign-extended** before `PcRaceMemory::put32(work+8, chara)` at `0x39ED50..0x39ED64`. This is **not** equivalent to preserving a raw 32-bit profile-table ID.

The function then re-reads `work+8` at `0x39ED94..0x39ED9C`, computes unsigned `u32(chara-3)` at `0x39EDA0`, compares with **16** at `0x39EDA4`, and uses a 17-byte native rodata category table only for `3<=signedChara<=19`. All other values go through the default category.

The table is an actual **native ELF rodata** object, not guest `PcRaceMemory`: symbol `race_robot_set_chara_487c30::cases` at **VA `0x001A58B6`, 17 bytes**, direct PT_LOAD readback:

```text
cases[0..16] = [0,0,1,1,1,1,1,1,2,2,3,3,3,4,2,2,1]
```

The `0x39EF2C..0x39F054` native switch maps this category to the **bone-group kind** used by the `0x4F1CF0 SetBone` service:

| Signed character ID (after `sxtb`) | Table category | Bone kind | Bone group offset `kind<<4` |
| --- | ---: | ---: | ---: |
| 3–4 | 0 | 4 | 0x40 |
| 5–10 | 1 | 2 | 0x20 |
| 11–12 | 2 | 3 | 0x30 |
| 13–15 | 3 | 0 | 0x00 |
| 16 | 4 | 5 | 0x50 |
| 17–18 | 2 | 3 | 0x30 |
| 19 | 1 | 2 | 0x20 |
| <3 or >19, including negative values | default 2 | 3 | 0x30 |

Native dataflow: `0x39EF34 ldrb w8,[x9,w8,uxtw]` loads the category; the branch groups assign **`w25=0x00/0x20/0x30/0x40/0x50`**; `0x39EE08` adds that offset to the guest bone-base value from **`0x84D974`**. The resulting parameters are published for **`0x4F1CF0 SetBone`** at `0x39EE28..0x39EE48`. The same function subsequently issues **`0x514BF0 rob_disp_init`** (`0x39EE58..0x39EE80`) and **`0x514F60 rob_osage_init`** (`0x39EE88..0x39EEC0`). Thus the selected character affects the skeleton family **before** display and osage initialization; it is not merely a cosmetic model-name label.

**Important subtlety:** IDs 11 and 12 (the two fixed selector routes established previously) both map to bone kind **3**. The six actual values of the guest table at `0x6549B0` remain **UNKNOWN**; do not assume all six profiles use the same bone kind. Signed-byte aliasing is exact: input `0x103` becomes 3 and chooses kind 4, whereas raw input 0x103 interpreted as a full 32-bit ID would choose default kind 3. Input 0xFF becomes -1 and chooses default kind 3. These are **conditional counterexamples**, not proof that the original game actually supplies such values.

## Original evidence addresses and verification

- `0x39ED1C..0x39F1C0`: symbol-bounded original ARM64 implementation; `0x39ED3C` signed byte conversion; `0x39ED50..0x39ED64` guest work+8 storage; `0x39EDA0..0x39EDA8` range gate; `0x39EF2C..0x39EF50` rodata lookup and branch; `0x39EF80/0x39EFD0/0x39F010/0x39F050` kind offsets; `0x39EE08/0x39EE28..0x39EE48` SetBone argument.
- `0x001A58B6`: 17 native category bytes read directly from original ELF's PT_LOAD mapping; native symbol table also independently identifies the same object and size.
- `0x3A01B0..0x3A01C0`: `race_robot_driver_init_4884d0` calls selector, moves return to w2, calls this receiving function. This is the same established initialization edge, included here to prove reachability, **not** a new independent achievement by itself.
- Secondary cross-check: public PC inverse reconstruction `r4dius/outrun2-decomp/src/platform/race_robots.cpp` contains `race_robot_set_chara_487c30` with explicit `int8_t(uint8_t(chara))` and the 17-byte table. This supports semantics but the **primary evidence is the original Quest ELF**.

### Reproduction (read-only, bounded)

On the existing authorized N100 analysis environment (no game binary edits):

```sh
aarch64-linux-gnu-objdump -t -C liboutrun_quest_core.so  # locate symbol and rodata
aarch64-linux-gnu-objdump -d -C --start-address=0x39ed1c --stop-address=0x39f058 liboutrun_quest_core.so
readelf -lW liboutrun_quest_core.so  # VA-to-file-offset conversion for 0x1A58B6
```

Read-only helper files stored outside the game repo:
- `apk/_analysis_focus/quest_20261026_2106_set_chara_native_symbol.py` — ELF hash and original symbol boundaries.
- `apk/_analysis_focus/quest_20261026_2106_set_chara_native_disasm.py` — bounded ARM64 and original 17-byte native table.
- `apk/_analysis_focus/quest_20261026_2106_driver_bone_kind_native_verify.py` — **32/32 fixed original opcode/address assertions PASS**, **17/17 rodata bytes PASS**, **24/24 independently enumerated boundary/alias fixtures PASS**, **256/256 signed low-byte domain classification PASS**. Exhaustive 256-entry distribution: kind 3=243, kind 4=2, kind 2=7, kind 0=3, kind 5=1.

The classification fixture checks **source-equivalent static arithmetic**, not game runtime, GPU skinning, actual PMT selection, or bone animation on Quest3.

## V2 failure mode, uncertainty and next step

**Risk:** a new V2 that preserves `u32` character ID without the original signed-byte normalization, treats the profile index as a skeleton ID, or hardcodes one skeleton kind can bind the wrong bone resource even when the event owner, occupant W×C model transform and LOD0 gate are correct. The result could be a wrong pose/mesh; **no actual runtime symptom has been observed**. Do not apply a global rendering or culling fix based on this finding.

**Proven statically:** exact narrowing opcode, work+8 store/read, 17-byte category mapping, bone-kind offset selection, SetBone→rob_disp_init→rob_osage_init call sequence, selector-to-receiver call edge. **Not proven:** the six live guest character IDs, exact bone/PMT resource contents, whether values >127 occur, whether any profile changes during a race, actual driver model rendering and Quest3 stereo behavior.

**Next independent research:** identify the six actual guest `0x6549B0` table values using a verified guest-image mapping/snapshot, then trace `0x4F1CF0 SetBone` and `rob_disp_init` resource IDs to a PMT mesh/bone set. For a future atomic V2 cutover, keep a typed **character selection → signed-byte normalization → skeleton-kind selection → model/osage init** contract and validate owner generation; do not alter existing R26+HUD/DriverSeat code during REVIEW_ONLY.

**CODE_CHANGE=NO | DOCS_ONLY=YES | SRC/DLL/INI/CI/BUILD/DEPLOY=UNCHANGED | MOZA_R3_FFB=UNCHANGED | HAND_TRACKING=OUT_OF_SCOPE | QUEST3_HMD=UNTESTED | GAME_RUNTIME=UNTESTED**
