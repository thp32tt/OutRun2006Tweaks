# QuestCockpitV2 independent finding — native occupant visibility is a **forced-visible / LOD0 bypass**, not node suppression

**Research timestamp:** 2026-10-26, starting 17:11:04 KST. **Mode:** REVIEW_ONLY. Target: Quest3 PCVR with **MOZA R3 physical wheel**, excluding Quest hand tracking, virtual hands and VirtualWheel steering. Existing DriverSeat hooks will be discarded only in a future, separately authorized atomic V2 cutover. This task does **not** change source, INI, DLL, CI, builds or deployment.

**GitHub target:** `thp32tt/OutRun2006Tweaks`, `vr-d3d9ex-focus`, pinned pre-commit HEAD `616787e6564f89400dda5bb6f227c6368b62343b` (2026-10-26 17:05:27 KST). Parallel automation may advance HEAD.

**Primary evidence:** user-owned Quest `liboutrun_quest_core.so` SHA256 `fa0f9db9b744515a9a1439741bc9806ad007470b621b88d22a0b8cbced6120b6`. Original ARM64 symbol `outrun::platform::(anonymous namespace)::node_visible(PcRenderContext&, PmtNode const&, CourseProbe&, int&)`, ELF virtual address `0x10AA17C`. Disassembled with AArch64 GNU binutils from the original ELF on N100; SHA256 verified immediately before analysis.

## 1. Novel correction to the earlier research: this gate **accepts**, rather than suppresses, the node

The existing `QUEST_APK_COCKPIT_RUNTIME_PROVIDER_TLS_GLASS_CHAIN_20261025.md` only noted that `node_visible` reads `cockpit_occupant_draw` under a context byte `+0x35`, and speculated that it may *suppress* some nodes. The original opcodes now resolve the **direction of the branch** unambiguously: when both conditions hold, `node_visible` returns **true** with **LOD index zero** and bypasses the remaining normal frustum/LOD path. The previous suppression interpretation is not supported.

**Exact opcode/owner chain:**
1. `0x10AA1A0`: `x20=x0` captures the `PcRenderContext&`; `0x10AA1A4`: `x19=x3` captures `int& lod_out`; `0x10AA1B0`: `x21=x1` captures the `PmtNode&`. This distinguishes context/view from the node.
2. `0x10AA1B8`: `x23 = *(x20+0x18)` is the **matrix stack**, used for the initial model/view-space bounding sphere calculation.
3. `0x10AA20C..0x10AA224`: `x8=*(x20+0x10)`; copies 64 bytes starting at **view/service object +0x36** into the current matrix slot. This confirms that the context's `+0x10` field is a separate **view-like service pointer**, not the `PmtNode` argument.
4. `0x10AA3E8`: `x23=*(x20+0x10)`. `0x10AA3F0`: `ldrb w8,[x23,#53]` reads **view/service object byte +0x35**, not `PmtNode+0x35`. `0x10AA3F4` branches to the normal near/frustum path `0x10AA578` if zero.
5. If view/service byte nonzero, `0x10AA3F8..0x10AA404` resolves the native TLS address via an indirect getter; `0x10AA408` reads its byte. Cross-reference to existing TLS symbol mapping identifies **`cockpit_occupant_draw`**. `0x10AA40C` branches to `0x10AA94C` if TLS zero.
6. If **both** conditions are nonzero, `0x10AA410` writes **`lod_out=0`** (`str wzr,[x19]`), `0x10AA414` sets **return `w0=1`**, and `0x10AA424` goes to common function epilogue `0x10AAB6C` after stack-cookie check. The normal near/far/plane and LOD calculations are not executed.
7. When view/service byte is zero, `0x10AA578..0x10AA928` executes the normal near/side/far frustum checks and `0x10AAB30..0x10AAB58` computes LOD and compares threshold. When TLS is zero but view/service byte is set, `0x10AA94C` additionally offers an optional callback at view/service `+0x20` before falling into normal checks. **The forced-visible path bypasses that callback too.**

The bypass occurs **after** initial node-centre transform and bounding-radius calculation (`0x10AA1B8..0x10AA3E4`), so it is not a free zero-cost path. It does not prove the resulting mesh is rendered: later queue code can still reject an absent `mesh[0]` or exhausted queue capacity.

### Static truth table (branch-directed, not a runtime fixture)

| View/service byte `+0x35` | `cockpit_occupant_draw` TLS | Original native outcome |
|---|---|---|
| 0 | 0 | Normal frustum + LOD route |
| 0 | 1 | Normal frustum + LOD route |
| nonzero | 0 | Optional view callback, then normal visibility/LOD route |
| **nonzero** | **nonzero** | **Force `visible=true`, `lod_out=0`; skip normal frustum/LOD and optional callback** |

The exact **semantic name and writer** of view/service byte `+0x35` are **UNKNOWN**. Do not relabel it as an HMD mode flag, player ID, node flag, or globally enable it without proving its writer. Likewise, the original native code does not establish which precise driver/passenger/hand meshes encounter the gate.

## 2. Independent PC source cross-check (NOT original Quest source)

The public independent PC reconstruction `r4dius/outrun2-decomp`:
- `src/platform/pc_render_queue.cpp::node_visible` normally evaluates near/far/frustum planes and computes LOD based on projected bounding sphere and node flags. Its return `true` means **visible**, `false` means **culled**.
- `src/platform/pc_render_queue.cpp::walk_404d10` enqueues only when `node_visible(...) && node.mesh[lod]>=0`, then copies the selected mesh and centre depth to a draw descriptor. Thus **forcing LOD0 does not guarantee a drawable mesh**.
- `src/platform/pc_pmt_records.hpp::PmtNode` is 0x38 bytes, but the native `+0x35` test is **not** a byte of that node; the register provenance proves it belongs to the view/service object. Do not mistake node's last mesh index byte for this flag.
- This independent PC reconstruction does not expose the Quest-specific TLS gate or the original Quest view/service ABI; use it only to cross-check visible/LOD/queue semantics.

## 3. Distinct QuestCockpitV2 implementation risk

A V2 port that assumes this native branch hides the driver, or simply disables culling for **all** vehicle geometry, reverses its meaning and scope. A port that preserves only the general PC frustum tests may cull a valid near-seat occupant that the original Quest runtime deliberately admits. A port that forces all occupant meshes to LOD0 without confirming `mesh[0]` can also select a missing LOD.

**Review-only design contract:** preserve a separate **per-occupant, per-game-frame, view-owner-qualified** visibility decision. Do not conflate this with the independent `W × C` model correction, the scoped `matrix_F0` identity, the robot light-work scaling, glass opacity, general VR PMT culling expansion, or the driver-suppression policy. The view/service flag and TLS producer must be identified before a future V2 implementation chooses whether and how to reproduce this native override. Do not modify global `D3DRS_CULLMODE`.

## 4. Reproduction (read-only)

On the authorized N100 ELF, bounded research helpers:
- `apk/_analysis_focus/quest_20261026_1711_node_visibility_probe.py`: original ELF SHA256 plus node and prior robot symbol disassembly.
- `apk/_analysis_focus/quest_20261026_1711_node_visibility_branches.py`: original function entry, TLS branch destination and true/false epilogues.
- `apk/_analysis_focus/quest_20261026_1711_node_visibility_cull_branch.py`: zero-view-flag normal frustum path and LOD computation.
- `apk/_analysis_focus/quest_20261026_1711_node_callback_probe.py`: optional callback route `0x10AA94C..0x10AA9B4`.

Direct command equivalent (read-only; no game execution):
```sh
aarch64-linux-gnu-objdump -d -C \
  --start-address=0x10aa17c --stop-address=0x10aab90 \
  liboutrun_quest_core.so
```
Verify register provenance `x20=x0`, `x19=x3`, `x21=x1`, `x23=[x20+0x10]`; then follow `0x10AA3F4`, `0x10AA40C`, `0x10AA410/414`, `0x10AA424`, and normal `0x10AA578`. These addresses are **ELF virtual addresses**, not Windows EXE RVA or D3D9 hooks.

## 5. Next independent research and limits

1. Identify original **writer/semantic field** for view/service `+0x35`, plus the view-service callback at `+0x20`; determine whether the byte is toggled during cockpit mode, culling override or some unrelated render mode.
2. Find **producer and lifetime** of `cockpit_occupant_draw` TLS around `race_robot_display_487880` / `rob_disp_disp_514E60`, with normal and exceptional cleanup. Do not assume every robot or passenger shares the player owner.
3. Map actual affected PMT nodes and availability of `mesh[0]`, including near-seat driver geometry, then test with bounded runtime logging only after explicit future integration authorization.
4. Confirm that Quest3 left/right views use the same intended visibility owner before changing the PCVR renderer.

**Evidence level:** original ARM64 gate/return/LOD control flow **BINARY VERIFIED**; PC queue semantics **INDEPENDENT RECONSTRUCTION CORRELATED**; exact view flag identity, producer, affected meshes, HMD behavior and FPS impact **UNTESTED/UNKNOWN**. No claims of actual Quest3 visual improvement.

**CODE_CHANGE=NO | FILES_CHANGED=1_RESEARCH_MD_ONLY | R26+HUD=UNCHANGED | MOZA_R3_FFB=UNTOUCHED | CI=NOT_RUN | QUEST3_HMD=UNTESTED**.
