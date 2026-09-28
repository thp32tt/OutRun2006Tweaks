param(
    [string]$ManifestPath = "",
    [Parameter(Mandatory = $true)]
    [string]$OutputDirectory
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$toolsRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $toolsRoot
if ([string]::IsNullOrWhiteSpace($ManifestPath)) {
    $ManifestPath = Join-Path $repoRoot "docs/VR_DXVK_PROVIDER.json"
}
if (-not (Test-Path $ManifestPath)) { throw "DXVK provider manifest missing: $ManifestPath" }

$manifest = Get-Content $ManifestPath -Raw | ConvertFrom-Json
if ($manifest.schemaVersion -ne 1) { throw "Unsupported DXVK provider manifest schema: $($manifest.schemaVersion)" }
if ($manifest.provider -ne "DXVK") { throw "Unexpected provider: $($manifest.provider)" }
if ($manifest.sourceRepository -ne "doitsujin/dxvk") { throw "Unexpected DXVK source repository: $($manifest.sourceRepository)" }
if ($manifest.assetSha256 -notmatch '^[0-9a-fA-F]{64}$') { throw "Invalid DXVK asset SHA256" }
if ($manifest.backendMode -ne "dxvk-safe") { throw "Provider manifest must target dxvk-safe" }
if ($manifest.policy.preferD3D9Ex -ne $false) { throw "DXVK SAFE must keep PreferD3D9Ex=false" }
if ($manifest.policy.directGpuOnly -ne $false) { throw "DXVK SAFE must keep DirectGpuOnly=false" }
if ($manifest.policy.disableDesktopDuplication -ne $false) { throw "DXVK SAFE must keep Desktop Duplication fallback available" }
if ($manifest.policy.multiviewPatcherIncluded -ne $false) { throw "DXVK SAFE must not include the multiview patcher" }

function Get-PeMachine([string]$Path) {
    $bytes = [IO.File]::ReadAllBytes($Path)
    if ($bytes.Length -lt 256) { throw "PE file is too small: $Path" }
    if ($bytes[0] -ne 0x4D -or $bytes[1] -ne 0x5A) { throw "Missing MZ header: $Path" }
    $peOffset = [BitConverter]::ToInt32($bytes, 0x3C)
    if ($peOffset -lt 0 -or $peOffset + 6 -gt $bytes.Length) { throw "Invalid PE header offset: $Path" }
    if ($bytes[$peOffset] -ne 0x50 -or $bytes[$peOffset + 1] -ne 0x45 -or
        $bytes[$peOffset + 2] -ne 0 -or $bytes[$peOffset + 3] -ne 0) {
        throw "Missing PE signature: $Path"
    }
    return [BitConverter]::ToUInt16($bytes, $peOffset + 4)
}

$tempRoot = Join-Path ([IO.Path]::GetTempPath()) ("outrun-dxvk-provider-" + [guid]::NewGuid().ToString("N"))
$archive = Join-Path $tempRoot ([string]$manifest.assetName)
$extractRoot = Join-Path $tempRoot "extract"

try {
    New-Item -ItemType Directory -Force $tempRoot,$extractRoot,$OutputDirectory | Out-Null
    Write-Host "Downloading pinned DXVK provider: $($manifest.releaseTag) / $($manifest.assetName)"
    Invoke-WebRequest -Uri ([string]$manifest.assetUrl) -OutFile $archive

    $archiveSha = (Get-FileHash $archive -Algorithm SHA256).Hash.ToLowerInvariant()
    $expectedArchiveSha = ([string]$manifest.assetSha256).ToLowerInvariant()
    if ($archiveSha -ne $expectedArchiveSha) {
        throw "DXVK archive SHA256 mismatch: expected=$expectedArchiveSha actual=$archiveSha"
    }
    Write-Host "DXVK_ARCHIVE_SHA256=$archiveSha"

    & tar.exe -xzf $archive -C $extractRoot
    if ($LASTEXITCODE -ne 0) { throw "tar extraction failed with exit code $LASTEXITCODE" }

    $suffixPattern = ([string]$manifest.x86D3D9RelativeSuffix).Replace('/','[\\/]')
    $matches = @(Get-ChildItem $extractRoot -Recurse -File -Filter d3d9.dll | Where-Object {
        $_.FullName -match ($suffixPattern + '$')
    })
    if ($matches.Count -ne 1) {
        throw "Expected exactly one pinned x86 d3d9.dll, found $($matches.Count)"
    }
    $providerDll = $matches[0].FullName
    $machine = Get-PeMachine $providerDll
    if ($machine -ne 0x014C) {
        throw ("Pinned DXVK d3d9.dll is not x86 PE32; machine=0x{0:X4}" -f $machine)
    }

    $providerSha = (Get-FileHash $providerDll -Algorithm SHA256).Hash.ToLowerInvariant()
    Copy-Item $providerDll (Join-Path $OutputDirectory "d3d9.dll") -Force

    if (-not $manifest.licenseUrl) { throw "Pinned DXVK license URL missing from manifest" }
    $licensePath = Join-Path $OutputDirectory "DXVK_LICENSE.txt"
    Invoke-WebRequest -Uri ([string]$manifest.licenseUrl) -OutFile $licensePath
    if (-not (Test-Path $licensePath) -or (Get-Item $licensePath).Length -lt 100) {
        throw "Pinned DXVK license download is missing or unexpectedly small"
    }

    $identity = [ordered]@{
        SchemaVersion = 1
        Provider = "DXVK"
        SourceRepository = [string]$manifest.sourceRepository
        ReleaseTag = [string]$manifest.releaseTag
        AssetId = [int64]$manifest.assetId
        AssetName = [string]$manifest.assetName
        AssetUrl = [string]$manifest.assetUrl
        AssetSha256 = $archiveSha
        D3D9RelativeSuffix = [string]$manifest.x86D3D9RelativeSuffix
        D3D9Sha256 = $providerSha
        PeMachine = "0x014C"
        BackendMode = "dxvk-safe"
        PreferD3D9Ex = $false
        DirectGpuOnly = $false
        DisableDesktopDuplication = $false
        MultiviewPatcherIncluded = $false
        PreparedUtc = (Get-Date).ToUniversalTime().ToString("o")
    }
    $identity | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $OutputDirectory "DXVK_PROVIDER.json") -Encoding UTF8

    if (Test-Path (Join-Path $OutputDirectory "multiviewpatcher.dll")) {
        throw "DXVK SAFE output must not contain multiviewpatcher.dll"
    }

    Write-Host "DXVK_D3D9_SHA256=$providerSha"
    Write-Host "DXVK provider preparation: PASS"
} finally {
    Remove-Item $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
}
