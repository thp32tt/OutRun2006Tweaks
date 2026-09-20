param([switch]$All)
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $MyInvocation.MyCommand.Path
$active=Join-Path $root 'ACTIVE_VR_BACKEND.txt'
if(!(Test-Path $active)){throw 'ACTIVE_VR_BACKEND.txt not found; select a backend first.'}
$kv=@{}; Get-Content $active | ForEach-Object { if($_ -match '^([^=]+)=(.*)$'){$kv[$matches[1]]=$matches[2]} }
$backend=$kv.backend; if(!$backend){throw 'backend identity missing'}
$variant=switch($backend){'d3d9'{'A_CONTROL'};'dxvk-safe'{'E_DXVK_SAFE'};'dxvk'{'E_DXVK'};'dx12'{'F_DX12'};'2d'{'CONTROL_2D'};default{'UNKNOWN'}}
$matrix=if($kv.matrix){$kv.matrix}else{'UNIFIED'}
$session=Get-Date -Format 'yyyyMMdd-HHmmss'
$base=Join-Path $root "logs/$matrix"
$dest=Join-Path $base "$variant/$session"; New-Item -ItemType Directory -Force $dest|Out-Null
$patterns=@('OutRun2006Tweaks*.log','outrun-vr-host*.log','outrun-vr-host-pipeline*.log','outrun-vr-watchdog*.log','backend*.log','*.dmp','OutRun2006Tweaks.ini','ACTIVE_VR_BACKEND.txt')
foreach($p in $patterns){Get-ChildItem $root -Filter $p -File -ErrorAction SilentlyContinue|ForEach-Object{Copy-Item $_.FullName $dest -Force}}
$source=Join-Path $root "backends/$($backend -replace 'dxvk-safe','d3d9')/SOURCE_SHA.txt"; $sha=if(Test-Path $source){(Get-Content $source -Raw).Trim()}else{'unknown'}
@("VARIANT=$variant","BACKEND=$backend","SESSION=$session","BUILD_MATRIX=$matrix","SOURCE_SHA=$sha")|Set-Content (Join-Path $dest 'MANIFEST.txt') -Encoding UTF8
@{VariantId=$variant;Backend=$backend;SessionId=$session;BuildMatrixId=$matrix;GitSha=$sha;CollectedAt=(Get-Date -Format o)}|ConvertTo-Json|Set-Content (Join-Path $dest 'variant_manifest.json') -Encoding UTF8
@('FPS=','HMD_SMOOTHNESS=','STEREO=','RECENTER=','HUD_RANK_SCORE=','SKY_CLOUD=','SMOKE_SKID=','MENU_CAR=','EXIT_YES_NO=','NOTES=')|Set-Content (Join-Path $dest 'TEST_RESULT.txt') -Encoding UTF8
if($All){$zip=Join-Path $root "OutRun2_VR_MATRIX_LOGS_${matrix}_${session}.zip"; if(Test-Path $zip){Remove-Item $zip -Force}; Compress-Archive -Path "$base/*" -DestinationPath $zip}else{$zip=Join-Path $root "OutRun2_VR_LOGS_${matrix}_${variant}_${session}.zip"; if(Test-Path $zip){Remove-Item $zip -Force}; Compress-Archive -Path "$dest/*" -DestinationPath $zip}
Write-Host "Diagnostic archive: $zip"
