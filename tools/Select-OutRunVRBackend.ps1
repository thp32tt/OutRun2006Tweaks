param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("d3d9","dxvk","dx12")]
    [string]$Backend
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendRoot = Join-Path $root "backends"
$src = Join-Path $backendRoot $Backend
if (-not (Test-Path $src)) { throw "Backend payload not found: $src" }

function Copy-Required([string]$name) {
    $p = Join-Path $src $name
    if (-not (Test-Path $p)) { throw "Required backend file missing: $p" }
    Copy-Item $p (Join-Path $root $name) -Force
}
function Remove-Root([string]$name) {
    $p = Join-Path $root $name
    if (Test-Path $p) { Remove-Item $p -Force }
}

Copy-Required "dinput8.dll"
Copy-Required "outrun-vr-host.exe"

if ($Backend -eq "dxvk") {
    Copy-Required "d3d9.dll"
    Copy-Required "multiviewpatcher.dll"
} else {
    Remove-Root "d3d9.dll"
    Remove-Root "multiviewpatcher.dll"
}

$ini = Join-Path $root "OutRun2006Tweaks.ini"
if (Test-Path $ini) {
    $value = switch ($Backend) {
        "d3d9" { "1" }
        "dxvk" { "2" }
        "dx12" { "3" }
    }
    $text = Get-Content $ini -Raw
    if ($text -match '(?m)^RenderBackend\s*=') {
        $text = [regex]::Replace($text, '(?m)^RenderBackend\s*=.*$', "RenderBackend = $value")
    } elseif ($text -match '(?m)^\[VR\]\s*$') {
        $text = [regex]::Replace($text, '(?m)^\[VR\]\s*$', "[VR]`r`nRenderBackend = $value", 1)
    }
    Set-Content $ini $text -Encoding UTF8
}

Set-Content (Join-Path $root "ACTIVE_VR_BACKEND.txt") ("backend=" + $Backend + "`r`nselected=" + (Get-Date -Format o)) -Encoding ascii
Write-Host "OutRun VR backend activated: $Backend"
if ($Backend -eq "dx12") {
    Write-Host "DX12 strict mode: local d3d9.dll removed; D3D9On12 must be provided by Windows."
} elseif ($Backend -eq "dxvk") {
    Write-Host "DXVK mode: local d3d9.dll + multiviewpatcher.dll activated."
} else {
    Write-Host "D3D9 safe mode: local d3d9.dll removed."
}
