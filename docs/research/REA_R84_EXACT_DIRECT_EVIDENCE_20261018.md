# REA 직접 증거 기반 R84 GPU 경로 교차 검증 (2026-10-18)

원본 EXE SHA256: 68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3
REA 원본 함수 개별 JSON 주소/해시 검증: 17개 PASS; 직접 호출 관계 20개 PASS.
이미 가동 중인 REA 배치 작업을 수정하거나 재시작하지 않았다. REA pseudocode/게임 원본을 GitHub에 올리지 않는다.

## 직접 확인한 원본 렌더 경로
- 원본 0x00449050 -> 0x0042D710, 그리고 조건부 0x004C50A0 호출. 실제 Sprite 소비 진입 XREF: 0x004491D7, 0x004C50B1.
- 큐 0x0042D710 direct callee: 0x00429C60(D3DX Begin), 0x00429F60(End), 0x0042A0A0(Draw), 0x0042A3A0(native draw), 0x0042A800(mask composite), 0x0042C0F0(glyph draw), 0x0042A2B0(state). 큐 unresolved indirect callsite 36개.
- 고정 6th/6 함수 0x004B9D80 -> 0x00429530(sprani) 및 0x0042D280(clip) 모두 확인. REA 기본 callers 0으로 보여도 실제 native incoming XREF 2개가 존재.
- 차량 부착 순위 0x004BAD20 -> 0x00429580(alpha sprani), 0x0042D280(clip), 0x00449940(Calc3D2D). 고정 rank와 다른 owner.
- 두 rank 함수의 native incoming XREF 주소는 겹치지 않는다. 고정 rank 0x004BEC7E/0x004BED98, 차량 rank 0x004BEB98/0x004BED83/0x004BED9E/0x004BEDAE. 인접 코드 영역의 구조적 맥락만 확인되며 동일 상위 부모/동일 프레임 발동은 아직 미입증. 화면 HUD/월드 마커 합치기 금지.
- +TIME 관련 0x004979E0는 0x00429530과 0x0042D280를 둘 다 호출. 0x0042CFE0(type0), 0x0042D0C0(type1)는 각각 0x0042DD50으로 할당. 소스가 한 GPU Draw로 1:1 제출된다고 가정 금지.
- 렌즈 원본 0x0040CBC0는 0x0040C980(centre parent), 0x0040C9A0(outer) 둘 다 호출. C980 개별 REA 재시도 성공: 원본 CALL 0x0040D3A5 -> 0x0040C980 -> 0x004056D0 정확 주소/기계어 확인. 이것만으로 VR 양안 GPU 출력은 증명되지 않음.
- 마스크 합성 함수 0x0042A800은 미해결 원본 간접 CALL 85개. UI 알파/차량 선택 경로의 정확 texture/sampler/RT 상태는 미확정.

## 최신 R84 소스 정합성 점검
- 현재 render_semantics.hpp는 EndSpriteQueueFrame 및 frame-expire cutoff가 있어 과거 부분 소비 큐의 미방문 태그 삭제 결함은 이미 수정됨. 중복 패치 금지.
- ScreenHud와 ProjectedWorldMarker2D 분리 존재. 병행 TASK 01039 material SHA 513434b6에서 원본 E8 opcode 검사와 source serial 보호가 C++에 추가된 사실을 확인. 이를 이번 독립 분석의 변경/점수로 중복 보고하지 않음.
- universal_draw_trace.hpp noR33EyeEvidence는 R30 조기 성공을 mono라 단정할 수 없음. native 실제 left/right HRESULT/RT/WVP 복원과 host OpenXR frame 증거는 아직 없음.

## 남은 구현/검증 우선순위
1. +TIME·6th/6 원본 kind0/1 source serial -> D3DX batch/native GPU draw -> R30 eye pair -> R33/host 최종 submit 이벤트 연쇄.
2. world rank 0x00449940 차량 좌표와 R30 FVF 0x142 오른눈 재투영; 소유권 상위 XREF만으로 화면 HUD 승격 금지.
3. 렌즈 중심/외곽/SkyGlow 독립 shader/c64/pose, 차량 선택 마스크 alpha/sampler 및 상태 복원 동일 SHA 비교.
4. 큐 간접 36개, mask 간접 85개 원본 기능 미확정은 UNKNOWN으로 유지. HMD 런타임 UNTESTED.

이번 REA 검토는 새 GPU 동작 수정 없이 정적 검증 결과를 확정한 것으로, Windows CI/Quest3 정상 화면을 주장하지 않는다.