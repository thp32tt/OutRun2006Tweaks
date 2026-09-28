Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$toolsRoot = $PSScriptRoot
$targetPath = Join-Path $toolsRoot 'VR_ONE_CLICK_TARGET.json'
if (!(Test-Path $targetPath)) { throw "Missing one-click target metadata: $targetPath" }

$parseFiles = @(
    'Invoke-OutRunVROneClick.ps1',
    'Select-OutRunVRBackend.ps1',
    'Run-OutRunVRTest.ps1',
    'OutRunVR-Test-Selector.ps1',
    'Build-OutRunPCFast.ps1'
)

foreach ($name in $parseFiles) {
    $path = Join-Path $toolsRoot $name
    if (!(Test-Path $path)) { throw "Missing one-click dependency: $path" }

    $tokens = $null
    $errors = $null
    [void][System.Management.Automation.Language.Parser]::ParseFile(
        $path, [ref]$tokens, [ref]$errors)
    if ($errors -and $errors.Count -gt 0) {
        $detail = ($errors | ForEach-Object {
            "{0}:{1} {2}" -f $_.Extent.StartLineNumber,$_.Extent.StartColumnNumber,$_.Message
        }) -join '; '
        throw "PowerShell syntax error in $name :: $detail"
    }
}

$target = Get-Content $targetPath -Raw | ConvertFrom-Json
if (!$target.DevelopmentBranch) {
    throw 'VR_ONE_CLICK_TARGET.json has no DevelopmentBranch.'
}
$allowed = @('2d','d3d9','dx11','dxvk-safe','dxvk')
if ($allowed -notcontains [string]$target.LaunchBackend) {
    throw "Invalid LaunchBackend in VR_ONE_CLICK_TARGET.json: $($target.LaunchBackend)"
}

$startHere = Get-Content (Join-Path $toolsRoot 'START_HERE_VR_TEST.cmd') -Raw
if ($startHere -notmatch 'Invoke-OutRunVROneClick\.ps1') {
    throw 'START_HERE_VR_TEST.cmd does not route through the one-click launcher.'
}

$selectorCmd = Get-Content (Join-Path $toolsRoot 'Select-OutRunVRBackend.cmd') -Raw
$selectorUi = Get-Content (Join-Path $toolsRoot 'OutRunVR-Test-Selector.ps1') -Raw
if ($selectorCmd -match '(?i)dx12' -or $selectorUi -match '(?i)dx12') {
    throw 'Retired DX12 path is still exposed by a user-facing selector.'
}

$selector = Get-Content (Join-Path $toolsRoot 'Select-OutRunVRBackend.ps1') -Raw
$quotedBackend = [regex]::Escape('"' + [string]$target.LaunchBackend + '"')
if ($selector -notmatch $quotedBackend) {
    throw "Select-OutRunVRBackend.ps1 does not accept branch LaunchBackend=$($target.LaunchBackend)"
}

$package = Get-Content (Join-Path $toolsRoot 'Build-OutRunPCFast.ps1') -Raw
foreach ($required in @(
    'Invoke-OutRunVROneClick.ps1',
    'VR_ONE_CLICK_TARGET.json',
    'START_HERE_VR_TEST.cmd',
    'Collect-OutRunVRLogs.ps1'
)) {
    if ($package -notmatch [regex]::Escape($required)) {
        throw "PC FAST package does not include one-click dependency: $required"
    }
}

$collector = Get-Content (Join-Path $toolsRoot 'Collect-OutRunVRLogs.ps1') -Raw
foreach ($requiredText in @(
    'VR_ONE_CLICK_TARGET.json',
    'IntegrationBranch=$developmentBranch',
    'RendererTarget=$rendererTarget',
    "dxvk-safe' -or $backend -eq 'dx11"
)) {
    if ($collector -notmatch [regex]::Escape($requiredText)) {
        throw "Collector is not branch-aware for one-click runs: $requiredText"
    }
}

switch ([string]$target.RendererTarget) {
    'dx11-native' {
        if ([string]$target.DevelopmentBranch -ne 'vr-dx11-native-r71') {
            throw "DX11 one-click DevelopmentBranch mismatch: $($target.DevelopmentBranch)"
        }
        if ([string]$target.LaunchBackend -ne 'dx11') {
            throw 'DX11-native development branch must currently launch the isolated dx11-host DirectGPU validation mode.'
        }
        if ([bool]$target.NativeDrawPathActive) {
            throw 'NativeDrawPathActive must remain false until the native D3D11 draw owner is actually connected.'
        }
        foreach ($requiredText in @(
            'OUTRUN_VR_DX11_CENSUS',
            "RendererTarget -eq 'dx11-native'"
        )) {
            $launcher = Get-Content (Join-Path $toolsRoot 'Invoke-OutRunVROneClick.ps1') -Raw
            if ($launcher -notmatch [regex]::Escape($requiredText)) {
                throw "DX11 one-click census activation missing: $requiredText"
            }
        }
        foreach ($path in @(
            'src/vr/d3d11/native_backend.cpp',
            'src/vr/d3d11/native_backend.hpp',
            'src/vr/d3d11/state_translation.cpp',
            'src/vr/d3d11/startup_census.cpp',
            'src/vr/d3d11/pipeline_translation.cpp',
            'src/vr/d3d11/runtime_census.cpp',
            'src/vr/core/d3d9_draw_state.hpp',
            'src/vr/game/disasm_render_contract.hpp'
        )) {
            if (!(Test-Path (Join-Path $repoRoot $path))) {
                throw "DX11 branch contract file missing: $path"
            }
        }
    }

    'dxvk' {
        if ([string]$target.DevelopmentBranch -ne 'vr-dxvk-r71-disasm') {
            throw "DXVK one-click DevelopmentBranch mismatch: $($target.DevelopmentBranch)"
        }
        if ([string]$target.LaunchBackend -ne 'dxvk-safe') {
            throw 'DXVK R71 must stay on dxvk-safe until stock two-pass visual parity passes.'
        }
        if ([string]$target.DxvkVersion -ne '3.1.1') {
            throw "Unexpected pinned DXVK version: $($target.DxvkVersion)"
        }
        foreach ($required in @(
            'Acquire-OutRunDXVK.ps1',
            "dxvkVersion = '3.1.1'",
            "backends/dxvk",
            'DXVK_D3D9_SHA256.txt'
        )) {
            if ($package -notmatch [regex]::Escape($required)) {
                throw "DXVK one-click packaging contract missing: $required"
            }
        }
        if (!(Test-Path (Join-Path $toolsRoot 'Acquire-OutRunDXVK.ps1'))) {
            throw 'DXVK acquisition helper is missing.'
        }
        if (!(Test-Path (Join-Path $repoRoot 'src/vr/d3d9/dxvk_provider_probe.cpp'))) {
            throw 'DXVK passive provider probe is missing.'
        }
        $deviceProbe = Get-Content (Join-Path $repoRoot 'src/vr/d3d9/device_probe.cpp') -Raw
        if ($deviceProbe -notmatch [regex]::Escape('OutRunVR::Dxvk::ProbeProvider(device)')) {
            throw 'DXVK provider census is not connected to the game-device lifecycle.'
        }
    }

    default {
        throw "Unsupported RendererTarget in one-click contract: $($target.RendererTarget)"
    }
}

Write-Host ("One-click VR contract PASS: renderer={0} launchBackend={1} stage={2}" -f
    $target.RendererTarget,$target.LaunchBackend,$target.Stage)