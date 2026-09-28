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
    'START_HERE_VR_TEST.cmd'
)) {
    if ($package -notmatch [regex]::Escape($required)) {
        throw "PC FAST package does not include one-click dependency: $required"
    }
}

switch ([string]$target.RendererTarget) {
    'dx11-native' {
        if ([string]$target.LaunchBackend -ne 'dx11') {
            throw 'DX11-native development branch must currently launch the isolated dx11-host DirectGPU validation mode.'
        }
        if ([bool]$target.NativeDrawPathActive) {
            throw 'NativeDrawPathActive must remain false until the native D3D11 draw owner is actually connected.'
        }
        foreach ($path in @(
            'src/vr/d3d11/native_backend.cpp',
            'src/vr/d3d11/native_backend.hpp',
            'src/vr/d3d11/state_translation.cpp',
            'src/vr/game/disasm_render_contract.hpp'
        )) {
            if (!(Test-Path (Join-Path $repoRoot $path))) {
                throw "DX11 branch contract file missing: $path"
            }
        }
    }

    'dxvk' {
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
    }

    default {
        throw "Unsupported RendererTarget in one-click contract: $($target.RendererTarget)"
    }
}

Write-Host ("One-click VR contract PASS: renderer={0} launchBackend={1} stage={2}" -f
    $target.RendererTarget,$target.LaunchBackend,$target.Stage)
