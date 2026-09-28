Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$analyzer = Join-Path $PSScriptRoot 'Analyze-OutRunVRSession.ps1'
if(!(Test-Path $analyzer -PathType Leaf)){
    throw "Missing VR session analyzer: $analyzer"
}

function Invoke-AnalyzerCase {
    param(
        [Parameter(Mandatory=$true)][string]$Name,
        [Parameter(Mandatory=$true)][string]$GameLog,
        [Parameter(Mandatory=$true)][string]$DxvkLog,
        [Parameter(Mandatory=$true)][string]$HostLog,
        [Parameter(Mandatory=$true)][bool]$ExpectedSharedFailure,
        [string[]]$ExpectedReasons=@(),
        [Parameter(Mandatory=$true)][int64]$ExpectedDirectFrames,
        [Parameter(Mandatory=$true)][int64]$ExpectedFallbacks
    )

    $caseRoot = Join-Path $script:TestRoot $Name
    New-Item -ItemType Directory -Force $caseRoot | Out-Null

    [ordered]@{
        SchemaVersion=3
        VariantId='E_DXVK_SAFE'
        Backend='dxvk-safe'
        TestProfile='CORRECTNESS'
        SourceSha='fixture-source'
    } | ConvertTo-Json | Set-Content (Join-Path $caseRoot 'session_manifest.json') -Encoding UTF8

    Set-Content (Join-Path $caseRoot 'OutRun2006Tweaks.log') $GameLog -Encoding UTF8
    Set-Content (Join-Path $caseRoot 'OR2006C2C_d3d9.log') $DxvkLog -Encoding UTF8
    Set-Content (Join-Path $caseRoot 'outrun-vr-host-v3.log') $HostLog -Encoding UTF8

    & $analyzer -SessionDir $caseRoot | Out-Null

    $summaryPath = Join-Path $caseRoot 'AUTO_ANALYSIS_SUMMARY.json'
    if(!(Test-Path $summaryPath -PathType Leaf)){
        throw "${Name}: AUTO_ANALYSIS_SUMMARY.json missing"
    }
    $summary = Get-Content $summaryPath -Raw | ConvertFrom-Json

    if([bool]$summary.SharedD3D9ExProbeFailed -ne $ExpectedSharedFailure){
        throw "${Name}: SharedD3D9ExProbeFailed=$($summary.SharedD3D9ExProbeFailed), expected $ExpectedSharedFailure"
    }
    if([int64]$summary.DirectFrames -ne $ExpectedDirectFrames){
        throw "${Name}: DirectFrames=$($summary.DirectFrames), expected $ExpectedDirectFrames"
    }
    if([int64]$summary.DirectFallbacks -ne $ExpectedFallbacks){
        throw "${Name}: DirectFallbacks=$($summary.DirectFallbacks), expected $ExpectedFallbacks"
    }

    $actualReasons=@($summary.SharedD3D9ExProbeFailureReasons)
    foreach($reason in $ExpectedReasons){
        if($actualReasons -notcontains $reason){
            throw "${Name}: missing shared-probe reason $reason; actual=$($actualReasons -join ',')"
        }
    }
    if(-not $ExpectedSharedFailure -and $actualReasons.Count -ne 0){
        throw "${Name}: unexpected shared-probe reasons: $($actualReasons -join ',')"
    }

    $flags=@($summary.Flags)
    if($ExpectedSharedFailure -and $flags -notcontains 'D3D9EX_SHARED_PROBE_FAILED'){
        throw "${Name}: D3D9EX_SHARED_PROBE_FAILED flag missing"
    }
    if(-not $ExpectedSharedFailure -and $flags -contains 'D3D9EX_SHARED_PROBE_FAILED'){
        throw "${Name}: unexpected D3D9EX_SHARED_PROBE_FAILED flag"
    }
}

$script:TestRoot = Join-Path ([IO.Path]::GetTempPath()) ('outrun-vr-analyzer-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force $script:TestRoot | Out-Null

try{
    Invoke-AnalyzerCase -Name 'legacy-marker' `
        -GameLog "VR direct transport: shared verification texture creation/upload failed`ndirect[frames=0,fallbacks=3,fenceTimeout=0]" `
        -DxvkLog "DXVK: v3.1.1" -HostLog "" `
        -ExpectedSharedFailure $true -ExpectedReasons @('LEGACY_VERIFY') `
        -ExpectedDirectFrames 0 -ExpectedFallbacks 3

    # Exact failure signature observed in the 2026-09-29 Quest3/VDXR DXVK run.
    Invoke-AnalyzerCase -Name 'dxvk-d3dkmt-runtime-regression' `
        -GameLog "keeping SBS/Desktop Duplication fallback`ndirect[frames=0,fallbacks=1504,fenceTimeout=0]" `
        -DxvkLog @"
DXVK: v3.1.1
DxvkMemoryAllocator::createImageResource: Failed to open shared D3DKMT handle
D3D9: Failed to write shared resource info for a texture
"@ `
        -HostLog "probeAck=0 directReady=0" `
        -ExpectedSharedFailure $true `
        -ExpectedReasons @('DXVK_OPEN_D3DKMT','DXVK_WRITE_SHARED_INFO') `
        -ExpectedDirectFrames 0 -ExpectedFallbacks 1504

    # A working direct path must not be classified as a legacy shared-probe
    # failure merely because it is a DXVK session.
    Invoke-AnalyzerCase -Name 'direct-frames-active' `
        -GameLog "direct[frames=240,fallbacks=1,fenceTimeout=0]" `
        -DxvkLog "DXVK: v3.1.1" -HostLog "directReady=1" `
        -ExpectedSharedFailure $false -ExpectedReasons @() `
        -ExpectedDirectFrames 240 -ExpectedFallbacks 1

    Write-Host 'OutRun VR session analyzer shared-probe regression tests: PASS'
} finally {
    if(Test-Path $script:TestRoot){
        Remove-Item $script:TestRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}
