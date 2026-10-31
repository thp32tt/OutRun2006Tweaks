param(
    [string]$GameDirectory = '',
    [switch]$ProbeOnly,
    [switch]$ApproveTemporaryWrapperIsolation
)
$ErrorActionPreference = 'Stop'
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (!$GameDirectory) {
    if (Test-Path -LiteralPath (Join-Path $scriptDir 'OR2006C2C.EXE')) { $GameDirectory = $scriptDir }
    elseif (Test-Path -LiteralPath (Join-Path (Split-Path -Parent $scriptDir) 'OR2006C2C.EXE')) {
        $GameDirectory = Split-Path -Parent $scriptDir
    }
    elseif ($ProbeOnly) { $GameDirectory = $scriptDir }
    else { $GameDirectory = Read-Host 'Full OutRun game folder containing OR2006C2C.EXE' }
}
if (!$GameDirectory) { throw 'Game folder not specified.' }
$gameDir = (Resolve-Path -LiteralPath $GameDirectory).Path
$exePath = Join-Path $gameDir 'OR2006C2C.EXE'
$wrapperPath = Join-Path $gameDir 'd3d9.dll'
if (!$ProbeOnly -and !(Test-Path -LiteralPath $exePath)) {
    throw "Original OR2006C2C.EXE not found: $exePath"
}
if (!$ProbeOnly) {
    if (Get-Process -Name OR2006C2C -ErrorAction SilentlyContinue) {
        throw 'Close OutRun 2006 before launching.'
    }
    if (Get-Process -Name outrun-vr-host -ErrorAction SilentlyContinue) {
        throw 'Close existing outrun-vr-host.exe before launching.'
    }
}
$hadWrapper = Test-Path -LiteralPath $wrapperPath
$savedWrapper = $null
$wrapperHash = $null
$logRoot = Join-Path $gameDir 'VR_NATIVE_QUALITY_LOGS'
$report = $null
$gameExit = -1
try {
    if ($hadWrapper) {
        Write-Host ''
        Write-Host 'HIGH-RES VR BLOCKER FOUND: a third-party d3d9.dll exists beside the game.'
        Write-Host "Path: $wrapperPath"
        Write-Host 'The attached run skipped D3D9Ex upgrade because of this file.'
        Write-Host 'This native test will move it to a backup folder ONLY while the game runs.'
        Write-Host 'The file will be restored, unchanged, when the game exits.'
        if (!$ApproveTemporaryWrapperIsolation) {
            $response = Read-Host 'Temporarily isolate d3d9.dll for this run? Type YES to proceed'
            if ($response -cne 'YES') { throw 'No files changed. Native VR test canceled.' }
        }
        $wrapperHash = (Get-FileHash -LiteralPath $wrapperPath -Algorithm SHA256).Hash
        $backupRoot = Join-Path $gameDir 'VR_NATIVE_D3D9_BACKUP'
        New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
        $saveName = (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + ([guid]::NewGuid().ToString('N')) + '-d3d9.dll'
        $savedWrapper = Join-Path $backupRoot $saveName
        Move-Item -LiteralPath $wrapperPath -Destination $savedWrapper -ErrorAction Stop
        if (Test-Path -LiteralPath $wrapperPath) { throw 'Wrapper is still in the game directory; refusing to start.' }
        Write-Host "Temporary wrapper backup: $savedWrapper"
    }
    if ($ProbeOnly) {
        Write-Host 'NATIVE D3D9 TEST: preflight move/recovery path PASS'
    } else {
        # Never overwrite the game DLL, x64 VR host, original executable or user INI.
        if (!(Test-Path -LiteralPath (Join-Path $gameDir 'dinput8.dll'))) { throw 'Missing VR dinput8.dll. Restore the last known-good test build first.' }
        if (!(Test-Path -LiteralPath (Join-Path $gameDir 'outrun-vr-host.exe'))) { throw 'Missing VR host. Restore the matching x64 host first.' }
        New-Item -ItemType Directory -Path $logRoot -Force | Out-Null
        $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
        $session = Join-Path $logRoot ("NATIVE_D3D9EX_" + $stamp)
        New-Item -ItemType Directory -Path $session -Force | Out-Null
        $report = Join-Path $session 'TRANSPORT_RESULT.txt'
        $gameArgs = @(
            '-FramerateLimit=0',
            '-FramerateFastLoad=0',
            '-FramerateInterpolation=true',
            '-FramerateUnlockExperimental=true',
            '-FrameCadenceMode=1',
            '-FrameCadenceTargetHz=0',
            '-DisableDesktopVsync=true',
            '-SkyGlowFactor=0',
            '-PreferD3D9Ex=true',
            '-DirectGpuOnly=true',
            '-DisableDesktopDuplication=false',
            '-RivalDx11NativeRoute=false',
            '-AutoRenderResolution=true',
            '-FollowGameResolution=false',
            '-UnifiedEyeMenuSource=false',
            '-AntiAliasing=2',
            '-Graphics.ReflectionResolution=256',
            '-Graphics.TransparencySupersampling=false',
            '-VR.TransparencySupersampling=false',
            '-VR.Telemetry=false',
            '-Hud1080pReference=true',
            '-HudResponsiveLayout=true',
            '-HudScale=0.55',
            '-MenuScale=1.00',
            '-CullingUnionFov=true',
            '-CullingUnionMarginDegrees=8.0'
        )
        Set-Content -LiteralPath (Join-Path $session 'GAME_ARGS.txt') -Value $gameArgs -Encoding UTF8
        $env:OUTRUN_VR_R23_PIXEL_PROBE = '0'
        Write-Host 'Launching with DirectGPU-only GAMEPLAY, 90 Hz runtime-owned pacing and OpenXR recommended per-eye resolution.'
        Write-Host 'Menu/Desktop Duplication remains enabled. Unsafe low-resolution SBS gameplay is intentionally rejected.'
        Write-Host 'If gameplay fails to render, exit the game; wrapper will be restored automatically.'
        $proc = Start-Process -FilePath $exePath -ArgumentList $gameArgs -WorkingDirectory $gameDir -PassThru
        $proc.WaitForExit()
        $gameExit = $proc.ExitCode
        Start-Sleep -Seconds 2
        Get-Process -Name outrun-vr-host -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

        $gameLog = Join-Path $gameDir 'OutRun2006Tweaks.log'
        $summary = @()
        $directCount = -1
        $sbsCount = -1
        $wrapperSkip = $false
        $probeD3D9Ex = $false
        $eyeExtent = 'UNKNOWN'
        if (Test-Path -LiteralPath $gameLog) {
            # A bounded tail avoids filling test reports with megabytes of verbose telemetry.
            $recent = @(Get-Content -LiteralPath $gameLog -Tail 20000)
            foreach ($line in $recent) {
                if ($line -match 'VR stereo:.*direct\[frames=(\d+),fallbacks=(\d+)') {
                    $directCount = [int]$matches[1]
                    $sbsCount = [int]$matches[2]
                }
                if ($line -match 'deviceType=.*D3D9Ex=1') { $probeD3D9Ex = $true }
                if ($line -match 'full-size eye surfaces ready (\d+x\d+)') { $eyeExtent = $matches[1] }
                if ($line -match 'third-party d3d9 provider detected') { $wrapperSkip = $true }
            }
            $recent | Where-Object {
                $_ -match 'D3D9Ex upgrade|VR D3D9 probe|full-size eye surfaces ready|TRUE STEREO PRESENT COMPLETE|VR stereo: draws=|XR startup'
            } | Select-Object -Last 80 | Set-Content (Join-Path $session 'GAME_RENDER_EVIDENCE.txt') -Encoding UTF8
        }
        @(
            'TEST=NATIVE_D3D9EX_STRICT_QUALITY'
            "finished=$(Get-Date -Format o)"
            "gameExitCode=$gameExit"
            "thirdPartyWrapperPresentAtStart=$hadWrapper"
            "gameLogReportedThirdPartySkip=$wrapperSkip"
            "gameLogD3D9ExProbe=$probeD3D9Ex"
            "directGpuFrames=$directCount"
            "desktopSbsFallbackFrames=$sbsCount"
            "gameEyeExtent=$eyeExtent"
            'expected=nonzero DirectGPU game frames and live XR-native target (not 1920x1080 SBS)'
            'status=UNVERIFIED_UNTIL_REAL_QUEST_TEST'
        ) | Set-Content -LiteralPath $report -Encoding UTF8
        $hostLog = Join-Path $gameDir 'outrun-vr-host-pipeline.log'
        if (Test-Path -LiteralPath $hostLog) {
            Get-Content -LiteralPath $hostLog -Tail 100 | Set-Content -LiteralPath (Join-Path $session 'HOST_PIPELINE_TAIL.txt') -Encoding UTF8
        }
        if ($directCount -le 0 -or !$probeD3D9Ex -or $wrapperSkip) {
            Write-Warning 'DirectGPU / D3D9Ex success was NOT confirmed. No performance or resolution recovery is claimed.'
            Write-Warning "Inspect $report and upload that folder."
        } else {
            Write-Host "DirectGPU frames=$directCount; D3D9Ex detected. Check HMD sharpness and GPU frametime."
        }
        Write-Host "Test evidence: $session"
    }
} finally {
    if ($savedWrapper -and (Test-Path -LiteralPath $savedWrapper)) {
        if (Test-Path -LiteralPath $wrapperPath) {
            Write-Warning "WARNING: another d3d9.dll appeared. Prior wrapper retained at $savedWrapper. Refusing to overwrite."
        } else {
            Move-Item -LiteralPath $savedWrapper -Destination $wrapperPath -ErrorAction Stop
            $restoredHash = (Get-FileHash -LiteralPath $wrapperPath -Algorithm SHA256).Hash
            if ($wrapperHash -ne $restoredHash) { throw 'CRITICAL: restored wrapper checksum mismatch.' }
            Write-Host "Original d3d9.dll restored and SHA256 verified: $wrapperPath"
        }
    }
}
