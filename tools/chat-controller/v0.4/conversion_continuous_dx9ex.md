# DX9Ex 연속 자동검토 — REVIEW ONLY (2026-10-20)

이 지시는 과거 SOURCE_IMPLEMENTATION_70_PERCENT, DEVELOPMENT_FIRST, C0~C6 자동소스개발 지시를 모두 대체한다.

MODE=DX9EX_REVIEW_ONLY
CONTINUOUS_REVIEW=ON
CODE_CHANGE=FORBIDDEN
TARGET_BRANCH=vr-d3d9ex-focus

30분 롤오버/연속 실행은 **개발 재개 주기**가 아니라 화면오류·최적화 검토를 이어가는 주기다.
C 슬롯은 계속 자동 배정될 수 있지만 게임 소스, 빌드 설정, workflow, config를 스스로 고치지 않는다.

매 실행:
1. GitHub 최신 vr-d3d9ex-focus HEAD와 직전 `docs/reviews/dx9ex/automation/` 기록을 읽는다.
2. 직전 실행과 다른 렌더링 경로, 상태경계, 화면 증상 또는 성능 병목을 하나 이상 선택한다.
3. 관련 source/REA/disassembly/runtime evidence를 따라 호출부터 최종 draw/Present/OpenXR까지 시뮬레이션한다.
4. 확인된 사실과 가설을 분리하고 반증 조건을 적는다.
5. 수정이 필요해 보여도 실제 코드는 변경하지 않고 `PATCH_CANDIDATE_ONLY`로만 기록한다.
6. `docs/reviews/dx9ex/automation/<TASK_ID>.md` docs-only 결과를 만들고
   커밋 메시지에 정확히 `[AUTO:<TASK_ID>]`를 포함한다.
7. 동일 finding의 반복 기록은 피한다. 새 finding이 없으면 `NEW_FINDING=NONE`과
   이번에 새로 검토한 경로 및 `NEXT_REVIEW`를 남긴다.
8. Quest 3/VDXR 실기 증거가 없으면 `RUNTIME_VALIDATION=UNTESTED`를 유지한다.

절대 금지:
- C++/HLSL/source 자동 구현 또는 수정.
- CMake/workflow/config 수정.
- source patch/refactor, merge, update_ref, feature branch 생성, release/package.
- R84 재승격 또는 R26+HUD 기준 자동 교체.
- 위험한 B9200 post-CALL/+5 hook 재도입.
- CI 실패를 이유로 게임 소스나 검증 코드를 자동 수리하는 행위.
- 분석 결과를 runtime PASS로 과장하는 행위.

기준:
- R26+HUD baseline: `0cff83cf509c2acd6f3391b3a46c4dec1403a0d9`
- recent result HUD candidate: `aab9e02bcb2ad2e6253840e6267e5c5ad5040854`

우선순위:
+TIME/result HUD -> actual final GPU API -> D3DX batch ownership/queue epoch ->
viewport/game-pixel/XR extent -> non-zero eye cant -> rank/rival -> lens/sky/F11/ESC ->
StateBlock/Reset/device-loss -> frame pacing/draw/copy/wait/resource churn ->
sand/particle/culling optimization.

기존 TASK_ID가 docs-only result commit까지 끝났다면 같은 분석을 반복하지 않는다.
Gate가 아직 관찰 중이면 기존 result SHA를 유지해 확인하고 게임 소스 수리로 전환하지 않는다.
새 TASK_ID는 다음 독립 검토 범위에 사용한다.

최종 보고에는 반드시 다음을 포함한다:
SOURCE_HEAD
REVIEW_SCOPE
NEW_FINDING
EVIDENCE
PATCH_CANDIDATE_ONLY
REGRESSION_RISK
GITHUB_RECORD
CODE_CHANGE=NO
RUNTIME_VALIDATION=UNTESTED
NEXT_REVIEW
TASK_ID
RESULT_SHA
AUTOMATION_VALIDATION
