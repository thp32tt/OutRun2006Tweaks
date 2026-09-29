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
        [Parameter(Mandatory=$true)][AllowEmptyString()][string]$HostLog,
        [string]$TestProfile='CORRECTNESS',
        [Parameter(Mandatory=$true)][bool]$ExpectedSharedFailure,
        [string[]]$ExpectedReasons=@(),
        [Parameter(Mandatory=$true)][int64]$ExpectedDirectFrames,
        [Parameter(Mandatory=$true)][int64]$ExpectedFallbacks,
        [string]$ExpectedStatus='',
        [bool]$ExpectedBridgeReady=$false,
        [bool]$ExpectedImportReady=$false,
        [bool]$ExpectedImportFailed=$false,
        [bool]$ExpectedDirectPathActive=$false,
        [Nullable[bool]]$ExpectedGenerationMatches=$null,
        [ValidateSet('MATCH','MISMATCH','INCOMPLETE')][string]$IdentityMode='MATCH',
        [ValidateSet('VERIFIED','UNVERIFIED','MISSING')][string]$PackageIntegrityMode='VERIFIED',
        [Nullable[bool]]$ExpectedBuildIdentityVerified=$true,
        [bool]$ExpectedBuildIdentityMismatch=$false,
        [bool]$ExpectedDirectEvidenceTrusted=$false,
        [string[]]$ExpectedDirectEvidenceBlockers=@(),
        [bool]$ExpectedPerformanceEvidenceReady=$false,
        [string[]]$ExpectedPerformanceEvidenceBlockers=@(),
        [int]$ExpectedHostPipelineWindows=0,
        [int]$ExpectedProducerPerfWindows=0,
        [int64]$ExpectedProducerFenceOk=0,
        [int64]$ExpectedProducerBudgetFallback=0,
        [Nullable[double]]$ExpectedCaptureMaxMs=$null,
        [Nullable[double]]$ExpectedEndFrameP95MaxMs=$null,
        [int]$ExpectedDrawFingerprintCount=0,
        [int64]$ExpectedDrawFingerprintDropped=0,
        [string]$ExpectedFirstDrawFingerprintScope=''
    )

    $caseRoot = Join-Path $script:TestRoot $Name
    New-Item -ItemType Directory -Force $caseRoot | Out-Null

    [ordered]@{
        SchemaVersion=3
        VariantId='E_DXVK_SAFE'
        Backend='dxvk-safe'
        TestProfile=$TestProfile
        SourceSha='fixture-source'
    } | ConvertTo-Json | Set-Content (Join-Path $caseRoot 'session_manifest.json') -Encoding UTF8

    if($IdentityMode -ne 'INCOMPLETE'){
        $fixtureBuildSha=if($IdentityMode -eq 'MISMATCH'){'different-build-sha'}else{'fixture-source'}
        [ordered]@{
            IntegrationSha=$fixtureBuildSha
            DevelopmentBranch='vr-dxvk-r71-disasm'
            RendererTarget='dxvk'
            DevelopmentStage='SAFE'
            LaunchBackend='dxvk-safe'
            BuildMatrixId='fixture-matrix'
        } | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $caseRoot 'BUILD_INPUTS.json') -Encoding UTF8
        [ordered]@{
            SchemaVersion=1
            DevelopmentBranch='vr-dxvk-r71-disasm'
            RendererTarget='dxvk'
            Stage='SAFE'
            ResolvedBackend='dxvk-safe'
            VariantId='E_DXVK_SAFE'
            SourceSha='fixture-source'
            PackageIntegrity=if($PackageIntegrityMode -eq 'MISSING'){$null}else{[ordered]@{
                Verified=($PackageIntegrityMode -eq 'VERIFIED')
                EntryCount=42
                ManifestSha256=('a'*64)
            }}
            PackageBuildInputs=[ordered]@{
                IntegrationSha=$fixtureBuildSha
                DevelopmentBranch='vr-dxvk-r71-disasm'
                RendererTarget='dxvk'
                DevelopmentStage='SAFE'
                LaunchBackend='dxvk-safe'
                BuildMatrixId='fixture-matrix'
            }
        } | ConvertTo-Json -Depth 6 | Set-Content (Join-Path $caseRoot 'VR_ONE_CLICK_PREFLIGHT.json') -Encoding UTF8
    }

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
    if($ExpectedStatus -and [string]$summary.Status -ne $ExpectedStatus){
        throw "${Name}: Status=$($summary.Status), expected $ExpectedStatus"
    }
    if([bool]$summary.DxvkHostBridgeReady -ne $ExpectedBridgeReady){
        throw "${Name}: DxvkHostBridgeReady=$($summary.DxvkHostBridgeReady), expected $ExpectedBridgeReady"
    }
    if([bool]$summary.DxvkHostImportReady -ne $ExpectedImportReady){
        throw "${Name}: DxvkHostImportReady=$($summary.DxvkHostImportReady), expected $ExpectedImportReady"
    }
    if([bool]$summary.DxvkHostImportFailed -ne $ExpectedImportFailed){
        throw "${Name}: DxvkHostImportFailed=$($summary.DxvkHostImportFailed), expected $ExpectedImportFailed"
    }
    if([bool]$summary.DxvkHostDirectPathActive -ne $ExpectedDirectPathActive){
        throw "${Name}: DxvkHostDirectPathActive=$($summary.DxvkHostDirectPathActive), expected $ExpectedDirectPathActive"
    }
    if([bool]$summary.BuildIdentityMismatch -ne $ExpectedBuildIdentityMismatch){
        throw "${Name}: BuildIdentityMismatch=$($summary.BuildIdentityMismatch), expected $ExpectedBuildIdentityMismatch"
    }
    if([bool]$summary.DxvkDirectEvidenceTrusted -ne $ExpectedDirectEvidenceTrusted){
        throw "${Name}: DxvkDirectEvidenceTrusted=$($summary.DxvkDirectEvidenceTrusted), expected $ExpectedDirectEvidenceTrusted"
    }
    if([bool]$summary.DxvkPerformanceEvidenceReady -ne $ExpectedPerformanceEvidenceReady){
        throw "${Name}: DxvkPerformanceEvidenceReady=$($summary.DxvkPerformanceEvidenceReady), expected $ExpectedPerformanceEvidenceReady"
    }
    $actualPerformanceBlockers=@($summary.DxvkPerformanceEvidenceBlockers)
    foreach($blocker in $ExpectedPerformanceEvidenceBlockers){
        if($actualPerformanceBlockers -notcontains $blocker){
            throw "${Name}: missing performance-evidence blocker $blocker; actual=$($actualPerformanceBlockers -join ',')"
        }
    }
    if([int]$summary.FrameBudget.HostPipelineWindowCount -ne $ExpectedHostPipelineWindows){
        throw "${Name}: HostPipelineWindowCount=$($summary.FrameBudget.HostPipelineWindowCount), expected $ExpectedHostPipelineWindows"
    }
    if([int]$summary.FrameBudget.GameProducer.WindowCount -ne $ExpectedProducerPerfWindows){
        throw "${Name}: Producer WindowCount=$($summary.FrameBudget.GameProducer.WindowCount), expected $ExpectedProducerPerfWindows"
    }
    if([int64]$summary.FrameBudget.GameProducer.ProducerFenceOk -ne $ExpectedProducerFenceOk){
        throw "${Name}: ProducerFenceOk=$($summary.FrameBudget.GameProducer.ProducerFenceOk), expected $ExpectedProducerFenceOk"
    }
    if([int64]$summary.FrameBudget.GameProducer.ProducerBudgetFallback -ne $ExpectedProducerBudgetFallback){
        throw "${Name}: ProducerBudgetFallback=$($summary.FrameBudget.GameProducer.ProducerBudgetFallback), expected $ExpectedProducerBudgetFallback"
    }
    if($null -ne $ExpectedCaptureMaxMs){
        if([math]::Abs([double]$summary.FrameBudget.CaptureMs.MaxObserved-[double]$ExpectedCaptureMaxMs) -gt 0.0001){
            throw "${Name}: Capture MaxObserved=$($summary.FrameBudget.CaptureMs.MaxObserved), expected $ExpectedCaptureMaxMs"
        }
    }
    if($null -ne $ExpectedEndFrameP95MaxMs){
        if([math]::Abs([double]$summary.FrameBudget.XrEndFrameMs.MaxP95Observed-[double]$ExpectedEndFrameP95MaxMs) -gt 0.0001){
            throw "${Name}: XrEndFrame P95 max=$($summary.FrameBudget.XrEndFrameMs.MaxP95Observed), expected $ExpectedEndFrameP95MaxMs"
        }
    }
    if([int]$summary.DrawFingerprintUniqueCount -ne $ExpectedDrawFingerprintCount){
        throw "${Name}: DrawFingerprintUniqueCount=$($summary.DrawFingerprintUniqueCount), expected $ExpectedDrawFingerprintCount"
    }
    if([int64]$summary.DrawFingerprintDropped -ne $ExpectedDrawFingerprintDropped){
        throw "${Name}: DrawFingerprintDropped=$($summary.DrawFingerprintDropped), expected $ExpectedDrawFingerprintDropped"
    }
    if($ExpectedFirstDrawFingerprintScope){
        if(@($summary.DrawFingerprints).Count -eq 0){
            throw "${Name}: expected draw fingerprint entries but none were parsed"
        }
        if([string]$summary.DrawFingerprints[0].Scope -ne $ExpectedFirstDrawFingerprintScope){
            throw "${Name}: first draw fingerprint scope=$($summary.DrawFingerprints[0].Scope), expected $ExpectedFirstDrawFingerprintScope"
        }
    }
    $actualDirectBlockers=@($summary.DxvkDirectEvidenceBlockers)
    foreach($blocker in $ExpectedDirectEvidenceBlockers){
        if($actualDirectBlockers -notcontains $blocker){
            throw "${Name}: missing direct-evidence blocker $blocker; actual=$($actualDirectBlockers -join ',')"
        }
    }
    if($null -ne $ExpectedBuildIdentityVerified){
        if([bool]$summary.BuildIdentityVerified -ne [bool]$ExpectedBuildIdentityVerified){
            throw "${Name}: BuildIdentityVerified=$($summary.BuildIdentityVerified), expected $ExpectedBuildIdentityVerified"
        }
    }
    if($null -ne $ExpectedGenerationMatches){
        if($null -eq $summary.DxvkHostGenerationMatches -or [bool]$summary.DxvkHostGenerationMatches -ne [bool]$ExpectedGenerationMatches){
            throw "${Name}: DxvkHostGenerationMatches=$($summary.DxvkHostGenerationMatches), expected $ExpectedGenerationMatches"
        }
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

    Invoke-AnalyzerCase -Name 'host-bridge-import-not-established' `
        -GameLog "keeping SBS/Desktop Duplication fallback`ndirect[frames=0,fallbacks=12,fenceTimeout=0]" `
        -DxvkLog "DXVK: v3.1.1" `
        -HostLog "DXVK host-owned shared-eye bridge ready: 2124x2284 x2, slots=4, generation=12345; Desktop Duplication remains menu/fail-open only." `
        -ExpectedSharedFailure $false -ExpectedReasons @() `
        -ExpectedDirectFrames 0 -ExpectedFallbacks 12 `
        -ExpectedStatus 'DXVK_HOST_OWNED_IMPORT_NOT_ESTABLISHED' `
        -ExpectedBridgeReady $true

    Invoke-AnalyzerCase -Name 'host-bridge-import-failed' `
        -GameLog "VR DXVK native transport: host-owned KMT eye import failed generation=12345 slot=2 leftHr=0x8876086C rightHr=0x80004005; SBS fallback remains available`ndirect[frames=0,fallbacks=12,fenceTimeout=0]" `
        -DxvkLog "DXVK: v3.1.1" `
        -HostLog "DXVK host-owned shared-eye bridge ready: 2124x2284 x2, slots=4, generation=12345; Desktop Duplication remains menu/fail-open only." `
        -ExpectedSharedFailure $false -ExpectedReasons @() `
        -ExpectedDirectFrames 0 -ExpectedFallbacks 12 `
        -ExpectedStatus 'DXVK_HOST_OWNED_IMPORT_FAILED' `
        -ExpectedBridgeReady $true -ExpectedImportFailed $true

    Invoke-AnalyzerCase -Name 'host-bridge-direct-active' `
        -GameLog "VR DXVK native transport: imported host-owned D3D11 KMT 4-slot eye ring 2124x2284 generation=12345; Desktop Duplication is no longer required for gameplay frames`nVR stereo: 4-slot direct GPU transport uses bounded post-Present completion; path=DXVK host-owned D3D11 KMT import sourceEye=3440x1440`ndirect[frames=240,fallbacks=1,fenceTimeout=0]" `
        -DxvkLog "DXVK: v3.1.1" `
        -HostLog "DXVK host-owned shared-eye bridge ready: 2124x2284 x2, slots=4, generation=12345; Desktop Duplication remains menu/fail-open only." `
        -ExpectedSharedFailure $false -ExpectedReasons @() `
        -ExpectedDirectFrames 240 -ExpectedFallbacks 1 `
        -ExpectedStatus 'DXVK_HOST_OWNED_DIRECTGPU_ACTIVE' `
        -ExpectedBridgeReady $true -ExpectedImportReady $true `
        -ExpectedDirectPathActive $true -ExpectedGenerationMatches $true `
        -ExpectedDirectEvidenceTrusted $true

    # Performance decisions require exact-build/package/direct-path trust plus
    # both host stage budgets and game producer windows in a PERFORMANCE run.
    Invoke-AnalyzerCase -Name 'dxvk-performance-evidence-ready' `
        -TestProfile 'PERFORMANCE' `
        -GameLog "VR DXVK native transport: imported host-owned D3D11 KMT 4-slot eye ring 2124x2284 generation=12345`nVR stereo: path=DXVK host-owned D3D11 KMT import`ndirect[frames=240,fallbacks=1,fenceTimeout=0]`nVR R32 PERF 5s: liveWvpCheck=1 liveReject=0 stateBlock[record=0,apply=0] batchWvp[ok=4,fail=0] safety[stateReadFail=0,forcedZero=0] direct[probeCacheHit=5,producerFenceOk=7,producerBudgetFallback=1,backpressure=2,pendingDrain=3,pendingBlock=4,pendingError=0] reset[rearm=0,fail=0]" `
        -DxvkLog "DXVK: v3.1.1" `
        -HostLog "DXVK host-owned shared-eye bridge ready: 2124x2284 x2, slots=4, generation=12345`n[R23 pipeline] captureMs=1 commitCopyMs=0.5 renderMs=2 xrWaitFrameMs=3 xrFrameIntervalMs=13.8 cadenceSerialWaitMs=0.2 gamePresentToConsumeMs=4 xrEndFrameMs=5 captureAvgMaxP95=1.0/3.0/2.0 commitAvgMaxP95=0.5/1.5/1.0 renderAvgMaxP95=2.0/4.0/3.0 endAvgMaxP95=5.0/8.0/7.0" `
        -ExpectedSharedFailure $false -ExpectedReasons @() `
        -ExpectedDirectFrames 240 -ExpectedFallbacks 1 `
        -ExpectedStatus 'DXVK_HOST_OWNED_DIRECTGPU_ACTIVE' `
        -ExpectedBridgeReady $true -ExpectedImportReady $true -ExpectedDirectPathActive $true `
        -ExpectedGenerationMatches $true -ExpectedDirectEvidenceTrusted $true `
        -ExpectedPerformanceEvidenceReady $true `
        -ExpectedHostPipelineWindows 1 -ExpectedProducerPerfWindows 1 `
        -ExpectedProducerFenceOk 7 -ExpectedProducerBudgetFallback 1 `
        -ExpectedCaptureMaxMs 3.0 -ExpectedEndFrameP95MaxMs 7.0

    # Direct frames alone are not promotion evidence when exact-build identity
    # is incomplete.
    Invoke-AnalyzerCase -Name 'direct-active-identity-incomplete' `
        -GameLog "VR DXVK native transport: imported host-owned D3D11 KMT 4-slot eye ring 2124x2284 generation=12345`nVR stereo: path=DXVK host-owned D3D11 KMT import`ndirect[frames=240,fallbacks=1,fenceTimeout=0]" `
        -DxvkLog "DXVK: v3.1.1" `
        -HostLog "DXVK host-owned shared-eye bridge ready: 2124x2284 x2, slots=4, generation=12345" `
        -ExpectedSharedFailure $false -ExpectedReasons @() `
        -ExpectedDirectFrames 240 -ExpectedFallbacks 1 `
        -ExpectedStatus 'DXVK_DIRECTGPU_EVIDENCE_UNTRUSTED' `
        -ExpectedBridgeReady $true -ExpectedImportReady $true -ExpectedDirectPathActive $true `
        -ExpectedGenerationMatches $true -IdentityMode 'INCOMPLETE' `
        -ExpectedBuildIdentityVerified $false `
        -ExpectedDirectEvidenceTrusted $false `
        -ExpectedDirectEvidenceBlockers @('BUILD_IDENTITY_UNVERIFIED','PACKAGE_INTEGRITY_EVIDENCE_MISSING')

    # Package integrity is a separate promotion prerequisite from source/backend
    # identity.
    Invoke-AnalyzerCase -Name 'direct-active-package-unverified' `
        -GameLog "VR DXVK native transport: imported host-owned D3D11 KMT 4-slot eye ring 2124x2284 generation=12345`nVR stereo: path=DXVK host-owned D3D11 KMT import`ndirect[frames=240,fallbacks=1,fenceTimeout=0]" `
        -DxvkLog "DXVK: v3.1.1" `
        -HostLog "DXVK host-owned shared-eye bridge ready: 2124x2284 x2, slots=4, generation=12345" `
        -ExpectedSharedFailure $false -ExpectedReasons @() `
        -ExpectedDirectFrames 240 -ExpectedFallbacks 1 `
        -ExpectedStatus 'DXVK_DIRECTGPU_EVIDENCE_UNTRUSTED' `
        -ExpectedBridgeReady $true -ExpectedImportReady $true -ExpectedDirectPathActive $true `
        -ExpectedGenerationMatches $true -PackageIntegrityMode 'UNVERIFIED' `
        -ExpectedDirectEvidenceTrusted $false `
        -ExpectedDirectEvidenceBlockers @('PACKAGE_INTEGRITY_NOT_VERIFIED')

    # Host and game must refer to the same bridge generation before direct-frame
    # telemetry is trusted.
    Invoke-AnalyzerCase -Name 'direct-active-generation-mismatch' `
        -GameLog "VR DXVK native transport: imported host-owned D3D11 KMT 4-slot eye ring 2124x2284 generation=54321`nVR stereo: path=DXVK host-owned D3D11 KMT import`ndirect[frames=240,fallbacks=1,fenceTimeout=0]" `
        -DxvkLog "DXVK: v3.1.1" `
        -HostLog "DXVK host-owned shared-eye bridge ready: 2124x2284 x2, slots=4, generation=12345" `
        -ExpectedSharedFailure $false -ExpectedReasons @() `
        -ExpectedDirectFrames 240 -ExpectedFallbacks 1 `
        -ExpectedStatus 'DXVK_HOST_GENERATION_MISMATCH' `
        -ExpectedBridgeReady $true -ExpectedImportReady $true -ExpectedDirectPathActive $true `
        -ExpectedGenerationMatches $false `
        -ExpectedDirectEvidenceTrusted $false `
        -ExpectedDirectEvidenceBlockers @('HOST_IMPORT_GENERATION_MISMATCH')

    # Even apparently successful DirectGPU telemetry must fail closed when
    # session/build/preflight source identity disagrees.
    Invoke-AnalyzerCase -Name 'direct-active-build-identity-mismatch' `
        -GameLog "VR DXVK native transport: imported host-owned D3D11 KMT 4-slot eye ring 2124x2284 generation=12345; Desktop Duplication is no longer required for gameplay frames`nVR stereo: path=DXVK host-owned D3D11 KMT import`ndirect[frames=240,fallbacks=1,fenceTimeout=0]" `
        -DxvkLog "DXVK: v3.1.1" `
        -HostLog "DXVK host-owned shared-eye bridge ready: 2124x2284 x2, slots=4, generation=12345; Desktop Duplication remains menu/fail-open only." `
        -ExpectedSharedFailure $false -ExpectedReasons @() `
        -ExpectedDirectFrames 240 -ExpectedFallbacks 1 `
        -ExpectedStatus 'DXVK_BUILD_IDENTITY_MISMATCH' `
        -ExpectedBridgeReady $true -ExpectedImportReady $true `
        -ExpectedDirectPathActive $true -ExpectedGenerationMatches $true `
        -IdentityMode 'MISMATCH' -ExpectedBuildIdentityVerified $false `
        -ExpectedBuildIdentityMismatch $true `
        -ExpectedDirectEvidenceTrusted $false `
        -ExpectedDirectEvidenceBlockers @('BUILD_IDENTITY_MISMATCH')

    # Missing optional package identity reduces confidence but is not fabricated
    # into a mismatch; older/manual bundles remain analyzable.
    Invoke-AnalyzerCase -Name 'identity-incomplete-no-false-mismatch' `
        -GameLog "direct[frames=0,fallbacks=2,fenceTimeout=0]" `
        -DxvkLog "DXVK: v3.1.1" -HostLog "" `
        -ExpectedSharedFailure $false -ExpectedReasons @() `
        -ExpectedDirectFrames 0 -ExpectedFallbacks 2 `
        -ExpectedStatus 'DIRECT_GPU_UNAVAILABLE' `
        -IdentityMode 'INCOMPLETE' -ExpectedBuildIdentityVerified $false `
        -ExpectedBuildIdentityMismatch $false

    # R71 bounded semantic draw fingerprints are parsed without granting any
    # render ownership. The runtime emits first-seen unique fingerprints only.
    Invoke-AnalyzerCase -Name 'semantic-draw-fingerprint-aggregation' `
        -GameLog "direct[frames=0,fallbacks=2,fenceTimeout=0]`nVR DRAW FP: id=1111222233334444 scope=SCREEN_HUD owner=NONE api=DIP prim=4 primCount=2 arg0=4 arg1=0 arg2=0 vsHash=aaaaaaaaaaaaaaaa psHash=bbbbbbbbbbbbbbbb vsBytes=128 psBytes=96 exact=1 marker=0`nVR DRAW FP: id=5555666677778888 scope=SCREEN_OVERLAY_2D owner=NONE api=DPUP prim=5 primCount=2 arg0=24 arg1=0 arg2=0 vsHash=0000000000000000 psHash=cccccccccccccccc vsBytes=0 psBytes=64 exact=0 marker=0`nVR R30.9: drawFp[unique=2,hits=7,dropped=1]" `
        -DxvkLog "DXVK: v3.1.1" -HostLog "" `
        -ExpectedSharedFailure $false -ExpectedReasons @() `
        -ExpectedDirectFrames 0 -ExpectedFallbacks 2 `
        -ExpectedStatus 'DIRECT_GPU_UNAVAILABLE' `
        -ExpectedDrawFingerprintCount 2 -ExpectedDrawFingerprintDropped 1 `
        -ExpectedFirstDrawFingerprintScope 'SCREEN_HUD'

    # Existing game/host telemetry is promoted into a structured common
    # frame-budget summary without changing runtime instrumentation.
    Invoke-AnalyzerCase -Name 'dxvk-frame-budget-aggregation' `
        -GameLog "direct[frames=0,fallbacks=2,fenceTimeout=0]`nVR R32 PERF 5s: liveWvpCheck=1 liveReject=0 stateBlock[record=0,apply=0] batchWvp[ok=4,fail=0] safety[stateReadFail=0,forcedZero=0] direct[probeCacheHit=5,producerFenceOk=7,producerBudgetFallback=1,backpressure=2,pendingDrain=3,pendingBlock=4,pendingError=0] reset[rearm=0,fail=0]`nVR R32 PERF 5s: liveWvpCheck=2 liveReject=0 stateBlock[record=0,apply=0] batchWvp[ok=5,fail=0] safety[stateReadFail=0,forcedZero=0] direct[probeCacheHit=6,producerFenceOk=11,producerBudgetFallback=2,backpressure=5,pendingDrain=7,pendingBlock=8,pendingError=1] reset[rearm=0,fail=0]" `
        -DxvkLog "DXVK: v3.1.1" `
        -HostLog "[R23 pipeline] captureMs=1 commitCopyMs=0.5 renderMs=2 xrWaitFrameMs=3 xrFrameIntervalMs=11.1 cadenceSerialWaitMs=0.2 gamePresentToConsumeMs=4 xrEndFrameMs=5 captureAvgMaxP95=1.0/3.0/2.0 commitAvgMaxP95=0.5/1.5/1.0 renderAvgMaxP95=2.0/4.0/3.0 endAvgMaxP95=5.0/8.0/7.0`n[R23 pipeline] captureMs=2 commitCopyMs=0.7 renderMs=3 xrWaitFrameMs=5 xrFrameIntervalMs=22.2 cadenceSerialWaitMs=0.4 gamePresentToConsumeMs=6 xrEndFrameMs=7 captureAvgMaxP95=2.0/5.0/4.0 commitAvgMaxP95=0.7/2.0/1.4 renderAvgMaxP95=3.0/6.0/5.0 endAvgMaxP95=7.0/10.0/9.0" `
        -ExpectedSharedFailure $false -ExpectedReasons @() `
        -ExpectedDirectFrames 0 -ExpectedFallbacks 2 `
        -ExpectedStatus 'DIRECT_GPU_UNAVAILABLE' `
        -ExpectedHostPipelineWindows 2 -ExpectedProducerPerfWindows 2 `
        -ExpectedProducerFenceOk 18 -ExpectedProducerBudgetFallback 3 `
        -ExpectedCaptureMaxMs 5.0 -ExpectedEndFrameP95MaxMs 9.0

    $queuePath = Join-Path $PSScriptRoot '..\docs\VR_WORK_QUEUE.json'
    $workQueue = Get-Content $queuePath -Raw | ConvertFrom-Json
    $perfItems = @($workQueue.items | Where-Object { $_.id -eq 'VR-PERF-COMMON-001' })
    if($perfItems.Count -ne 1){ throw "VR-PERF-COMMON-001 queue item must be unique" }
    $perfItem = $perfItems[0]
    if([string]$perfItem.status -ne 'NEED_HMD_TEST'){
        throw "VR-PERF-COMMON-001 status=$($perfItem.status), expected NEED_HMD_TEST"
    }
    if([string]$perfItem.dxvkPerformanceEvidenceGate -ne 'DxvkPerformanceEvidenceReady'){
        throw "VR-PERF-COMMON-001 must name DxvkPerformanceEvidenceReady as its DXVK decision gate"
    }
    if([string]$perfItem.runtimeValidation -ne 'UNTESTED'){
        throw "VR-PERF-COMMON-001 runtimeValidation=$($perfItem.runtimeValidation), expected UNTESTED"
    }

    Write-Host 'OutRun VR session analyzer shared-probe/performance-evidence regression tests: PASS'
} finally {
    if(Test-Path $script:TestRoot){
        Remove-Item $script:TestRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}
