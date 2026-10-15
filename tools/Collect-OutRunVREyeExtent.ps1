param([string]$Root = $PSScriptRoot, [string]$Output = (Join-Path $PSScriptRoot 'eye-extent-export'))
$ErrorActionPreference = 'Stop'
$hostFile = Join-Path $Root 'outrun-vr-eye-extent.log'
if (-not (Test-Path $hostFile)) { throw 'OpenXR allocated-eye log not found' }
$line = Get-Content $hostFile | Where-Object { $_ -match '^XR_EYE_EXTENT_V1 allocated=\d+x\d+ ' } | Select-Object -Last 1
if (-not $line -or $line -notmatch 'allocated=(?<w>\d+)x(?<h>\d+)') { throw 'Invalid OpenXR eye extent record' }
$width = [uint32]$Matches.w; $height = [uint32]$Matches.h
if ($width -le 0 -or $height -le 0 -or $width -gt 8192 -or $height -gt 8192) { throw 'Eye extent out of range' }
$gameSizes = @()
foreach ($log in @(Get-ChildItem $Root -File -Filter 'OutRun2006Tweaks*.log' -ErrorAction SilentlyContinue)) {
    foreach ($row in @(Get-Content $log.FullName | Where-Object { $_ -match 'verified 4-slot D3D9Ex shared eye ring ready ' })) {
        if ($row -match 'shared eye ring ready (?<w>\d+)x(?<h>\d+)') {
            $gameSizes += ('{0}x{1}' -f $Matches.w, $Matches.h)
        }
    }
}
$observed = $gameSizes.Count -gt 0
$matching = $observed -and $gameSizes[-1] -eq ('{0}x{1}' -f $width,$height)
New-Item -ItemType Directory -Force $Output | Out-Null
Copy-Item $hostFile (Join-Path $Output 'outrun-vr-eye-extent.log') -Force
$source = Join-Path $Root 'backends/d3d9/SOURCE_SHA.txt'
$sha = if (Test-Path $source) { (Get-Content $source -Raw).Trim() } else { 'unknown' }
$report = [ordered]@{
    Schema = 'XR_EYE_EXTENT_V1'
    SourceSha = $sha
    XrSwapchainEyeWidth = $width
    XrSwapchainEyeHeight = $height
    GameDirectEyeAllocationObserved = $observed
    GameDirectEyeSizeMatchesXr = $matching
    GameLastDirectEyeSize = if ($observed) { $gameSizes[-1] } else { 'NOT_OBSERVED' }
    HostLogSha256 = (Get-FileHash $hostFile -Algorithm SHA256).Hash
    HmdRuntimeVerified = $false
    NativeFpsVerified = $false
    Note = 'Diagnostic allocation sizes only. Native stereo geometry detail/HMD validation not established.'
}
$report | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $Output 'eye-extent-summary.json') -Encoding UTF8
Write-Host "OpenXR $($width)x$($height); game DirectGPU eye allocation match=$matching; HMD UNTESTED."
