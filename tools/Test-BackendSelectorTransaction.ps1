Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$selectorSource = Join-Path $PSScriptRoot 'Select-OutRunVRBackend.ps1'
if (!(Test-Path $selectorSource -PathType Leaf)) {
    throw "Selector transaction test cannot find: $selectorSource"
}

$testRoot = Join-Path ([IO.Path]::GetTempPath()) ('outrun-selector-tx-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force $testRoot | Out-Null

try {
    $selector = Join-Path $testRoot 'Select-OutRunVRBackend.ps1'
    Copy-Item $selectorSource $selector -Force

    $slot = Join-Path $testRoot 'slots/A_CONTROL'
    New-Item -ItemType Directory -Force $slot | Out-Null
    Set-Content (Join-Path $slot 'SOURCE_SHA.txt') 'test-source-sha' -Encoding ascii
    Set-Content (Join-Path $slot 'dinput8.dll') 'new-game-dll' -Encoding ascii
    Set-Content (Join-Path $slot 'outrun-vr-host.exe') 'new-host' -Encoding ascii
    Set-Content (Join-Path $slot 'd3d9.dll') 'new-dxvk-provider' -Encoding ascii
    Set-Content (Join-Path $slot 'multiviewpatcher.dll') 'new-multiview' -Encoding ascii

    $sentinels = [ordered]@{
        'dinput8.dll' = 'old-game-dll'
        'outrun-vr-host.exe' = 'old-host'
        'd3d9.dll' = 'old-provider'
        'multiviewpatcher.dll' = 'old-multiview'
        'OutRun2006Tweaks.ini' = "[VR]`r`nEnabled = false`r`nRenderBackend = 1`r`n"
        'ACTIVE_VR_BACKEND.txt' = 'old-active'
        'CURRENT_VR_SESSION.json' = '{"old":true}'
        'ROOT_PAYLOAD_ATTESTATION.json' = '{"oldAttestation":true}'
    }

    foreach ($entry in $sentinels.GetEnumerator()) {
        Set-Content (Join-Path $testRoot $entry.Key) $entry.Value -Encoding ascii -NoNewline
    }

    # Force a failure only after payload copies, INI mutation and root payload
    # attestation have succeeded. The selector will fail when it tries to create
    # logs/<matrix>/<variant>/<profile>/<session> below this file.
    Set-Content (Join-Path $testRoot 'logs') 'intentional-parent-collision' -Encoding ascii -NoNewline

    $failed = $false
    try {
        & $selector -Backend dxvk -TestProfile CORRECTNESS -VariantId A_CONTROL
    } catch {
        $failed = $true
        if ($_.Exception.Message -match 'rollback failed') {
            throw "Selector reported rollback failure: $($_.Exception.Message)"
        }
    }
    if (-not $failed) {
        throw 'Selector transaction test expected the injected post-attestation failure.'
    }

    foreach ($entry in $sentinels.GetEnumerator()) {
        $actual = Get-Content (Join-Path $testRoot $entry.Key) -Raw
        if ($actual -ne [string]$entry.Value) {
            throw "Rollback did not restore $($entry.Key)."
        }
    }

    $leftoverTransactions = @(Get-ChildItem $testRoot -Directory -Filter '.vr-backend-switch-*' -ErrorAction SilentlyContinue)
    if ($leftoverTransactions.Count -ne 0) {
        throw 'Selector transaction backup directory was not cleaned after rollback.'
    }

    if ((Get-Content (Join-Path $testRoot 'logs') -Raw) -ne 'intentional-parent-collision') {
        throw 'Injected failure sentinel was unexpectedly modified.'
    }


    $failureEvidence = @(Get-ChildItem $testRoot -File -Filter 'VR_SELECTOR_FAILURE_*.json' -ErrorAction SilentlyContinue)
    if ($failureEvidence.Count -ne 1) {
        throw "Expected one root fallback selector failure diagnostic, found $($failureEvidence.Count)."
    }
    $failureRecord = Get-Content $failureEvidence[0].FullName -Raw | ConvertFrom-Json
    if ([string]$failureRecord.Phase -ne 'MUTATION_OR_SESSION_SETUP') {
        throw "Selector failure diagnostic phase mismatch: $($failureRecord.Phase)"
    }
    if ([string]$failureRecord.RollbackStatus -ne 'restored') {
        throw "Selector failure diagnostic rollback status mismatch: $($failureRecord.RollbackStatus)"
    }
    if ([bool]$failureRecord.SessionCreated) {
        throw 'Selector failure diagnostic incorrectly claims a normal session was created.'
    }

    $missingSourceRoot = Join-Path $testRoot 'missing-source-case'
    New-Item -ItemType Directory -Force $missingSourceRoot | Out-Null
    $missingSelector = Join-Path $missingSourceRoot 'Select-OutRunVRBackend.ps1'
    Copy-Item $selectorSource $missingSelector -Force
    $sourceFailed = $false
    try {
        & $missingSelector -Backend d3d9 -TestProfile CORRECTNESS -VariantId A_CONTROL | Out-Null
    } catch {
        $sourceFailed = $true
    }
    if (-not $sourceFailed) {
        throw 'Selector source-resolution diagnostic test expected a missing-payload failure.'
    }
    $sourceFailureReport = @(Get-ChildItem (Join-Path $missingSourceRoot 'logs/_selector_failures') -Filter 'SELECTOR_FAILURE.json' -File -Recurse -ErrorAction SilentlyContinue)
    if ($sourceFailureReport.Count -ne 1) {
        throw "Expected one source-resolution failure diagnostic, found $($sourceFailureReport.Count)."
    }
    $sourceFailureRecord = Get-Content $sourceFailureReport[0].FullName -Raw | ConvertFrom-Json
    if ([string]$sourceFailureRecord.Phase -ne 'SOURCE_RESOLUTION') {
        throw "Source-resolution diagnostic phase mismatch: $($sourceFailureRecord.Phase)"
    }
    if ([string]$sourceFailureRecord.RollbackStatus -ne 'not-required') {
        throw "Source-resolution rollback status mismatch: $($sourceFailureRecord.RollbackStatus)"
    }

    # Successful selection must persist the same root payload identity that the
    # selector verified after mutation and before session handoff.
    $successRoot = Join-Path $testRoot 'success-attestation-case'
    New-Item -ItemType Directory -Force $successRoot | Out-Null
    $successSelector = Join-Path $successRoot 'Select-OutRunVRBackend.ps1'
    Copy-Item $selectorSource $successSelector -Force
    $successSlot = Join-Path $successRoot 'slots/A_CONTROL'
    $successDxvk = Join-Path $successRoot 'backends/dxvk'
    New-Item -ItemType Directory -Force $successSlot | Out-Null
    New-Item -ItemType Directory -Force $successDxvk | Out-Null
    Set-Content (Join-Path $successSlot 'SOURCE_SHA.txt') 'success-source-sha' -Encoding ascii
    Set-Content (Join-Path $successSlot 'dinput8.dll') 'success-game-dll' -Encoding ascii
    Set-Content (Join-Path $successSlot 'outrun-vr-host.exe') 'success-host' -Encoding ascii
    Set-Content (Join-Path $successDxvk 'd3d9.dll') 'success-dxvk-provider' -Encoding ascii
    Set-Content (Join-Path $successRoot 'OutRun2006Tweaks.ini') "[VR]`r`nEnabled = false`r`nRenderBackend = 1`r`n" -Encoding UTF8
    Set-Content (Join-Path $successRoot 'BUILD_MATRIX_ID.txt') 'selector-behavior' -Encoding ascii

    & $successSelector -Backend dxvk-safe -TestProfile CORRECTNESS -VariantId A_CONTROL | Out-Null

    $attestationPath = Join-Path $successRoot 'ROOT_PAYLOAD_ATTESTATION.json'
    if (!(Test-Path $attestationPath -PathType Leaf)) {
        throw 'Successful selector did not persist ROOT_PAYLOAD_ATTESTATION.json.'
    }
    $attestation = Get-Content $attestationPath -Raw | ConvertFrom-Json
    foreach ($field in @('dinput8','host','d3d9')) {
        if (-not [bool]$attestation.Files.$field.Match) {
            throw "Successful selector root attestation did not match $field."
        }
    }
    if (Test-Path (Join-Path $successRoot 'multiviewpatcher.dll')) {
        throw 'dxvk-safe successful selection left forbidden multiviewpatcher.dll.'
    }
    $current = Get-Content (Join-Path $successRoot 'CURRENT_VR_SESSION.json') -Raw | ConvertFrom-Json
    if ([string]$current.Backend -ne 'dxvk-safe' -or [string]$current.SourceSha -ne 'success-source-sha') {
        throw "Successful selector session identity mismatch: backend=$($current.Backend) source=$($current.SourceSha)"
    }
    if (-not [bool]$current.RootPayloadAttestation.Files.dinput8.Match -or
        -not [bool]$current.RootPayloadAttestation.Files.host.Match -or
        -not [bool]$current.RootPayloadAttestation.Files.d3d9.Match) {
        throw 'Successful selector session did not embed verified root payload attestation.'
    }

    Write-Host 'Backend selector transactional rollback + pre-session diagnostic + successful root attestation PASS'
} finally {
    if (Test-Path $testRoot) {
        Remove-Item $testRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}
