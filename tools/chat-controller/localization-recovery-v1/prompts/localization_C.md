OutRun 2006 한글화 C-SALVAGE 실행 — 기존 A/B 자동화의 3번째 ChatGPT 탭
프로젝트: 기존 "아웃런 한글화 신규" 프로젝트. VR 프로젝트로 이동하지 마.

소스 저장소: thp32tt/OutRun2006Tweaks
한글화 자산 브랜치: korean-localization-recovery-20260928
컨트롤러 브랜치: localization-controller-recovery-20260928

1. 첫 작업으로 한글화 자산 브랜치 docs/KOREAN_LOCALIZATION_AUTOMATION_CONTRACT.md,
   docs/OUTRUN_C_SALVAGE_SLOT_20261015.md,
   docs/OUTRUN_C_SALVAGE_AUTOMATION_MANUAL_DEPLOY_20261015.md를 확인해.
2. A/B가 이미 생성·다운로드한 기존 PNG를 재사용하되 새 이미지를 생성하지 마.
   ChatGPT Create image/ImageGen, 외부 유료 이미지 API 및 계정/한도 우회 시도 금지.
   A/B용 생성 작업이나 상태/queue를 소비하거나 A/B 탭을 바꾸지 마.
3. 아직 처리되지 않은 A/B 생성 PNG 후보 하나를 골라 원본 PNG/DDS와 실제 SHA,
   영어 텍스트 마스크, 한국어만 추출한 레이어, Photoshop PSD 인덱스를 확인해.
   PSD가 있으면 정본과 비교해 영어 레이어 제거 CLEAN을 우선 검토하고,
   없으면 정본 HD DDS의 배경/투명도를 검증한 mask CLEAN만 시험해.
   관련 도구: tools/localization/c_salvage_worker.py, c_salvage_plate.py,
   c_salvage_compose.py. Source SHA / 출력 증빙이 없으면 HOLD 기록을 남겨.
4. 검증 가능한 샘플의 글자층/영문 제거 CLEAN 후보를 기존 A/B 결과와
   분리하여 TEST_ONLY로 남기고 원래 크기·좌표·방향·보호 아이콘·텍스트
   잘림/겹침/영문 잔상/기울기/한글 깨짐을 검사해.
   실물을 확보한 지원 DDS 포맷에 한해 별도 DDS 시험본을 만들 수 있어.
   DXT/BC 비지원 포맷, 누락 원본·검수되지 않은 PSD 레이어는 HOLD해.
5. C가 스스로 C1_PASS/C3_PASS/실게임 PASS를 표시하거나 완성 DDS를
   정식 승격하면 안 돼. 게임 검증하지 않았다면 RUNTIME_VALIDATION=UNTESTED.
6. GitHub 작업/자체 실행이 가능한 경우 먼저 사용하고 불가능한 실물 파일
   접근은 연결된 MCP N100을 사용해. RDC는 사용하지 마.
   완료된 항목 중복 작업 금지. 실제 변경이 있다면 자산 브랜치에
   증빙·상태를 기록해 커밋/push하고 원격 HEAD를 확인해.
7. 한 번 실행할 때 실제 미완료 작업 하나 또는 명시적 HOLD 원인 정리를
   끝내고 Q-ID, 원본 SHA, 생성한 파일, QA 결과, 원격 커밋을 짧게 보고해.

VR/FFB/DX11/DXVK 작업은 하지 마. 음악 제목은 영문 그대로 유지해.
