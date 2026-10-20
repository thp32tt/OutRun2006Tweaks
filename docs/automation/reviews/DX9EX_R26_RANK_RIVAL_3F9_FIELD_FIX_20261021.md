# R26 rank 1–6 / rival 3D attachment: DX11 comparison and Quest3 source fix

Date: 2026-10-21 KST. Direct user authorized source patch; scheduled automated DX9Ex lane remains REVIEW_ONLY, no autonomous edits.

## Authority

- DX9Ex HMD bundles: `20261020T154943238Z-ebe01a01`, `20261020T155629142Z-881e3904`, and `20261020T154512586Z-128303ea`, all source SHA `3f9ccd3b122d...`.
- User confirms DX11 test build's car-mounted ordinal and rival markers have correct stereo depth.
- DX11 `vr-dx11-native-r71`: native `Calc3D2D_dest` recovers original game-view point at ordinal 0xBAEE7; mode 6 uses per-eye projection + HeadInverse + relative eye IPD/FOV, without ordinal eye-cant. In DX9Ex R26 that pose policy is already the default `RankDx11ReferenceEyePose=true`.
- **Why the previous DX11 parity patch made no visible difference:** the source anchor never became valid, so the VR renderer never reached that corrected pose. The broken condition was upstream of the eye-pose math.

## Root-cause evidence from 3 physical runs

- `VR R57 ORDINAL EDGE PROBE` at exact original x86 E8 0xBAEE2 executed 16,384+ times; game view-space sourceZ is often -109, -69, -29 and moves as vehicles approach. `rawFinite=true` throughout samples.
- Yet `projectionValid=0 navipubDepth=1` for every sample and `projectedMarkerSemanticCount=0`.
- `src/hooks_uiscaling.cpp::Calc3D2D_dest` rejected all ordinal source captures when `RankMarkerSubScreenHudDepth != 0`, **even at the independent exact original E8 0xBAEE2 source**.
- `RankMarker_sprani` / `RankMarker_putClipSprite` then *again* forced NaviPub rank children down `ScreenHud` without consulting valid physical car depth. `R62 FIXEDFN KIND0 owner=SCREEN_HUD marker=0` proves the sprite pipeline never carried a depth payload.
- This is stronger evidence than changing world/hud shader projection because the latter is unreachable without a valid producer anchor. Similar DX11 mode-6 math already existed in R26.
- The separate rival `RivalMarker_sprani` had its own C2C `0xBB796` source, but the preceding original `Calc3D2D` return-site `0xBB6F5` can be hidden from an inline trampoline's `_ReturnAddress()`. R26 previously had no wrapper for the source E8 `0xBB6F0`; queue-time rival anchor could therefore remain invalid. This fix captures that exact call independently, not by reusing a preceding ordinal car's anchor.

## Material patch

- At the exact original ordinal E8 `0xBAEE2`, allow original Calc3D2D recovery even while a coarse NaviPub parent scope is active. Existing finite input, projected output, validity, and coordinate-space verification remain; no generic NaviPub/world promotion.
- In the two physical ordinal sprite families (sprani 1–3, clip 4–6), classify as `ProjectedWorldMarker2D` **only when the exact per-car recovered payload is valid**. Otherwise retain `ScreenHud` for NaviPub siblings and safe `WorldBillboard` fallback for other non-HUD sources. The original `DispRankFirst`/result/6th HUD remains separately `ScreenHud`.
- The rival original E8 `0xBB6F0` uses the same original Calc3D2D ABI and dedicated `RivalMarkerExactCalcEdge` TLS guard. Capture its projected payload before `0xBB796`; consume exactly once in the existing rival sprani wrapper. No fabricated anchor and no cross-car sharing.
- Add bounded `VR RIVAL EXACT CALC EDGE` and `VR RIVAL PHYSICAL PRODUCER` trace points to distinguish source-capture failure from renderer fallback. Existing rank probes should now log `projectionValid=1` and `anchorValid=1` for valid car points.
- Preserve DX11 R57 mode6 relative IPD and FOV reference, HUD scale 0.55, menus landscape 3440x1440, F11 screen-space, optics/sky, and game native 640×480 layout. No R84 activation.

## Safety/acceptance

- The canonical `VR_BINARY_CONTRACT.json` accurately records four NaviPub parent calls and their *normal* ScreenHud role; it does not veto the exact original child E8 on a provably spatial negative-Z vehicle anchor. Ambiguous or nonfinite child inputs remain HUD.
- If the projected anchor is invalid, no world-depth retarget is permitted; original drawing is preserved.
- Windows policy/compile/package CI is required on exact patch SHA. Such results test contracts and compilation, not headset appearance.
- **RUNTIME_VALIDATION=UNTESTED** for changes until physical Quest3 test. In next session verify 1st/2nd/3rd separately, 4th/5th/6th separately, and rival at near/mid/far distances. Compare to DX11 reference and look for binocular convergence and correct depth during head yaw. Attach fresh log ZIP. No retroactive PASS claims.
