# OutRun 2006 VR Dino 246 GTS v13 — Textured Cockpit (실험용)

2026-11-04 기준. Quest 3/VDXR 실제 게임 화면은 아직 검증되지 않았습니다 (**RUNTIME_VALIDATION=UNTESTED**).

## v12 대비 차이점

- 이전 테스트 빌드의 신규 운전석 모델은 UV만 갖고 있고 게임 PMT에는 단색 재질을 사용했습니다.
- **이번 v13은 갈색 가죽/검은 가죽 2개를 실제 DDS DXT1/BC1 텍스처로 사용하도록 변경**했습니다.
- 신규 텍스처: 128×128, 8개 MIP 레벨, 각 11,136바이트(버퍼 정렬 포함).
- 기존 Dino 원본의 41개 텍스처는 모두 보존하며 41/42번 슬롯을 추가합니다(총 43).
- 외관/원본 차량 메시 17개 오브젝트는 GPU 데이터 byte-equality를 유지하면서 포인터/버퍼 위치만 재배치합니다.
- 좌석/도어 갈색 가죽과 핸들 검정 가죽, 대시보드 윗면, 실내 카펫 등 **6개 재질 그룹**에 게임용 텍스처를 연결합니다.
- 나머지 크롬/금속/바늘/다이얼 등은 아직 기본 색상 재질입니다. 512px PBR 노멀/roughness는 D3D9 고정 파이프라인으로 아직 포팅되지 않았습니다.
- 원본 유리/승객/운전석 카메라 옵션은 기존 QuestCockpitV2 VR 실행 스크립트 그대로입니다.

## 테스트 방법

1. OutRun 2006 게임을 종료하고 기존 게임 디렉터리를 백업합니다.
2. ZIP 파일 전체를 원본 `OR2006C2C.exe` 폴더에 덮어씁니다. 이전 v12를 사용한 경우에도 지원합니다.
3. **INSTALL-DINO-COCKPIT-V13-TEXTURED.cmd** 실행. 패치할 `Cars/obj_plcar_dino_pmt.sz`가 존재해야 합니다.
4. 원본 SHA가 일치하거나 이전 v12 설치 SHA와 백업이 둘 다 검증되면 v13으로 전환합니다.
5. Quest 3 + VDXR 연결 후 **RUN-QUEST-COCKPIT-V2.cmd** 를 실행하고, Dino 246 GTS를 선택해 **운전석 1번 시점**에서 확인합니다.
6. 테스트 후 게임 종료 → **RESTORE-DINO-COCKPIT-V13-TEXTURED.cmd** 로 원본 PMT로 복원합니다.

원본 PMT SHA256: `1f8dfcb7b875d46bd58f110518c1a8815355162d4412fa4a0d4e2e2301d86284`
새 PMT SHA256(정적 레퍼런스): `83199d4f62519d8c0d77ed9944926d279832a1f9ee78cf04963d6218211e15ad`

## 검증

- PMT 구조 재파싱: 17개 오브젝트/43개 텍스처, 79,007개 GPU 인덱스 확인
- 원본 41개 텍스처의 XPR descriptor 내용 보존 확인
- 원본 26개 GPU 버퍼 각각 index/vertex byte-equality 검사 통과
- 신규 BC1 DDS 2개 디코딩, 텍스처 슬롯/메시 재질 연결 검사 통과
- 신설 재질용 모델 17,506개 삼각형, 28개 material groups 유지
- v13 신규 설치, 원본 복구, 복구 후 재설치, 기존 v12→v13 교체 후 원본 복구: 모두 바이트 단위 통과
- **실기: 미검증**. 실제 PC 게임 PMT 로더/셰이더 호환성, HMD 화면 색상/시야/성능은 확인하지 못했습니다.

텍스처 출처: Poly Haven `brown_leather` (<https://polyhaven.com/a/brown_leather>), CC0 (<https://polyhaven.com/license>). 이 패키지에는 게임 원본 DDS/GLB/PMT를 포함하지 않습니다. 기존 v0.01 릴리즈와 주 개발 브랜치는 변경하지 않았습니다.