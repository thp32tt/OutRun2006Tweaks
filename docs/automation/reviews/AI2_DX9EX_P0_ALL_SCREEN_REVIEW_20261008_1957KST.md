# DX9Ex Quest 3 전체 화면 문제 — 30분 집중 소스 딥리뷰

- REVIEW_ID: `DX9EX-AI2-P0-ALLSCREEN-20261008-1957KST`
- 요청: 기존에 발생한 실기 화면 문제 **전체**를 원본 모드 / EXE producer / 현재 소스 / CI / 사용자 런타임 증거로 재점검.
- 검토 시작(실측): 2026-10-08 19:57:25 KST. 시간 기록과 실제 진행은 별도 검증하며 30분 진행/완료를 미리 선언하지 않음.
- branch `vr-d3d9ex-focus`; 시작 HEAD `444609d872c2a319d42032b1afbb8b9dcd059472` (docs only); 검사한 최종 변경 소스 SHA `9d01dd3eb871be4a439457247596a60cb5c8f74b`.
- 최초 CI 정합 확인(4/4): DX9Ex Active `37766111828` SUCCESS, EXE HUD Inspector `37766111701` SUCCESS, DX9Ex Full Source Impact `37766111648` SUCCESS, Domain Isolation `37766111726` SUCCESS. 정확 코드 SHA 일치. 이는 **실기 광학 PASS가 아님**.
- `RUNTIME_VALIDATION=UNTESTED`; 이전 00519 USER_RUNTIME_FAIL 유지. 동일 소스에 대한 1000/5000 반복 정적검사 없음.
- 기준: `AGENTS.md`, `docs/VR_P0_VISUAL_COMPOSITION_CONVERGENCE.md`, `docs/VR_REGRESSION_KNOWLEDGE.json`, `docs/VR_HUD_SEMANTIC_BASELINE.md`, 이전 `AI2_DX9EX_RUNTIME_EVIDENCE_DEEP_RESEARCH_20261008.md`, 00519/00557/00558 및 현재 active renderer.

## 진행 체크포인트
- [x] C0: 인증된 GitHub 현재 브랜치, 원본 리그레션 기록, 정확 SHA 4종 CI 완료 재검증.
- [ ] C1: 사용자 기존 항목 총목록 및 증상·정확 원본 game producer 소유권 대조.
- [ ] C2: SceneEffect/lens/SkyGlow/그림자, WorldBillboard/rank 1~5위, HUD/글리프/+TIME/골인, 메뉴/YES-NO/F11/texture, recenter, 프레임 페이싱 소스 정적 분기 대조.
- [ ] C3: 새로운 소스 위험 여부를 기존 fix·negative test와 대조해 false-positive 배제. 발견 항목은 정확 수정 지점과 재현 가능한 반증 조건 기입.
- [ ] C4: 최종 triage·필수 CI/실기 검증·인계. 별도 요청 또는 확실한 소스 버그 없이는 넓은 휴리스틱 수정 금지.

## C0 상태
- 역사상 실기 오류를 source/static success만으로 지우지 않는다. 기존 결과 재사용 우선.
- 원본 binary manifest: `OR2006C2C.EXE` pinned `68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3`, manifest 계약 103개, explicit HUD CALL 71개.
- GitHub checkpoint: 다음 조사내용은 이 파일을 순차 업데이트해 세션 유실을 방지한다.

## C1 — 원본·증상 행렬
PENDING

## C2 — 코드 경로 감사
PENDING

## C3 — 반증·남은 결함
PENDING

## C4 — 최종 판정과 다음 변경
PENDING
