OutRun 2006 한글화 B 작업을 진행해줘. 역할은 추가 제작 + 전수 1차 QA + 즉시 재작업이다.

작업 기준은 GitHub 저장소 thp32tt/OutRun2006Tweaks의 korean-localization-clean 브랜치 최신 HEAD 하나뿐이다. N100의 로컬 clone/worktree/작업파일, GPT Library, 과거 대화의 진행률을 작업 기준이나 수정 대상으로 사용하지 마. GitHub를 직접 읽고 수정할 수 있는 현재 사용 가능한 GitHub 연결/도구를 사용해.

시작 즉시 docs/KOREAN_LOCALIZATION_AUTOMATION_CONTRACT.md 및 그 계약이 지정한 기준 문서, localization/WORKLOG.md, localization/progress.json, localization/resume_state.json, localization/graphics/README.md, localization/graphics/ORIENTATION_POLICY.md를 읽어. A의 최신 Git 결과와 기존 승인후보를 원본과 비교해 누락/오역/문맥/용어, 깨진 한글, 글자 잘림, 원본 영역 1픽셀 초과, 해상도 저하, DDS 포맷/mipmap/alpha/투명도, 배경 훼손, 중복/오교체를 전수 점검해.

문제를 발견하면 가능한 항목은 즉시 수정하고, 미완료 항목도 계속 제작해. 통과/재작업 상태와 WORKLOG를 갱신하고 실제 변경이 있으면 같은 korean-localization-clean 브랜치에 commit/push 후 SHA를 확인해.

GitHub 읽기/쓰기 권한이 없으면 N100 로컬 저장소로 우회하지 말고 실패 원인을 정확히 보고해. VR/FFB 및 빌드는 하지 마.