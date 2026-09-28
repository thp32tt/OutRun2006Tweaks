OutRun 2006 한글화 A 작업을 진행해줘. 역할은 실제 한글화 제작 + 수정이다.

작업 기준은 GitHub 저장소 thp32tt/OutRun2006Tweaks의 korean-localization-clean 브랜치 최신 HEAD 하나뿐이다. N100의 로컬 clone/worktree/작업파일, GPT Library, 과거 대화의 진행률을 작업 기준이나 수정 대상으로 사용하지 마. GitHub를 직접 읽고 수정할 수 있는 현재 사용 가능한 GitHub 연결/도구를 사용해.

시작 즉시 docs/KOREAN_LOCALIZATION_AUTOMATION_CONTRACT.md를 먼저 읽고, 그 문서가 지정하는 최신 기준 문서와 localization/WORKLOG.md, localization/progress.json, localization/resume_state.json, localization/graphics/README.md, localization/graphics/ORIENTATION_POLICY.md를 읽어 현재 상태를 재구성해. 현재 Git HEAD의 규칙이 이 프롬프트보다 우선한다.

이미 완료된 작업은 반복하지 말고 미완료 또는 REWORK 대상부터 실제 제작/수정해. 그래픽은 원본 캔버스/영역을 1픽셀도 벗어나지 않게 하고 잘림, 저해상도, DDS 속성, alpha/투명도, 배경 훼손, 오교체를 검사해. 실제 변경이 있으면 상태/WORKLOG를 갱신하고 같은 korean-localization-clean 브랜치에 commit/push한 뒤 SHA를 확인해.

GitHub 읽기/쓰기 권한이 없으면 N100 로컬 저장소로 우회하지 말고 실패 원인을 정확히 보고해. VR/FFB/DX9Ex/DX11/DXVK 작업과 빌드는 하지 마.