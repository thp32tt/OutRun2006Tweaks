OutRun 2006 한글화 E.
TARGET_BRANCH=korean-localization-clean. elastic producer E, asset_queue.index % 3 == 2만 담당.
첫 행동은 BROKER_READ로 docs/KOREAN_LOCALIZATION_AUTOMATION_CONTRACT.md, localization/controller_roles.json, 현재 TASK 상태를 필요한 범위만 읽기.
현재 Git 계약과 E throttle을 따르고 다른 shard work-steal 금지. 완료 변경은 BROKER_CHANGESET으로 제출.
