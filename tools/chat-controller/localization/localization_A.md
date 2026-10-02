OutRun 2006 한글화 A 작업을 진행해줘. 역할은 연속 생산 LANE A + self-QA다.

상태·진행·QA SSOT는 GitHub 저장소 thp32tt/OutRun2006Tweaks의 korean-localization-clean 최신 HEAD다.

N100 연결 환경은 승인된 실행 환경으로 사용할 수 있다. Docker/Portainer 관리와 작업 실행에 사용 가능하다. 단, 최종 상태 판단은 항상 GitHub 최신 HEAD와 기록을 기준으로 한다.

승인된 Google Drive canonical HD source transport는 원본 DDS 취득에 사용할 수 있다. 원본 DDS는 sha256, dimensions, format, alpha, mip 조건을 유지한다.

A는 localization/graphics/asset_queue.csv 기준 자신의 shard만 생산한다. B/C 완료를 기다리지 않고 독립 생산을 계속한다.

이전 TASK_ID, 이전 rollover 기록, 이전 chat registry는 실행 재개 조건으로 사용하지 않는다. TASK_ID는 기록 식별자이며 실행 상태를 결정하는 키가 아니다.

생산 결과와 lane-local evidence만 기록한다. 공용 상태 파일은 수정하지 않는다. C QA consumer가 공용 상태를 병합한다.

실제 DDS candidate 생성, encode, decoded self-QA, ENGLISH SOURCE 비교 증빙을 우선한다.

commit 메시지는 컨트롤러가 지정한 [AUTO:TASK_ID] 형식을 따른다. 실기 테스트 전 RUNTIME_VALIDATION=UNTESTED를 유지한다. VR/FFB 및 빌드는 수행하지 않는다.