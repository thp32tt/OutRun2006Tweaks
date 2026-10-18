# DX9Ex R84 개발 활용 문서 — 원본 게임 렌더 함수 전수 인덱스 기반

**대상**: 사용자 보유 OR2006C2C.exe SHA256 `68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3`, GitHub `thp32tt/OutRun2006Tweaks` 브랜치 `vr-d3d9ex-focus`.

**범위**: N100에서 Ghidra 기계어 함수 7,238개·404,925 명령어·71,667 흐름 참조를 새로 확인했고, 디컴파일 C 7,237개 및 **1,810개 렌더 연관 후보**를 주소별 문서 38권으로 구성함. REA 직접 검증은 `REA_RENDER_BATCH_STATUS.json`의 성공 레코드만 인정한다. 게임 R84 C++ 수정·CI/실기 증명은 이번 분석의 일부가 아니다.

## 1. 개발 중 우선 적용할 원본-모드 대응 지도

| 작업군 | 원본 확인 근거/함수(가상주소 VA) | 현재 R84 검토 지점 | 첫 번째 재현/진단 | 추정이 아닌 합격 조건 |
|---|---|---|---|---|
| P0 +TIME | `0x00498670` → B4 sprite `0x00429530` → `0x0042D0C0`; 시간 `0x004973C0` → `0x0042CFE0`; 소비 `0x0042D710` | `src/hooks_textures.cpp`, `src/vr/game/render_semantics.hpp`, `stereo_renderer_r30.cpp`, `stereo_renderer_r33.cpp` | 단일 프레임에서 SpriteNode type=1 vs glyph type=0, 동일 frameEpoch 다른 sourceSerial·BatchID 비교 | B4·시간 숫자 각각 좌/우 GPU Draw/RT, pose/c64 복원 및 HMD 중복/누락 없음 |
| P0 6th/6 고정 HUD | `0x004B9D80`, `0x00429530`·`0x0042D280` | R30 ScreenHud, R33 Draw 및 HudInspector, `src/vr/game/hud_native_source_transaction.hpp` | 숫자 glyph와 rank sprite가 서로 다른 호출자/queueEpoch인지 | 6th/6 전체 숫자·라벨 양안 표시·선명도, 월드 순위와 분리 |
| P0 차량 위 순위 | `0x004BAD20` → 원본 Calc3D2D `0x00449940` | R30 projected rank FVF `0x142` 경로와 R33 | 원본 월드 위치/투영행렬, 눈별 XYZ+WVP·poseEpoch 기록 | 좌/우 마커가 차량 위치에 함께 고정되고 헤드락 없음 |
| P0 렌즈 중심 | `0x0040CBC0` → `0x0040C980` 중심, `0x0040C9A0` 외곽 후보 | R30/R33 WorldBillboard/SceneEffect, LensCentre 소유 증명 | 중심 C993와 외곽 CABE 후보의 원본 함수·GPU Draw 구분 | 중심 이중 표시 소멸, 외곽·SkyGlow·월드 보존, 좌우 카메라 의존 |
| P0 하늘/SkyGlow | 원본 장면 렌더의 직접 D3D 호출/환경 그리기(정확 원본 owner 미확정) | R29-R33 SkyGlow pre-HUD / world paths | 원본/아이별 셰이더·카메라·렌더타깃·poseEpoch 확인 | 머리를 움직여도 하늘이 월드 고정, 노출·색상·깜박임 유지 |
| P0 ESC/옵션 화살표 | 원본 Sprite/queue type=0/1, 메뉴 state | R30 `pause_menu_eye_affine.hpp`, `render_semantics.hpp` | 메뉴 쉘·화살표 각각 UV/레이아웃/양안·입력영역 | 눈별 화면 위치 동일한 광학 패널에 정렬, 헤드락/2중/입력 오차 없음 |
| P0 F11 | **원본 EXE가 아닌** VR host ImGui overlay | `vrhost/src` UI/host compositor, 게임 DX9 별도 | ImGui DrawData 및 OpenXR layer/quad, hitbox·이벤트 로그 | 양안 모두 표시/선택·입력 일치, 게임 렌더 훅 중복 없이 단일 제출 |
| P0 메인 메뉴 | `SUMO_FE_CVT` Sprite DDS, 원본 Sprite/UV 생성자 | `src/hooks_textures.cpp`, R30 메뉴 scale/contain | DDS 슬롯+XXH32 해시, 교체 전후 원본 640×480 기준 좌표 | 갈색 네모·잘림·비율 왜곡·흰색·블렌딩 문제 없음 |
| P0 차량 선택 | `SELECTOR_CVT` DDS, original SPRARGS/SPRARGS2, 마스크 | `sprite_uv_transaction.hpp`, R30 2D + texture override | SPRARGS 원본 UV와 교체 이미지 실제 W/H, 같은 슬롯의 마스크 수명 | 차량/선택 화살표·반투명 프레임 정상 표시 |
| P1 GOAL/결과 | 원본 GOAL/Result glyph 출력, `0x004B9200`·`0x0042CFE0` 및 큐 | `goal_physical_source.hpp`, R30/R33 Goal | GOAL/타이머/결과 글자별 BatchID·sourceSerial 및 RT | 숫자 두 벌·리사이즈 실패·고정 위치 사라짐 |
| P1 파티클 | 직접 D3D DrawPrimitiveUP/Indexed GPU 함수(원본 emitter-Draw 대응 미확정) | R30/R33 world particle/alpha/blend/depth | 생성-업데이트-제거 수명과 드로우 index, texture/blend/depth/pose 기록 | 먼지/모래·반투명 파티클 눈별 부드럽게 일치 |
| P1 자동차 그림자 | original direct car-base shadow WVP | R30 `R30HasExactCarBaseShadowRawWvp`, R33 shadow | 원본 c64 write serial, draw serial, shader, left vs right depth/stencil | 시작 그림자 중복 제거, 좌우 접지 위치 동일 |
| P1 반사·유리·물 | 렌더 타깃·셰이더·텍스처 샘플/합성 API 근거만 확정 | R29/R30 world, source RT leases, device loss | 반사 render target과 본화면의 Draw 순서/좌우 참조/투명도 | 유리·반사 유지, 누락/이중 이미지·FPS 저하 없음 |
| P1 프레임·복원 | `0x00417B20` → `0x00449050` → `0x0042D710` | R33 Present/Reset + R30/R29 fallback, host | Begin/EndScene·reset·device lost·RT/viewport/stencil 복원 | CI x86 DLL/x64 host + Quest3 runtime, 잔상/오염 없음 |
| P1 월드 폴리곤 | original GPU direct Draw 20개 함수 및 indirect dispatcher 후보 | R33 four hooks, R30 FixedFn/xyzrhw, R29 world | FVF/VS/PS, Draw indexed counts, shader WVP, 원본→눈 RT | 지면·건물·차량·카메라 의도대로 출력, 배경 반투명 유지 |

**주의**: 이 표의 원본 함수 주소가 항목마다 모두 실증된 것은 아니다. 정확한 디컴파일 함수·COM API 호출이 확인된 경우와 원본 asset/분류만 확인한 경우가 다르다. 미확정인 행은 위와 같이 명시했고 `FUNCTION_PROFILE_INDEX.md`를 먼저 조회한다.

## 2. 핵심 원본 렌더링 함수 직접 검사 우선순위

| 함수 VA | 정적 확인 | R84 경계 |
|---|---|---|
| `0x00417B20` | Windows 원본 게임 루프/장치 실패/프레임 | BeginScene, Present, device-loss |
| `0x00449050` | 우선순위 렌더 루프/소비 호출 | 네이티브 Draw API 진입 |
| `0x004C50A0` | 특정 게임 상태일 때 별도 큐 소비 | 중복 소비 가설은 런타임 검증 필요 |
| `0x0042D710` | 타입별 소스 선택·알파/샘플러 상태·D3DX begin/end | SpriteNode 타입 0·1 및 queueEpoch |
| `0x0042DD50` | 직접 호출자는 `0x0042CFE0`·`0x0042D0C0` 두 개 | 노드 pointer 재사용·생성 세대 |
| `0x00429C60` | ID3DXSprite Begin | pending direct stage glyph batch |
| `0x0042A0A0` | ID3DXSprite Draw | 물리 GPU 제출 시점은 지연 가능 |
| `0x00429F60` | ID3DXSprite End | GPU Batch ID·원본 sourceSerial 복원 |
| `0x0042A3A0` | device DrawPrimitiveUP (원본 vtable index 83) | 원본 sprite quads 다중 눈 |
| `0x0042A800` | 알파/마스크/복합 원본 DrawPrimitiveUP 경로 여러 개 | 마스크·배경·흰 sprite·스테레오 상태 |
| `0x0042C0F0` | 일부 glyph 특수 직접 DrawPrimitiveUP | D3DX deferred vs direct path 분리 |
| `0x0042A2B0` | sampler/blend·render-state 조정 | 알파/필터/쉐이더별 복원 |
| `0x0040CBC0` / `0x0040C980` / `0x0040C9A0` | 렌즈 렌더 그룹, 중심·외곽 분리 | world pose vs projected screen |
| `0x00498670` | +TIME 원본 이벤트/상태 분기 | 6개 원본 E8 caller 별 계측 |
| `0x004979E0` | 단순 predicate가 아닌 progress UI producer | 다른 부모의 glyph와 batch 혼합 방지 |
| `0x004B9D80` / `0x004BAD20` | 고정 HUD rank와 차량 world rank 독립 | 2D 조정/3D 투영 구분 |

## 3. 원본 Call Site 기준 +TIME 재현 계약

- Game mode 1/9: animation ID `0x2C00B4`, original E8 CALL RVA `0x9898E`.
- 동일 이벤트 time string original E8 CALL RVA `0x989AD`, seven-digit original E8 CALL RVA `0x98A10`.
- 대체 branch animation ID `0x2C00B5` at `0x98A36`, text at `0x98A89`.
- 별도 branch `0x2C006C` at `0x98AC6`, 관련 시각 결과를 +TIME으로 확정 금지.
- Stage animation queue type=1 and glyph queue type=0. 실제 sprite 전체가 *하나의* GPU draw가 된다고 가정 금지.
- One frame, one runtime schema: `sourceSerial, producerCallRVA, animId, glyphRunId, spriteNodePtr, spriteNodeGeneration, queueEpoch, priority, D3DXBatchID, originalGpuDrawID, physicalR84DrawID, leftTarget, rightTarget, leftHr, rightHr, restoreHr, poseEpoch, rawWvpSerial, shaderEpoch, frameId, OpenXRSubmitID`.
- 만약 여러 glyph source가 하나의 GPU draw에 합쳐졌다면 *n:1* 소유자 목록/범위로 표시, 틀린 1:1 매핑 금지.

## 4. 디버깅 경로와 순서

1. 최신 GitHub 브랜치·활성 lease/기존 FEATURE·TASK_ID를 먼저 읽고, 다른 자동 작업의 소유 영역을 덮어쓰지 않는다.
2. `FUNCTION_CATALOG_NATIVE_MERGED.jsonl`에서 원본 VA 검색, caller/callee/COM virtual slot 검토. 간접 호출이면 `INDIRECT_RENDER_CALL_SITES.csv` 및 네이티브 XREF 우선.
3. `src/hooks_textures.cpp` 의 반환 주소/queue-tail proof, `RegisterSpriteNodeScope` 의 producer/serial 확인. 증명 불가하면 UNKNOWN; 알파/FVF/텍스처만으로 HUD 스코프 변경 금지.
4. `stereo_renderer_r30.cpp` R30 native XYZRHw/FixedFn 조기 종료, source transaction 전후, R33 `DrawPrimitiveDestR33`/`DrawIndexedPrimitiveDestR33`/UP 경로, 원본 보존·R29 fallback 순서 확인.
5. **진단은 먼저 실패/폴백 근거를 확보**해야 한다. 방어 장치를 무조건 해제하여 오른쪽 눈을 강제 렌더하는 방식은 허용하지 않는다.
6. 특정 화면 결함을 증명한 뒤 해당 실질 소스 수정 + 긍/부정 회귀 테스트 + exact-SHA Windows build/CI; Quest3 런타임 결과 별도 확인.
7. 원본 게임 EXE, 역컴파일 C, DDS 텍스처 전체를 GitHub 커밋하지 않는다.

## 5. 완료 판정

- 정적 함수 경로 확인: `STATIC_CONFIRMED` 가능.
- R84 C++ 기능 구현: material commit + affected tests 없으면 `NOT_IMPLEMENTED`.
- Windows x86 게임·x64 OpenXR host 빌드: exact SHA 필수 CI 성공 시 `BUILD_VERIFIED`.
- Quest 3 실기 같은 빌드 SHA를 검증하지 않았으면 `RUNTIME_VALIDATION=UNTESTED`.
- 일반 렌더 Draw 5초 카운터는 장애 추적에 도움되지만, 실제 좌/우 눈 전수 성공 또는 OpenXR visible PASS를 뜻하지 않는다.