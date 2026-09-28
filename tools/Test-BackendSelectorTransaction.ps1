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

    Write-Host 'Backend selector transactional rollback PASS'
} finally {
    if (Test-Path $testRoot) {
        Remove-Item $testRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}
