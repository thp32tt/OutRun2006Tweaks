# DX9Ex R26 — 16.57 GiB screen-error evidence (2026-10-22)

Status: **static/log evidence archived; R69 CABE flare fix implemented separately in the same change. HMD optical validation remains UNTESTED.**

## Evidence bundle identity

The raw capture is intentionally **not committed to Git**. It remains an external evidence bundle because the expanded game log is 17,790,238,505 bytes.

- N100 evidence bundle: `~/logs/OutRun_vr_debug.zip`
- ZIP size: 316,650,363 bytes
- ZIP SHA-256: `3f6fa0168dd9e645ecbf5d4ac1e15f510d1a28fc75d75d6384d622a62e7a89e7`
- `OutRun2006Tweaks.log`: 17,790,238,505 bytes, compressed 316,586,771 bytes, CRC32 `0f38fbe1`
- `OutRun2006Tweaks-hudtrace.csv`: 777,700 bytes
- visible log interval used by the focused samples: approximately 2026-10-22 00:17:16–00:23:50 KST
- capture source resolution/backbuffer: 3440×1440; `HudScale=0.55`; `LensFlareCentreEnabled=true`
- device probe reported plain `IDirect3DDevice9` (`D3D9Ex=0`). The helper log explicitly says zero-copy cross-process sharing was unavailable in that run.

The game log does not emit a trustworthy Git source SHA for this capture, so this document does **not** claim exact-SHA runtime validation.

## Whole-log counters

The 16.57 GiB file was processed as a stream rather than loaded into memory.

| Family | Count |
|---|---:|
| PRESENT_PRE / PRESENT_POST | 13,828 / 13,828 |
| DRAW_BEGIN | 7,214,489 |
| DRAW_STATE | 14,428,978 |
| MATRIX | 14,428,978 |
| D3DX events | 1,340,138 |
| STATEBLOCK events | 2,403,951 |
| route `GUARD_R29_NATIVE` | 6,945,288 |
| route `XYZRHW_UP` | 251,226 |
| route `R62_FIXED_FUNCTION` | 14,839 |
| route `F11_IMGUI` | 3,136 |
| route `FiniteHud` | 14 |

Focused producer counts include `LENS_FLARE_CENTRE_C993=9,806`, `DISPLAY_RANK_FIRST=18,628`, `DISPRANK_KIND0_CLIP=37,256`, `RANK_MARKER_SPRANI=326`, `RANK_MARKER_CLIP=3,987`, `OUTRUN_RESULT_PROGRESS=45`, `EXACT_SCREEN_HUD_CLIP=45`, and `OUTRUN_HUD_TEXT=89,224`.

## Screen-error findings

### 1. Rank marker source is now proven valid in this capture

The exact `0xBAEE2` rank `Calc3D2D` edge reports `rawFinite=true projectionValid=1`. Bounded physical-producer telemetry also reports `anchorValid=1 ordinalCant=1 projected=1`, with representative `sourceViewZ=-103.381996`. The 1st–3rd producer reaches the physical draw as `scope=ProjectedWorldMarker2D`, `producer=RANK_MARKER_SPRANI`, and exits through `XYZRHW_UP` without a D3D failure.

This supersedes older captures where `anchorValid=0/projected=0`. It proves source ownership and a stereo-capable draw route, **not** final Quest 3 optical correctness. No exact rival-marker producer was observed in this capture, so rival correctness cannot be inferred.

### 2. GOAL result-progress GPU submission is bilateral

`OUTRUN_RESULT_PROGRESS` appears in the D3DX queue and the bounded physical result trace records 14 `FiniteHud` samples with LEFT=`S_OK`, RIGHT=`S_OK`, `projectionRestored=true`, and `frameIncomplete=false`.

That removes “right eye draw failed” as the explanation for the observed duplicate result-progress image in this capture. It does not prove binocular convergence. The separate +TIME producer was not observed here, so +TIME remains an independent unresolved path.

### 3. C993 centre is exact, but remains native/fallback in this capture

`LENS_FLARE_CENTRE_C993` is observed 9,806 times. Representative physical state is exact `scope=WorldBillboard`, `producer=LENS_FLARE_CENTRE_C993`, FVF `0x112`, with a shader bound. The last focused sample exits as `route=GUARD_R29_NATIVE`.

The dedicated proof reports `rawOwned=0 worldRoute=PreserveOriginal` from the first sample through the bounded 4,096-hit sample. Therefore this log does not prove a source-owned C993 stereo transform. Previous HMD testing also showed that simply hiding C993 does not remove the remaining doubled central light, so this change does not reintroduce suppression as a “fix.”

### 4. CABE projected flare has a concrete DX11/R26 route divergence

The current hook already marks the exact EXE +0xCABE projected flare as `RenderScope::ProjectedScreenEffect2D`.

The known-good DX11 comparison branch has an HMD-reviewed R69 route that treats this as a **centre-eye screen effect**: it submits the same original WVP to LEFT and RIGHT instead of reprojecting the already-`Calc3D2D` screen position independently. The R26 safe path had lost that dedicated class and instead reclassified projected-screen effects as `WorldBillboard` or `PerspectiveHud`, allowing a second head/IPD transform.

The accompanying source change restores the exact `ProjectedScreenEffect2D` class and zero-disparity L/R fusion only for that exact semantic owner. Generic SceneEffect, C993 centre, HUD, rank markers, F11, and cockpit paths are unchanged by this fix.

### 5. F11 draw path itself shows no D3D failure

3,136 focused `F11_IMGUI` draw-state events complete with `failure=0`. The current branch also contains the later `world-lock and shrink F11 overlay` source fix after this capture lineage. No additional F11 mutation is justified by this log alone.

## Transport limitation

The end of the focused transport summary still reports `composed=0 directTransport=0 poseSeq=0` with fallback accumulation while `directOnly=1`. Therefore this 16.57 GiB dataset is excellent for game-side producer/draw provenance, but it is **not** an HMD optical PASS and cannot certify final left/right compositor visibility.

## Reusable evidence files outside Git

The streaming parsers produced these N100-side working artifacts: `evidence_awk_summary.tsv`, `evidence_producer_counts.txt`, `evidence_targeted_summary.txt`, `screen_issue_summary.txt`, `lens_c993_summary.txt`, `flare_object_summary.txt`, and the extracted `hudtrace.csv`.

Git stores this normalized report plus the machine-readable JSON below so future reviews do not need to rescan 16.57 GiB for the same conclusions.


## Validation performed on the source change

PASS on the modified worktree:

- `tools/verify_dx9ex_r26_projected_flare_fusion.py`
- `tools/verify_vr_dx9ex_launch_paths.py`
- `tools/verify_vr_r30_screen_hud_finite_plane.py`
- `tools/verify_dx9ex_gpu_visual_20261014.py`
- `tools/verify_dx9ex_r84_lens_source.py`
- `tools/verify_vr_r26_result_hud_pose.py`
- `tools/verify_vr_20261020_hmd_baseline.py`

Three legacy broad/specialized validators currently fail on the unmodified parent `d68888ba0c436b67a9f16170b8c17af2ac459d10` as well as the modified tree: `verify_vr_visual_composition_p0.py` (pre-restart HUD provenance assertion), `verify_vr_projected_marker_anchor.py` (negative-W policy assertion), and `verify_vr_f11_font_density.py` (older F11 affine assertion). They are recorded as pre-existing validator/HEAD drift rather than regressions caused by R69. The broad visual validator was updated only where its R69 contract itself changed; its earlier unrelated baseline failure remains visible rather than being hidden.

HMD/Quest 3 runtime validation: **UNTESTED**.