param(
    [switch]$Clean
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)][string]$File,
        [Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments
    )
    & $File @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$File failed with exit code $LASTEXITCODE"
    }
}

function Patch-DependencyProject {
    param([Parameter(Mandatory = $true)][string]$Path)
    if (-not (Test-Path $Path)) {
        throw "Expected dependency project missing: $Path"
    }
    $text = Get-Content $Path -Raw
    if ($text -notmatch '_DISABLE_CONSTEXPR_MUTEX_CONSTRUCTOR') {
        $text = $text -replace 'ZYCORE_STATIC_BUILD', '_DISABLE_CONSTEXPR_MUTEX_CONSTRUCTOR;ZYCORE_STATIC_BUILD'
        Set-Content -Path $Path -Value $text
    }
}

if (-not (Get-Command cmake -ErrorAction SilentlyContinue)) {
    throw 'cmake.exe is not in PATH. Install CMake before starting the runner.'
}
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw 'git.exe is not in PATH. Install Git for Windows before starting the runner.'
}

$sourceSha = (git rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0) {
    throw 'Unable to read source SHA.'
}

$shortSha = $sourceSha.Substring(0, 12)
$jobs = [Math]::Max(1, [Environment]::ProcessorCount)
$root = Join-Path $repoRoot 'out/pc-fast'
$gameBuild = Join-Path $root 'game'
$hostBuild = Join-Path $root 'host'
$packageDir = Join-Path $root 'package'

if ($Clean -and (Test-Path $root)) {
    Write-Host 'PC fast build: CLEAN requested; deleting persistent build cache.'
    Remove-Item $root -Recurse -Force
}
New-Item -ItemType Directory -Force $root | Out-Null

Remove-Item Env:CI -ErrorAction SilentlyContinue
$totalWatch = [Diagnostics.Stopwatch]::StartNew()

Write-Host "PC fast build: configure Win32 game (persistent cache: $gameBuild)"
Invoke-Checked cmake '-S' '.' '-B' $gameBuild '-G' 'Visual Studio 17 2022' '-A' 'Win32' '-DOUTRUN_VR_SAFE_DRAW_COMPARE=OFF' '-DOUTRUN_VR_R26_HUD_COMPARE=OFF' '-DOUTRUN_VR_C1_COMPARE=OFF' '-DOUTRUN_VR_C2_COMPARE=OFF'

Patch-DependencyProject (Join-Path $gameBuild '_deps/safetyhook-build/src/safetyhook.vcxproj')
Patch-DependencyProject (Join-Path $gameBuild '_deps/zydis-build/Zydis.vcxproj')
Patch-DependencyProject (Join-Path $gameBuild '_deps/zydis-build/zycore/Zycore.vcxproj')

$sdlSource = Join-Path $gameBuild '_deps/sdl-src/src/joystick/gdk/SDL_gameinputjoystick.c'
$sdlConfig = Join-Path $gameBuild '_deps/sdl-build/include-config-release/build_config/SDL_build_config.h'
if (-not (Test-Path $sdlSource)) { throw "SDL source workaround target missing: $sdlSource" }
if (-not (Test-Path $sdlConfig)) { throw "SDL config workaround target missing: $sdlConfig" }
Set-Content -Path $sdlSource -Value ''
$sdlText = Get-Content $sdlConfig -Raw
if ($sdlText -match '#define SDL_JOYSTICK_GAMEINPUT 1') {
    $sdlText = $sdlText -replace '#define SDL_JOYSTICK_GAMEINPUT 1', '/* #undef SDL_JOYSTICK_GAMEINPUT */'
    Set-Content -Path $sdlConfig -Value $sdlText
}

$gameWatch = [Diagnostics.Stopwatch]::StartNew()
Write-Host "PC fast build: compile game DLL with up to $jobs parallel jobs"
Invoke-Checked cmake '--build' $gameBuild '--config' 'Release' '--target' 'outrun2006tweaks' '--parallel' "$jobs"
$gameWatch.Stop()

$hostWatch = [Diagnostics.Stopwatch]::StartNew()
Write-Host "PC fast build: configure/build x64 OpenXR host (persistent cache: $hostBuild)"
Invoke-Checked cmake '-S' 'vrhost' '-B' $hostBuild '-G' 'Visual Studio 17 2022' '-A' 'x64'
Invoke-Checked cmake '--build' $hostBuild '--config' 'Release' '--target' 'outrun-vr-host' '--parallel' "$jobs"
$hostWatch.Stop()

$packageWatch = [Diagnostics.Stopwatch]::StartNew()
if (Test-Path $packageDir) {
    Remove-Item $packageDir -Recurse -Force
}
$backendDir = Join-Path $packageDir 'backends/d3d9'
New-Item -ItemType Directory -Force $backendDir | Out-Null

$dll = Get-ChildItem $gameBuild -Recurse -Filter dinput8.dll | Where-Object { $_.FullName -match '\\bin\\' } | Select-Object -First 1
if (-not $dll) { throw 'dinput8.dll missing after incremental build.' }

$hostExe = Join-Path $hostBuild 'bin/outrun-vr-host.exe'
if (-not (Test-Path $hostExe)) { throw 'outrun-vr-host.exe missing after incremental build.' }

Copy-Item $dll.FullName (Join-Path $backendDir 'dinput8.dll')
Copy-Item $hostExe (Join-Path $backendDir 'outrun-vr-host.exe')
Set-Content (Join-Path $backendDir 'SOURCE_SHA.txt') $sourceSha -Encoding ascii
Set-Content (Join-Path $backendDir 'VARIANT_ID.txt') 'ACTIVE_FULL_R34' -Encoding ascii
Set-Content (Join-Path $backendDir 'CMAKE_FLAGS.txt') '-DOUTRUN_VR_SAFE_DRAW_COMPARE=OFF -DOUTRUN_VR_R26_HUD_COMPARE=OFF -DOUTRUN_VR_C1_COMPARE=OFF -DOUTRUN_VR_C2_COMPARE=OFF' -Encoding ascii

Copy-Item 'OutRun2006Tweaks.ini' (Join-Path $packageDir 'OutRun2006Tweaks.ini')
Copy-Item 'OutRun2006Tweaks.lods.ini' (Join-Path $packageDir 'OutRun2006Tweaks.lods.ini')

$runtimeFiles = @(
    'OutRunVR-TestProfiles.ps1',
    'Select-OutRunVRBackend.ps1',
    'Run-OutRunVRTest.ps1',
    'Run-OutRunVRTest.cmd',
    'Collect-OutRunVRLogs.ps1',
    'Collect-OutRunVRLogs.cmd',
    'OutRunVR-Backend-Selector.ps1',
    'OutRunVR-Backend-Selector.cmd'
)
foreach ($file in $runtimeFiles) {
    $src = Join-Path 'tools' $file
    if (-not (Test-Path $src)) { throw "Runtime packaging file missing: $src" }
    Copy-Item $src (Join-Path $packageDir $file)
}
Copy-Item 'docs/VR_TEST_STRATEGY.md' (Join-Path $packageDir 'VR_TEST_STRATEGY.md')

@(
    'OUTRUN VR TEST / LOG UPLOAD'
    ''
    '1. Run the packaged test normally.'
    '2. Exit the game to let the collector seal the session.'
    '3. Upload the generated OutRun2_VR_ANALYZE_*.zip to the OutRun VR project chat.'
    '4. No additional problem description is required. The ZIP itself is the analysis request.'
    ''
    'This package was produced by the PC FAST incremental path.'
    'It is for interactive test/retest iteration and is not final hosted-CI validation.'
) | Set-Content (Join-Path $packageDir 'UPLOAD_LOG_ZIP_ONLY.txt') -Encoding UTF8

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$matrixId = "PC-FAST-$stamp-$shortSha"
Set-Content (Join-Path $packageDir 'BUILD_MATRIX_ID.txt') $matrixId -Encoding ascii
Set-Content (Join-Path $packageDir 'PC_FAST_BUILD.txt') 'PC_FAST_INCREMENTAL_NOT_FINAL_CI' -Encoding ascii

$buildInputs = [ordered]@{
    SchemaVersion = 1
    BuildMatrixId = $matrixId
    IntegrationSha = $sourceSha
    VariantId = 'ACTIVE_FULL_R34'
    DefaultTestProfile = 'CORRECTNESS'
    Profiles = @('CONTROL', 'CORRECTNESS', 'PERFORMANCE')
    UserRuntimeVerified = $false
    ValidationClass = 'PC_FAST_INCREMENTAL_NOT_FINAL_CI'
}
$buildInputs | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $packageDir 'BUILD_INPUTS.json') -Encoding UTF8

$bad = Get-ChildItem $packageDir -Recurse -File | Where-Object { $_.Name -in @('d3d9.dll', 'multiviewpatcher.dll', 'outrun-vr-host-dx12.exe') }
if ($bad) { throw "Forbidden backend payload: $($bad.FullName -join ', ')" }

$packageRoot = (Resolve-Path $packageDir).Path
Get-ChildItem $packageDir -Recurse -File | Get-FileHash -Algorithm SHA256 | ForEach-Object {
    "$($_.Hash)  $($_.Path.Substring($packageRoot.Length + 1))"
} | Set-Content (Join-Path $packageDir 'SHA256SUMS.txt') -Encoding ascii

$zipName = "OutRun2_VR_PC_FAST_$($stamp)_$($shortSha).zip"
$zipPath = Join-Path $root $zipName
Compress-Archive -Path (Join-Path $packageDir '*') -DestinationPath $zipPath -Force

if (-not [string]::IsNullOrWhiteSpace($env:OUTRUN_TEST_DROP_ROOT)) {
    $dropRoot = $env:OUTRUN_TEST_DROP_ROOT
} elseif (Test-Path 'L:\') {
    # The interactive self-hosted PC uses L: as the fast SSD. Keep test payloads
    # off the small system drive by default.
    $dropRoot = 'L:\OutRunTestBuilds'
} else {
    $desktop = [Environment]::GetFolderPath('Desktop')
    if ([string]::IsNullOrWhiteSpace($desktop)) {
        $desktop = Join-Path $env:USERPROFILE 'Desktop'
    }
    $dropRoot = Join-Path $desktop 'OutRunTestBuilds'
}
$latestDrop = Join-Path $dropRoot 'LATEST'
New-Item -ItemType Directory -Force $dropRoot | Out-Null
if (Test-Path $latestDrop) { Remove-Item $latestDrop -Recurse -Force }
Copy-Item $packageDir $latestDrop -Recurse
Copy-Item $zipPath (Join-Path $dropRoot $zipName) -Force

$zipHash = (Get-FileHash $zipPath -Algorithm SHA256).Hash
@(
    "SourceSha=$sourceSha"
    "BuildMatrixId=$matrixId"
    "Zip=$zipName"
    "ZipSha256=$zipHash"
    "ValidationClass=PC_FAST_INCREMENTAL_NOT_FINAL_CI"
) | Set-Content (Join-Path $latestDrop 'PC_BUILD_INFO.txt') -Encoding UTF8

Get-ChildItem $dropRoot -Filter 'OutRun2_VR_PC_FAST_*.zip' -File | Sort-Object LastWriteTime -Descending | Select-Object -Skip 8 | Remove-Item -Force -ErrorAction SilentlyContinue

$resolvedZip = (Resolve-Path $zipPath).Path
$resolvedDrop = (Resolve-Path $latestDrop).Path
Set-Content (Join-Path $root 'LAST_ZIP_PATH.txt') $resolvedZip -Encoding UTF8
Set-Content (Join-Path $root 'LAST_DROP_PATH.txt') $resolvedDrop -Encoding UTF8

$packageWatch.Stop()
$totalWatch.Stop()

Write-Host ''
Write-Host 'PC FAST BUILD READY'
Write-Host "  Source : $sourceSha"
Write-Host "  Game   : $([Math]::Round($gameWatch.Elapsed.TotalSeconds, 1)) s"
Write-Host "  Host   : $([Math]::Round($hostWatch.Elapsed.TotalSeconds, 1)) s"
Write-Host "  Package: $([Math]::Round($packageWatch.Elapsed.TotalSeconds, 1)) s"
Write-Host "  Total  : $([Math]::Round($totalWatch.Elapsed.TotalSeconds, 1)) s"
Write-Host "  Test   : $resolvedDrop"
Write-Host "  ZIP    : $resolvedZip"
Write-Host "  SHA256 : $zipHash"
