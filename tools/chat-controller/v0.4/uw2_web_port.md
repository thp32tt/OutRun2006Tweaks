# 대항해시대 2 — 원작 그대로 브라우저 웹포팅 전용 C 슬롯
MODE=UW2_ORIGINAL_FIDELITY_WEB_IMPLEMENTATION
TARGET_REPO=thp32tt/ai-dev-lab
TARGET_BRANCH=uw2-web-port
SCHEDULE_KST=00,30
TASK_ID_POLICY=REUSE_UNTIL_TERMINAL
REVIEW_ONLY=NO

## 절대 목표
유저 소유 한국어판 대항해시대 2 원작의 게임 동작을 변경하거나 재해석하지 않고, 기존 DOS 프로그램의 실제 실행 순서·화면·키 입력·전투·항해·경제·이벤트·세이브·오디오를 브라우저에서 재현한다. 이는 모드나 리메이크가 아니라 포팅이다. 기존 포팅 프로젝트의 실제 진척부터 확인하고 이어서 구현한다.

## 실행 방법
1. 연결된 GitHub 도구로 thp32tt/ai-dev-lab@uw2-web-port 최신 HEAD, README/AGENTS, 포팅 계획, 최신 web/ 소스, tests/ 및 이전 수행 이력을 확인한다. GitHub가 SSOT이다. OutRun2006Tweaks 원본 게임 코드나 DX9Ex/DX11/DXVK 브랜치는 수정하지 않는다.
2. 기존 문서에 전체 원본 역어셈블리 포팅 계획이 있으면 그대로 따르고, 없거나 누락되었으면 단계별 원작 실행 호출/자산·세이브·렌더링/입력/오디오 경계를 근거와 함께 GitHub에 먼저 기록한다. '계획 문서만 작성'으로 자동 개발 TASK를 완료하지 않는다.
3. 원작 부팅: OPEN.EXE 한국어판 오프닝 12장면/OPGRAPH/GRAPH/BGM → 종료 또는 Enter 건너뛰기 → MAIN.EXE 시스템 메뉴 → 원작 항구·세계지도·출항/항해·상점·전투·이벤트·세이브 순서를 실제 원본 자료와 코드로 역추적한다. 이전 구현의 모듈을 훼손하지 않고 아직 빠진 원작 기능을 하나씩 소스에 연결한다.
4. 원본 바이너리, DOS 데이터, 디스어셈블리, 데이터 매핑 등의 직접 증거와 현재 코드의 차이를 찾고 최소 패치를 실제 웹 소스(web/)에 구현하며 가능한 회귀 테스트를 추가한다. 추정한 부분은 정확한 원작 구현으로 포장하지 않는다. 정적 검토와 실제 브라우저 검증을 구분한다.
5. 작업 중 사용자 승인 대기로 멈추지 말고 미완료 범위를 이어간다. 롤오버/재시도는 원래 TASK_ID 유지. 다른 작업자의 커밋을 덮어쓰거나 force push하지 않는다. 각 신규 성과에는 실제 변경 파일과 재현·검증 결과를 남긴다.
6. GitHub web/ 의 JavaScript/TypeScript/HTML/CSS 중 최소 하나의 **실제 게임 구현 변경**과 필요한 회귀가 포함된 커밋에 정확히 `[AUTO:<TASK_ID>]`를 넣는다. 컨트롤러는 해당 tagged commit의 web/ 소스 변경과 브랜치 조상 관계를 확인해야만 완료로 인정한다. 문서·검토·상태·테스트만 있는 커밋은 완료가 아니다.
7. 자동 빌드·브라우저·원작 실행을 실제 수행하지 않았으면 성공으로 보고하지 말고 UNTESTED/UNKNOWN으로 구분한다. 콘텐츠·자산 저작권을 준수해 원본 게임 바이너리나 저작권 파일을 공개 커밋에 넣지 않는다.

## 종료 출력
TASK_ID=<current task>
SOURCE_HEAD=<verified GitHub branch SHA>
RESULT_SHA=<source-changing tagged commit SHA>
IMPLEMENTED=<actual user-visible behavior>
FILES_CHANGED=<concrete paths>
TESTS_RUN=<actual commands and results or UNTESTED>
AUTOMATION_VALIDATION=<actually observed evidence>
RUNTIME_VALIDATION=<actual browser/asset evidence or UNTESTED>
NEXT_ACTION=<next original fidelity gap>
