param(
    [ValidateSet('auto','2d','d3d9','dx11','dxvk-safe','dxvk')]
    [string]$Backend = 'auto',
    [ValidateSet('CONTROL','CORRECTNESS','HUD_SCREEN','HUD_MENU','HUD_WORLD','PERFORMANCE','STAGE_DIAGNOSTIC','A_BASELINE','B_CULLING','C_CULLING_NO_SSAA','D_CULLING_NO_SSAA_R512')]
    [string]$TestProfile = 'CORRECTNESS',
    [string]$VariantId = 'AUTO'
)

$ErrorActionPreference = 'Stop'
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$selector = Join-Path $scriptRoot 'Select-OutRunVRBackend.ps1'
$runner = Join-Path $scriptRoot 'Run-OutRunVRTest.ps1'
$targetFile = Join-Path $scriptRoot 'VR_ONE_CLICK_TARGET.json'

if (!(Test-Path $selector)) { throw "Select-OutRunVRBackend.ps1 not found: $selector" }
if (!(Test-Path $runner)) { throw "Run-OutRunVRTest.ps1 not found: $runner" }

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
Write-Host ''

# One-click owns the complete preparation -> game -> host lifecycle. The game
# DLL starts outrun-vr-host.exe via AutoLaunchHost; this launcher never starts a
# second host process.
& $selector -Backend $resolvedBackend -TestProfile $TestProfile -VariantId $resolvedVariant
if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) {
    throw "Backend preparation failed with exit code $LASTEXITCODE"
}

& $runner -TestProfile $TestProfile
if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

exit 0
