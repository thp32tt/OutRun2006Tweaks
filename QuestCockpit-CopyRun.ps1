param([ValidateSet('NORMAL','SKY','INTERP','DINO','PBR')][string]$Mode='NORMAL',[switch]$VerifyOnly)
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $MyInvocation.MyCommand.Path
$payload=Join-Path $root 'QUEST_APK_COPYRUN_PAYLOAD'
$identityFile=Join-Path $payload 'IDENTITY.json'
$backup=Join-Path $root 'QUEST_APK_COPYRUN_ORIGINAL_BACKUP'
$backupManifest=Join-Path $backup 'original_files.json'
$dinoName='Dino246_Cockpit_LHD_v15.ovc'
$pbrName='Dino246_Cockpit_LHD_v15_PBR.ovc'
$dinoExpected='eba3510b2848b13702452ca6e0216ac99ad0528d0c40fd47c182e003ea5d1e6b'
$dinoPayload=Join-Path $payload ('model/'+$dinoName)
function HashFile([string]$p){(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}
function Assert-Machine([string]$p,[int]$expected){
    $f=[IO.File]::OpenRead($p)
    try{
        if($f.Length -lt 256){throw "PE too small: $p"}
        $r=[IO.BinaryReader]::new($f)
        if($r.ReadUInt16() -ne 0x5a4d){throw "MZ missing: $p"}
        $f.Position=0x3c;$offset=$r.ReadInt32()
        if($offset -lt 64 -or $offset+6 -gt $f.Length){throw "PE offset invalid: $p"}
        $f.Position=$offset
        if($r.ReadUInt32() -ne 0x4550 -or $r.ReadUInt16() -ne $expected){
            throw "PE architecture mismatch: $p"
        }
    }finally{$f.Dispose()}
}
if(!(Test-Path -LiteralPath $identityFile -PathType Leaf)){throw 'Extract ALL ZIP contents, including QUEST_APK_COPYRUN_PAYLOAD.'}
$identity=Get-Content -LiteralPath $identityFile -Raw | ConvertFrom-Json
if([string]$identity.SourceSha -notmatch '^[0-9a-f]{40}$' -or
   [string]$identity.VariantId -ne 'ACTIVE_R26_R43_R44'){
    throw 'Invalid Quest source identity/renderer variant.'
}
$expectedFiles=@{
    'backend/dinput8.dll'=[string]$identity.GameDllSha256
    'backend/outrun-vr-host.exe'=[string]$identity.HostExeSha256
}
foreach($relative in $expectedFiles.Keys){
    $source=Join-Path $payload $relative
    if(!(Test-Path $source -PathType Leaf) -or
       $expectedFiles[$relative] -notmatch '^[0-9a-f]{64}$' -or
       (HashFile $source) -ne $expectedFiles[$relative]){
        throw "Hash verification failed: $relative"
    }
}
Assert-Machine (Join-Path $payload 'backend/dinput8.dll') 0x014c
Assert-Machine (Join-Path $payload 'backend/outrun-vr-host.exe') 0x8664
foreach($item in @(@('SOURCE_SHA.txt',$identity.SourceSha),
                    @('VARIANT_ID.txt',$identity.VariantId))){
    $file=Join-Path $payload ('backend/'+$item[0])
    if(!(Test-Path $file) -or (Get-Content $file -Raw).Trim() -ne $item[1]){
        throw "Backend source/variant marker mismatch: $($item[0])"
    }
}
$hostSourceSha=if($identity.PSObject.Properties.Name -contains 'HostSourceSha'){
    [string]$identity.HostSourceSha
}else{
    [string]$identity.SourceSha
}
$hostSourceSha=$hostSourceSha.ToLowerInvariant()
if($hostSourceSha -notmatch '^[0-9a-f]{40}$'){
    throw 'Invalid OpenXR host source identity.'
}
$hostMarker=Join-Path $payload 'backend/HOST_BUILD_SOURCE_SHA.txt'
if(!(Test-Path -LiteralPath $hostMarker -PathType Leaf) -or
   (Get-Content -LiteralPath $hostMarker -Raw).Trim().ToLowerInvariant() -ne $hostSourceSha){
    throw 'OpenXR host source marker does not match this package manifest.'
}

$scripts=@('Run-OutRunVRTest.ps1','Select-OutRunVRBackend.ps1',
    'OutRunVR-TestProfiles.ps1','Collect-OutRunVRLogs.ps1',
    'Collect-OutRunVRLogs.cmd','Analyze-OutRunVRSession.ps1',
    'Run-QuestCockpitV2-CrashDiag.ps1','analyze_outrun_assets.py')
foreach($name in $scripts){
    if(!(Test-Path (Join-Path $payload ('scripts/'+$name)) -PathType Leaf)){
        throw "Incomplete test helper: $name"
    }
}
foreach($name in @('OutRun2006Tweaks.ini','OutRun2006Tweaks.lods.ini')){
    if(!(Test-Path (Join-Path $payload ('defaults/'+$name)) -PathType Leaf)){
        throw "Missing default config $name"
    }
}
if($Mode -eq 'DINO') {
    if(!(Test-Path -LiteralPath $dinoPayload -PathType Leaf) -or
       (HashFile $dinoPayload) -ne $dinoExpected) {
        throw 'Dino FitV6 model payload is missing or has the wrong SHA256.'
    }
}
if($Mode -eq 'PBR') {
    # PBR is an explicit opt-in. Never replace the stable OVC2 file.
    $expectedPbr=[string]$identity.DinoPbrModelSha256
    $pbrPayload=Join-Path $payload ('model/'+$pbrName)
    if($expectedPbr -notmatch '^[0-9a-f]{64}
    Write-Host "PASS copy-run source=$($identity.SourceSha), payload verified, no game file modifications."
    return
}
if(!(Test-Path (Join-Path $root 'OR2006C2C.EXE') -PathType Leaf)){
    throw 'Copy ZIP contents next to YOUR original OR2006C2C.EXE and launch again.'
}
$running=Get-Process -ErrorAction SilentlyContinue|Where-Object{
    $_.ProcessName -ieq 'OR2006C2C' -or $_.ProcessName -ieq 'outrun-vr-host'
}
if($running){throw 'Close game and OpenXR host before switching.'}
# One-time baseline snapshot: no root DLL, config, metadata or other helper
# is touched until complete file-level backup/manifest is written.
if(!(Test-Path $backupManifest)){
    if(Test-Path $backup){throw 'Partial original backup detected; refusing unsafe overwrite.'}
    $rootNames=@('dinput8.dll','outrun-vr-host.exe','d3d9.dll',
      'multiviewpatcher.dll','OutRun2006Tweaks.ini','OutRun2006Tweaks.lods.ini',
      'ACTIVE_VR_BACKEND.txt','CURRENT_VR_SESSION.json',
      'BUILD_INPUTS.json','PC_FAST_BUILD.txt',$dinoName,$pbrName)+$scripts
    $backendNames=@('dinput8.dll','outrun-vr-host.exe','SOURCE_SHA.txt',
      'HOST_BUILD_SOURCE_SHA.txt','VARIANT_ID.txt','BUILD_VARIANT.txt',
      'CMAKE_FLAGS.txt','GAME_DLL_SHA256.txt')
    $snapshot=[ordered]@{SchemaVersion=1;SourceSha=[string]$identity.SourceSha;
        CreatedUtc=(Get-Date).ToUniversalTime().ToString('o');Entries=@()}
    foreach($scope in @('root','backend')){
        New-Item -ItemType Directory -Path (Join-Path $backup $scope) -Force|Out-Null
        $base=if($scope -eq 'root'){$root}else{Join-Path $root 'backends/d3d9'}
        $names=if($scope -eq 'root'){$rootNames}else{$backendNames}
        foreach($name in $names){
            $src=Join-Path $base $name
            $exists=Test-Path -LiteralPath $src -PathType Leaf
            $sum=''
            if($exists){
                $sum=HashFile $src
                $saved=Join-Path (Join-Path $backup $scope) $name
                Copy-Item -LiteralPath $src -Destination $saved -Force
                if((HashFile $saved) -ne $sum){throw "Backup verification failed: $scope/$name"}
            }
            $snapshot.Entries+=([ordered]@{
                Scope=$scope;Name=$name;Existed=[bool]$exists;Sha256=$sum})
        }
    }
    $temp=Join-Path $backup 'original_files.pending.json'
    $snapshot|ConvertTo-Json -Depth 8|Set-Content -LiteralPath $temp -Encoding UTF8
    Move-Item -LiteralPath $temp -Destination $backupManifest
    Write-Host "Original game-folder files backed up: $backup"
}
foreach($name in @('OutRun2006Tweaks.ini','OutRun2006Tweaks.lods.ini')){
    $dest=Join-Path $root $name
    if(!(Test-Path $dest -PathType Leaf)){
        Copy-Item (Join-Path $payload ('defaults/'+$name)) $dest
    }
}
foreach($name in $scripts){
    $src=Join-Path $payload ('scripts/'+$name);$dest=Join-Path $root $name
    if(!(Test-Path $dest) -or (HashFile $src) -ne (HashFile $dest)){
        Copy-Item -LiteralPath $src -Destination $dest -Force
    }
    if((HashFile $src) -ne (HashFile $dest)){throw "Helper not installed: $name"}
}
$backend=Join-Path $root 'backends/d3d9'
New-Item -ItemType Directory -Path $backend -Force|Out-Null
foreach($name in @('dinput8.dll','outrun-vr-host.exe','SOURCE_SHA.txt',
    'HOST_BUILD_SOURCE_SHA.txt','VARIANT_ID.txt')){
    $src=Join-Path $payload ('backend/'+$name);$dest=Join-Path $backend $name
    if(!(Test-Path $src)){continue}
    if(!(Test-Path $dest) -or (HashFile $src) -ne (HashFile $dest)){
        Copy-Item -LiteralPath $src -Destination $dest -Force
    }
}
# Old package-specific identity files were backed up. Do not let their
# build variant or stale PC Fast SHA override this verified pair.
foreach($name in @('BUILD_VARIANT.txt','CMAKE_FLAGS.txt','GAME_DLL_SHA256.txt')){
    $p=Join-Path $backend $name
    if(Test-Path $p){Remove-Item -LiteralPath $p -Force}
}
foreach($name in @('BUILD_INPUTS.json','PC_FAST_BUILD.txt')){
    $p=Join-Path $root $name
    if(Test-Path $p){Remove-Item -LiteralPath $p -Force}
}
if($Mode -eq 'DINO') {
    $dinoDest=Join-Path $root $dinoName
    if((Test-Path -LiteralPath $dinoDest -PathType Leaf) -and
       (HashFile $dinoDest) -ne $dinoExpected) {
        throw "Refusing to overwrite a different existing $dinoName"
    }
    Copy-Item -LiteralPath $dinoPayload -Destination $dinoDest -Force
    if((HashFile $dinoDest) -ne $dinoExpected){throw 'Dino FitV6 model copy verification failed.'}
}
if($Mode -eq 'PBR') {
    $pbrDest=Join-Path $root $pbrName
    if((Test-Path -LiteralPath $pbrDest -PathType Leaf) -and
       (HashFile $pbrDest) -ne $expectedPbr){
        throw "Refusing to overwrite an existing different $pbrName"
    }
    Copy-Item -LiteralPath $pbrPayload -Destination $pbrDest -Force
    if((HashFile $pbrDest) -ne $expectedPbr){
        throw 'PBR sidecar copy verification failed.'
    }
}
Write-Host "Quest APK test backend activated: $($identity.SourceSha)"
Write-Host 'The original EXE, models, textures and saved OutRun2006Tweaks.user.ini remain untouched.'
& (Join-Path $root 'Select-OutRunVRBackend.ps1') -Backend d3d9 -TestProfile CORRECTNESS -VariantId CURRENT_FOCUS
if(-not $?){throw 'Backend activation failed; backups are preserved.'}
if((HashFile (Join-Path $root 'dinput8.dll')) -ne $identity.GameDllSha256 -or
   (HashFile (Join-Path $root 'outrun-vr-host.exe')) -ne $identity.HostExeSha256){
    throw 'Installed game DLL or OpenXR host does not match this package manifest.'
}
$launchArgs=@{
    TestProfile='CORRECTNESS'
    QuestCockpitV2ReleaseParity='ON'
    QuestCockpitV2='ON'
}
if($Mode -eq 'SKY'){$launchArgs.QuestCockpitV2SkyProbe='ON'}
if($Mode -eq 'DINO' -or $Mode -eq 'PBR'){$launchArgs.DinoFitV6='ON'}
if($Mode -eq 'INTERP'){
    $launchArgs.QuestCockpitV2Interpolation='OFF'
    $launchArgs.QuestCockpitV2SkyProbe='ON'
}
Write-Host "Starting Quest cockpit; mode=$Mode"
# The test flag is inherited by the game process; it never persists across runs.
$oldPbr=[Environment]::GetEnvironmentVariable('OUTRUN_VR_DINO_PBR_TEST','Process')
try {
    if($Mode -eq 'PBR') {
        [Environment]::SetEnvironmentVariable('OUTRUN_VR_DINO_PBR_TEST','1','Process')
    }else{
        [Environment]::SetEnvironmentVariable('OUTRUN_VR_DINO_PBR_TEST',$null,'Process')
    }
    & (Join-Path $root 'Run-OutRunVRTest.ps1') @launchArgs
    if(-not $?){throw 'VR runner failed. See OUTRUNVR_LAUNCH_ERROR.txt or collected logs.'}
} finally {
    [Environment]::SetEnvironmentVariable('OUTRUN_VR_DINO_PBR_TEST',$oldPbr,'Process')
}
 -or
       !(Test-Path -LiteralPath $pbrPayload -PathType Leaf) -or
       (HashFile $pbrPayload) -ne $expectedPbr){
        throw 'PBR OVC3 sidecar is missing or does not match the package manifest.'
    }
    $magic=[IO.File]::ReadAllBytes($pbrPayload)
    if($magic.Length -lt 36 -or
       [Text.Encoding]::ASCII.GetString($magic,0,8) -ne 'OVRCABH3' -or
       [BitConverter]::ToUInt32($magic,8) -ne 3){
        throw 'PBR sidecar is not an OVC3 model.'
    }
}
if($VerifyOnly){
    Write-Host "PASS copy-run source=$($identity.SourceSha), payload verified, no game file modifications."
    return
}
if(!(Test-Path (Join-Path $root 'OR2006C2C.EXE') -PathType Leaf)){
    throw 'Copy ZIP contents next to YOUR original OR2006C2C.EXE and launch again.'
}
$running=Get-Process -ErrorAction SilentlyContinue|Where-Object{
    $_.ProcessName -ieq 'OR2006C2C' -or $_.ProcessName -ieq 'outrun-vr-host'
}
if($running){throw 'Close game and OpenXR host before switching.'}
# One-time baseline snapshot: no root DLL, config, metadata or other helper
# is touched until complete file-level backup/manifest is written.
if(!(Test-Path $backupManifest)){
    if(Test-Path $backup){throw 'Partial original backup detected; refusing unsafe overwrite.'}
    $rootNames=@('dinput8.dll','outrun-vr-host.exe','d3d9.dll',
      'multiviewpatcher.dll','OutRun2006Tweaks.ini','OutRun2006Tweaks.lods.ini',
      'ACTIVE_VR_BACKEND.txt','CURRENT_VR_SESSION.json',
      'BUILD_INPUTS.json','PC_FAST_BUILD.txt',$dinoName)+$scripts
    $backendNames=@('dinput8.dll','outrun-vr-host.exe','SOURCE_SHA.txt',
      'HOST_BUILD_SOURCE_SHA.txt','VARIANT_ID.txt','BUILD_VARIANT.txt',
      'CMAKE_FLAGS.txt','GAME_DLL_SHA256.txt')
    $snapshot=[ordered]@{SchemaVersion=1;SourceSha=[string]$identity.SourceSha;
        CreatedUtc=(Get-Date).ToUniversalTime().ToString('o');Entries=@()}
    foreach($scope in @('root','backend')){
        New-Item -ItemType Directory -Path (Join-Path $backup $scope) -Force|Out-Null
        $base=if($scope -eq 'root'){$root}else{Join-Path $root 'backends/d3d9'}
        $names=if($scope -eq 'root'){$rootNames}else{$backendNames}
        foreach($name in $names){
            $src=Join-Path $base $name
            $exists=Test-Path -LiteralPath $src -PathType Leaf
            $sum=''
            if($exists){
                $sum=HashFile $src
                $saved=Join-Path (Join-Path $backup $scope) $name
                Copy-Item -LiteralPath $src -Destination $saved -Force
                if((HashFile $saved) -ne $sum){throw "Backup verification failed: $scope/$name"}
            }
            $snapshot.Entries+=([ordered]@{
                Scope=$scope;Name=$name;Existed=[bool]$exists;Sha256=$sum})
        }
    }
    $temp=Join-Path $backup 'original_files.pending.json'
    $snapshot|ConvertTo-Json -Depth 8|Set-Content -LiteralPath $temp -Encoding UTF8
    Move-Item -LiteralPath $temp -Destination $backupManifest
    Write-Host "Original game-folder files backed up: $backup"
}
foreach($name in @('OutRun2006Tweaks.ini','OutRun2006Tweaks.lods.ini')){
    $dest=Join-Path $root $name
    if(!(Test-Path $dest -PathType Leaf)){
        Copy-Item (Join-Path $payload ('defaults/'+$name)) $dest
    }
}
foreach($name in $scripts){
    $src=Join-Path $payload ('scripts/'+$name);$dest=Join-Path $root $name
    if(!(Test-Path $dest) -or (HashFile $src) -ne (HashFile $dest)){
        Copy-Item -LiteralPath $src -Destination $dest -Force
    }
    if((HashFile $src) -ne (HashFile $dest)){throw "Helper not installed: $name"}
}
$backend=Join-Path $root 'backends/d3d9'
New-Item -ItemType Directory -Path $backend -Force|Out-Null
foreach($name in @('dinput8.dll','outrun-vr-host.exe','SOURCE_SHA.txt',
    'HOST_BUILD_SOURCE_SHA.txt','VARIANT_ID.txt')){
    $src=Join-Path $payload ('backend/'+$name);$dest=Join-Path $backend $name
    if(!(Test-Path $src)){continue}
    if(!(Test-Path $dest) -or (HashFile $src) -ne (HashFile $dest)){
        Copy-Item -LiteralPath $src -Destination $dest -Force
    }
}
# Old package-specific identity files were backed up. Do not let their
# build variant or stale PC Fast SHA override this verified pair.
foreach($name in @('BUILD_VARIANT.txt','CMAKE_FLAGS.txt','GAME_DLL_SHA256.txt')){
    $p=Join-Path $backend $name
    if(Test-Path $p){Remove-Item -LiteralPath $p -Force}
}
foreach($name in @('BUILD_INPUTS.json','PC_FAST_BUILD.txt')){
    $p=Join-Path $root $name
    if(Test-Path $p){Remove-Item -LiteralPath $p -Force}
}
if($Mode -eq 'DINO') {
    $dinoDest=Join-Path $root $dinoName
    if((Test-Path -LiteralPath $dinoDest -PathType Leaf) -and
       (HashFile $dinoDest) -ne $dinoExpected) {
        throw "Refusing to overwrite a different existing $dinoName"
    }
    Copy-Item -LiteralPath $dinoPayload -Destination $dinoDest -Force
    if((HashFile $dinoDest) -ne $dinoExpected){throw 'Dino FitV6 model copy verification failed.'}
}
Write-Host "Quest APK test backend activated: $($identity.SourceSha)"
Write-Host 'The original EXE, models, textures and saved OutRun2006Tweaks.user.ini remain untouched.'
& (Join-Path $root 'Select-OutRunVRBackend.ps1') -Backend d3d9 -TestProfile CORRECTNESS -VariantId CURRENT_FOCUS
if(-not $?){throw 'Backend activation failed; backups are preserved.'}
if((HashFile (Join-Path $root 'dinput8.dll')) -ne $identity.GameDllSha256 -or
   (HashFile (Join-Path $root 'outrun-vr-host.exe')) -ne $identity.HostExeSha256){
    throw 'Installed game DLL or OpenXR host does not match this package manifest.'
}
$launchArgs=@{
    TestProfile='CORRECTNESS'
    QuestCockpitV2ReleaseParity='ON'
    QuestCockpitV2='ON'
}
if($Mode -eq 'SKY'){$launchArgs.QuestCockpitV2SkyProbe='ON'}
if($Mode -eq 'DINO'){$launchArgs.DinoFitV6='ON'}
if($Mode -eq 'INTERP'){
    $launchArgs.QuestCockpitV2Interpolation='OFF'
    $launchArgs.QuestCockpitV2SkyProbe='ON'
}
Write-Host "Starting Quest cockpit; mode=$Mode"
& (Join-Path $root 'Run-OutRunVRTest.ps1') @launchArgs
if(-not $?){throw 'VR runner failed. See OUTRUNVR_LAUNCH_ERROR.txt or collected logs.'}
