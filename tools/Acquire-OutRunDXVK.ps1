param(
    [string]$Version = '3.1.1',
    [string]$DestinationRoot = '',
    [string]$ArchiveSha256 = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
if ([string]::IsNullOrWhiteSpace($DestinationRoot)) {
    $DestinationRoot = Join-Path $repoRoot 'out/dxvk'
}

# Official release archive digests are trust anchors for stock-DXVK packaging.
# Unknown versions must provide an explicit expected archive digest; they are
# never accepted merely because the payload is a PE32 d3d9.dll.
$pinnedArchiveSha256ByVersion = @{
    '3.1.1' = '40565b4a724aadc4433fa4e010b4b23916d9b1f1baeee64e17186db94f54e608'
}

if ([string]::IsNullOrWhiteSpace($ArchiveSha256)) {
    if (-not $pinnedArchiveSha256ByVersion.ContainsKey($Version)) {
        throw "No pinned DXVK archive SHA256 is registered for version $Version. Pass -ArchiveSha256 with an independently verified release digest."
    }
    $ArchiveSha256 = [string]$pinnedArchiveSha256ByVersion[$Version]
}
$expectedArchiveSha = $ArchiveSha256.Trim().ToLowerInvariant()
if ($expectedArchiveSha -notmatch '^[0-9a-f]{64}$') {
    throw "Invalid DXVK archive SHA256: $ArchiveSha256"
}

function Get-PeMachine([string]$Path) {
    $bytes = [System.IO.File]::ReadAllBytes($Path)
    if ($bytes.Length -lt 256) { throw "PE file is too small: $Path" }
    if ($bytes[0] -ne 0x4D -or $bytes[1] -ne 0x5A) { throw "Not an MZ image: $Path" }
    $peOffset = [BitConverter]::ToInt32($bytes, 0x3C)
    if ($peOffset -lt 0 -or ($peOffset + 6) -gt $bytes.Length) {
        throw "Invalid PE header: $Path"
    }
    return [BitConverter]::ToUInt16($bytes, $peOffset + 4)
}

function Get-Sha256([string]$Path) {
    return (Get-FileHash $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Assert-Sha256([string]$Path, [string]$Expected, [string]$Label) {
    $actual = Get-Sha256 $Path
    if ($actual -ne $Expected) {
        throw "$Label SHA256 mismatch: expected=$Expected actual=$actual path=$Path"
    }
    return $actual
}

function Expand-DxvkArchive([string]$Archive, [string]$ExtractRoot, [string]$ExpectedVersion) {
    if (Test-Path $ExtractRoot) {
        Remove-Item $ExtractRoot -Recurse -Force
    }
    New-Item -ItemType Directory -Force $ExtractRoot | Out-Null

    $tar = Get-Command tar.exe -ErrorAction SilentlyContinue
    if (!$tar) { $tar = Get-Command tar -ErrorAction SilentlyContinue }
    if (!$tar) { throw 'tar is required to extract the official DXVK release archive.' }

    & $tar.Source -xzf $Archive -C $ExtractRoot
    if ($LASTEXITCODE -ne 0) {
        throw "DXVK archive extraction failed with exit code $LASTEXITCODE"
    }

    $candidate = Get-ChildItem $ExtractRoot -Recurse -File -Filter d3d9.dll |
        Where-Object { $_.FullName -match '[\\/]x32[\\/]d3d9\.dll$' } |
        Select-Object -First 1
    if (!$candidate) {
        throw "x32/d3d9.dll not found in DXVK $ExpectedVersion archive."
    }
    if ((Get-PeMachine $candidate.FullName) -ne 0x014C) {
        throw "DXVK release x32/d3d9.dll is not PE32 x86: $($candidate.FullName)"
    }
    return $candidate.FullName
}

$versionRoot = Join-Path $DestinationRoot $Version
$providerDir = Join-Path $versionRoot 'x32'
$providerPath = Join-Path $providerDir 'd3d9.dll'
$provenancePath = Join-Path $versionRoot 'PROVENANCE.txt'
$archive = Join-Path $versionRoot "dxvk-$Version.tar.gz"
$extractRoot = Join-Path $versionRoot 'extract'
$releaseUrl = "https://github.com/doitsujin/dxvk/releases/download/v$Version/dxvk-$Version.tar.gz"

New-Item -ItemType Directory -Force $versionRoot | Out-Null

if (!(Test-Path $archive)) {
    Write-Host "Downloading DXVK $Version release from pinned GitHub URL..."
    Invoke-WebRequest -Uri $releaseUrl -OutFile $archive
}

# Fail closed on an existing or newly downloaded archive that does not match
# the expected release digest. Do not silently redownload over mismatched bytes.
$archiveSha = Assert-Sha256 $archive $expectedArchiveSha "DXVK $Version archive"
$candidatePath = Expand-DxvkArchive $archive $extractRoot $Version
$candidateSha = Get-Sha256 $candidatePath

New-Item -ItemType Directory -Force $providerDir | Out-Null
if (Test-Path $providerPath) {
    if ((Get-PeMachine $providerPath) -ne 0x014C) {
        throw "Cached DXVK provider is not x86: $providerPath"
    }
    $cachedSha = Get-Sha256 $providerPath
    if ($cachedSha -ne $candidateSha) {
        Write-Host "Cached DXVK provider differs from the pinned archive; replacing it with verified release bytes."
        Copy-Item $candidatePath $providerPath -Force
    }
} else {
    Copy-Item $candidatePath $providerPath -Force
}

if ((Get-PeMachine $providerPath) -ne 0x014C) {
    throw "DXVK provider is not x86 after acquisition: $providerPath"
}
$providerSha = Get-Sha256 $providerPath
if ($providerSha -ne $candidateSha) {
    throw "DXVK provider does not match x32/d3d9.dll extracted from the pinned archive."
}

@(
    "Version=$Version"
    "ReleaseUrl=$releaseUrl"
    "ArchiveSha256=$archiveSha"
    "ExpectedArchiveSha256=$expectedArchiveSha"
    "D3D9Sha256=$providerSha"
    "Machine=0x014C"
    "Verification=PINNED_ARCHIVE_SHA256_AND_EXTRACTED_PROVIDER"
    "AcquiredUtc=$((Get-Date).ToUniversalTime().ToString('o'))"
) | Set-Content $provenancePath -Encoding UTF8

Write-Host "DXVK $Version x86 provider verified from pinned archive: $providerPath"
Write-Output $providerPath
