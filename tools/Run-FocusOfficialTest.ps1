param()
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $root
$health = Join-Path $root 'DX9EX_LAUNCH_HEALTH.txt'
$errorFile = Join-Path $root 'OUTRUNVR_LAUNCH_ERROR.txt'
$gamePath = Join-Path $root 'OR2006C2C.EXE'
$variantPath = Join-Path $root 'DX9EX_VARIANT.txt'
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$logRoot = Join-Path $root 'DX9EX_LOGS'
$session = Join-Path $logRoot $stamp
$hostSeen = $false
$hostLost = $false
$hostFirstSeen = ''
$hostMissingSeconds = 0
$exitCode = -1
$gameProcess = $null
try {
    foreach ($file in @('OR2006C2C.EXE','dinput8.dll','outrun-vr-host.exe','OutRun2006Tweaks.ini','DX9EX_VARIANT.txt')) {
        if (-not (Test-Path -LiteralPath (Join-Path $root $file))) { throw "Missing $file; extract one ZIP directly beside the original game EXE." }
    }
    $line = @(Get-Content -LiteralPath $variantPath | Where-Object { $_ -match '^variant=' } | Select-Object -First 1)
    if ($line.Count -ne 1) { throw 'DX9EX_VARIANT.txt has no variant= entry.' }
    $variant = ($line[0] -split '=',2)[1].Trim()
    if ($variant -notin @('R26_FOCUS_OFFICIAL_TEST','R26_FOCUS_OFFICIAL_DEBUG')) { throw "Unexpected test variant: $variant" }
    if (Get-Process -Name OR2006C2C -ErrorAction SilentlyContinue) { throw 'Original game is already running. Exit it before launching this test.' }
    Get-Process -Name outrun-vr-host -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    New-Item -ItemType Directory -Force -Path $session | Out-Null
    # Refuse to run with an invalid INI. Prior 2026-10-24 packages shipped
    # duplicated [VR].DriverSeatCarSpaceBasis and silently fell back to defaults.
    foreach ($iniName in @('OutRun2006Tweaks.ini','OutRun2006Tweaks.user.ini')) {
        $iniPath = Join-Path $root $iniName
        if (-not (Test-Path -LiteralPath $iniPath)) { continue }
        $currentSection = ''
        $seenKeys = @{}
        $lineNo = 0
        foreach ($rawLine in (Get-Content -LiteralPath $iniPath)) {
            $lineNo++
            $cleanLine = $rawLine.Trim()
            if ($cleanLine -match '^[#;]' -or $cleanLine -eq '') { continue }
            if ($cleanLine -match '^\[([^\]]+)\]') {
                $currentSection = $matches[1].Trim().ToLowerInvariant()
                continue
            }
            if ($cleanLine -match '^([A-Za-z_][A-Za-z0-9_\.]*)\s*=') {
                $keyId = $currentSection + '|' + $matches[1].ToLowerInvariant()
                if ($seenKeys.ContainsKey($keyId)) {
                    throw ("INI_DUPLICATE_KEY in " + $iniName + " line " + $lineNo + ": " + $keyId + "; game startup canceled instead of silently using defaults.")
                }
                $seenKeys[$keyId] = $lineNo
            }
        }
    }
    $debugMode = $variant -eq 'R26_FOCUS_OFFICIAL_DEBUG'
    # Debug gathers diagnostic logical GPU Draw sampling, never enables experimental VB/throttle render changes.
    $env:OUTRUN_VR_R30_PARTICLE_VB = '0'
    $env:OUTRUN_VR_GPU_PROFILE = if ($debugMode) { '1' } else { '0' }
    $env:OUTRUN_VR_GPU_PROFILE_CENSUS_V2 = if ($debugMode) { '1' } else { '0' }
    $env:OUTRUN_VR_GPU_SCENE = $variant
    $argsList = @(
        '-FramerateLimit=0','-FramerateFastLoad=0',
        '-FramerateInterpolation=true','-FramerateUnlockExperimental=true',
        '-FrameCadenceMode=1','-FrameCadenceTargetHz=0',
        '-DisableDesktopVsync=true','-SkyGlowFactor=4',
        '-PreferD3D9Ex=true','-DirectGpuOnly=false','-DisableDesktopDuplication=false',
        '-ReflectionLateFrameThrottle=false','-DriverSeatView=false',
        '-RivalDx11NativeRoute=false','-UIScalingMode=1',
        '-AutoRenderResolution=true','-FollowGameResolution=false',
        '-PreserveLogicalBackBuffer=true',
        '-MirrorPreserveAspect=true',
        '-UnifiedEyeMenuSource=false','-AntiAliasing=2',
        '-Hud1080pReference=true','-HudScale=0.55',
        '-MenuScale=1.00','-CullingUnionMarginDegrees=8.0'
    )
    @("sourceSha=$(Get-Content (Join-Path $root 'SOURCE_SHA.txt') -ErrorAction SilentlyContinue)",
      "variant=$variant","debug=$debugMode","arguments=$($argsList -join ' ')",
      "OUTRUN_VR_GPU_PROFILE=$env:OUTRUN_VR_GPU_PROFILE",
      "OUTRUN_VR_GPU_PROFILE_CENSUS_V2=$env:OUTRUN_VR_GPU_PROFILE_CENSUS_V2",
      "runtimeValidation=UNTESTED") | Set-Content -LiteralPath (Join-Path $session 'RUN_CONFIG.txt') -Encoding UTF8
    # Record the actual installed payload, not only a package-label SHA.
    $binaryIdentity = @('dinput8.dll','outrun-vr-host.exe') | ForEach-Object {
        $binaryPath = Join-Path $root $_
        [PSCustomObject]@{ name = $_; sha256 = (Get-FileHash -LiteralPath $binaryPath -Algorithm SHA256).Hash; bytes = (Get-Item -LiteralPath $binaryPath).Length }
    }
    ConvertTo-Json -InputObject @($binaryIdentity) | Set-Content -LiteralPath (Join-Path $session 'BINARY_IDENTITY.json') -Encoding UTF8
    Write-Host "Launching $variant; cockpit is disabled by default because DriverSeatView=true was reported unstable."
    $gameProcess = Start-Process -FilePath $gamePath -WorkingDirectory $root -ArgumentList $argsList -PassThru
    $firstLaunch = Get-Date
    while (-not $gameProcess.HasExited) {
        $hostProcesses = @(Get-Process -Name outrun-vr-host -ErrorAction SilentlyContinue)
        if ($hostProcesses.Count -gt 0) {
            if (-not $hostSeen) { $hostFirstSeen = (Get-Date).ToString('o') }
            $hostSeen = $true
            $hostMissingSeconds = 0
        } elseif ($hostSeen) {
            $hostMissingSeconds += 1
            if ($hostMissingSeconds -ge 10) { $hostLost = $true }
        }
        if ((Get-Date) - $firstLaunch -gt [TimeSpan]::FromSeconds(25) -and -not $hostSeen) {
            Write-Warning 'OpenXR host not observed after 25 seconds; game remains running. Check headset, VDXR, and logs.'
            $firstLaunch = [DateTime]::MaxValue
        }
        Start-Sleep -Seconds 1
        $gameProcess.Refresh()
    }
    $exitCode = $gameProcess.ExitCode
    Start-Sleep -Milliseconds 700
    $gameLog = Join-Path $root 'OutRun2006Tweaks.log'
    $iniParseFailed = (Test-Path -LiteralPath $gameLog) -and
        (Select-String -LiteralPath $gameLog -Pattern 'Settings::read - INI read failed!' -Quiet -ErrorAction SilentlyContinue)
    $state = if ($iniParseFailed) { 'INI_PARSE_FAILED' } elseif (-not $hostSeen) { 'HOST_NEVER_STARTED' } elseif ($hostLost) { 'HOST_DISAPPEARED_DURING_GAME' } elseif ($exitCode -ne 0) { 'GAME_NONZERO_EXIT' } else { 'HOST_PROCESS_OBSERVED_NOT_HMD_VERIFIED' }
    @("variant=$variant","sourceSha=$(Get-Content (Join-Path $root 'SOURCE_SHA.txt') -ErrorAction SilentlyContinue)",
      "hostStatus=$state","hostFirstSeen=$hostFirstSeen","gameExitCode=$exitCode",
      "runtimeValidation=UNTESTED","finished=$((Get-Date).ToString('o'))") | Set-Content -LiteralPath $health -Encoding UTF8
    Copy-Item -LiteralPath $health -Destination (Join-Path $session 'DX9EX_LAUNCH_HEALTH.txt') -Force
    foreach ($pattern in @('OutRun2006Tweaks*.log','outrun-vr-host*.log','outrun-vr-host-pipeline*.log','outrun-vr-watchdog*.log')) {
        Get-ChildItem -Path $root -Filter $pattern -File -ErrorAction SilentlyContinue | ForEach-Object {
            if ($_.Length -lt 2000000000) { Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $session $_.Name) -Force }
            else { Add-Content (Join-Path $session 'LARGE_LOGS_NOT_COPIED.txt') $_.FullName }
        }
    }
    $logZip = Join-Path $logRoot ("DX9EX_LOG_{0}_{1}.zip" -f $variant,$stamp)
    Compress-Archive -Path (Join-Path $session '*') -DestinationPath $logZip -Force
    Write-Host "Log ZIP: $logZip"
    if ($state -ne 'HOST_PROCESS_OBSERVED_NOT_HMD_VERIFIED') { throw "Launch check failed: $state. Session logs saved; do not treat this as VR runtime PASS." }
    exit 0
} catch {
    $msg = $_.Exception.Message
    @("error=$msg","variant=$variant","runtimeValidation=UNTESTED","timestamp=$((Get-Date).ToString('o'))") | Set-Content -LiteralPath $errorFile -Encoding UTF8
    Write-Error $msg -ErrorAction Continue
    exit 5
}
