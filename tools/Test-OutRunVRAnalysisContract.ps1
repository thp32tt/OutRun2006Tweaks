# Bounded semantic analyzer fixture. One independent test for each real user
# regression; never repeat an unchanged 1000/5000-cycle HUD static audit.
$ErrorActionPreference = 'Stop'
$analyzer = Join-Path $PSScriptRoot 'Analyze-OutRunVRSession.ps1'
$testRoot = Join-Path ([System.IO.Path]::GetTempPath()) ('OutRunVR-Analyze-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $testRoot -Force | Out-Null

function Invoke-Fixture {
    param(
        [string]$Name,
        [int]$Projected,
        [string]$DllMatched,
        [string]$ExpectedStatus
    )
    $dir = Join-Path $testRoot $Name
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
    '{"VariantId":"CURRENT_FOCUS","Backend":"d3d9","TestProfile":"CORRECTNESS","SourceSha":"fixture-source"}' |
        Set-Content (Join-Path $dir 'session_manifest.json') -Encoding UTF8
    'RankMarker/sub_4BAD20 count=9' |
        Set-Content (Join-Path $dir 'HUD_TRACE_SUMMARY.txt') -Encoding UTF8
    @(
        'VR R51 HUD OWNER: projected[semantic=' + $Projected +
            ',missingPayload=0,buildAttempts=3,buildOk=3,buildFail=0]'
        'VR R51: direct[frames=3,fallbacks=0,fenceTimeout=0]'
    ) | Set-Content (Join-Path $dir 'OutRun2006Tweaks.log') -Encoding UTF8
    "installedMatchesSelected=$DllMatched" |
        Set-Content (Join-Path $dir 'GAME_DLL_IDENTITY.txt') -Encoding UTF8

    if ($Name -eq 'r28-present-over-budget') {
        'VR R28 PERF: lower-Present avgMs=6.124 maxMs=28.557 drawsPerPresent=1164.8' |
            Add-Content (Join-Path $dir 'OutRun2006Tweaks.log') -Encoding UTF8
        '[R23 pipeline] actualXrHz=90 xrFrameIntervalMs=12.368' |
            Set-Content (Join-Path $dir 'outrun-vr-host-pipeline.log') -Encoding UTF8
        'GameDefaultConfigOverride: default resolution set to 3440x1440, windowed enabled' |
            Add-Content (Join-Path $dir 'OutRun2006Tweaks.log') -Encoding UTF8
    }
    & $analyzer -SessionDir $dir
    $outputPath = Join-Path $dir 'AUTO_ANALYSIS_SUMMARY.json'
    if (-not (Test-Path $outputPath)) {
        throw "No analysis result created for $Name"
    }
    $result = Get-Content $outputPath -Raw | ConvertFrom-Json
    if ($result.Status -ne $ExpectedStatus) {
        throw "$Name incorrect status $($result.Status); expected $ExpectedStatus"
    }
    if (-not $result.RankProducerObserved -or
        $result.ProjectedMarkerSemanticCount -ne $Projected) {
        throw "$Name lost exact rank producer/projection counters"
    }
    if ($result.GameDllIdentityMismatch -ne ($DllMatched -eq 'False')) {
        throw "$Name lost installed DLL match evidence"
    }
    if ($ExpectedStatus -ne 'OK' -and
        $result.Flags -contains 'NO_AUTOMATIC_RED_FLAG') {
        throw "$Name gave a false no-red-flag verdict"
    }
    if ($Name -eq 'r28-present-over-budget' -and
        ($result.R28PresentOverBudgetWindows -ne 1 -or
         $result.R28PresentMaxMs -ne 28.557 -or
         $result.GameDefaultWidth -ne 3440 -or
         $result.XrRefreshBudgetMs -lt 11.1 -or
         $result.XrRefreshBudgetMs -gt 11.12 -or
         $result.Flags -notcontains 'D3D9EX_PRESENT_LATENCY_OVER_XR_BUDGET')) {
        throw "$Name failed real R28/per-eye budget regression"
    }
    Write-Host "PASS $Name : $($result.Status)"
}

try {
    Invoke-Fixture 'real-user-rank-projected-zero' 0 'True' 'HUD_RANK_PROJECTED_PATH_ZERO'
    Invoke-Fixture 'stale-installed-dll' 5 'False' 'GAME_DLL_SHA256_MISMATCH'
    Invoke-Fixture 'healthy-telemetry-only' 5 'True' 'OK'
    Invoke-Fixture 'r28-present-over-budget' 5 'True' 'PERFORMANCE_WARNING'
} finally {
    Remove-Item $testRoot -Recurse -Force -ErrorAction SilentlyContinue
}
