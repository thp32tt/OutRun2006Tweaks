# OutRun 2006 VR · Ferrari 16종 외부 모델/계기판 고도화 파이프라인

검토일: 2026-11-16. 이 디렉터리는 **전 차종을 동일한 고품질 외부 모델 규격으로 변환하기 위한 도구**이며, 권리 확인되지 않은 제3자 차량 모델 자체를 공개 배포하지 않습니다.

## 현재 확보 상태

- 런타임 대상은 원본/튜닝 변형을 포함한 플레이어 차량 ID 0..29이며, runtime_car_id_manifest_20261116.json에 고정 매핑되어 있습니다.
- 현재 작업자료에서 실제 외부 차량 원본/변환물이 확인된 것은 **F50, 288 GTO, F40**입니다.
- 그 외 Ferrari 기본 차종은 원본 게임 PMT/참고 사진은 있으나, 완성된 외부 full-car GLB가 모두 확보된 상태는 아닙니다.
- 따라서 소스가 없는 차종을 "모델링 고도화 완료"로 표시하지 않습니다. 런타임과 변환 규격은 모든 ID를 수용하지만, 실제 교체는 설치된 검증 sidecar만 사용하고 나머지는 원본 게임 차량으로 fail-closed fallback 합니다.

## OVRCABH4 고도화

tools/ferrari_batch_converter.py는 완전 내장형 glTF 2.0 GLB를 OVRCABH4 sidecar로 변환합니다.

- 삼각형 보존: 디시메이트/LOD 축약 없음
- 원본 노드 변환, 인덱스, UV, 노멀 보존
- 알베도 + 노멀 + ORM(occlusion/roughness/metallic) PBR
- 유리 그룹 분리 및 기존 depth/fallback 안전장치 유지
- 차량 최저점 기반 지면 파묻힘 방지
- SHA-256, CRC, DDS mip, 인덱스/메모리 범위 검증
- **속도계/RPM/기어 계기판 메시 바인딩**
- 계기판 대상 노드는 정적 메시와 합치지 않아 런타임 개별 회전/표시가 가능
- 기존 OVRCABH3는 계속 읽을 수 있어 현재 F50/288/F40 테스트 자산과 하위 호환됩니다.

## 게임 데이터 연동

런타임은 원본 게임 EVWORK_CAR의 HUD와 같은 값을 사용합니다.

- 속도: field_1F8 (EVWORK_CAR + 0x1F8, km/h 표시값)
- 현재 기어: cur_gear_208 (+0x208)
- RPM: dword20C (+0x20C)

이 세 값은 DashboardFrameLatch에서 **native frame/player 단위로 한 번만 캡처**합니다. 같은 프레임에서 재생되는 좌/우 눈은 동일한 속도/RPM/기어 값을 사용하므로 VR 양안 계기판 불일치를 만들지 않습니다.

## source.json 계기판 규격

GLB 내부의 계기판 바늘/기어 숫자가 **독립 mesh node**여야 합니다. 이름을 추측해서 자동 승인하지 않고 source.json에서 정확히 지정합니다.

~~~json
{
  "dashboard_required": true,
  "dashboard": {
    "bindings": [
      {
        "node": "SpeedNeedle",
        "kind": "speed",
        "pivot": "node_origin",
        "axis_node": [0.0, 1.0, 0.0],
        "input": [0.0, 320.0],
        "angle_deg": [-130.0, 130.0]
      },
      {
        "node": "RpmNeedle",
        "kind": "rpm",
        "pivot": "node_origin",
        "axis_node": [0.0, 1.0, 0.0],
        "input": [0.0, 10000.0],
        "angle_deg": [-130.0, 130.0]
      },
      { "node": "Gear1", "kind": "gear", "gear": 1 },
      { "node": "Gear2", "kind": "gear", "gear": 2 }
    ]
  }
}
~~~

권장 방식은 Blender에서 바늘 오브젝트의 origin을 실제 회전축에 둔 뒤 pivot=node_origin과 axis_node를 사용하는 것입니다. 변환기가 노드 원점/축을 최종 OutRun 로컬 좌표로 자동 변환합니다. 명시적 pivot/axis 숫자도 계속 지원합니다. 실제 계기판 눈금에 맞는 입력 범위와 회전각은 차량별로 측정합니다. 바늘이 하나의 메시로 합쳐진 모델은 Blender 단계에서 바늘을 분리한 뒤 사용합니다.

전체 예시는 source.example.json을 참조합니다.


### 합쳐진 바늘 메시 분리

F40처럼 속도계/RPM 바늘이 한 메시/재질에 합쳐진 소스는 Blender 5.x에서 다음 보조 스크립트로 coincident seam만 1e-5 단위로 weld한 뒤 loose part를 분리할 수 있습니다.

~~~bash
blender --background --python tools/split_dashboard_needles_blender.py --   source.glb dashboard_split.glb dashboard_split.blend F40_Strelki F40_DASH   F40_SPEED_NEEDLE,F40_RPM_NEEDLE
~~~

이 도구는 원본 GLB를 덮어쓰지 않고 새 GLB/.blend를 만들며, 분리된 각 바늘의 object origin을 회전축 후보인 geometry bounds center에 둡니다. 실제 speed/RPM 역할과 눈금 회전방향은 실차 계기판/렌더 QA로 확인한 뒤 source.json에 기록합니다.

## 변환

Python 3.10 이상, numpy, Pillow가 필요합니다.

~~~bash
python -m pip install numpy Pillow
python tools/ferrari_batch_converter.py audit --workspace . --strict
python tools/ferrari_batch_converter.py convert --workspace . --car f40
python tools/ferrari_batch_converter.py verify --workspace .
~~~

입력:

~~~text
sources/<차종 ID>/source.glb
sources/<차종 ID>/source.json
~~~

출력:

~~~text
outputs/<차종 ID>/<차종 ID>_External_Test.ovc
outputs/<차종 ID>/conversion_report.json
~~~

## 품질/안전 제한

- GLB는 전체 차량(full-car), 미터 단위, OutRun Y-up 로컬 좌표로 검증되어야 합니다.
- D3D9Ex 32비트 프로세스 안정성을 위해 현재 텍스처 최대 2048px, 단일 모델 GPU payload 112MiB, sidecar 128MiB, 그룹 512개를 상한으로 둡니다. 제한 초과 시 몰래 LOD/다운스케일하지 않고 BLOCKED 처리합니다.
- skin/morph/vertex-color/외부 이미지 URI 및 미지원 glTF 확장은 손실 없이 베이크한 GLB가 필요합니다.
- dashboard_required=true인 소스는 검증된 계기판 binding이 없으면 변환하지 않습니다.
- 기어 표시는 별도 gear mesh를 선택적으로 그리는 방식입니다. 텍스처 한 장을 런타임에 임의 교체하지 않습니다.
- 바퀴/조향 애니메이션은 이번 계기판 V4 범위와 별도이며 아직 정적 sidecar 동작을 유지합니다.
- 외부 모델 파일의 재배포 권리는 별도로 확인해야 합니다. 권리 불명 모델은 개인 테스트 자료로만 유지합니다.

## 검증

CI와 로컬 단위테스트는 다음을 검증합니다.

- 지면 파묻힘 방지 floor guard
- 플레이어 차량 교체 gate/fallback
- 속도/RPM 각도 보간과 gear visibility
- native-frame stereo telemetry latch
- OVRCABH4/OVCDASH4 파서 및 잘못된 축 거부
- 변환기 Python AST 및 source-level linkage 검증

현재 실제 외부 모델이 없는 차종은 런타임 준비 완료 상태일 뿐, 모델 자산 완료 상태가 아닙니다.
## 2026-11-17 작업 범위 정정 (외부 차량 16종 최종 완료 기준)

**중요: `native_hq_completion_20261116.json`의 16/16은 원본 OutRun OBJ의 bevel/smoothing 결과만 뜻한다. Assetto Corsa·GTA5·기타 외부 고품질 full-car 모델 16종 완성이 아니다. 이 결과를 외부 모델 완료율에 합산하지 않는다.**

외부 모델 실재 증거가 있는 차량은 현재 작업 상태 파일 기준 Dino 246 GTS, F50, 288 GTO, 250 GTO, F40, F430, Enzo **7종**이다. 그중 Dino/250/F430/Enzo는 TDM 변환 경로가 있고 F40은 속도계/RPM 바늘의 실제 분리 및 Blender 재열기 검증이 되어 있다. 나머지 **9종**(Daytona 365, 360 Spider, F355 Spider, 575 Superamerica, Testarossa, 328 GTS, 512 BB, 550 Barchetta, F430 Spider)은 외부 full-car 원본이 미확보다. 7종도 실제 게임 내 완성/계기판 눈금 보정이 모두 통과한 것은 아니다.

최종 완료 판정은 각 차종별로 (1) 라이선스 확인 또는 사용자 개인 로컬 소스 확보, (2) 외부 full-car 모델 및 실내/UV/PBR 검증, (3) 원본 차종과 좌표/지면/시트/핸들 정렬, (4) 속도/RPM/기어 메시를 정확히 분리하고 OVRCABH4로 변환, (5) 게임의 실제 EVWORK_CAR 값을 받아 0/중간/최대/기어 변화를 검증, (6) 좌/우 눈 동일 프레임 데이터 및 Quest 3 게임 실측, (7) 설치된 차량만 표시되는 로더 테스트가 모두 PASS일 때만 허용한다. NativeHQ 결과는 외부 모델이 없는 차종의 대체 완료로 간주하지 않는다.

현재 판정: **외부 full-car 16종 완료 = NO / 계기판 16종 최종 캘리브레이션 = NO / VR 실게임 16종 QA = NO**.
