param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("2d","d3d9","dx11","dxvk-safe","dxvk")]
    [string]$Backend,
    [ValidateSet("CONTROL","CORRECTNESS","HUD_SCREEN","HUD_MENU","HUD_WORLD","PERFORMANCE","STAGE_DIAGNOSTIC","A_BASELINE","B_CULLING","C_CULLING_NO_SSAA","D_CULLING_NO_SSAA_R512")]
    [string]$TestProfile = "CORRECTNESS",
    [ValidateSet("AUTO","CONTROL_2D","CURRENT_FOCUS","A_CONTROL","B_HUD","C_FLARE","D_PERF","E_DXVK_SAFE","E_DXVK_MULTIVIEW","G_COCKPIT","X_BASE","X_SCREEN_HUD","X_WORLD_RANK","X_COMBINED","R54_A_NEXTDRAW","R54_B_STICKY","R54_C_FULL_OWNER","R54_D_HUD_PLANE","R55_A_ZERO","R55_B_SCALE35","R55_C_WORLD35","R55_D_RANKZERO","R56_01_ZERO","R56_02_SCALE35","R56_03_WORLD35","R56_04_RANKZERO","R56_05_POSITION_XP96","R56_06_POSITION_XM96","R56_07_POSITION_XS35","R56_08_POSITION_XCENTER","R56_09_RANK13_XP96","R56_10_RANK13_XM96","R56_11_RANK13_YM72","R56_12_RANK13_CENTER","R56_13_RANK46_XP96","R56_14_RANK46_YM72","R56_15_RANK46_CENTER","R56_16_RANK13_AS_HUD","R56_17_RANK46_AS_HUD","R56_18_RANK46_NEXTDRAW","R56_19_POSITION_NEXTDRAW","R56_20_ALLSCREEN_RAW","R57_01_POSITION_KIND1_HUD35","R57_02_POSITION_KIND0_HUD35","R57_03_POSITION_ALL_WORLD35","R57_04_RANK_ALL_AS_HUD","R57_05_RANK_PROJECTED_IPD","R57_06_RANK_PROJECTED_HEAD","R57_07_RANK_PROJECTED_13","R57_08_RANK_PROJECTED_46","R57_09_RANK_PROJECTED_ZERO","R57_10_RANK_PROJECTED_TRACE","R67_EYE_REPROJECT","R68_FIXPACK","R69_FIXPACK")]
    [string]$VariantId = "AUTO"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendRoot = Join-Path $root "backends"
$payloadBackend = if ($Backend -eq "2d" -or $Backend -eq "dxvk-safe" -or $Backend -eq "dx11") { "d3d9" } else { $Backend }

$defaultVariant = switch ($Backend) {
    "2d"        { "CONTROL_2D" }
    "d3d9"      { "A_CONTROL" }
    "dx11"      { "R57_05_RANK_PROJECTED_IPD" }
    "dxvk-safe" { "E_DXVK_SAFE" }
    "dxvk"      { "E_DXVK_MULTIVIEW" }
}
$variant = if ($VariantId -eq "AUTO") { $defaultVariant } else { $VariantId }

$slotPayload = Join-Path $root ("slots/" + $variant)
$backendPayload = Join-Path $backendRoot $payloadBackend
$src = if (Test-Path $slotPayload) { $slotPayload } else { $backendPayload }
$sourceSha = "unknown"

$logPatterns=@(
    'OutRun2006Tweaks*.log',
    'OutRun2006Tweaks-hudtrace*.csv',
    'OutRun2006Tweaks-xstmap*.csv',
    'outrun-vr-host*.log',
    'outrun-vr-host-pipeline*.log',
    'outrun-vr-watchdog*.log',
    'backend*.log',
    'OR2006C2C_d3d9.log',
    'OR2006C2C_dxgi.log',
    'OR2006C2C_d3d11.log',
    'OR2006C2C_vkd3d*.log',
    'dxvk*.log',
    'vkd3d*.log',
    'crash.log',
    'OR2006C2C.EXE.*.zip',
    '*.dmp'
)

function Get-SessionFiles {
    $seen=@{}
    $files=@()
    foreach($pattern in $logPatterns){
        foreach($file in Get-ChildItem $root -Filter $pattern -File -ErrorAction SilentlyContinue){
            if($seen.ContainsKey($file.FullName)){continue}
            $seen[$file.FullName]=$true
            $files+=$file
        }
    }
    return $files
}

function Seal-PendingSessionLogs {
    $files=Get-SessionFiles
    if(-not $files -or $files.Count -eq 0){return}

    $current=Join-Path $root 'CURRENT_VR_SESSION.json'
    $dest=$null
    $oldState=$null
    if(Test-Path $current){
        try{$oldState=Get-Content $current -Raw|ConvertFrom-Json}catch{$oldState=$null}
    }

    if($oldState -and $oldState.SessionId -and $oldState.BuildMatrixId -and $oldState.VariantId){
        $oldProfile=if($oldState.TestProfile){[string]$oldState.TestProfile}else{'CORRECTNESS'}
        $dest=Join-Path $root ("logs/{0}/{1}/{2}/{3}" -f $oldState.BuildMatrixId,$oldState.VariantId,$oldProfile,$oldState.SessionId)
    }else{
        $stamp=(Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssfffZ')
        $dest=Join-Path $root ("logs/_orphaned/{0}" -f $stamp)
    }
    New-Item -ItemType Directory -Force $dest|Out-Null

    $moved=@()
    foreach($file in $files){
        $target=Join-Path $dest $file.Name
        if(Test-Path $target){
            $prefix=(Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssfffZ')
            $target=Join-Path $dest ($prefix+'_'+$file.Name)
        }
        Move-Item $file.FullName $target -Force
        $moved+=[IO.Path]::GetFileName($target)
    }
    @(
        "AUTO_ARCHIVED_UTC=$((Get-Date).ToUniversalTime().ToString('o'))"
        "REASON=backend-selection-started-new-session"
        "FILES=$($moved -join ',')"
    )|Set-Content (Join-Path $dest 'AUTO_ARCHIVED_ON_NEXT_SESSION.txt') -Encoding UTF8
}

function Copy-Required([string]$name) {
    $p = Join-Path $src $name
    if (-not (Test-Path $p)) { throw "Required backend file missing: $p" }
    Copy-Item $p (Join-Path $root $name) -Force
}

function Remove-RootVerified([string]$name) {
    $p = Join-Path $root $name
    if (Test-Path $p) {
        Remove-Item $p -Force
        if (Test-Path $p) { throw "Could not remove $name. Close OutRun/VR host and retry." }
    }
}

$transactionFileNames = @(
    'dinput8.dll',
    'outrun-vr-host.exe',
    'd3d9.dll',
    'multiviewpatcher.dll',
    'OutRun2006Tweaks.ini',
    'ACTIVE_VR_BACKEND.txt',
    'CURRENT_VR_SESSION.json',
    'ROOT_PAYLOAD_ATTESTATION.json'
)

function Start-BackendSwitchTransaction {
    $backupRoot = Join-Path $root ('.vr-backend-switch-' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Force $backupRoot | Out-Null

    $original = [ordered]@{}
    foreach ($name in $transactionFileNames) {
        $sourcePath = Join-Path $root $name
        $present = Test-Path $sourcePath -PathType Leaf
        $original[$name] = $present
        if ($present) {
            Copy-Item $sourcePath (Join-Path $backupRoot $name) -Force
        }
    }

    return [pscustomobject]@{
        BackupRoot = $backupRoot
        Original = $original
        SessionRoot = $null
    }
}

function Restore-BackendSwitchTransaction($State) {
    $rollbackErrors = @()
    foreach ($name in $transactionFileNames) {
        try {
            $destinationPath = Join-Path $root $name
            if ([bool]$State.Original[$name]) {
                $backupPath = Join-Path $State.BackupRoot $name
                if (-not (Test-Path $backupPath -PathType Leaf)) {
                    throw "Backup file missing: $backupPath"
                }
                Copy-Item $backupPath $destinationPath -Force
            } elseif (Test-Path $destinationPath) {
                Remove-Item $destinationPath -Force
            }
        } catch {
            $rollbackErrors += ("{0}: {1}" -f $name,$_.Exception.Message)
        }
    }

    if ($State.SessionRoot -and (Test-Path $State.SessionRoot)) {
        try {
            Remove-Item $State.SessionRoot -Recurse -Force
        } catch {
            $rollbackErrors += ("session-root: {0}" -f $_.Exception.Message)
        }
    }

    if ($rollbackErrors.Count -gt 0) {
        throw ("Backend selection rollback failed: " + ($rollbackErrors -join '; '))
    }
}

function Remove-BackendSwitchTransaction($State) {
    if ($State -and $State.BackupRoot -and (Test-Path $State.BackupRoot)) {
        Remove-Item $State.BackupRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}


function Write-BackendSelectionFailureDiagnostic(
    [string]$Phase,
    [string]$ErrorText,
    [string]$RollbackStatus,
    [string]$BackupRoot = ''
) {
    $stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssfffZ')
    $record = [ordered]@{
        SchemaVersion = 1
        RecordedUtc = (Get-Date).ToUniversalTime().ToString('o')
        Phase = $Phase
        Backend = $Backend
        VariantId = $variant
        SourceSha = $sourceSha
        Error = $ErrorText
        RollbackStatus = $RollbackStatus
        BackupRoot = $BackupRoot
        SessionCreated = $false
    }

    $path = $null
    try {
        $dest = Join-Path $root ("logs/_selector_failures/{0}" -f $stamp)
        New-Item -ItemType Directory -Force $dest | Out-Null
        $path = Join-Path $dest 'SELECTOR_FAILURE.json'
        $record | ConvertTo-Json -Depth 6 | Set-Content $path -Encoding UTF8
        return $path
    } catch {
        # Pre-session failures can occur because the logs tree itself is the
        # broken resource. Fall back to a root sidecar so the original failure
        # still has durable evidence without masking it.
        try {
            $path = Join-Path $root ("VR_SELECTOR_FAILURE_{0}.json" -f $stamp)
            $record | ConvertTo-Json -Depth 6 | Set-Content $path -Encoding UTF8
            return $path
        } catch {
            return 'diagnostic-write-failed'
        }
    }
}

if (-not (Test-Path $src)) {
    $message = "Test payload not found for variant=$variant backend=$Backend : $src"
    $diagnostic = Write-BackendSelectionFailureDiagnostic -Phase 'SOURCE_RESOLUTION' -ErrorText $message -RollbackStatus 'not-required'
    throw ("{0} Diagnostic={1}" -f $message,$diagnostic)
}
$sourceFile = Join-Path $src "SOURCE_SHA.txt"
$sourceSha = if (Test-Path $sourceFile) { (Get-Content $sourceFile -Raw).Trim() } else { "unknown" }

function Get-FileIdentity([string]$Path) {
    if (-not (Test-Path $Path -PathType Leaf)) { return $null }
    $resolved = (Resolve-Path $Path).Path
    return [ordered]@{
        Path = [IO.Path]::GetFileName($resolved)
        Length = (Get-Item $resolved).Length
        Sha256 = (Get-FileHash $resolved -Algorithm SHA256).Hash.ToLowerInvariant()
    }
}

function Assert-SamePayloadFile([string]$ExpectedPath,[string]$ActualPath,[string]$Label) {
    $expected = Get-FileIdentity $ExpectedPath
    $actual = Get-FileIdentity $ActualPath
    if ($null -eq $expected) { throw "Payload attestation source missing for $Label : $ExpectedPath" }
    if ($null -eq $actual) { throw "Payload attestation root file missing for $Label : $ActualPath" }
    if ($expected.Length -ne $actual.Length -or $expected.Sha256 -ne $actual.Sha256) {
        throw "Root payload attestation mismatch for $Label : expected=$($expected.Sha256) actual=$($actual.Sha256)"
    }
    return [ordered]@{ Expected = $expected; Actual = $actual; Match = $true }
}

function Assert-RootPayloadIdentity {
    $report = [ordered]@{
        SchemaVersion = 1
        VerifiedUtc = (Get-Date).ToUniversalTime().ToString('o')
        Backend = $Backend
        VariantId = $variant
        SourceRoot = $src
        Files = [ordered]@{}
    }

    $report.Files.dinput8 = Assert-SamePayloadFile (Join-Path $src 'dinput8.dll') (Join-Path $root 'dinput8.dll') 'dinput8.dll'

    if ($Backend -eq '2d') {
        foreach ($name in @('outrun-vr-host.exe','d3d9.dll','multiviewpatcher.dll')) {
            if (Test-Path (Join-Path $root $name)) {
                throw "Root payload attestation found forbidden file for 2d: $name"
            }
        }
        return $report
    }

    $report.Files.host = Assert-SamePayloadFile (Join-Path $src 'outrun-vr-host.exe') (Join-Path $root 'outrun-vr-host.exe') 'outrun-vr-host.exe'

    if ($Backend -eq 'dxvk-safe') {
        $providerSource = Join-Path (Join-Path $backendRoot 'dxvk') 'd3d9.dll'
        $report.Files.d3d9 = Assert-SamePayloadFile $providerSource (Join-Path $root 'd3d9.dll') 'd3d9.dll'
        if (Test-Path (Join-Path $root 'multiviewpatcher.dll')) {
            throw 'Root payload attestation found forbidden multiviewpatcher.dll in dxvk-safe mode.'
        }
    } elseif ($Backend -eq 'dxvk') {
        $report.Files.d3d9 = Assert-SamePayloadFile (Join-Path $src 'd3d9.dll') (Join-Path $root 'd3d9.dll') 'd3d9.dll'
        $report.Files.multiview = Assert-SamePayloadFile (Join-Path $src 'multiviewpatcher.dll') (Join-Path $root 'multiviewpatcher.dll') 'multiviewpatcher.dll'
    } else {
        foreach ($name in @('d3d9.dll','multiviewpatcher.dll')) {
            if (Test-Path (Join-Path $root $name)) {
                throw "Root payload attestation found forbidden file for $Backend : $name"
            }
        }
    }

    return $report
}

function Repair-IniSectionHeaders([string]$text) {
    $text = $text -replace '(?m)^\[VR\]\\\s*$', '[VR]'
    $text = $text -replace '(?m)^\\\s*$\r?\n?', ''
    return $text
}

function Set-IniSectionValue([string]$text,[string]$section,[string]$key,[string]$value) {
    $escapedSection = [regex]::Escape($section)
    $escapedKey = [regex]::Escape($key)
    $sectionPattern = "(?ms)(^\[$escapedSection\]\s*\r?\n)(.*?)(?=^\[|\z)"
    $m = [regex]::Match($text,$sectionPattern)
    $nl = [Environment]::NewLine
    if (-not $m.Success) {
        if ($text.Length -gt 0 -and -not $text.EndsWith($nl)) { $text += $nl }
        return $text + "[$section]" + $nl + "$key = $value" + $nl
    }

    $body = $m.Groups[2].Value
    $keyPattern = "(?m)^$escapedKey\s*=.*$"
    if ([regex]::IsMatch($body,$keyPattern)) {
        $body = [regex]::Replace($body,$keyPattern,"$key = $value",1)
    } else {
        $body = "$key = $value" + $nl + $body
    }
    return $text.Substring(0,$m.Groups[2].Index) + $body +
        $text.Substring($m.Groups[2].Index + $m.Groups[2].Length)
}

$running = Get-Process -ErrorAction SilentlyContinue | Where-Object {
    $_.ProcessName -ieq "OR2006C2C" -or $_.ProcessName -ieq "outrun-vr-host"
}
if ($running) {
    $message = "OutRun or outrun-vr-host.exe is still running. Close it before switching."
    $diagnostic = Write-BackendSelectionFailureDiagnostic -Phase 'PROCESS_GUARD' -ErrorText $message -RollbackStatus 'not-required'
    throw ("{0} Diagnostic={1}" -f $message,$diagnostic)
}

# Preserve any uncollected logs before touching the backend or starting a new
# session. This makes game-side truncate/overwrite behavior harmless.
try {
    Seal-PendingSessionLogs
} catch {
    $diagnostic = Write-BackendSelectionFailureDiagnostic -Phase 'ARCHIVE_PENDING_LOGS' -ErrorText $_.Exception.Message -RollbackStatus 'not-required'
    throw ("Could not archive pending VR logs before backend switch. Diagnostic={0}; error={1}" -f $diagnostic,$_.Exception.Message)
}

$backendSwitchTransaction = $null
try {
    $backendSwitchTransaction = Start-BackendSwitchTransaction
} catch {
    $diagnostic = Write-BackendSelectionFailureDiagnostic -Phase 'TRANSACTION_SNAPSHOT' -ErrorText $_.Exception.Message -RollbackStatus 'not-started'
    throw ("Could not snapshot backend selection state. Diagnostic={0}; error={1}" -f $diagnostic,$_.Exception.Message)
}
$removeBackendSwitchTransactionBackup = $true
try {
Copy-Required "dinput8.dll"

if ($Backend -eq "2d") {
    Remove-RootVerified "d3d9.dll"
    Remove-RootVerified "multiviewpatcher.dll"
    Remove-RootVerified "outrun-vr-host.exe"
} else {
    Copy-Required "outrun-vr-host.exe"
    if ($Backend -eq "dxvk") {
        Copy-Required "d3d9.dll"
        Copy-Required "multiviewpatcher.dll"
    } elseif ($Backend -eq "dxvk-safe") {
        $dxvkProvider = Join-Path (Join-Path $backendRoot "dxvk") "d3d9.dll"
        if (-not (Test-Path $dxvkProvider)) { throw "DXVK provider missing: $dxvkProvider" }
        Copy-Item $dxvkProvider (Join-Path $root "d3d9.dll") -Force
        Remove-RootVerified "multiviewpatcher.dll"
    } else {
        Remove-RootVerified "d3d9.dll"
        Remove-RootVerified "multiviewpatcher.dll"
        if (Test-Path (Join-Path $root "d3d9.dll")) {
            throw "Local d3d9.dll is still present; refusing $Backend mode."
        }
    }
}

$ini = Join-Path $root "OutRun2006Tweaks.ini"
if (Test-Path $ini) {
    $text = Get-Content $ini -Raw
    $text = Repair-IniSectionHeaders $text

    if ($Backend -eq "2d") {
        $text = Set-IniSectionValue $text "VR" "RenderBackend" "1"
        $text = Set-IniSectionValue $text "VR" "Enabled" "false"
        $text = Set-IniSectionValue $text "VR" "AutoLaunchHost" "false"
        $text = Set-IniSectionValue $text "VR" "AutoEnableWhenHostPresent" "false"
        $text = Set-IniSectionValue $text "VR" "PreferD3D9Ex" "false"
        $text = Set-IniSectionValue $text "VR" "DirectGpuOnly" "false"
        $text = Set-IniSectionValue $text "VR" "DisableDesktopDuplication" "false"
    } elseif ($Backend -eq "dxvk-safe") {
        $text = Set-IniSectionValue $text "VR" "RenderBackend" "1"
        $text = Set-IniSectionValue $text "VR" "Enabled" "true"
        $text = Set-IniSectionValue $text "VR" "AutoLaunchHost" "true"
        $text = Set-IniSectionValue $text "VR" "AutoEnableWhenHostPresent" "true"
        $text = Set-IniSectionValue $text "VR" "PreferD3D9Ex" "true"
        $text = Set-IniSectionValue $text "VR" "DirectGpuOnly" "false"
        $text = Set-IniSectionValue $text "VR" "DisableDesktopDuplication" "false"
        $text = Set-IniSectionValue $text "Graphics" "TransparencySupersampling" "false"
    } elseif ($Backend -eq "d3d9") {
        # DX9Ex focus branch: D3D9 is the reference backend. DirectGPU remains optional
        # so SBS/Desktop Duplication can still fail open while Ex promotion is tested.
        $text = Set-IniSectionValue $text "VR" "RenderBackend" "1"
        $text = Set-IniSectionValue $text "VR" "Enabled" "true"
        $text = Set-IniSectionValue $text "VR" "AutoLaunchHost" "true"
        $text = Set-IniSectionValue $text "VR" "AutoEnableWhenHostPresent" "true"
        $text = Set-IniSectionValue $text "VR" "PreferD3D9Ex" "true"
        $text = Set-IniSectionValue $text "VR" "DirectGpuOnly" "false"
        $text = Set-IniSectionValue $text "VR" "DisableDesktopDuplication" "false"
    } elseif ($Backend -eq "dx11") {
        # Explicitly exercise the x64 D3D11 OpenXR DirectGPU host. The game side
        # remains D3D9Ex; DirectGPU-only prevents a desktop-duplication fallback
        # from hiding ACK/run-identity failures.
        $text = Set-IniSectionValue $text "VR" "RenderBackend" "1"
        $text = Set-IniSectionValue $text "VR" "Enabled" "true"
        $text = Set-IniSectionValue $text "VR" "AutoLaunchHost" "true"
        $text = Set-IniSectionValue $text "VR" "AutoEnableWhenHostPresent" "true"
        $text = Set-IniSectionValue $text "VR" "PreferD3D9Ex" "true"
        $text = Set-IniSectionValue $text "VR" "DirectGpuOnly" "true"
        $text = Set-IniSectionValue $text "VR" "DisableDesktopDuplication" "true"
    } else {
        $value = switch ($Backend) {
            "dxvk" { "2" }
        }
        $text = Set-IniSectionValue $text "VR" "RenderBackend" $value
        $text = Set-IniSectionValue $text "VR" "Enabled" "true"
        $text = Set-IniSectionValue $text "VR" "AutoLaunchHost" "true"
        $text = Set-IniSectionValue $text "VR" "AutoEnableWhenHostPresent" "true"
        $text = Set-IniSectionValue $text "VR" "PreferD3D9Ex" "true"
        $text = Set-IniSectionValue $text "VR" "DirectGpuOnly" "true"
        if ($Backend -eq "dxvk") {
            $text = Set-IniSectionValue $text "Graphics" "TransparencySupersampling" "false"
        }
    }

    # Keep the experimental cockpit camera completely isolated from normal
    # A/B/HUD/performance/backend sessions. It is enabled only by G_COCKPIT.
    $driverSeatValue = if ($variant -eq "G_COCKPIT") { "true" } else { "false" }
    $text = Set-IniSectionValue $text "VR" "DriverSeatView" $driverSeatValue

    Set-Content $ini $text -Encoding UTF8
}

# Seal preflight-to-root continuity before any game launch/session handoff.
# This is deliberately after binary + INI mutation and before session creation,
# so a partial or stale selection fails closed instead of becoming runnable.
$rootPayloadAttestation = Assert-RootPayloadIdentity
$rootPayloadAttestationPath = Join-Path $root 'ROOT_PAYLOAD_ATTESTATION.json'
$rootPayloadAttestation | ConvertTo-Json -Depth 8 | Set-Content $rootPayloadAttestationPath -Encoding UTF8

$nl = [Environment]::NewLine
$matrixFile = Join-Path $root "BUILD_MATRIX_ID.txt"
$matrix = if (Test-Path $matrixFile) { (Get-Content $matrixFile -Raw).Trim() } else { "UNIFIED_LOCAL" }
$startedUtc = (Get-Date).ToUniversalTime()
$session = $startedUtc.ToString("yyyyMMddTHHmmssfffZ") + "-" + [guid]::NewGuid().ToString("N").Substring(0,8)
$sessionRoot = Join-Path $root ("logs/{0}/{1}/{2}/{3}" -f $matrix,$variant,$TestProfile,$session)
$backendSwitchTransaction.SessionRoot = $sessionRoot
New-Item -ItemType Directory -Force $sessionRoot | Out-Null

$activeText = @(
    "backend=$Backend"
    "variant=$variant"
    "profile=$TestProfile"
    "sourceSha=$sourceSha"
    "matrix=$matrix"
    "session=$session"
    "startedUtc=$($startedUtc.ToString('o'))"
    "selected=$((Get-Date).ToString('o'))"
) -join $nl
Set-Content (Join-Path $root "ACTIVE_VR_BACKEND.txt") $activeText -Encoding ascii

$configHash = "missing"
if (Test-Path $ini) { $configHash = (Get-FileHash $ini -Algorithm SHA256).Hash.ToLowerInvariant() }
$sessionManifest = [ordered]@{
    SchemaVersion = 4
    BuildMatrixId = $matrix
    VariantId = $variant
    Backend = $Backend
    TestProfile = $TestProfile
    SourceSha = $sourceSha
    SessionId = $session
    StartedUtc = $startedUtc.ToString("o")
    ConfigSha256 = $configHash
    RootPayloadAttestation = $rootPayloadAttestation
    CollectionStatus = "started-before-game-launch"
    PreexistingLogs = @()
}
$sessionManifest | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $root "CURRENT_VR_SESSION.json") -Encoding UTF8
$sessionManifest | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $sessionRoot "session_manifest.json") -Encoding UTF8

if (Test-Path $ini) {
    $allowed = '^(Enabled|AutoLaunchHost|AutoEnableWhenHostPresent|RenderBackend|PreferD3D9Ex|DirectGpuOnly|DisableDesktopDuplication|SkyGlowFactor|DriverSeatView)\s*='
    Get-Content $ini | Where-Object { $_ -match $allowed } |
        Set-Content (Join-Path $sessionRoot "VR_CONFIG_SNAPSHOT.txt") -Encoding UTF8
}
Copy-Item (Join-Path $root "ACTIVE_VR_BACKEND.txt") $sessionRoot -Force
Copy-Item $rootPayloadAttestationPath $sessionRoot -Force
if (Test-Path (Join-Path $root "BUILD_INPUTS.json")) {
    Copy-Item (Join-Path $root "BUILD_INPUTS.json") $sessionRoot -Force
}
} catch {
    $selectionFailure = $_.Exception
    try {
        Restore-BackendSwitchTransaction $backendSwitchTransaction
        $diagnostic = Write-BackendSelectionFailureDiagnostic -Phase 'MUTATION_OR_SESSION_SETUP' -ErrorText $selectionFailure.Message -RollbackStatus 'restored'
        throw ("Backend selection failed before launch; rollback restored prior root state. Diagnostic={0}; error={1}" -f
            $diagnostic,$selectionFailure.Message)
    } catch {
        if ($_.Exception.Message -like 'Backend selection failed before launch; rollback restored prior root state.*') {
            throw
        }
        $rollbackFailure = $_.Exception
        $removeBackendSwitchTransactionBackup = $false
        $diagnostic = Write-BackendSelectionFailureDiagnostic -Phase 'MUTATION_OR_SESSION_SETUP' -ErrorText $selectionFailure.Message -RollbackStatus ('failed: ' + $rollbackFailure.Message) -BackupRoot $backendSwitchTransaction.BackupRoot
        throw ("Backend selection failed: {0}; rollback failed: {1}; backup preserved at {2}; Diagnostic={3}" -f
            $selectionFailure.Message,$rollbackFailure.Message,$backendSwitchTransaction.BackupRoot,$diagnostic)
    }
} finally {
    if ($removeBackendSwitchTransactionBackup) {
        Remove-BackendSwitchTransaction $backendSwitchTransaction
    }
}

Write-Host "OutRun renderer mode activated: $Backend"
Write-Host "Test variant: $variant"
Write-Host "Test profile: $TestProfile"
Write-Host "Source SHA: $sourceSha"
Write-Host "Diagnostic session prepared before launch: $session"
Write-Host "Any previous root logs were archived before this session was created."
switch ($Backend) {
    "2d"   { Write-Host "2D ORIGINAL: classic D3D9, VR disabled, D3D9Ex promotion disabled, no VR host." }
    "d3d9" { Write-Host "D3D9Ex REFERENCE: PreferD3D9Ex enabled; DirectGPU optional; profile=$TestProfile." }
    "dx11" { Write-Host "DX11 HOST/DIRECTGPU: D3D9Ex game + x64 D3D11 OpenXR host; DirectGPU-only; ACK run identity required." }
    "dxvk-safe" { Write-Host "DXVK SAFE: provider-local D3D9Ex is probed when exported; DirectGPU optional; multiview patcher disabled." }
    "dxvk" { Write-Host "DXVK MULTIVIEW: local d3d9.dll + multiviewpatcher.dll active." }
}