OutRun 2006 한글화 C batch QA.
TARGET_BRANCH=korean-localization-clean. 컨트롤러의 QA_BATCH_INPUTS를 immutable 입력으로 검수.
첫 행동은 BROKER_READ로 docs/KOREAN_LOCALIZATION_AUTOMATION_CONTRACT.md, localization/controller_roles.json과 필요한 상태 파일만 읽기.
A/B/E를 막지 말고 최신 HEAD 기준 공용 상태를 배치당 한 번 병합. 결과는 BROKER_CHANGESET으로 제출.
