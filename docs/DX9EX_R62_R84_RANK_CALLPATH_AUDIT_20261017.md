# R62 차량 순위 마커 최초 실기 개선과 R84 회귀 전수 대조 (2026-10-17)

**정정:** R26_SAFE는 차량 위 마커가 차량에 고정되어 있던 정상 기준이 아니다. 2026-09-19 18b41369은 WORLD_RANK 후보 구현 이후 실기에서 HMD 머리추종이 재현됐다. R51 17ad376b도 vehicle marker head-follow. 2026-09-26/27 R62 build 945e4471은 사용자 실기에서 4th/5th 마커가 한 개로 보이고 차량을 따라간다는 부분 성공이 명시된 비교 기준이다. 그러나 6th/6 화면 HUD는 당시에도 실패했으며 1st~5th 전체 성공으로 과장하지 않는다.

## Source call-path comparison
- 원본 Calc3D2D 차량 3D 앵커: 1~3 sprani와 4+ put_clip_sprite는 ScreenHud DispRank(6th/6)와 다르다.
- R62 source producer->queue projected marker->DrawIndexedPrimitive TRIANGLELIST, no vertex shader, FVF 0x142 (XYZ+DIFFUSE+TEX1)->R62TryFixedFunctionSpriteIndexed->per-eye corrected D3DTS_PROJECTION->original PROJECTION restore.
- R84 before repair: R33 DrawIndexedPrimitive->R32ReviewTryXyzrhwIndexedPrimitiveVB (POSITIONT/XYZRHW gate, not FVF 0x142)->R33 screen/world fallback. R84 source had NO R62TryFixedFunctionSpriteIndexed equivalent, even while R26_SAFE file retained it.
- New restricted path: R33 indexed dispatcher->R30SupportTryFixedFunctionProjectedRankIndexed->semantic exact ProjectedWorldMarker2D, live valid Calc3D2D anchor, TRIANGLELIST, VS null, exact FVF0x142, backbuffer, latched pose->projectedRank for BOTH eyes->R30ExecuteXyzrhwStereo->restore original D3DTS_PROJECTION. Never promote generic HUD, F11, world, particle, aux RT or other FVFs. One original draw remains on lack of proof.
- 1000 deterministic native exact FVF/owner/pose-equivalent admission cases (100 admitted, 900 rejected). Source-only contract does not replace HMD.

## Follow-up acceptance
Quest3 RUNTIME_VALIDATION=UNTESTED. Compare same game location for 4th/5th; require car tracking during head yaw and both eyes. Check 1~3 separately (sprani shader path), 6th/6 separately (ScreenHud). Recheck R26_SAFE only as boot/rollback, not as rank geometry reference.
