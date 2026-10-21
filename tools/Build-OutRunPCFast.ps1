param(
    [switch]$Clean,
    [string]$ExpectedSha = ''
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

if ($sourceSha -notmatch '^[a-fA-F0-9]{40}$') { throw "Invalid HEAD SHA: $sourceSha" }
if ($ExpectedSha -and $sourceSha -ne $ExpectedSha) { throw "PC Fast WRONG CHECKOUT: expected=$ExpectedSha actual=$sourceSha" }
$dirtyTracked = @(git status --porcelain --untracked-files=no)
if ($LASTEXITCODE -ne 0 -or $dirtyTracked.Count -gt 0) { throw "PC Fast tracked source dirty; refusing ambiguous build: $($dirtyTracked -join '; ')" }
$shortSha = $sourceSha.Substring(0, 12)
$jobs = [Math]::Max(1, [Environment]::ProcessorCount)
$root = Join-Path $repoRoot 'out/pc-fast'
$gameBuild = Join-Path $root 'game'
$hostBuild = Join-Path $root 'host'
$packageDir = Join-Path $root 'package'

# Single canonical R26+HUD PC Fast build. Do not append prior v2 script bodies.
$buildContractVersion = 'R26HUD-PC-FAST-v3-EXACT-SHA'
$canonicalGameFlags = @(
    '-DOUTRUN_VR_SAFE_DRAW_COMPARE=OFF'
    '-DOUTRUN_VR_R26_HUD_COMPARE=ON'
    '-DOUTRUN_VR_C1_COMPARE=OFF'
    '-DOUTRUN_VR_C2_COMPARE=OFF'
    '-DOUTRUN_VR_REFACTOR_SPLIT_R33_R32=OFF'
    '-DOUTRUN_VR_REFACTOR_SPLIT_R32_R31=OFF'
    '-DOUTRUN_VR_REFACTOR_SPLIT_R31_R30=OFF'
    '-DOUTRUN_VR_REFACTOR_SPLIT_R30_R29=OFF'
)
$canonicalGameFlagString = $canonicalGameFlags -join ' '
$buildMode = if ($Clean) { 'CLEAN' } else { 'INCREMENTAL' }

function Assert-R26PcBuildContract {
    param([Parameter(Mandatory = $true)][string]$BuildDir)

    $cache = Join-Path $BuildDir 'CMakeCache.txt'
    if (-not (Test-Path $cache)) {
        throw "R26 PC build contract: CMakeCache missing after configure: $cache"
    }

    $required = @(
        'OUTRUN_VR_SAFE_DRAW_COMPARE:BOOL=OFF'
        'OUTRUN_VR_R26_HUD_COMPARE:BOOL=ON'
        'OUTRUN_VR_C1_COMPARE:BOOL=OFF'
        'OUTRUN_VR_C2_COMPARE:BOOL=OFF'

        'OUTRUN_VR_REFACTOR_SPLIT_R33_R32:BOOL=OFF'
        'OUTRUN_VR_REFACTOR_SPLIT_R32_R31:BOOL=OFF'
        'OUTRUN_VR_REFACTOR_SPLIT_R31_R30:BOOL=OFF'
        'OUTRUN_VR_REFACTOR_SPLIT_R30_R29:BOOL=OFF'
    )
    $cacheText = Get-Content $cache -Raw
    foreach ($line in $required) {
        if ($cacheText -notmatch [regex]::Escape($line)) {
            throw "R26 PC build contract mismatch: expected '$line'. Refusing to compile/package a non-R26 renderer configuration."
        }
    }

    Write-Host "PC fast build contract PASS: $buildContractVersion [$canonicalGameFlagString]"
}

if ($Clean -and (Test-Path $root)) {
    Write-Host 'PC fast build: CLEAN requested; deleting persistent build cache.'
    Remove-Item $root -Recurse -Force
}
New-Item -ItemType Directory -Force $root | Out-Null

Remove-Item Env:CI -ErrorAction SilentlyContinue
$totalWatch = [Diagnostics.Stopwatch]::StartNew()

Write-Host "PC fast build: configure Win32 game (persistent cache: $gameBuild)"
Invoke-Checked cmake '-S' '.' '-B' $gameBuild '-G' 'Visual Studio 17 2022' '-A' 'Win32' @canonicalGameFlags
Assert-R26PcBuildContract -BuildDir $gameBuild
# Verify the MSVC compilation graph, not only CMakeCache option strings.
$vcxproj = Join-Path $gameBuild 'outrun2006tweaks.vcxproj'
if (!(Test-Path $vcxproj)) { throw "Missing generated Win32 target: $vcxproj" }
[xml]$projXml = Get-Content $vcxproj -Raw
# PowerShell XML property projection is brittle when an ItemGroup contains no
# ClCompile child (common on clean GitHub-hosted runners). Select by local-name
# across all MSBuild ItemGroups so the source-graph proof works with or without
# the default MSBuild XML namespace.
$compileInputs = @(
    $projXml.SelectNodes("//*[local-name()='ClCompile']") |
        ForEach-Object { $_.GetAttribute('Include') } |
        Where-Object { $_ }
)
$r26Owner = @($compileInputs | Where-Object { $_ -match 'stereo_renderer_r30_r26_safe\.cpp$' })
$r84Owner = @($compileInputs | Where-Object { $_ -match 'stereo_renderer_r33\.cpp$' })
if ($r26Owner.Count -ne 1 -or $r84Owner.Count -ne 0) { throw "PC FAST SOURCE GRAPH MISMATCH: R26=$($r26Owner.Count), R84=$($r84Owner.Count)" }
Write-Host 'PC FAST SOURCE GRAPH VERIFIED: R26+HUD only'
Patch-DependencyProject (Join-Path $gameBuild '_deps/safetyhook-build/src/safetyhook.vcxproj')
Patch-DependencyProject (Join-Path $gameBuild '_deps/zydis-build/Zydis.vcxproj')
Patch-DependencyProject (Join-Path $gameBuild '_deps/zydis-build/zycore/Zycore.vcxproj')

$sdlSourceCandidates = @(
    (Join-Path $gameBuild '_deps/sdl-src/src/joystick/gdk/SDL_gameinputjoystick.cpp'),
    (Join-Path $gameBuild '_deps/sdl-src/src/joystick/gdk/SDL_gameinputjoystick.c')
)
$sdlSource = $sdlSourceCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
$sdlConfig = Join-Path $gameBuild '_deps/sdl-build/include-config-release/build_config/SDL_build_config.h'
if (-not $sdlSource) {
    throw "SDL GameInput workaround target missing. Checked: $($sdlSourceCandidates -join ', ')"
}
if (-not (Test-Path $sdlConfig)) { throw "SDL config workaround target missing: $sdlConfig" }
Write-Host "PC fast build: disabling SDL GameInput source $sdlSource"
Set-Content -Path $sdlSource -Value ''
$sdlText = Get-Content $sdlConfig -Raw
if ($sdlText -match '#define SDL_JOYSTICK_GAMEINPUT 1') {
    $sdlText = $sdlText -replace '#define SDL_JOYSTICK_GAMEINPUT 1', '/* #undef SDL_JOYSTICK_GAMEINPUT */'
    Set-Content -Path $sdlConfig -Value $sdlText
}

$gameWatch = [Diagnostics.Stopwatch]::StartNew()
Write-Host "PC fast build: compile game DLL with up to $jobs parallel jobs"
Invoke-Checked cmake '--build' $gameBuild '--config' 'Release' '--target' 'outrun2006tweaks' '--parallel' "$jobs"
Assert-R26PcBuildContract -BuildDir $gameBuild
if ((git rev-parse HEAD).Trim() -ne $sourceSha) { throw 'Source SHA changed during compile' }
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

$dllCandidates = @(Get-ChildItem $gameBuild -Recurse -File -Filter dinput8.dll | Where-Object { $_.FullName -match '\\bin\\' })
if ($dllCandidates.Count -ne 1) { throw "Expected precisely one game DLL; found $($dllCandidates.Count)" }
$dll = $dllCandidates[0]
$bytes = [IO.File]::ReadAllBytes($dll.FullName)
if ($bytes.Length -lt 512 -or $bytes[0] -ne 0x4d -or $bytes[1] -ne 0x5a) { throw 'Invalid game PE DLL' }
$peOffset = [BitConverter]::ToInt32($bytes, 0x3c)
if ($peOffset -le 0 -or $peOffset + 6 -ge $bytes.Length -or [BitConverter]::ToUInt16($bytes,$peOffset + 4) -ne 0x014c) { throw 'PC Fast game DLL is not x86' }
$signature = [Text.Encoding]::ASCII.GetString($bytes)
if (!$signature.Contains('VR R26+HUD SAFE TEST:') -or $signature.Contains('VR R33 DISPATCH: final Reset/Present/DirectGPU/draw physical ownership READY')) { throw 'PC Fast wrong embedded renderer (R26 marker absent or R84 present)' }
$dllSha256 = (Get-FileHash $dll.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
Write-Host "PC FAST COMPILED R26 DLL SHA256=$dllSha256"

$hostExe = Join-Path $hostBuild 'bin/outrun-vr-host.exe'
if (-not (Test-Path $hostExe)) { throw 'outrun-vr-host.exe missing after incremental build.' }

Copy-Item $dll.FullName (Join-Path $backendDir 'dinput8.dll')
Copy-Item $hostExe (Join-Path $backendDir 'outrun-vr-host.exe')
Set-Content (Join-Path $backendDir 'SOURCE_SHA.txt') $sourceSha -Encoding ascii
Set-Content (Join-Path $backendDir 'VARIANT_ID.txt') 'ACTIVE_R26_R43_R44' -Encoding ascii
Assert-R26PcBuildContract -BuildDir $gameBuild
Set-Content (Join-Path $backendDir 'CMAKE_FLAGS.txt') $canonicalGameFlagString -Encoding ascii
Set-Content (Join-Path $backendDir 'BUILD_CONTRACT.txt') $buildContractVersion -Encoding ascii
Set-Content (Join-Path $backendDir 'GAME_DLL_SHA256.txt') $dllSha256 -Encoding ascii
if ((Get-FileHash (Join-Path $backendDir 'dinput8.dll') -Algorithm SHA256).Hash.ToLowerInvariant() -ne $dllSha256) { throw 'Staged DLL hash mismatch' }

Copy-Item 'OutRun2006Tweaks.ini' (Join-Path $packageDir 'OutRun2006Tweaks.ini')
Copy-Item 'OutRun2006Tweaks.lods.ini' (Join-Path $packageDir 'OutRun2006Tweaks.lods.ini')

$runtimeFiles = @(
    'OutRunVR-TestProfiles.ps1',
    'Select-OutRunVRBackend.ps1',
    'Run-OutRunVRTest.ps1',
    'Run-OutRunVRTest.cmd',
    'START_DX9EX_PC_FAST.cmd',
    'Collect-OutRunVRLogs.ps1',
    'Collect-OutRunVRLogs.cmd',
    'Analyze-OutRunVRSession.ps1',
    'OutRunVR-Backend-Selector.ps1',
    'OutRunVR-Backend-Selector.cmd',
    'OutRunVR-Slot-Selector.ps1',
    'OutRunVR-Slot-Selector.cmd',
    'analyze_outrun_assets.py'
)
foreach ($file in $runtimeFiles) {
    $src = Join-Path 'tools' $file
    if (-not (Test-Path $src)) { throw "Runtime packaging file missing: $src" }
    $dst = Join-Path $packageDir $file
    Copy-Item $src $dst
    # Windows PowerShell 5.1 treats UTF-8 without BOM as the active ANSI code
    # page. Re-emit packaged PS1 launchers as UTF-8-with-BOM so Korean UI text
    # cannot corrupt quotes/tokens on GitHub-hosted Windows runners or user PCs.
    if ([IO.Path]::GetExtension($file) -ieq '.ps1') {
        $utf8Text = Get-Content -LiteralPath $src -Raw -Encoding UTF8
        Set-Content -LiteralPath $dst -Value $utf8Text -Encoding UTF8
    }
}
Copy-Item 'docs/VR_TEST_STRATEGY.md' (Join-Path $packageDir 'VR_TEST_STRATEGY.md')

# A successful CMake build says NOTHING about the PowerShell launcher.
# Fail packaging before ZIP publication if ANY shipped PS1 is unparseable.
# This uses the actual Windows PowerShell AST parser on the PC build runner.
foreach ($scriptFile in Get-ChildItem -LiteralPath $packageDir -Filter '*.ps1' -File) {
    $parseTokens = $null
    $parseErrors = $null
    [void][System.Management.Automation.Language.Parser]::ParseFile(
        $scriptFile.FullName, [ref]$parseTokens, [ref]$parseErrors)
    if ($parseErrors -and $parseErrors.Count -gt 0) {
        $parseDetail = ($parseErrors | ForEach-Object { $_.ToString() }) -join '; '
        throw "PC Fast launcher syntax invalid: $($scriptFile.Name) :: $parseDetail"
    }
}
Write-Host 'PC Fast launcher PowerShell parser: PASS (all packaged PS1 files)'


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
Set-Content (Join-Path $packageDir 'PC_FAST_BUILD.txt') "PC_FAST_${buildMode}_NOT_FINAL_CI" -Encoding ascii

$buildInputs = [ordered]@{
    SchemaVersion = 1
    BuildMatrixId = $matrixId
    IntegrationSha = $sourceSha
    VariantId = 'ACTIVE_R26_R43_R44'
    DefaultTestProfile = 'CORRECTNESS'
    Profiles = @('CONTROL', 'CORRECTNESS', 'PERFORMANCE')
    UserRuntimeVerified = $false
    ValidationClass = 'PC_FAST_INCREMENTAL_NOT_FINAL_CI'
    BuildMode = $buildMode
    BuildContract = $buildContractVersion
    CMakeFlags = $canonicalGameFlagString
    RendererSourceOwner = 'src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp'
    GameDllSha256 = $dllSha256
}
$buildInputs | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $packageDir 'BUILD_INPUTS.json') -Encoding UTF8
if ((git rev-parse HEAD).Trim() -ne $sourceSha) { throw 'Checkout changed before package publication' }

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
# Never publish an older queued build over the newest test folder.
# The runner checkout stays pinned to ExpectedSha; also verify the GitHub
# branch tip *at publication time*, after all expensive compilation is done.
$hostedArtifactBuild = $env:GITHUB_ACTIONS -eq 'true'
if ($ExpectedSha -and -not $hostedArtifactBuild) {
    $publicationBranch = if ([string]::IsNullOrWhiteSpace($env:GITHUB_REF_NAME)) {
        'vr-d3d9ex-focus'
    } else {
        $env:GITHUB_REF_NAME
    }
    $remote = @(git ls-remote --heads origin ("refs/heads/{0}" -f $publicationBranch))
    if ($LASTEXITCODE -ne 0 -or $remote.Count -ne 1) { throw 'PC Fast cannot verify branch tip before publication' }
    $remoteSha = ($remote[0] -split '\s+')[0]
    if ($remoteSha -ne $ExpectedSha) {
        throw "PC Fast stale build blocked before LATEST publication: expected=$ExpectedSha remote=$remoteSha"
    }
} elseif ($ExpectedSha -and $hostedArtifactBuild) {
    # GitHub artifacts are immutable and SHA-named. A docs-only branch advance
    # during a long clean hosted build must not discard an already verified
    # exact-SHA ZIP; only the persistent self-hosted LATEST path needs the
    # branch-tip publication fence.
    Write-Host "PC Fast hosted artifact: exact SHA package retained even if branch tip advances ($ExpectedSha)"
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
    "BuildMode=$buildMode"
    "BuildContract=$buildContractVersion"
    "RendererVariant=ACTIVE_R26_R43_R44"
    "GameDllSha256=$dllSha256"
    "CMakeFlags=$canonicalGameFlagString"
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
Write-Host "  Mode   : $buildMode"
Write-Host "  Contract: $buildContractVersion"
Write-Host "  Source : $sourceSha"
Write-Host "  Renderer: R26+HUD / ACTIVE_R26_R43_R44"
Write-Host "  DLL SHA: $dllSha256"
Write-Host "  Game   : $([Math]::Round($gameWatch.Elapsed.TotalSeconds, 1)) s"
Write-Host "  Host   : $([Math]::Round($hostWatch.Elapsed.TotalSeconds, 1)) s"
Write-Host "  Package: $([Math]::Round($packageWatch.Elapsed.TotalSeconds, 1)) s"
Write-Host "  Total  : $([Math]::Round($totalWatch.Elapsed.TotalSeconds, 1)) s"
Write-Host "  Test   : $resolvedDrop"
Write-Host "  ZIP    : $resolvedZip"
Write-Host "  SHA256 : $zipHash"
