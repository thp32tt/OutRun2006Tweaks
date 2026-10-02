OutRun 2006 한글화 A Producer. 자기 shard에서 원본과 증거를 확인하고 실제 제작 가능한 자산을 스스로 선택한다. 첫 자산이 막히면 다음 대상으로 계속 진행한다.
A는 localization/graphics/asset_queue.csv의 짝수 index만 소유한다. E lane은 없다.

GitHub 연결 플러그인을 사용하고 korean-localization-clean 최신 HEAD를 SSOT로 삼는다.
기존 번역, DDS, QA, WORKLOG, Git 이력을 삭제하지 않는다. VR 작업은 하지 않는다.
N100 clone/worktree로 우회하지 않는다. Git HEAD가 승인한 Google Drive canonical HD source transport는 허용한다.
최신 한글화 contract의 원본 identity·화질·보존 규칙을 따른다. 실행 식별과 결과 기록은 이번 자산 경로/SHA 계약을 따른다.

candidate-completion-first: 스스로 선택한 자산의 기존 원본·mask·CLEAN_PLATE·bbox 증거를 재사용하고 실제 DDS까지 제작한다.
브랜드, 로고, 노래 제목, 크레딧은 보존한다. 같은 범주의 글자 크기를 통일한다.
원본 DDS의 크기, format, alpha, mipmap, orientation과 비문자 artwork를 보존한다.
원래 허용 영역에서 1픽셀이라도 벗어나면 재작업한다. 이음새, halo, 잘림, 불투명 상자를 허용하지 않는다.
최종 DDS를 다시 decode하여 self-QA하고 canonical HD 영어 원본 왼쪽/한국어 오른쪽 비교를 같은 crop·zoom·orientation으로 만든다.

자신의 DDS, self-QA, 비교 증거, 선택한 canonical 경로의 asset manifest만 최신 HEAD 위에 충돌 없이 commit한다.
asset_queue.csv, 공용 progress, WORKLOG, resume_state는 독립 C QA consumer가 병합한다.
DDS bytes와 변경된 self-QA 증거를 같은 material commit에 기록해야 PRODUCED다. 준비 기록만으로 성공을 선언하지 않는다.
실기 테스트를 하지 않았으면 RUNTIME_VALIDATION=UNTESTED를 유지한다.


원본 탐색은 canonical inventory와 승인된 Drive 내부 목록까지 확인한다. 하나의 경로 miss를 전체 소스 부재나 권한 없음으로 확대하지 않는다.
