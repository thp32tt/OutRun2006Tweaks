param(
    [ValidateSet('auto','2d','d3d9','dx11','dxvk-safe','dxvk')]
    [string]$Backend = 'auto'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$targetPath = Join-Path $root 'VR_ONE_CLICK_TARGET.json'
$reportPath = Join-Path $root 'VR_ONE_CLICK_PREFLIGHT.json'

# Never leave a previous successful preflight report behind when this run fails.
# Pre-session failure diagnostics are written by the one-click launcher.
if (Test-Path $reportPath -PathType Leaf) {
    Remove-Item $reportPath -Force
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

function Require-File([string]$Path,[string]$Label) {
    if (!(Test-Path $Path -PathType Leaf)) {
        throw "$Label is missing: $Path"
    }
    return (Resolve-Path $Path).Path
}

function Get-Identity([string]$Path,[int]$ExpectedMachine = 0) {
    $resolved = Require-File $Path 'Required file'
    $machine = $null
    if ($ExpectedMachine -ne 0) {
        $machine = Get-PeMachine $resolved
        if ($machine -ne $ExpectedMachine) {
            throw ("Unexpected PE machine for {0}: got 0x{1:X4}, expected 0x{2:X4}" -f
                $resolved,$machine,$ExpectedMachine)
        }
    }
    return [ordered]@{
        Path = [IO.Path]::GetFileName($resolved)
        Length = (Get-Item $resolved).Length
        Sha256 = (Get-FileHash $resolved -Algorithm SHA256).Hash.ToLowerInvariant()
        Machine = if ($machine -ne $null) { ('0x{0:X4}' -f $machine) } else { $null }
    }
}

if (!(Test-Path $targetPath -PathType Leaf)) {
    throw "One-click target metadata is missing: $targetPath"
}
try {
    $target = Get-Content $targetPath -Raw | ConvertFrom-Json
} catch {
    throw "Invalid VR_ONE_CLICK_TARGET.json: $($_.Exception.Message)"
}

foreach ($field in @('SchemaVersion','RendererTarget','LaunchBackend','Stage','VariantId','DevelopmentBranch')) {
    if ($null -eq $target.$field -or [string]::IsNullOrWhiteSpace([string]$target.$field)) {
        throw "VR_ONE_CLICK_TARGET.json is missing required field: $field"
    }
}

$resolvedBackend = $Backend
if ($resolvedBackend -eq 'auto') {
    $resolvedBackend = [string]$target.LaunchBackend
}
$allowed = @('2d','d3d9','dx11','dxvk-safe','dxvk')
if ($allowed -notcontains $resolvedBackend) {
    throw "Unsupported one-click backend: $resolvedBackend"
}

$packageIntegrity=$null
$packageIntegrityLib=Require-File (Join-Path $root 'OutRunVR-PackageIntegrity.ps1') 'Package integrity verifier'
. $packageIntegrityLib
$packageManifestPath=Join-Path $root 'SHA256SUMS.txt'
$requiresPackageManifest=($resolvedBackend -eq 'dxvk-safe' -or $resolvedBackend -eq 'dxvk')
if($requiresPackageManifest -or (Test-Path $packageManifestPath -PathType Leaf)){
    if(!(Test-Path $packageManifestPath -PathType Leaf)){
        throw "DXVK package SHA256 manifest missing: $packageManifestPath"
    }
    $packageIntegrity=Test-OutRunVRPackageIntegrity -Root $root -ManifestPath $packageManifestPath
    if(-not $packageIntegrity.Verified){
        throw 'Package-wide SHA256 integrity verification did not return a verified result.'
    }
}

$gamePath = Require-File (Join-Path $root 'OR2006C2C.EXE') 'OutRun executable'
$iniPath = Require-File (Join-Path $root 'OutRun2006Tweaks.ini') 'OutRun2006Tweaks.ini'
$d3d9Backend = Join-Path $root 'backends/d3d9'
$dxvkBackend = Join-Path $root 'backends/dxvk'

$gameDllPath = Require-File (Join-Path $d3d9Backend 'dinput8.dll') 'Game VR DLL'
$hostPath = Require-File (Join-Path $d3d9Backend 'outrun-vr-host.exe') 'x64 OpenXR host'
$sourceShaPath = Require-File (Join-Path $d3d9Backend 'SOURCE_SHA.txt') 'Backend source identity'
$sourceSha = (Get-Content $sourceShaPath -Raw).Trim()
if ([string]::IsNullOrWhiteSpace($sourceSha)) { throw 'Backend SOURCE_SHA.txt is empty.' }

$canonicalVariantId = [string]$target.VariantId
$d3d9VariantPath = Require-File (Join-Path $d3d9Backend 'VARIANT_ID.txt') 'D3D9 backend variant identity'
$d3d9VariantId = (Get-Content $d3d9VariantPath -Raw).Trim()
if ($d3d9VariantId -ne $canonicalVariantId) {
    throw "Package variant mismatch: backends/d3d9 VARIANT_ID=$d3d9VariantId target=$canonicalVariantId"
}
if ($resolvedBackend -eq 'dxvk-safe' -or $resolvedBackend -eq 'dxvk') {
    $dxvkVariantPath = Require-File (Join-Path $dxvkBackend 'VARIANT_ID.txt') 'DXVK backend variant identity'
    $dxvkVariantId = (Get-Content $dxvkVariantPath -Raw).Trim()
    if ($dxvkVariantId -ne $canonicalVariantId) {
        throw "Package variant mismatch: backends/dxvk VARIANT_ID=$dxvkVariantId target=$canonicalVariantId"
    }
}

# One-click must not allow an old variant slot to silently outrank the
# package payload that was just verified above. A target-named slot is allowed
# only when its source identity and executable bytes exactly match the
# canonical D3D9 backend payload.
$targetSlotPayload = Join-Path $root ("slots/" + [string]$target.VariantId)
$slotIdentity = $null
if (Test-Path $targetSlotPayload -PathType Container) {
    $slotSourceShaPath = Require-File (Join-Path $targetSlotPayload 'SOURCE_SHA.txt') 'One-click slot source identity'
    $slotSourceSha = (Get-Content $slotSourceShaPath -Raw).Trim()
    if ($slotSourceSha -ne $sourceSha) {
        throw "One-click slot source mismatch: variant=$($target.VariantId) slot=$slotSourceSha package=$sourceSha"
    }

    $canonicalGameIdentity = Get-Identity $gameDllPath 0x014C
    $slotGameIdentity = Get-Identity (Join-Path $targetSlotPayload 'dinput8.dll') 0x014C
    if ($slotGameIdentity.Sha256 -ne $canonicalGameIdentity.Sha256) {
        throw "One-click slot payload mismatch: dinput8.dll variant=$($target.VariantId)"
    }

    $canonicalHostIdentity = Get-Identity $hostPath 0x8664
    $slotHostIdentity = Get-Identity (Join-Path $targetSlotPayload 'outrun-vr-host.exe') 0x8664
    if ($slotHostIdentity.Sha256 -ne $canonicalHostIdentity.Sha256) {
        throw "One-click slot payload mismatch: outrun-vr-host.exe variant=$($target.VariantId)"
    }

    $slotIdentity = [ordered]@{
        VariantId = [string]$target.VariantId
        SourceSha = $slotSourceSha
        GameVrDll = $slotGameIdentity
        OpenXrHost = $slotHostIdentity
        MatchesCanonicalPayload = $true
    }
}

$buildInputsPath = Require-File (Join-Path $root 'BUILD_INPUTS.json') 'BUILD_INPUTS.json'
try {
    $buildInputs = Get-Content $buildInputsPath -Raw | ConvertFrom-Json
} catch {
    throw "Invalid BUILD_INPUTS.json: $($_.Exception.Message)"
}
if ([string]$buildInputs.IntegrationSha -ne $sourceSha) {
    throw "Package source mismatch: BUILD_INPUTS=$($buildInputs.IntegrationSha) payload=$sourceSha"
}
if ([string]$buildInputs.DevelopmentBranch -ne [string]$target.DevelopmentBranch) {
    throw "Package branch mismatch: BUILD_INPUTS=$($buildInputs.DevelopmentBranch) target=$($target.DevelopmentBranch)"
}
if ([string]$buildInputs.RendererTarget -ne [string]$target.RendererTarget) {
    throw "Package renderer mismatch: BUILD_INPUTS=$($buildInputs.RendererTarget) target=$($target.RendererTarget)"
}
if ([string]$buildInputs.LaunchBackend -ne [string]$target.LaunchBackend) {
    throw "Package launch backend mismatch: BUILD_INPUTS=$($buildInputs.LaunchBackend) target=$($target.LaunchBackend)"
}
if ([string]$buildInputs.VariantId -ne $canonicalVariantId) {
    throw "Package variant mismatch: BUILD_INPUTS=$($buildInputs.VariantId) target=$canonicalVariantId"
}

$report = [ordered]@{
    SchemaVersion = 1
    VerifiedUtc = (Get-Date).ToUniversalTime().ToString('o')
    DevelopmentBranch = [string]$target.DevelopmentBranch
    RendererTarget = [string]$target.RendererTarget
    Stage = [string]$target.Stage
    RequestedBackend = $Backend
    ResolvedBackend = $resolvedBackend
    VariantId = [string]$target.VariantId
    SourceSha = $sourceSha
    PackageIntegrity = if($null -ne $packageIntegrity){
        [ordered]@{
            Verified=[bool]$packageIntegrity.Verified
            EntryCount=[int]$packageIntegrity.EntryCount
            ManifestSha256=[string]$packageIntegrity.ManifestSha256
        }
    }else{$null}
    SlotPayload = $slotIdentity
    PackageBuildInputs = [ordered]@{
        BuildMatrixId = [string]$buildInputs.BuildMatrixId
        IntegrationSha = [string]$buildInputs.IntegrationSha
        DevelopmentBranch = [string]$buildInputs.DevelopmentBranch
        RendererTarget = [string]$buildInputs.RendererTarget
        DevelopmentStage = [string]$buildInputs.DevelopmentStage
        LaunchBackend = [string]$buildInputs.LaunchBackend
    }
    Game = Get-Identity $gamePath 0x014C
    GameVrDll = Get-Identity $gameDllPath 0x014C
    OpenXrHost = Get-Identity $hostPath 0x8664
    IniSha256 = (Get-FileHash $iniPath -Algorithm SHA256).Hash.ToLowerInvariant()
    Dxvk = $null
}

if ($resolvedBackend -eq 'dxvk-safe' -or $resolvedBackend -eq 'dxvk') {
    $providerPath = Require-File (Join-Path $dxvkBackend 'd3d9.dll') 'Pinned DXVK x86 provider'
    $provider = Get-Identity $providerPath 0x014C

    $versionPath = Require-File (Join-Path $dxvkBackend 'DXVK_VERSION.txt') 'DXVK version identity'
    $hashPath = Require-File (Join-Path $dxvkBackend 'DXVK_D3D9_SHA256.txt') 'DXVK hash identity'
    $version = (Get-Content $versionPath -Raw).Trim()
    $expectedHash = (Get-Content $hashPath -Raw).Trim().ToLowerInvariant()

    if ($target.PSObject.Properties.Name -contains 'DxvkVersion') {
        if ($version -ne [string]$target.DxvkVersion) {
            throw "DXVK version mismatch: package=$version target=$($target.DxvkVersion)"
        }
    }
    if ($provider.Sha256 -ne $expectedHash) {
        throw "DXVK d3d9.dll hash mismatch: package=$($provider.Sha256) metadata=$expectedHash"
    }

    $report.Dxvk = [ordered]@{
        Version = $version
        Provider = $provider
        ExpectedSha256 = $expectedHash
        MultiviewEnabled = ($resolvedBackend -eq 'dxvk')
    }
}

$report | ConvertTo-Json -Depth 8 | Set-Content $reportPath -Encoding UTF8
Write-Host ("One-click preflight PASS: renderer={0} backend={1} source={2}" -f
    $report.RendererTarget,$resolvedBackend,$sourceSha)
Write-Host ("Preflight report: {0}" -f $reportPath)