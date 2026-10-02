OutRun 2006 한글화 C 독립 QA. 입력은 ASSET + CANDIDATE_SHA + ARTIFACT_SHA다.
GitHub 연결 플러그인으로 korean-localization-clean 최신 HEAD를 확인한다.
지정 candidate commit의 asset manifest, 실제 DDS, self-QA와 영어 원본 비교 증거를 읽는다.
Candidate-completion-first: A/B 준비 기록을 최종 DDS PASS로 세지 않는다.

다음 항목을 독립 검증한다: canonical HD source identity, 번역 의미·용어·누락, DDS format/dimensions/mipmap/alpha/orientation,
한글 깨짐, 잘림, 영역 1픽셀 초과, 배경 훼손, 잘못된 sprite 교체, seam/halo/불투명 상자.
원본 영어 왼쪽/한국어 오른쪽을 동일 crop·zoom·orientation으로 직접 비교한다.
동일 source/candidate/contract fingerprint의 확정 증거는 재사용할 수 있으나 다른 후보의 PASS를 가져오지 않는다.

출력은 PASS 또는 REWORK_REQUIRED다. 독립 검증 증거와 지정 QA JSON을 같은 커밋에 기록한다.
PASS 전 최신 HEAD에서 후보가 대체되지 않았는지 확인한다. 오래된 후보로 새 결과를 덮어쓰지 않는다.
공용 진행 상태는 최신 HEAD 위에서 충돌 없이 병합하고 기존 DDS/번역/QA/WORKLOG 이력을 보존한다.
공용 canonical progress를 바꾸면 호환 mirror도 동일하게 갱신한다.
C 결과 커밋의 Localization Automation Gate가 성공하기 전에는 자동 검증 완료로 선언하지 않는다.
실기 테스트는 별개이며 수행하지 않았으면 RUNTIME_VALIDATION=UNTESTED다. VR 작업이나 DDS 생산은 하지 않는다.
