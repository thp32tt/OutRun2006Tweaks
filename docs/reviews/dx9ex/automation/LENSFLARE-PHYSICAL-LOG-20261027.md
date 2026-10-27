# Lens flare C993/CABE physical-log escalation — 2026-10-27

- TASK_ID: `LENSFLARE-PHYSICAL-LOG-20261027`; mode: **read-only telemetry plus negative regression guards**; branch: `vr-d3d9ex-focus`; source SSOT: GitHub.
- Review baseline: `LENSFLARE-REVIEW-APPLY-20261027.md` and `CONVERSION-DX9EX-01522..01533`, original opaque 4056D0/4052C0 split, R26 query-specific single execution and normal one XR projection layer.
- Existing `[VR] Telemetry = true` default; additional logs sample first 32 matching R30 native events and power-of-two increments. Output is observational; no new EXE instruction hook, ray correction, alpha suppress, depth override, shader edit or host compositor change.
- Applicable material commits: `52edf64122e19ae0f1aa45d2f7b2f65de3c3a72b` (native class + L/R receipt), `be93cc0db2f9bea0fe6f6964975d363173e5ca83` (game c64 gate), `d12eac9bd339057eb4e2925d871aa1de2dd7e0c9` (sampled live VS/FVF), `35699cf9232074498f60687bd49f6d96646f6ceb` (R30→R29 fallback). Verifier `tools/verify_vr_lens_physical_telemetry.py` and official workflow gate added. Exact final validation to be recorded after CI.
- `RUNTIME_VALIDATION=UNTESTED`; headset visual root cause still **OPEN**.

## Log-to-evidence matrix

| Event | Proven | **Not** proven |
| --- | --- | --- |
| `VR LENS C993 SOURCE ADMISSION` | Hooked original 0xC993 call ID/sequence/scope and mod SpriteNode queue flag | Original opaque 4056D0 mesh submission, 4052C0 flush, physical eye RT/pixels |
| `VR LENS 570008 ORIGINAL BOTH DRAWN` | Original 0xCABE source ordinal, alpha, flags, ambient mod semantic | Same-eye re-rendering; source ordinal is not a GPU draw ID |
| `VR LENS GAME C64 GATE` | Observed c64 upload entry, captured draw serial/scope, camera override and projected raw eligibility | Native upload success, physical source/object correlation, final WVP |
| `VR LENS R30 PHYSICAL CLASS` | Actual R30 native call serial/site, semantic at GPU entry, R30 class, *sampled* live VS binding/FVF HRESULT and values | An actual CABE/C993 object ID; the cached shader and original PMT identity |
| `VR LENS R30 PHYSICAL EYES` | R30 admitted native draw left/right HRESULTs, restore, latched pose, source cameraSync flag, exact left/right WVP equality and translation terms | Final GPU pixels, actual per-object alpha, source mesh identity, correct angular optical alignment |
| `VR LENS R30 LOWER FALLBACK` | R30 rejected that classified screen candidate (`E_NOTIMPL`) and delegated to R29 | Whether subsequent R29 physically rendered/duplicated the primitive |
| existing R7/R26 occlusion query logs | Tracked query per-original-native-Draw single-exec condition | A single Draw per BEGIN/END; original PMT walker can contain multiple legitimate Draws |

## What counts as a root-cause confirmation

1. **Same-eye duplication** requires *the same original object invocation + opaque descriptor + mesh/primitive/pass + material + texture + colour-write mask* submitted more times than the original against the **same eye RT**. Two source 0x570008 ordinals, R30 L/R pair and a 0x570010 query with N legitimate draws are NOT evidence of duplication.
2. **Mixed eye policy** is supported if (after real source/physical identity correlation) queued CABE ordinal1 reaches SceneEffect or R29, while the immediate ordinal2 or C993 uses R30 ProjectedScreenEffect2D with different valid eye constants under the same fresh pose; physical eye placement/pixel verification is still necessary.
3. **Directional head-lock** should be tested while game sun direction is fixed: a fresh source-eye pose and changing headset **yaw** must change head-relative angular direction. Pure headset translation with zero sun parallax is consistent with the original camera-relative far sun; do not inject artificial finite depth.
4. **Host duplication** needs two unintended same-tick composition operations. Reuse of paired source-eye metadata on a later cached tick alone does not prove same-tick overlay duplication.
5. An absent `VR LENS R30 PHYSICAL` event does **not** establish that there were no lens GPU draws: fast XYZ/RHW paths or lower R29 may execute without that R30 admission.

## Field capture checklist for one actual Quest 3 / VDXR reproduction

- Keep `[VR] Telemetry = true`. Observe the same stationary game scene containing visible sun discs for a few seconds; turn headset **yaw slowly** left and right, then return to center. Avoid changing graphics options or permanently enabling high-volume trace.
- Retain log segments containing `VR LENS`, `R30`, `R26`, `R7`, game c64 and host fresh/cache/pose information together, including **frame order**. Do not filter down to isolated positive "FLARE FIX" or paired-eye PASS strings.
- Compare the original visible 0x570002/006/00F and CABE 0x570008 alpha siblings separately from 0x570010 zero-colour occlusion query and its legitimate multi-primitive traversal.
- If physical IDs are still unlinked after the session, the next escalation is an **exact opaque descriptor/flush-generation correlation** at an already proven safe source site, not speculative changes to 4052C0, R84 default, renderer c64, Quest host cache, or unsafe B9200 post-call instructions.

## Release constraints

- No forced new stereo depths, opacity/visibility changes, child suppression, R26 query replay, host XR layer duplication, GL/DX11/DXVK changes, or production/performance improvement claims.
- Static/CI PASS is not Quest3 optical PASS; final `RUNTIME_VALIDATION` stays `UNTESTED` until game/HMD evidence.
