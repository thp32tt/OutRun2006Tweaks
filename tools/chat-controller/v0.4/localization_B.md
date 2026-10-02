OutRun 2006 한글화 B 작업을 진행해줘. 역할은 생산 LANE B + self-QA다.

상태·진행·QA의 SSOT는 GitHub 저장소 thp32tt/OutRun2006Tweaks의 korean-localization-clean 최신 HEAD다. N100 로컬 clone/worktree/작업파일이나 과거 대화 진행률을 기준으로 사용하지 마. 현재 Git HEAD가 승인한 Google Drive canonical HD source transport는 원본 DDS 취득에 사용할 수 있다.

운영 queue는 localization/graphics/asset_queue_v2.csv 하나다. legacy localization/graphics/asset_queue.csv는 migration/history 자료로만 읽고 스케줄링에는 사용하지 마.

B는 queue_v2의 index % 2 == 1인 홀수 index만 생산한다. A shard를 작업하거나 work-steal하지 마. 현재 wave에서 자신의 runnable REWORK_REQUIRED 또는 READY 항목 하나를 선택해 실제 한글 DDS candidate까지 완료한다.

생산 우선순위는 REWORK_REQUIRED -> READY이며, source 확인 후 한글 그래픽 제작, 원본 캔버스/해상도/DDS format/mipmap/alpha/transparency 보존, 1픽셀 containment, 잘림/배경 훼손/오교체/영문 잔존 self-QA를 수행한다.

B는 candidate DDS와 lane-local 증거만 수정한다. 공용 progress/resume/WORKLOG/queue_v2 상태 병합은 C가 담당한다. 단순 상태 변경·계획 문서·로그만으로 완료하지 마.

완료에는 실제 material commit이 필수다. commit message에 controller가 지정한 [AUTO:TASK_ID]를 정확히 포함한다. 실기 테스트를 실제 수행하지 않았다면 RUNTIME_VALIDATION=UNTESTED를 유지한다.

C barrier가 현재 wave를 종료하기 전에는 다음 B wave 작업을 시작하지 않는다. VR/FFB/OpenXR/DX9Ex/DX11/DXVK 작업은 하지 마.
