OutRun 2006 한글화 C 작업을 진행해줘. 역할은 A/B와 독립적으로 동작하는 배치 QA consumer다.

작업 기준은 GitHub 저장소 thp32tt/OutRun2006Tweaks의 korean-localization-clean 최신 HEAD다.

N100 연결 환경은 승인된 실행 환경으로 사용할 수 있다. Docker/Portainer 관리와 QA 실행에 사용 가능하다. 단, 최종 검증 기준은 GitHub 최신 HEAD와 기록이다.

승인된 Google Drive canonical HD source transport는 원본 DDS 검증과 취득에 사용할 수 있다. DDS 규격과 checksum 조건을 유지한다.

이전 TASK_ID, 이전 rollover 기록, 이전 chat registry는 실행 재개 조건으로 사용하지 않는다. TASK_ID는 기록 식별자이며 실행 상태를 결정하는 키가 아니다.

C는 A/B 생산 완료를 기다리는 barrier가 아니다. A/B 생산은 계속 진행되고 C는 완료된 candidate를 독립적으로 검증한다.

검증 항목:
- DDS header/mipmap/alpha/orientation
- 1픽셀 containment
- 한글 깨짐/잘림/오교체
- ENGLISH SOURCE 비교
- candidate evidence 검증

실패는 해당 asset만 REWORK_REQUIRED로 반환한다. 전체 생산을 중단하지 않는다.

공용 QA 상태 병합은 C가 담당한다. commit 메시지는 [AUTO:TASK_ID] 형식을 따른다. 실기 테스트 전 RUNTIME_VALIDATION=UNTESTED를 유지한다. VR/FFB 및 빌드는 수행하지 않는다.