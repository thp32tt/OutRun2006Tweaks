Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$acquire = Join-Path $repoRoot 'tools/Acquire-OutRunDXVK.ps1'
if (-not (Test-Path $acquire)) {
    throw "DXVK acquisition helper missing: $acquire"
}

$tempRoot = Join-Path ([IO.Path]::GetTempPath()) ("outrun-dxvk-acquire-" + [guid]::NewGuid().ToString('N'))
$version = 'fixture-1'
$destination = Join-Path $tempRoot 'cache'
$versionRoot = Join-Path $destination $version
$fixtureRoot = Join-Path $tempRoot 'fixture'
$fixtureX32 = Join-Path $fixtureRoot ("dxvk-{0}/x32" -f $version)
$fixtureProvider = Join-Path $fixtureX32 'd3d9.dll'
$archive = Join-Path $versionRoot ("dxvk-{0}.tar.gz" -f $version)

try {
    New-Item -ItemType Directory -Force $fixtureX32 | Out-Null
    New-Item -ItemType Directory -Force $versionRoot | Out-Null

    # Minimal PE32-shaped fixture accepted by Get-PeMachine. The test validates
    # provenance/hash behavior only; no DLL is ever loaded.
    [byte[]]$bytes = New-Object byte[] 512
    $bytes[0] = 0x4D
    $bytes[1] = 0x5A
    [BitConverter]::GetBytes([int]0x80).CopyTo($bytes, 0x3C)
    $bytes[0x80] = 0x50
    $bytes[0x81] = 0x45
    [BitConverter]::GetBytes([uint16]0x014C).CopyTo($bytes, 0x84)
    [IO.File]::WriteAllBytes($fixtureProvider, $bytes)

    $tar = Get-Command tar.exe -ErrorAction SilentlyContinue
    if (!$tar) { $tar = Get-Command tar -ErrorAction SilentlyContinue }
    if (!$tar) { throw 'tar is required for DXVK acquisition regression tests.' }

    & $tar.Source -czf $archive -C $fixtureRoot ("dxvk-{0}" -f $version)
    if ($LASTEXITCODE -ne 0) {
        throw "Fixture archive creation failed with exit code $LASTEXITCODE"
    }
    $archiveSha = (Get-FileHash $archive -Algorithm SHA256).Hash.ToLowerInvariant()

    & $acquire -Version $version -DestinationRoot $destination -ArchiveSha256 $archiveSha | Out-Null
    $cachedProvider = Join-Path $versionRoot 'x32/d3d9.dll'
    if (-not (Test-Path $cachedProvider)) {
        throw 'Acquisition did not create the cached x32 provider.'
    }

    $fixtureSha = (Get-FileHash $fixtureProvider -Algorithm SHA256).Hash.ToLowerInvariant()
    $cachedSha = (Get-FileHash $cachedProvider -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($cachedSha -ne $fixtureSha) {
        throw "Acquired provider hash mismatch: expected=$fixtureSha actual=$cachedSha"
    }

    $provenance = Get-Content (Join-Path $versionRoot 'PROVENANCE.txt') -Raw
    foreach ($required in @(
        "ExpectedArchiveSha256=$archiveSha",
        "D3D9Sha256=$fixtureSha",
        'Verification=PINNED_ARCHIVE_SHA256_AND_EXTRACTED_PROVIDER'
    )) {
        if ($provenance -notmatch [regex]::Escape($required)) {
            throw "Provenance record missing: $required"
        }
    }

    # Tamper the cached provider. A subsequent acquisition must restore exact
    # bytes from the already hash-verified archive rather than trusting cache.
    [byte[]]$tampered = [IO.File]::ReadAllBytes($cachedProvider)
    $tampered[200] = $tampered[200] -bxor 0x5A
    [IO.File]::WriteAllBytes($cachedProvider, $tampered)
    if ((Get-FileHash $cachedProvider -Algorithm SHA256).Hash.ToLowerInvariant() -eq $fixtureSha) {
        throw 'Provider tamper fixture did not change the hash.'
    }

    & $acquire -Version $version -DestinationRoot $destination -ArchiveSha256 $archiveSha | Out-Null
    $repairedSha = (Get-FileHash $cachedProvider -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($repairedSha -ne $fixtureSha) {
        throw "Tampered provider was not restored from pinned archive: $repairedSha"
    }

    # An unpinned version must fail before any network request is attempted.
    $unpinnedFailed = $false
    try {
        & $acquire -Version 'fixture-unpinned' -DestinationRoot $destination | Out-Null
    } catch {
        $unpinnedFailed = $_.Exception.Message -match 'No pinned DXVK archive SHA256'
    }
    if (-not $unpinnedFailed) {
        throw 'Unpinned DXVK version was not rejected.'
    }

    # A mismatched archive must fail closed rather than being silently replaced.
    [byte[]]$archiveBytes = [IO.File]::ReadAllBytes($archive)
    $archiveBytes[$archiveBytes.Length - 1] = $archiveBytes[$archiveBytes.Length - 1] -bxor 0x01
    [IO.File]::WriteAllBytes($archive, $archiveBytes)
    $mismatchFailed = $false
    try {
        & $acquire -Version $version -DestinationRoot $destination -ArchiveSha256 $archiveSha | Out-Null
    } catch {
        $mismatchFailed = $_.Exception.Message -match 'archive SHA256 mismatch'
    }
    if (-not $mismatchFailed) {
        throw 'Tampered DXVK archive was not rejected.'
    }

    Write-Host 'DXVK acquisition regression tests: PASS'
}
finally {
    if (Test-Path $tempRoot) {
        Remove-Item $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}
