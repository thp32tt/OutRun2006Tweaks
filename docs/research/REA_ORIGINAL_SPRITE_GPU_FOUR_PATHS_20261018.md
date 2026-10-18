# REA 원본 함수 실증: Sprite 큐 4분기·+TIME 6개 CALL

분석: 2026-10-18 KST. 원본 OR2006C2C.exe SHA-256 68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3.
분석 도구: N100 REA 6.5.0 + Ghidra 12.1.4 함수 증거 JSON, 원본 PE x86 E8 rel32 바이트 개별 검증. 원본 EXE와 디컴파일 코드는 N100-local만 사용.

## 원본 +TIME E8 rel32 6/6 확인

| 원본 호출 RVA | 역할 | 원본 target VA | 바이트 검사 |
|---|---|---|---|
| 0x9898E | B4 애니메이션 | 0x429530 | PASS |
| 0x989AD | B4 숫자/문자 출력 | 0x4973C0 | PASS |
| 0x98A10 | B4 숫자 | 0x4974E0 | PASS |
| 0x98A36 | B5 애니메이션 | 0x429530 | PASS |
| 0x98A89 | B5 숫자/문자 출력 | 0x4973C0 | PASS |
| 0x98AC6 | 6C 애니메이션 | 0x429530 | PASS |

중요: 0x498AC6은 원본 EXE 바이트에서 명확한 E8 rel32 CALL이며 목적지도 정확하다. 그러나 REA가 0x498670 함수의 비연속 body에서 복구한 outgoing call inventory에는 이 호출이 누락됐다. 이 함수의 Ghidra 의사코드에는 일부 unreachable-block 제거도 보고된다. 따라서 디컴파일 함수 call 목록만으로 6C 훅을 잘못된 주소라 판단해 제거하면 안 된다. 현행 6개 원본 훅 RVA 유지가 타당하다. 이는 GPU/VR 실행 여부 증명과 다르다.

## REA로 직접 검증한 원본 4개 GPU 경로

REA 0x42D710 함수 증거 ID: ev_298a764e0893409001c5ae5a4fc36b2d31821750855c00084d56c64b78ae5e1f.

| SpriteNode 분기 | 원본 조건 | 실제 호출 함수 | GPU 의미 |
|---|---|---|---|
| type 0: D3DX | node[3] == 0, node[0x11] & 0x100 == 0 | 0x42A0A0 | D3DXSprite Draw; Begin/End에서 지연 제출 가능 |
| type 0: 직접 | node[3] == 0, node[0x11] & 0x100 != 0 | 0x42C0F0 | direct primitive UP |
| type 1: 애니메이션 쿼드 | node[3] != 0, node[0x18] & 0x40000 == 0 | 0x42A3A0 | animation direct primitive |
| type 1: 마스크/합성 | node[3] != 0, node[0x18] & 0x40000 != 0 | 0x42A800 | masked/composite animation draw |

위 4개 target은 REA 원본 큐 함수의 참조 및 피호출자 증거로 확인. 큐 함수 내 unresolved CALL 36개가 있어 간접 호출 경로 전수 완료로 간주하지 않는다. 두 애니메이션 경로가 서로 다르므로 6th/6·+TIME·SELECTOR 마스크 등을 일반 Sprite Draw 한 군데만으로 추적하는 것은 누락 위험이 있다.

원본 0x449050 → 0x42D710 정규 소비 CALL VA 0x4491D7은 REA XREF에서 확인. 조건부 부분 소비 함수 0x4C50A0은 기존 Ghidra C 경로로 확인되나 새 REA 배치의 개별 함수 검증 대기 중이므로 완전한 REA PASS라고 표시하지 않는다.

## 분석 파이프라인 검증 및 미확정 부분

- 기존 REA 확인 2개, REA 신규 정상 결과 22개, 타임아웃 1개 (REA_RENDER_BATCH_AUDITED.json의 19:56 KST 스냅샷).
- 실행 중인 별도 워커가 원본 함수 주소를 0x004... / 0x4...처럼 서로 다르게 표기해 정상 분석을 FAILED로 기록하는 상태 불일치가 있다. 숫자 주소와 원본 SHA를 함께 확인한 audited 결과를 성공의 기준으로 삼아야 한다. 타임아웃은 성공으로 바꾸지 않는다.
- 현재 R84는 SpriteNode 세대 재사용 보호 및 partial→full 큐 프레임 종료 보호가 추가된 상태다. 같은 수정을 다시 적용하지 않는다.
- R30/R33의 실제 좌우 눈 GPU HRESULT·pose·RT/Depth/Stencil·WVP 복원과 호스트 OpenXR Submit은 정적 REA로 확인할 수 없어 RUNTIME_VALIDATION=UNTESTED.
- 스크린 HUD와 월드 rank/중앙 lens/SkyGlow는 서로 다른 소유권 경로. 다른 분야를 단일 alpha heuristic으로 ScreenHud 처리하지 않는다.

## 개발 후속 조치

1. 기존 REA/원본 EXE 근거로 StageExtensionSpraniCalls 3개, 숫자 CALL 3개는 유지한다.
2. 최종 GPU 계측은 네 개 SpriteNode 물리 분기(type0 D3DX, type0 UP, type1 quad, type1 mask) 모두를 커버해야 한다. 특히 type1 마스크 경로 0x42A800의 원본 Draw와 R84 네 Draw* 훅 매칭을 검증한다.
3. 개별 함수 REA 성공이 확대되면 새 증거만 추가 검토하고 동일 함수의 무의미한 중복 재분석은 하지 않는다. 기존 실행 중인 배치, 다른 DX9Ex TASK_ID/owner를 건드리지 않는다.
4. 이번 산출물은 정적 함수 근거 보강이며 **게임 C++ 수정/빌드/HMD 오류 해결 완료가 아니다**. 기존 HUD/화면 오류 실기 검증은 그대로 필요하다.