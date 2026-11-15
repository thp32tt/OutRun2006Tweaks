# Ferrari F50 external sidecar importer prototype — separate-directory R26 D3D9Ex

## Scope and safety
This is a **model-free** test build, never a redistribution of the CSR2-derived external F50 model. The local external sample has unresolved underlying rights; user must independently ensure permission to convert/use. No source model, resulting OVC, original game EXE/PMT/XPR or screenshots are committed to this branch. Do not publish the privately produced OVC without rights.

### Actual local conversion QA (N100, 2026-11-15 KST)
- v0.1 Importer staged externally obtained Ferrari F50 GLB as `staged_car.blend` (SHA256 `f3d169a0125bd296de0371780c4ec7e604785227648b8710392efbd8d9d437c6`) and `staged_car.glb`.
- New Blender worker converted that **actual** staged external model to **OVRCABH2 v2**: `F50_External_Test.ovc`, 26,640,731 bytes, SHA256 `e59b15df0923598165350948123dab8de5af8ffabbc78f9d9b30d64dbc3e221e`; 875 input Blender mesh objects were batched into 17 OVC groups, 17 materials, 637,914 expanded vertices and 212,638 triangles. Window/glass meshes were deliberately skipped (not transparent in the fixed-function path).
- Exact existing native C++ parser `src/vr/game/dino_external_sidecar.hpp` compiled with g++ -std=c++17 and **parsed the full real OVC**: `F50_OCR2_CPP_PARSER_PASS groups=17 materials=17 vertices=637914 triangles=212638 hq=1`.
- Source original F50 PMT SHA256 `10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab` stays unchanged. No game process was launched; **Quest 3 stereo visual and game/launcher runtime are still UNTESTED**.

## Original-preserving runtime path
- Based on the independently developed `feature/dino-external-pbr-runtime-v1-20261106` conditional R26/HUD original-display replacement. Existing Dino path is retained untouched when new opt-in test flag is absent.
- F50 `car_kind_11==0`, Dino ==1. Resource-index correspondence corroborated by public `r4dius/outrun2-decomp/src/platform/frontend_vehicle_data.hpp` model list: F50 first, Dino second.
- Only the F50 player, VR stereo, native mode-1 cockpit, valid eye/pose, non-recording device state and explicit `OUTRUN_VR_F50_EXTERNAL_TEST=1` are allowed to attempt alternate draw. The separate default `[VR] F50ExternalSidecar=true` is harmless without that environment flag.
- Loader default: `<copied-game>\\ExternalModels\\F50\\F50_External_Test.ovc`. If process env `OUTRUN_VR_EXTERNAL_MODEL_DIR` is an **absolute local directory**, load `F50_External_Test.ovc` from that directory instead. No game `Cars/*.sz` writes.
- Missing/corrupt sidecar or failed pre-submission draw falls back to original player callback, matching the inherited gate. Partial draw can temporarily hide the original for that eye/frame to avoid double geometry, quarantining GPU state until Reset.
- No per-car wheel animation decomposition, shader parity, passenger/driver effects, HUD/menu end-to-end correctness, or 120-fps stereo budget verified. Full exterior F50 experimental OVC is **not** a tested production VR asset.

## Using the test artifacts safely
1. Get an authorized `.glb`, select official Blender 4.5+, use the Windows Importer to **Stage** then **F50 OVC2 출력** to a fresh separate model folder. The user owns and retains that OVC file; it is not bundled.
2. Make a complete **COPY** of the game. Place an empty file called `.F50_TEST_COPY` beside the copied `OR2006C2C.EXE`. Never test against the live game folder.
3. Extract the **exact matched** R26 DLL/x64 OpenXR host/launcher bundle into the copied game's root; the package contains `QUEST_APK_COPYRUN_PAYLOAD/IDENTITY.json` and all same-SHA dependencies. Test preflight with `powershell -NoProfile -ExecutionPolicy Bypass -File .\\QuestCockpit-CopyRun.ps1 -Mode F50 -F50ModelDir "C:\\external-models\\f50" -VerifyOnly`.
4. Drag the **separate** OVC directory onto `RUN-F50-EXTERNAL-TEST.cmd`. The launcher sets the opt-in environment only for its child run, never globally; model bytes are not copied into the game or GitHub. No `Cars/` change.
5. If any issue occurs, use the provided `RESTORE-QUEST-APK-COCKPIT.cmd` on the copied game. Do not replace an active release DLL or mix a different-sha host.

**Verified:** actual external GLB -> Blender -> OVC2 serializer -> independent existing C++ parser. **Unverified:** compiled F50 sidecar renderer working in live game, physical Quest 3 stereo/120Hz/frame timing and full car visual parity.
