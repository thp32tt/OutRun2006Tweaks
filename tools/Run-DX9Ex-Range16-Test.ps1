param()
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$meta = Join-Path $root 'RANGE16_VARIANT.txt'
if (-not (Test-Path $meta)) { throw 'RANGE16_VARIANT.txt missing.' }
$variant = ((Get-Content $meta | Where-Object { $_ -match '^variant=' } | Select-Object -First 1) -split '=',2)[1].Trim()
$game = Join-Path $root 'OR2006C2C.EXE'
if (-not (Test-Path $game)) { throw 'OR2006C2C.EXE not found. Extract ZIP into the game folder.' }
if (Get-Process OR2006C2C -ErrorAction SilentlyContinue) { throw 'Game is already running.' }

Get-Process outrun-vr-host -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 500

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$logRoot = Join-Path $root 'DX9EX_RANGE16_LOGS'
$session = Join-Path $logRoot "$variant-$stamp"
$pre = Join-Path $logRoot "_preexisting-$stamp"
New-Item -ItemType Directory -Force $session | Out-Null

$patterns = @('OutRun2006Tweaks*.log','outrun-vr-host*.log','outrun-vr-host-pipeline*.log','outrun-vr-watchdog*.log')
$old=@()
foreach($pattern in $patterns){ $old += Get-ChildItem $root -Filter $pattern -File -ErrorAction SilentlyContinue }
$old=$old | Sort-Object FullName -Unique
if($old.Count -gt 0){
  New-Item -ItemType Directory -Force $pre | Out-Null
  foreach($file in $old){ Move-Item $file.FullName (Join-Path $pre $file.Name) -Force }
}

$args=@(
 '-FramerateLimit=0',
 '-FramerateFastLoad=0',
 '-FramerateInterpolation=true',
 '-FramerateUnlockExperimental=true',
 '-FrameCadenceMode=1',
 '-FrameCadenceTargetHz=0',
 '-TargetRefreshRateHz=0',
 '-DisableDesktopVsync=true',
 '-SkyGlowFactor=1',
 '-HudScale=0.55',
 '-PreferD3D9Ex=true',
 '-DirectGpuOnly=true',
 '-DisableDesktopDuplication=false'
)
Set-Content (Join-Path $session 'RUN_ARGS.txt') ($args -join ' ') -Encoding UTF8
Copy-Item $meta (Join-Path $session 'RANGE16_VARIANT.txt')

Write-Host "DX9Ex Range16 test: $variant"
Write-Host "Visual variants: check HUD rank, white rank/YES-NO, lens flare, world geometry."
Write-Host "FAST variants: focus on FPS/stutter first; also note any graphics regression."
$p=Start-Process -FilePath $game -ArgumentList $args -WorkingDirectory $root -PassThru
$p.WaitForExit()
Start-Sleep -Seconds 2
Get-Process outrun-vr-host -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

foreach($pattern in $patterns){
  Get-ChildItem $root -Filter $pattern -File -ErrorAction SilentlyContinue |
    ForEach-Object { Copy-Item $_.FullName (Join-Path $session $_.Name) -Force }
}
@("variant=$variant","finished=$(Get-Date -Format o)","gameExitCode=$($p.ExitCode)") |
 Set-Content (Join-Path $session 'TEST_RESULT.txt') -Encoding UTF8
$zip=Join-Path $logRoot ("DX9EX_RANGE16_LOG_{0}_{1}.zip" -f $variant,$stamp)
Compress-Archive -Path (Join-Path $session '*') -DestinationPath $zip -Force
Write-Host ""
Write-Host "Upload log ZIP: $zip"
