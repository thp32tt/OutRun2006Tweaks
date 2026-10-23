param()

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$variantFile = Join-Path $root 'DX9EX_VARIANT.txt'
if (-not (Test-Path $variantFile)) { throw 'DX9EX_VARIANT.txt is missing.' }
$variantLine = Get-Content $variantFile | Where-Object { $_ -match '^variant=' } | Select-Object -First 1
if (-not $variantLine) { throw 'variant= entry is missing from DX9EX_VARIANT.txt.' }
$variant = ($variantLine -split '=',2)[1].Trim()

$game = Join-Path $root 'OR2006C2C.EXE'
if (-not (Test-Path $game)) { throw 'OR2006C2C.EXE not found. Extract this ZIP into the OutRun 2006 game folder.' }

if (Get-Process OR2006C2C -ErrorAction SilentlyContinue) {
    throw 'OR2006C2C.EXE is already running. Exit the game before starting a variant test.'
}
Get-Process outrun-vr-host -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 500

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$logRoot = Join-Path $root 'DX9EX_LOGS'
$pre = Join-Path $logRoot "_preexisting-$stamp"
$session = Join-Path $logRoot "$variant-$stamp"
New-Item -ItemType Directory -Force $session | Out-Null

$logPatterns = @(
    'OutRun2006Tweaks*.log',
    'outrun-vr-host*.log',
    'outrun-vr-host-pipeline*.log',
    'outrun-vr-watchdog*.log'
)
$old = @()
foreach ($pattern in $logPatterns) {
    $old += Get-ChildItem -Path $root -Filter $pattern -File -ErrorAction SilentlyContinue
}
$old = $old | Sort-Object FullName -Unique
if ($old.Count -gt 0) {
    New-Item -ItemType Directory -Force $pre | Out-Null
    foreach ($file in $old) { Move-Item $file.FullName (Join-Path $pre $file.Name) -Force }
}

$gameArgs = @(
    '-FramerateLimit=0',
    '-FramerateFastLoad=0',
    '-FramerateInterpolation=true',
    '-FramerateUnlockExperimental=true',
    '-FrameCadenceMode=1',
    '-FrameCadenceTargetHz=0',
    '-DisableDesktopVsync=true',
    '-SkyGlowFactor=1',
    '-PreferD3D9Ex=true',
    '-DirectGpuOnly=false',
    '-DisableDesktopDuplication=false'
)
Set-Content (Join-Path $session 'RUN_ARGS.txt') ($gameArgs -join ' ') -Encoding UTF8
Copy-Item $variantFile (Join-Path $session 'DX9EX_VARIANT.txt')
Copy-Item (Join-Path $root 'OutRun2006Tweaks.ini') (Join-Path $session 'OutRun2006Tweaks.ini')

Write-Host "Starting DX9Ex variant $variant"
Write-Host "Test the same short gameplay section, then exit normally."

$p = Start-Process -FilePath $game -ArgumentList $gameArgs -WorkingDirectory $root -PassThru
$p.WaitForExit()
Start-Sleep -Seconds 2
Get-Process outrun-vr-host -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 700

foreach ($pattern in $logPatterns) {
    Get-ChildItem -Path $root -Filter $pattern -File -ErrorAction SilentlyContinue |
        ForEach-Object { Copy-Item $_.FullName (Join-Path $session $_.Name) -Force }
}

$result = @(
    "variant=$variant",
    "finished=$(Get-Date -Format o)",
    "gameExitCode=$($p.ExitCode)",
    "policy=DX9Ex-only; dynamic XR cadence; DirectGPU preferred with desktop fallback allowed"
)
Set-Content (Join-Path $session 'TEST_RESULT.txt') $result -Encoding UTF8

$zip = Join-Path $logRoot ("DX9EX_LOG_{0}_{1}.zip" -f $variant,$stamp)
Compress-Archive -Path (Join-Path $session '*') -DestinationPath $zip -Force
Write-Host ""
Write-Host "Log ZIP created:"
Write-Host $zip
Write-Host ""
Write-Host "Upload that ZIP with a short note about graphics correctness, stereo depth, and stutter."
