Set-StrictMode -Version Latest

function Test-OutRunVRPackageIntegrity {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][string]$Root,
        [Parameter(Mandatory=$true)][string]$ManifestPath
    )

    if(!(Test-Path $Root -PathType Container)){
        throw "Package integrity root missing: $Root"
    }
    if(!(Test-Path $ManifestPath -PathType Leaf)){
        throw "Package SHA256 manifest missing: $ManifestPath"
    }

    $rootFull=(Resolve-Path $Root).Path.TrimEnd([IO.Path]::DirectorySeparatorChar,[IO.Path]::AltDirectorySeparatorChar)
    $rootPrefix=$rootFull+[IO.Path]::DirectorySeparatorChar
    $manifestFull=(Resolve-Path $ManifestPath).Path
    $manifestName=[IO.Path]::GetFileName($manifestFull)
    $seen=[System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    $entries=@()

    foreach($rawLine in Get-Content $manifestFull){
        if([string]::IsNullOrWhiteSpace($rawLine)){continue}
        if($rawLine -notmatch '^([0-9A-Fa-f]{64})\s{2}(.+)$'){
            throw "Malformed package SHA256 manifest entry: $rawLine"
        }

        $expectedHash=$matches[1].ToLowerInvariant()
        $relative=[string]$matches[2]
        if([string]::IsNullOrWhiteSpace($relative)){
            throw 'Package SHA256 manifest contains an empty path.'
        }
        if([IO.Path]::IsPathRooted($relative)){
            throw "Package SHA256 manifest contains rooted path: $relative"
        }

        $parts=$relative -split '[\\/]'
        if($parts -contains '..' -or $parts -contains '.'){
            throw "Package SHA256 manifest contains unsafe relative path: $relative"
        }
        if([string]::Equals([IO.Path]::GetFileName($relative),$manifestName,[StringComparison]::OrdinalIgnoreCase)){
            throw "Package SHA256 manifest must not self-reference: $relative"
        }
        if(-not $seen.Add($relative)){
            throw "Package SHA256 manifest contains duplicate path: $relative"
        }

        $candidate=[IO.Path]::GetFullPath((Join-Path $rootFull $relative))
        if(-not $candidate.StartsWith($rootPrefix,[StringComparison]::OrdinalIgnoreCase)){
            throw "Package SHA256 manifest path escapes package root: $relative"
        }
        if(!(Test-Path $candidate -PathType Leaf)){
            throw "Package manifest file missing: $relative"
        }

        $actualHash=(Get-FileHash $candidate -Algorithm SHA256).Hash.ToLowerInvariant()
        if($actualHash -ne $expectedHash){
            throw "Package manifest hash mismatch: $relative expected=$expectedHash actual=$actualHash"
        }

        $entries += [pscustomobject]@{
            Path=$relative
            Sha256=$actualHash
        }
    }

    if($entries.Count -eq 0){
        throw 'Package SHA256 manifest has no file entries.'
    }

    return [pscustomobject]@{
        Verified=$true
        EntryCount=$entries.Count
        ManifestSha256=(Get-FileHash $manifestFull -Algorithm SHA256).Hash.ToLowerInvariant()
        Entries=$entries
    }
}
