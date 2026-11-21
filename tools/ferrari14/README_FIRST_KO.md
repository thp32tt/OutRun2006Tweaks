# Ferrari14 · 공식 v0.03 기반 격리 테스트 패치

**상태:** GitHub C++·Windows PowerShell 설치/복구 CI PASS. **Quest 3 양안 / FPS / 외부 모델 위치 실기 미검증**. 기존 정상 VR 게임 폴더에 직접 설치하면 안 됩니다.

## 새 설치 방법 (정상 릴리즈 폴더 보존)

1. 이 ZIP의 파일을 임시 패치 폴더에 압축 해제합니다. 게임은 반드시 **2026-11-20 게시된 공식 v0.03 다운로드**의 EXE / INI / DLL / VR 호스트가 들어 있는 정상 설치본을 사용합니다. 이전 11월 19일 Ferrari13 테스트 설치본을 입력하면 해시 검사에서 거부됩니다.
2. 관리자 권한은 불필요합니다. 먼저 검증만 수행합니다.

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File .\PREPARE-FERRARI14-V003-TEST-COPY.ps1 -ReleaseRoot "C:\OutRun2006-Normal" -TestRoot "C:\OutRun-Ferrari14-Test"
   ```

3. PASS가 나오면 같은 명령에 **`-Create`** 를 붙여 별도 `OutRun-Ferrari14-Test` 폴더를 생성합니다. 일반 게임 데이터까지 복사하며, 원본 폴더는 변경하지 않습니다.
4. 복사된 **테스트 폴더**에서 원본 `Start-OutRun.cmd`로 VR이 정상 구동하는지 먼저 확인하고 종료합니다. 이 기준 테스트는 아직 패치 DLL이 적용되지 않은 상태입니다.
5. 패치를 검증합니다.

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File .\APPLY-FERRARI14-V003-CLEAN.ps1 -GameRoot "C:\OutRun-Ferrari14-Test"
   ```

6. 검증 PASS 후 같은 명령에 **`-Install`** 을 추가합니다. 테스트 폴더의 DLL만 교체하고 공식 v0.03 호스트·EXE·INI 및 정상 릴리즈 폴더는 보존합니다. 백업 경로를 출력합니다.
7. `RUN-FERRARI14-V003-MODEL-OFF.cmd vr`를 먼저 실행해서 메뉴/창/양안/주행 FPS를 확인합니다. 그다음 비공개 575 OVC를 `ExternalCars\car_id_05.ovc`에 수동 배치하여 `RUN-FERRARI14-V003-575-ON.cmd vr`로 비교합니다. 차량 ID 5와 튜닝 20만 외부 모델 대상입니다.
8. 불일치가 있으면 `RUN-FERRARI14-V003-575-TRACE.cmd vr`로 짧게 로그를 수집합니다. 복구하려면 위 설치 시 생성된 백업 폴더를 지정합니다.

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File .\RESTORE-FERRARI14-V003-CLEAN.ps1 -GameRoot "C:\OutRun-Ferrari14-Test" -BackupFolder "C:\OutRun-Ferrari14-Test\FERRARI14_V003_BACKUP_..."
   ```

## 안전성·남은 문제

- 게시된 공식 v0.03의 SHA: EXE `68ceb386...`, INI `630fc782...`, DLL `5d3c4fa5...`, 호스트 `8c7e5742...`. **이전 CI 임시 아티팩트의 `b4fc8d10...` DLL / `bbeb46ea...` 호스트를 공식 릴리즈로 간주하지 않습니다.**
- 모델 OFF에서 게임 자체 구동이 릴리즈와 달라지면 575 모델과 무관하게 초기화/후크 문제입니다. 그 경우 모델 ON 테스트를 하지 마세요.
- 575 ON은 `ExternalFerrariNativeCallbackReplacement=true`로 **원본 차량 표시 콜백을 통째로 대신하는 위험을 명시적으로 허용한 실험**입니다. 원본의 부품별 효과/렌더링 콜백이 완전히 유지된다는 보장이 없습니다.
- 외부 모델 PBR c0/c4/c8 양안 경로는 아직 검증되지 않아 OFF이며, 고정 기능 A/B만 사용합니다. 575에는 F50 차체 상하 필터를 적용하지 않습니다.
- 기존 575 하이브리드 모델의 검은 페인트와 저품질 계기판 문제는 DLL 수정으로 해결되지 않습니다. 원본 계기판을 보존한 비공개 진단 모델이 별도로 있으며 공식 게임 데이터나 타사 차량 에셋은 이 ZIP에 포함되지 않습니다.
- 백업/복구는 파일 해시가 변한 경우 안전을 위해 중단하며, 사용자의 수정 파일을 무조건 덮어쓰지 않습니다.
