param([switch]$All)
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $MyInvocation.MyCommand.Path
$active=Join-Path $root 'ACTIVE_VR_BACKEND.txt'
if(!(Test-Path $active)){throw 'ACTIVE_VR_BACKEND.txt not found; select a backend first.'}
$kv=@{}; Get-Content $active | ForEach-Object { if($_ -match '^([^=]+)=(.*)$'){$kv[$matches[1]]=$matches[2]} }
$backend=$kv.backend; if(!$backend){throw 'backend identity missing'}
$variant=if($kv.variant){$kv.variant}else{switch($backend){'d3d9'{'A_CONTROL'};'dxvk-safe'{'E_DXVK_SAFE'};'dxvk'{'E_DXVK_MULTIVIEW'};'dx12'{'F_DX12_STRICT'};'2d'{'CONTROL_2D'};default{'UNKNOWN'}}}
$matrix=if($kv.matrix){$kv.matrix}else{'UNIFIED'}
$sessionState=Join-Path $root 'CURRENT_VR_SESSION.json'
if(!(Test-Path $sessionState)){throw 'CURRENT_VR_SESSION.json not found; select the backend again before launching the game.'}
$state=Get-Content $sessionState -Raw | ConvertFrom-Json
$session=$state.SessionId
if(!$session -or $state.Backend -ne $backend -or $state.BuildMatrixId -ne $matrix){throw 'Current session identity does not match the active backend/matrix.'}
$startedUtc=[datetime]::Parse($state.StartedUtc).ToUniversalTime()
$base=Join-Path $root "logs/$matrix"
$dest=Join-Path $base "$variant/$session"; New-Item -ItemType Directory -Force $dest|Out-Null
$patterns=@('OutRun2006Tweaks*.log','outrun-vr-host*.log','outrun-vr-host-pipeline*.log','outrun-vr-watchdog*.log','backend*.log','*.dmp')
$copied=@()
foreach($p in $patterns){Get-ChildItem $root -Filter $p -File -ErrorAction SilentlyContinue|Where-Object{$_.LastWriteTimeUtc -ge $startedUtc}|ForEach-Object{Copy-Item $_.FullName $dest -Force;$copied+=$_.Name}}
Copy-Item $active $dest -Force
Copy-Item $sessionState $dest -Force
$inputs=Join-Path $root 'BUILD_INPUTS.json'; if(Test-Path $inputs){Copy-Item $inputs $dest -Force}
$payloadBackend=if($backend -eq '2d' -or $backend -eq 'dxvk-safe'){'d3d9'}else{$backend}
$source=Join-Path $root "backends/$payloadBackend/SOURCE_SHA.txt"; $sha=if(Test-Path $source){(Get-Content $source -Raw).Trim()}else{'unknown'}
$configHash=if(Test-Path (Join-Path $root 'OutRun2006Tweaks.ini')){(Get-FileHash (Join-Path $root 'OutRun2006Tweaks.ini') -Algorithm SHA256).Hash.ToLowerInvariant()}else{'missing'}
@("VARIANT=$variant","BACKEND=$backend","SESSION=$session","SESSION_STARTED_UTC=$($startedUtc.ToString('o'))","BUILD_MATRIX=$matrix","SOURCE_SHA=$sha","CONFIG_SHA256=$configHash","FILES=$($copied -join ',')")|Set-Content (Join-Path $dest 'MANIFEST.txt') -Encoding UTF8
@{SchemaVersion=1;VariantId=$variant;Backend=$backend;SessionId=$session;SessionStartedUtc=$startedUtc.ToString('o');BuildMatrixId=$matrix;GitSha=$sha;ConfigSha256=$configHash;CollectedAtUtc=(Get-Date).ToUniversalTime().ToString('o');CollectedFiles=$copied}|ConvertTo-Json -Depth 4|Set-Content (Join-Path $dest 'variant_manifest.json') -Encoding UTF8
@('FPS=','HMD_SMOOTHNESS=','STEREO=','RECENTER=','HUD_RANK_SCORE=','SKY_CLOUD=','SMOKE_SKID=','MENU_CAR=','EXIT_YES_NO=','NOTES=')|Set-Content (Join-Path $dest 'TEST_RESULT.txt') -Encoding UTF8
if($All){$zip=Join-Path $root "OutRun2_VR_MATRIX_LOGS_${matrix}_${session}.zip"; if(Test-Path $zip){Remove-Item $zip -Force}; Compress-Archive -Path "$base/*" -DestinationPath $zip}else{$zip=Join-Path $root "OutRun2_VR_LOGS_${matrix}_${variant}_${session}.zip"; if(Test-Path $zip){Remove-Item $zip -Force}; Compress-Archive -Path "$dest/*" -DestinationPath $zip}
Write-Host "Diagnostic archive: $zip"
