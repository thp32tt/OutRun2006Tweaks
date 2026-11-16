# OutRun 2006 VR · Ferrari 16종 외부 모델 일괄 변환 준비 패키지

검토일: 2026-11-16. **이 파일은 15종의 완성 외부 차량 모드를 포함한 배포판이 아닙니다.**

## 현재 확정된 사실

- 전체 목록: `registry.json`의 16종. F50는 별도의 HQ V2 직접 설치 ZIP이 이미 존재합니다.
- 2026-11-16 N100 및 연결된 Google Drive 조사에서 **F50 외의 완성 외부 차량(차체+실내) GLB는 발견되지 않았습니다.**
- Dino 246 v3/v4는 실제 3D 운전석 GLB, Daytona는 원본 게임 유래 운전석 GLB 및 Blender가 있지만, 둘 다 **F50처럼 차량 전체를 교체할 수 있는 완성 외부 차량 모델이 아닙니다.**
- N100에 있는 나머지 16종의 `original_native.obj`/PMT는 **원본 게임 모델**입니다. 이 원본을 외부 모델이라고 주장하거나 품질을 높였다고 주장하지 않습니다.
- 실제 외부 모델 파일 없이 다른 15종을 고품질 외부 모델로 변환 완료했다고 보고할 수 없습니다.

## 구현된 것

`tools/ferrari_batch_converter.py`는 16종을 개별 식별하여 사용자 제공 **완전 내장형 GLB(glTF 2.0)** 를 실험용 `OVRCABH3`로 변환합니다.

- 원본 삼각형 개수 보존(디시메이트/LOD 축약 없음), 노드별 변환 및 인덱스 보존
- 원본 텍스처를 임의 다운스케일하지 않음. 알베도, 노멀, 금속성/거칠기/오클루전 채널을 DDS와 PBR로 패킹
- 투명 재질을 독립 그룹으로 분리. 단, 게임의 전용 유리 렌더러가 필요하며 완전한 광학 투과 표현은 아닙니다
- SHA-256, GLB 바이너리 범위, 머티리얼/텍스처/UV, 출력 CRC·DDS mip·인덱스 검증
- 차종 ID/축/피벗/높이 검증값이 없는 입력은 **자동 변환을 차단**합니다
- 변환 실패 시 기존 게임 파일은 건드리지 않음. 기존 OVC 파일도 덮어쓰지 않음

### 준비

Windows 또는 Linux의 Python 3.10 이상과 `numpy`, `Pillow`를 설치합니다.

```bash
python -m pip install -r requirements.txt
python tools/ferrari_batch_converter.py audit --workspace .
python -m pytest -q tests/test_converter.py
```

각 차종에 다음 두 파일이 필요합니다.

```text
sources/<차종 ID>/source.glb
sources/<차종 ID>/source.json
```

`source.json` 구조는 `source.example.json`을 참조합니다. **차종 ID와 실제 원본 SHA-256, 전체 차량 모델 여부, 4×4 좌표계 변환, OutRun Y-up 현지 좌표 및 조향/높이 검증**이 필요합니다. `alignment_verified=true`는 실제 확인 후에만 사용하십시오. 원본 외부 모델 없이 파일을 채우거나 임의 좌표를 승인하지 마십시오.

```bash
python tools/ferrari_batch_converter.py convert --workspace . --car 288gto
python tools/ferrari_batch_converter.py convert --workspace .
python tools/ferrari_batch_converter.py verify --workspace .
```

결과는 `outputs/<차종 ID>/<차종 ID>_External_Test.ovc` 및 `conversion_report.json`에 저장됩니다.

## 주요 제한

- **실제 게임에서 자동으로 16종을 교체하지 않습니다.** 현재 F50 HQ V2 게임 런타임은 F50 전용이며, 다른 차종의 `car_kind`/`car_id` 대응 관계와 정상적인 양안 렌더·바퀴 애니메이션까지 검증해야 합니다. 다른 차량용 OVC를 F50로 이름만 바꿔 설치하지 마십시오.
- GLB가 이미 **게임 기준 X-right/Y-up/Z-longitudinal, 미터 단위**로 정렬돼 있어야 합니다. 소스 게임의 축, 피벗, 차량 전후/좌우를 추정해 자동 승인하지 않습니다.
- D3D9Ex 32비트 로더의 현재 고정 형식상 DDS는 최대 2048px(2의 거듭제곱), 단일 모델 GPU 데이터 112MiB, 파일 128MiB, 인덱스 그룹 512개 제한입니다. 품질을 몰래 줄이지 않고 이 제한을 넘으면 `BLOCKED` 처리합니다. 더 큰 모델은 향후 로더 스트리밍/BC 압축이 필요합니다.
- skin/morph/vertex-color/외부 이미지 URI, glTF 확장에 의존한 변환은 소스 손실 없이 재질/형상을 베이크한 뒤 다시 제공해야 합니다.
- 외부 모델의 바퀴/조향/차체 애니메이션은 현재 정적 sidecar에서 재현되지 않습니다.
- Assetto Corsa `KN5`와 GTA 특수 차량 포맷을 직접 읽지는 않습니다. 먼저 적절한 Blender/정식 임포터로 텍스처를 포함한 GLB로 내보내야 합니다.
- 모델 권리 미확인 상태에서는 제삼자 GLB/OVC를 공개 GitHub·Discord·릴리스에 포함하지 마십시오. 변환 프로그램(코드)만 공개해도 됩니다.
- `imsi1`의 과거 **원본 PMT 운전석 메시 리워크 큐**와 이 외부 모델 변환 실험은 별도 작업입니다. 기존 `imsi1` 큐 상태, 게임 PMT, 원본 게임 실행 파일, 기존 F50 HQ V2 ZIP은 수정하지 않았습니다.

## 소스 위치

- N100 외부 F50: `mod_trials/f50_glb_poc_20261115/external_1995_ferrari_f50.glb`
- N100 Dino 운전석 v4: `Dino246_ConceptDetail_v4_EditableGLB_20261106.zip` (부분 모델, 전체 차량 아님)
- N100 Daytona 편집 운전석: `work_handoff/daytona365_rework_20261107/` (원본 게임 유래, 전체 외부 차량 아님)
- 원본 PMT: `rea-input/outrun/outrun2006/Cars/`
- 원본 UV/사진 참고: `stableprojectorz_ferrari16_20261114/vehicles/` (외부 고품질 차량 모델 아님)

기존 F50 HQ V2 게임 테스트 설치본은 그대로 유지합니다. 이 ZIP은 새로운 외부 모델 원본을 확보했을 때 반복적으로 활용하는 **준비/검증 도구**입니다.