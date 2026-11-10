param([ValidateSet('NORMAL','SKY','INTERP','TURN')][string]$Mode='NORMAL',[switch]$VerifyOnly)
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $MyInvocation.MyCommand.Path
$payload=Join-Path $root 'QUEST_APK_COPYRUN_PAYLOAD'
$identityFile=Join-Path $payload 'IDENTITY.json'
$backup=Join-Path $root 'QUEST_APK_COPYRUN_ORIGINAL_BACKUP'
$backupManifest=Join-Path $backup 'original_files.json'
function Get-Sha256Lower([string]$Path){
    $stream=[System.IO.File]::OpenRead($Path)
    try {
        $sha=[System.Security.Cryptography.SHA256]::Create()
        try {
            $bytes=$sha.ComputeHash($stream)
            return ([System.BitConverter]::ToString($bytes)).Replace('-','').ToLowerInvariant()
        } finally { $sha.Dispose() }
    } finally { $stream.Dispose() }
}
function HashFile([string]$p){Get-Sha256Lower $p}
function Assert-BackupManifest([string]$manifestPath,[string]$backupRoot){
    if(!(Test-Path -LiteralPath $manifestPath -PathType Leaf)){return}
    try{$m=Get-Content -LiteralPath $manifestPath -Raw|ConvertFrom-Json}
    catch{throw 'Existing original backup manifest is unreadable; refusing to modify the game folder.'}
    if($m.SchemaVersion -ne 1 -or !$m.Entries){
        throw 'Existing original backup manifest is invalid; refusing to modify the game folder.'
    }
    if($m.RestoredUtc){
        throw 'Existing original backup was already restored but not archived; refusing stale baseline reuse.'
    }
    if(Test-Path -LiteralPath (Join-Path $backupRoot 'RESTORE_IN_PROGRESS.txt') -PathType Leaf){
        throw 'Interrupted restore detected. Run RESTORE-QUEST-APK-COCKPIT.cmd again before starting a new test.'
    }
    $sourceId=[string]$m.SourceSha
    if($sourceId.Length -ne 40 -or $sourceId -match '[^0-9a-f]'){
        throw 'Existing original backup source identity is invalid.'
    }
    $seen=New-Object 'System.Collections.Generic.HashSet[string]' ([System.StringComparer]::OrdinalIgnoreCase)
    foreach($e in $m.Entries){
        $entryName=[string]$e.Name
        if($e.Scope -notin @('root','backend') -or $entryName -match '[^A-Za-z0-9._-]'){
            throw 'Unsafe path in existing original backup manifest.'
        }
        $key=([string]$e.Scope)+'/'+$entryName
        if(!$seen.Add($key)){throw "Duplicate original backup entry: $key"}
        if($e.Existed){
            $entryHash=[string]$e.Sha256
            if($entryHash.Length -ne 64 -or $entryHash -match '[^0-9a-fA-F]'){
                throw "Invalid original backup hash: $key"
            }
            $saved=Join-Path (Join-Path $backupRoot ([string]$e.Scope)) $entryName
            if(!(Test-Path -LiteralPath $saved -PathType Leaf) -or
               (HashFile $saved) -ne $entryHash.ToLowerInvariant()){
                throw "Original backup is missing or corrupted: $key"
            }
        }
    }
}
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
$hostMarker=Join-Path $payload 'backend/HOST_BUILD_SOURCE_SHA.txt'
if((Test-Path $hostMarker) -and
   (Get-Content $hostMarker -Raw).Trim() -ne $identity.SourceSha){
    throw 'OpenXR host belongs to another source SHA.'
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

# Static launcher contract: parse the exact payload scripts and confirm every
# named parameter used below still exists. This prevents a future positional
# binding regression such as CORRECTNESS being consumed by QuestCockpitV2.
function Assert-ScriptParameters([string]$path,[string[]]$required){
    $tokens=$null
    $parseErrors=$null
    $ast=[System.Management.Automation.Language.Parser]::ParseFile(
        $path,[ref]$tokens,[ref]$parseErrors)
    if($parseErrors.Count -gt 0){
        throw "PowerShell parse failure: $([IO.Path]::GetFileName($path)): $(($parseErrors|ForEach-Object Message)-join '; ')"
    }
    if(!$ast.ParamBlock){throw "Missing param block: $([IO.Path]::GetFileName($path))"}
    $names=@($ast.ParamBlock.Parameters|ForEach-Object{$_.Name.VariablePath.UserPath})
    foreach($name in $required){
        if($name -notin $names){
            throw "Launcher contract mismatch: $([IO.Path]::GetFileName($path)) has no -$name parameter."
        }
    }
}
Assert-ScriptParameters (Join-Path $payload 'scripts/Run-OutRunVRTest.ps1') @(
    'TestProfile','QuestCockpitV2ReleaseParity','QuestCockpitV2',
    'QuestCockpitV2F0','QuestCockpitV2SkyProbe','QuestCockpitV2Interpolation')
Assert-ScriptParameters (Join-Path $payload 'scripts/Select-OutRunVRBackend.ps1') @(
    'Backend','TestProfile','VariantId')

foreach($name in @('OutRun2006Tweaks.ini','OutRun2006Tweaks.lods.ini')){
    if(!(Test-Path (Join-Path $payload ('defaults/'+$name)) -PathType Leaf)){
        throw "Missing default config $name"
    }
}
if($VerifyOnly){
    if((Test-Path -LiteralPath $backup) -and !(Test-Path -LiteralPath $backupManifest -PathType Leaf)){
        throw 'Partial original backup detected; VERIFY refuses unsafe state.'
    }
    Assert-BackupManifest $backupManifest $backup
    Write-Host "PASS copy-run source=$($identity.SourceSha), payload verified, no game file modifications."
    return
}
$gameExe=Join-Path $root 'OR2006C2C.EXE'
if(!(Test-Path -LiteralPath $gameExe -PathType Leaf)){
    throw 'Copy ZIP contents next to YOUR original OR2006C2C.EXE and launch again.'
}
Assert-Machine $gameExe 0x014c
$canonicalGameSha='68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3'
$actualGameSha=HashFile $gameExe
if($actualGameSha -ne $canonicalGameSha){
    throw "Unsupported OR2006C2C.EXE before any game-folder changes. Expected $canonicalGameSha, got $actualGameSha"
}
Assert-BackupManifest $backupManifest $backup
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
      'BUILD_INPUTS.json','PC_FAST_BUILD.txt')+$scripts
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
    Assert-BackupManifest $backupManifest $backup
    Write-Host "Original game-folder files backed up and verified: $backup"
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
Write-Host "Quest APK test backend activated: $($identity.SourceSha)"
Write-Host 'The original EXE, models, textures and saved OutRun2006Tweaks.user.ini remain untouched.'
& (Join-Path $root 'Select-OutRunVRBackend.ps1') -Backend d3d9 -TestProfile CORRECTNESS -VariantId CURRENT_FOCUS
if(-not $?){throw 'Backend activation failed; backups are preserved.'}
if((HashFile (Join-Path $root 'dinput8.dll')) -ne $identity.GameDllSha256 -or
   (HashFile (Join-Path $root 'outrun-vr-host.exe')) -ne $identity.HostExeSha256){
    throw 'Installed game DLL and OpenXR host do not match the same source build.'
}
$launchArgs=@{
    TestProfile='CORRECTNESS'
    QuestCockpitV2ReleaseParity='ON'
    QuestCockpitV2='ON'
    QuestCockpitV2F0='ON'
}
if($Mode -eq 'SKY'){$launchArgs.QuestCockpitV2SkyProbe='ON'}
if($Mode -eq 'INTERP'){
    $launchArgs.QuestCockpitV2Interpolation='OFF'
    $launchArgs.QuestCockpitV2SkyProbe='ON'
}
if($Mode -eq 'TURN'){
    # Keep the normal high-rate interpolation path and verified F0 scope;
    # only enable bounded camera/body phase telemetry.
    $launchArgs.QuestCockpitV2Interpolation='ON'
    $launchArgs.QuestCockpitV2SkyProbe='ON'
}
$runner=Join-Path $root 'Run-OutRunVRTest.ps1'
if(!(Test-Path -LiteralPath $runner -PathType Leaf)){
    throw 'Run-OutRunVRTest.ps1 was not installed into the game folder.'
}
Write-Host "Starting Quest cockpit; mode=$Mode"
& $runner @launchArgs
if(-not $?){throw 'VR runner failed. See OUTRUNVR_LAUNCH_ERROR.txt or collected logs.'}
