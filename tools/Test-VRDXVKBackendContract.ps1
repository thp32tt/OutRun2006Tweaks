$ErrorActionPreference = "Stop"

$selectorSource = Join-Path $PSScriptRoot "Select-OutRunVRBackend.ps1"
if (-not (Test-Path $selectorSource)) { throw "Selector source missing: $selectorSource" }

function Write-TestPe([string]$Path,[UInt16]$Machine) {
    $bytes = New-Object byte[] 512
    $bytes[0] = 0x4D
    $bytes[1] = 0x5A
    [BitConverter]::GetBytes([Int32]0x80).CopyTo($bytes,0x3C)
    $bytes[0x80] = 0x50
    $bytes[0x81] = 0x45
    $bytes[0x82] = 0
    $bytes[0x83] = 0
    [BitConverter]::GetBytes($Machine).CopyTo($bytes,0x84)
    [IO.File]::WriteAllBytes($Path,$bytes)
}

$sandbox = Join-Path $env:RUNNER_TEMP ("outrun-dxvk-selector-" + [guid]::NewGuid().ToString("N"))
try {
    New-Item -ItemType Directory -Force $sandbox | Out-Null
    Copy-Item $selectorSource (Join-Path $sandbox "Select-OutRunVRBackend.ps1")

    $d3d9 = Join-Path $sandbox "backends/d3d9"
    $dxvk = Join-Path $sandbox "backends/dxvk"
    New-Item -ItemType Directory -Force $d3d9,$dxvk | Out-Null

    foreach ($dir in @($d3d9,$dxvk)) {
        Write-TestPe (Join-Path $dir "dinput8.dll") 0x014C
        Set-Content (Join-Path $dir "outrun-vr-host.exe") "synthetic-host" -Encoding ascii
        Set-Content (Join-Path $dir "SOURCE_SHA.txt") "synthetic-source" -Encoding ascii
    }

    $dxvkDll = Join-Path $dxvk "d3d9.dll"
    $patcher = Join-Path $dxvk "multiviewpatcher.dll"
    Write-TestPe $dxvkDll 0x014C
    Write-TestPe $patcher 0x014C

    @"
[VR]
Enabled = true
AutoLaunchHost = true
AutoEnableWhenHostPresent = true
RenderBackend = 1
PreferD3D9Ex = true
DirectGpuOnly = false
DisableDesktopDuplication = false
DriverSeatView = false
[Graphics]
TransparencySupersampling = true
"@ | Set-Content (Join-Path $sandbox "OutRun2006Tweaks.ini") -Encoding ascii

    $selector = Join-Path $sandbox "Select-OutRunVRBackend.ps1"

    & $selector -Backend dxvk-safe -TestProfile CORRECTNESS -VariantId E_DXVK_SAFE
    $safeHash = (Get-FileHash $dxvkDll -Algorithm SHA256).Hash.ToLowerInvariant()
    $active = Get-Content (Join-Path $sandbox "ACTIVE_VR_BACKEND.txt")
    if ($active -notcontains "backend=dxvk-safe") { throw "DXVK SAFE backend identity missing" }
    if ($active -notcontains "provider=DXVK_X86_SAFE") { throw "DXVK SAFE provider identity missing" }
    if ($active -notcontains "dxvkD3D9Sha256=$safeHash") { throw "DXVK SAFE SHA256 identity missing" }
    $gameDllHash = (Get-FileHash (Join-Path $sandbox "dinput8.dll") -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($active -notcontains "gameDllSha256=$gameDllHash") { throw "Selected game DLL SHA256 attestation missing" }
    if (Test-Path (Join-Path $sandbox "multiviewpatcher.dll")) { throw "DXVK SAFE must not install multiviewpatcher.dll" }

    $manifest = Get-Content (Join-Path $sandbox "CURRENT_VR_SESSION.json") -Raw | ConvertFrom-Json
    if ($manifest.SchemaVersion -ne 4) { throw "DXVK session manifest schema was not advanced" }
    if ($manifest.BackendProvider -ne "DXVK_X86_SAFE") { throw "DXVK SAFE manifest provider mismatch" }
    if ($manifest.DxvkD3D9Sha256 -ne $safeHash) { throw "DXVK SAFE manifest hash mismatch" }

    & $selector -Backend dxvk -TestProfile PERFORMANCE -VariantId E_DXVK_MULTIVIEW
    $patcherHash = (Get-FileHash $patcher -Algorithm SHA256).Hash.ToLowerInvariant()
    $active = Get-Content (Join-Path $sandbox "ACTIVE_VR_BACKEND.txt")
    if ($active -notcontains "provider=DXVK_X86_MULTIVIEW") { throw "DXVK multiview provider identity missing" }
    if ($active -notcontains "multiviewPatcherSha256=$patcherHash") { throw "DXVK multiview patcher hash missing" }

    # Wrong-architecture provider must be rejected before it can replace the game-root d3d9.dll.
    $rootHashBefore = (Get-FileHash (Join-Path $sandbox "d3d9.dll") -Algorithm SHA256).Hash
    Write-TestPe $dxvkDll 0x8664
    $failed = $false
    try {
        & $selector -Backend dxvk-safe -TestProfile CORRECTNESS -VariantId E_DXVK_SAFE
    } catch {
        $failed = $true
        if ($_.Exception.Message -notmatch "must be x86 PE32") { throw }
    }
    if (-not $failed) { throw "x64 DXVK provider was not rejected" }
    $rootHashAfter = (Get-FileHash (Join-Path $sandbox "d3d9.dll") -Algorithm SHA256).Hash
    if ($rootHashAfter -ne $rootHashBefore) { throw "Rejected provider changed installed d3d9.dll" }

    Write-Host "VR DXVK backend identity contract: PASS"
} finally {
    Remove-Item $sandbox -Recurse -Force -ErrorAction SilentlyContinue
}
