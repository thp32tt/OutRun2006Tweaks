# OutRun 2006 — 기존 한글 PNG + DDS 기반 게임 적용 계획 (2026-11-02 KST)

## 목적과 운영 경계
- **목표:** 새 한글 이미지를 대량 재생성하기보다 기존 A/B ImageGen 후보 PNG와 이미 생성된 v3 한글 DDS 시험본을 재사용하여 **텍스처/UI 한글화 실게임 적용**으로 진행한다.
- **범위:** OutRun 2006 PC/HD 텍스처와 UI, 원문이 DDS에 베이크된 문구. 동적 런타임 문자열과 이름입력/Unicode는 별개 경로로 분리하며 VR/FFB/DX11/DXVK 설정과 코드는 건드리지 않는다.
- **배포 책임:** GitHub에서 소스/계획/시험 산출물을 준비해도 Portainer Git Stack pull/rebuild/redeploy, 게임 폴더 반영, 사용자 실게임 검증은 사용자가 수행한다. **현재 모든 DDS는 TEST_ONLY_NOT_RUNTIME_APPROVED.**
- **삭제 금지:** 원본 DDS, 원본 HD PNG, 기존 A/B 후보와 QA 기록, 이전 패키지, 설치본을 덮어쓰지 않는다.

## 2026-11-02 현물 재확인 근거
| 확인 항목 | 결과 | 해석 |
|---|---|---|
| GitHub `thp32tt/OutRun2006Tweaks`, 자산 브랜치 `korean-localization-recovery-20260928` | 계정 push 권한 확인 | 계획 문서만 해당 브랜치에 반영 가능 |
| N100 `work/image-src/text_roi_batches/production_manifest.json` | 1,002 rows = 활성 954 + 이전 A→B 재배정 48 | **활성 row만** 설치 대상 |
| N100 `candidate_outputs/A`, `candidate_outputs/B` | PNG 파일명 각각 454, 501개 | A/B 파일 총 955개. 954 활성 row와 1:1 동일하다고 가정 금지 |
| `A_state.json`, `B_state.json` | 완료 counter A=453, B=501, active=null | PNG 파일 수와 QA/사용 승인 분리 |
| N100 `offline_overlap_v3_ink_test_only/last_run.json` | 108 source 검사 / 104 ALREADY_VERIFIED / 2 별칭 / 2 원문보존 / hold 0 | 104 DDS 시험본 제공 |
| v3 통합 변환 | 실제 렌더링 950 + 중복 대표 4 = 활성 ROI 954 | **오프라인 단순 글꼴 백업**, A/B ImageGen 품질 승인 아님 |
| v3 ZIP | `OUTRUN_OFFLINE_KOREAN_TEST_ONLY_96e9372fb718.zip`, 140,069,153 bytes, SHA256 `84d92c22ff957ebeaa3156165b9ed7ef769802756ddc183d18bd586ff5c1ddf3` | `textures/load/...` DDS 및 `qa_receipts/...` |
| N100 v3 디렉터리 | `/home/chatgpt-runner2/work/image-src/text_roi_batches/offline_overlap_v3_ink_test_only/` | DDS/샘플 원본 위치 |
| 샘플 | Q032/Q051/Q054/Q057/Q241 5개 실제 DDS→PNG 변환본 | 미리보기/표본 검사 가능 |
| 독립 QA/실게임 | C1/C3와 실제 플레이 전체 승인 없음 | `RUNTIME_VALIDATION=UNTESTED` |

## 권장 전략: v3 DDS를 공통 베이스로, 검증된 A/B PNG만 고품질 교체
- **베이스(v3):** 104개 시험 DDS는 파일이 이미 있으므로 1차 전체 커버리지 확인용으로 재사용. 부정확한 영어 지우기, 단순 글꼴/기울기, ROI 내부 그림 손상, 1 mip·비압축으로 인한 VRAM 증가 가능성을 미해결로 유지.
- **우선 채택(A/B):** 실제 PNG 파일 SHA, 활성 ROI, 원문 DDS/HD SHA, 번역, 배치 소유권, 원래 줄 수·기울기를 확인한 개별 후보만 선택. C1 PASS + 실제 글자 검사 + 원문 CLEAN/alpha/보호 마스크 검증이 되어야 후보를 채택.
- **후순위 대체:** A/B가 미검수·깨짐·중복·과다줄임·보호영역 침범이면 무리하게 붙이지 말고 v3 시험본 유지. 게임에서 눈에 띄는 중요한 곳만 A/B 재작업 우선.
- **중요:** 950개의 v3 글꼴 렌더링과 955개의 A/B 후보 파일을 같은 성과로 합산하면 안 된다. 동일 ROI에 대한 **서로 다른 구현물**이며 최종 결과에는 ROI별 1개 소유자만 정한다.

## 실행 단계 및 종료 조건

### G0. 불변 재고 조사 / 대응표 확정 (읽기 전용)
1. 원본 DDS 경로·SHA, 원본 풀 HD PNG·SHA, `production_manifest.json`의 활성 ROI ID/XYXY/영문/한글/variant를 읽는다.
2. A/B PNG 955개를 파일명·SHA·원래 작업 배치/격리/QA 기록과 교차대조하고, 활성 954 ROI에 대해 `A_B_VALID / DUPLICATE / QUARANTINED / MISSING / UNMATCHED`를 계산한다. 수량 차이를 수동 추정하지 않는다.
3. v3 104 DDS를 원본 경로(플랫폼 variant 포함)와 연결하고 별칭 2·보존 2는 쓰지 않는다.
4. 1행 1 ROI의 `placement_plan.csv`를 만들고 각 행에 `source_dds_sha, original_hd_sha, ROI, text, preferred_candidate_sha, fallback_dds_sha, decision, qa_status, runtime_status`를 기록한다.
**종료 조건:** 활성 ROI 954개 모두 중복 없이 정확한 출처·결정 상태 존재, 경로 불명/자산 SHA 불일치는 HOLD.

### G1. 2개 DDS 작은 설치 검증 → 5개 시각 점검
1. 위험도 낮은 샘플 Q241(로딩), Q032(랭킹)부터 **사용자 테스트 전용** 게임 폴더의 해당 텍스처 경로에 설치해 로딩 여부를 확인한다. 원본은 백업하고 설치 스크립트는 해시가 일치하지 않으면 중단한다.
2. 기존 5개 실제 DDS→PNG 표본(Q032/Q051/Q054/Q057/Q241)을 눈으로 확인한다. Q051(HUD), Q054(미션), Q057(골)는 처음부터 위험군으로 관리한다.
3. DDS 변환 전후 RAW/FLIP-Y, 크기, 채널·alpha, sprite UV, 게임의 실제 경로/캐시를 검증한다.
**종료 조건:** 최소 2개 장면에서 텍스처가 게임에 실제 로드됐고 화면 증거가 남음. 미실행 시 TEST_ONLY 유지.

### G2. 원본 CLEAN + A/B 한글 PNG 합성
1. A/B 후보의 실제 글자/effect alpha만 분리. 원문 제거는 독립 클린 플레이트/PSD/검증된 마스크를 사용. 무관한 아트의 alpha/RGB는 원본 픽셀과 유지.
2. ImageGen PNG는 원본 ROI 확대 참조이므로 그대로 atlas에 붙이지 않고 원문 UI cell/좌표에 **종횡비 유지**해 역변환. 글자·그림자·외곽선이 원래 안전영역을 벗어나면 HOLD.
3. 원본이 두 줄이면 줄 구분·의미 강조·아이콘 내부 배열·기준선을 유지한다. 한국어 문구가 짧다고 임의로 한 줄로 합치지 않으며, 불가피한 변화는 별도 판정.
4. 플랫폼/선택상태/코스 단계/좌우 변형 및 공유 아틀라스는 각 variant에 매칭. 동일 source DDS에 서로 다른 좌표를 쓸 때는 single-owner 합성 결과를 확정한 후 **최종 DDS 1회 작성**.
5. 우선순위: P0 제목·메뉴 상단·HUD/하트·Stage2 겹침·목표차/랭크/온라인 기록·아이콘 줄바꿈, P1 차량/코스·미션, P2 기타.
**종료 조건:** 좌표/텍스트/sha에 연결된 합성 PNG + 픽셀 변경 마스크 + 리뷰 가능한 before/after. 위험한 ROI만 보류, 안전한 ROI는 계속 진행.

### G3. DDS 재인코딩 및 패키징
1. 가급적 원본 포맷(DXT5/비압축, mip 개수, alpha 의미, FLIP-Y)을 보존하는 검증된 인코딩 경로 사용. 지원하지 않는 포맷은 **무손실인 척 하지 않고** 별도 호환성 시험 후 HOLD 또는 v3 시험본 유지.
2. 원본 DDS 헤더/길이와 DDS decode→PNG 재디코드, atlas 내 허용 mask 밖의 픽셀 변경, 알파·회전·줄바꿈을 자동 검사.
3. 안정판으로 `textures/load/... .dds` 같은 상대 경로를 보존한 `KOREAN_PREVIEW_TEST_ONLY.zip`을 별도 생성하고 ZIP·원본·후보 SHA 매니페스트와 복원용 manifest를 포함.
4. 이미 있는 v3 ZIP을 삭제/덮어쓰지 않으며, A/B PNG 반영판은 다른 SHA의 새 패키지로 명확히 구분.
**종료 조건:** 동일 입력→동일 출력 SHA 재현, 포맷/픽셀 QA PASS, 경로 충돌 0, 원본 복원 가능. 그래도 출시 승인 아님.

### G4. 게임 장면별 실기 검증 / 우선 결함 수정
- 1차: 로딩·타이틀·메뉴·차량 선택·랭킹. 처음 열기/선택/복귀/다시 열기까지 확인.
- 2차: Stage1→Stage2→GOAL, HUD 심장/타이머/점수/상대순위, 미션/코스좌우·난이도. 일부 문구는 동적 런타임 글자일 수 있으므로 DDS와 별도 분류.
- 3차: 컨트롤러별 아이콘/PlayStation/Switch/Xbox/Keyboard variant, 온라인 기록·저장 상태, 2줄 아이콘, 50% 축소 가독성.
- FPS/VRAM: 기존 DDS가 DXT5+다중 mip이었으면 v3 비압축+1 mip 시험본과 메모리/프레임/경계 계단현상을 비교. VR 성능 영향 있으면 해당 텍스처를 원래 코덱/밉으로 재패키징하거나 게임 적용 HOLD.
- 증거: ZIP SHA, 설치 경로, 게임 실행판/HD mod, 씬, 사용자 조작, 원본/수정 스크린샷, PASS/FAIL/NOT_TESTED. 미검증 결함을 닫지 않는다.
**종료 조건:** 실사용자가 핵심 경로를 시험하고 명시적으로 승인한 DDS에 한하여 RELEASE 후보로 승격.

## 작업 순서(최소 수고/최대 커버리지)
1. **즉시:** 104 DDS v3 보존·SHA 고정 및 955 A/B 후보↔954 활성 ROI 검증 인덱스.
2. **첫 게임 확인:** Q241·Q032 2개 실기 로드 성공 → Q051/Q054/Q057 표본 시각 점검.
3. **커버리지:** 전체 104 DDS 테스트 ZIP을 이미 있는 v3 패키지로 활용하여 한국어 UI의 실제 로드율/깨짐 지도를 만든다. 바로 RELEASE로 지정하지 않는다.
4. **고품질 전환:** 눈에 띄는 결함부터 A/B 후보 합성 → 저장 DDS 정적 QA → 실기 검증 순서로 올린다.
5. **최종:** 원본 코덱/밉 호환·2줄 및 HUD/Stage2를 통과한 장면만 배포.

## 절대로 합격으로 오인하면 안 되는 사항
- `A/B completed_files`, `v3 ALREADY_VERIFIED`, `held_count=0`, ZIP 생성, PNG 리디코드 PASS, C1 간이 PASS는 각각 서로 다른 범위다.
- 기존 단순 DDS writer `tools/localization/replace_uncompressed_dds.py`는 **비압축 BGRA32·single mip**만 지원하므로 DXT5/다중 mip 소스에 무검증으로 사용하지 않는다.
- 남은 영문과 한글을 동시에 표시하는 현상, 아이콘 줄바꿈 축소, 원본 ROI 안 보호아트 손상, 회전/기울기와 압축/밉 차이를 무시하지 않는다.
- 사용자가 수동 배포 전에는 Portainer나 게임 설치본을 자동 변경하지 않는다.

## 소스
- 자산 정본: `docs/KOREAN_LOCALIZATION_AUTOMATION_CONTRACT.md`, `docs/KOREAN_LOCALIZATION_GLYPH_SCALE_POLICY.md`, `docs/KOREAN_LOCALIZATION_END_TO_END_PLAYTEST_GATE.md`
- 컨트롤러: `tools/chat-controller/localization-recovery-v1/OVERLAP_INK_V3_20261102.md`, `OCR_FREE_BULK_DEPLOY_20261102.md` (브랜치 `localization-controller-recovery-20260928`)
- N100 실제 snapshot: `work/image-src/text_roi_batches/`, `offline_overlap_v3_ink_test_only/last_run.json`, 후보 A/B, ZIP 직접 확인.
