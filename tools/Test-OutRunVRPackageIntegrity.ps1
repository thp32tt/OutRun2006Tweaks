Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'

$lib=Join-Path $PSScriptRoot 'OutRunVR-PackageIntegrity.ps1'
if(!(Test-Path $lib -PathType Leaf)){throw "Missing package-integrity library: $lib"}
. $lib

$root=Join-Path ([IO.Path]::GetTempPath()) ('outrun-package-integrity-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force (Join-Path $root 'nested')|Out-Null

function Write-Manifest([string[]]$RelativePaths){
    $lines=@()
    foreach($rel in $RelativePaths){
        $hash=(Get-FileHash (Join-Path $root $rel) -Algorithm SHA256).Hash
        $lines+=("$hash  $rel")
    }
    Set-Content (Join-Path $root 'SHA256SUMS.txt') $lines -Encoding ascii
}

function Expect-Failure([string]$Name,[scriptblock]$Action,[string]$ExpectedText){
    $failed=$false
    try{& $Action}catch{
        $failed=$true
        if($_.Exception.Message -notlike "*$ExpectedText*"){
            throw "$Name failed with unexpected message: $($_.Exception.Message)"
        }
    }
    if(-not $failed){throw "$Name unexpectedly passed"}
}

try{
    Set-Content (Join-Path $root 'launcher.ps1') 'Write-Host launcher' -Encoding UTF8
    Set-Content (Join-Path $root 'nested/analyzer.py') 'print("analyzer")' -Encoding UTF8
    Write-Manifest @('launcher.ps1','nested/analyzer.py')

    $ok=Test-OutRunVRPackageIntegrity -Root $root -ManifestPath (Join-Path $root 'SHA256SUMS.txt')
    if(-not $ok.Verified -or $ok.EntryCount -ne 2){
        throw "valid manifest result unexpected: verified=$($ok.Verified) entries=$($ok.EntryCount)"
    }

    Add-Content (Join-Path $root 'nested/analyzer.py') '# tampered'
    Expect-Failure 'tampered-file' {
        Test-OutRunVRPackageIntegrity -Root $root -ManifestPath (Join-Path $root 'SHA256SUMS.txt')|Out-Null
    } 'Package manifest hash mismatch'

    Set-Content (Join-Path $root 'nested/analyzer.py') 'print("analyzer")' -Encoding UTF8
    Write-Manifest @('launcher.ps1','nested/analyzer.py')
    Remove-Item (Join-Path $root 'nested/analyzer.py') -Force
    Expect-Failure 'missing-file' {
        Test-OutRunVRPackageIntegrity -Root $root -ManifestPath (Join-Path $root 'SHA256SUMS.txt')|Out-Null
    } 'Package manifest file missing'

    Set-Content (Join-Path $root 'escape.txt') 'safe' -Encoding UTF8
    $escapeHash=(Get-FileHash (Join-Path $root 'escape.txt') -Algorithm SHA256).Hash
    Set-Content (Join-Path $root 'SHA256SUMS.txt') ("$escapeHash  ../escape.txt") -Encoding ascii
    Expect-Failure 'path-traversal' {
        Test-OutRunVRPackageIntegrity -Root $root -ManifestPath (Join-Path $root 'SHA256SUMS.txt')|Out-Null
    } 'unsafe relative path'

    Write-Manifest @('launcher.ps1')
    $line=(Get-Content (Join-Path $root 'SHA256SUMS.txt') -Raw).Trim()
    Set-Content (Join-Path $root 'SHA256SUMS.txt') @($line,$line) -Encoding ascii
    Expect-Failure 'duplicate-path' {
        Test-OutRunVRPackageIntegrity -Root $root -ManifestPath (Join-Path $root 'SHA256SUMS.txt')|Out-Null
    } 'duplicate path'

    Write-Host 'OutRun package-wide SHA256 integrity tests: PASS'
} finally {
    if(Test-Path $root){Remove-Item $root -Recurse -Force -ErrorAction SilentlyContinue}
}
