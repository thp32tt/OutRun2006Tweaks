$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

$root=Split-Path -Parent $MyInvocation.MyCommand.Path
$analyzer=Join-Path $root 'Analyze-OutRunVRSession.ps1'
if(!(Test-Path $analyzer)){throw 'Analyze-OutRunVRSession.ps1 missing'}

function Assert-True([bool]$condition,[string]$message){
    if(-not $condition){throw $message}
}

function New-SessionCase([string]$name,[string]$hostText){
    $dir=Join-Path ([IO.Path]::GetTempPath()) ("outrun-vr-analysis-{0}-{1}" -f $name,[guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Force $dir|Out-Null
    [ordered]@{
        VariantId='DX11_NATIVE'
        Backend='dx11'
        TestProfile='CORRECTNESS'
        SourceSha='TEST_SHA'
    }|ConvertTo-Json|Set-Content (Join-Path $dir 'session_manifest.json') -Encoding UTF8
    @(
        'native D3D9Ex zero-copy transport'
        'direct[frames=4662,fallbacks=3,fenceTimeout=0]'
    )|Set-Content (Join-Path $dir 'OutRun2006Tweaks.log') -Encoding UTF8
    $hostText|Set-Content (Join-Path $dir 'outrun-vr-host-pipeline.log') -Encoding UTF8
    return $dir
}

$bad=$null
$good=$null
try{
    $bad=New-SessionCase 'sustained-fallback' @'
window=menu actualFinal=fallback-cached-image actualSubmits={fallback-cached-image:450}
window=menu actualFinal=fallback-cached-image actualSubmits={fallback-cached-image:450}
'@
    & $analyzer -SessionDir $bad | Out-Null
    $badResult=Get-Content (Join-Path $bad 'AUTO_ANALYSIS_SUMMARY.json') -Raw|ConvertFrom-Json
    Assert-True ($badResult.Status -eq 'DX11_SUSTAINED_CACHED_IMAGE_FALLBACK_CONFIRMED') 'sustained cached-image fallback must be a DX11 failure status'
    Assert-True ($badResult.SustainedCachedImageFallback -eq $true) 'sustained fallback boolean missing'
    Assert-True ($badResult.MaxFallbackCachedImageWindowFrames -eq 450) 'max fallback window should be 450 frames'
    Assert-True ($badResult.FallbackCachedImageFrames -eq 900) 'fallback frame total should sum both 450-frame windows'
    Assert-True (@($badResult.Flags) -contains 'DX11_SUSTAINED_CACHED_IMAGE_FALLBACK') 'red flag missing for sustained cached-image fallback'
    Assert-True (-not (@($badResult.Flags) -contains 'NO_AUTOMATIC_RED_FLAG')) 'known visual fallback must not report NO_AUTOMATIC_RED_FLAG'

    $good=New-SessionCase 'direct-control' @'
window=menu actualFinal=direct-gpu actualSubmits={direct-gpu:450}
'@
    & $analyzer -SessionDir $good | Out-Null
    $goodResult=Get-Content (Join-Path $good 'AUTO_ANALYSIS_SUMMARY.json') -Raw|ConvertFrom-Json
    Assert-True ($goodResult.Status -eq 'OK') 'direct control should remain OK'
    Assert-True ($goodResult.SustainedCachedImageFallback -eq $false) 'direct control must not be marked as sustained fallback'
    Assert-True (@($goodResult.Flags) -contains 'NO_AUTOMATIC_RED_FLAG') 'direct control should keep NO_AUTOMATIC_RED_FLAG'

    Write-Host 'OutRun VR session analyzer regression passed: sustained DX11 cached-image fallback is detected and direct control remains clean.'
} finally {
    foreach($dir in @($bad,$good)){
        if($dir -and (Test-Path $dir)){Remove-Item $dir -Recurse -Force -ErrorAction SilentlyContinue}
    }
}
