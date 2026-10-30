# OutRun 2006 한글화 오류 분류 및 복구 순서 — 2026-10-31 KST

**범위:** 진단·복구 계획만. 이 검토 문서 자체는 A/B 생성물을 재생성하거나, OCR 시도 횟수를 초기화하거나, DDS·게임 파일을 변경하지 않는다. Portainer 수동 배포 계약을 유지한다.

## 확인한 사실 (N100 기록 + GitHub controller branch)

- A 436개/142배치, B 483개/146배치: **919건 이미지 생성 기록 완료**, `active=null`. Manifest 967항목 중 919건 `ROI_APPROVED_FOR_IMAGEGEN`; 나머지 48건 `ROI_REBALANCED_TO_B`는 역할 변경 이력으로, 신규 미생산 48건이 아니다. C1의 최근 Q228 두 PNG PASS는 *글자 레이어* 판정이며, 원본 복원·DDS 실저장·게임 PASS가 아니다.
- `work/image-src/text_roi_batches/export_evidence/` JSON 289개에서 확인한 **920개 export 항목 모두 `REWORK_DIMENSIONS`**. 이 숫자는 919개 완료 카운터와 집계 범위가 달라 920개의 *서로 다른 미완료 게임 자산*을 뜻하지 않는다. `text_roi_queue.py`의 이 상태는 생성 PNG의 *캔버스 크기*가 목표 ROI와 다른 경우 기록된다. **시각적 glyph PASS/FAIL과 분리**해야 하며, 전량 일괄 확대·압축하거나 전량 폐기하지 않는다.
- Q228 `multiplayer` 목표 1191×154 / 출력 2172×724, `game lobby` 목표 1128×156 / 출력 2172×724; 둘 다 C1 glyph-layer PASS, DDS `UNTESTED`. 동일한 캔버스 크기를 임의 x/y 독립 스케일로 억지로 맞추면 원본 대비 획/기울기/줄 구조 손상 위험.
- GPT OCR `state.json`: 완료 기록 **240건**, 마지막 기록 **2026-10-30 16:31 KST**, `active=null`; 10-31 00:10 KST에도 새 기록 없음. `summary()` 기준 미해결 **51개 원본/153개 문구**: 자동 재시도 **14개/83문구**, 좌표 충돌 검토 **21개/45문구**, 시도 소진 **16개/25문구**.
- OCR `NO_VALID_DETECTIONS` **121건** 중, `rejected`가 중복 좌표만인 경우 **86건**, `rejected=[]`인 경우 **35건**. 뒤쪽은 단순한 OCR 부재로 단정 불가: 실제 빈 detections, uncertain 응답, 이미 처리된 텍스트 등 별도 계측 필요. `RESPONSE_HOLD` **4건 모두 `ValueError:GPT_OCR_RESPONSE_JSON_NOT_FOUND`**.
- `work/gpt_ocr_host_watchdog.py`는 `active`가 있는 stale 상태 복구만 수행하며 **`active=null`에서 새 OCR 작업을 예약·전송하지 않는다**. 응답 대기 감시 기준은 2400초, 컨트롤러 `gpt_vision_chat_ocr.py` 기본값은 600초로 다르다. 호스트 감시기의 timeout 시도 카운트는 `attempts[fingerprint]`를 참조하므로 C2 키 `C2:fingerprint`와 일치하지 않을 수 있다. 또한 컨트롤러 갱신과 파일 상태 동시 쓰기의 경합 위험을 점검해야 한다. 따라서 재배포/컨테이너 활성 여부는 별도 확인이 필요하며 지금 원인을 단정하지 않는다.
- Q205 원본 BASE에서 요청된 `Exchange OutRun miles for this item?`는 육안으로 확인되지 않았고, BASE/KEYBOARD는 SHA와 픽셀이 같으나 플랫폼별 차이도 있다. 이 경우 마구 재시도하기보다 `NOT_PRESENT_IN_VARIANT` 검증이 필요. Q140 `PRESS [ENTER-KEY ICON] KEY`는 특수 키 아이콘이 섞인 문구로 일반 문자열 일치 OCR이 실패할 수 있다. Q228은 실제 육안으로 확인한 2건만 수동 복구했고 다른 요청 문구를 추측으로 등록하지 않았다.
- `work/qa_icon_layout_20261028/rework_hold.json`의 HOLD 5건: Q095 원문 3→후보 2줄 / 4→3줄 / 4→2줄 3건, Q100 보호 아이콘·배경 재생성 2건. 기존 후보는 삭제하지 않고 재작업 대상을 별도 경로에 새 SHA로 제작한다.

## 처리 우선순위 / 완료 게이트

1. **P0 — QA 승격과 DDS 합성 안전 차단:** 생산 완료와 `DDS_APPROVED`를 분리. 대표 이미지의 생성 캔버스→실제 glyph/effect alpha bounding box→원본의 개별 줄·glyph/effect bbox→안전 UI cell/UV를 명확히 대응. **가로/세로 비율 강제 맞춤 및 underfill 단독 반려 금지.** 필요한 경우 정비례·고품질 보정 후 원본 복원 CLEAN과 겹침/보호아트 검증, 실패는 HOLD. 대표 DDS 1건은 저장 바이트 재디코딩, mip, native/75%/50% 및 게임 렌더까지 검증. 승인되기 전 919건 일괄 DDS 쓰기 금지.
2. **P1 — OCR 정체 해소:** 먼저 Portainer 실제 컨테이너의 브랜치/빌드/스케줄(A :00/:20/:40, B :10/:30/:50, C1 :15/:45), `AUTO_SEND`, 실제 B/C1 브라우저 health, 마지막 런타임 로그 확인. host watchdog는 dispatcher가 아님. OCR C1/C2 분리된 timeout counters 및 watcher timeout을 **상태 변경 전에** 통일하고, 파일 임시 쓰기·락 및 lease ownership 일원화; 프로세스와 배포는 운영 규칙에 따라 사용자 수동 처리. 단독 stale 상태 복구만으로 재시작 성공 주장 금지. 다음 정상 OCR task 실제 `SENT`→응답 수신→검증된 `APPLIED`를 관찰한 뒤 정상화 판정.
3. **P2 — OCR 품질:** 86 중복-only 역사적 기록은 fingerprint+원본 SHA 기준 21개 수동 검토 묶음으로 디듀프; 기존 bbox의 텍스트와 다르면 자동 승인 금지. 35건 `rejected=[]`은 매 응답의 `detections/uncertain/covered/skipped` 건수와 이유를 남겨 `ABSENT_VERIFIED`, `AMBIGUOUS`, `MODEL_NO_DETECTION`, `ICON_MIXED`로 분리. JSON 오류 4건은 채팅 DOM에서 **해당 task의 완전한 최종 assistant turn**만 추출하고, 신뢰할 수 없는 JSON 조각을 자동 채택하지 말고 원본 답변/턴 식별 근거를 보존해 동일 채팅에서 재수집. OCR attempts를 무작정 0으로 초기화하지 말 것.
4. **P3 — 5개 명시적 시각 오류:** Q095 세 건은 기존 행 구조를 유지한 **행별 한글 레이어**를 재생성하고 줄 수·기울기·잘림 검수. Q100 두 건은 텍스트 전용 RGBA와 아이콘/배경 제외 마스크로 재생성; 원본 배경 보호 픽셀 변화가 0인지 검사. 한 번에 1~2건 재작업, 별도 SHA로 C1 재검수, 원본 및 기존 후보 보존. 단순 프롬프트 강조만으로 PASS 처리 금지.
5. **P4 — 최종 합성 단계:** 정확한 SHA의 SOURCE→CLEAN PLATE→GLYPH ONLY→DDS 저장/재디코드→미프→C1/C3→사용자 실게임 증거가 갖춰진 것만 실사용 승격. DDS 없음/게임 미검증은 `UNTESTED` 유지. VR/FFB/DX11/DXVK 코드 불변.

## 주의

- `REWORK_DIMENSIONS` 920건은 이미지 캔버스 **기계적 불일치 현황**이며, 920건 모두 시각 FAIL이라고 판정하지 않는다.
- OCR `APPLIED` 카운트는 실제 사용자 게임 한글화 PASS 카운트가 아니다.
- `NO_VALID_DETECTIONS` 35건의 세부 원인, 컨테이너가 마지막 이후 OCR을 디스패치하지 않은 정확한 이유, 게임 DDS 품질은 추가 증거가 있어야 판정할 수 있다.

**증거 경로:** `work/review_export_status_20261031.py`, `work/ocr_error_histogram_20261031.py`, `work/ocr_error_review_sizes_20261031.py`, `work/ocr_manual_hold_summary_20261030.py`, `work/qa_icon_layout_20261028/rework_hold.json`, `work/C1_QA_20261030_1815_AI2_report.json`; GitHub `text_roi_queue.py`, `gpt_vision_chat_ocr.py`, `patch_controller_b_idle_gpt_ocr.py`; assets branch `docs/KOREAN_LOCALIZATION_GLYPH_SCALE_POLICY.md` / `docs/KOREAN_LOCALIZATION_EVIDENCE_GATE.md`.
