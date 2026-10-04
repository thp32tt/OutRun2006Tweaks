Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'

$preflightSource=Join-Path $PSScriptRoot 'Test-OutRunVROneClickPreflight.ps1'
$integritySource=Join-Path $PSScriptRoot 'OutRunVR-PackageIntegrity.ps1'
$launcherSource=Join-Path $PSScriptRoot 'Invoke-OutRunVROneClick.ps1'
$targetSource=Join-Path $PSScriptRoot 'VR_ONE_CLICK_TARGET.json'
foreach($path in @($preflightSource,$integritySource,$launcherSource,$targetSource)){
    if(!(Test-Path $path -PathType Leaf)){throw "One-click behavior dependency missing: $path"}
}

function Write-FakePe([string]$Path,[uint16]$Machine,[byte]$Salt=0){
    $bytes=New-Object byte[] 512
    $bytes[0]=0x4D
    $bytes[1]=0x5A
    [BitConverter]::GetBytes([int]0x80).CopyTo($bytes,0x3C)
    $bytes[0x80]=0x50
    $bytes[0x81]=0x45
    $bytes[0x82]=0
    $bytes[0x83]=0
    [BitConverter]::GetBytes($Machine).CopyTo($bytes,0x84)
    $bytes[0x100]=$Salt
    [IO.File]::WriteAllBytes($Path,$bytes)
}

function Write-PackageManifest([string]$Root){
    $manifest=Join-Path $Root 'SHA256SUMS.txt'
    $rootFull=(Resolve-Path $Root).Path
    $lines=@()
    foreach($file in Get-ChildItem $Root -Recurse -File | Sort-Object FullName){
        if($file.FullName -eq $manifest){continue}
        if($file.Name -eq 'VR_ONE_CLICK_PREFLIGHT.json'){continue}
        $hash=(Get-FileHash $file.FullName -Algorithm SHA256).Hash
        $relative=$file.FullName.Substring($rootFull.Length+1)
        $lines+=("$hash  $relative")
    }
    Set-Content $manifest $lines -Encoding ascii
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

$root=Join-Path ([IO.Path]::GetTempPath()) ('outrun-oneclick-behavior-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force $root|Out-Null
try{
    Copy-Item $preflightSource (Join-Path $root 'Test-OutRunVROneClickPreflight.ps1')
    Copy-Item $integritySource (Join-Path $root 'OutRunVR-PackageIntegrity.ps1')
    Copy-Item $targetSource (Join-Path $root 'VR_ONE_CLICK_TARGET.json')

    New-Item -ItemType Directory -Force (Join-Path $root 'backends/d3d9')|Out-Null
    New-Item -ItemType Directory -Force (Join-Path $root 'backends/dxvk')|Out-Null
    New-Item -ItemType Directory -Force (Join-Path $root 'slots/R69_FIXPACK')|Out-Null

    Write-FakePe (Join-Path $root 'OR2006C2C.EXE') 0x014C 1
    Set-Content (Join-Path $root 'OutRun2006Tweaks.ini') "[VR]`r`nEnabled = true`r`n" -Encoding UTF8
    Write-FakePe (Join-Path $root 'backends/d3d9/dinput8.dll') 0x014C 2
    Write-FakePe (Join-Path $root 'backends/d3d9/outrun-vr-host.exe') 0x8664 3
    Set-Content (Join-Path $root 'backends/d3d9/SOURCE_SHA.txt') 'test-source-sha' -Encoding ascii
    Set-Content (Join-Path $root 'backends/d3d9/VARIANT_ID.txt') 'R69_FIXPACK' -Encoding ascii
    Write-FakePe (Join-Path $root 'backends/dxvk/d3d9.dll') 0x014C 4
    Set-Content (Join-Path $root 'backends/dxvk/DXVK_VERSION.txt') '3.1.1' -Encoding ascii
    Set-Content (Join-Path $root 'backends/dxvk/VARIANT_ID.txt') 'R69_FIXPACK' -Encoding ascii
    $providerHash=(Get-FileHash (Join-Path $root 'backends/dxvk/d3d9.dll') -Algorithm SHA256).Hash.ToLowerInvariant()
    Set-Content (Join-Path $root 'backends/dxvk/DXVK_D3D9_SHA256.txt') $providerHash -Encoding ascii

    Copy-Item (Join-Path $root 'backends/d3d9/dinput8.dll') (Join-Path $root 'slots/R69_FIXPACK/dinput8.dll')
    Copy-Item (Join-Path $root 'backends/d3d9/outrun-vr-host.exe') (Join-Path $root 'slots/R69_FIXPACK/outrun-vr-host.exe')
    Set-Content (Join-Path $root 'slots/R69_FIXPACK/SOURCE_SHA.txt') 'test-source-sha' -Encoding ascii

    $buildInputs=[ordered]@{
        SchemaVersion=1
        BuildMatrixId='behavior-fixture'
        IntegrationSha='test-source-sha'
        DevelopmentBranch='vr-dxvk-r71-disasm'
        RendererTarget='dxvk'
        DevelopmentStage='R71-stock-dxvk-3.1.1-two-pass-parity-game-local-provider-verified'
        LaunchBackend='dxvk-safe'
        VariantId='R69_FIXPACK'
    }
    $buildInputs|ConvertTo-Json -Depth 4|Set-Content (Join-Path $root 'BUILD_INPUTS.json') -Encoding UTF8
    Write-PackageManifest $root

    & (Join-Path $root 'Test-OutRunVROneClickPreflight.ps1') -Backend dxvk-safe
    $report=Get-Content (Join-Path $root 'VR_ONE_CLICK_PREFLIGHT.json') -Raw|ConvertFrom-Json
    if(-not [bool]$report.PackageIntegrity.Verified){throw 'Valid preflight did not verify package integrity.'}
    if(-not [bool]$report.SlotPayload.MatchesCanonicalPayload){throw 'Valid preflight did not attest target slot precedence.'}
    if([string]$report.SourceSha -ne 'test-source-sha'){throw "Valid preflight source mismatch: $($report.SourceSha)"}
    if([string]$report.VariantId -ne 'R69_FIXPACK'){throw "Valid preflight variant mismatch: $($report.VariantId)"}
    if([string]$report.Dxvk.Version -ne '3.1.1'){throw "Valid preflight DXVK version mismatch: $($report.Dxvk.Version)"}

    # A target-named slot can outrank the canonical backend only while its
    # executable bytes remain identical. Re-seal the package so this exercises
    # slot precedence rather than the package-integrity gate.
    Write-FakePe (Join-Path $root 'slots/R69_FIXPACK/dinput8.dll') 0x014C 9
    Write-PackageManifest $root
    Expect-Failure 'slot-precedence' {
        & (Join-Path $root 'Test-OutRunVROneClickPreflight.ps1') -Backend dxvk-safe
    } 'One-click slot payload mismatch: dinput8.dll'
    Copy-Item (Join-Path $root 'backends/d3d9/dinput8.dll') (Join-Path $root 'slots/R69_FIXPACK/dinput8.dll') -Force

    $buildInputs.IntegrationSha='wrong-source-sha'
    $buildInputs|ConvertTo-Json -Depth 4|Set-Content (Join-Path $root 'BUILD_INPUTS.json') -Encoding UTF8
    Write-PackageManifest $root
    Expect-Failure 'package-source' {
        & (Join-Path $root 'Test-OutRunVROneClickPreflight.ps1') -Backend dxvk-safe
    } 'Package source mismatch'
    $buildInputs.IntegrationSha='test-source-sha'
    $buildInputs|ConvertTo-Json -Depth 4|Set-Content (Join-Path $root 'BUILD_INPUTS.json') -Encoding UTF8

    $buildInputs.VariantId='ACTIVE_R26_HUD_R69'
    $buildInputs|ConvertTo-Json -Depth 4|Set-Content (Join-Path $root 'BUILD_INPUTS.json') -Encoding UTF8
    Write-PackageManifest $root
    Expect-Failure 'package-variant' {
        & (Join-Path $root 'Test-OutRunVROneClickPreflight.ps1') -Backend dxvk-safe
    } 'Package variant mismatch: BUILD_INPUTS='
    $buildInputs.VariantId='R69_FIXPACK'
    $buildInputs|ConvertTo-Json -Depth 4|Set-Content (Join-Path $root 'BUILD_INPUTS.json') -Encoding UTF8

    # F02 canonical VariantId must fail closed at every packaged identity layer,
    # not only BUILD_INPUTS and the DXVK provider directory.
    Set-Content (Join-Path $root 'backends/d3d9/VARIANT_ID.txt') 'ACTIVE_R26_HUD_R69' -Encoding ascii
    Write-PackageManifest $root
    Expect-Failure 'd3d9-backend-variant' {
        & (Join-Path $root 'Test-OutRunVROneClickPreflight.ps1') -Backend dxvk-safe
    } 'Package variant mismatch: backends/d3d9'
    Set-Content (Join-Path $root 'backends/d3d9/VARIANT_ID.txt') 'R69_FIXPACK' -Encoding ascii

    Set-Content (Join-Path $root 'backends/dxvk/VARIANT_ID.txt') 'DXVK_SAFE_R71' -Encoding ascii
    Write-PackageManifest $root
    Expect-Failure 'dxvk-backend-variant' {
        & (Join-Path $root 'Test-OutRunVROneClickPreflight.ps1') -Backend dxvk-safe
    } 'Package variant mismatch: backends/dxvk'
    Set-Content (Join-Path $root 'backends/dxvk/VARIANT_ID.txt') 'R69_FIXPACK' -Encoding ascii

    Set-Content (Join-Path $root 'backends/dxvk/DXVK_D3D9_SHA256.txt') ('0'*64) -Encoding ascii
    Write-PackageManifest $root
    Expect-Failure 'provider-hash' {
        & (Join-Path $root 'Test-OutRunVROneClickPreflight.ps1') -Backend dxvk-safe
    } 'DXVK d3d9.dll hash mismatch'

    # Launcher target locking is deliberately tested without a runnable game.
    # Stub dependencies throw if execution gets past the lock.
    $lockRoot=Join-Path $root 'target-lock'
    New-Item -ItemType Directory -Force $lockRoot|Out-Null
    Copy-Item $launcherSource (Join-Path $lockRoot 'Invoke-OutRunVROneClick.ps1')
    Copy-Item $targetSource (Join-Path $lockRoot 'VR_ONE_CLICK_TARGET.json')
    foreach($name in @('Select-OutRunVRBackend.ps1','Run-OutRunVRTest.ps1','Test-OutRunVROneClickPreflight.ps1')){
        Set-Content (Join-Path $lockRoot $name) "throw 'target-lock stub executed unexpectedly'" -Encoding UTF8
    }

    Expect-Failure 'backend-target-lock' {
        & (Join-Path $lockRoot 'Invoke-OutRunVROneClick.ps1') -Backend d3d9
    } 'One-click backend override blocked'
    Expect-Failure 'variant-target-lock' {
        & (Join-Path $lockRoot 'Invoke-OutRunVROneClick.ps1') -Backend dxvk-safe -VariantId A_CONTROL
    } 'One-click variant override blocked'

    Write-Host 'OutRun DXVK one-click preflight + target-lock behavior tests: PASS'
} finally {
    if(Test-Path $root){Remove-Item $root -Recurse -Force -ErrorAction SilentlyContinue}
}
