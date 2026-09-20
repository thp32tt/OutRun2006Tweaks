param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("2d","d3d9","dxvk-safe","dxvk","dx12")]
    [string]$Backend
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendRoot = Join-Path $root "backends"
$payloadBackend = if ($Backend -eq "2d" -or $Backend -eq "dxvk-safe") { "d3d9" } else { $Backend }
$src = Join-Path $backendRoot $payloadBackend
if (-not (Test-Path $src)) { throw "Backend payload not found: $src" }

function Copy-Required([string]$name) {
    $p = Join-Path $src $name
    if (-not (Test-Path $p)) { throw "Required backend file missing: $p" }
    Copy-Item $p (Join-Path $root $name) -Force
}

function Remove-RootVerified([string]$name) {
    $p = Join-Path $root $name
    if (Test-Path $p) {
        Remove-Item $p -Force
        if (Test-Path $p) { throw "Could not remove $name. Close OutRun/VR host and retry." }
    }
}

function Repair-IniSectionHeaders([string]$text) {
    $text = $text -replace '(?m)^\[VR\]\\\s*$', '[VR]'
    $text = $text -replace '(?m)^\\\s*$\r?\n?', ''
    return $text
}

function Set-IniSectionValue([string]$text,[string]$section,[string]$key,[string]$value) {
    $escapedSection = [regex]::Escape($section)
    $escapedKey = [regex]::Escape($key)
    $sectionPattern = "(?ms)(^\[$escapedSection\]\s*\r?\n)(.*?)(?=^\[|\z)"
    $m = [regex]::Match($text,$sectionPattern)
    $nl = [Environment]::NewLine
    if (-not $m.Success) {
        if ($text.Length -gt 0 -and -not $text.EndsWith($nl)) { $text += $nl }
        return $text + "[$section]" + $nl + "$key = $value" + $nl
    }

    $body = $m.Groups[2].Value
    $keyPattern = "(?m)^$escapedKey\s*=.*$"
    if ([regex]::IsMatch($body,$keyPattern)) {
        $body = [regex]::Replace($body,$keyPattern,"$key = $value",1)
    } else {
        $body = "$key = $value" + $nl + $body
    }
    return $text.Substring(0,$m.Groups[2].Index) + $body +
        $text.Substring($m.Groups[2].Index + $m.Groups[2].Length)
}

$running = Get-Process -ErrorAction SilentlyContinue | Where-Object {
    $_.ProcessName -ieq "OR2006C2C" -or $_.ProcessName -ieq "outrun-vr-host"
}
if ($running) { throw "OutRun or outrun-vr-host.exe is still running. Close it before switching." }

Copy-Required "dinput8.dll"

if ($Backend -eq "2d") {
    Remove-RootVerified "d3d9.dll"
    Remove-RootVerified "multiviewpatcher.dll"
    Remove-RootVerified "outrun-vr-host.exe"
} else {
    Copy-Required "outrun-vr-host.exe"
    if ($Backend -eq "dxvk") {
        Copy-Required "d3d9.dll"
        Copy-Required "multiviewpatcher.dll"
    } elseif ($Backend -eq "dxvk-safe") {
        $dxvkProvider = Join-Path (Join-Path $backendRoot "dxvk") "d3d9.dll"
        if (-not (Test-Path $dxvkProvider)) { throw "DXVK provider missing: $dxvkProvider" }
        Copy-Item $dxvkProvider (Join-Path $root "d3d9.dll") -Force
        Remove-RootVerified "multiviewpatcher.dll"
    } else {
        Remove-RootVerified "d3d9.dll"
        Remove-RootVerified "multiviewpatcher.dll"
        if (Test-Path (Join-Path $root "d3d9.dll")) {
            throw "Local d3d9.dll is still present; refusing $Backend mode."
        }
    }
}

$ini = Join-Path $root "OutRun2006Tweaks.ini"
if (Test-Path $ini) {
    $text = Get-Content $ini -Raw
    $text = Repair-IniSectionHeaders $text

    if ($Backend -eq "2d") {
        $text = Set-IniSectionValue $text "VR" "RenderBackend" "1"
        $text = Set-IniSectionValue $text "VR" "Enabled" "false"
        $text = Set-IniSectionValue $text "VR" "AutoLaunchHost" "false"
        $text = Set-IniSectionValue $text "VR" "AutoEnableWhenHostPresent" "false"
        $text = Set-IniSectionValue $text "VR" "PreferD3D9Ex" "false"
        $text = Set-IniSectionValue $text "VR" "DirectGpuOnly" "false"
        $text = Set-IniSectionValue $text "VR" "DisableDesktopDuplication" "false"
    } elseif ($Backend -eq "dxvk-safe") {
        $text = Set-IniSectionValue $text "VR" "RenderBackend" "1"
        $text = Set-IniSectionValue $text "VR" "Enabled" "true"
        $text = Set-IniSectionValue $text "VR" "AutoLaunchHost" "true"
        $text = Set-IniSectionValue $text "VR" "AutoEnableWhenHostPresent" "true"
        $text = Set-IniSectionValue $text "VR" "PreferD3D9Ex" "false"
        $text = Set-IniSectionValue $text "VR" "DirectGpuOnly" "false"
        $text = Set-IniSectionValue $text "VR" "DisableDesktopDuplication" "false"
    } else {
        $value = switch ($Backend) {
            "d3d9" { "1" }
            "dxvk" { "2" }
            "dx12" { "3" }
        }
        $text = Set-IniSectionValue $text "VR" "RenderBackend" $value
        $text = Set-IniSectionValue $text "VR" "Enabled" "true"
        $text = Set-IniSectionValue $text "VR" "AutoLaunchHost" "true"
        $text = Set-IniSectionValue $text "VR" "AutoEnableWhenHostPresent" "true"
        $text = Set-IniSectionValue $text "VR" "PreferD3D9Ex" "true"
        $text = Set-IniSectionValue $text "VR" "DirectGpuOnly" "true"
    }
    Set-Content $ini $text -Encoding UTF8
}

$nl = [Environment]::NewLine
Set-Content (Join-Path $root "ACTIVE_VR_BACKEND.txt") ("backend=" + $Backend + $nl + "selected=" + (Get-Date -Format o)) -Encoding ascii

Write-Host "OutRun renderer mode activated: $Backend"
switch ($Backend) {
    "2d"   { Write-Host "2D ORIGINAL: classic D3D9, VR disabled, D3D9Ex promotion disabled, no VR host." }
    "d3d9" { Write-Host "D3D9 VR SAFE: guarded D3D9Ex/DirectGPU VR path." }
    "dxvk-safe" { Write-Host "DXVK SAFE: classic D3D9 calls translated by DXVK; validated two-pass VR, multiview patcher disabled." }
    "dxvk" { Write-Host "DXVK MULTIVIEW: local d3d9.dll + multiviewpatcher.dll active." }
    "dx12" { Write-Host "DX12 STRICT: local d3d9.dll verified absent; Windows D3D9On12 required." }
}
