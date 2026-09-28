param(
    [string]$Version = '3.1.1',
    [string]$DestinationRoot = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
if ([string]::IsNullOrWhiteSpace($DestinationRoot)) {
    $DestinationRoot = Join-Path $repoRoot 'out/dxvk'
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

$versionRoot = Join-Path $DestinationRoot $Version
$providerDir = Join-Path $versionRoot 'x32'
$providerPath = Join-Path $providerDir 'd3d9.dll'
$provenancePath = Join-Path $versionRoot 'PROVENANCE.txt'
$releaseUrl = "https://github.com/doitsujin/dxvk/releases/download/v$Version/dxvk-$Version.tar.gz"

if (Test-Path $providerPath) {
    if ((Get-PeMachine $providerPath) -ne 0x014C) {
        throw "Cached DXVK provider is not x86: $providerPath"
    }
    Write-Host "DXVK $Version x86 provider cache hit: $providerPath"
    Write-Output $providerPath
    exit 0
}

New-Item -ItemType Directory -Force $versionRoot | Out-Null
$archive = Join-Path $versionRoot "dxvk-$Version.tar.gz"
$extractRoot = Join-Path $versionRoot 'extract'

if (!(Test-Path $archive)) {
    Write-Host "Downloading official DXVK $Version release..."
    Invoke-WebRequest -Uri $releaseUrl -OutFile $archive
}

if (Test-Path $extractRoot) {
    Remove-Item $extractRoot -Recurse -Force
}
New-Item -ItemType Directory -Force $extractRoot | Out-Null

$tar = Get-Command tar.exe -ErrorAction SilentlyContinue
if (!$tar) { $tar = Get-Command tar -ErrorAction SilentlyContinue }
if (!$tar) { throw 'tar is required to extract the official DXVK release archive.' }

& $tar.Source -xzf $archive -C $extractRoot
if ($LASTEXITCODE -ne 0) {
    throw "DXVK archive extraction failed with exit code $LASTEXITCODE"
}

$candidate = Get-ChildItem $extractRoot -Recurse -File -Filter d3d9.dll |
    Where-Object { $_.FullName -match '[\\/]x32[\\/]d3d9\.dll$' } |
    Select-Object -First 1
if (!$candidate) {
    throw "x32/d3d9.dll not found in DXVK $Version archive."
}
if ((Get-PeMachine $candidate.FullName) -ne 0x014C) {
    throw "DXVK release x32/d3d9.dll is not PE32 x86: $($candidate.FullName)"
}

New-Item -ItemType Directory -Force $providerDir | Out-Null
Copy-Item $candidate.FullName $providerPath -Force

$archiveSha = (Get-FileHash $archive -Algorithm SHA256).Hash.ToLowerInvariant()
$providerSha = (Get-FileHash $providerPath -Algorithm SHA256).Hash.ToLowerInvariant()
@(
    "Version=$Version"
    "ReleaseUrl=$releaseUrl"
    "ArchiveSha256=$archiveSha"
    "D3D9Sha256=$providerSha"
    "Machine=0x014C"
    "AcquiredUtc=$((Get-Date).ToUniversalTime().ToString('o'))"
) | Set-Content $provenancePath -Encoding UTF8

Write-Host "DXVK $Version x86 provider ready: $providerPath"
Write-Output $providerPath
