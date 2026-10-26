# QuestCockpitV2 REA deep algebra — compact matrix_B0/matrix_F0 body-correction formula

**Analysis date:** 2026-10-26 KST. **Mode:** REVIEW_ONLY, documentation/standalone research code, not a production mod patch. **Hardware target:** Quest 3 PCVR with MOZA R3 physical wheel; no tracked hands or virtual-wheel input.

## 1. Evidence and exact input ownership

Authorized user-owned original Quest APK ELF `liboutrun_quest_core.so`, SHA256 `fa0f9db9b744515a9a1439741bc9806ad007470b621b88d22a0b6`.

Original native `PcSceneRenderer::render_frame` ELF **`0x10CBE9C`**, 2,816-byte routine:
- Only on original native event `(eventFlags & ~2)==0x10` plus cockpit setting enabled plus valid paired vehicle/camera provider and camera `[+0x34A]==1`.
- The **first** callback result is vehicle bytes, with `EVWORK_CAR::matrix_B0` at `+0xB0` and `matrix_F0` at `+0xF0`. The **second** is camera bytes, from which mode 1 is read.
- Original ARM64 correction instruction span `0x10CBF6C..0x10CC2FC` writes 16 float values to thread-local `cockpit_body_correction`, then changes the **vehicle's** `matrix_F0` to identity for a scoped render and restores all original floats on normal and exceptional exit.
- Downstream `Draw::disp_514c30` uses the separate `cockpit_occupant_draw` TLS and multiplies an *occupant model* matrix by the correction. **This is NOT a camera pose override and must not replace base HMD tracking.**
- Existing `docs/research/quest_cockpit_body_correction_reconstructed_20261025.cpp` is a 240-assignment, 211 generated-op, ARM64-to-FMA clean-room research transcription, **not original authored C++**. Original machine-level arithmetic remains the authoritative evidence.

## 2. New closed-form affine result: dramatic simplification

Represent vehicle matrices `matrix_B0=A`, `matrix_F0=B`, using row-major 4×4, upper-left 3×3 `A_R`/`B_R`, and translation in indices `12,13,14` (column-vector algebra is used to describe the 3D translation formula; the stored 4×4 is still row-major). Let:

```text
D = diag(1,-1,1)
C_R = - transpose(A_R) * transpose(B_R) * A_R
C_t = [I + transpose(A_R) * B_R * D * A_R] * t_A
                - [transpose(A_R) * B_R] * t_B

Quest correction C (row-major):
C = [C_R(0,0), C_R(0,1), C_R(0,2), 0,
     C_R(1,0), C_R(1,1), C_R(1,2), 0,
     C_R(2,0), C_R(2,1), C_R(2,2), 0,
     C_t[0],     C_t[1],     C_t[2],     1]
```

**New finding**: on affine inputs this **compact 3×3 plus translation representation** matches the long ARM64-FMA transcription within float32 rounding error; it is not necessary to keep 240 intermediate C++ assignments in a future implementation. The `D` sign on the Y coordinate is important and must not be silently removed by normalizing axes.

Identity fixture `A=I`, `B=I` yields `C_R=-I` (determinant -1). This indicates an **orientation-reversing reflection** in the correction matrix, not merely a proper 3D rotation. This operation belongs to the occupant **model** transformation. Blind application to view/culling matrices could reverse winding/culling or introduce double head transforms.

For a car `A=I`, `B=I`, arbitrary translations the exact synthetic output is `C_t = [2a_x-b_x, -b_y, 2a_z-b_z]`. This odd Y-axis asymmetry was independently observed before the closed-form derivation. A generic `C = inverse(B)*A` formula is **wrong**.

## 3. Numerical evidence — actual compiled C++ long-form versus compact model

Executed on the user's N100 using `g++ 13.3.0`. The original clean-room long formula was compiled directly from `docs/research/quest_cockpit_body_correction_reconstructed_20261025.cpp` (locally cached under `apk/_analysis_focus/`), linked with bounded fixture tests. All tests compare against the *independent, pre-existing* 240-assignment version, not against original HMD output.

| Reproducible fixture | Number of independent inputs | Result |
|---|---:|---|
| Proper rigid-body rotations + translation (seed 20261026) | 250 | C_R max absolute error **1.18e-7**, C_t **1.57e-6** |
| General affine, including nonorthogonal/sheared/scale rotation components | 125 | C_R <= **1.77e-6**, C_t <= **3.25e-6** |
| General non-affine 4×4 stress (some perspective/homogeneous terms nonzero) | 125 | The 3×3 rotation/translation *subexpressions* remain close, but the extra homogeneous elements **do not**, and output[3,7,11,15] cannot be reconstructed by the affine model |
| **Standalone C++17 compact header vs existing ARM64 transcription** (fixed mt19937 seed 20261026) | **2,000 fresh random affine pairs** | **PASS**, maximum absolute entry error **7.629394531e-6**, maximum relative entry error **1.651908946e-6** |
| Malformed/NaN/non-affine rejection fixtures | 2 | **PASS**, previous result value unchanged on failure |
| C++ compiler | `g++ -std=c++17 -O2 -Wall -Wextra -Werror -pedantic` | **PASS** |

For 246 random proper-rotation fixtures (excluding four hand-selected initial cases), determinant `det(C_R)` fell between **-1.0000002100 and -0.9999997889**, maximum orthogonality error **3.0500564e-7**. These are exactly the synthetic fingerprints expected of an orientation-reversing matrix after float32 rounding. For nonorthonormal data det need not be -1; do not use an unconditional determinant-equals-minus-one check on real vehicle matrices.

## 4. New useful artifacts (all research-only, isolated from live game)

- `docs/research/quest_v2_affine_correction_candidate_20261026.hpp`: `IsFiniteAffine`, `ComputeQuestBodyCorrectionAffine(matrixB0,matrixF0,output)`, compact algebraic candidate. Uses temporary output and **leaves the destination unchanged** when inputs are not finite, not affine (4th column malformed) or output overflows.
- `docs/research/quest_v2_affine_correction_candidate_20261026.test.cpp`: deterministic 2,000 synthetic affine regression pairs, identity reflection assertion, NaN/non-affine rejects. The header has **no** dependency on game memory, D3D9, Quest/XR runtime, wheels or legacy cockpit code.
- The original long-form reference remains `docs/research/quest_cockpit_body_correction_reconstructed_20261025.cpp`. These two versions must remain separate for continued numerical regression checking.

From the repo root, a compatible C++17 compiler can build *only the research fixture* (not the PC game):
```sh
g++ -std=c++17 -O2 -Wall -Wextra -Werror -pedantic \
  docs/research/quest_cockpit_body_correction_reconstructed_20261025.cpp \
  docs/research/quest_v2_affine_correction_candidate_20261026.test.cpp \
  -o /tmp/quest_v2_matrix_fixture
/tmp/quest_v2_matrix_fixture
```
The executable should print `PASS 2000 random affine tests...`. This must **never** be described as a Windows VR build or Quest3 runtime validation.

N100 private numeric research:
`apk/_analysis_focus/quest_v2_body_matrix_random250_PRIVATE.json`,
`quest_v2_body_translation_dependency_PRIVATE.json`,
`quest_v2_body_matrix_formula_250_nonrigid_PRIVATE.json`;
analysis scripts `quest_20261026_body_matrix_cpp_random250.py`,
`quest_20261026_check_rotation_candidates.py`,
`quest_20261026_matrix_translation_probe.py`,
`quest_20261026_body_matrix_formula_250verify.py`,
`quest_20261026_body_matrix_formula_nonrigid.py`,
`quest_v2_affine_correction_candidate_20261026.run.py`.
Only original clean-room C++ and its mathematical findings are committed, not raw copyrighted game assets/binaries.

## 5. Applied design implications for the deferred QuestCockpitV2 full rebuild

1. **Delete all legacy DriverSeat runtime hooks at the eventual atomic cutover**, but keep unrelated FixZBufferPrecision, RestoreCarBaseShadow, culling, menu, rank/GOAL/HUD, stereo transport and MOZA R3 FFB. Do not patch existing camera-offset routine into the new foundation.
2. Establish actual **game-frame + player identity + native mode1** owner; no equivalence between `frame_render_449050`, `BeginScene` and `PresentEpoch` has been proven by runtime tests.
3. Capture both **B0 and F0 from the same verified player render-frame**. Affine validation, finite values and player identity checks precede the compact body-correction calculation.
4. Use Quest's original operation scope: stage `F0 = identity` on a **renderer-local player-car copy only**, while the corrected occupant-model matrix is applied inside the correct player model draw scope; normal/error restores must not alter game physics or simulation data.
5. **Preserve matrix reflection parity**; investigate winding, frontface, two-sided materials and culling for occupant models separately. The model correction is not an XR head or eye view matrix.
6. On tracking/mode/player/focus/recenter generation changes: invalidate the frame and fail open to non-cockpit original rendering. No stale camera or reused B0/F0 snapshot.
7. The exact role and handedness of `A_R,B_R`, after subsequent renderer `pc_matrix_push`/multiply and D3D9 view transformation, require original car model display call-graph verification and Quest3 HMD test. **The closed formula is a math contract, not proof of visual parity.**
8. New windshield/alpha path, if any, is separate and must remain disabled until matching player draw-entry ownership/mesh identities.

## 6. Explicit status

**NEW_CLOSED_FORM=DERIVED_AND_NUMERICALLY_VERIFIED** on 2,500 synthetic cases across groups. **REA_ORIGINAL_ASM_REF=PREVIOUSLY_VERIFIED**, not recompiled proprietary source. **LIVE_GAME_SOURCE_CHANGED=NO**. **LINUX_CPP_FIXTURE=PASS**. **WINDOWS_GITHUB_ACTIONS_BUILD=NOT_RUN**. **QUEST3_HMD_RUNTIME=UNTESTED**. **USER_REQUESTED_LATER_INTEGRATION=HONORED**.
