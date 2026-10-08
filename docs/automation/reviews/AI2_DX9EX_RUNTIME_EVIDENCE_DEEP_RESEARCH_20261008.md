# DX9Ex Quest 3 실기 회귀 — 원본·바이너리·전체 소스 교차 검토 (2026-10-08)

> 상태: **IN_PROGRESS / EVIDENCE_RESEARCH_ONLY**. 이 파일은 채팅 중간중간 GitHub에 저장하는 내구성 체크포인트입니다. **이번 작업에서 런타임 소스·빌드 설정은 수정하지 않습니다.**
> 기준: vr-d3d9ex-focus, Quest3/VDXR 실기 회귀. RUNTIME_VALIDATION=UNTESTED. 진단 가설을 수정 완료로 쓰지 않습니다.

## Checkpoint 0 — 조사 범위 및 방법 (persisted)
- 목적: 렌즈플레어, +TIME 연장, 체크포인트·골인기록·결과화면, 흰색 HUD·6th/6, 메뉴/YES-NO/화살표, 라이벌·차량 순위 마커(4~5위), F11 메뉴, 차량선택 텍스처, 시작 그림자, 재중앙정렬과 밀집·모래·연기 프레임 저하 등 기존 실기 오류.
- 증거 우선순위: emoose/OutRun2006Tweaks 원본 hooks/주소 → 포크 과거 브랜치와 의미 계약 → canonical EXE 디스어셈블리/XREF/byte 계약 및 HUD Inspector → 현재 생산자·SpriteNode·queue·R29/R30/R31/R33·OpenXR host → 정확 SHA 정적·빌드 게이트 → 최후 실기.
- 각 결함마다 증상 / 원본 호출자·정확 주소 / 현재 소스 경로 / 최소 가설 / 반증 / 영향 범위 / 정적 재현·결함주입 / 실기에서만 판단할 항목을 기입.
- 기존 VR_REGRESSION_KNOWLEDGE.json, VR_PROBLEM_HISTORY.md, VR_P0_VISUAL_COMPOSITION_CONVERGENCE.md, VR_HUD_SEMANTIC_BASELINE.md, VR_BINARY_CONTRACT.json, 00519 실기 실패/00557·00558 검증 및 Issue #13/#14와 중복 대조.
- 정적 PASS ≠ 실기 PASS. 1000/5000 반복 검사는 재가동하지 않으며 실제 변경 SHA별 관련 검사만.

## Checkpoint 1 — 원본·레거시 소스 (PENDING)

## Checkpoint 2 — canonical EXE / disassembly / producer map (PENDING)

## Checkpoint 3 — 런타임 경로와 결함별 원인·반증 (PENDING)

## Checkpoint 4 — 수정 순서·검증 행렬·최종 인계 (PENDING)

## 변경·출처
- 중간 체크포인트를 동일 파일의 개별 GitHub 커밋으로 업데이트하고 각 파일 URL 또는 SHA를 명시합니다.
- 빌드/실기 수행 없음. 소스 변경 없음.