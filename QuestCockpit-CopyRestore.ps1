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
if($VerifyOnly){
    Write-Host 'PASS restore launcher entrypoint verified; no files changed.'
    return
}
if(!(Test-Path $manifest -PathType Leaf)){throw 'No copy-run original backup exists.'}
$running=Get-Process -ErrorAction SilentlyContinue|Where-Object{
    $_.ProcessName -ieq 'OR2006C2C' -or $_.ProcessName -ieq 'outrun-vr-host'
}
if($running){throw 'Close the game and VR host before restoring.'}
$m=Get-Content $manifest -Raw|ConvertFrom-Json
if($m.SchemaVersion -ne 1 -or !$m.Entries){throw 'Invalid original backup manifest.'}
# Validate ALL saved originals before modifying anything.
foreach($e in $m.Entries){
    if($e.Scope -notin @('root','backend') -or
       $e.Name -notmatch '^[A-Za-z0-9._-]+$'){throw 'Unsafe manifest path.'}
    if($e.Existed){
        $src=Join-Path (Join-Path $backup $e.Scope) $e.Name
        if(!(Test-Path $src -PathType Leaf) -or
           (Get-Sha256Lower $src) -ne [string]$e.Sha256){
            throw "Original backup corrupted: $($e.Scope)/$($e.Name)"
        }
    }
}
foreach($e in $m.Entries){
    $base=if($e.Scope -eq 'root'){$root}else{Join-Path $root 'backends/d3d9'}
    $dest=Join-Path $base $e.Name
    if($e.Existed){
        New-Item -ItemType Directory -Path $base -Force|Out-Null
        Copy-Item -LiteralPath (Join-Path (Join-Path $backup $e.Scope) $e.Name) -Destination $dest -Force
    } elseif(Test-Path $dest -PathType Leaf){
        if($e.Scope -eq 'root' -and
           $e.Name -in @('OutRun2006Tweaks.ini','OutRun2006Tweaks.lods.ini')){
            Write-Host "Leaving user-editable new $($e.Name) (was absent before)."
        }else{
            Remove-Item -LiteralPath $dest -Force
        }
    }
}
Write-Host 'Original game-folder DLL, DXVK, config, helpers and active session restored.'
Write-Host 'APK payload and original backup folder are retained; original EXE/assets untouched.'
