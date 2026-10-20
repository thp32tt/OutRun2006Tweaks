# R26 projected car-rank/rival regression: historical source delta audit

Date: 2026-10-21 KST. Review-only user request; **no game/runtime code change**. Authoritative branch `vr-d3d9ex-focus` (read head `5f089983ade9efe6bb6d3c6a657a5b69a5734d1e`). Evidence in `docs/VR_HUD_KNOWN_GOOD_RESTORE_RUNBOOK.md`, `docs/automation/reviews/AI2_DX9EX_HMD_HISTORICAL_REGRESSION_20261009.md`, `docs/automation/reviews/DX9EX_HMD_FEEDBACK_20261009_2348_RANK_TIME_PERF_RESOLUTION.md`.

## Actual user HMD evidence — categories NOT one universal all-pass ZIP

- 2026-09-26 R57_06: 1–3 ordinal projected car markers follow cars with head yaw. R57/R58 report cited in restore runbook.
- 2026-09-26 R62 source **`945e4471d6463f757f38b4b39d3eb8e492b2254f`**, fixed-function indexed renderer blob `31ab2c90ed20943bd563bccb7914c064ca92db7c`: 4–5 attached/single in Quest 3. In that distinct test, 6th/result/menu other issues remained.
- 2026-09-26 R64 `10c73daa037b5cc521b42ce7fb3a7cc1820b1921`: 6th/6 normal and HUD resize works, **not** a complete rank/flare/result PASS.
- OutRun rival separately user-confirmed properly attached in 5868/f490 and **2026-10-09 exact `a6f8497c2fbe83959984275c30fbf43aa6a72d55`**: 1–5 displayed single/no head following BUT detached from car; rival attached. This disproves treating 1–5 stereo fusion as car anchoring success.
- Historical complete simultaneous all 1–6 + rival exact user-loaded source hash **not attested**.

## Concrete source-regression chronology

1. **10/07 `71f1663c14d5`: broad `sub_4BAD20` NaviPub reuse split.** Four parent callsites `0xBEB98/0xBED83/0xBED9E/0xBEDAE` became `RankMarkerSubSemanticDest` with `RankMarkerSubScreenHudDepth` and force rank sprani/clip into ScreenHud when depth != 0. This is correct for true NaviPub 2D text but introduces an owner-priority barrier. Code prior to it (e.g. `b3edb278c9e1`) keyed 3D classification directly on actual recovered `RankMarkerProjectedInfo.valid`.
2. **10/08 `0173641d1e34`: added `RankMarkerSubActiveDepth != 0` to exact `Calc3D2D` rank capture.** HMD-proven `0xBAEE7` source could be rejected if optional parent inline hook not active. **Confirmed source regression** against R57_06, later removed in `270e7a15f022`; however `RankMarkerSubScreenHudDepth==0` remained.
3. **October refactor: lost R62 fixed-function indexed owner.** HMD-proven FVF0x142, null VS `R62TryFixedFunctionSpriteIndexed` path was absent from failing R84 branch. Restored in `f2153aa26356`. It is PRESENT in current R26 safe and invoked after external F11 and before generic routes. Thus the old omission is a historical cause, not a currently missing function.
4. **October refactor: lost R64 D3DXSprite vtable[9] Draw -> vtable[10] Flush isolation.** Different ordinal/rival sprites could share a batch and wrong marker anchor. Restored in `87a275de7d02`; current `VRProjectedD3DXSpriteIsolationR64` present. Its physical *successful count* in current Quest3 is still unproven by merely inspecting source.
5. **10/08–10/18:** native producer scoping `ScopedProducerSemantic` migrated to exact producer + multiple queued SpriteNode lifetime/epoch guards and selective raw WVP gates. Source differences are real, and may reject legacy ranked draws. Queue-count/pass/fail source logs must identify *which* class and GPU API reaches R62/R57. No single commit proven first optical regression for both.
6. **10/19 `b0d6f977e793`: +32 native 640x480 Y lift cancellation** introduced **only when projected marker anchor valid**. This cannot rescue an invalid marker; if valid, moves rank by 32 native pixels and should be optically A/B against old car-position offsets. Does not apply to rival.
7. **10/20 `fbcb0cb3`/`3ed5290c`: ordinal-only eye-cant added** relative to original R57_06 identity eye rotation; later default `RankDx11ReferenceEyePose=true` reverted that difference. With `projectedMarkerSemanticCount=0`, neither formula is reached, so eye pose alone could not fix the user complaint.
8. **10/21 `0d25480814d0` and verification `8a456a8`: last unverified fix**, allows exact `0xBAEE2` ordinal source to override active NaviPub parent and, with valid anchor, tags rank children `ProjectedWorldMarker2D`. It separately installs a rival exact `0xBB6F0` E8 wrapper. **Warning:** exact `0xBAEE2` is inside shared `sub_4BAD20`, which all four NaviPub parents can invoke. Therefore E8 proof by itself does NOT distinguish a real opponent car from a legitimate NaviPub screen-HUD rank; `rawFinite` and negative view-Z alone are not proven to make that distinction. The new override can inadvertently give NaviPub HUD a 3D source if its internal projected point validates. New rival E8 is also absent from the 71-E8 canonical binary manifest; its byte signature and runtime hook install/result need independent proof before claiming fully recovered. **Do not declare optical PASS** from source or CI.

## Most likely remaining failure boundary

Original `Calc3D2D` E8 → call context (NaviPub vs actual vehicle, preserve one car per owner) → original 3D anchor `valid/viewX/Y/Z` → exact 1–3 sprani, 4–6 clip, rival `BB796` source/queue identity → D3DXSprite Draw/Flush split → R62 FVF0x142 or R57 shader/XYZRHW → LEFT/RIGHT eye submission.

Runtime `projectedMarkerSemanticCount=0` while rank producers active proves the **projected class never reaches stereo renderer**, but not why individual samples are NaviPub. Separate real-vehicle parent and NaviPub samples by original E8 parent-site return *and game state, source node, sourceZ, proof of screen-world provenance*. Do not use aggregate `sourceZ<0` as sole classifier. For rival, compare original 0xBB6F5 capture + `RivalMarkerProjectedInfo` consumed in 0xBB796, before changing its earlier HMD-good route.

## Proposed controlled next step, not implemented

1. First confirm/obtain exact historically HMD-accepted 1–3 R57_06 and R62 4–5 artifacts (with DLL identity) and test settings `OUTRUN_VR_R57_MODE=6`. Do not treat `0cff83cf` as all-rank HMD GOOD: its source already contains NaviPub priority gate.
2. Protect menu 4:3/landscape source, car selector, 6th/6, DX11-proven eye pose, and currently present R62 + R64 hooks. Do not wholesale revert the full branch or activate R84.
3. A/B per source class: exact car vs NaviPub four parent callsites; left/right counts, recovered WVP, R64 flush and true 3D anchor vs screen HUD. Require same-sha Windows compile/package, actual HMD confirmation before promotion.
4. Due to collision risk, specifically review **whether 10/21 NaviPub bypass must be narrowed/reverted** after independent parent-source evidence. User currently asked for diagnosis, **no source code altered by this review**.

Status: `HISTORICAL_SOURCE_DIFF_CONFIRMED`; `FIRST_SINGLE_BAD_COMMIT_FOR_ALL_CAR_RANK_AND_RIVAL=NOT_PROVEN`; `RUNTIME_VALIDATION=UNTESTED`.
