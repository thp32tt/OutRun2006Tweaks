param(
    [string]$Root = $PSScriptRoot,
    [string]$Output = (Join-Path $PSScriptRoot 'pacing-export')
)
$ErrorActionPreference = 'Stop'
$inputFile = Join-Path $Root 'outrun-vr-frame-pacing.csv'
if (-not (Test-Path $inputFile)) {
    throw 'No opt-in pacing CSV; enable OUTRUN_VR_PACING_DIAGNOSTICS=1 before launching.'
}
New-Item -ItemType Directory -Force $Output | Out-Null
$destination = Join-Path $Output 'outrun-vr-frame-pacing.csv'
Copy-Item $inputFile $destination -Force
$rows = 0
$cached = 0
$missingRender = 0
Import-Csv $destination | ForEach-Object {
    $rows++
    if ($_.cached -eq '1') { $cached++ }
    if ([double]::Parse($_.gameRenderCpuMs,
            [System.Globalization.CultureInfo]::InvariantCulture) -lt 0) {
        $missingRender++
    }
}
$shaFile = Join-Path $Root 'backends/d3d9/SOURCE_SHA.txt'
$sourceSha = if (Test-Path $shaFile) {
    (Get-Content $shaFile -Raw).Trim()
} else { 'unknown' }
$report = [ordered]@{
    Format = 'OUTRUN_FRAME_PACING_V1'
    SourceSha = $sourceSha
    SubmissionRows = $rows
    CachedProjectionRows = $cached
    MissingGameBeginRows = $missingRender
    CSV_SHA256 = (Get-FileHash $destination -Algorithm SHA256).Hash
    HmdRuntimeVerified = $false
    NativeFpsVerified = $false
    Note = 'QPC CPU timing only; cached XR submissions are not game-render FPS.'
}
$report | ConvertTo-Json -Depth 3 |
    Set-Content (Join-Path $Output 'frame-pacing-summary.json') -Encoding UTF8
Write-Host "Pacing export: $rows linked XR rows ($cached cached); no runtime FPS acceptance."
