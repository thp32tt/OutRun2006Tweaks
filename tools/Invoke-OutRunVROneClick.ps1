param(
    [ValidateSet('auto','2d','d3d9','dx11','dxvk-safe','dxvk')]
    [string]$Backend = 'auto',
    [ValidateSet('CONTROL','CORRECTNESS','HUD_SCREEN','HUD_MENU','HUD_WORLD','PERFORMANCE','STAGE_DIAGNOSTIC','A_BASELINE','B_CULLING','C_CULLING_NO_SSAA','D_CULLING_NO_SSAA_R512')]
    [string]$TestProfile = 'CORRECTNESS',
    [string]$VariantId = 'AUTO',
    [switch]$AllowTargetOverride
)

$ErrorActionPreference = 'Stop'
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$selector = Join-Path $scriptRoot 'Select-OutRunVRBackend.ps1'
$runner = Join-Path $scriptRoot 'Run-OutRunVRTest.ps1'
$targetFile = Join-Path $scriptRoot 'VR_ONE_CLICK_TARGET.json'
$visualChecklist = Join-Path $scriptRoot 'ONE_RUN_VISUAL_CHECKLIST.txt'
$preflight = Join-Path $scriptRoot 'Test-OutRunVROneClickPreflight.ps1'
$runtimeIni = Join-Path $scriptRoot 'OutRun2006Tweaks.ini'
$packagedBaselineIni = Join-Path $scriptRoot 'package-baseline/OutRun2006Tweaks.ini'

function Restore-PackagedBaselineIni {
    if (Test-Path $packagedBaselineIni -PathType Leaf) {
        Copy-Item $packagedBaselineIni $runtimeIni -Force
    }
}

if (!(Test-Path $selector)) { throw "Select-OutRunVRBackend.ps1 not found: $selector" }
if (!(Test-Path $runner)) { throw "Run-OutRunVRTest.ps1 not found: $runner" }
if (!(Test-Path $preflight)) { throw "Test-OutRunVROneClickPreflight.ps1 not found: $preflight" }

function Write-OneClickPreflightFailureDiagnostic(
    [string]$ErrorText,
    [string]$RequestedBackend,
    [string]$RequestedVariant
) {
    $stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssfffZ')
    $record = [ordered]@{
        SchemaVersion = 1
        RecordedUtc = (Get-Date).ToUniversalTime().ToString('o')
        Phase = 'PREFLIGHT'
        RequestedBackend = $RequestedBackend
        RequestedVariant = $RequestedVariant
        Error = $ErrorText
        SessionCreated = $false
    }

    try {
        $dest = Join-Path $scriptRoot ("logs/_preflight_failures/{0}" -f $stamp)
        New-Item -ItemType Directory -Force $dest | Out-Null
        $path = Join-Path $dest 'PREFLIGHT_FAILURE.json'
        $record | ConvertTo-Json -Depth 6 | Set-Content $path -Encoding UTF8
        return $path
    } catch {
        try {
            $path = Join-Path $scriptRoot ("VR_PREFLIGHT_FAILURE_{0}.json" -f $stamp)
            $record | ConvertTo-Json -Depth 6 | Set-Content $path -Encoding UTF8
            return $path
        } catch {
            return 'diagnostic-write-failed'
        }
    }
}

$target = $null
if (Test-Path $targetFile) {
    try {
        $target = Get-Content $targetFile -Raw | ConvertFrom-Json
    } catch {
        throw "Invalid VR_ONE_CLICK_TARGET.json: $($_.Exception.Message)"
    }
}

$resolvedBackend = $Backend
$resolvedVariant = $VariantId
if ($resolvedBackend -eq 'auto') {
    if (!$target -or !$target.LaunchBackend) {
        throw 'Auto backend requested but VR_ONE_CLICK_TARGET.json has no LaunchBackend.'
    }
    $resolvedBackend = [string]$target.LaunchBackend
}
if ($resolvedVariant -eq 'AUTO' -and $target -and $target.VariantId) {
    $resolvedVariant = [string]$target.VariantId
}

if ($target -and -not $AllowTargetOverride) {
    if ($resolvedBackend -ne [string]$target.LaunchBackend) {
        throw "One-click backend override blocked: requested=$resolvedBackend target=$($target.LaunchBackend). Use -AllowTargetOverride only for explicit developer diagnostics."
    }
    if ($resolvedVariant -ne [string]$target.VariantId) {
        throw "One-click variant override blocked: requested=$resolvedVariant target=$($target.VariantId). Use -AllowTargetOverride only for explicit developer diagnostics."
    }
}

$validBackends = @('2d','d3d9','dx11','dxvk-safe','dxvk')
if ($validBackends -notcontains $resolvedBackend) {
    throw "Unsupported one-click backend: $resolvedBackend"
}

Write-Host '============================================================'
Write-Host ' OutRun 2006 VR One-Click'
Write-Host '============================================================'
if ($target) {
    Write-Host ("Target renderer : {0}" -f $target.RendererTarget)
    Write-Host ("Development stage: {0}" -f $target.Stage)
    Write-Host ("Native draw path : {0}" -f $target.NativeDrawPathActive)
}
Write-Host ("Launch backend  : {0}" -f $resolvedBackend)
Write-Host ("Test profile    : {0}" -f $TestProfile)
Write-Host ("Variant         : {0}" -f $resolvedVariant)
if (Test-Path $visualChecklist) {
    Write-Host ("One-run QA       : {0}" -f $visualChecklist)
}
Write-Host ''

# The backend selector intentionally mutates the root INI for each run.
# Restore the immutable packaged copy before package-integrity verification so
# DXVK -> D3D9 -> DX11 (or any other order) can be tested repeatedly.
Restore-PackagedBaselineIni

# Fail before mutating the game directory when the packaged renderer/host/provider
# identity does not match this branch target. The report is collected into the
# same session ZIP for exact reproduction.
try {
    # PowerShell child scripts that return normally do not guarantee that the
    # automatic $LASTEXITCODE variable has ever been created. Under StrictMode
    # reading an undefined automatic variable throws even after a PASS.
    $LASTEXITCODE = 0
    & $preflight -Backend $resolvedBackend
    $preflightExitCode = [int]$LASTEXITCODE
    if ($preflightExitCode -ne 0) {
        throw "One-click preflight failed with exit code $preflightExitCode"
    }
} catch {
    $preflightFailure = $_.Exception
    $diagnostic = Write-OneClickPreflightFailureDiagnostic -ErrorText $preflightFailure.Message -RequestedBackend $resolvedBackend -RequestedVariant $resolvedVariant
    throw ("One-click preflight failed before session creation. Diagnostic={0}; error={1}" -f $diagnostic,$preflightFailure.Message)
}


# One-click owns the complete preparation -> game -> host lifecycle. The game
# DLL starts outrun-vr-host.exe via AutoLaunchHost; this launcher never starts a
# second host process.
$oldDx11Census = $env:OUTRUN_VR_DX11_CENSUS
if ($target -and [string]$target.RendererTarget -eq 'dx11-native') {
    # R72 is observation-only. Source draw/state census is enabled
    # automatically, but NativeDrawPathActive remains false and no draw is
    # redirected to D3D11.
    $env:OUTRUN_VR_DX11_CENSUS = '1'
} else {
    $env:OUTRUN_VR_DX11_CENSUS = $null
}

$oneClickExitCode = 0
try {
    $LASTEXITCODE = 0
    & $selector -Backend $resolvedBackend -TestProfile $TestProfile -VariantId $resolvedVariant
    $selectorExitCode = [int]$LASTEXITCODE
    if ($selectorExitCode -ne 0) {
        throw "Backend preparation failed with exit code $selectorExitCode"
    }

    $LASTEXITCODE = 0
    & $runner -TestProfile $TestProfile
    $runnerExitCode = [int]$LASTEXITCODE
    if ($runnerExitCode -ne 0) {
        $oneClickExitCode = $runnerExitCode
    }
} finally {
    $env:OUTRUN_VR_DX11_CENSUS = $oldDx11Census
    # Run-OutRunVRTest seals the logs/analysis ZIP before returning.
    # Leave the extracted package pristine for the next selector choice.
    Restore-PackagedBaselineIni
}

exit $oneClickExitCode