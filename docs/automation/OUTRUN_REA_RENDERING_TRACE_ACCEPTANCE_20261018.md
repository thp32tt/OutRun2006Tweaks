# R84 전체 원본 렌더링 추적 — 구현 가능한 이벤트·합격 기준

이 문서는 분석 산출물에 기반한 개발용 진단 계약이다. **로그 포맷 제안은 구현/실행 완료 증거가 아니다.** 현재 모드에는 `VRTelemetry`/`universal_draw_trace.hpp`의 집계가 있으나 모든 원본 source_serial → physical draw → host eye를 세밀하게 이어 주는 이벤트 체인은 별도 구현 필요.

## 1. 계측 지점별 이벤트

| 원본/모드 단계 | 최소 필드 | 실행 트리거 | 오분류 예방 |
|---|---|---|---|
| 원본 EXE dispatch | originalExeSHA, functionVA, originalE8CallRVA, sourceSerial, frameEpoch | 허용된 원본 E8 부모 호출 | 함수 시작 VA와 CALL 명령 RVA를 혼동하지 않음 |
| SPRANI animation | animId, childId, keyframe, branchMode, writerSerial | `0x00429530`·`0x00429350` | 원본 애니메이션 1:N child 분리 |
| glyph creation | textRunId, glyphSerial, originalCallRVA, sourceSerial | `0x004973C0` / `0x004974E0` → `0x004B9200` | +TIME 숫자와 GOAL 및 다른 % UI 분리 |
| queue allocate | nodePtr, nodeGeneration, nodeType0or1, priority, queueEpoch | `0x0042DD50` | 동일 포인터 재사용 시 generation 필수 |
| queue consumer | queuePriority, queueNodeSerial, sourceSerialSet, batchID | `0x0042D710`, `0x00429C60` | 한 draw가 여러 source를 포함할 수 있음 |
| D3DX Sprite Draw | batchID, bufferPendingCount, spritePtr, producerId | `0x0042A0A0` | Draw 함수 반환 != 실제 GPU Draw |
| D3DX Flush/End | batchID, originalGpuPrimitiveIDs, finalSourceSerialSet | `0x00429F60` 및 강제 정합 Flush | 같은 소유자에 의해 batch 종료되는지 |
| Original D3D Draw | originalDrawSerial, FVF, VS/PS, RT/DS, viewport, depthStencil | original device vtable indices 81~84 | 원본 모노와 R84 좌우 Draw 혼동 금지 |
| R84 R30 stage | route, eyePoses, rawWvpSerial, queueEpoch, nativeLeftHr, nativeRightHr, reason | R30 FixedFn/XYZRHW 조기 반환 | R33 generic 카운터 없다고 mono 판정 금지 |
| R84 R33 GPU | physicalDrawID, producer/source, leftHr, rightHr, restored, target, pose, shader | 4 Draw 진입점 및 원본 폴백 | 상태 복원 실패는 frame invalid |
| x64 OpenXR host | gameFrameEpoch, stereoFrame, leftSwapchainImage, rightSwapchainImage, submitResult | host final composite | GPU 성공 != HMD 육안 성공 |

## 2. 공통 메타 스키마 (권장, 미구현)

```json
{
  "schema": 1,
  "session_id": "test-session",
  "exe_sha256": "68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3",
  "vr_material_sha": "from actual installed binary",
  "frame_epoch": 0,
  "source_serial": 0,
  "call_rva": "0x9898E",
  "sprite_node": {"address": null, "generation": null, "node_type": 1, "queue_epoch": null},
  "d3dx_batch_id": null,
  "physical_draw_id": null,
  "left": {"attempted": false, "hresult": null, "target": null},
  "right": {"attempted": false, "hresult": null, "target": null},
  "restoration": {"result": "UNKNOWN"},
  "pose_epoch": null,
  "shader_epoch": null,
  "openxr_frame_id": null,
  "validation": "UNTESTED"
}
```

## 3. 예측 가능한 장애 플래그

- `SOURCE_NOT_ATTACHED`: 원본 call RVA는 확인됐으나 물리 GPU Draw의 source/queue 연계가 없음.
- `MIXED_D3DX_BATCH`: 2개 이상의 원본 source가 같은 물리 배치에 섞임. 실제 표시 오류인지 별도 확인.
- `QUEUE_NODE_REUSED_WITHOUT_GENERATION`: 큐 포인터는 같으나 epoch/serial 연계 없음.
- `LEFT_OK_RIGHT_UNVERIFIED`: Native LEFT 성공, RIGHT 이벤트 없음. R30 보호 fallback인지 재확인.
- `RIGHT_EYE_VETO_AFTER_LEFT`: pose/WVP/shader/producer 재진입 변동으로 오른쪽 눈 거부. 안전상 올바른 동작일 수 있음.
- `DUPLICATE_SOURCE_DRAWS`: 단일 원본 sourceSerial이 중복 물리 Draw로 이어지며 동일 RT/eye가 중복 기여하는 것으로 관측됨.
- `STATE_RESTORE_FAILED`: render target/depth/stencil/WVP/viewport 원복 실패. Present 안전성 검사.
- `F11_HOST_UNCORRELATED`: 원본 게임 D3D9가 아닌 host UI라 합성 로그 미연결.
- `NOT_OBSERVED`: 테스트 중 해당 모드/장면이 실행되지 않음. PASS도 FAIL도 아님.
- `GPU_BOTH_BUT_HMD_WRONG`: GPU/host 합성은 양안 성공이나 HMD 육안 검사에서 오배치. 광학/행렬/캔버스 원인으로 추가 조사.

## 4. 상태별 권장 성능·검증 정책

- 모든 draw에는 가벼운 카테고리별 카운터만 허용. 상세 이벤트는 문제 프레임 전후 bounded ring buffer에 보관. GPU readback과 다량 동기 파일 쓰기는 핫패스에서 금지.
- HMD에서 같은 설정으로 재현: 시작 화면 → 차량 선택 → 게임 시작 → HUD·순위 → +TIME → GOAL → ESC → F11 → 렌즈/하늘 회전 → 프레임 재센터.
- CI는 긍정/부정 도메인 격리, source owner 상태 회복, FVF 0x142 조기 draw, 고정 screen-plane/3D world 분리, D3DX pending flush, queue node pointer reuse, shader change, pose reentry 및 eye restore 실패 케이스를 포함.
- 기존 양안/파티클/하늘/GPU 최적화 훼손 없는지 회귀 검사.
- Quest3 실기 전 `RUNTIME_VALIDATION=UNTESTED` 유지.