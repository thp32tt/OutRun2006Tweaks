OutRun 2006 한글화 C 작업을 진행해줘. 역할은 현재 A/B wave의 독립 QA barrier + 공용 상태 병합이다.

작업 기준은 GitHub 저장소 thp32tt/OutRun2006Tweaks의 korean-localization-clean 최신 HEAD다. 컨트롤러가 제공한 QA_BATCH_INPUTS의 TASK_ID + RESULT_SHA를 immutable 검수 기준으로 사용한다.

C가 현재 wave를 terminal 처리하기 전에는 다음 A/B wave가 시작되지 않는다. C는 producer candidate bytes를 임의 수정해서 PASS를 만들지 않는다.

각 입력마다 source identity, 원본 영역 동일성, 1픽셀 초과, clipping, 해상도 저하, DDS format/mipmap/alpha/transparency, 배경 훼손, 잘못된 이미지 교체, 번역 누락, 영문 잔존, 한글 깨짐을 검증한다.

판정은 PASS / REWORK_REQUIRED / HOLD / SUPERSEDED 중 하나로 명시한다. REWORK_REQUIRED는 해당 owner A/B shard로 반환한다.

C만 localization/graphics/asset_queue_v2.csv 및 공용 progress/resume/WORKLOG/QA 상태를 병합한다. legacy asset_queue.csv는 history/migration 자료이며 새 실행 상태를 기록하지 않는다.

한 C task에서 QA_BATCH_INPUTS 전체를 검수하고, 모든 입력의 disposition 및 current_candidate_sha/current_qa_sha/blocker_code 반영을 하나의 durable commit으로 남긴다. commit message에 controller가 지정한 [AUTO:TASK_ID]를 정확히 포함한다.

실기 테스트를 실제 수행하지 않았다면 RUNTIME_VALIDATION=UNTESTED를 유지한다. VR/FFB/OpenXR/DX9Ex/DX11/DXVK 작업은 하지 마.
