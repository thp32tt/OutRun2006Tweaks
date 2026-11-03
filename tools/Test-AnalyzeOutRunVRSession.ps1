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
        [string]$ExpectedHostDominantBudgetStage='',
        [Nullable[double]]$ExpectedHostDominantBudgetP95Ms=$null,
        [int]$ExpectedHostPipelineWindows=0,
        [int]$ExpectedProducerPerfWindows=0,
        [int64]$ExpectedProducerFenceOk=0,
        [int64]$ExpectedProducerBudgetFallback=0,
        [Nullable[double]]$ExpectedCaptureMaxMs=$null,
        [Nullable[double]]$ExpectedEndFrameP95MaxMs=$null,
        [int]$ExpectedDrawFingerprintCount=0,
        [int64]$ExpectedDrawFingerprintDropped=0,
        [string]$ExpectedFirstDrawFingerprintScope='',
        [bool]$ExpectedRankProjectedMarkerDrawEvidence=$false,
        [int]$ExpectedRankProjectedMarkerDrawFingerprintCount=0,
        [Nullable[int]]$ExpectedMenuCadenceWindows=$null,
        [Nullable[int]]$ExpectedGameplayCadenceWindows=$null,
        [Nullable[int]]$ExpectedMixedCadenceWindows=$null,
        [Nullable[double]]$ExpectedMenuCadenceHz=$null,
        [Nullable[double]]$ExpectedGameplayCadenceHz=$null,
        [Nullable[bool]]$ExpectedGameplayCadenceDegraded=$null,
        [Nullable[int64]]$ExpectedGameplayFreshProjectionCount=$null,
        [Nullable[int64]]$ExpectedGameplayCachedProjectionCount=$null,
        [Nullable[double]]$ExpectedGameplayFreshProjectionFraction=$null,
        [Nullable[int]]$ExpectedGameplayCadenceEvidenceWindows=$null,
        [Nullable[int64]]$ExpectedGameplayXrFrameCount=$null,
        [Nullable[double]]$ExpectedGameplayFreshProjectionHzEstimate=$null,
        [Nullable[double]]$ExpectedGameplayCachedProjectionHzEstimate=$null,
        [Nullable[int64]]$ExpectedGameplayDirectSubmitCount=$null,
        [Nullable[int64]]$ExpectedGameplayCachedProjectionSubmitCount=$null,
        [Nullable[double]]$ExpectedGameplayDirectSubmitFraction=$null
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
    if([string]$summary.DxvkHostDominantBudgetStage -ne $ExpectedHostDominantBudgetStage){
        throw "${Name}: DxvkHostDominantBudgetStage=$($summary.DxvkHostDominantBudgetStage), expected $ExpectedHostDominantBudgetStage"
    }
    if($null -ne $ExpectedHostDominantBudgetP95Ms){
        if($null -eq $summary.DxvkHostDominantBudgetP95Ms -or
           [math]::Abs([double]$summary.DxvkHostDominantBudgetP95Ms-[double]$ExpectedHostDominantBudgetP95Ms) -gt 0.0001){
            throw "${Name}: DxvkHostDominantBudgetP95Ms=$($summary.DxvkHostDominantBudgetP95Ms), expected $ExpectedHostDominantBudgetP95Ms"
        }
    } elseif($null -ne $summary.DxvkHostDominantBudgetP95Ms){
        throw "${Name}: unexpected DxvkHostDominantBudgetP95Ms=$($summary.DxvkHostDominantBudgetP95Ms)"
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
    if([bool]$summary.RankProjectedMarkerDrawEvidenceAvailable -ne $ExpectedRankProjectedMarkerDrawEvidence){
        throw "${Name}: RankProjectedMarkerDrawEvidenceAvailable=$($summary.RankProjectedMarkerDrawEvidenceAvailable), expected $ExpectedRankProjectedMarkerDrawEvidence"
    }
    if([int]$summary.RankProjectedMarkerDrawFingerprintCount -ne $ExpectedRankProjectedMarkerDrawFingerprintCount){
        throw "${Name}: RankProjectedMarkerDrawFingerprintCount=$($summary.RankProjectedMarkerDrawFingerprintCount), expected $ExpectedRankProjectedMarkerDrawFingerprintCount"
    }
    if($null -ne $ExpectedMenuCadenceWindows -and
       [int]$summary.PresentationCadence.Menu.WindowCount -ne [int]$ExpectedMenuCadenceWindows){
        throw "${Name}: Menu cadence windows=$($summary.PresentationCadence.Menu.WindowCount), expected $ExpectedMenuCadenceWindows"
    }
    if($null -ne $ExpectedGameplayCadenceWindows -and
       [int]$summary.PresentationCadence.Gameplay.WindowCount -ne [int]$ExpectedGameplayCadenceWindows){
        throw "${Name}: Gameplay cadence windows=$($summary.PresentationCadence.Gameplay.WindowCount), expected $ExpectedGameplayCadenceWindows"
    }
    if($null -ne $ExpectedMixedCadenceWindows -and
       [int]$summary.PresentationCadence.MixedOrUnknown.WindowCount -ne [int]$ExpectedMixedCadenceWindows){
        throw "${Name}: Mixed cadence windows=$($summary.PresentationCadence.MixedOrUnknown.WindowCount), expected $ExpectedMixedCadenceWindows"
    }
    if($null -ne $ExpectedMenuCadenceHz){
        if($null -eq $summary.PresentationCadence.Menu.ApproxHz -or
           [math]::Abs([double]$summary.PresentationCadence.Menu.ApproxHz-[double]$ExpectedMenuCadenceHz) -gt 0.05){
            throw "${Name}: Menu cadence Hz=$($summary.PresentationCadence.Menu.ApproxHz), expected $ExpectedMenuCadenceHz"
        }
    }
    if($null -ne $ExpectedGameplayCadenceHz){
        if($null -eq $summary.PresentationCadence.Gameplay.ApproxHz -or
           [math]::Abs([double]$summary.PresentationCadence.Gameplay.ApproxHz-[double]$ExpectedGameplayCadenceHz) -gt 0.05){
            throw "${Name}: Gameplay cadence Hz=$($summary.PresentationCadence.Gameplay.ApproxHz), expected $ExpectedGameplayCadenceHz"
        }
    }
    if($null -ne $ExpectedGameplayCadenceDegraded -and
       [bool]$summary.DxvkGameplayCadenceDegraded -ne [bool]$ExpectedGameplayCadenceDegraded){
        throw "${Name}: DxvkGameplayCadenceDegraded=$($summary.DxvkGameplayCadenceDegraded), expected $ExpectedGameplayCadenceDegraded"
    }
    if($null -ne $ExpectedGameplayFreshProjectionCount -and [int64]$summary.PresentationCadence.Gameplay.FreshProjectionCount -ne [int64]$ExpectedGameplayFreshProjectionCount){throw "${Name}: Gameplay FreshProjectionCount mismatch"}
    if($null -ne $ExpectedGameplayCachedProjectionCount -and [int64]$summary.PresentationCadence.Gameplay.CachedProjectionCount -ne [int64]$ExpectedGameplayCachedProjectionCount){throw "${Name}: Gameplay CachedProjectionCount mismatch"}
    if($null -ne $ExpectedGameplayFreshProjectionFraction -and ($null -eq $summary.PresentationCadence.Gameplay.FreshProjectionFraction -or [math]::Abs([double]$summary.PresentationCadence.Gameplay.FreshProjectionFraction-[double]$ExpectedGameplayFreshProjectionFraction) -gt 0.0001)){throw "${Name}: Gameplay FreshProjectionFraction mismatch"}
    if($null -ne $ExpectedGameplayCadenceEvidenceWindows -and [int]$summary.PresentationCadence.Gameplay.CadenceEvidenceWindowCount -ne [int]$ExpectedGameplayCadenceEvidenceWindows){throw "${Name}: Gameplay CadenceEvidenceWindowCount mismatch"}
    if($null -ne $ExpectedGameplayXrFrameCount -and [int64]$summary.PresentationCadence.Gameplay.XrFrameCount -ne [int64]$ExpectedGameplayXrFrameCount){throw "${Name}: Gameplay XrFrameCount mismatch"}
    if($null -ne $ExpectedGameplayFreshProjectionHzEstimate -and ($null -eq $summary.PresentationCadence.Gameplay.FreshProjectionHzEstimate -or [math]::Abs([double]$summary.PresentationCadence.Gameplay.FreshProjectionHzEstimate-[double]$ExpectedGameplayFreshProjectionHzEstimate) -gt 0.05)){throw "${Name}: Gameplay FreshProjectionHzEstimate mismatch"}
    if($null -ne $ExpectedGameplayCachedProjectionHzEstimate -and ($null -eq $summary.PresentationCadence.Gameplay.CachedProjectionHzEstimate -or [math]::Abs([double]$summary.PresentationCadence.Gameplay.CachedProjectionHzEstimate-[double]$ExpectedGameplayCachedProjectionHzEstimate) -gt 0.05)){throw "${Name}: Gameplay CachedProjectionHzEstimate mismatch"}
    if($null -ne $ExpectedGameplayDirectSubmitCount -and [int64]$summary.PresentationCadence.Gameplay.DirectSubmitCount -ne [int64]$ExpectedGameplayDirectSubmitCount){throw "${Name}: Gameplay DirectSubmitCount mismatch"}
    if($null -ne $ExpectedGameplayCachedProjectionSubmitCount -and [int64]$summary.PresentationCadence.Gameplay.CachedProjectionSubmitCount -ne [int64]$ExpectedGameplayCachedProjectionSubmitCount){throw "${Name}: Gameplay CachedProjectionSubmitCount mismatch"}
    if($null -ne $ExpectedGameplayDirectSubmitFraction -and ($null -eq $summary.PresentationCadence.Gameplay.DirectSubmitFraction -or [math]::Abs([double]$summary.PresentationCadence.Gameplay.DirectSubmitFraction-[double]$ExpectedGameplayDirectSubmitFraction) -gt 0.0001)){throw "${Name}: Gameplay DirectSubmitFraction mismatch"}
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
        -ExpectedHostDominantBudgetStage 'XR_END_FRAME' -ExpectedHostDominantBudgetP95Ms 7.0 `
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
        -GameLog "direct[frames=0,fallbacks=2,fenceTimeout=0]`nVR DRAW FP: id=1111222233334444 scope=SCREEN_HUD owner=NONE api=DIP prim=4 primCount=2 arg0=4 arg1=0 arg2=0 vsHash=aaaaaaaaaaaaaaaa psHash=bbbbbbbbbbbbbbbb vsBytes=128 psBytes=96 exact=1 marker=0`nVR DRAW FP: id=5555666677778888 scope=SCREEN_OVERLAY_2D owner=NONE api=DPUP prim=5 primCount=2 arg0=24 arg1=0 arg2=0 vsHash=0000000000000000 psHash=cccccccccccccccc vsBytes=0 psBytes=64 exact=0 marker=0`nVR DRAW FP: id=9999aaaabbbbcccc scope=PROJECTED_WORLD_MARKER_2D owner=NONE api=DIP prim=4 primCount=2 arg0=4 arg1=0 arg2=0 vsHash=dddddddddddddddd psHash=eeeeeeeeeeeeeeee vsBytes=128 psBytes=96 exact=1 marker=1`nVR R30.9: drawFp[unique=3,hits=8,dropped=1]" `
        -DxvkLog "DXVK: v3.1.1" -HostLog "" `
        -ExpectedSharedFailure $false -ExpectedReasons @() `
        -ExpectedDirectFrames 0 -ExpectedFallbacks 2 `
        -ExpectedStatus 'DIRECT_GPU_UNAVAILABLE' `
        -ExpectedDrawFingerprintCount 3 -ExpectedDrawFingerprintDropped 1 `
        -ExpectedFirstDrawFingerprintScope 'SCREEN_HUD' `
        -ExpectedRankProjectedMarkerDrawEvidence $true `
        -ExpectedRankProjectedMarkerDrawFingerprintCount 1

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

    # 2026-09-30 HMD evidence showed that one aggregate XR-Hz value can hide
    # healthy ~90 Hz menu windows and degraded ~30-33 Hz gameplay windows.
    # Pure phase windows must be kept separate; a transition window is excluded
    # from both phase averages instead of contaminating either side.
    Invoke-AnalyzerCase -Name 'dxvk-menu-gameplay-cadence-split' `
        -GameLog "direct[frames=2359,fallbacks=0,fenceTimeout=0]" `
        -DxvkLog "DXVK: v3.1.1" `
        -HostLog @"
[R23 pipeline] requestedLayer=menu-local-fixed-projection-cached actualFinal=menu-local-fixed-projection-cached captureMs=0.1 commitCopyMs=0.0 renderMs=0.1 xrWaitFrameMs=9.0 xrFrameIntervalMs=11.1 cadenceSerialWaitMs=0.0 gamePresentToConsumeMs=1.0 xrEndFrameMs=1.0 displayPeriodMs=11.1 intervalFrames=450 actualSubmits={menu-local-fixed-projection-cached:450} rejectCounts={none} captureAvgMaxP95=0.1/0.2/0.2 commitAvgMaxP95=0.0/0.0/0.0 renderAvgMaxP95=0.1/0.2/0.2 endAvgMaxP95=1.0/1.5/1.2 cadence={mode:auto,xr:450,req:0,fresh:0,cached:450,other:0,noLayer:0}
[R23 pipeline] requestedLayer=projection-cached actualFinal=projection-direct-r32-fast captureMs=0.0 commitCopyMs=0.001 renderMs=0.01 xrWaitFrameMs=9.0 xrFrameIntervalMs=30.0 cadenceSerialWaitMs=0.0 gamePresentToConsumeMs=29.0 xrEndFrameMs=20.0 displayPeriodMs=11.1 intervalFrames=166 actualSubmits={projection-direct-r32-fast:166} rejectCounts={none} captureAvgMaxP95=0.0/0.1/0.1 commitAvgMaxP95=0.001/0.002/0.002 renderAvgMaxP95=0.01/0.02/0.02 endAvgMaxP95=20.0/24.0/22.0 cadence={mode:auto,xr:166,req:0,fresh:100,cached:66,other:0,noLayer:0}
[R23 pipeline] requestedLayer=projection-cached actualFinal=projection-direct-r32-fast captureMs=0.0 commitCopyMs=0.001 renderMs=0.01 xrWaitFrameMs=9.2 xrFrameIntervalMs=31.0 cadenceSerialWaitMs=0.0 gamePresentToConsumeMs=30.0 xrEndFrameMs=22.0 displayPeriodMs=11.1 intervalFrames=161 actualSubmits={projection-direct-r32-fast:161} rejectCounts={none} captureAvgMaxP95=0.0/0.1/0.1 commitAvgMaxP95=0.001/0.002/0.002 renderAvgMaxP95=0.01/0.02/0.02 endAvgMaxP95=22.0/26.0/24.0 cadence={mode:auto,xr:161,req:0,fresh:120,cached:41,other:0,noLayer:0}
[R23 pipeline] requestedLayer=projection-cached actualFinal=projection-cached captureMs=0.0 commitCopyMs=0.001 renderMs=0.01 xrWaitFrameMs=9.1 xrFrameIntervalMs=20.0 cadenceSerialWaitMs=0.0 gamePresentToConsumeMs=15.0 xrEndFrameMs=10.0 displayPeriodMs=11.1 intervalFrames=250 actualSubmits={menu-local-fixed-projection-cached:100,projection-cached:150} rejectCounts={none} captureAvgMaxP95=0.0/0.1/0.1 commitAvgMaxP95=0.001/0.002/0.002 renderAvgMaxP95=0.01/0.02/0.02 endAvgMaxP95=10.0/12.0/11.0 cadence={mode:auto,xr:250,req:0,fresh:100,cached:150,other:0,noLayer:0}
"@ `
        -ExpectedSharedFailure $false -ExpectedReasons @() `
        -ExpectedDirectFrames 2359 -ExpectedFallbacks 0 `
        -ExpectedHostPipelineWindows 4 `
        -ExpectedMenuCadenceWindows 1 -ExpectedGameplayCadenceWindows 2 `
        -ExpectedMixedCadenceWindows 1 `
        -ExpectedMenuCadenceHz (1000.0/11.1) `
        -ExpectedGameplayCadenceHz (1000.0/30.5) `
        -ExpectedGameplayCadenceDegraded $true `
        -ExpectedGameplayFreshProjectionCount 220 `
        -ExpectedGameplayCachedProjectionCount 107 `
        -ExpectedGameplayFreshProjectionFraction (220.0/327.0) `
        -ExpectedGameplayCadenceEvidenceWindows 2 `
        -ExpectedGameplayXrFrameCount 327 `
        -ExpectedGameplayFreshProjectionHzEstimate ((1000.0/30.5)*(220.0/327.0)) `
        -ExpectedGameplayCachedProjectionHzEstimate ((1000.0/30.5)*(107.0/327.0)) `
        -ExpectedGameplayDirectSubmitCount 327 `
        -ExpectedGameplayCachedProjectionSubmitCount 0 `
        -ExpectedGameplayDirectSubmitFraction 1.0

    # A syntactically present but incomplete cadence block must not be treated
    # as fresh/cached decision evidence. Keep the gameplay window for phase
    # timing, but exclude its partial counters from cadence-derived rates.
    Invoke-AnalyzerCase -Name 'dxvk-incomplete-cadence-fail-closed' `
        -GameLog "direct[frames=200,fallbacks=0,fenceTimeout=0]" `
        -DxvkLog "DXVK: v3.1.1" `
        -HostLog @"
[R23 pipeline] requestedLayer=projection-cached actualFinal=projection-direct-r32-fast captureMs=0.0 commitCopyMs=0.001 renderMs=0.01 xrWaitFrameMs=9.0 xrFrameIntervalMs=20.0 cadenceSerialWaitMs=0.0 gamePresentToConsumeMs=18.0 xrEndFrameMs=10.0 displayPeriodMs=11.1 intervalFrames=100 actualSubmits={projection-direct-r32-fast:100} rejectCounts={none} captureAvgMaxP95=0.0/0.1/0.1 commitAvgMaxP95=0.001/0.002/0.002 renderAvgMaxP95=0.01/0.02/0.02 endAvgMaxP95=10.0/12.0/11.0 cadence={mode:auto, xr:100, req:0, fresh:60, cached:40, other:0, noLayer:0}
[R23 pipeline] requestedLayer=projection-cached actualFinal=projection-direct-r32-fast captureMs=0.0 commitCopyMs=0.001 renderMs=0.01 xrWaitFrameMs=9.0 xrFrameIntervalMs=20.0 cadenceSerialWaitMs=0.0 gamePresentToConsumeMs=18.0 xrEndFrameMs=10.0 displayPeriodMs=11.1 intervalFrames=100 actualSubmits={projection-direct-r32-fast:100} rejectCounts={none} captureAvgMaxP95=0.0/0.1/0.1 commitAvgMaxP95=0.001/0.002/0.002 renderAvgMaxP95=0.01/0.02/0.02 endAvgMaxP95=10.0/12.0/11.0 cadence={mode:auto,xr:100,req:0,fresh:100,other:0,noLayer:0}
"@ `
        -ExpectedSharedFailure $false -ExpectedReasons @() `
        -ExpectedDirectFrames 200 -ExpectedFallbacks 0 `
        -ExpectedHostPipelineWindows 2 `
        -ExpectedGameplayCadenceWindows 2 `
        -ExpectedGameplayCadenceHz 50.0 `
        -ExpectedGameplayCadenceDegraded $true `
        -ExpectedGameplayFreshProjectionCount 60 `
        -ExpectedGameplayCachedProjectionCount 40 `
        -ExpectedGameplayFreshProjectionFraction 0.6 `
        -ExpectedGameplayCadenceEvidenceWindows 1 `
        -ExpectedGameplayXrFrameCount 100 `
        -ExpectedGameplayFreshProjectionHzEstimate 30.0 `
        -ExpectedGameplayCachedProjectionHzEstimate 20.0 `
        -ExpectedGameplayDirectSubmitCount 200 `
        -ExpectedGameplayCachedProjectionSubmitCount 0 `
        -ExpectedGameplayDirectSubmitFraction 1.0

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

    $l2Items = @($workQueue.items | Where-Object { $_.id -eq 'L2-PERF-001' })
    if($l2Items.Count -ne 1){ throw "L2-PERF-001 queue item must be unique" }
    $l2Item = $l2Items[0]
    if([string]$l2Item.status -ne 'NEED_HMD_TEST'){
        throw "L2-PERF-001 status=$($l2Item.status), expected NEED_HMD_TEST"
    }
    if([string]$l2Item.dxvkPerformanceEvidenceGate -ne 'DxvkPerformanceEvidenceReady'){
        throw "L2-PERF-001 must retain DxvkPerformanceEvidenceReady as the optimization evidence gate"
    }
    if([string]$l2Item.dxvkHostDominantBudgetField -ne 'DxvkHostDominantBudgetStage'){
        throw "L2-PERF-001 must name DxvkHostDominantBudgetStage as its host ranking field"
    }
    if([string]$l2Item.runtimeValidation -ne 'UNTESTED'){
        throw "L2-PERF-001 runtimeValidation=$($l2Item.runtimeValidation), expected UNTESTED"
    }

    Write-Host 'OutRun VR session analyzer shared-probe/performance-evidence regression tests: PASS'
} finally {
    if(Test-Path $script:TestRoot){
        Remove-Item $script:TestRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}
