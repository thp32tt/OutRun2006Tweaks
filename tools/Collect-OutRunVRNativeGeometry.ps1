param([string]$Root=$PSScriptRoot,[string]$Output=(Join-Path $PSScriptRoot 'native-eye-geometry-export'))
$ErrorActionPreference='Stop'
$hostLog=Join-Path $Root 'outrun-vr-eye-extent.log'
if(-not(Test-Path $hostLog)){throw 'No actual OpenXR eye size log'}
$line=Get-Content $hostLog|Where-Object {$_ -match '^XR_EYE_EXTENT_V1 allocated='}|Select-Object -Last 1
if($line -notmatch 'allocated=(?<w>\d+)x(?<h>\d+)'){throw 'No valid XR eye dimensions'}
$eyeW=[uint32]$Matches.w
$eyeH=[uint32]$Matches.h
$observed=@()
foreach($log in @(Get-ChildItem $Root -File -Filter 'OutRun2006Tweaks*.log' -ErrorAction SilentlyContinue)){
    foreach($line in @(Get-Content $log.FullName|Where-Object {$_ -match 'VR native eye geometry: .* RASTER '})){
        if($line -match 'RASTER (?<w>\d+)x(?<h>\d+) >= XR eye (?<ew>\d+)x(?<eh>\d+)'){
            $observed+=([pscustomobject]@{
                SourceWidth=[uint32]$Matches.w
                SourceHeight=[uint32]$Matches.h
                ExpectedWidth=[uint32]$Matches.ew
                ExpectedHeight=[uint32]$Matches.eh
            })
        }
    }
}
$sample=if($observed.Count){$observed[-1]}else{$null}
$valid=$null -ne $sample -and
    $sample.ExpectedWidth -eq $eyeW -and $sample.ExpectedHeight -eq $eyeH -and
    $sample.SourceWidth -ge $eyeW -and $sample.SourceHeight -ge $eyeH
New-Item -ItemType Directory -Force $Output|Out-Null
[ordered]@{
    Schema='XR_NATIVE_EYE_GEOMETRY_V1'
    OpenXrEyeWidth=$eyeW
    OpenXrEyeHeight=$eyeH
    GameNativeRasterObserved=($null -ne $sample)
    GameRasterAtLeastXrPixels=$valid
    GameBackbufferWidth=if($sample){$sample.SourceWidth}else{0}
    GameBackbufferHeight=if($sample){$sample.SourceHeight}else{0}
    RuntimeHmdVisualVerified=$false
    Note='Backbuffer allocation proof only. Does not demonstrate game per-draw viewport, HUD placement, HMD quality or FPS.'
}|ConvertTo-Json -Depth 3|Set-Content (Join-Path $Output 'native-geometry-summary.json') -Encoding UTF8
Write-Host "Game raster at least XR resolution=$valid; Quest3 runtime UNTESTED."
