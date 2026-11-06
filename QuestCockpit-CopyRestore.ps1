param([switch]$VerifyOnly)
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $MyInvocation.MyCommand.Path
$backup=Join-Path $root 'QUEST_APK_COPYRUN_ORIGINAL_BACKUP'
$manifest=Join-Path $backup 'original_files.json'

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

function Read-ValidatedManifest {
    if(!(Test-Path -LiteralPath $manifest -PathType Leaf)){return $null}
    try{$m=Get-Content -LiteralPath $manifest -Raw|ConvertFrom-Json}
    catch{throw 'Original backup manifest is unreadable.'}
    if($m.SchemaVersion -ne 1 -or !$m.Entries){throw 'Invalid original backup manifest.'}
    $sourceId=[string]$m.SourceSha
    if($sourceId.Length -ne 40 -or $sourceId -match '[^0-9a-f]'){
        throw 'Invalid original backup source identity.'
    }
    $seen=New-Object 'System.Collections.Generic.HashSet[string]' ([System.StringComparer]::OrdinalIgnoreCase)
    foreach($e in $m.Entries){
        $entryName=[string]$e.Name
        if($e.Scope -notin @('root','backend') -or $entryName -match '[^A-Za-z0-9._-]'){
            throw 'Unsafe manifest path.'
        }
        $key=([string]$e.Scope)+'/'+$entryName
        if(!$seen.Add($key)){throw "Duplicate original backup entry: $key"}
        if($e.Existed){
            $entryHash=[string]$e.Sha256
            if($entryHash.Length -ne 64 -or $entryHash -match '[^0-9a-fA-F]'){
                throw "Invalid original backup hash: $key"
            }
            $src=Join-Path (Join-Path $backup ([string]$e.Scope)) $entryName
            if(!(Test-Path -LiteralPath $src -PathType Leaf) -or
               (Get-Sha256Lower $src) -ne $entryHash.ToLowerInvariant()){
                throw "Original backup corrupted: $key"
            }
        }
    }
    return $m
}

if($VerifyOnly){
    if((Test-Path -LiteralPath $backup) -and !(Test-Path -LiteralPath $manifest -PathType Leaf)){
        throw 'Partial original backup detected.'
    }
    if(Test-Path -LiteralPath $manifest -PathType Leaf){[void](Read-ValidatedManifest)}
    Write-Host 'PASS restore launcher entrypoint verified; no files changed.'
    return
}
if(!(Test-Path -LiteralPath $manifest -PathType Leaf)){throw 'No copy-run original backup exists.'}
$running=Get-Process -ErrorAction SilentlyContinue|Where-Object{
    $_.ProcessName -ieq 'OR2006C2C' -or $_.ProcessName -ieq 'outrun-vr-host'
}
if($running){throw 'Close the game and VR host before restoring.'}
$m=Read-ValidatedManifest
$restoreTxn=Join-Path $backup 'RESTORE_IN_PROGRESS.txt'
@(
    "RESTORE_STARTED_UTC=$((Get-Date).ToUniversalTime().ToString('o'))"
    "SOURCE_SHA=$($m.SourceSha)"
)|Set-Content -LiteralPath $restoreTxn -Encoding ascii

# Restore every tracked original only after the complete backup passed validation.
# If any operation throws, RESTORE_IN_PROGRESS.txt remains and CopyRun fails closed.
foreach($e in $m.Entries){
    $base=if($e.Scope -eq 'root'){$root}else{Join-Path $root 'backends/d3d9'}
    $dest=Join-Path $base ([string]$e.Name)
    if($e.Existed){
        New-Item -ItemType Directory -Path $base -Force|Out-Null
        Copy-Item -LiteralPath (Join-Path (Join-Path $backup ([string]$e.Scope)) ([string]$e.Name)) -Destination $dest -Force
        if((Get-Sha256Lower $dest) -ne ([string]$e.Sha256).ToLowerInvariant()){
            throw "Restore verification failed: $($e.Scope)/$($e.Name)"
        }
    } elseif(Test-Path -LiteralPath $dest -PathType Leaf){
        if($e.Scope -eq 'root' -and $e.Name -in @('OutRun2006Tweaks.ini','OutRun2006Tweaks.lods.ini')){
            Write-Host "Leaving user-editable new $($e.Name) (was absent before)."
        }else{
            Remove-Item -LiteralPath $dest -Force
            if(Test-Path -LiteralPath $dest){throw "Restore could not remove package-created file: $($e.Name)"}
        }
    }
}
if(Test-Path -LiteralPath $restoreTxn){Remove-Item -LiteralPath $restoreTxn -Force}

# Mark restore completion before archival. If archival itself fails, CopyRun
# sees RestoredUtc and refuses to reuse this stale baseline.
$restoredUtc=(Get-Date).ToUniversalTime().ToString('o')
$m|Add-Member -NotePropertyName RestoredUtc -NotePropertyValue $restoredUtc -Force
$pending=Join-Path $backup 'original_files.restored.pending.json'
$m|ConvertTo-Json -Depth 8|Set-Content -LiteralPath $pending -Encoding UTF8
Move-Item -LiteralPath $pending -Destination $manifest -Force

$historyRoot=Join-Path $root 'QUEST_APK_COPYRUN_BACKUP_HISTORY'
New-Item -ItemType Directory -Path $historyRoot -Force|Out-Null
$stamp=(Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssfffZ')
$suffix=[guid]::NewGuid().ToString('N').Substring(0,8)
$archiveName=$stamp+'-'+([string]$m.SourceSha).Substring(0,12)+'-'+$suffix
$archive=Join-Path $historyRoot $archiveName
Move-Item -LiteralPath $backup -Destination $archive
if(Test-Path -LiteralPath $backup){throw 'Restored backup could not be archived; refusing stale active baseline.'}

Write-Host 'Original game-folder DLL, DXVK, config, helpers and active session restored.'
Write-Host "Completed baseline archived: $archive"
Write-Host 'The next cockpit test will create a fresh backup of the then-current game folder.'
Write-Host 'Original EXE/assets and saved OutRun2006Tweaks.user.ini remain untouched.'
