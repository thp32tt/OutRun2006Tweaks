# OutRun 2006 VR — Dino 246 GTS cockpit v12 test

**2026-11-04. 실험용 HMD 테스트 패키지입니다. 실제 PC/Quest3에서 실행 검증되지 않았습니다.**

## 구성
- 게임 내 실제 Dino 모델 포맷 PMT에 신규 운전석 메시를 추가한 테스트입니다. GLB 미리보기 이미지만 넣은 것이 아닙니다.
- 1인칭 Dino 246 GTS 시점만 대상으로 합니다. 나머지 차종은 변경하지 않습니다.
- 2026-11-04 제작한 경량형 v12 실내: 실내 17,506개 삼각형, 28개 재질/메시 그룹, 10,082개 정점.
- 계기판, 좌측 핸들, 좌석, 센터터널, 기어봉 등이 포함됩니다. 이 단계에서는 신규 핸들/계기판 애니메이션이 정적입니다.
- 원본 Dino 메시와 16개 다른 PMT 오브젝트를 유지하는 방식으로 새 실내 메시 그룹을 추가합니다.
- 기존 QuestCockpitV2 VR 실행/카메라/동승자/유리 옵션은 포함된 기존 실행 스크립트를 사용합니다.

## 게임 설치
1. 게임과 OpenXR 호스트를 완전히 종료하고 게임 폴더를 백업합니다.
2. ZIP 내용물을 **OR2006C2C.exe가 있는 원본 OutRun 게임 폴더에** 압축해제합니다.
3. 기존 게임 디렉터리에 **Cars\\obj_plcar_dino_pmt.sz** 파일이 있어야 합니다. 이 파일이 이미 개조되어 있으면 패치가 안전하게 거부됩니다.
4. **INSTALL-DINO-COCKPIT-V12.cmd** 를 실행합니다. SHA256 검증을 통과한 경우에만 원본 파일을 .dino-v12-original.bak 으로 먼저 백업한 뒤 새 모델을 적용합니다.
5. Quest3 + VDXR를 연결한 뒤 **RUN-QUEST-COCKPIT-V2.cmd** 로 VR을 시작하고 **Dino 246 GTS 선택 → 1번 운전석 시점**으로 변경하여 확인합니다.
6. 테스트가 끝나면 **RESTORE-DINO-COCKPIT-V12.cmd** 로 원본 차량 PMT로 되돌립니다. 게임이 실행 중일 때는 설치/복원하지 마세요.

Python이 없어도 테스트 ZIP에 포함된 `DinoCockpitV12.exe`로 설치/복원할 수 있습니다. EXE가 없는 소스 패키지를 이용한다면 Python 3이 필요합니다.

## 안전 정책
- 원본 실행파일, 기존 안정 v0.01 릴리즈, 기존 GitHub의 운전석 브랜치는 수정하지 않습니다. 이번 패치는 분리된 실험본입니다.
- 원본 파일 해시가 **1f8dfcb7b875d46bd58f110518c1a8815355162d4412fa4a0d4e2e2301d86284** 와 일치하지 않으면 자동 패치를 거부합니다.
- 원본 PMT 변경에 대한 자동 복원 백업: `Cars/obj_plcar_dino_pmt.sz.dino-v12-original.bak`.
- PC/Quest3 실기 테스트: **UNTESTED**. 화면 가림, 차량 외부와 실내 중첩, 반사/그림자/애니메이션/텍스처 표현, 충돌, 성능은 검증되지 않았습니다.
- 설치 후 실행 안 되거나 시야가 가려지면 바로 종료한 다음 복원하세요.

## 빌드 출처
- QuestCockpitV2 기반: `thp32tt/OutRun2006Tweaks@vr-quest-cockpit-v2`
- Windows x86 DLL CI: `01cd99e3113cb9a8ed662beadab0600efdf4709a`
- QuestCockpitV2 OpenXR host + 실행 스크립트: `cbf035bd72d8bfd13080ed5c50822e45cef32457`
- 게임 원본 모델/텍스처는 ZIP에 넣지 않았으며, 사용자 게임 폴더 내의 원본 파일에 새 실내 모델만 결합합니다.
- 파일 검증: 17개 PMT 오브젝트, 총 79,007개 GPU vertex index 참조 정적검증 성공. 설치 및 복원 byte-exact 통과. VR 실기 미검증.