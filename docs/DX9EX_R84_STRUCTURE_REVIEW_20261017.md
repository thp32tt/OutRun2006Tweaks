# DX9Ex R84 전체 경로 감사 및 Screen/WVP 교차 경로 수정 (2026-10-17)

**근거**: GitHub `vr-d3d9ex-focus` 커밋 `9fc04dc83a69d0647af05dba5665361e52de6ec0`의 소스와 사용자가 보고한 R26/R84 Quest 3 화면 비교. 아래의 원인 설명 중 런타임 경로 진입 빈도는 아직 새 HMD 계측으로 확인되지 않았음.

## 추적한 경로 (순서)

1. 원본 게임의 `SpriteNode`/메뉴/월드/파티클은 `src/vr/game/render_semantics.hpp`가 생성자·queue node 단위로 scope/producer를 부여. `ScreenOverlay2D`는 미확정 queue 기본값이며 **월드 인증이 아님**.
2. `src/vr/game/outrun_renderer.cpp`가 게임 원본 c64 WVP, 카메라 projection, head inverse, shader/pose epoch를 추적.
3. D3D9 물리 Draw hook은 `src/vr/d3d9/stereo_renderer_r33.cpp`의 XYZRHW 조기 경로와 `R33Dispatch`로 들어감.
4. `R32` 안정성·StateBlock/RT 판단, `R30ClassifyScreenSpacePass`가 screen/marker/lens/effect를 재분류.
5. screen 증거가 있을 때 `R30`은 exact ScreenHud 및 +TIME/GOAL을 원본 c64·pose 검증 뒤 finite HUD plane으로 재투영; XYZRHW queue overlay는 소유권/헤드 포즈 조건을 통과해야 같은 유한 평면 처리.
6. world 경로는 `R31BuildFastWorldConstants`에서 셰이더 세대·원본 WVP·같은 포즈 및 projection generation을 검증. 부적합/fragile하면 `R29`의 R28 기준 fallback을 거침.
7. `R29`는 verified shader rebind와 원본 행렬 복원, 우안 depth/RT/state 보존이 핵심. `ScreenHud` 등은 자체 rebind에서 제외되나 **상위 R33의 R31 분기까지 보호하지는 못했음**.
8. R30/R29의 left/right eye D3D9 렌더 타깃은 present frame으로 게시되고 x64 OpenXR 호스트가 공유 GPU 리소스와 동일 pose/FOV를 사용.
9. 메뉴는 게임 월드와 분리되어 `vrhost/src/main_r23.cpp`의 Desktop Duplication UV→client aspect→양안 공통 tangent FOV→LOCAL fixed quad로 합성. 기본 `opticalCoverage=0.78`은 이전 Quest3 실기에서 full-FOV가 과대하게 보인 회피값이므로 이번 수정에서 **유지**.

## 이번에 확인한 코드상의 결함 및 수정

`R30ClassifyScreenSpacePass`가 perspective `ScreenOverlay2D`를 `None`으로 반환하거나 `SkyGlow`를 screen으로 인정하지 못한 경우, `R33Dispatch`는 `R33TryFastWorld`에 도달했음. R31은 shader/pose/WVP 일치만 확인하고 **원본 scope가 screen인지 검사하지 않아** 이전 월드 WVP를 사용하게 될 수 있음. 또한 `R33TryHud` 실패 뒤 하위 R29 진입 역시 화면 ownership과 충돌 가능.

새 `PhysicalDrawCommand::DeniesGenericWorldFallback()`은 5개 nonworld scope를 명시적 제외. R33의 (1) resync 실패 (2) screen classification=None fast-world 이전 (3) 화면 스테레오 실패 후 lower R29 이전 세 갈래에서 *한 번의 원본 Draw*로 복귀. 정상/검증된 R30 screen stereo, R31 true world, R26_SAFE 코드는 변경하지 않음. 한 번의 원본 Draw가 양안 HUD 정상화를 보장하는 것은 아니며, 화면이 일그러지는 잘못된 **월드 행렬 상속을 차단**하는 fail-closed 정책.

## 남은 런타임 검증과 수정 후보

- **P0 HUD**: `6th/6`의 문자/배경/아이콘 별 producer·physical GPU Draw 대응, `R30GetRecentOriginalHudWvp` 미인증 횟수, queue 전달 누락. 원본 매칭이 실패하면 현재 한 눈 원본 fallback일 수 있으므로 양안 비대칭 확인 필요.
- **P0 하늘**: 실제 sky mesh는 월드인지, `SkyGlow` 후처리/렌즈플레어가 두 눈에 다른 캡처 시점인지 분리. 머리 회전/recener 시 같은 pose sequence와 per-eye RT 확인.
- **P1 메뉴**: Virtual Desktop Low/High를 바꾼 동일 게임 클라이언트에서 `clientAspect`, `sourceWidth/Height`, clip UV, `PlanCapturedAspect`, `opticalCoverage=0.78`로 계산한 두 눈 배치를 A/B. 4:3 또는 3:5 하드코딩 금지.
- **P1 복원**: R29/R30/R33 각 실패에서 원본 c64, viewport, RT, depth/stencil, StateBlock을 비교하고 Present 거부·reset telemetry 검사.
- **P2 성능**: 월드·HUD·하늘이 정확해진 뒤 반투명, 모래, 물, particle GPU 측정 재개.

## 검증/출시 정책

새 정확 SHA에서 DX9Ex Active (x86 R84/R26_SAFE + x64 host + ZIP/launcher), Domain Guard, HUD Inspector, Full Source CI를 구분해 확인. 같은 소스 HEAD의 실제 Quest 3 실기는 `RUNTIME_VALIDATION=UNTESTED`로 별도 표기. 코드 CI 성공만으로 HUD 정합성이나 sky 정상화로 판정하지 않음.
