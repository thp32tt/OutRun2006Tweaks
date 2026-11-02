# OutRun 2006 Q012 ImageGen 한글 DDS — 원본 BGRA32 포맷 보존 단일 파일 TEST_ONLY (2026-11-02 KST)

## 정적 검증
- **범위:** Q012 `Continue?` → `계속?` 1개, `textures/load/spr_etc_xst/D6DC1380_256x64.dds`만.
- N100에서 **게임 설치본 원본 DDS 읽기 전용** SHA256 `42aa10e021f9170247612b2e8231be43458abc3cda1011595db2fe2902df4352`를 확인. 원본 DDS 디코드가 정본 HD PNG(256×64, SHA256 `bfabe98fb448814401f1c4c5bb6ae0cbb2c8ef81bbf9ec4b6457fdcc795ab2e8`)와 **전 픽셀 일치**.
- 실제 A/B ImageGen 후보 PNG SHA256 `f88974af1876c6cf4ef21339dcd7c61ec1203165890773033b66c131e82ca75b`; 합성 PNG SHA256 `9a84d2ea1dd5d553f4e026af690ebbc20c8253456f526f11d6c90fa6e80a86b5`. 한국어 문구는 이미지에서 직접 확인(1줄).
- 기존 8-DDS v4는 RGBA32 색상 마스크를 새로 작성했으나, 이번 Q012는 **원본 DDS 128바이트 헤더·BGRA32 마스크·256×64·mip 1·NORMAL 방향을 바이트 단위로 유지**하고 텍스트만 변경.
- 영어 원문 알파의 정확한 영역 `[8,10,248,44)`만 CLEAN/교체. 영역 밖 RGBA 변경 **0픽셀**, 원본 알파 영역 밖 영어 잔상 없음. 저장 DDS를 Pillow로 **재디코드해 합성 PNG와 픽셀 완전 일치**.
- 결과 DDS SHA256 **`7f06b1a8892d760783ee158e51440eae5702d72e48fecf709dd06492701a9bf9`**.
- 동일 입력을 서로 다른 N100 신규 출력 폴더에 2회 생성해 **DDS/ZIP SHA 완전 일치**. ZIP 9,756 bytes, SHA256 **`b943788616522a5a4b5b2210f61cde344c7878a68881bc01213ee6b4fe318c2e`**. ZIP CRC 및 내부 DDS 바이트 일치 PASS.
- 기존 104-DDS v3 ZIP은 보존: SHA256 `84d92c22ff957ebeaa3156165b9ed7ef769802756ddc183d18bd586ff5c1ddf3`.

## 승인 범위
- **TEST_ONLY / RUNTIME_VALIDATION=UNTESTED**. 정적 DDS 포맷·픽셀 검증이지 게임 동작, C1/C3 전체 QA 또는 RELEASE 승인이 아니다.
- 다른 7개 v4 DDS는 원본과 차원/압축/마스크가 달라 동일한 게임 설치 절차로 확대하지 않는다. 겹치는 아틀라스, HUD, Q116/Q241 경계 alpha는 HOLD.
- N100 게임 설치본, 기존 A/B/C1, VR/FFB/DX11/DXVK, Portainer, 원본 DDS 및 v3 ZIP은 **변경하지 않았다**.
- **Portainer 재배포 불필요.** 게임 파일을 직접 만질 수 있는 사용자만 아래의 1개 DDS 실기 시험을 진행한다.

## Windows PowerShell — 원본 해시 일치 시에만 수동 적용
게임을 종료한 뒤 **PowerShell**에서 `$GameRoot`와 `$Zip`를 실제 경로로 수정한다. 원본 DDS SHA가 다르면 **중단하고 설치하지 않는다**.

```powershell
$GameRoot = "C:\\Games\\OutRun2006" # 실제 게임 폴더로 수정
$Zip = "C:\\Downloads\\OUTRUN_Q012_IMAGEGEN_NATIVE_FORMAT_1DDS_TEST_ONLY.zip"
$Rel = "textures\\load\\spr_etc_xst\\D6DC1380_256x64.dds"
$ExpectedZip = "b943788616522a5a4b5b2210f61cde344c7878a68881bc01213ee6b4fe318c2e"
$ExpectedOriginal = "42aa10e021f9170247612b2e8231be43458abc3cda1011595db2fe2902df4352"
$ExpectedNew = "7f06b1a8892d760783ee158e51440eae5702d72e48fecf709dd06492701a9bf9"
$Target = Join-Path $GameRoot $Rel
$Backup = "$Target.Q012_ORIGINAL_BACKUP_20261102"
$Stage = Join-Path $env:TEMP "OutRun_Q012_NATIVE_FORMAT_TEST_20261102"
function Assert-Sha($Path,$Expected) {
  if (!(Test-Path -LiteralPath $Path -PathType Leaf)) { throw "FILE_NOT_FOUND: $Path" }
  if ((Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $Expected) { throw "SHA_MISMATCH: $Path" }
}
Assert-Sha $Zip $ExpectedZip
Assert-Sha $Target $ExpectedOriginal
if ((Test-Path -LiteralPath $Backup) -or (Test-Path -LiteralPath $Stage)) { throw "BACKUP_OR_STAGE_ALREADY_EXISTS" }
Expand-Archive -LiteralPath $Zip -DestinationPath $Stage -ErrorAction Stop
$StagedDDS = Join-Path $Stage $Rel
Assert-Sha $StagedDDS $ExpectedNew
Copy-Item -LiteralPath $Target -Destination $Backup -ErrorAction Stop
Assert-Sha $Backup $ExpectedOriginal
Copy-Item -LiteralPath $StagedDDS -Destination $Target -ErrorAction Stop
Assert-Sha $Target $ExpectedNew
Write-Host "Q012 TEST_ONLY 설치됨. 게임에서 Continue? -> 계속?를 확인하고 반드시 복원하세요."
```

게임에서 해당 UI 표시, 글자 방향/색/잘림, 메뉴 복귀 후 재표시를 확인하고 스크린샷을 남긴다. 실패하거나 확인 후에는 아래를 실행한다.

```powershell
Assert-Sha $Backup $ExpectedOriginal
Copy-Item -LiteralPath $Backup -Destination $Target -ErrorAction Stop
Assert-Sha $Target $ExpectedOriginal
Write-Host "Q012 원본 DDS 복원 검증 완료."
```

백업을 지우기 전에는 복원 SHA가 정확히 일치하는지 확인한다. **원본 SHA가 다른 사용자 설치본에는 적용 금지**. 테스트 결과를 승인 없이 다른 DDS로 확장하지 않는다.

## 재현 소스
- `tools/localization/q012_native_format_pilot_20261102.py` — SHA 핀, 원본 HD↔DDS 전 픽셀 일치, BGRA32 헤더 보존, 원문 CLEAN, 보호 픽셀, DDS 재디코드, deterministic ZIP, 기존 출력 덮어쓰기 금지.
- ZIP 안에는 상대경로 DDS 1개, `qa_receipts/Q012_native_format.json`, `TEST_ONLY_MANIFEST.json`만 포함.
