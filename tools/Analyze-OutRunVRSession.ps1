param(
    [Parameter(Mandatory=$true)]
    [string]$SessionDir
)

$ErrorActionPreference='Stop'
if(!(Test-Path $SessionDir)){throw "Session directory not found: $SessionDir"}

function Read-AllText([string]$name){
    $p=Join-Path $SessionDir $name
    if(Test-Path $p){return (Get-Content $p -Raw -ErrorAction SilentlyContinue)}
    return ''
}

function Get-LastRegexMatch([string]$text,[string]$pattern){
    $matches=[regex]::Matches($text,$pattern,[Text.RegularExpressions.RegexOptions]::IgnoreCase)
    if($matches.Count -eq 0){return $null}
    return $matches[$matches.Count-1]
}

function Read-OptionalJson([string]$name){
    $path=Join-Path $SessionDir $name
    if(!(Test-Path $path -PathType Leaf)){return $null}
    try{return Get-Content $path -Raw|ConvertFrom-Json}catch{return $null}
}

function Convert-InvariantDouble([string]$value){
    return [double]::Parse($value,[Globalization.CultureInfo]::InvariantCulture)
}

function Get-HostTripletSummary([string]$text,[string]$name){
    $matches=[regex]::Matches($text,([regex]::Escape($name)+'=([0-9]+(?:\.[0-9]+)?)/([0-9]+(?:\.[0-9]+)?)/([0-9]+(?:\.[0-9]+)?)'))
    if($matches.Count -eq 0){
        return [pscustomobject]@{WindowCount=0;AverageOfWindowAverages=$null;MaxObserved=$null;MaxP95Observed=$null}
    }
    $averages=@()
    $maxima=@()
    $p95s=@()
    foreach($match in $matches){
        $averages+=Convert-InvariantDouble $match.Groups[1].Value
        $maxima+=Convert-InvariantDouble $match.Groups[2].Value
        $p95s+=Convert-InvariantDouble $match.Groups[3].Value
    }
    return [pscustomobject]@{
        WindowCount=$matches.Count
        AverageOfWindowAverages=($averages|Measure-Object -Average).Average
        MaxObserved=($maxima|Measure-Object -Maximum).Maximum
        MaxP95Observed=($p95s|Measure-Object -Maximum).Maximum
    }
}

function Get-HostScalarSummary([string]$text,[string]$name){
    $values=@()
    foreach($match in [regex]::Matches($text,([regex]::Escape($name)+'=([0-9]+(?:\.[0-9]+)?)'))){
        $values+=Convert-InvariantDouble $match.Groups[1].Value
    }
    if($values.Count -eq 0){
        return [pscustomobject]@{SampleCount=0;Average=$null;Maximum=$null}
    }
    return [pscustomobject]@{
        SampleCount=$values.Count
        Average=($values|Measure-Object -Average).Average
        Maximum=($values|Measure-Object -Maximum).Maximum
    }
}

function Get-R23LineScalar([string]$line,[string]$name){
    $match=[regex]::Match(
        $line,
        ([regex]::Escape($name)+'=(-?[0-9]+(?:\.[0-9]+)?)'),
        [Text.RegularExpressions.RegexOptions]::IgnoreCase)
    if(-not $match.Success){return $null}
    return Convert-InvariantDouble $match.Groups[1].Value
}

function Get-R23MetricSummary([object[]]$values){
    $numeric=@($values | Where-Object { $null -ne $_ } | ForEach-Object { [double]$_ })
    if($numeric.Count -eq 0){
        return [pscustomobject]@{
            SampleCount=0
            Average=$null
            Minimum=$null
            Maximum=$null
        }
    }
    return [pscustomobject]@{
        SampleCount=$numeric.Count
        Average=($numeric|Measure-Object -Average).Average
        Minimum=($numeric|Measure-Object -Minimum).Minimum
        Maximum=($numeric|Measure-Object -Maximum).Maximum
    }
}

function Get-R23PhaseMetricSummary([object[]]$windows){
    $items=@($windows)
    $interval=Get-R23MetricSummary @($items | ForEach-Object { $_.XrFrameIntervalMs })
    $wait=Get-R23MetricSummary @($items | ForEach-Object { $_.XrWaitFrameMs })
    $endFrame=Get-R23MetricSummary @($items | ForEach-Object { $_.XrEndFrameMs })
    $presentToConsume=Get-R23MetricSummary @($items | ForEach-Object { $_.GamePresentToConsumeMs })
    $display=Get-R23MetricSummary @($items | ForEach-Object { $_.DisplayPeriodMs })
    $approxHz=$null
    if($null -ne $interval.Average -and [double]$interval.Average -gt 0){
        $approxHz=1000.0/[double]$interval.Average
    }
    $ratio=$null
    if($null -ne $interval.Average -and $null -ne $display.Average -and
       [double]$display.Average -gt 0){
        $ratio=[double]$interval.Average/[double]$display.Average
    }
    $cadenceEvidenceWindows=0
    $xrFrameCount=0L
    $freshProjectionCount=0L
    $cachedProjectionCount=0L
    $directSubmitCount=0L
    $cachedProjectionSubmitCount=0L
    foreach($item in $items){
        if($item.CadenceEvidence){
            $cadenceEvidenceWindows++
            $xrFrameCount+=[int64]$item.XrFrameCount
            $freshProjectionCount+=[int64]$item.FreshProjectionCount
            $cachedProjectionCount+=[int64]$item.CachedProjectionCount
        }
        $directSubmitCount+=[int64]$item.DirectSubmitCount
        $cachedProjectionSubmitCount+=[int64]$item.CachedProjectionSubmitCount
    }
    $freshProjectionFraction=$null
    $projectionCadenceCount=$freshProjectionCount+$cachedProjectionCount
    if($projectionCadenceCount -gt 0){
        $freshProjectionFraction=[double]$freshProjectionCount/[double]$projectionCadenceCount
    }
    $freshProjectionHzEstimate=$null
    $cachedProjectionHzEstimate=$null
    if($null -ne $approxHz -and $xrFrameCount -gt 0){
        $freshProjectionHzEstimate=[double]$approxHz*[double]$freshProjectionCount/[double]$xrFrameCount
        $cachedProjectionHzEstimate=[double]$approxHz*[double]$cachedProjectionCount/[double]$xrFrameCount
    }
    $directSubmitFraction=$null
    $directOrCachedSubmitCount=$directSubmitCount+$cachedProjectionSubmitCount
    if($directOrCachedSubmitCount -gt 0){
        $directSubmitFraction=[double]$directSubmitCount/[double]$directOrCachedSubmitCount
    }
    return [pscustomobject]@{
        WindowCount=$items.Count
        XrFrameIntervalMs=$interval
        ApproxHz=$approxHz
        XrWaitFrameMs=$wait
        XrEndFrameMs=$endFrame
        GamePresentToConsumeMs=$presentToConsume
        DisplayPeriodMs=$display
        IntervalToDisplayPeriodRatio=$ratio
        CadenceEvidenceWindowCount=$cadenceEvidenceWindows
        XrFrameCount=$xrFrameCount
        FreshProjectionCount=$freshProjectionCount
        CachedProjectionCount=$cachedProjectionCount
        FreshProjectionFraction=$freshProjectionFraction
        FreshProjectionHzEstimate=$freshProjectionHzEstimate
        CachedProjectionHzEstimate=$cachedProjectionHzEstimate
        DirectSubmitCount=$directSubmitCount
        CachedProjectionSubmitCount=$cachedProjectionSubmitCount
        DirectSubmitFraction=$directSubmitFraction
    }
}

function Get-R23PipelinePhaseSummary([string]$text){
    $menu=@()
    $gameplay=@()
    $mixed=@()
    foreach($line in [regex]::Split($text,"\r?\n")){
        if($line -notmatch '\[R23 pipeline\]'){continue}

        $requested=''
        $requestedMatch=[regex]::Match(
            $line,'requestedLayer=([^\s]+)',
            [Text.RegularExpressions.RegexOptions]::IgnoreCase)
        if($requestedMatch.Success){$requested=$requestedMatch.Groups[1].Value}

        $menuSubmits=0L
        $gameplaySubmits=0L
        $directSubmits=0L
        $cachedProjectionSubmits=0L
        $submitMatch=[regex]::Match(
            $line,'actualSubmits=\{([^}]*)\}',
            [Text.RegularExpressions.RegexOptions]::IgnoreCase)
        if($submitMatch.Success){
            foreach($entry in $submitMatch.Groups[1].Value -split ','){
                $countMatch=[regex]::Match($entry.Trim(),'^([^:]+):(\d+)')
                if(-not $countMatch.Success){continue}
                $kind=$countMatch.Groups[1].Value
                $count=[int64]$countMatch.Groups[2].Value
                if($kind -match '^menu-'){$menuSubmits+=$count}
                elseif($kind -match '^(projection-|gameplay-|direct-only-|recovery-)'){
                    $gameplaySubmits+=$count
                }
                if($kind -match '^projection-direct-'){$directSubmits+=$count}
                if($kind -match 'projection-cached$'){$cachedProjectionSubmits+=$count}
            }
        }

        $cadenceEvidence=$false
        $cadenceXrFrames=0L
        $cadenceFresh=0L
        $cadenceCached=0L
        $cadenceCounterCount=0
        $cadenceMatch=[regex]::Match($line,'cadence=\{([^}]*)\}',[Text.RegularExpressions.RegexOptions]::IgnoreCase)
        if($cadenceMatch.Success){
            $cadenceBody=$cadenceMatch.Groups[1].Value
            foreach($counterName in @('xr','fresh','cached')){
                $counterMatch=[regex]::Match($cadenceBody,('(?:^|,)\s*'+[regex]::Escape($counterName)+':(\d+)'),[Text.RegularExpressions.RegexOptions]::IgnoreCase)
                if(-not $counterMatch.Success){continue}
                $cadenceCounterCount++
                $counterValue=[int64]$counterMatch.Groups[1].Value
                if($counterName -eq 'xr'){$cadenceXrFrames=$counterValue}
                elseif($counterName -eq 'fresh'){$cadenceFresh=$counterValue}
                elseif($counterName -eq 'cached'){$cadenceCached=$counterValue}
            }
            # Fresh/cached attribution is decision evidence only when all three
            # co-timed counters are present. A partial cadence block must not
            # silently contribute zeroes to phase freshness rates.
            $cadenceEvidence=($cadenceCounterCount -eq 3)
        }

        $phase='MIXED_OR_UNKNOWN'
        if($menuSubmits -gt 0 -and $gameplaySubmits -eq 0){
            $phase='MENU'
        } elseif($gameplaySubmits -gt 0 -and $menuSubmits -eq 0){
            $phase='GAMEPLAY'
        } elseif($menuSubmits -eq 0 -and $gameplaySubmits -eq 0){
            if($requested -match '^menu-'){$phase='MENU'}
            elseif($requested -match '^(projection-|gameplay-|direct-only-|recovery-)'){
                $phase='GAMEPLAY'
            }
        }

        $window=[pscustomobject]@{
            RequestedLayer=$requested
            MenuSubmitCount=$menuSubmits
            GameplaySubmitCount=$gameplaySubmits
            XrFrameIntervalMs=Get-R23LineScalar $line 'xrFrameIntervalMs'
            XrWaitFrameMs=Get-R23LineScalar $line 'xrWaitFrameMs'
            XrEndFrameMs=Get-R23LineScalar $line 'xrEndFrameMs'
            GamePresentToConsumeMs=Get-R23LineScalar $line 'gamePresentToConsumeMs'
            DisplayPeriodMs=Get-R23LineScalar $line 'displayPeriodMs'
            CadenceEvidence=$cadenceEvidence
            XrFrameCount=$cadenceXrFrames
            FreshProjectionCount=$cadenceFresh
            CachedProjectionCount=$cadenceCached
            DirectSubmitCount=$directSubmits
            CachedProjectionSubmitCount=$cachedProjectionSubmits
        }
        if($phase -eq 'MENU'){$menu+=$window}
        elseif($phase -eq 'GAMEPLAY'){$gameplay+=$window}
        else{$mixed+=$window}
    }

    return [pscustomobject]@{
        TotalWindowCount=(@($menu).Count+@($gameplay).Count+@($mixed).Count)
        Menu=Get-R23PhaseMetricSummary @($menu)
        Gameplay=Get-R23PhaseMetricSummary @($gameplay)
        MixedOrUnknown=Get-R23PhaseMetricSummary @($mixed)
        ClassificationNote='R23 5-second pipeline windows are classified from actualSubmits first, then requestedLayer. Windows containing both menu and gameplay submissions stay MIXED_OR_UNKNOWN and are excluded from pure phase cadence/freshness averages. Fresh/cached projection counts come from the co-emitted cadence block; direct/cached final-submit counts come from actualSubmits.'
    }
}

$session=@{}
$manifestPath=Join-Path $SessionDir 'session_manifest.json'
if(Test-Path $manifestPath){
    try{$session=Get-Content $manifestPath -Raw|ConvertFrom-Json}catch{$session=@{}}
}
$buildInputs=Read-OptionalJson 'BUILD_INPUTS.json'
$oneClickPreflight=Read-OptionalJson 'VR_ONE_CLICK_PREFLIGHT.json'

$gameLog=Read-AllText 'OutRun2006Tweaks.log'
$dxvkLog=Read-AllText 'OR2006C2C_d3d9.log'
$hostLog=(Read-AllText 'outrun-vr-host-v3.log')+"\n"+(Read-AllText 'outrun-vr-host-pipeline.log')
$combined=$gameLog+"\n"+$dxvkLog+"\n"+$hostLog

$provider='UNKNOWN'
if($dxvkLog -match 'DXVK:\s*v([0-9\.]+)'){$provider='DXVK '+$matches[1]}
elseif($gameLog -match 'native D3D9Ex zero-copy transport'){$provider='NATIVE_D3D9EX'}
elseif($gameLog -match 'plain IDirect3DDevice9 detected'){$provider='PLAIN_D3D9'}

$sbsFallback=($combined -match 'transport=SBS Desktop Duplication' -or
    $combined -match 'SBS/Desktop Duplication remains active' -or
    $combined -match 'keeping SBS/Desktop Duplication fallback')
$plainD3D9=($combined -match 'plain IDirect3DDevice9 detected')
$sharedProbeFailurePatterns=[ordered]@{
    LEGACY_VERIFY='shared verification texture creation/upload failed'
    DXVK_OPEN_D3DKMT='Failed to open shared D3DKMT handle'
    DXVK_WRITE_SHARED_INFO='Failed to write shared resource info for a texture'
}
$sharedProbeFailureReasons=@()
foreach($entry in $sharedProbeFailurePatterns.GetEnumerator()){
    if($combined -match [regex]::Escape([string]$entry.Value)){
        $sharedProbeFailureReasons+=[string]$entry.Key
    }
}
$sharedProbeFailed=($sharedProbeFailureReasons.Count -gt 0)

$dxvkHostBridgeReadyMatch=Get-LastRegexMatch $hostLog 'DXVK host-owned shared-eye bridge ready:\s*(\d+)x(\d+)\s*x2,\s*slots=(\d+),\s*generation=(\d+)'
$dxvkHostBridgeAllocationFailed=($hostLog -match 'DXVK host-owned shared-eye bridge allocation failed')
$dxvkHostImportReadyMatch=Get-LastRegexMatch $gameLog 'VR DXVK native transport: imported host-owned D3D11 KMT 4-slot eye ring\s+(\d+)x(\d+)\s+generation=(\d+)'
$dxvkHostImportFailed=($gameLog -match 'VR DXVK native transport: host-owned KMT eye import failed')
$dxvkHostPathActive=($gameLog -match 'path=DXVK host-owned D3D11 KMT import')
$dxvkHostBridgeReady=($null -ne $dxvkHostBridgeReadyMatch)
$dxvkHostImportReady=($null -ne $dxvkHostImportReadyMatch)
$dxvkHostBridgeWidth=if($dxvkHostBridgeReady){[int]$dxvkHostBridgeReadyMatch.Groups[1].Value}else{0}
$dxvkHostBridgeHeight=if($dxvkHostBridgeReady){[int]$dxvkHostBridgeReadyMatch.Groups[2].Value}else{0}
$dxvkHostBridgeSlots=if($dxvkHostBridgeReady){[int]$dxvkHostBridgeReadyMatch.Groups[3].Value}else{0}
$dxvkHostBridgeGeneration=if($dxvkHostBridgeReady){[uint32]$dxvkHostBridgeReadyMatch.Groups[4].Value}else{0}
$dxvkHostImportWidth=if($dxvkHostImportReady){[int]$dxvkHostImportReadyMatch.Groups[1].Value}else{0}
$dxvkHostImportHeight=if($dxvkHostImportReady){[int]$dxvkHostImportReadyMatch.Groups[2].Value}else{0}
$dxvkHostImportGeneration=if($dxvkHostImportReady){[uint32]$dxvkHostImportReadyMatch.Groups[3].Value}else{0}
$dxvkHostGenerationMatches=if($dxvkHostBridgeReady -and $dxvkHostImportReady){$dxvkHostBridgeGeneration -eq $dxvkHostImportGeneration}else{$null}
$driverSeatCount=([regex]::Matches($gameLog,'VR DRIVER SEAT CAMERA:')).Count
$crashEvidence=($combined -match '(?im)\b(crash|unhandled exception|access violation|fatal error)\b')
$whiteScreenEvidence=($combined -match '(?im)white screen|white-screen|startup white')

$drawFingerprints=@()
$drawFingerprintPattern='VR DRAW FP:\s*id=([0-9A-Fa-f]{16})\s+scope=([A-Z0-9_]+)\s+owner=([A-Z0-9_]+)\s+api=([A-Z]+)\s+prim=(\d+)\s+primCount=(\d+)\s+arg0=(\d+)\s+arg1=(\d+)\s+arg2=(\d+)\s+vsHash=([0-9A-Fa-f]{16})\s+psHash=([0-9A-Fa-f]{16})\s+vsBytes=(\d+)\s+psBytes=(\d+)\s+exact=(\d+)\s+marker=(\d+)'
foreach($fp in [regex]::Matches($gameLog,$drawFingerprintPattern,[Text.RegularExpressions.RegexOptions]::IgnoreCase)){
    $drawFingerprints += [pscustomobject]@{
        Id=$fp.Groups[1].Value.ToLowerInvariant()
        Scope=$fp.Groups[2].Value
        Owner=$fp.Groups[3].Value
        Api=$fp.Groups[4].Value
        PrimitiveType=[int]$fp.Groups[5].Value
        PrimitiveCount=[int]$fp.Groups[6].Value
        Arg0=[uint32]$fp.Groups[7].Value
        Arg1=[uint32]$fp.Groups[8].Value
        Arg2=[uint32]$fp.Groups[9].Value
        VertexShaderHash=$fp.Groups[10].Value.ToLowerInvariant()
        PixelShaderHash=$fp.Groups[11].Value.ToLowerInvariant()
        VertexShaderBytes=[uint32]$fp.Groups[12].Value
        PixelShaderBytes=[uint32]$fp.Groups[13].Value
        ExactQueueScope=([int]$fp.Groups[14].Value -ne 0)
        ProjectedMarker=([int]$fp.Groups[15].Value -ne 0)
    }
}
$drawFpSummary=Get-LastRegexMatch $gameLog 'drawFp\[unique=(\d+),hits=(\d+),dropped=(\d+)\]'
$drawFingerprintUniqueCount=if($null -ne $drawFpSummary){[int]$drawFpSummary.Groups[1].Value}else{$drawFingerprints.Count}
$drawFingerprintHits=if($null -ne $drawFpSummary){[int64]$drawFpSummary.Groups[2].Value}else{[int64]$drawFingerprints.Count}
$drawFingerprintDropped=if($null -ne $drawFpSummary){[int64]$drawFpSummary.Groups[3].Value}else{0}
$drawFingerprintEvidenceAvailable=($drawFingerprints.Count -gt 0 -or $null -ne $drawFpSummary)
$rankProjectedMarkerDrawFingerprints=@(
    $drawFingerprints | Where-Object {
        $_.Scope -eq 'PROJECTED_WORLD_MARKER_2D' -and
        $_.ExactQueueScope -and $_.ProjectedMarker
    }
)
$rankProjectedMarkerDrawFingerprintCount=
    [int]$rankProjectedMarkerDrawFingerprints.Count
$rankProjectedMarkerDrawEvidenceAvailable=
    ($rankProjectedMarkerDrawFingerprintCount -gt 0)

$directFrames=0
$directFallbacks=0
$fenceTimeout=0
$m=Get-LastRegexMatch $gameLog 'direct\[frames=(\d+),fallbacks=(\d+),fenceTimeout=(\d+)\]'
if($m){
    $directFrames=[int64]$m.Groups[1].Value
    $directFallbacks=[int64]$m.Groups[2].Value
    $fenceTimeout=[int64]$m.Groups[3].Value
}

$semanticRegistered=0
$semanticConsumed=0
$semanticStaleCleared=0
$semantic=Get-LastRegexMatch $gameLog 'VR HUD SEMANTIC R53: queuePass=\d+ registered=(\d+) consumed=(\d+) staleCleared=(\d+)'
if($semantic){
    $semanticRegistered=[int64]$semantic.Groups[1].Value
    $semanticConsumed=[int64]$semantic.Groups[2].Value
    $semanticStaleCleared=[int64]$semantic.Groups[3].Value
}

$recenterPublished=([regex]::Matches($gameLog,'VR recenter: published host requestId=')).Count
$recenterGameplayApplied=([regex]::Matches($gameLog,'VR renderer: yaw recentered gameplay pose')).Count
$recenterHostReceived=([regex]::Matches($hostLog,'(?i)recenter.*(?:received.*requestId|requestId=.*received)|requestId=.*recenter.*received')).Count
$recenterHostApplied=([regex]::Matches($hostLog,'(?i)recenter.*requestId=.*applied|requestId=.*completed by fresh visible|anchorUpdated=1 submitSuccess=1')).Count

$frameIntervals=@()
foreach($m2 in [regex]::Matches($hostLog,'xrFrameIntervalMs=([0-9\.]+)')){
    $v=0.0
    if([double]::TryParse($m2.Groups[1].Value,[Globalization.NumberStyles]::Float,[Globalization.CultureInfo]::InvariantCulture,[ref]$v)){
        if($v -gt 0 -and $v -lt 1000){$frameIntervals+=$v}
    }
}
$avgFrameMs=$null
$approxHz=$null
if($frameIntervals.Count -gt 0){
    $avgFrameMs=($frameIntervals|Measure-Object -Average).Average
    if($avgFrameMs -gt 0){$approxHz=1000.0/$avgFrameMs}
}

$hostCaptureBudget=Get-HostTripletSummary $hostLog 'captureAvgMaxP95'
$hostCommitBudget=Get-HostTripletSummary $hostLog 'commitAvgMaxP95'
$hostRenderBudget=Get-HostTripletSummary $hostLog 'renderAvgMaxP95'
$hostEndFrameBudget=Get-HostTripletSummary $hostLog 'endAvgMaxP95'
$hostXrWaitBudget=Get-HostScalarSummary $hostLog 'xrWaitFrameMs'
$hostXrIntervalBudget=Get-HostScalarSummary $hostLog 'xrFrameIntervalMs'
$hostCadenceWaitBudget=Get-HostScalarSummary $hostLog 'cadenceSerialWaitMs'
$hostPresentToConsumeBudget=Get-HostScalarSummary $hostLog 'gamePresentToConsumeMs'
$presentationCadence=Get-R23PipelinePhaseSummary $hostLog

$r32PerfWindows=0
$r32ProducerFenceOk=0L
$r32ProducerBudgetFallback=0L
$r32Backpressure=0L
$r32PendingDrain=0L
$r32PendingBlock=0L
$r32PendingError=0L
$r32Pattern='VR R32 PERF 5s:.*?direct\[probeCacheHit=\d+,producerFenceOk=(\d+),producerBudgetFallback=(\d+),backpressure=(\d+),pendingDrain=(\d+),pendingBlock=(\d+),pendingError=(\d+)\]'
foreach($r32 in [regex]::Matches($gameLog,$r32Pattern,[Text.RegularExpressions.RegexOptions]::IgnoreCase)){
    $r32PerfWindows++
    $r32ProducerFenceOk+=[int64]$r32.Groups[1].Value
    $r32ProducerBudgetFallback+=[int64]$r32.Groups[2].Value
    $r32Backpressure+=[int64]$r32.Groups[3].Value
    $r32PendingDrain+=[int64]$r32.Groups[4].Value
    $r32PendingBlock+=[int64]$r32.Groups[5].Value
    $r32PendingError+=[int64]$r32.Groups[6].Value
}
$hostPipelineWindowCount=@(
    $hostCaptureBudget.WindowCount,
    $hostCommitBudget.WindowCount,
    $hostRenderBudget.WindowCount,
    $hostEndFrameBudget.WindowCount
)|Measure-Object -Maximum|Select-Object -ExpandProperty Maximum
$frameBudgetEvidenceAvailable=($hostPipelineWindowCount -gt 0 -or $r32PerfWindows -gt 0)

$variant=if($session.VariantId){[string]$session.VariantId}else{'UNKNOWN'}
$backend=if($session.Backend){[string]$session.Backend}else{'UNKNOWN'}
$profile=if($session.TestProfile){[string]$session.TestProfile}else{'UNKNOWN'}
$sourceSha=if($session.SourceSha){[string]$session.SourceSha}else{'UNKNOWN'}

$dxvkGameplayCadenceRatio=$presentationCadence.Gameplay.IntervalToDisplayPeriodRatio
$dxvkGameplayCadenceDegraded=(
    $backend -match 'dxvk' -and
    [int]$presentationCadence.Gameplay.WindowCount -ge 2 -and
    $null -ne $dxvkGameplayCadenceRatio -and
    [double]$dxvkGameplayCadenceRatio -ge 1.5)
$dxvkGameplayCadenceStatus=if($backend -notmatch 'dxvk'){
    'NOT_DXVK'
} elseif([int]$presentationCadence.Gameplay.WindowCount -lt 2 -or
         $null -eq $dxvkGameplayCadenceRatio){
    'INSUFFICIENT_PURE_GAMEPLAY_WINDOWS'
} elseif($dxvkGameplayCadenceDegraded){
    'DXVK_GAMEPLAY_CADENCE_DEGRADED'
} else {
    'DXVK_GAMEPLAY_CADENCE_WITHIN_DISPLAY_RATIO'
}

$buildIdentityIssues=@()
$buildInputSourceSha=''
$preflightSourceSha=''
$preflightBackend=''
$buildInputBackend=''
$buildIdentityEvidenceCount=0
if($null -ne $buildInputs){
    if($buildInputs.IntegrationSha){$buildInputSourceSha=[string]$buildInputs.IntegrationSha;$buildIdentityEvidenceCount++}
    if($buildInputs.LaunchBackend){$buildInputBackend=[string]$buildInputs.LaunchBackend}
}
if($null -ne $oneClickPreflight){
    if($oneClickPreflight.SourceSha){$preflightSourceSha=[string]$oneClickPreflight.SourceSha;$buildIdentityEvidenceCount++}
    if($oneClickPreflight.ResolvedBackend){$preflightBackend=[string]$oneClickPreflight.ResolvedBackend}
    if($oneClickPreflight.PackageBuildInputs -and $oneClickPreflight.PackageBuildInputs.IntegrationSha){
        $preflightInputSha=[string]$oneClickPreflight.PackageBuildInputs.IntegrationSha
        if($preflightSourceSha -and $preflightInputSha -ne $preflightSourceSha){$buildIdentityIssues+='PREFLIGHT_PACKAGE_SOURCE_MISMATCH'}
    }
}
if($sourceSha -and $sourceSha -ne 'UNKNOWN'){
    if($buildInputSourceSha -and $buildInputSourceSha -ne $sourceSha){$buildIdentityIssues+='SESSION_BUILD_INPUT_SOURCE_MISMATCH'}
    if($preflightSourceSha -and $preflightSourceSha -ne $sourceSha){$buildIdentityIssues+='SESSION_PREFLIGHT_SOURCE_MISMATCH'}
}
if($buildInputSourceSha -and $preflightSourceSha -and $buildInputSourceSha -ne $preflightSourceSha){$buildIdentityIssues+='BUILD_INPUT_PREFLIGHT_SOURCE_MISMATCH'}
if($backend -and $backend -ne 'UNKNOWN'){
    if($buildInputBackend -and $buildInputBackend -ne $backend){$buildIdentityIssues+='SESSION_BUILD_INPUT_BACKEND_MISMATCH'}
    if($preflightBackend -and $preflightBackend -ne $backend){$buildIdentityIssues+='SESSION_PREFLIGHT_BACKEND_MISMATCH'}
}
if($buildInputBackend -and $preflightBackend -and $buildInputBackend -ne $preflightBackend){$buildIdentityIssues+='BUILD_INPUT_PREFLIGHT_BACKEND_MISMATCH'}
$buildIdentityMismatch=($buildIdentityIssues.Count -gt 0)
$buildIdentityComplete=($sourceSha -ne 'UNKNOWN' -and $buildInputSourceSha -and $preflightSourceSha -and $buildInputBackend -and $preflightBackend)
$buildIdentityVerified=($buildIdentityComplete -and -not $buildIdentityMismatch)

$packageIntegrityEvidenceAvailable=$false
$packageIntegrityVerified=$false
$packageIntegrityEntryCount=0
$packageIntegrityManifestSha=''
if($null -ne $oneClickPreflight -and $oneClickPreflight.PackageIntegrity){
    $packageIntegrityEvidenceAvailable=$true
    $packageIntegrityVerified=[bool]$oneClickPreflight.PackageIntegrity.Verified
    if($oneClickPreflight.PackageIntegrity.EntryCount){$packageIntegrityEntryCount=[int]$oneClickPreflight.PackageIntegrity.EntryCount}
    if($oneClickPreflight.PackageIntegrity.ManifestSha256){$packageIntegrityManifestSha=[string]$oneClickPreflight.PackageIntegrity.ManifestSha256}
}

$dxvkHostGenerationMismatch=($dxvkHostBridgeReady -and $dxvkHostImportReady -and $null -ne $dxvkHostGenerationMatches -and -not [bool]$dxvkHostGenerationMatches)
$dxvkDirectEvidenceBlockers=@()
if($backend -match 'dxvk'){
    if($buildIdentityMismatch){$dxvkDirectEvidenceBlockers+='BUILD_IDENTITY_MISMATCH'}
    elseif(-not $buildIdentityVerified){$dxvkDirectEvidenceBlockers+='BUILD_IDENTITY_UNVERIFIED'}
    if(-not $packageIntegrityEvidenceAvailable){$dxvkDirectEvidenceBlockers+='PACKAGE_INTEGRITY_EVIDENCE_MISSING'}
    elseif(-not $packageIntegrityVerified){$dxvkDirectEvidenceBlockers+='PACKAGE_INTEGRITY_NOT_VERIFIED'}
    if($dxvkHostGenerationMismatch){$dxvkDirectEvidenceBlockers+='HOST_IMPORT_GENERATION_MISMATCH'}
    if(-not $dxvkHostPathActive){$dxvkDirectEvidenceBlockers+='HOST_DIRECT_PATH_NOT_ACTIVE'}
    if($directFrames -le 0){$dxvkDirectEvidenceBlockers+='DIRECT_FRAMES_ZERO'}
}
$dxvkDirectEvidenceTrusted=($backend -match 'dxvk' -and $dxvkDirectEvidenceBlockers.Count -eq 0)

$dxvkPerformanceEvidenceBlockers=@()
if($backend -match 'dxvk'){
    if($profile -ne 'PERFORMANCE'){$dxvkPerformanceEvidenceBlockers+='PROFILE_NOT_PERFORMANCE'}
    if(-not $dxvkDirectEvidenceTrusted){$dxvkPerformanceEvidenceBlockers+='DIRECT_EVIDENCE_UNTRUSTED'}
    if($hostCaptureBudget.WindowCount -le 0){$dxvkPerformanceEvidenceBlockers+='HOST_CAPTURE_BUDGET_MISSING'}
    if($hostCommitBudget.WindowCount -le 0){$dxvkPerformanceEvidenceBlockers+='HOST_COMMIT_BUDGET_MISSING'}
    if($hostRenderBudget.WindowCount -le 0){$dxvkPerformanceEvidenceBlockers+='HOST_RENDER_BUDGET_MISSING'}
    if($hostEndFrameBudget.WindowCount -le 0){$dxvkPerformanceEvidenceBlockers+='HOST_ENDFRAME_BUDGET_MISSING'}
    if($r32PerfWindows -le 0){$dxvkPerformanceEvidenceBlockers+='GAME_PRODUCER_BUDGET_MISSING'}
}
$dxvkPerformanceEvidenceReady=($backend -match 'dxvk' -and $dxvkPerformanceEvidenceBlockers.Count -eq 0)

$dxvkHostDominantBudgetStage=''
$dxvkHostDominantBudgetP95Ms=$null
if($dxvkPerformanceEvidenceReady){
    $hostStageBudgets=@(
        [pscustomobject]@{Stage='CAPTURE';P95=[double]$hostCaptureBudget.MaxP95Observed},
        [pscustomobject]@{Stage='COMMIT_COPY';P95=[double]$hostCommitBudget.MaxP95Observed},
        [pscustomobject]@{Stage='RENDER';P95=[double]$hostRenderBudget.MaxP95Observed},
        [pscustomobject]@{Stage='XR_END_FRAME';P95=[double]$hostEndFrameBudget.MaxP95Observed}
    )
    foreach($candidate in $hostStageBudgets){
        if($null -eq $dxvkHostDominantBudgetP95Ms -or $candidate.P95 -gt $dxvkHostDominantBudgetP95Ms){
            $dxvkHostDominantBudgetStage=$candidate.Stage
            $dxvkHostDominantBudgetP95Ms=$candidate.P95
        }
    }
}

$flags=@()
if($sbsFallback){$flags+='SBS_DESKTOP_DUP_FALLBACK'}
if($plainD3D9){$flags+='PLAIN_D3D9_PROVIDER'}
if($sharedProbeFailed){$flags+='D3D9EX_SHARED_PROBE_FAILED'}
if($dxvkHostBridgeAllocationFailed){$flags+='DXVK_HOST_BRIDGE_ALLOCATION_FAILED'}
if($dxvkHostBridgeReady){$flags+='DXVK_HOST_BRIDGE_READY'}
if($dxvkHostImportFailed){$flags+='DXVK_HOST_BRIDGE_IMPORT_FAILED'}
if($dxvkHostImportReady){$flags+='DXVK_HOST_BRIDGE_IMPORT_READY'}
if($dxvkHostPathActive){$flags+='DXVK_HOST_DIRECT_PATH_ACTIVE'}
if($backend -match 'dxvk' -and $buildIdentityMismatch){$flags+='DXVK_BUILD_IDENTITY_MISMATCH'}
elseif($backend -match 'dxvk' -and -not $buildIdentityComplete){$flags+='DXVK_BUILD_IDENTITY_INCOMPLETE'}
elseif($backend -match 'dxvk' -and $buildIdentityVerified){$flags+='DXVK_BUILD_IDENTITY_VERIFIED'}
if($backend -match 'dxvk'){
    if($packageIntegrityVerified){$flags+='DXVK_PACKAGE_INTEGRITY_VERIFIED'}
    elseif($packageIntegrityEvidenceAvailable){$flags+='DXVK_PACKAGE_INTEGRITY_NOT_VERIFIED'}
    else{$flags+='DXVK_PACKAGE_INTEGRITY_EVIDENCE_MISSING'}
    if($dxvkHostGenerationMismatch){$flags+='DXVK_HOST_GENERATION_MISMATCH'}
    if($dxvkDirectEvidenceTrusted){$flags+='DXVK_DIRECT_EVIDENCE_TRUSTED'}
    elseif($dxvkHostPathActive -and $directFrames -gt 0){$flags+='DXVK_DIRECT_EVIDENCE_UNTRUSTED'}
    if($dxvkPerformanceEvidenceReady){$flags+='DXVK_PERFORMANCE_EVIDENCE_READY'}
    elseif($profile -eq 'PERFORMANCE'){$flags+='DXVK_PERFORMANCE_EVIDENCE_INCOMPLETE'}
    if($dxvkGameplayCadenceDegraded){$flags+='DXVK_GAMEPLAY_CADENCE_DEGRADED'}
}
if($driverSeatCount -gt 0){$flags+='DRIVER_SEAT_CAMERA_ACTIVE'}
if($directFrames -eq 0 -and $directFallbacks -gt 0){$flags+='DIRECT_GPU_NOT_ACTIVE'}
if($crashEvidence){$flags+='CRASH_TEXT_PRESENT'}
if($whiteScreenEvidence){$flags+='WHITE_SCREEN_TEXT_PRESENT'}
if($flags.Count -eq 0){$flags+='NO_AUTOMATIC_RED_FLAG'}

$status='OK'
if($backend -match 'dxvk' -and $buildIdentityMismatch){$status='DXVK_BUILD_IDENTITY_MISMATCH'}
elseif($backend -match 'dxvk' -and $dxvkHostGenerationMismatch){$status='DXVK_HOST_GENERATION_MISMATCH'}
elseif($backend -match 'dxvk' -and $dxvkHostPathActive -and $directFrames -gt 0 -and -not $dxvkDirectEvidenceTrusted){$status='DXVK_DIRECTGPU_EVIDENCE_UNTRUSTED'}
elseif($backend -match 'dxvk' -and $dxvkHostPathActive -and $directFrames -gt 0 -and $dxvkDirectEvidenceTrusted){$status='DXVK_HOST_OWNED_DIRECTGPU_ACTIVE'}
elseif($backend -match 'dxvk' -and $dxvkHostImportFailed){$status='DXVK_HOST_OWNED_IMPORT_FAILED'}
elseif($backend -match 'dxvk' -and $dxvkHostBridgeAllocationFailed){$status='DXVK_HOST_OWNED_BRIDGE_ALLOCATION_FAILED'}
elseif($backend -match 'dxvk' -and $dxvkHostBridgeReady -and -not $dxvkHostImportReady -and $directFrames -eq 0 -and $directFallbacks -gt 0){$status='DXVK_HOST_OWNED_IMPORT_NOT_ESTABLISHED'}
elseif($sbsFallback -and $backend -match 'dxvk'){$status='DXVK_SBS_FALLBACK_CONFIRMED'}
elseif($driverSeatCount -gt 0 -and $variant -ne 'G_COCKPIT'){$status='UNEXPECTED_DRIVER_SEAT_CAMERA_ACTIVE'}
elseif($directFrames -eq 0 -and $directFallbacks -gt 0){$status='DIRECT_GPU_UNAVAILABLE'}

$result=[ordered]@{
    SchemaVersion=1
    Status=$status
    VariantId=$variant
    Backend=$backend
    TestProfile=$profile
    SourceSha=$sourceSha
    BuildIdentityComplete=$buildIdentityComplete
    BuildIdentityVerified=$buildIdentityVerified
    BuildIdentityMismatch=$buildIdentityMismatch
    BuildIdentityIssues=@($buildIdentityIssues)
    BuildInputSourceSha=$buildInputSourceSha
    PreflightSourceSha=$preflightSourceSha
    BuildInputBackend=$buildInputBackend
    PreflightBackend=$preflightBackend
    PackageIntegrityEvidenceAvailable=$packageIntegrityEvidenceAvailable
    PackageIntegrityVerified=$packageIntegrityVerified
    PackageIntegrityEntryCount=$packageIntegrityEntryCount
    PackageIntegrityManifestSha256=$packageIntegrityManifestSha
    DxvkDirectEvidenceTrusted=$dxvkDirectEvidenceTrusted
    DxvkDirectEvidenceBlockers=@($dxvkDirectEvidenceBlockers)
    DxvkPerformanceEvidenceReady=$dxvkPerformanceEvidenceReady
    DxvkPerformanceEvidenceBlockers=@($dxvkPerformanceEvidenceBlockers)
    DxvkGameplayCadenceStatus=$dxvkGameplayCadenceStatus
    DxvkGameplayCadenceDegraded=$dxvkGameplayCadenceDegraded
    DxvkGameplayCadenceRatio=$dxvkGameplayCadenceRatio
    PresentationCadence=$presentationCadence
    DxvkHostDominantBudgetStage=$dxvkHostDominantBudgetStage
    DxvkHostDominantBudgetP95Ms=$dxvkHostDominantBudgetP95Ms
    DxvkHostGenerationMismatch=$dxvkHostGenerationMismatch
    Provider=$provider
    SBSDesktopDupFallback=$sbsFallback
    PlainD3D9Device=$plainD3D9
    SharedD3D9ExProbeFailed=$sharedProbeFailed
    SharedD3D9ExProbeFailureReasons=@($sharedProbeFailureReasons)
    DxvkHostBridgeReady=$dxvkHostBridgeReady
    DxvkHostBridgeAllocationFailed=$dxvkHostBridgeAllocationFailed
    DxvkHostBridgeWidth=$dxvkHostBridgeWidth
    DxvkHostBridgeHeight=$dxvkHostBridgeHeight
    DxvkHostBridgeSlots=$dxvkHostBridgeSlots
    DxvkHostBridgeGeneration=$dxvkHostBridgeGeneration
    DxvkHostImportReady=$dxvkHostImportReady
    DxvkHostImportFailed=$dxvkHostImportFailed
    DxvkHostImportWidth=$dxvkHostImportWidth
    DxvkHostImportHeight=$dxvkHostImportHeight
    DxvkHostImportGeneration=$dxvkHostImportGeneration
    DxvkHostGenerationMatches=$dxvkHostGenerationMatches
    DxvkHostDirectPathActive=$dxvkHostPathActive
    DirectFrames=$directFrames
    DirectFallbacks=$directFallbacks
    FenceTimeouts=$fenceTimeout
    DriverSeatCameraActivationCount=$driverSeatCount
    DrawFingerprintEvidenceAvailable=$drawFingerprintEvidenceAvailable
    DrawFingerprintUniqueCount=$drawFingerprintUniqueCount
    DrawFingerprintHits=$drawFingerprintHits
    DrawFingerprintDropped=$drawFingerprintDropped
    DrawFingerprints=@($drawFingerprints)
    RankProjectedMarkerDrawEvidenceAvailable=$rankProjectedMarkerDrawEvidenceAvailable
    RankProjectedMarkerDrawFingerprintCount=$rankProjectedMarkerDrawFingerprintCount
    SemanticRegistered=$semanticRegistered
    SemanticConsumed=$semanticConsumed
    SemanticStaleCleared=$semanticStaleCleared
    RecenterPublished=$recenterPublished
    RecenterGameplayApplied=$recenterGameplayApplied
    RecenterHostReceived=$recenterHostReceived
    RecenterHostApplied=$recenterHostApplied
    ApproxAverageXrFrameMs=$avgFrameMs
    ApproxAverageXrHz=$approxHz
    ApproxAverageXrHzScope='LEGACY_ALL_PIPELINE_WINDOWS_DO_NOT_USE_FOR_PHASE_HEALTH'
    FrameBudgetEvidenceAvailable=$frameBudgetEvidenceAvailable
    FrameBudget=[ordered]@{
        HostPipelineWindowCount=[int]$hostPipelineWindowCount
        CaptureMs=$hostCaptureBudget
        CommitCopyMs=$hostCommitBudget
        RenderMs=$hostRenderBudget
        XrEndFrameMs=$hostEndFrameBudget
        XrWaitFrameMs=$hostXrWaitBudget
        XrFrameIntervalMs=$hostXrIntervalBudget
        CadenceSerialWaitMs=$hostCadenceWaitBudget
        GamePresentToConsumeMs=$hostPresentToConsumeBudget
        GameProducer=[ordered]@{
            WindowCount=$r32PerfWindows
            ProducerFenceOk=$r32ProducerFenceOk
            ProducerBudgetFallback=$r32ProducerBudgetFallback
            Backpressure=$r32Backpressure
            PendingDrain=$r32PendingDrain
            PendingBlock=$r32PendingBlock
            PendingError=$r32PendingError
        }
    }
    Flags=$flags
}
$result|ConvertTo-Json -Depth 4|Set-Content (Join-Path $SessionDir 'AUTO_ANALYSIS_SUMMARY.json') -Encoding UTF8

$lines=@(
    'OUTRUN VR AUTO ANALYSIS'
    "status=$status"
    "variant=$variant"
    "backend=$backend"
    "profile=$profile"
    "sourceSha=$sourceSha"
    "buildIdentityComplete=$buildIdentityComplete"
    "buildIdentityVerified=$buildIdentityVerified"
    "buildIdentityMismatch=$buildIdentityMismatch"
    "buildIdentityIssues=$($buildIdentityIssues -join ',')"
    "buildInputSourceSha=$buildInputSourceSha"
    "preflightSourceSha=$preflightSourceSha"
    "buildInputBackend=$buildInputBackend"
    "preflightBackend=$preflightBackend"
    "packageIntegrityEvidenceAvailable=$packageIntegrityEvidenceAvailable"
    "packageIntegrityVerified=$packageIntegrityVerified"
    "packageIntegrityEntryCount=$packageIntegrityEntryCount"
    "packageIntegrityManifestSha256=$packageIntegrityManifestSha"
    "dxvkDirectEvidenceTrusted=$dxvkDirectEvidenceTrusted"
    "dxvkDirectEvidenceBlockers=$($dxvkDirectEvidenceBlockers -join ',')"
    "dxvkHostGenerationMismatch=$dxvkHostGenerationMismatch"
    "provider=$provider"
    "sbsDesktopDupFallback=$sbsFallback"
    "plainD3D9Device=$plainD3D9"
    "sharedD3D9ExProbeFailed=$sharedProbeFailed"
    "sharedD3D9ExProbeFailureReasons=$($sharedProbeFailureReasons -join ',')"
    "dxvkHostBridgeReady=$dxvkHostBridgeReady"
    "dxvkHostBridgeAllocationFailed=$dxvkHostBridgeAllocationFailed"
    "dxvkHostBridgeSize=$($dxvkHostBridgeWidth)x$($dxvkHostBridgeHeight)"
    "dxvkHostBridgeSlots=$dxvkHostBridgeSlots"
    "dxvkHostBridgeGeneration=$dxvkHostBridgeGeneration"
    "dxvkHostImportReady=$dxvkHostImportReady"
    "dxvkHostImportFailed=$dxvkHostImportFailed"
    "dxvkHostImportSize=$($dxvkHostImportWidth)x$($dxvkHostImportHeight)"
    "dxvkHostImportGeneration=$dxvkHostImportGeneration"
    "dxvkHostGenerationMatches=$dxvkHostGenerationMatches"
    "dxvkHostDirectPathActive=$dxvkHostPathActive"
    "directFrames=$directFrames"
    "directFallbacks=$directFallbacks"
    "fenceTimeouts=$fenceTimeout"
    "driverSeatCameraActivationCount=$driverSeatCount"
    "drawFingerprintEvidenceAvailable=$drawFingerprintEvidenceAvailable"
    "drawFingerprintUniqueCount=$drawFingerprintUniqueCount"
    "drawFingerprintHits=$drawFingerprintHits"
    "drawFingerprintDropped=$drawFingerprintDropped"
    "rankProjectedMarkerDrawEvidenceAvailable=$rankProjectedMarkerDrawEvidenceAvailable"
    "rankProjectedMarkerDrawFingerprintCount=$rankProjectedMarkerDrawFingerprintCount"
    "semanticRegistered=$semanticRegistered"
    "semanticConsumed=$semanticConsumed"
    "semanticStaleCleared=$semanticStaleCleared"
    "recenterPublished=$recenterPublished"
    "recenterGameplayApplied=$recenterGameplayApplied"
    "recenterHostReceived=$recenterHostReceived"
    "recenterHostApplied=$recenterHostApplied"
    ("approxAverageXrFrameMs="+$(if($null -ne $avgFrameMs){'{0:F3}' -f $avgFrameMs}else{'n/a'}))
    ("approxAverageXrHz="+$(if($null -ne $approxHz){'{0:F1}' -f $approxHz}else{'n/a'}))
    "approxAverageXrHzScope=LEGACY_ALL_PIPELINE_WINDOWS_DO_NOT_USE_FOR_PHASE_HEALTH"
    "presentationCadenceMenuWindows=$($presentationCadence.Menu.WindowCount)"
    ("presentationCadenceMenuHz="+$(if($null -ne $presentationCadence.Menu.ApproxHz){'{0:F1}' -f $presentationCadence.Menu.ApproxHz}else{'n/a'}))
    "presentationCadenceGameplayWindows=$($presentationCadence.Gameplay.WindowCount)"
    ("presentationCadenceGameplayHz="+$(if($null -ne $presentationCadence.Gameplay.ApproxHz){'{0:F1}' -f $presentationCadence.Gameplay.ApproxHz}else{'n/a'}))
    "presentationCadenceGameplayCadenceEvidenceWindows=$($presentationCadence.Gameplay.CadenceEvidenceWindowCount)"
    "presentationCadenceGameplayFreshProjectionCount=$($presentationCadence.Gameplay.FreshProjectionCount)"
    "presentationCadenceGameplayCachedProjectionCount=$($presentationCadence.Gameplay.CachedProjectionCount)"
    ("presentationCadenceGameplayFreshProjectionFraction="+$(if($null -ne $presentationCadence.Gameplay.FreshProjectionFraction){'{0:F3}' -f $presentationCadence.Gameplay.FreshProjectionFraction}else{'n/a'}))
    ("presentationCadenceGameplayFreshProjectionHzEstimate="+$(if($null -ne $presentationCadence.Gameplay.FreshProjectionHzEstimate){'{0:F1}' -f $presentationCadence.Gameplay.FreshProjectionHzEstimate}else{'n/a'}))
    ("presentationCadenceGameplayCachedProjectionHzEstimate="+$(if($null -ne $presentationCadence.Gameplay.CachedProjectionHzEstimate){'{0:F1}' -f $presentationCadence.Gameplay.CachedProjectionHzEstimate}else{'n/a'}))
    "presentationCadenceGameplayDirectSubmitCount=$($presentationCadence.Gameplay.DirectSubmitCount)"
    "presentationCadenceGameplayCachedProjectionSubmitCount=$($presentationCadence.Gameplay.CachedProjectionSubmitCount)"
    ("presentationCadenceGameplayDirectSubmitFraction="+$(if($null -ne $presentationCadence.Gameplay.DirectSubmitFraction){'{0:F3}' -f $presentationCadence.Gameplay.DirectSubmitFraction}else{'n/a'}))
    "presentationCadenceMixedOrUnknownWindows=$($presentationCadence.MixedOrUnknown.WindowCount)"
    "dxvkGameplayCadenceStatus=$dxvkGameplayCadenceStatus"
    ("dxvkGameplayCadenceRatio="+$(if($null -ne $dxvkGameplayCadenceRatio){'{0:F3}' -f $dxvkGameplayCadenceRatio}else{'n/a'}))
    "frameBudgetEvidenceAvailable=$frameBudgetEvidenceAvailable"
    "dxvkPerformanceEvidenceReady=$dxvkPerformanceEvidenceReady"
    "dxvkPerformanceEvidenceBlockers=$($dxvkPerformanceEvidenceBlockers -join ',')"
    "dxvkHostDominantBudgetStage=$dxvkHostDominantBudgetStage"
    ("dxvkHostDominantBudgetP95Ms="+$(if($null -ne $dxvkHostDominantBudgetP95Ms){'{0:F3}' -f $dxvkHostDominantBudgetP95Ms}else{'n/a'}))
    "hostPipelineWindowCount=$hostPipelineWindowCount"
    ("hostCaptureAvgMs="+$(if($null -ne $hostCaptureBudget.AverageOfWindowAverages){'{0:F3}' -f $hostCaptureBudget.AverageOfWindowAverages}else{'n/a'}))
    ("hostCaptureMaxMs="+$(if($null -ne $hostCaptureBudget.MaxObserved){'{0:F3}' -f $hostCaptureBudget.MaxObserved}else{'n/a'}))
    ("hostCommitCopyAvgMs="+$(if($null -ne $hostCommitBudget.AverageOfWindowAverages){'{0:F3}' -f $hostCommitBudget.AverageOfWindowAverages}else{'n/a'}))
    ("hostRenderAvgMs="+$(if($null -ne $hostRenderBudget.AverageOfWindowAverages){'{0:F3}' -f $hostRenderBudget.AverageOfWindowAverages}else{'n/a'}))
    ("hostXrEndFrameAvgMs="+$(if($null -ne $hostEndFrameBudget.AverageOfWindowAverages){'{0:F3}' -f $hostEndFrameBudget.AverageOfWindowAverages}else{'n/a'}))
    "producerPerfWindows=$r32PerfWindows"
    "producerFenceOk=$r32ProducerFenceOk"
    "producerBudgetFallback=$r32ProducerBudgetFallback"
    "producerBackpressure=$r32Backpressure"
    "producerPendingBlock=$r32PendingBlock"
    "producerPendingError=$r32PendingError"
    "flags=$($flags -join ',')"
)
if($status -eq 'DXVK_BUILD_IDENTITY_MISMATCH'){
    $lines+='interpretation=DXVK runtime evidence identity is inconsistent across session/build/preflight metadata; do not attribute DirectGPU or pacing results to a source SHA until the package/session mismatch is resolved.'
}
elseif($status -eq 'DXVK_HOST_GENERATION_MISMATCH'){
    $lines+='interpretation=DXVK host bridge and game import generations disagree; direct-frame telemetry is not trusted until the same transport generation is observed at both ends.'
}
elseif($status -eq 'DXVK_DIRECTGPU_EVIDENCE_UNTRUSTED'){
    $lines+='interpretation=DXVK DirectGPU frames were observed, but exact-build/package-integrity evidence is incomplete or unverified; do not use this bundle to promote the transport. Inspect DxvkDirectEvidenceBlockers.'
}
elseif($status -eq 'DXVK_HOST_OWNED_DIRECTGPU_ACTIVE'){
    $lines+='interpretation=DXVK host-owned shared-eye bridge was created, imported by the game, selected as the direct path, and produced DirectGPU frames.'
}
elseif($status -eq 'DXVK_HOST_OWNED_IMPORT_FAILED'){
    $lines+='interpretation=The OpenXR host reached the DXVK shared-eye bridge, but the game-side KMT eye import failed; inspect leftHr/rightHr and provider errors before pacing changes.'
}
elseif($status -eq 'DXVK_HOST_OWNED_BRIDGE_ALLOCATION_FAILED'){
    $lines+='interpretation=The OpenXR host failed to allocate/publish the host-owned shared-eye bridge; game-side import cannot succeed until host allocation is fixed.'
}
elseif($status -eq 'DXVK_HOST_OWNED_IMPORT_NOT_ESTABLISHED'){
    $lines+='interpretation=The host published a ready shared-eye bridge, but no matching game import was observed while gameplay fell back; inspect mapping visibility, generation identity and import eligibility.'
}
elseif($status -eq 'DXVK_SBS_FALLBACK_CONFIRMED'){
    $lines+='interpretation=DXVK loaded, but DirectGPU shared-eye transport did not activate; runtime fell back to SBS/Desktop Duplication.'
}
if($backend -match 'dxvk' -and $dxvkGameplayCadenceDegraded){
    $lines+='interpretation_cadence=DXVK pure gameplay pipeline windows are materially slower than the observed runtime display period. Menu and gameplay cadence are reported separately; do not use the legacy all-window approxAverageXrHz as a performance-health verdict.'
}
if($backend -match 'dxvk' -and $profile -eq 'PERFORMANCE'){
    if($dxvkPerformanceEvidenceReady){
        $lines+="interpretation_performance=DXVK PERFORMANCE evidence is decision-ready for bottleneck attribution: exact-build/package/direct-path trust plus host capture/commit/render/xrEndFrame and game producer budget windows are present. Largest host P95 stage=$dxvkHostDominantBudgetStage ($dxvkHostDominantBudgetP95Ms ms). This is diagnostic ranking only, not a performance PASS or an instruction to change that stage."
    } else {
        $lines+="interpretation_performance=DXVK PERFORMANCE evidence is incomplete; do not change waits/copies/draw policy from this bundle. Blockers=$($dxvkPerformanceEvidenceBlockers -join ',')"
    }
}
if($driverSeatCount -gt 0 -and $variant -ne 'G_COCKPIT'){
    $lines+='interpretation_camera=Driver-seat camera code activated during a non-cockpit test slot.'
}
$lines|Set-Content (Join-Path $SessionDir 'AUTO_ANALYSIS_SUMMARY.txt') -Encoding UTF8
Write-Host ($lines -join [Environment]::NewLine)
