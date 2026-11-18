param()
$ErrorActionPreference='Stop'
$game=$PSScriptRoot
$exe=Join-Path $game 'OR2006C2C.EXE'
$base=Join-Path $game 'FERRARI13_PAYLOAD'
$mfile=Join-Path $base 'manifest.json'
$src=Join-Path $base 'backend/outrun-vr-host.exe'
$dest=Join-Path $game 'outrun-vr-host.exe'
$launcher=Join-Path $game 'FERRARI13_RUN.ps1'
function Hash([string]$p) { return (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant() }
$newSha='9ecc80a902985506a66b93446f38d724190d622eba09a0f2683891714579460c'
$oldSha='e12a136cba5110216180b68ee2c20cadac1e0fe365bc0a58c4d42003360b5e40'
$dllSha='313d9925b48fab98dbe2445201cfc54a1e2a05ab34fb940b6bc3761c94e97a4e'
foreach($f in @($exe,$mfile,$src,$dest,$launcher,(Join-Path $game 'dinput8.dll'))) {
 if(!(Test-Path -LiteralPath $f -PathType Leaf)){throw ('Missing '+$f+'; use full recovery ZIP instead')}
}
$m=Get-Content -LiteralPath $mfile -Raw | ConvertFrom-Json
if($m.Schema -ne 1 -or $m.CarCount -ne 13 -or @($m.Files).Count -ne 30){throw 'Manifest is not Ferrari13'}
$entry=@($m.Files|Where-Object{ $_.Target -eq 'outrun-vr-host.exe' })
if($entry.Count -ne 1 -or $entry[0].Sha256 -ne $newSha){throw 'Incorrect recovery manifest'}
if((Hash $src) -ne $newSha){throw 'Recovery source host mismatch'}
if((Hash (Join-Path $game 'dinput8.dll')) -ne $dllSha){throw 'Mismatched DLL; use full recovery ZIP to restore matched assets'}
$existing=Hash $dest
if($existing -eq $newSha){
 Write-Host 'PASS: matched host already installed'
 return
}
if($existing -ne $oldSha){throw ('Unknown installed host hash '+$existing+'. No files changed. Use full recovery ZIP.')}
$running=@(Get-Process -Name 'OR2006C2C','outrun-vr-host' -ErrorAction SilentlyContinue)
if($running.Count){throw 'Close original game and VR host before recovery'}
$stamp=(Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssfffZ')
$dir=Join-Path $game ('FERRARI13_HOST_BACKUP_'+$stamp)
New-Item -ItemType Directory -Path $dir -Force|Out-Null
$backup=Join-Path $dir 'outrun-vr-host.exe'
Copy-Item -LiteralPath $dest -Destination $backup -Force
if((Hash $backup) -ne $oldSha){throw 'Failed to protect old host; no original files touched'}
try{
 Copy-Item -LiteralPath $src -Destination $dest -Force
 if((Hash $dest) -ne $newSha){throw 'Post-install host SHA mismatch'}
}catch{
 Copy-Item -LiteralPath $backup -Destination $dest -Force
 throw
}
Write-Host ('PASS: matched VR host installed. Backup at '+$backup)
Write-Host 'No original game executable, 13 body models or 13 dashboard files were modified.'
