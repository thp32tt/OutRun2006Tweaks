# 대항해시대 2 — 원작 그대로 브라우저 웹포팅 전용 C 슬롯
MODE=UW2_ORIGINAL_FIDELITY_WEB_IMPLEMENTATION
IMPLEMENTATION_STRATEGY=FULL_DECOMPILE_FIRST_IR_HYBRID_JS_WASM
FIRST_WORK_ITEM=P1-BATCH-001
TARGET_REPO=thp32tt/ai-dev-lab
TARGET_BRANCH=uw2-web-port
SCHEDULE_KST=00,30
TASK_ID_POLICY=ONE_ID_UNTIL_P0_P9_ORIGINAL_GAME_ACCEPTANCE
PARTIAL_COMMIT_IS_TERMINAL=NO
COMPLETION_GATE=P0_P1_P2_P3_P4_P5_P6_P7_P8_P9_FULL_ORIGINAL_REFERENCE_AND_BROWSER_ACCEPTANCE
REVIEW_ONLY=NO

## 절대 목표
유저 소유 한국어판 대항해시대 2 원작의 게임 동작을 변경하거나 재해석하지 않고, 기존 DOS 프로그램의 실제 실행 순서·화면·키 입력·전투·항해·경제·이벤트·세이브·오디오를 브라우저에서 재현한다. 이는 모드나 리메이크가 아니라 포팅이다. 기존 포팅 프로젝트의 실제 진척부터 확인하고 이어서 구현한다.

## 공식 최신 우선순위 (2026-10-31 개정)

- 공식 SSOT는 target branch의 `uw2-web/docs/ORIGINAL_DOS_TO_WEB_DISASSEMBLY_MASTER_PLAN_20261031.md` 3-A절이다. 기존 P0~P9 인수 기준 및 전체 완성 전 중지 금지는 유지하되, 작업 우선순위를 **REA/Ghidra 전체 배치 디컴파일 → full-code 함수/기본블록/간접호출/갭 계량 → 8086 실행 의미 코어·공통 IR → JS/WASM native block + instruction interpreter fallback → DOS 원본 differential → 전체 화면·전투·항해·이벤트·세이브**로 변경한다.
- 일괄 추출은 **미확인 코드를 제거하지 않고** 모듈별 SHA·원본 raw/REA 주소·함수/기본블록·xref/CFG·미해결 분기를 기록해야 한다. REA/Ghidra가 모든 함수에서 실행가능한 C 소스를 만들어 준다고 가정하지 않는다. 실패/추정/UNKNOWN은 별도 통계로 기록한다.
- N100은 기존 분석 프로젝트의 REA/Ghidra 실제 실행 및 원본 read-only 검증에 필요한 최소 작업만 사용하고 새 clone/worktree/불필요한 반복 전체 분석을 금지한다. 공개 GitHub에 대량 디컴파일 원문이나 원작 EXE·이미지·음악을 올리지 않는다. 분석기·IR 런타임·테스트는 자체 작성 소스로 커밋한다.
- P1-BATCH-001: 전체 분석 프로젝트와 지원 인터페이스 조사 후 모듈별 범위 manifest, chunk-based batch export, 누락/실패/중단 후 재개 검사기 + synthetic test 구현. 이어 P1-BATCH-002 MAIN/OPEN 전체 코드·gap·간접호출 추출/검증, KOEI/END/GRPDRV/FMDRV 조사; P3-CORE-001 DOS 부팅→OPEN→MAIN 최소 실제 분기를 공유 상태 코어에서 실행하고 참조 trace와 대조한다.
- 기존 검증된 웹 포팅 기능은 보존한다. 초기 P1 일괄 디컴파일 결과만으로 게임 기능 완성을 선언하거나 매 예약에서 같은 함수 분석을 반복하지 않는다.

## 종료 금지 / 연속 실행 계약

- **하나의 소스/도구/회귀 기능 커밋은 절대 작업의 종료가 아니다.** 부분 구현마다 GitHub에 material commit하고, 현재 TASK_ID와 P0~P9 마스터 계획을 계속 유지한다. 커밋/테스트 PASS/작업 보고 뒤에 이어서 다음 미완료 함수·상태·화면을 개발한다.
- 원본 DOS 실행과 브라우저가 전체적으로 일치하고 P0~P9 모든 단계, 여섯 인물 시작~엔딩, 세이브/불러오기, 항해, 항구, 경제, 전투, 이벤트, 그래픽/입력/음악 검증 및 최종 인수가 모두 통과하기 전에는 `TASK_COMPLETE`/`DONE`/`TERMINAL`을 출력·주장하지 않는다.
- C 슬롯 매시 00분·30분(KST)은 **동일 진행 작업 재개/체크포인트/롤오버 예약**이다. 새 TASK_ID를 생성하거나 이미 완료한 단계를 처음부터 다시 분석하지 않는다. 대화가 끝나거나 컨텍스트가 차면 GitHub 증거 및 마스터 계획을 읽고 즉시 미완료 작업을 이어간다.
- P0~P9 게이트가 일부 PASS인 경우에도 개발을 종료하지 않는다. 원본 자료 부족/HOLD/UNTESTED는 증거 부족으로 기록하되, 다른 구현 가능한 미완료 항목을 계속한다.
- 모든 진행 보고에는 진행 단계, 실제 source SHA, 새 소스/테스트 변경, 실패·미검증, 다음 원본 주소/함수/화면까지 남긴다. 작업 완료 보고 대신 `FULL_GAME_STATUS=IN_PROGRESS`와 `NEXT_ACTION`을 제공한다.
- 전체 기능 완성 후에만 `uw2-web/docs/ORIGINAL_FULL_GAME_ACCEPTANCE.json`에 P0~P9 증적을 모으고 실제 DOS 원본 비교·브라우저 end-to-end·6인 엔딩·세이브·화면·음악 확인 및 최종 검수를 거친다. 컨트롤러의 기본 최종 완료 허용값은 OFF다.

## 실행 방법
1. 연결된 GitHub 도구로 thp32tt/ai-dev-lab@uw2-web-port 최신 HEAD, README/AGENTS, `uw2-web/docs/ORIGINAL_DOS_TO_WEB_DISASSEMBLY_MASTER_PLAN_20261031.md`, 최신 `uw2-web/` 실제 원작 역어셈블리 도구·웹포팅 소스 및 tests/ 이력을 확인한다. GitHub가 SSOT이다. OutRun2006Tweaks 원본 게임 코드나 DX9Ex/DX11/DXVK 브랜치는 수정하지 않는다.
2. 최신 3-A절 전체 디컴파일 우선 계획을 따른다. 계획이 이미 있으면 새 문서 반복 작성 대신 P1-BATCH-001 진행 위치에서 **배치 디컴파일 도구 소스 + 합성 회귀**를 구현하고, 가능한 기존 REA/Ghidra 프로젝트에서 실제 검증한다. 계획 문서만으로 자동 개발 TASK를 완료하지 않는다.
3. 원작 정적 전체 호출 흐름을 KOEI.COM/OPEN.EXE/MAIN.EXE/END.EXE/GRPDRV.EXE/FMDRV.COM 원본 SHA에 연결해 batch export하고, 미해결 near/far/indirect 분기/메모리 영역을 빠짐없이 목록화한다. 그 증거를 이용해 OPEN 12장면→MAIN 시스템 메뉴→항구·항해·경제·전투·이벤트·세이브·엔딩을 공통 IR/JS/WASM 실행 엔진에 이어 붙인다. 기존 구현 훼손 금지.
4. 추출 결과→원본 바이트→8086 명령 의미→공통 IR→JS/WASM 실행/폴백→DOS 원본 trace의 연결을 먼저 구현한다. 새 함수·메모리·DOS interrupt/OPL/VGA/입력/세이브 경로는 원본 비교와 synthetic 회귀를 따로 남기고 미검증은 HOLD로 처리한다. 구체적인 구현은 `uw2-web/tools/` 또는 `uw2-web/web/` 실제 소스로 커밋한다. 단순 문서·통계 출력만으로 TERMINAL 불가.
5. 작업 중 사용자 승인 대기로 멈추지 말고 미완료 범위를 이어간다. 롤오버/재시도는 원래 TASK_ID 유지. 다른 작업자의 커밋을 덮어쓰거나 force push하지 않는다. 각 신규 성과에는 실제 변경 파일과 재현·검증 결과를 남긴다.
6. GitHub `uw2-web/` 또는 `web/`의 JavaScript/TypeScript/HTML/CSS/Python/C++ 중 최소 하나의 **실제 게임 포팅·원본 디스어셈블리 도구 구현 변경**과 관련 회귀를 묶어 커밋하고 정확히 `[AUTO:<TASK_ID>]`를 남긴다. 컨트롤러가 원격 HEAD와 material commit을 확인하면 **중간 진척만 기록**한다. 그 직후 다음 미완료 원본 기능을 계속 구현한다. 문서·검토·상태·테스트 전용 커밋은 포팅 완료로 계산하지 않는다.
7. 자동 빌드·브라우저·원작 실행을 실제 수행하지 않았으면 성공으로 보고하지 말고 UNTESTED/UNKNOWN으로 구분한다. 콘텐츠·자산 저작권을 준수해 원본 게임 바이너리나 저작권 파일을 공개 커밋에 넣지 않는다.

## 각 실행/롤오버 시 진행 출력 (전체 완료 선언 금지)
TASK_ID=<current task>
SOURCE_HEAD=<verified GitHub branch SHA>
RESULT_SHA=<source-changing tagged commit SHA>
IMPLEMENTED=<actual user-visible behavior>
FILES_CHANGED=<concrete paths>
TESTS_RUN=<actual commands and results or UNTESTED>
AUTOMATION_VALIDATION=<actually observed evidence>
RUNTIME_VALIDATION=<actual browser/asset evidence or UNTESTED>
FULL_GAME_STATUS=IN_PROGRESS
P0_P9_GATE=<stage-by-stage verified / pending / blocked>
NEXT_ACTION=<next P1 batch range / IR block / original differential gap>
