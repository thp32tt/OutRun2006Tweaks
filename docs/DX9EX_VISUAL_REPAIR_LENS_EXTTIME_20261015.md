# DX9Ex 화면오류 수정 개발 지침 — 렌즈 중심광 / +TIME 우선
작성: 2026-10-15 KST. 사용자 요청: 화면오류 수정 방법을 개발 지침에 반영하고, 전체 소스 경로를 검토해서라도 렌즈 플레어와 추가시간까지 해결.
TASK_ID: DX9EX-VISUAL-REPAIR-GUIDANCE-20261015-013652
대상: thp32tt/OutRun2006Tweaks / vr-d3d9ex-focus
검토 기준 SHA: 837550addbd7ec26bee680c0f39f9abb5077dde9
상태: DEVELOPMENT_DIRECTIVE_PUBLISHED / SOURCE_FINDINGS_CONFIRMED / OPTICAL_ROOT_CAUSE_NOT_YET_PROVEN
RUNTIME_VALIDATION=UNTESTED. 이 문서는 렌즈/+TIME 수정 완료나 새 DLL 배포 증거가 아니다.

## 1. 실행 원칙
기존 FEATURE_ID DX9EX:VIS:LENS_FLARE_CENTRE, DX9EX:VIS:EXTENDED_TIME 및 동일 symptom_id를 재사용한다.
현재 살아 있는 TASK/lease를 유지하고 공유 소스의 쓰기 권한을 빼앗지 않는다.
사용자가 특별히 지목한 두 결함을 다음 가능한 P0-A 작업으로 우선한다. 진행 중인 정확 SHA 검증을 취소하거나 UI/프레임 안정성 수정을 덮어쓰지 않는다.
한 결함의 원본 생성자 → 즉시/지연 제출 → 실제 선택된 DLL의 렌더러 → 양안 출력 전체를 완결한다.
문서/카운터/문자열 검증만으로 DONE 또는 점수를 부여하지 않는다. HMD 실패가 반복되면 같은 증상으로 이어서 수정한다.
새 파이프라인을 통째로 교체하거나 모든 alpha draw/WorldBillboard/HUD의 분류를 바꾸는 방식은 금지한다.

## 2. 실제 배포되는 기본 렌더러 — 2026-10-15 R84 메인 전환 반영
**본 절이 검토 SHA의 옛 R26 기본 패키지 판단을 대체한다.** `vr-d3d9ex-focus`의 옵션 없는 CMake, `DX9Ex Active Validation` 및 `CURRENT_FOCUS` 게임 DLL은 모두 **R84 독립 R29~R33** 기본 경로다. 검증 SHA `2465fe644fd17e0422ad0ce041612b62c1d114d9`: Active #38671905763 / Domain #38671905693 / Full Source #38671905747 SUCCESS.
- `full-chain-compile` x86 DLL이 `backends/d3d9/dinput8.dll`로 배포된다. `game` x86 작업은 **`R26_SAFE` 명시적 롤백 슬롯**에만 들어간다. 동일 정확 SHA x64 OpenXR 호스트를 사용한다.
- 렌즈/+TIME 수정은 **`stereo_renderer_r29/r30/r31/r32/r33.cpp`와 공유 game/host** 소스에서 실제 작동하는지 확인한다. `stereo_renderer_r30_r26_safe.cpp` 전용 변경은 R84 메인 개선이 아니다.
- `BUILD_INPUTS.json`, `MAINLINE_BUILD_MODE.txt`, `SOURCE_SHA.txt`, 실행 세션 변형, DLL/호스트 SHA256과 shader/XYZRHW/원본 producer를 확인한다. HMD 정상과 CI 빌드 통과를 구분한다.
- R26 전용 C993 원본 WVP/중앙 렌즈/+TIME 보호는 이식 참고다. 자동 복사나 모든 alpha draw의 광범위 분류 변경 대신 R84에서 원본 생성자→제출→렌더러→양안 경계를 직접 증명한다.
- 이전 `CONVERSION-DX9EX-00851`은 별도 작업이며 이 검토로 렌즈/+TIME 해결을 주장하지 않는다.

## 3. 렌즈 플레어 중심점: 원본 호출 재설치가 아닌 행렬 소유 경계 수정
### 확인된 소스
- 원본 EXE SHA256: 68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3.
- hooks_graphics.cpp::VRLensFlareProjected2D:
  중심 0xD3A5→0xC980→0xC993, objectId=0x570002.
  바깥 원 0xD5F5..0xD796→0xC9A0→0xCABE는 별도 경로.
- D3A5/D3AA enter/leave와 C993 DrawObjectAlphaCentre, 정확 WorldBillboard, pending token 격리는 이미 구현되어 있다.
  그러므로 같은 훅을 다시 추가하거나 '중심만 WorldBillboard로 변경'을 새 해결책으로 보고하지 않는다.
- R26+HUD R30BuildScreenSpaceEyeConstants에서 R44GetOwnedRawOverlayWvp는 원본 c64와 shader epoch 및 draw age<=12를 요구한다.
  이 조건 실패 후 WorldBillboard는 SceneEffect/HUD의 확장 원본-WVP 경로에 해당하지 않으면 live GetVertexShaderConstantF로 내려간다.
- 이후 WorldBillboard는 stockWvp*inverseBaseProjection에서 WorldView를 재구성하고 headInverse와 eyeInverse를 적용한다.
  따라서 live c64가 이미 head 보정되었는지 증명하지 않고 이 분기로 진입하면 중복 보정 위험이 있다.
  실제 실패 프레임이 이 경로를 탔는지는 아직 미확인이다. '확정 실기 원인'으로 승격하지 않는다.
- 일반 R30의 비큐 WorldBillboard→하위 world owner 경로는 R26+HUD의 위 재구성 경로와 같지 않다.

### 구현 요구
1. 중심광의 정확한 producer/호출 수명에만 적용되는 식별자를 유지한다. 바깥 원, rival, smoke, SkyGlow에 권한을 넓히지 않는다.
2. c64 write의 원본 값·shader epoch·Present epoch·producer·pose를 하나의 수명으로 연결한다.
   중심광 전용 분기는 원본임이 입증되지 않은 live c64를 'stock'으로 재사용하지 않도록 고친다.
   단순 draw age 12→128/무한 확대는 해결이 아니다. 같은 shader라도 다른 오브젝트의 행렬이면 배제한다.
3. C993 진입 전에 WVP가 쓰였는지, 진입 후 쓰였는지 구분한다. producer를 늦게 붙이고 이미 보정된 c64를 raw로 간주하지 않는다.
4. 실제 원본이 spatial WorldView인지 투영 완료 geometry인지 확인한다.
   전자는 raw WV→headInverse→eyeInverse→eyeProjection을 정확히 한 번, 후자는 원본 투영/깊이 증거에 근거한 별도 복원 경로를 구현한다.
   원본 형식을 확인하지 않은 채 중심광을 HUD 평면에 고정하거나 깊이를 0으로 만들지 않는다.
5. 원본 증거가 없을 때 기존 안전 fallback을 유지하고 해당 후보를 미완료로 기록한다. 효과 삭제/alpha=0은 수정이 아니다.
6. 중첩 호출·VR toggle·부분 훅 실패에서도 원본 draw 1회 및 scope 복구를 보장한다.

검증: shader 교체, c64 age 12/13/128, 같은 shader의 다른 object write, Present/Reset, 누락 pose, depth-off alpha를 포함한다.
양안 중앙광 1개/장면 고정과 바깥 3~4개 원·SkyGlow 동일성은 나중에 같은 DLL HMD로 확인한다.

## 4. +TIME: 스프라이트와 숫자, 지연 GPU 배치까지 한 기능
### 확인된 소스
원본 6개 E8:
- sprite 0x9898E/0x98A36/0x98AC6→0x29530
- numeric 0x989AD/0x98A89→0x973C0, 0x98A10→0x974E0
StageExtensionEnter/Leave는 직접 호출 scope와 추가된 모든 SpriteNode를 StageExtensionTime/ScreenHud로 처리한다.
SumoUISpriteReplay::capture/replay는 scope/producer/marker를 보존한다. 이 기존 구현을 누락된 것으로 다시 보고하지 않는다.
CurrentRenderProducerToken은 직접 호출과 queue producer를 구분한다. queue 실행 중에는 실제 queue node가 우선이다.
R64 ID3DXSprite::Draw 후 Flush는 정확 rank/DispRank 전용이며 +TIME은 제외한다.
Microsoft ID3DXSprite 계약상 Draw는 배치 등록이고 실제 GPU 제출은 Flush/End에서 일어날 수 있다.
따라서 원본 parent RAII 안에 D3DXSprite::Draw가 있었다는 것만으로 GPU DrawIndexedPrimitive가 같은 scope에서 실행됐다고 증명할 수 없다.

### 재현된 한계와 미확인 부분
첨부 counterexample은 실제 render_semantics.hpp로 다음을 재현한다:
StageExtensionTime/ScreenHud scope 안에서 등록 → scope 종료 → 지연 ConsumeForDraw 시 None.
이는 직접 scope만으로 지연 GPU 제출을 소유할 수 없다는 계약 반례다.
실제 게임 +TIME이 그 D3DX batch를 사용하는지, End/Flush가 이미 안전한 queue 경계 안에서 호출되는지는 별도 확인이 필요하다.
이 반례를 실게임 재현 또는 GPU/HMD 테스트 PASS로 표현하지 않는다.

### 구현 요구
1. 6개 원본 caller 각각을 sprite와 숫자로 구분하여 immediate GPU draw인지 queued SpriteNode인지 D3DX delayed batch인지 분류한다.
2. queue select/leave 및 D3DX Draw/Flush/End의 순서를 같은 batch/device/frame 식별자로 연결한다.
   kind0 FVF0x142 / kind1 XYZRHW(FVF 또는 POSITIONT declaration) / VS c64의 세 경로를 모두 포함한다.
3. 지연 batch 손실이 확인되면 batch가 실제 GPU에 제출되는 동안 원래 producer/scope를 복원하거나 정확한 batch 경계에서 분리한다.
   단순 +TIME Draw 뒤 Flush 하나만 추가하면 이전 unrelated sprites도 +TIME 소유권으로 제출할 수 있으므로 금지한다.
   이전 batch는 이전 owner로 먼저 제출, +TIME batch는 +TIME owner로 제출, 이후 owner는 복구하는 순서를 입증한다.
   Begin/End 실패, nested/reentrant, 원본 HRESULT, device Reset, texture 정렬/alpha order를 보존한다.
   전역 매 Draw Flush나 game timer tick 수정은 금지한다.
4. queue tag가 실제 GPU sink까지 살아 있다면 batch 가설을 기각하고 raw c64 provenance, 잘못된 FVF/declaration admission, pose epoch, 좌우 draw HRESULT/restore를 조사한다.
5. shader/XYZRHW/fixedfn 각각이 같은 HUD 좌표 의미를 갖도록 수치 비교한다. 숫자만 단일이고 '+TIME' sprite가 이중인 경우도 실패다.
6. GOAL 0–99 진행과 완성 결과, 일반 타이머, 6th/6, rival, pause/F11을 보존한다. 원래 두 GOAL helper를 삭제하지 않는다.

최소 재현 행렬: live tick/no-tick, sprite+숫자 혼합/서로 다른 texture, 이전·다음 다른 owner batch, 6개 source, VS on/off, FVF0x142/XYZRHW/declaration, Reset/recenter.
최종 HMD: stage 통과 때 sprite와 숫자 모두 단일·비 headlock, 시간 로직/애니메이션/최종 결과 그대로.

## 5. 나머지 화면오류의 개발 요구
- 메뉴: 실제 작성된 전체 영역과 물리적 VR 표시 크기를 분리. INI 1/1만으로 가운데 4:3이 전부라고 추정하지 않는다.
  crop ON/OFF 양쪽 사용자 실패를 negative case로 보존. 차량 선택 우측 모델/목록과 이동 UI를 자르지 않는다.
- HUD: 글자 크기와 anchor를 분리하고 exact speed/time/rank/gear/REV producer 전체를 다룬다. PR #120의 존재만으로 병합/배포 완료라 하지 않는다.
- F11: 고해상도 atlas 구현은 이미 있음. 최종 plane/viewport/시야 위치·입력 hitbox를 확인하고 중복 축소를 제거한다.
- 차량 순위: Calc3D2D의 차량별 깊이/anchor를 queue+replay+양안까지 유지. 집계 projected counter는 차량 부착 증거가 아니다.
- 건물 깜빡임: 원본 CPU submission/visibility, shader world WVP, R33/R30/R29/보수 fallback 및 depth를 분리한다.
  DisableStageCulling=true였어도 관측 실패했고, 당시 CullingUnionFov는 내부 비활성 로그였다.
  DrawDistanceIncrease=0 && DrawDistanceBehind=0에서 validate=false는 의도된 동작이다.
  검토 중 2ed14c08 및 후속 수정이 들어왔으므로 재작업 전에 최신 소스/선택된 빌드 경로와 비교한다.

## 6. 완료 조건
- 실제 수정은 기존 feature/TASK_ID로 C++ + 필요한 회귀검증을 한 묶음으로 개발한다.
- 위의 가설 중 적어도 하나를 실소스/호출 순서 증거로 채택하고 다른 원인을 배제한다.
- 실제 배포 DLL에 수정 함수가 들어감, Windows x86 game+x64 host+package / Domain / 해당 Full Source Impact+EXE Inspector 통과.
- 테스트 코드가 수정 전 실패/후 성공하며 원본 source 의미 보존과 부정 조건을 검사. 문자열만 존재하는 테스트는 동작 증거의 대체가 아니다.
- 실제 기본 R84 독립 R29~R33 Active DLL 검증과 R26_SAFE 롤백 빌드를 별도로 확인한다. 최종 SHA CI 통합 검증 후 Quest3 실기 광학 결과를 기다린다.
- 새로운 HMD 광학 확인 전 상태는 BUILD_VERIFIED + NEED_HMD_TEST. 이번 문서 반영에는 실게임 해결/성능 점수 없음.
- GitHub 지침 변경은 Docker/Portainer가 실제 로드했다는 증거가 아니다. 재시작/배포 여부는 별도 실측.

## 7. 검토 범위 / 출처
Git tree 전체 1112항목을 목록화하고 DX9Ex 및 원본 훅 관련 56개 소스 파일을 확보·검색했다.
핵심 경로 상세 검토: hooks_graphics/uiscaling/framerate, render_semantics, outrun_renderer, R26/R29/R30/R30_R26_SAFE, host main_r23, CMake와 Active workflow.
전체 저장소 모든 행을 읽었다는 주장이 아니다. unrelated DX11/DXVK/FFB/한글화 소스 변경 없음.
소스 경로와 blob SHA: docs/automation/reviews/DX9EX_VISUAL_SOURCE_INVENTORY_20261015.json 참조.
최근 실기 근거: Issue #119의 2026-10-14 23:38 / 2026-10-15 00:12 KST 기록, tested SHA 1d161a18efcfe4ddf3cad318ea6be50102458ac3.
- https://github.com/thp32tt/OutRun2006Tweaks/issues/119
- https://learn.microsoft.com/en-us/windows/win32/direct3d9/id3dxsprite
- https://learn.microsoft.com/en-us/windows/win32/direct3d9/id3dxsprite--draw
- https://learn.microsoft.com/en-us/windows/win32/direct3d9/id3dxsprite--flush
Microsoft 문서는 현재 열람한 API 계약의 근거이며, 2026년 신규 패치/최근 해결 사례라는 뜻이 아니다.
