# DX9Ex 자동검토 — 렌즈플레어 단일 주제 (2026-10-27)

이 지시는 2026-10-27 사용자 요청에 따른 DX9Ex C 슬롯의 최우선 범위 고정 정책이다. 예전 +TIME/GOAL/F11/sky/성능/파티클/HUD 종합 검토 지시보다 우선한다. 신규 TASK_ID, retry, 대화 롤오버, 체크포인트 복구에서도 동일하다.

MODE=DX9EX_REVIEW_ONLY
REVIEW_SUBJECT=LENS_FLARE_ONLY
TARGET_BRANCH=vr-d3d9ex-focus
CODE_CHANGE=FORBIDDEN
BASELINE=R26+HUD
BASELINE_SHA=0cff83cf509c2acd6f3391b3a46c4dec1403a0d9
CONTINUOUS_INVESTIGATION=ON

## 단일 목표와 관찰된 증상

- **렌즈플레어만** 조사한다. 렌즈플레어 중심 광점/원형 halo/glow/rays/ghost 및 렌즈플레어 전용 텍스처·draw·host composite·OpenXR eye 제출 경로가 대상이다.
- 사용자 관찰: 화면 중앙 렌즈플레어가 둘로 보이거나, 깊이감 없이 head-follow/head-lock처럼 보인다. 이는 사용자 보고이며 현재 SHA의 재현/원인은 미확정이다.
- 플레어가 원래 하나의 emitter에서 나온 것인지, 각 눈에서 보여야 하는 정상 stereo 두 draw가 합성 과정에서 중복 표현된 것인지 구분한다. **양안 draw 2회 자체를 오류로 단정하지 않는다.**
- 별도의 태양 원판/sky/광원 스파이크는 플레어 발생 또는 합성 경로와 직접 연결되는 부분만 읽는다. +TIME, GOAL, F11, ESC, 순위, 라이벌, UI, 드라이버뷰, culling, FPS 최적화 등은 **독립 조사·새 finding·NEXT_REVIEW 주제로 선택 금지**. 공유 코드가 원인 후보일 때도 렌즈플레어 영향만 분석한다.

## 연속 재검토 — 반복이 아니라 원인 수렴

1. GitHub 최신 대상 HEAD, AGENTS.md(있을 경우), 과거 렌즈플레어 관련 작업/Issue/REA/로그/실기 관찰, 최근 docs/reviews/dx9ex/automation 문서를 읽고 기존 가설·검증 결과를 인수한다. 파일 경로를 찾지 못하면 실제 경로를 재탐색하되 없다고 단정하지 않는다.
2. **같은 렌즈플레어를 다음 실행에서도 계속 재검토한다.** 새 주제를 억지로 고르지 않는다. 미해결 가설 하나를 선택해 이전과 **다른 검증 관점·호출 경계·증거**로 시험한다. 이전 가설을 반박하거나 강화하는 것도 유효한 성과다.
3. 분석 경로: emitter/game light position -> flare producer/texture or SpriteNode -> 2D/3D 판정·semantic owner/lifetime -> D3DX Sprite/DP/DIP/XYZRHW/FlatPerspective -> batch/queue flush -> L/R view/projection/viewport -> OpenXR eye 제출/host composition -> Present. 실제로 존재하는 함수·실제 호출자·결정 분기·state 저장/복원만 근거로 연결한다.
4. **원인 경쟁 가설을 구분**한다: (A) game-origin flare sprite 2회 생성, (B) D3DX/queue 재제출, (C) left/right eye projection 또는 XYZRHW 화면고정, (D) center flare texture/halo가 별도 pass에서 중복, (E) host layer/composite 재사용, (F) source position과 HMD-local 변환 오류. 증거가 없는 후보를 원인으로 확정하지 않는다.
5. R26+HUD/최근 focus HEAD/기존 정상·불량 화면 보고를 정확한 코드·상태 차이로 비교한다. 가능하면 실제 로그의 draw ID·eye·texture·state·frame sequence 증거를 확인한다. 소스 정적 추론과 HMD 실기 결과는 엄격히 분리한다.
6. 검토 기록에는 **HYPOTHESIS_LEDGER**(ID, 상태 OPEN/SUPPORTED/REFUTED/BLOCKED, 이전 증거, 이번 새 증거, 반증 조건), **SOURCE_TRACE**(파일/함수/가능한 라인), **EVIDENCE_GAPS**, **NEXT_FALSIFICATION_TEST**를 넣는다. 분기별 예상 화면 결과와 예상 로그 지표를 구체적으로 적어 다음 TASK가 실제로 이어받게 한다.
7. 새로운 결함이 입증되지 않아도 유의미하게 검토한 근거가 있다면 NEW_FINDING=NONE으로 기록한다. 불확실한 가설을 매번 '새 발견'으로 포장하거나 같은 결론을 복사해 독립 성과라고 주장하지 않는다. 기존 문서의 단순 재서술은 금지한다.
8. **NEXT_REVIEW는 반드시 LENS_FLARE:<미해결 함수/분기/검증명>**으로 설정한다. 렌즈플레어 원인 입증 전까지 다른 오류로 주제를 돌리지 않는다. 확정 후에도 사용자 변경 지시 전에는 렌즈플레어 관련 회귀·반증을 계속 조사한다.

## 변경·기록 제한

- DX9Ex 게임/런타임 source, C++, HLSL, CMake, workflow, config, 실행물, 브랜치, 릴리스 수정/생성/병합 금지. 이 자동화는 소스 수정 작업이 아니다.
- 위험한 B9200 post-CALL/+5 hook 재도입, R84 기본값 승격, R26+HUD 기준 자동 교체 금지.
- 실제 수정이 타당해 보이면 PATCH_CANDIDATE_ONLY에 파일/함수/정확한 조건/근거/최소 변경 제안/반증조건/회귀 경계만 작성한다. 패치를 적용하지 않는다.
- 매 **새** TASK_ID의 실제 검토 결과는 `docs/reviews/dx9ex/automation/<TASK_ID>.md` **한 파일만** 새로 만들어 docs-only commit에 정확히 `[AUTO:<TASK_ID>]` 태그를 남긴다. 기존 TASK_ID의 성공 커밋을 재작성·중복 채점하지 않는다. 기록 외 소스·설정 경로 변경 금지.
- AI 점수는 검토 중에 자동으로 부풀리지 않는다. 이전과 구별되는 실제 검증 결과가 없는 단순 반복/rollover/retry는 새 성과로 계산하지 않는다.
- 외부 CI 성공은 Quest3/VDXR 동작 확인이 아니다. 실기 없으면 RUNTIME_VALIDATION=UNTESTED, CODE_CHANGE=NO. 어떠한 수치/화면 정상 판정도 조작하지 않는다.

## 매 실행 종료 보고

SOURCE_HEAD=<실제 조회 SHA>
REVIEW_SCOPE=LENS_FLARE_ONLY
HYPOTHESIS_LEDGER=<검토한 가설과 상태>
NEW_FINDING=<검증 결과 또는 NONE>
SOURCE_TRACE=<실제 확인한 파일/함수/라인/경로>
EVIDENCE=<source/disasm/log/user-report 별 증거>
EVIDENCE_GAPS=<런타임/해석 미확정 사항>
NEXT_FALSIFICATION_TEST=<다음에 다른 관점으로 재검증할 방법>
PATCH_CANDIDATE_ONLY=<수정 후보 또는 NONE>
REGRESSION_RISK=<회귀 위험>
GITHUB_RECORD=<docs-only 경로/commit>
CODE_CHANGE=NO
NEXT_REVIEW=LENS_FLARE:<구체적 하위 문제>
TASK_ID=<현재 TASK_ID>
RESULT_SHA=<실제 docs-only commit SHA>
AUTOMATION_VALIDATION=<PASS/PENDING/FAIL>
RUNTIME_VALIDATION=UNTESTED
