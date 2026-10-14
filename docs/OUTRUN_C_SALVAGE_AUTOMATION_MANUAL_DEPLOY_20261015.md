# C-SALVAGE 자동작업 적용 / 사용자 수동 Portainer 배포

적용 범위: \`thp32tt/OutRun2006Tweaks@korean-localization-recovery-20260928\`  
코드 상태: **GitHub staged + 격리 실행 테스트 확인**. **Portainer 배포 전 / 실제 Docker 운영 E2E 미검증**.
선행 설계: [OUTRUN_C_SALVAGE_SLOT_20261015.md](OUTRUN_C_SALVAGE_SLOT_20261015.md)

## 안전하게 구분된 역할

- A/B: 기존 ChatGPT 이미지 생성용 슬롯과 대화/스케줄 그대로 유지.
- C1: 기존 독립 4~8개 QA용 브라우저/슬롯 그대로 유지.
- C-SALVAGE: **새로운 별도 offline CPU service**, 기존 C1 탭을 대체하지 않으며 ChatGPT 창·ImageGen·API를 전혀 호출하지 않음. 사용자 Portainer **수동 Pull and redeploy** 후에만 30분마다 자동 반복 실행.
- C2: 기존대로 비활성. C-SALVAGE는 스스로 C1/C3/GAME PASS 기록을 만들지 않음.

## GitHub 파일

1. 자동 워커: \`tools/localization/c_salvage_worker.py\`.
2. SHA 고정 합성기/시험 DDS: \`tools/localization/c_salvage_compose.py\`.
3. 독립 실행 이미지: \`docker/localization-production/Dockerfile.c-salvage\`.
4. 기존 Git 기반 Portainer Stack의 추가 서비스 override: \`docker/localization-production/portainer-git-c-salvage.override.yml\`.
5. 정책: \`localization/controller_roles.json\`; 기존 활성 A/B/C1 탭 순서/분별 dispatch를 유지.
6. PSD/source 플레이트 작업자: `tools/localization/c_salvage_plate.py`, `plate_jobs/*.json` 처리.
7. 테스트 전용 CI: \`.github/workflows/localization-c-salvage-ci.yml\` (production run 아님).

## 실제 자동 반복 작업: 30분마다 최대 10개 신규 후보

### 검토된 plate_jobs 자동 처리

\`plate_jobs/*.json\`이 추가되면 동일한 30분 순환의 나머지 최대 10건 작업 슬롯에서 \`tools/localization/c_salvage_plate.py\`를 수행한다. 파일은 \`outrun-c-salvage-plate-v1\` 스키마이며 \`bundles/\` 아래 입력 파일에 대한 상대경로와 실제 SHA256을 명시해야 한다.

\`\`\`json
{
  "schema": "outrun-c-salvage-plate-v1",
  "orientation": "IDENTITY",
  "source_dds": {"path": "Q012/canonical.dds", "sha256": "<actual DDS SHA256>"},
  "removal_mask": {"path": "Q012/english_removal_mask.png", "sha256": "<actual PNG SHA256>"},
  "protected_mask": {"path": "Q012/protected_mask.png", "sha256": "<actual PNG SHA256>"},
  "source_transparent_under_english_reviewed": true
}
\`\`\`

PSD가 있는 경우 선택된 PSD 원본 SHA와 \`english_layer_paths\`를 추가하면 원본 Photoshop 레이어를 격리 내보내기 한다. 원본 native DDS 크기/보호 픽셀/제거 범위와 불일치하는 PSD는 그대로 합성하지 않는다. PSD가 없거나 canonical 원본과 일치하지 않는 경우 위처럼 **사전 검토된 source-transparent 마스크**가 있을 때만 source fallback CLEAN 후보를 만든다. 불투명 배경은 복원 가능한 원본 계층이 없으면 HOLD한다. 생성되는 \`plates/<SHA>/clean_candidate.png\`는 항상 \`CLEAN_CANDIDATE_REQUIRES_INDEPENDENT_C1_PLATE_REVIEW\`이며, \`recipes/\`의 별도 승인된 native 합성 recipe로 이후 단계에서 사용한다. 실제 PSD 레이어 경로를 추측해 자동으로 선택하지 않는다.

- **READ ONLY**: A/B가 이미 저장한 \`ab_batches/candidate_outputs/{A,B}/*.png\`를 실물 SHA256/실제 PNG 헤더로 검증하고 중복 항목 건너뜀. 갱신된 마스크/후보 SHA는 새 작업으로 인식.
- 추출: 알파 투명도가 뚜렷한 후보는 알파 기반 글자/효과 *후보*만 crop → \`lettering_PROPOSAL.png\`, 정확 SHAs, 원본 경로, 좌표, \`receipt.json\` 보관. 투명 PNG에도 원본 로고/아이콘이 섞였을 수 있으므로 **\`LAYER_PROPOSAL_REVIEW_REQUIRED\`**로만 보관. 이미지 속 글자 정확성은 C1/수동 확인 대상.
- 불투명 후보: 자동 글자 탐지/AI 생성/자동 배경 날리기 금지. 별도의 동일 크기 0/255 텍스트 마스크 \`<generated-stem>.mask.png\`가 있으면 그 영역만 후보층으로 분리, 없으면 \`HOLD_OPAQUE_GENERATED_REQUIRES_EXPLICIT_GLYPH_MASK\`.
- 원본 검색: 동일 tile basename에서 \`_k\`를 뺀 파일을 \`a_tile_batches/upright_sources\`, \`ab_batches/upright_sources\`에서 확인. 없으면 \`SOURCE_TILE_MISSING_NEEDS_STAGING\`, DDS 원본이라고 속이지 않음.
- PSD 검색: 저장소에 SHA 고정된 \`localization/graphics/plate_library/PSD_UPSTREAM_FULL_INDEX.json\`에서 queue ID와 texture hash를 함께 매칭. 원본 upstream commit, blob SHA, GitHub 복사 현황, 로컬 실물 PSD 존재 및 기록된 SHA256이 있으면 검증. **PSD 검색 일치 = 레이어 분리/영문 제거 성공 아님**. Docker 기본 구성은 카탈로그만 이미지에 포함하며 대용량 PSD는 포함하지 않음; 필요시 별도 오프라인 staging.
- CLEAN: 원본 PSD에서 선택된 English/effect 레이어나 SHA-pinned 정본 HD DDS+정확 영문 마스크가 준비된 경우에만 \`c_salvage_compose.py\`의 recipe를 처리. PSD 글자 그룹이 불명확하면 기존 \`psd_layer_workbase.py\`의 분리·검수 작업 선행. PSD가 없고 배경 투명한 경우 \`clean_method=TRANSPARENT_MASK_TEST_ONLY\`와 *정확* 제거 마스크를 사용할 수 있으나 opaque/복잡 배경은 독립 복구/플레이트 검수가 필요. 자동 상상 픽셀/확장/영문 잔상 위험을 감수해 결과를 승인하지 않음.
- 합성: 검수된 번역/마스크/SHA/원본 DDS/READABLE PNG/원본 UI cell/보호 영역/좌표·방향의 **manifest**를 \`recipes/\`에 제공하면 C가 원본 포맷 조건 확인 후 별도 \`composites/\`에 중간 PNG, 추출층, CLEAN 후보, 지원 DDS 시험본, JSON 결과를 출력. BGRA32 single mip만 현재 내부 직접 인코딩. DXT/BC 등 압축 DDS는 **\`ENCODER_UNSUPPORTED\`**로 HOLD하고 기존 원본 코덱 변환 파이프라인/검수가 필요.
- 결과는 \`TEST_ONLY\` 또는 \`HOLD\`만 가능하며 \`hd_candidates/\`, \`approved_dds/\`, 게임 설치 폴더 및 A/B state/queue를 건드리지 않음. C1 독립 QA, C3(고위험)와 사용자 실게임 확인 전 정식 최종본 승격 금지.

## Portainer 기존 Git Stack — 사용자가 수동으로 배포할 때

**필수 사전 조건**: Stack이 실제로 이 Git 저장소의 해당 브랜치를 build context로 사용 가능한지, 현재 base Compose 파일 경로·image build context·Git Additional compose path를 먼저 확인. 실제 운영 Stack이 다른 Git 저장소를 보는 경우 *동일 내용의 파일을 그 저장소에 반영*해야 함. 이 override를 독립 Stack으로 올리거나 C1 슬롯과 교체하지 않음.

준비 환경변수:
- \`C_SALVAGE_INPUT_HOST_PATH\`: 실제 기존 \`image-src\`의 호스트 절대경로. 참고로 2026-10-15 N100에서 관찰된 원본 경로는 \`/home/chatgpt-runner2/work/image-src\`; **실제 Portainer 노드가 동일 호스트인지 먼저 확인**.
- \`C_SALVAGE_OUTPUT_HOST_PATH\`: 별도로 신규 생성한 쓰기 가능한 C 전용 절대경로. 기존 A/B 출력 폴더, 그 부모 내부 또는 컨트롤러 \`sent/\` 폴더가 아니어야 함.
- \`C_SALVAGE_RUN_AS\` (선택): 호스트 출력 폴더 쓰기 권한이 있는 UID:GID. 기본값 \`1000:1000\`, 실제 권한 검증 필요.

절차:
1. 기존 Stack의 Git URL/ref, 기본 Compose, 추가 경로, 현재 컨테이너 목록, volume 마운트를 기록/백업. 자동 GitOps 재배포 비활성 여부 확인.
2. 기존 Compose 옆에 **추가 파일** \`docker/localization-production/portainer-git-c-salvage.override.yml\`만 적용(Portainer Git Additional paths). 파일의 \`build.context: ../..\`가 실제 Git Stack build context에서 해석되는지 사용자가 config 검증; 실제 context와 다르면 수동으로 재조정.
3. 사전 준비 디렉터리: C 출력의 \`masks/\`, \`recipes/\`, \`bundles/\`; 생성 권한을 확인. \`bundles/\`는 C용 원본 DDS/승인 CLEAN/PNG 등을 별도로 복제해 검수된 recipe에서 상대경로 SHA256로 참조.
4. 사용자가 직접 Portainer에서 **Pull and redeploy**. Git 커밋이나 테스트 워크플로만으로 배포하지 않음.
5. \`outrun-c-salvage-offline\` 컨테이너의 \`last_cycle.json\`, \`candidates/*/receipt.json\`을 확인. 한 주기에 최대 10건, 30분마다 반복. 기존 A/B/C1을 유지하고 C는 네트워크 없는 제한된 CPU 프로세스.
6. 작동이 맞지 않으면 override 추가 경로만 제거하고 사용자가 기존 Stack을 수동 재배포. 기존 A/B 데이터와 C1을 수정·삭제하지 않음.

## 실제 결과 폴더

C 호스트 OUTPUT 내부:
\`\`\`
last_cycle.json
candidates/<role-queue-generatedSHA-maskSHA>/
  lettering_PROPOSAL.png  # 가능한 경우에만
  receipt.json            # 항상
masks/<generated-stem>.mask.png
plate_jobs/<asset-id>.json
plates/<plate-job-sha>/
  english_original_readable.png
  clean_candidate.png
  english_removal_mask.png
  receipt.json
recipes/<asset-id>.json
bundles/<asset-id>/...      # 별도 정본 DDS/PNG/CLEAN/승인 마스크
composites/<recipe-sha>/
  korean_letter_only.png
  clean_candidate.png
  intermediate_readable.png
  intermediate_native_raw.png
  intermediate_TEST_ONLY.dds  # BGRA32 single mip 검증 조건 충족 시에만
  C_SALVAGE_TEST_ONLY.json
recipe_failures/<recipe-sha>.json
\`\`\`

## 확인된 시험과 미검증 사항

- N100 격리 실제 A Q012(투명) 및 B Q092(불투명) 후보 2장: 투명 글자층 제안 1, 불투명 마스크 대기 1, 동일 입력 두 번째 실행 신규 0; A/B 원본은 불변.
- 합성기 합성/마스크 보호/SHA 검증 3건 합성 시험 통과, synthetic BGRA32 1-mip DDS 재디코딩 PASS.
- 별도 synthetic worker 투명/불투명/명시마스크/PSD-index/재실행/불완전 recipe fail-closed PASS.
- **실제 Portainer 스택 Compose 렌더, 이미지 build, 배포, 290장 전체 결과 생성, 실제 PSD layer export, 고난도 원본 DDS CLEAN, DXT5 최종 저장본 및 실게임 런타임은 여전히 \`UNTESTED\`.** CI push 워크플로 실행 여부는 Actions 로그로 별도 확인.
