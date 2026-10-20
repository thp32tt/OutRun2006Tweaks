# DX9Ex 자동검토 전용 — 2026-10-20 사용자 최신 지시

이 문서는 이 파일에 있던 모든 과거 DX9Ex 자동개발·자동소스수정·자동리팩터링·자동승격 지시보다 우선한다.

MODE=DX9EX_REVIEW_ONLY
TARGET_BRANCH=vr-d3d9ex-focus
CODE_CHANGE=FORBIDDEN
BASELINE=R26+HUD
BASELINE_SHA=0cff83cf509c2acd6f3391b3a46c4dec1403a0d9
RECENT_RESULT_HUD_CANDIDATE=aab9e02bcb2ad2e6253840e6267e5c5ad5040854

## 목적

DX9Ex C 슬롯은 계속 자동 실행하지만 더 이상 게임 코드를 스스로 개발하거나 수정하지 않는다.
화면오류와 성능·최적화 문제를 찾기 위해 GitHub의 최신 소스, REA/디스어셈블리 자료, 런타임 로그,
과거 정상/불량 빌드와 관련 Issue를 계속 읽고 실제 렌더링 경로를 소스 수준에서 시뮬레이션한다.
새롭고 의미 있는 결과는 GitHub에 **검토 기록만** 남긴다.

## 절대 금지

- production source, C++, HLSL, CMake, workflow, runtime/config 파일 자동 수정.
- 자동 patch/refactor/merge/update_ref/branch 생성/release/package 생성.
- feature branch에서 소스를 고친 뒤 target branch로 자동 승격하는 행위.
- R84 구조최적화를 현재 기본값으로 다시 승격하거나 R26+HUD 기준을 자동 교체하는 행위.
- B9200 post-CALL/+5 등 과거 크래시 원인이 된 위험한 midhook 재도입.
- 근거 없는 SpriteNode blanket HUD 승격, global alpha, IPD/깊이 수치 튜닝.
- 빌드/정적검사 결과를 Quest 3 화면 정상 또는 runtime PASS로 표현.
- 같은 finding을 반복 커밋하거나 같은 Issue 댓글을 반복 작성.

## 허용 작업

- 연결된 GitHub 도구로 vr-d3d9ex-focus 최신 HEAD/AGENTS.md/관련 docs와 Issue를 읽기.
- 관련 소스, REA/Ghidra/디스어셈블리, 기존 런타임 로그와 과거 정상/불량 SHA 비교.
- producer -> semantic registry/replay -> queue -> D3DX/native D3D9 draw ->
  R30/R62 -> left/right eye -> state/projection restore -> Present/OpenXR 제출 경로 시뮬레이션.
- 화면오류 owner/lifetime/state/viewport 경계 분석.
- CPU/GPU draw amplification, duplicate eye draw, copy/resolve/wait, StateBlock/state churn,
  texture/resource churn, particle overdraw, culling, XR cadence 등 최적화 병목 분석.
- 새 finding을 docs/reviews/dx9ex/automation/ 아래 docs-only 기록으로 커밋.
- 수정 필요성이 충분히 입증된 경우 실제 코드는 건드리지 않고 PATCH_CANDIDATE_ONLY로
  정확한 파일/함수/라인 범위/근거/반증 조건/회귀 경계만 기록.

## 매 TASK_ID 수행 절차

1. 현재 vr-d3d9ex-focus HEAD와 AGENTS.md를 다시 읽고, 최근 DX9Ex 자동검토 기록을 확인한다.
2. 이전 기록과 동일한 내용만 반복하지 말고 다른 호출경로·상태경계·성능 병목 또는 미검증 가설을 하나 이상 선택한다.
3. 관련 원본 함수 호출부터 최종 GPU draw/OpenXR 제출까지 가능한 범위를 순차 추적한다.
4. 화면오류는 다음 필드를 분리한다:
   - USER_SYMPTOM
   - STATIC_SOURCE_EVIDENCE
   - DISASM_EVIDENCE
   - RUNTIME_EVIDENCE
   - OWNERSHIP_HYPOTHESIS
   - FALSIFICATION_SIGNAL
   - PATCH_CANDIDATE_ONLY
   - REGRESSION_BOUNDARY
5. 최적화는 MEASURED와 HYPOTHESIS를 구분한다. 실측 로그가 없으면 추정값을 측정값처럼 쓰지 않는다.
6. 결과를 `docs/reviews/dx9ex/automation/<TASK_ID>.md`에 기록한다.
   새 패치 후보가 없더라도 `NEW_FINDING=NONE`과 이번에 실제로 검토한 경로·근거·다음 검토 지점을 기록한다.
7. docs-only 커밋 메시지에 정확히 `[AUTO:<TASK_ID>]`를 포함한다. CI-skip 지시어는 사용하지 않는다.
8. Issue #13/#14/#100 등에는 실제 새 finding이 있을 때만 중복 없이 보강한다.
9. 게임/런타임 소스 변경은 항상 `CODE_CHANGE=NO`로 남긴다.
10. Quest 3/VDXR 실기 검증이 없으면 항상 `RUNTIME_VALIDATION=UNTESTED`다.

## 우선 검토 범위

- +TIME 텍스트/숫자의 양안 분리, 복시, head-lock.
- GOAL/finish stage progress, percent, time, title/glyph의 중복/헤드 추종.
- 실제 visible result element의 최종 D3D9 API 경로가 DIP/FVF 0x142인지, 다른 Draw 경로가 섞이는지.
- D3DX deferred Sprite batch owner, source scope, queue node/queue epoch와 semantic lifetime.
- cached shader identity와 live GetVertexShader authority.
- game-pixel/desktop viewport/XR eye extent 좌표 변환과 XYZRHW 처리.
- OpenXR head-local eye orientation과 non-zero eye cant가 R26 finite HUD에 정확히 반영되는지.
- 차량 순위/라이벌의 이전 정상 경로와 현재 owner/depth 차이.
- lens flare, sky, ESC/F11/menu, 시작 shadow 등 stereo/head-lock 오류.
- StateBlock, projection/world/view 복원, Reset/ResetEx/device-loss/host reconnect.
- frame pacing, draw amplification, copy/resolve/wait, resource churn.
- 모래/파티클 overdraw 및 밀집 건물 구간 성능.
- VR 시야에 맞는 culling 범위와 desktop-resolution/VR-viewport 불일치.

## 보호 기준

- R26+HUD를 현재 비교 기준으로 사용한다.
- 정상 동작 중인 메뉴/ESC/F11/라이벌/차량순위/sky/lens/input/FFB/recenter 등은
  해당 검토에서 실제 회귀 증거가 없으면 수정 대상으로 승격하지 않는다.
- 최근 result HUD 후보 SHA는 비교 자료일 뿐 HMD PASS가 아니다.
- 과거 R84/legacy 문서는 증거 자료로 읽을 수 있지만 자동 구현 지시로 해석하지 않는다.

## 종료 형식

SOURCE_HEAD=<sha>
REVIEW_SCOPE=<scope>
NEW_FINDING=<summary or NONE>
EVIDENCE=<source/disasm/log/docs evidence>
PATCH_CANDIDATE_ONLY=<candidate or NONE>
REGRESSION_RISK=<risk>
GITHUB_RECORD=<docs-only path/commit>
CODE_CHANGE=NO
AUTOMATION_VALIDATION=<PASS/PENDING/FAIL>
RUNTIME_VALIDATION=UNTESTED
NEXT_REVIEW=<next distinct scope>

TASK_ID=<TASK_ID>
RESULT_SHA=<docs-only result sha>
AUTOMATION_VALIDATION=<value>
RUNTIME_VALIDATION=UNTESTED
