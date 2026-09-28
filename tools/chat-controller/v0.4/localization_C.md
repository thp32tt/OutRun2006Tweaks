OutRun 2006 한글화 C 작업을 진행해줘. 역할은 최종 전수 QA + 승인 + 필요한 수정 + Git 상태 정리다.

작업 기준은 GitHub 저장소 thp32tt/OutRun2006Tweaks의 korean-localization-clean 브랜치 최신 HEAD 하나뿐이다. N100의 로컬 clone/worktree/작업파일, GPT Library, 과거 대화의 진행률을 작업 기준이나 수정 대상으로 사용하지 마. GitHub를 직접 읽고 수정할 수 있는 현재 사용 가능한 GitHub 연결/도구를 사용해.

시작 즉시 docs/KOREAN_LOCALIZATION_AUTOMATION_CONTRACT.md 및 그 계약이 지정한 최신 기준 문서와 WORKLOG/progress/resume/graphics 규칙을 읽어. A/B 최신 결과와 기존 승인후보를 원본과 최종 대조하고, 의미/문맥/용어, 누락, 한글 깨짐, 글자 잘림, 원본 영역 1픽셀 초과, 원본 크기/해상도, DDS 포맷/mipmap/alpha/투명도, 배경 훼손, 오교체, 고해상도 GUI 보존을 검증해.

PASS만 기존 승인 구조에 반영하고 실패 항목은 REWORK로 기록해. QA 중 발견한 문제는 가능한 경우 즉시 수정해. 상태/WORKLOG/report를 최신화하고 실제 변경이 있으면 같은 korean-localization-clean 브랜치에 commit/push하여 SHA까지 확인해.

GitHub 읽기/쓰기 권한이 없으면 N100 로컬 저장소로 우회하지 말고 실패 원인을 정확히 보고해. VR/FFB 및 빌드는 하지 마.