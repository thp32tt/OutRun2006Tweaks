# B·C1 ChatGPT 이미지 생성 생산 레인 — 2026-10-11

## 2026-10-11 C1 imagegen extension (current; overrides historic B-only wording)

B and C1 share the **same real ChatGPT ImageGen -> transparent RGBA PNG -> SHA-bound CLEAN/plate -> saved unapproved DDS -> producer self-QA workflow**. A remains the existing native/manual lane. On NEW unclaimed even indexes, B selects index % 4 == 0 and C1 selects index % 4 == 2. Never overwrite pre-existing explicit B in-flight ownership on an index % 4 == 2 or an assigned game-regression P0/P1. C2 is the sole independent PLATE_PASS / final QA reviewer for **all** A/B/C1 candidates (odd and even); C3 and user game review stay independent.
C1 uses `schema=outrun-c1-imagegen-v1`, `role=C1`, real generation provenance, and stores PNG+manifest under `localization/graphics/role_C1/imagegen_requests/` and trial under `role_C1/imagegen_trials/`. B retains `schema=outrun-b-imagegen-v1`, `role=B`, `role_B` paths. The existing `tools/localization/imagegen_b_pipeline.py` strictly validates both schemas, producer roles, mod-4 indexes, and correct output folder and prefixes. The original q060 B manifest below remains an example for B only; a C1 manifest must change schema, role, index, input/output folders, and actual SHA-bound evidence.
The historic B-only paragraphs below describe the common manufacturing procedure but not exclusive ownership. Any wording limiting real ImageGen to B alone, C1 to QA, or C2 to even QA is superseded here. Missing generator and binary-upload support is not a fallback excuse for fabricated outputs.


## 운영 결정과 적용 우선순위

사용자의 최신 지시에 따라 **A는 기존 폰트/벡터/수작업 제작 방식을 그대로 유지**한다.
**B(짝수 index)는 기존 폰트/벡터로 새 글자를 제작하지 않고 ChatGPT 이미지 생성 도구로 한글 텍스트 그래픽을 만든다.**
이 문서는 B에 한해 `KOREAN_LOCALIZATION_PRODUCTION_RESET.md`의 "AI 이미지는 배경 참조에 한정" 및 `KOREAN_LOCALIZATION_LETTERING_ENGINE.md`의 폰트/벡터 전용 제작 경로보다 우선한다.
그 외 소스/CLEAN/독립 C1·C2/C3/실게임/0픽셀 보호 조건은 **절대 완화하지 않는다**. 사용자 지정 승격 기준 없이 스스로 합격이라고 변경하지 않는다.

## 실행 위치와 플러그인 현실

- Docker 컨트롤러는 ChatGPT 프로젝트에 **짧은 B 명령**을 보낸다. 실제 이미지 생성은 그 대화를 수행하는 ChatGPT의 이미지 생성 도구에서만 수행한다. **GitHub Actions CPU 러너에는 ChatGPT 이미지 생성 플러그인이 없다.** 컨트롤러/Actions에서 실행된 일반 Pillow 변환을 AI 생성으로 가장하지 않는다.
- B 에이전트는 첫 작업으로 계약서를 읽고, 실제 이미지 생성 도구를 호출한다. 영문 원본 SOURCE **이미지**와 정본 문구를 도구에 전달하며 투명 RGBA PNG 한 줄 글자층만 요청한다. 결과의 실제 생성 ID/프롬프트/도구/PNG SHA/원본 SHA를 기록한다. 영문 원본을 텍스트만 상상해서 재구성하지 않는다.
- 도구 호출 불가/실제 출력 미수령 시 `IMAGEGEN_UNAVAILABLE` 또는 `IMAGEGEN_OUTPUT_MISSING`을 상태로 명시한다. **자동 폰트/수동 벡터 우회 금지**. 이 경우 B는 다른 이미지 생성 가능 작업을 시도할 수 있지만 허위 DDS/승인 수는 0으로 기록한다.
- 생성된 PNG를 같은 GitHub 브랜치 `localization/graphics/role_B/imagegen_requests/` 하위에 저장하고 아래 manifest를 함께 commit한다. ChatGPT 로컬 실행 환경과 GitHub 연결을 우선 사용해 바이너리 업로드를 시도한다. 대화 도구에 바이너리 GitHub 업로드 방법이 없으면 그 사실을 실제 호출로 검증하고 별도 전달 경로가 필요한 상태라고 기록한다. **Github image commit까지 수행하지 않고 Docker만으로 B 이미지 생성이 가능하다고 주장하지 않는다.**
- 이미 동일 생성물 SHA + 동일 자산의 manifest가 있다면 재실행 시 **중복 제작/점수/QA 처리 금지**. 새 후보는 기존 B-A/B-B 2안을 동시에 만들지 않는다. B는 **이미지 생성 1안**을 생산하고, A는 기존 자기 담당 자산을 생산한다.

## B 매회 생산 단계

1. `asset_queue.csv`, `INGAME_REWORK_BACKLOG.csv`를 최신 HEAD에서 조회한다. 짝수 B 담당 P0→P1→실제 REWORK→RENDER_READY 순. `rework_triage.py --index N`을 읽고 복구 불가능한 근거 없는 재렌더는 금지한다.
2. `plate_library`에서 source/region/orientation SHA 일치, 독립 C2 `PLATE_PASS`를 확인한다. 원본이 아닌 과거 실패 후보는 CLEAN의 근거로 쓰지 않는다.
3. **ChatGPT 이미지 생성 도구에서** 원본 영문 UI 스타일을 참조한 정확한 한글 문구만 투명 배경 한 줄로 생성한다. 기울임 방향, 원본 획·금속 질감, 보호 영역, 콜론 등을 명시한다. 이미지가 부정확하면 한 번에 동일 방법을 무한 반복하지 말고 실패 사유와 생성 ID를 남긴다.
4. 생성 결과를 SHA-bound 진짜 RGBA PNG로 보관한다. `tools/localization/imagegen_b_pipeline.py --repo . --manifest ...`를 실행하면 알파 경계를 자르고 단 한 번의 premultiplied-alpha LANCZOS 리사이즈로 영문 source_bbox **안에** 배치하고 CLEAN에 합성한다. `contain` 기본, `width_priority`는 시각 확인 필요.
5. 원본/CLEAN/기존 공식/B 이미지생성 실저장 DDS를 FLIPY 100/75/50, RAW로 비교한다. 기계 판정과 실제 이미지 관찰을 별도 기록한다. 한글 오자, 생성 특유의 가짜 획, 콜론·내부공간 붕괴, 타 UI 간섭, 과도한 바깥 푸른광, 글자 크기나 1px 클리핑은 시각 FAIL이며 숫자 PASS로 덮지 못한다.
6. 새 파일은 **role_B 아래 미승격 시험 DDS**로 보존한다. source/CLEAN 분리, 전/후 마스크·타셀 0, 저장 DDS 디코딩 일치, 실제 QA evidence, visual PASS와 production_pixel_guard 최종 manifest가 있을 때만 official hd_candidates 변경을 **별도 통상 승인 절차**로 검토한다. C2 / C3 / 사용자 실게임 검사는 각자 독립. `RUNTIME_VALIDATION=UNTESTED` 유지.
7. 생성물·QA·queue/WORKLOG/STATUS/progress/resume 기록을 같은 브랜치에 commit/push하고 **원격 HEAD 재조회**. 사용자 재배포 전에는 Docker 프로세스를 직접 교체하지 않는다.

## SHA 바인딩 imagegen_requests manifest 예시

`localization/graphics/role_B/imagegen_requests/q060_<genid>.json`

```json
{
  "schema": "outrun-b-imagegen-v1",
  "role": "B",
  "queue_index": 60,
  "target_text": "최고 기록:",
  "generator": {
    "provider": "chatgpt-image-generator",
    "generation_id": "ACTUAL_GENERATION_ID",
    "prompt": "EXACT_PROMPT"
  },
  "source": {"path":"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/PIN/Release/...dds","sha256":"64_HEX"},
  "official": {"path":"localization/graphics/hd_candidates/...dds","sha256":"64_HEX"},
  "clean": {"path":"localization/graphics/plate_library/objects/...png","sha256":"64_HEX"},
  "removal_mask": {"path":"localization/graphics/plate_library/objects/...png","sha256":"64_HEX"},
  "plate_review": {
    "status": "PLATE_PASS",
    "ref": {"path":"localization/graphics/plate_library/reviews/...json","sha256":"64_HEX"}
  },
  "generated": {"path":"localization/graphics/role_B/imagegen_requests/q060_<genid>.png","sha256":"64_HEX"},
  "source_bbox": [2179,340,3028,474],
  "placement_bbox": [2190,344,3012,469],
  "replace_roi": [2090,337,3120,485],
  "fit_mode": "contain",
  "output_dir": "localization/graphics/role_B/imagegen_trials/q060_<genid>"
}
```

예시의 `PIN`, `64_HEX`, `ACTUAL_GENERATION_ID`는 **실제 작업 시 반드시 정본으로 치환**한다. 이 예시는 실행 가능한 실제 승인 자료가 아니다.

## A/B 생산 경쟁 관측

- A는 기존 방식, B는 imagegen으로 **각자 독립 자산**을 생산한다. 서로 상대 레인 자산을 제작해 중복하지 않는다.
- 기록 항목: 최초 실제 생성/렌더 timestamp, 첫 persisted DDS SHA, 생성 시도 수, 재제작/리워크 횟수, 후보당 생산 시간, 첫 독립 C PASS 소요시간, C3 엄격 PASS, 사용자 실기 재불량률.
- 비교에서 `PRODUCER_PASS`와 `C2_PASS`, `C3_STRICT_PASS`, 실제 `INGAME_PASS`를 반드시 별도 분모/분자로 표기한다. 선행 준비가 오래된 자산을 정직하게 표시하고, 입력 난이도(P0/P1/UI군)별 층화를 제공한다.
- 중복 SHA/재보고/재실행은 새 생산 및 점수 성과가 아니다. **경쟁 점수(계정 AI SCOREBOARD)와 생산 속도/검수 지표는 별개의 기록**이다.
