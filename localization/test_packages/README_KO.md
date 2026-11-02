# OutRun 2006 한글화 1차 실제 DDS 테스트 및 2차 A/B 준비 (2026-11-02)

## 1차: 실제 DDS 두 파일 다운로드
- [Q032 랭킹 + Q241 로딩 DDS 2개 ZIP](./OUTRUN_KOR_Q032_Q241_DDS_TEST_ONLY.zip)
- ZIP SHA256: `63d713551e4018f4f1cc131db230e422ef2ca643d3bffb99a0a8c26c39203633`
- ZIP 크기 581,991바이트, 원본 DDS 경로 2개, `PILOT_MANIFEST.json`, 2 QA receipt 포함.
- GitHub의 **실제 DDS**를 가져온 것이며 ImageGen 재생성/모의 JPG가 아니다.
- **TEST_ONLY / RUNTIME_VALIDATION=UNTESTED**. ZIP은 설치 프로그램이 아니다. *별도 빈 폴더에 풀어 먼저 파일을 확인*하고 게임/HD 텍스처 경로를 알아낸 뒤 수동 백업/시험해야 한다.

### 2 DDS 경로
- `textures/load/spr_sprani_FLAG_RANK_Exst/DCC7B488_512x256.dds` (Q032)
- `textures/load/spr_sprani_sumo_loading_Exst/E1639D2E_256x64.dds` (Q241)

## 전체 104 DDS 시험본
N100에 원본 해시 고정으로 보존:
`/home/chatgpt-runner2/work/image-src/text_roi_batches/offline_overlap_v3_ink_test_only/OUTRUN_OFFLINE_KOREAN_TEST_ONLY_96e9372fb718.zip`

- 140,069,153 bytes, SHA256 `84d92c22ff957ebeaa3156165b9ed7ef769802756ddc183d18bd586ff5c1ddf3`
- 104 DDS, 104 QA receipts, 1 TEST_ONLY_MANIFEST.json; 압축 해제 총 크기 약 2.19GB.
- 이 ZIP은 **GitHub에서 다운로드 가능한 소형 2-DDS ZIP과 서로 다르다**. N100 원본을 별도로 접근/복사해야 한다.
- 전체 시험용 파일은 비압축 RGBA32/밉1일 수 있어 VRAM·성능·호환성이 미검증. 자동 게임 설치 금지.

## 2차: 기존 ImageGen PNG 재활용 준비
- [A/B 후보 → 활성 ROI 대응표](./ab_preparation_20261102/ab_roi_crosswalk.csv)
- [실제 읽기 전용 재고 검사 결과](./ab_preparation_20261102/audit_summary.json)
- [재검사용 소스 코드](../../tools/localization/existing_korean_candidate_audit.py)
- N100 `work/image-src/text_roi_batches/production_manifest.json`: 1,002행 = 활성 ROI 954 + 폐기된 A→B 재배정 행 48.
- 후보 PNG 955개 중 954개가 활성 ROI 954개와 **정확히 1:1 파일명 매칭**; 나머지 1개는 레거시 Q104 실험 이미지. 이 매칭은 QA/번역/깨짐 PASS가 아님.
- A/B 소스 `work/image-src/text_roi_batches/candidate_outputs/{A,B}`.
- 읽기 전용 N100 실행: `python3 work/image-src/text_roi_batches/existing_korean_candidate_audit.py`.

### 다음에 필요한 합성 게이트
1. 각 ROI에서 실제 PNG SHA 확인, 정확한 원본 HD PNG/DDS SHA·좌표/플랫폼 variant 매칭, C1 검수 결과 병합.
2. 독립 승인 CLEAN 플레이트/PSD로 원문 영어만 제거. 인접 아트/알파/2줄·기울기 손상 금지.
3. 한글 글자만 ROI/UV 경계 안에 종횡비 유지 합성 → 원본 DDS 형식/밉 보존 가능한 변환 및 RAW/FLIP-Y 검증.
4. 먼저 Q032/Q241 두 DDS로 실게임에서 파일 소비 여부 확인한 후 HUD Q051/미션 Q054/GOAL Q057로 확대.
5. 사용자 실게임 PASS 전 최종 배포 승인 금지. VR/FFB/DX11/DXVK 및 Portainer 배포 변경 없음.

문서: [기존 한글 PNG/DDS 기반 전체 적용 계획](../../docs/OUTRUN_EXISTING_KOREAN_ASSET_INTEGRATION_PLAN_20261102.md)
