## 2026-10-17 — 사용자 추가 지시: Docker 자동 영문 영역 탐색

기존 C-only 컨테이너에 `docker/c-original-english-crop/discover.py`를 추가했다.
- 기존 60초 큐 실행 외에 600초마다 검증된 전체-HD 원본의 알파 기반 연결 요소 후보 탐색을 수행한다. 원본 영상·알파·좌표·파일 SHA는 변경하지 않는다.
- 기존 255개 기록과 실행 큐에 중복되는 영역은 후보에서 배제한다. 제안 후보는 `auto_discovery/Q*_candidates.json`에만 기록하며 **자동으로 영문 확정/검수 PASS로 간주하지 않는다**. 글자가 아닐 수도 있으므로 `REVIEW_REQUIRED_UNVERIFIED_TEXT` 상태로 보류한다. Docker에 OCR은 설치되어 있지 않다.
- 사전에 원본·문구·좌표를 육안 검증한 영문 ROI만 `reviewed_regions.json`에 승인 기록 후, 공식 원문 표기와 비교하여 C 큐로 자동 등록한다. 큐 실행기가 원본 DDS SHA 및 픽셀 동등성을 다시 확인한다.
- 2026-10-17 점검: Q051(4096×2048)과 Q060(4096×2048)의 전체 DDS/PNG 픽셀 동등성 입증 후 VERIFIED 허용 목록 등록. Q051 DDS SHA `5b029de75fa10ed00e547ef2c5d9df9691e8e5d8b9f2622fee62bc4972c7ae67`.
- 시험: 자동 제안 11건은 전부 검수 HOLD. 원문 `KNOCKOUT! IN...`의 별도 표현 `IN...`를 이미지로 직접 확인한 검증 좌표 [1990,127,2300,232]에서 Q060 크롭 1건 310×105 PNG 생성. 원본 픽셀 SHA 및 crop_manifest 확인, TEST_ONLY, 게임 실기기 검증 미완료.
- 기존 ChatGPT 시간당 작업은 **비활성화 유지**. A/B/C1/VR/한글 생성/클린 플레이트/DDS 수정 및 타일 재조립은 금지. N100 C 독립 컨테이너 외 서비스 배포 금지.

---

## 2026-10-17 00:18 KST 사용자 변경 — C 영문 크롭 Docker 자동화 허용

ChatGPT 시간당 예약 실행 대신 **독립 N100 Docker 컨테이너의 폴링 워커만 허용**한다. 2026-10-16 비활성화 지시는 A/B/C1/브라우저/ImageGen/한글 합성 및 기존 한글화 컨트롤러에 그대로 적용한다. 신규 C 전용 컨테이너만 재시작 가능하며 다른 Portainer 스택을 재배포하지 않는다.

- 정본: `docker/c-original-english-crop/{compose.yaml,loop.py,README.md}`.
- N100 독립 컨테이너: `outrun-c-original-english-crop`; 60초마다 신규 검증 큐 검사, 1회 최대 10건, 리소스 제한, network=none, 원본 RO.
- `MASTER_CROP_MANIFEST_255.json`에 이미 있는 255개 및 기존 output은 중복 크롭 금지.
- 기존 runner는 Q060만 verified allowlist에 보유한다. 다른 자산 추가 시 원본 DDS/전체 PNG 픽셀 동등성, 문구/좌표 육안 검증 이후에만 allowlist와 queue_specs를 추가한다.
- **단순 주기 실행은 새로운 영문 문구의 자동 발견이나 OCR을 의미하지 않는다**. 신규 검증 스펙 없을 때는 IDLE; 그 결과를 신규 산출물로 보고하거나 점수 중복 가산하지 않는다.
- 현 승인 범위는 C 전용 네이티브 원본 크롭, TEST_ONLY 산출물뿐이다. 사용자 별도 승인 없는 이미지생성·확대·CLEAN·DDS·게임 패치는 금지.

---

## 2026-10-17 00:10 KST — C English-only native crop automation REAUTHORIZED (newer user instruction)

The user has explicitly authorized restarting **only** automatic C extraction of original English lettering/phrase ROIs. This supersedes the October 16 *no C scheduling* instruction for this narrow function only. The existing ChatGPT automation `OutRun 영문 HD 크롭 자동화` (task ID `6ad160ee3a2c81918f7afe2b99ad29cd`) is enabled on an hourly cadence at minute 03 KST; it must not create a second scheduler/timer. Every invocation must seek at most one **new** genuine complete-original HD English phrase crop. Check existing `MASTER_255_V2_20261016/MASTER_CROP_MANIFEST_255.json` (255 existing) and the standalone C queue and output IDs first. A simple repeat of a completed queue item is not progress.

Admit additional sources only after source original-DDS provenance, SHA256, full-frame dimensions, orientation and actual text ROI boundaries are verified. English-only native pixels and original background/effects are preserved without alpha removal, rescaling, masks, CLEAN, Korean, composites, DDS editing or ImageGen. One new phrase => exactly one separate `english_original_native_crop.png` and SHA/coords-bearing `crop_manifest.json`, `CROP_TEST_ONLY_REVIEW_REQUIRED`; uncertain items => HOLD (without guessing). Previously completed crops and A/B state are immutable. Original 986 tiles/reassemblies are excluded. Legacy A/B/C1/other image production controllers, Portainer auto dispatch and VR remain stopped. This authorization applies to the **ChatGPT task-only C worker**, not to restarting any Docker container. The user can stop this task separately without affecting A/B.

---

# OutRun 2006 C — N100 original HD English crop only (2026-10-16)

## Latest user override and emergency pause

**All existing OutRun Korean-localization A/B/C/C1 production, sending, recomposition,
ImageGen and related browser automation are stopped.**
The OutRun Korean-localization controller was stopped on N100 and its Docker restart
policy disabled. The N100 `outrun-kor-chrome-hourly.timer` was disabled.
This is a PAUSED runtime, **not** an automatic rollout of a new C process.
Other projects (especially VR) are out of scope.

**C's future role replaces C-ROI-SOURCE, C-SALVAGE and all ImageGen input production:**
crop the complete English text phrase **as original unmodified pixels** only from
the real original HD full-image PNGs available on N100, retaining original image
size, RGB/RGBA channels and orientation. For each English phrase use one native
XYXY rectangle including full text, outline, shadow and any effects; no sliced
letters and no neighboring unrelated phrase. Review the crop for cut edges.
Do not make 2x/3x/4x ImageGen inputs, masks, transparency removal, CLEAN,
reassembly, translated Korean images, DDS edits or game patches.

## Authorized source and output boundaries

- Source: `/home/chatgpt-runner2/work/c_salvage_text_roi/source_full_20261012/`
  `q*_*.png` **only after** confirming each file is a genuine native
  original-HD **complete** English atlas, not any of 986 previous tiles,
  generated Korean files or tile reassembly. Pin full PNG SHA256, full dimensions,
  originating original DDS path/platform/SHA if available. Hold any unverified source.
- Existing completed earlier crop archive:
  `work/c_salvage_text_roi/original_hd_phrase_crops_20261016/`.
  Preserve it. Do not overwrite, re-export, or recount the same crops.
- Future isolated C-only output under `work/c_salvage_text_roi/c_original_hd_crop_only/`
  with one native `english_original_native_crop.png` and
  `crop_manifest.json` per **new** English phrase. Do not put crops into
  ImageGen's A/B `inputs`, queues, or automatic dispatch.
- Official English transcription table may identify the phrase. Translation
  outputs are not a C operation; music/product/brand text remains unmodified.
- Record `source_full_png_sha256`, DDS provenance, native xyxy,
  crop SHA256, exact English source text and visual HOLD if unclear.
  `CROP_TEST_ONLY_REVIEW_REQUIRED`, `RUNTIME_VALIDATION=UNTESTED`.

## One-shot helper, no scheduling

```bash
python3 tools/localization/c_n100_original_hd_crop_only.py \
  --spec path/to/new_unique_crop_spec.json \
  --source-root /home/chatgpt-runner2/work/c_salvage_text_roi/source_full_20261012 \
  --output-root /home/chatgpt-runner2/work/c_salvage_text_roi/c_original_hd_crop_only
```

Schema `outrun-c-n100-hd-original-crop-v1`. Provide original full PNG name/SHA,
source dimensions, `queue_id`, optional original DDS path/SHA and
`regions: [{id,english,bbox_xyxy:[x0,y0,x1,y1]}]`.
Source kind must be `N100_PINNED_FULL_ORIGINAL_HD_PNG` or
`N100_DDS_VERIFIED_READABLE_FULL_HD_PNG`. The helper never authorizes a fake
full-source provenance: perform original-versus-DDS proof separately.
If source, translation, borders or orientation are uncertain, **HOLD**, not
pretend cropping is game QA.

A/B state and historic SHA/evidence must not be consumed or changed.
Future restart requires a **new explicit user instruction**, and then separate
Portainer manual deployment. No GitHub push alone starts any container.
