param(
    [Parameter(Mandatory=$true)]
    [string]$SourceRoot,

    [string]$OutputZip = (Join-Path (Get-Location) ("OutRun2_HD_Localization_Source_{0}.zip" -f (Get-Date -Format "yyyyMMdd_HHmm"))),

    [string]$AssetQueueCsv = ""
)

$ErrorActionPreference = "Stop"

function Get-DdsSize {
    param([string]$Path)
    $fs = [System.IO.File]::OpenRead($Path)
    try {
        if ($fs.Length -lt 20) { return $null }
        $br = New-Object System.IO.BinaryReader($fs)
        $magic = $br.ReadBytes(4)
        if ([System.Text.Encoding]::ASCII.GetString($magic) -ne "DDS ") { return $null }
        $fs.Position = 12
        $height = $br.ReadInt32()
        $width  = $br.ReadInt32()
        if ($width -le 0 -or $height -le 0) { return $null }
        return [pscustomobject]@{ Width=$width; Height=$height; Area=([int64]$width * [int64]$height) }
    }
    finally {
        $fs.Dispose()
    }
}

$SourceRoot = (Resolve-Path $SourceRoot).Path

if ([string]::IsNullOrWhiteSpace($AssetQueueCsv)) {
    $queueUrl = "https://raw.githubusercontent.com/thp32tt/OutRun2006Tweaks/korean-localization-clean/localization/graphics/asset_queue.csv"
    Write-Host "[1/6] Downloading localization target list..."
    $queueText = (Invoke-WebRequest -UseBasicParsing -Uri $queueUrl).Content
    $queue = $queueText | ConvertFrom-Csv
} else {
    $queue = Import-Csv (Resolve-Path $AssetQueueCsv)
}

$wantedActions = @("localize_text", "font_pipeline", "hangul_name_entry", "zoom_review")
$targets = @($queue | Where-Object { $wantedActions -contains $_.action })

Write-Host "[2/6] Indexing DDS files under: $SourceRoot"
$allDds = @(Get-ChildItem -LiteralPath $SourceRoot -Recurse -File -Filter *.dds)

$work = Join-Path $env:TEMP ("outrun_hd_loc_" + [guid]::NewGuid().ToString("N"))
$payload = Join-Path $work "payload"
New-Item -ItemType Directory -Force -Path $payload | Out-Null

$manifest = New-Object System.Collections.Generic.List[object]
$missing  = New-Object System.Collections.Generic.List[object]

Write-Host "[3/6] Selecting highest-resolution DDS for each localization target..."
$i = 0
foreach ($t in $targets) {
    $i++
    $expectedPath = ($t.path -replace "\\","/").Trim()
    $expectedName = [System.IO.Path]::GetFileName($expectedPath)

    $key = $expectedName -replace "_\d+x\d+\.dds$",""
    if ($key -eq $expectedName) {
        $key = [System.IO.Path]::GetFileNameWithoutExtension($expectedName)
    }

    $expectedDirLeaf = Split-Path (Split-Path $expectedPath -Parent) -Leaf
    $candidates = @($allDds | Where-Object {
        $_.BaseName -match ("^" + [regex]::Escape($key) + "(?:_|$)")
    })

    if ($candidates.Count -eq 0) {
        $missing.Add([pscustomobject]@{
            key=$key; action=$t.action; expected_path=$expectedPath
        })
        continue
    }

    $ranked = foreach ($f in $candidates) {
        $dds = Get-DdsSize $f.FullName
        if ($null -eq $dds) { continue }
        $rel = $f.FullName.Substring($SourceRoot.Length).TrimStart("\","/")
        $dirLeaf = $f.Directory.Name
        [pscustomobject]@{
            File=$f
            Width=$dds.Width
            Height=$dds.Height
            Area=$dds.Area
            DirMatch=([int]($dirLeaf -ieq $expectedDirLeaf))
            Rel=$rel
        }
    }

    $best = $ranked | Sort-Object @{Expression="DirMatch";Descending=$true}, @{Expression="Area";Descending=$true}, @{Expression={ $_.File.Length };Descending=$true} | Select-Object -First 1

    if ($null -eq $best) {
        $missing.Add([pscustomobject]@{
            key=$key; action=$t.action; expected_path=$expectedPath
        })
        continue
    }

    $dest = Join-Path $payload $best.Rel
    New-Item -ItemType Directory -Force -Path (Split-Path $dest -Parent) | Out-Null
    Copy-Item -LiteralPath $best.File.FullName -Destination $dest -Force

    $sha = (Get-FileHash -Algorithm SHA256 -LiteralPath $best.File.FullName).Hash.ToLowerInvariant()
    $manifest.Add([pscustomobject]@{
        key=$key
        action=$t.action
        expected_stock_path=$expectedPath
        hd_source_relative_path=($best.Rel -replace "\\","/")
        width=$best.Width
        height=$best.Height
        bytes=$best.File.Length
        sha256=$sha
    })

    if (($i % 20) -eq 0) {
        Write-Host ("  {0}/{1} targets checked" -f $i,$targets.Count)
    }
}

Write-Host "[4/6] Writing manifests..."
$manifest | Sort-Object key | Export-Csv -NoTypeInformation -Encoding UTF8 (Join-Path $work "HD_LOCALIZATION_SOURCE_MANIFEST.csv")
$missing  | Sort-Object key | Export-Csv -NoTypeInformation -Encoding UTF8 (Join-Path $work "MISSING_TARGETS.csv")

$summary = [pscustomobject]@{
    created_at = (Get-Date).ToString("o")
    source_root = $SourceRoot
    target_rows = $targets.Count
    collected = $manifest.Count
    missing = $missing.Count
    purpose = "Canonical high-resolution DDS source for OutRun 2006 Korean localization"
}
$summary | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 (Join-Path $work "HD_SOURCE_SUMMARY.json")

Write-Host "[5/6] Creating ZIP..."
if (Test-Path $OutputZip) { Remove-Item -LiteralPath $OutputZip -Force }
Compress-Archive -Path (Join-Path $work "*") -DestinationPath $OutputZip -CompressionLevel Optimal

Write-Host "[6/6] Verifying..."
$zipHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $OutputZip).Hash.ToLowerInvariant()
$zipSize = (Get-Item $OutputZip).Length

Write-Host ""
Write-Host "DONE"
Write-Host ("ZIP      : {0}" -f $OutputZip)
Write-Host ("SHA-256  : {0}" -f $zipHash)
Write-Host ("Collected: {0}/{1}" -f $manifest.Count,$targets.Count)
Write-Host ("Missing  : {0}" -f $missing.Count)
Write-Host ("Bytes    : {0}" -f $zipSize)
Write-Host ""
Write-Host "Upload this ZIP to the Korean-localization chat. The manifest preserves the exact HD source identity."

Remove-Item -LiteralPath $work -Recurse -Force
