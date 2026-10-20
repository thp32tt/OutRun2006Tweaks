# OutRun 2006 R26+HUD 소스 교차검토 — 결과 HUD·차량 위 순위·렌즈플레어

검토일: 2026-10-20 KST. 요청 시각: 16:35:27 KST.

- 저장소/브랜치: `thp32tt/OutRun2006Tweaks` / `vr-d3d9ex-focus`
- 검토 SHA 및 조회 당시 HEAD: `aab9e02bcb2ad2e6253840e6267e5c5ad5040854`
- 비교 기준: `0cff83cf509c2acd6f3391b3a46c4dec1403a0d9`, `PC-FAST-20261020-012805-0cff83cf509c`
- 기존 작업 연결: `CHAT-DX9EX-R26-RESULT-HUD-20261020`, attempt 1, 독립 검토 기록. 기존 구현 작업/lease를 대체하지 않음.
- 상태: 정적 검토 수행, 기존 소스 계약·portable smoke PASS. Windows exact-SHA CI는 이번 조회에서 run 목록이 비어 확인하지 못함. `RUNTIME_VALIDATION=UNTESTED`.
- 이번 변경: 검토 보고서만 작성. 렌더러·설정·hook·배포 패키지를 변경하지 않음. 기능 완료 점수 +0.

## 1. CRITICAL — 확정된 치명적 결함

이번에 읽은 소스만으로 **이번 HUD 커밋이 필연적으로 이중 head rotation 또는 세 번째 mono draw를 만든다는 CRITICAL 결함은 확인하지 못했다.** 그렇다고 전체 화면 PASS를 뜻하지 않는다. 다음 HIGH 항목은 실제 증상이 남을 수 있는 명확한 검증 공백/조건부 결함이다.

특히 비교 범위를 구분해야 한다. `aab9e02` 단독 변경은 R26 result HUD에 좁혀져 있으나, 사용자 기준 `0cff83cf → aab9e02`에는 **44개 커밋, 45개 변경 파일**이 있다. 전체 구간을 “HUD 외 경로 불변”으로 취급할 수 없다.

## 2. HIGH — 화면 문제를 남길 수 있는 경로

### H1. 결과 HUD의 모든 GPU 표현에 eye-cant 수정이 적용된 것은 아니다

정적 사실:

- `stereo_renderer_r30_r26_safe.cpp:3192–3224`의 XYZRHW/고정기능 구성은 exact result에 `BuildStageEyePoses()`를 사용한다.
- 같은 파일 `R30BuildScreenSpaceEyeConstants():4739–4765`의 **셰이더 HUD 경로는 여전히 `identityOrientation`**을 쓴다. exact result의 별도 분기가 없다.
- `R30PrepareXyzrhwState():2432–2435`는 **cached VS != 0이면 live VS 조회 전에 거절**한다. 이번 live VS 우선 수정은 `R62TryFixedFunctionSpriteIndexed():5033`에만 적용된다.

따라서 정확한 결과 producer가 셰이더 경로로 나오면 R62와 eye pose가 다르고, XYZRHW로 나오면서 cache/live VS가 불일치하면 수정된 pose 구성까지 도달하지 못한다. 이 조건부 코드 차이는 확정이다. 실제 +TIME 문자/숫자가 그 조건을 밟았다는 런타임 증거는 이번 입력에 없다. ResultProgress의 DIP/FVF142 한 샘플로 전체를 정상 판정하면 안 된다.

수정 방향: 먼저 API별 producer fingerprint를 확보한다. 해당 경로가 확인되면 exact result에 한해 셰이더 HUD도 동일 head-local eye pose를 쓰게 하고, XYZRHW의 live-VS 판정을 R62와 일관되게 만든다. 일반 HUD 전체 확대는 금지한다.

### H2. 중앙 렌즈플레어는 기본적으로 숨겨져 있다 — 광학 수정과 구분해야 한다

`src/vr/settings.cpp:115`는 `VRLensFlareCentreEnabled`의 기본값을 **false**로 선언한다. `src/hooks_graphics.cpp::DrawObjectAlphaCentre():677–683`는 정확한 VR 중앙 광원 scope에서 이 설정이 꺼져 있으면 `Game::DrawObjectAlpha_Internal()` 전에 반환한다.

이는 원본 `D3A5 → C980 → C993`, object `0x570002`를 제한적으로 생략하는 동작이다. 주변 `CABE` 원반 및 SkyGlow를 한꺼번에 없애는 코드는 아니다. 사용자의 INI가 설정을 덮어쓸 수 있으므로 실제 현재 실행값은 미확인이다.

결론: 중앙점이 사라져 겹침이 안 보이는 것은 **중앙 렌즈의 양안 수정 성공 증거가 아니다.** 기존 기준 SHA의 settings 소스에는 이 설정이 없었다. 기준 이후 렌즈 동작도 변경된 것이다. 이번 검토에서 설정을 임의로 켜거나 끄지 않았다.

활성화 시의 경로:

1. 원본 parent/object/queue 조건으로 중앙 광원만 `WorldBillboard + LensFlareCentre` 소유권 획득.
2. `R30GetExactLensCentreRawWvp():1970`가 call epoch, pose epoch, shader/epoch, 원본 c64 provenance를 검사.
3. 셰이더 world billboard는 `stockWvp * inverseBaseProjection * HeadInverse * EyeInverse * EyeProjection`을 구성(`:4628–4682`). 이곳은 원래부터 실제 head-local eye orientation을 쓴다.
4. 중앙은 full head-local position, 결과 HUD/rank는 두 eye 중심을 뺀 relative IPD를 쓴다. 공간 광원과 가상 HUD의 서로 다른 기준을 무조건 통일해서는 안 된다.

추가 위험: shared `PhysicalDrawCommand::CanUseGenericXyzrhwStereo()`에는 중앙 광원 배제 규칙이 있지만, 검토한 R26 safe 파일의 `R30PrepareXyzrhwState()`는 이 helper를 호출하지 않는다. 만약 중앙이 shaderless XYZRHW로 나타나면 shader/raw-c64 중앙 전용 증명을 거치지 않는 경로가 가능하다. **실제 중앙 draw가 XYZRHW라는 사실은 미확인**이다. 중앙 활성화 진단에서 API/FVF/VS를 먼저 확인해야 한다.

### H3. 차량 위 순위는 이미 별도 변경되었으며 result HUD 검증으로 대체할 수 없다

원본 owner를 분리한다.

| 화면 요소 | 원본/소유권 | 검토 SHA의 처리 |
|---|---|---|
| 고정 `6th/6`, POSITION HUD | `0x004B9D80`, ScreenHud | 차량 좌표 anchor와 별개 |
| 차량 위 ordinal 순위 | `0x004BAD20`, `0xBAEE2 → Calc3D2D`, return `0xBAEE7` | `ProjectedWorldMarker2D`, `exactOrdinalEyeCant` 사용 |
| rival marker | return `0xBB6F5` | 기존 anchor 복원, identity-eye 분기 유지 |

`hooks_uiscaling.cpp:896–1013`은 Calc3D2D 호출 전 입력을 저장하고, 원본 출력에 재투영되는지 검증한 뒤 차량 view-space point를 복원한다. `RankMarker_sprani():1916`와 clip wrapper는 anchor를 원본 호출 전에 복사하고 appended node에 전달한다. `hooks_textures.cpp:1029–1110`도 기준 이후 projected marker/token을 보존하도록 변경되었다.

`R57BuildProjectedMarkerDelta():1565–1660`는 검증된 anchor에만 head/eye 투영을 적용한다. ordinal은 실제 cant, rival은 이전 identity-eye 수식을 유지한다. R62/FVF142는 원래 D3DX projection 뒤에 anchor 중심 clip shift/scale을 붙인다. XYZRHW와 VS 경로도 동일 delta helper를 사용한다.

중요한 남은 제한:

- R62의 cached-VS 예외는 `exactResult` 전용이다. 차량 rank는 exact result가 아니므로 stale cached VS가 있으면 여전히 선행 거절된다. 발생 사실은 미확인이다.
- rank는 R64에서 queued D3DX Draw 뒤 Flush로 분리하지만, direct rank deferred batch를 result owner처럼 일반 복원하는 정책은 없다. direct와 queued를 로그에서 분리해야 한다.
- anchor가 없으면 `WorldBillboard` fallback으로 내려간다. parent 호출 수만 증가했다고 차량 부착 성공으로 볼 수 없다.
- `exactOrdinalEyeCant`가 false인 rival의 **수식**은 유지된다. 하지만 generic native sprite tagging이 rank와 rival 모두 바뀌었으므로 전체 기준 구간의 rival 동작이 bit-for-bit 같다는 주장은 할 수 없다.

### H4. 통합 non-zero cant 및 producer별 실기 증거가 부족하다

기존 `stage_extension_eye_plane_smoke.cpp`는 cant를 가진 quaternion helper와 임의 clip matrix의 pixel 변환을 검사한다. 그러나 실제 R30의 head/eye matrix 생성, 비영 head yaw/pitch/roll, 비대칭 FOV, 원본 D3DX projection, R62 clipMap, 좌우 제출을 함께 실행하는 통합 테스트는 아니다.

`ReadHmdlessDebugPose():688–730`은 yaw/pitch, 64 mm IPD, 비대칭 FOV를 설정하지만 eye orientation을 변경하지 않는다. 기본 identity eye로는 cant 누락을 검출할 수 없다. 단순 기존 smoke PASS를 통합 cant PASS로 표시하지 않는다.

## 3. MEDIUM — 상태 복원·소유권·좌표계 위험

### M1. E_FAIL 반환은 실패 통지이며 GPU 상태 복원 자체가 아니다

R62 성공 경로는 projection 변경 후 left draw → right RT/depth/viewport → right draw → 기존 RT/depth/viewport 복원 → 마지막에 원래 projection 복원이다. `RestoreRightPassState()`는 `stereo_renderer_r7.inc:1462`에 있으며 RT, depth, viewport 순서로 복원한다. R62는 world/view를 직접 변경하지 않는다. scissor/stateblock을 이 함수가 별도 저장·복원하는 것도 아니다.

left 실패 시 right를 시도하지 않지만 R62 호출자는 이후 projection 복원을 수행한다. right 또는 right-state 실패 시 helper는 frame을 poison하고 fallback을 arm하지만 **left HRESULT를 반환**한다. 따라서 함수 S_OK만으로 양안 성공을 판단하면 안 된다.

projection 복원 실패 시 `NoteRestoreFailure()`도 frame을 poison한다. 새 `exactResult && !restored && SUCCEEDED(hr) ? E_FAIL : hr`는 실패 은폐를 줄이지만, 실패한 SetTransform을 성공으로 바꾸거나 다음 batch의 오염을 제거하지 않는다. D3DX End는 정상 동작에서 Flush 및 Begin 이전 상태 복원을 수행하지만, 내부 D3D draw가 실패했을 때 사용하는 D3DX DLL의 정확한 cleanup/재시도 분기는 문서만으로 증명할 수 없다.

권고: 강제 실패 fixture로 left projection, right RT/depth/viewport, right draw, final projection restore를 각각 실패시키고, 반환값·frameIncomplete·실제 state getter·추가 mono 호출 수·다음 batch를 확인한다. E_FAIL을 제거하거나 무조건 native replay하는 식의 수정은 금지한다.

### M2. telemetry의 두 HRESULT가 두 번의 Draw 성공만을 뜻하지는 않는다

`eyeHr[]`는 먼저 SetTransform 결과를 저장하고 이후 Draw 결과로 덮어쓴다. right RT/depth/viewport에서 실패하면 right는 E_PENDING으로 남는다. 현재 로그에 right-state HRESULT나 restore의 각 HRESULT가 없다. `R30ExecuteXyzrhwStereo()`의 누적 duplicated counter는 right 실패에도 증가할 수 있다.

권고: `projectionSetHr`, `drawAttempted`, `drawHr`, `targetSetHr`, `depthSetHr`, `viewportSetHr`, `restore*Hr`를 분리한다. RESULT_HUD_EYES의 S_OK 두 개와 `projectionRestored=1`, `frameIncomplete=0`도 최종 XR submit 증명과는 별개다.

### M3. physical draw identity를 한 번 snapshot하여 전달하는 편이 명확하다

현재 exact 판정은 R62 입구, pose 구성, 사후 로그에서 다시 capture한다. TLS이므로 다른 thread가 직접 바꾸는 데이터 race는 아니다. 일반 동기 경로에서 상태를 바꾸는 game source 호출도 확인되지 않았다. 따라서 실제 identity drift가 발생했다고 단정하지 않는다.

다만 COM 호출 및 D3DX reentry를 전제로 한 코드베이스이므로, draw 진입의 `PhysicalDrawCommand`를 한 번 확보해 exact 판정·pose·로그에 전달하고 좌우 사이 동일 identity를 검증하는 방식이 더 강하다. 사후 capture는 별도의 `after`로 비교해야 하며 원래 source identity를 대체하면 안 된다.

### M4. queueEpoch는 pointer 재사용을 구분하지만 손실된 batch를 복구하지는 않는다

`SelectSpriteQueueNode():1789–1820`은 같은 pointer라도 매번 epoch를 증가시킨다. batch ledger의 queued/node/epoch 검증과 generation snapshot은 적절하다. `BeforeQueueNode():3580`는 선택 전에 direct result drain 및 outgoing node Flush를 실행한다. unknown/mixed/foreign/실패 batch에는 소유권을 부여하지 않는다.

제한: Flush 실패 후 원본 D3DX 내부 buffer가 남았는지까지 metadata만으로 알 수 없다. proof 철회와 native fallback은 과도한 relabel을 피하지만 **화면이 반드시 올바르다는 보증은 아니다.** physical draw 이후 frame/submit 상태와 함께 검사해야 한다.

### M5. game pixel과 현재 viewport가 같다는 전제가 R26 XYZRHW에 남아 있다

좌표계는 세 단계다: 원본 640×480 logical 위치 → UIScaling/`Game::screen_resolution`/sprite transform을 거친 game presentation pixel → 실제 D3D viewport/eye surface.

- `hooks_uiscaling.cpp:800–890`의 native quad는 screen resolution/scale 기반 mapping을 거쳐 `DrawPrimitiveUP(..., stride=0x1C)`로 제출된다. 모든 원본 sprite가 최종에도 640×480이라는 주장은 틀리다.
- `R30TransformXyzrhwVertices():3390` 이후는 `state.viewport`를 source pixel 정규화와 destination 환산에 함께 쓴다.
- `ProjectPixelPairAcrossViewports()`는 source/destination viewport를 분리한 helper지만 **R26 safe renderer에서 호출되지 않는다.** header include 자체는 사용 증거가 아니다.
- R62/FVF142는 원본 D3DX projection을 보존하고 clip-space map을 postmultiply하므로 같은 pixel 문제를 무조건 공유한다고 볼 수 없다. 원본 world/view/projection이 어느 game extent를 encode하는지와 live viewport를 함께 기록해야 한다.

결론: source game extent ≠ 실제 eye viewport인 XYZRHW의 오류 가능성은 남아 있다. 이번 자료에 두 extent가 실제로 달랐다는 샘플은 없어 현재 증상의 확정 원인으로 승격하지 않는다. 해상도를 강제로 되돌리는 대신 각 좌표의 실제 값을 먼저 확인한다.

## 4. 현재 패치가 논리적으로 맞는 부분

### 4.1 v2와 v3 모두 이 생산 경로에서는 head-local orientation이다

추적 경로:

`main_r23.cpp:2804–2829 xrLocateViews(localSpace)` → `main.cpp::SharedWriter::Write():632–643` → `ToHeadLocalOrientation(head,eye) = conjugate(head.q) * eye.q` → packed v2 orientation → `v3_shadow_bridge.cpp:406 HostStateFromV2` → `shadow_legacy_v2.hpp:226–231` 복사 → `host_pose_v3.hpp` snapshot → `ReadHostPose():740–774` → `LatchFramePose():1486–1497`.

OpenXR XrView 자체가 자동으로 head-local인 것은 아니다. 호출한 space 기준이며, **이 host가 명시적으로 변환한다.** 현재 v3 publisher는 그 변환된 packed v2 값을 복사한다. 이번 확인 경로에 reference-space absolute eye orientation을 그대로 WireEyeView에 넣는 단계는 없다.

`LatchedStereo.eyeOrientation`은 head-local이고, `effectiveEyeOrientation = effectiveHeadOrientation * eyeOrientation`은 compositor용 절대 pose다. 결과 HUD는 전자를 사용한다. 둘을 혼용하지 않는다.

### 4.2 row-vector 행렬 순서와 quaternion 순서는 맞다

head-local eye pose를 E, recentered head pose를 H라고 하면 row-vector eye-to-world는 `E H`, inverse view는 `(E H)^-1 = H^-1 E^-1`이다. 따라서 가상 HUD plane point p의 clip 좌표는:

`p × HeadInverse × EyeInverse × EyeProjection`

현재 식과 일치한다. quaternion은 Hamilton 곱 `qHead * qEye`이고, `MatrixFromQuaternionTranslation()`은 이에 대응하는 row-vector rotation matrix와 마지막 행 translation을 만든다. D3D9이라는 이유만으로 임의 Z flip을 추가해서는 안 된다. 본 코드의 보이는 물체는 음의 view-Z/양의 clip-W convention을 쓰며 해당 projection과 일관된다.

### 4.3 eye orientation을 normalize만 하는 것은 현재 producer에 적절하다

이미 `inverse(head) * eye`인 quaternion에서 다시 `inverse(centerEyeOrientation)`을 곱하면 런타임이 정의한 eye-to-head 공통 축 성분까지 제거할 수 있다. 현재 생산 경로에는 그런 추가 상대화가 필요하다는 근거가 없다. 두 위치의 중심을 빼는 정책과 orientation의 head-local 변환은 별개의 연산이다.

`BuildStageEyePoses(worldScale)`은 scale의 유효성만 검사하며 offset 자체를 scale하지 않는다. 실제 scale은 `MatrixFromQuaternionTranslation()`에서 한 번 적용되므로 여기서 이중 scale은 없다.

### 4.4 R62가 처리한 draw 뒤 원본 mono draw를 추가하지 않는다

`DrawIndexedPrimitiveDestR30():5285–5324`는 R62 결과가 E_NOTIMPL이 아니면 즉시 반환한다. 정상 경로의 실제 DIP는 left/right 두 번이며, 원본 게임 DIP가 세 번째로 이어지는 코드는 없다. `InternalPassScope`는 이전 값을 저장/복원하며 stereo 재진입을 차단하고 실제 draw는 원본 trampoline을 호출한다.

거절이면 후속 XYZRHW/셰이더/하위 renderer로 위임한다. 이것은 이미 두 번 그린 후의 추가 mono와 다르다. 단, 원본 source가 별도 duplicate geometry를 생성하거나 D3DX가 실패 후 재시도하는지는 이 wrapper 흐름만으로 배제할 수 없다.

### 4.5 live VS 조회와 좁은 형식 gate가 적절하다

GetVertexShader는 실제 device에 설정된 shader를 조회한다. exact result에서 stale cache를 예비 거절로 쓰지 않는 것은 합리적이며, 실제 VS가 있으면 고정기능 projection 변경으로 처리하지 않고 E_NOTIMPL을 반환하는 것도 맞다. shader COM reference를 Release한다.

FVF142는 `XYZ | DIFFUSE | TEX1`을 나타내는 좁은 gate이다. 이것은 해당 fixed-function DIP를 처리하기에 적절하다는 뜻이지 모든 결과 HUD의 GPU 형식이라는 뜻은 아니다.

### 4.6 deferred batch 및 B9200 보호는 유지된다

`FlushDest/EndDest:3351–3423`는 active/homogeneous/live sprite/owner가 맞을 때 이전 batch producer를 복원한다. unproven direct result는 현재 source의 잘못된 소유권을 빌리지 못하게 한다. direct source enter/exit 및 first queue transition의 순서도 이를 지원한다.

B9200은 GOAL 상태와 원본 19 CALL의 return 주소를 stack trace로 확인하고, direct D3DX Draw에서 얻은 증명을 ledger에 보관한다. **19개 post-CALL/+5 hook을 복원하지 않는다.** 24-frame stack walk가 실제 최적화된 x86 모든 호출을 항상 포착한다는 보증은 없다. 미포착은 UNKNOWN/native fallback으로 다루고 broad GOAL 분류로 메우지 않는다.

## 5. producer별 추적 결과와 수정안

다음 표의 U는 이번 자료에서 해당 producer별 최종 GPU 형식/실제 좌우 제출을 확정하지 못했다는 뜻이다. 원본 EXE/REA 전체 본문과 최신 실행 로그를 이번 검토에서 다시 취득하지 않았으므로, checked-in 원본 호출 증거가 끝나는 곳을 넘어서 추정하지 않는다.

| producer / original caller RVA | SpriteNode / direct 및 D3DX 경계 | 최종 API · FVF · VS 증거 | R30/R62 및 실제 left/right/mono |
|---|---|---|---|
| +TIME decoration: 9898E, 98A36 → 29530 | StageExtensionTime, appended queue tag; direct scope도 존재. queue는 Begin/Draw/End 또는 native 혼합 | producer별 U | DIP142/null VS라면 R62; XYZRHW라면 R30. 실제 L/R U, R62 소유 성공 뒤 추가 mono 없음 |
| +TIME 문자: 989AD, 98A10, 98A89의 text/number 지원 | direct owner + appended queue; homogeneous source-exit/Flush/End 복원 | 문자만의 API/FVF/VS U | 동일 조건부 경로, 실제 L/R U |
| +TIME 숫자: 위 print family | 문자와 숫자를 token 하나만으로 분리할 수 없음; batch/texture/glyph 추가 식별 필요 | 숫자만의 API/FVF/VS U | 동일 조건부 경로, 실제 L/R U |
| progress graph/fill: 97BE4, 97DEC → 2D200 | ResultProgress queue; 98924/992AC → 979E0 parent가 더 넓은 graph/text를 감쌈 | baseline 기록에 DIP, FVF142, VS null, queueEpoch 존재 | R62 eligible. 기록은 입구 증거이며 실제 left/right 성공은 U |
| result percent | full ResultProgress parent와 B9200 glyph family의 자식일 수 있음; 픽셀 요소와 정확 CALL 일대일 대응 U | U | token과 GPU fingerprint 함께 필요 |
| stage time: BEA5A/BEA5F, 975EE/97727/977FB 계열 | GoalTime020/150, OutRunStagePrintf direct/queued ownership | U | R62/XYZRHW/VS 중 실제 형식별 분기 |
| title/text: 975EE/97727/977FB 및 result glyph family | Sumo_Printf 및 원본 B9200 stack proof, deferred batch | U | shader HUD가 나오면 identity-eye 잔존 문제 적용 |
| B9200 19 CALL: 973AF…97E6D | 원본 CALL 무수정, stack-proven put_sprite_ex/direct D3DX 및 queued tag | U | proof 있으면 exact result; 없으면 native/기존 fallback. L/R U |
| mode2: 98AC6 → 29530 | +TIME owner에서 제외 | U | StageExtensionTime으로 재편입 금지 |
| 차량 rank: BAD20, BB0FB/BB133/BB16C/BB1A5, BB21F/BB241/BB271/BB2BC/BB2D0 | Calc3D2D anchor, sprani/clip, R64 queued D3DX Flush | repo에 kind0 DIP142/null VS 경로와 native kind1 UP 코드. 이번 실행별 관측 U | R57 delta + R62/XYZRHW/VS. actual L/R U |
| rival: BB6F5 Calc return | 별도 anchor와 producer | U | ordinal cant flag 제외; 실제 회귀 여부 U |
| 렌즈 중앙: D3A5 → C980 → C993, 570002 | direct object, D3DX SpriteNode라고 가정하지 않음 | actual API/FVF/VS U | 설정 false면 draw 생략. true + 원본 WVP proof면 shader WorldBillboard 후보 |
| 렌즈 외곽: CABE / C9A0 | ProjectedScreenEffect2D, 중앙과 별개 | U | matrix evidence로 spatial/flat 분류; 전체 SceneEffect 통합 금지 |

소스상 queue renderer는 D3DX와 native draw를 혼용한다. `hooks_uiscaling.cpp:889`에는 native DrawPrimitiveUP가 실제 존재한다. 다만 이것을 특정 +TIME glyph가 반드시 사용한다고 연결할 증거는 부족하다.

수정 위치/논리 제안:

| 우선순위 | 파일 / 함수 / 위치 | 제안 |
|---|---|---|
| HIGH | R26 safe `R30BuildScreenSpaceEyeConstants`, 4739 | 실제 해당 producer가 VS 경로임을 확인 후 exact result만 head-local cant 적용. 일반 HUD identity 분기 보존 |
| HIGH | R26 safe `R30PrepareXyzrhwState`, 2432 | 확인된 exact result에만 live VS 우선 gate. R62와 동일 판정 snapshot 사용 |
| HIGH | `hooks_graphics.cpp::DrawObjectAlphaCentre`, 677; settings 115 | 억제 상태를 수정 완료와 구분해 보고. opt-in 중앙만 활성화하여 physical fingerprint를 수집한 뒤 실제 경로 수정 |
| HIGH | rank R57 1565 / R62 5011 | CalcCapture→Producer→NativeSprite→queue→physical draw 연쇄 확인. rank cached/live mismatch가 관측되기 전 global bypass 금지 |
| MEDIUM | R30 Draw* 입구 / Configure / R62 / telemetry | 하나의 immutable command 전달; after-native identity는 별도 비교 |
| MEDIUM | R62 5158 / Execute 3772 | state HRESULT와 Draw HRESULT를 분리, restore failure 주입 테스트 |
| MEDIUM | R26 XYZRHW transform 3390 | source pixel extent를 별도로 보존하고 필요한 producer에만 destination viewport 변환. 모든 game resolution 전역 변경 금지 |

제안 통합 deterministic test는 helper 테스트에 그치지 않아야 한다. yaw/pitch/roll 모두 비영인 H, 좌우 ±cant E, asymmetric FOV, 64 mm IPD, nonidentity HeadInverse, -2.5 plane, 원본 D3DX orthographic projection을 입력한다. 실제 R30 matrix/clipMap 구성 코드를 공유하거나 추출해 검증한다. `inverse(E*H)`와 `H^-1*E^-1`를 독립 비교하고, 양안 ray를 같은 world plane point로 역투영해 일치시킨다. 잘못된 `E^-1*H^-1`, identity cant, absolute eye 재사용 mutation은 실패해야 한다. **좌우 pixel 좌표가 똑같아야 convergence라는 테스트는 잘못이다.** FOV/IPD에 따른 disparity와 동일 공간점 복원이 기준이다.

## 6. 수정하지 말아야 할 부분 및 회귀 범위

- B9200 19개 +5 post-CALL hook, 특히 97C57+5/97E6D+5 및 금지된 queue entry 2D734.
- mode2 98AC6의 +TIME owner 편입.
- 원본 timer, 입력/FFB, 하늘/SkyGlow, ESC, F11, 주변 렌즈 원반의 일괄 분류/억제.
- 고정 HUD rank와 차량 위 rank의 owner 통합.
- 보호 baseline SHA/ZIP 덮어쓰기, R84를 기본 renderer로 조용히 교체하기.

단독 HUD 커밋과 전체 비교 구간의 판정:

| 경로 | aab9e02 단독 | 0cff83cf→aab9e02 전체 |
|---|---|---|
| 일반 HUD / ESC | exactResult=false이면 기존 pose 분기 유지 | 공유 소스 및 다른 커밋 포함, 전체 불변 주장 불가 |
| 차량 위 rank | 단독 HUD 변경의 대상 아님 | ordinal cant, marker 전달·probe 변경 있음 |
| rival | 단독 HUD 변경 대상 아님 | 수식 false branch 유지, shared sprite provenance 변경 있음 |
| 렌즈 중앙 | 단독 HUD 변경 대상 아님 | 기본 억제 설정/early return 추가됨 |
| 주변 렌즈 / SkyGlow | 단독 diff에는 관련 변경 없음 | graphics 공유 파일 변경 포함; 동일 환경 실기 비교 필요 |
| F11 / menu | 단독 diff에는 직접 변경 없음 | host menu aspect, mirror aspect, settings, build/selector 변경 포함 |
| input / FFB | 단독 diff에 없음 | 직접 input/FFB 파일 변경은 compare 목록에 없음; 패키지 전체 동일성 보증은 아님 |
| D3DX batching | 단독 HUD 커밋에 Begin/Draw/Flush/End 수정 없음 | shared semantic/provenance 변경 포함; 실기 검증 분리 |

## 7. Quest 3에서 확인할 로그와 합격 조건

1. SHA, 설치 DLL의 R26+HUD build 옵션, host SHA, 실제 INI, `LensFlareCentreEnabled`, `VRUnifiedEyeMenuSource`, game source extent, D3D viewport, XR eye extent를 먼저 고정한다.
2. +TIME decoration·문자·숫자, result graph·percent·stage time·title·B9200 glyph를 각각 검사한다. ResultProgress 한 줄을 전체의 대리 증거로 쓰지 않는다.
3. `RESULT_HUD_EYES`: producer, queued, node, epoch, pose, viewport, left/right HRESULT, projectionRestored, frameIncomplete. right E_PENDING은 미시도다. Draw 성공 두 개 + restore + frame 유효성 + matching XR submit을 연결한다.
4. `RESULT_HUD_REJECT`: cachedVS/liveVS/vsHr/fvf/fvfHr/seeded/incomplete 및 최종 선택 route를 연결한다. 현재 메시지는 DIP/R62 거절 전용이며 모든 API의 reject 총계가 아니다.
5. 차량 위 rank: `R57 RANK OWNER PROBE`, `R57 ORDINAL EDGE PROBE`, `EXACT CALC EDGE`, projected marker stages, `R64 D3DX ISOLATE RESTORED`, `R62 FIXEDFN KIND0`를 같은 frame/node/epoch로 연결한다. ordinal 1–3 및 4–6 숫자 조합, 근거리/원거리·화면 가장자리, 여러 차량을 확인한다. parentActive=0이 parent 종료 시 로그에 찍히는 것은 위치상 정상일 수 있다.
6. 중앙 렌즈와 외곽을 별도 비교한다. 중앙 OFF에서 사라짐은 억제 판정. 중앙 ON은 동일 call epoch/raw-c64/pose/VS와 실제 양안 draw, 최종 submit을 요구한다. 기존 `P0 FLARE OBJECT`는 CABE 외곽 로그이므로 C993 중앙 성공 증거로 대체할 수 없다.
7. head yaw/pitch/roll·좌우 이동·recenter·해상도 전환·ESC 복귀·두 번째 경기에서 검사한다. 두 눈 영상의 존재, 실제 양안 융합, head-follow 여부를 따로 기록한다. stereo separation과 원본 third draw를 distinct physical draw ID/RT로 구분한다.

## 검증 기록과 한계

- GitHub HEAD 확인: 요청 SHA와 일치.
- compare: ahead 44, behind 0; merge base가 지정 baseline과 일치.
- `python3 tools/verify_vr_r26_result_hud_pose.py`: PASS.
- `g++ -std=c++17 -O2 vrhost/tests/stage_extension_eye_plane_smoke.cpp` 후 실행: exit 0.
- 위 검사는 조회 SHA에서 내려받은 소스에 대해 수행했다. 실제 Windows DLL/D3DX/OpenXR 실행 검사가 아니다.
- exact-SHA workflow 조회 결과 빈 배열: CI 성공/실패를 확정하지 않음. run이 존재하지 않는다고도 단정하지 않음.
- 최신 원본 EXE/REA 함수 JSON 및 런타임 로그의 전 producer 종단 추적은 이번 입력에 없으므로 최종 GPU API 미확정 항목을 U로 남겼다. N100 대규모 재분석·빌드는 실행하지 않았다.
- 다음 실행 작업: 기존 TASK_ID에서 producer/API별 missing physical evidence를 수집한 후, H1의 해당 확인 경로만 보완하고 같은 SHA Windows gate 및 Quest 3 검증을 수행한다.

## 근거 링크

- [검토 커밋](https://github.com/thp32tt/OutRun2006Tweaks/commit/aab9e02bcb2ad2e6253840e6267e5c5ad5040854)
- [baseline 비교](https://github.com/thp32tt/OutRun2006Tweaks/compare/0cff83cf509c2acd6f3391b3a46c4dec1403a0d9...aab9e02bcb2ad2e6253840e6267e5c5ad5040854)
- [R26 renderer](https://github.com/thp32tt/OutRun2006Tweaks/blob/aab9e02bcb2ad2e6253840e6267e5c5ad5040854/src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp)
- [UIScaling / source / D3DX](https://github.com/thp32tt/OutRun2006Tweaks/blob/aab9e02bcb2ad2e6253840e6267e5c5ad5040854/src/hooks_uiscaling.cpp)
- [렌즈 producer](https://github.com/thp32tt/OutRun2006Tweaks/blob/aab9e02bcb2ad2e6253840e6267e5c5ad5040854/src/hooks_graphics.cpp)
- [설정](https://github.com/thp32tt/OutRun2006Tweaks/blob/aab9e02bcb2ad2e6253840e6267e5c5ad5040854/src/vr/settings.cpp)
- [v3 변환](https://github.com/thp32tt/OutRun2006Tweaks/blob/aab9e02bcb2ad2e6253840e6267e5c5ad5040854/src/vr/ipc/shadow_legacy_v2.hpp)
- [원본 호출 증거](https://github.com/thp32tt/OutRun2006Tweaks/blob/aab9e02bcb2ad2e6253840e6267e5c5ad5040854/docs/research/REA_R84_EXACT_DIRECT_EVIDENCE_20261018.md)
- [mode2 분리 증거](https://github.com/thp32tt/OutRun2006Tweaks/blob/aab9e02bcb2ad2e6253840e6267e5c5ad5040854/docs/research/REA_STAGE_EXTENSION_MODE2_SOURCE_SCOPE_20261019.md)
- [Khronos xrLocateViews 1.1](https://registry.khronos.org/OpenXR/specs/1.1/man/html/xrLocateViews.html), [XrView](https://registry.khronos.org/OpenXR/specs/1.1/man/html/XrView.html)
- [Microsoft GetVertexShader](https://learn.microsoft.com/en-us/windows/win32/api/d3d9/nf-d3d9-idirect3ddevice9-getvertexshader), [D3DX End](https://learn.microsoft.com/en-us/windows/win32/direct3d9/id3dxsprite--end)

외부 API 문서는 2026-10-20 조회한 공식 문서의 현행 계약을 사용했다. 오래된 API의 문서 최초 작성일을 제품의 최근 출시 정보로 오인하지 않았다.
