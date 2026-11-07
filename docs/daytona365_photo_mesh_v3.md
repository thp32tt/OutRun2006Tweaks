# Daytona 365 GTS/4 사진 기반 실제 메시/텍스처 리워크 v3

- **차량:** 두 번째 Ferrari 365 GTS/4 Daytona. Dino 246 원본, 기존 Dino 외부모델, 기본 게임 PMT 원본은 변경하지 않는다.
- **사진 참조:** 사용자 N100 `outrun2_vr_refs/20261104_16car_cockpit/02_365_GTS4_Daytona`. 실차 사진 원본은 공개 GitHub에 업로드하지 않는다.
- **실제 게임 메시:** 원본 PMT object0 좌표를 따라 시트·센터터널·뒤쪽 덮개를 세분화하고 표면 법선 방향으로 약 4mm 보정, 시트 가장자리 파이핑 36개 경계 구간, 사진에 보이는 검정 띠 8개를 삼각형 표면에 직접 맞춰 배치. 계기판 금속 베젤, 1024px 원본 UV 계기판, 실물 스위치 사진 투영, 변속기 게이트 외곽 추가. 총 11개 메시 그룹, 2,815정점 / 3,854삼각형, 7개 BaseColor 재질.
- **실제 게임 파일:** N100 개인 작업 공간 `work_handoff/daytona365_rework_20261107/runtime_v3/Daytona365_Cockpit_R26_v2.ovc` (버전명은 현행 C++ 로더 하드코딩을 유지하기 위함), `obj_plcar_dayts_pmt.sz` 6종 원본 DDS 교체본. 원본 차량 Draw 및 원본 핸들은 그대로 남기므로 **원본 차체 전체 중복 생성은 하지 않음**.
- **지원 범위:** D3D9Ex OVRCABH2는 BaseColor DDS + 정점/노멀/UV만 사용. 저장된 Normal/Roughness 파일은 **오프라인 향후 확장용**이며 실기에서 현재 PBR로 표시된다고 주장할 수 없음.
- **편집 가능한 모델:** `Daytona365_Cockpit_SOURCE_ALIGNED_v3.obj` + MTL + photo BaseColor, 정상 좌표 저장.
- **검증:** v3 모델/OVC CRC·DDS 크기·인덱스 경계; 원본 PMT 30개 오브젝트·39개 텍스처·UV/정점/나머지 DDS 동일성 및 파일 무변경; 원본 모델 별도 저장. N100 원본이 없는 공개 CI에서는 4개 합성 회귀 테스트.
- **미검증:** Quest 3 실제 시야/장착 위치, Daytona `car_kind_11 == 2` 런타임 확인, 렌더링 순서·깊이 버퍼·실제 질감 품질. 테스트 브랜치이며 안정판 아님.
- **포장:** `Daytona365_PHOTO_MESH_TEXTURE_TEST_v3_PRIVATE.zip` (N100 전용). 공개 재배포용 게임 원본 파일을 GitHub에 커밋하지 않는다. 설치 전 v2 작업 시 원상복구를 권장한다.
- **패키징:** `tools/build_daytona365_photo_mesh_v3.py`, `tools/paint_daytona365_native_photo_v3.py`, `tools/package_daytona365_photo_runtime_v3.py`. N100 사설 폴더에 v2 기반 스크립트 및 개인 참조 사진이 있어야 실행 가능.

> 참고 이미지의 실제 외관은 품질 목표이며, GLB/OVC 메시에 사진 한 장을 붙였다고 모델이 자동으로 목표 수준에 도달하지는 않는다. 손수 수정해야 할 형상 및 HMD 재질 검수는 별도 남음.
