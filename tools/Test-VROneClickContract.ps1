Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$toolsRoot = $PSScriptRoot
$targetPath = Join-Path $toolsRoot 'VR_ONE_CLICK_TARGET.json'
if (!(Test-Path $targetPath)) { throw "Missing one-click target metadata: $targetPath" }

$parseFiles = @(
    'Invoke-OutRunVROneClick.ps1',
    'Test-OutRunVROneClickPreflight.ps1',
    'Select-OutRunVRBackend.ps1',
    'Test-BackendSelectorTransaction.ps1',
    'Test-RunOutRunVRFailureDiagnostics.ps1',
    'Run-OutRunVRTest.ps1',
    'OutRunVR-TestProfiles.ps1',
    'OutRunVR-Test-Selector.ps1',
    'Build-OutRunPCFast.ps1',
    'Acquire-OutRunDXVK.ps1',
    'Test-DxvkAcquisition.ps1',
    'OutRunVR-PackageIntegrity.ps1',
    'Test-OutRunVRPackageIntegrity.ps1',
    'Test-OutRunVROneClickBehavior.ps1'
)

foreach ($name in $parseFiles) {
    $path = Join-Path $toolsRoot $name
    if (!(Test-Path $path)) { throw "Missing one-click dependency: $path" }

    $tokens = $null
    $errors = $null
    [void][System.Management.Automation.Language.Parser]::ParseFile(
        $path, [ref]$tokens, [ref]$errors)
    if ($errors -and $errors.Count -gt 0) {
        $detail = ($errors | ForEach-Object {
            "{0}:{1} {2}" -f $_.Extent.StartLineNumber,$_.Extent.StartColumnNumber,$_.Message
        }) -join '; '
        throw "PowerShell syntax error in $name :: $detail"
    }
}

$profileLib = Join-Path $toolsRoot 'OutRunVR-TestProfiles.ps1'
. $profileLib
$performanceProfile = Get-OutRunVRTestProfile -Name PERFORMANCE
foreach ($requiredArg in @(
    '-FramerateLimit=0',
    '-FramerateInterpolation=true',
    '-FramerateUnlockExperimental=true',
    '-FrameCadenceMode=1',
    '-FrameCadenceTargetHz=0',
    '-DisableDesktopVsync=true'
)) {
    if ($performanceProfile.Arguments -notcontains $requiredArg) {
        throw "PERFORMANCE profile cadence contract missing: $requiredArg"
    }
}
foreach ($forbiddenArg in @(
    '-FramerateLimit=60',
    '-FramerateInterpolation=false',
    '-FramerateUnlockExperimental=false',
    '-FrameCadenceMode=0',
    '-DisableDesktopVsync=false'
)) {
    if ($performanceProfile.Arguments -contains $forbiddenArg) {
        throw "PERFORMANCE profile still contains conservative cadence override: $forbiddenArg"
    }
}
if ([string]$performanceProfile.Environment.OUTRUN_VR_PERFORMANCE_PROFILE -ne '1') {
    throw 'PERFORMANCE profile does not enable OUTRUN_VR_PERFORMANCE_PROFILE.'
}

$runnerPerformanceText = Get-Content (Join-Path $toolsRoot 'Run-OutRunVRTest.ps1') -Raw
foreach ($requiredText in @(
    '$cleanDxvkPerformance = ($backend -eq ''dxvk-safe'' -and $TestProfile -eq ''PERFORMANCE'')',
    'if($backend -eq ''d3d9'' -or $cleanDxvkPerformance)',
    '$gameArgs += ''-HudInspector=false''',
    'if($backend -ne ''2d'' -and -not $cleanDxvkPerformance)',
    '"cleanDxvkPerformance=$cleanDxvkPerformance"',
    '"shaderFingerprintEnabled=$($backend -ne ''2d'' -and -not $cleanDxvkPerformance)"'
)) {
    if ($runnerPerformanceText -notmatch [regex]::Escape($requiredText)) {
        throw "DXVK clean-performance runner contract missing: $requiredText"
    }
}

$selectorTransactionTest = Join-Path $toolsRoot 'Test-BackendSelectorTransaction.ps1'
& $selectorTransactionTest

$oneClickBehaviorTest = Join-Path $toolsRoot 'Test-OutRunVROneClickBehavior.ps1'
if (!(Test-Path $oneClickBehaviorTest -PathType Leaf)) {
    throw "Missing one-click behavior test: $oneClickBehaviorTest"
}
& $oneClickBehaviorTest

$runnerFailureTest = Join-Path $toolsRoot 'Test-RunOutRunVRFailureDiagnostics.ps1'
& $runnerFailureTest

$pythonFiles = @(
    'analyze_dxvk_session.py',
    'test_analyze_dxvk_session.py'
)
$python = Get-Command python -ErrorAction SilentlyContinue
if (!$python) { throw 'python is required for one-click analyzer syntax validation.' }
foreach ($name in $pythonFiles) {
    $path = Join-Path $toolsRoot $name
    if (!(Test-Path $path)) { throw "Missing one-click Python analyzer: $path" }
    & $python.Source -m py_compile $path
    if ($LASTEXITCODE -ne 0) {
        throw "Python syntax validation failed: $name"
    }
}

$target = Get-Content $targetPath -Raw | ConvertFrom-Json
if (!$target.DevelopmentBranch) {
    throw 'VR_ONE_CLICK_TARGET.json has no DevelopmentBranch.'
}
$allowed = @('2d','d3d9','dx11','dxvk-safe','dxvk')
if ($allowed -notcontains [string]$target.LaunchBackend) {
    throw "Invalid LaunchBackend in VR_ONE_CLICK_TARGET.json: $($target.LaunchBackend)"
}

$startHere = Get-Content (Join-Path $toolsRoot 'START_HERE_VR_TEST.cmd') -Raw
if ($startHere -notmatch 'OutRunVR-Test-Selector\.ps1') {
    throw 'START_HERE_VR_TEST.cmd does not route through the evening selector.'
}
$startupSelector = Get-Content (Join-Path $toolsRoot 'OutRunVR-Test-Selector.ps1') -Raw
foreach ($requiredText in @(
    'Invoke-OutRunVROneClick.ps1',
    '& $launcher -Backend $backendValue -TestProfile $profileValue -VariantId AUTO -AllowTargetOverride',
    'DXVK SAFE - 오늘 밤 기본 테스트',
    'CORRECTNESS - 화면/HUD/렌즈플레어 우선'
)) {
    if ($startupSelector -notmatch [regex]::Escape($requiredText)) {
        throw "Evening selector one-click routing contract missing: $requiredText"
    }
}

$launcherText = Get-Content (Join-Path $toolsRoot 'Invoke-OutRunVROneClick.ps1') -Raw
foreach ($required in @(
    '[switch]$AllowTargetOverride',
    'One-click backend override blocked',
    'One-click variant override blocked',
    'Restore-PackagedBaselineIni',
    'package-baseline/OutRun2006Tweaks.ini',
    'Write-OneClickPreflightFailureDiagnostic',
    '_preflight_failures',
    'VR_PREFLIGHT_FAILURE_',
    'One-click preflight failed before session creation'
)) {
    if ($launcherText -notmatch [regex]::Escape($required)) {
        throw "One-click branch target override lock missing: $required"
    }
}
foreach ($required in @('Test-OutRunVROneClickPreflight.ps1','& $preflight -Backend $resolvedBackend')) {
    if ($launcherText -notmatch [regex]::Escape($required)) {
        throw "One-click launcher does not invoke runtime preflight: $required"
    }
}

$selectorCmd = Get-Content (Join-Path $toolsRoot 'Select-OutRunVRBackend.cmd') -Raw
$selectorUi = Get-Content (Join-Path $toolsRoot 'OutRunVR-Test-Selector.ps1') -Raw
if ($selectorCmd -match '(?i)dx12' -or $selectorUi -match '(?i)dx12') {
    throw 'Retired DX12 path is still exposed by a user-facing selector.'
}

$selector = Get-Content (Join-Path $toolsRoot 'Select-OutRunVRBackend.ps1') -Raw
$quotedBackend = [regex]::Escape('"' + [string]$target.LaunchBackend + '"')
if ($selector -notmatch $quotedBackend) {
    throw "Select-OutRunVRBackend.ps1 does not accept branch LaunchBackend=$($target.LaunchBackend)"
}

$package = Get-Content (Join-Path $toolsRoot 'Build-OutRunPCFast.ps1') -Raw
foreach ($requiredText in @(
    'DevelopmentBranch = [string]$oneClickTarget.DevelopmentBranch',
    'RendererTarget = [string]$oneClickTarget.RendererTarget',
    'DevelopmentStage = [string]$oneClickTarget.Stage',
    'LaunchBackend = [string]$oneClickTarget.LaunchBackend',
    'VariantId = $canonicalVariantId'
)) {
    if ($package -notmatch [regex]::Escape($requiredText)) {
        throw "Package source/branch identity contract missing: $requiredText"
    }
}
$preflightText = Get-Content (Join-Path $toolsRoot 'Test-OutRunVROneClickPreflight.ps1') -Raw
foreach ($requiredText in @(
    'BUILD_INPUTS.json',
    'Package source mismatch',
    'Package branch mismatch',
    'Package renderer mismatch',
    'Package launch backend mismatch',
    'Package variant mismatch',
    'One-click slot source mismatch',
    'One-click slot payload mismatch',
    'SlotPayload',
    'Remove-Item $reportPath -Force',
    'OutRunVR-PackageIntegrity.ps1',
    'SHA256SUMS.txt',
    'Test-OutRunVRPackageIntegrity',
    'PackageIntegrity'
)) {
    if ($preflightText -notmatch [regex]::Escape($requiredText)) {
        throw "Runtime package identity preflight missing: $requiredText"
    }
}
foreach ($required in @(
    "packageBaselineDir = Join-Path `$packageDir 'package-baseline'",
    "Copy-Item 'OutRun2006Tweaks.ini' (Join-Path `$packageBaselineDir 'OutRun2006Tweaks.ini')",
    'Invoke-OutRunVROneClick.ps1',
    'VR_ONE_CLICK_TARGET.json',
    'ONE_RUN_VISUAL_CHECKLIST.txt',
    'START_HERE_VR_TEST.cmd',
    'Collect-OutRunVRLogs.ps1',
    'OutRunVR-PackageIntegrity.ps1'
)) {
    if ($package -notmatch [regex]::Escape($required)) {
        throw "PC FAST package does not include one-click dependency: $required"
    }
}

foreach ($requiredText in @(
    'Assert-RootPayloadIdentity',
    'ROOT_PAYLOAD_ATTESTATION.json',
    'RootPayloadAttestation',
    'Start-BackendSwitchTransaction',
    'Restore-BackendSwitchTransaction',
    'Remove-BackendSwitchTransaction',
    'Backend selection rollback failed',
    'backup preserved at',
    'Write-BackendSelectionFailureDiagnostic',
    '_selector_failures',
    'VR_SELECTOR_FAILURE_',
    'RollbackStatus',
    'SOURCE_RESOLUTION'
)) {
    if ($selector -notmatch [regex]::Escape($requiredText)) {
        throw "Selector root payload attestation contract missing: $requiredText"
    }
}

$collector = Get-Content (Join-Path $toolsRoot 'Collect-OutRunVRLogs.ps1') -Raw
if ($collector -notmatch [regex]::Escape("VisualGateChecklist='ONE_RUN_VISUAL_CHECKLIST.txt'")) {
    throw 'Collector does not bind the one-run visual gate into analysis metadata.'
}
if ($collector -notmatch [regex]::Escape('VR_ONE_CLICK_PREFLIGHT.json')) {
    throw 'Collector does not preserve one-click preflight report.'
}
foreach ($requiredText in @(
    "BUILD_INPUTS.json",
    "Analyze-OutRunVRSession.ps1",
    "AUTO_ANALYSIS_SUMMARY.json"
)) {
    if ($collector -notmatch [regex]::Escape($requiredText)) {
        throw "Collector exact-build analysis identity contract missing: $requiredText"
    }
}
$runtimeAnalyzer = Get-Content (Join-Path $toolsRoot 'Analyze-OutRunVRSession.ps1') -Raw
foreach ($requiredText in @(
    'BuildIdentityVerified',
    'BuildIdentityMismatch',
    'DXVK_BUILD_IDENTITY_MISMATCH',
    'SESSION_BUILD_INPUT_SOURCE_MISMATCH',
    'SESSION_PREFLIGHT_SOURCE_MISMATCH',
    'DxvkDirectEvidenceTrusted',
    'DxvkDirectEvidenceBlockers',
    'DXVK_DIRECTGPU_EVIDENCE_UNTRUSTED',
    'DXVK_HOST_GENERATION_MISMATCH',
    'PACKAGE_INTEGRITY_EVIDENCE_MISSING',
    'FrameBudgetEvidenceAvailable',
    'HostPipelineWindowCount',
    'ProducerBudgetFallback',
    'captureAvgMaxP95',
    'endAvgMaxP95'
)) {
    if ($runtimeAnalyzer -notmatch [regex]::Escape($requiredText)) {
        throw "Runtime analyzer exact-build identity gate missing: $requiredText"
    }
}
foreach ($requiredText in @(
    '[switch]$Emergency',
    'emergency-snapshot-running-process',
    'Source logs/captures and CURRENT_VR_SESSION.json were preserved'
)) {
    if ($collector -notmatch [regex]::Escape($requiredText)) {
        throw "Emergency collector contract missing: $requiredText"
    }
}
$runnerText = Get-Content (Join-Path $toolsRoot 'Run-OutRunVRTest.ps1') -Raw
foreach ($requiredText in @(
    'GAME_LAUNCH_OR_WAIT',
    'HOST_TEARDOWN',
    '& $collector -Emergency',
    'RUNNER_FAILURE.json',
    'COLLECTOR_FAILURE.json',
    'DIAGNOSTIC_COLLECTION'
)) {
    if ($runnerText -notmatch [regex]::Escape($requiredText)) {
        throw "Runner failure diagnostic survivability contract missing: $requiredText"
    }
}
foreach ($requiredText in @(
    'VR_ONE_CLICK_TARGET.json',
    'IntegrationBranch=$developmentBranch',
    'RendererTarget=$rendererTarget',
    "dxvk-safe' -or `$backend -eq 'dx11"
)) {
    if ($collector -notmatch [regex]::Escape($requiredText)) {
        throw "Collector is not branch-aware for one-click runs: $requiredText"
    }
}

switch ([string]$target.RendererTarget) {
    'dx11-native' {
        if ([string]$target.DevelopmentBranch -ne 'vr-dx11-native-r71') {
            throw "DX11 one-click DevelopmentBranch mismatch: $($target.DevelopmentBranch)"
        }
        if ([string]$target.LaunchBackend -ne 'dx11') {
            throw 'DX11-native development branch must currently launch the isolated dx11-host DirectGPU validation mode.'
        }
        if ([bool]$target.NativeDrawPathActive) {
            throw 'NativeDrawPathActive must remain false until the native D3D11 draw owner is actually connected.'
        }
        foreach ($requiredText in @(
            'OUTRUN_VR_DX11_CENSUS',
            "RendererTarget -eq 'dx11-native'"
        )) {
            $launcher = Get-Content (Join-Path $toolsRoot 'Invoke-OutRunVROneClick.ps1') -Raw
            if ($launcher -notmatch [regex]::Escape($requiredText)) {
                throw "DX11 one-click census activation missing: $requiredText"
            }
        }
        foreach ($path in @(
            'src/vr/d3d11/native_backend.cpp',
            'src/vr/d3d11/native_backend.hpp',
            'src/vr/d3d11/state_translation.cpp',
            'src/vr/d3d11/startup_census.cpp',
            'src/vr/d3d11/pipeline_translation.cpp',
            'src/vr/d3d11/runtime_census.cpp',
            'src/vr/core/d3d9_draw_state.hpp',
            'src/vr/game/disasm_render_contract.hpp'
        )) {
            if (!(Test-Path (Join-Path $repoRoot $path))) {
                throw "DX11 branch contract file missing: $path"
            }
        }
    }

    'dxvk' {
        if ([string]$target.DevelopmentBranch -ne 'vr-dxvk-r71-disasm') {
            throw "DXVK one-click DevelopmentBranch mismatch: $($target.DevelopmentBranch)"
        }
        if ([string]$target.LaunchBackend -ne 'dxvk-safe') {
            throw 'DXVK R71 must stay on dxvk-safe until stock two-pass visual parity passes.'
        }
        if ([string]$target.DxvkVersion -ne '3.1.1') {
            throw "Unexpected pinned DXVK version: $($target.DxvkVersion)"
        }

        $acquireDxvk = Get-Content (Join-Path $toolsRoot 'Acquire-OutRunDXVK.ps1') -Raw
        foreach ($requiredText in @(
            '40565b4a724aadc4433fa4e010b4b23916d9b1f1baeee64e17186db94f54e608',
            'PINNED_ARCHIVE_SHA256_AND_EXTRACTED_PROVIDER',
            'No pinned DXVK archive SHA256',
            'DXVK provider does not match x32/d3d9.dll extracted from the pinned archive'
        )) {
            if ($acquireDxvk -notmatch [regex]::Escape($requiredText)) {
                throw "DXVK pinned acquisition contract missing: $requiredText"
            }
        }
        foreach ($requiredText in @(
            'officialDxvkProviderSha',
            'Explicit DXVK provider does not match pinned official DXVK'
        )) {
            if ($package -notmatch [regex]::Escape($requiredText)) {
                throw "DXVK stock-provider package enforcement missing: $requiredText"
            }
        }
        foreach ($required in @(
            'Acquire-OutRunDXVK.ps1',
            "dxvkVersion = '3.1.1'",
            "backends/dxvk",
            'DXVK_D3D9_SHA256.txt'
        )) {
            if ($package -notmatch [regex]::Escape($required)) {
                throw "DXVK one-click packaging contract missing: $required"
            }
        }
        $collectorDxvk = Get-Content (Join-Path $toolsRoot 'Collect-OutRunVRLogs.ps1') -Raw
        foreach ($requiredText in @(
            'analyze_dxvk_session.py',
            'DXVK_SESSION_SUMMARY.json'
        )) {
            if ($collectorDxvk -notmatch [regex]::Escape($requiredText)) {
                throw "DXVK collector provider extraction missing: $requiredText"
            }
        }
        if (!(Test-Path (Join-Path $toolsRoot 'Acquire-OutRunDXVK.ps1'))) {
            throw 'DXVK acquisition helper is missing.'
        }
        if (!(Test-Path (Join-Path $repoRoot 'src/vr/d3d9/dxvk_provider_probe.cpp'))) {
            throw 'DXVK passive provider probe is missing.'
        }
        $stockInteropHeaderPath = Join-Path $repoRoot 'src/vr/d3d9/dxvk_stock_interop.hpp'
        if (!(Test-Path $stockInteropHeaderPath)) {
            throw 'DXVK stock interop ABI declaration is missing.'
        }
        $stockInteropHeader = Get-Content $stockInteropHeaderPath -Raw
        foreach ($requiredText in @(
            'ID3D9VkInteropDeviceR71',
            'GetVulkanHandles',
            'GetSubmissionQueue',
            'VK_KHR_external_memory_win32',
            'VK_KHR_external_semaphore_win32',
            'vkGetMemoryWin32HandleKHR',
            'vkGetSemaphoreWin32HandleKHR'
        )) {
            if ($stockInteropHeader -notmatch [regex]::Escape($requiredText)) {
                throw "DXVK stock native-transport ABI gate missing: $requiredText"
            }
        }
        $deviceProbe = Get-Content (Join-Path $repoRoot 'src/vr/d3d9/device_probe.cpp') -Raw
        if ($deviceProbe -notmatch [regex]::Escape('OutRunVR::Dxvk::LogProviderCensus')) {
            throw 'DXVK provider census is not connected to the startup device lifecycle.'
        }
        $providerProbe = Get-Content (Join-Path $repoRoot 'src/vr/d3d9/dxvk_provider_probe.cpp') -Raw
        if ($providerProbe -notmatch [regex]::Escape('gameLocalProvider')) {
            throw 'DXVK provider census does not verify game-local provider identity.'
        }
        foreach ($requiredText in @(
            'LogProviderCensus',
            'source={} attestation={}',
            'ProbeStockNativeTransportPrerequisites',
            'nativeTransportCandidate',
            'vkGetDeviceProcAddr'
        )) {
            if ($providerProbe -notmatch [regex]::Escape($requiredText)) {
                throw "DXVK provider re-attestation logger missing: $requiredText"
            }
        }

        $exUpgrade = Get-Content (Join-Path $repoRoot 'src/vr/d3d9/ex_device_upgrade.cpp') -Raw
        foreach ($requiredText in @(
            'create-device-classic',
            'create-device-ex',
            'OutRunVR::Dxvk::LogProviderCensus'
        )) {
            if ($exUpgrade -notmatch [regex]::Escape($requiredText)) {
                throw "DXVK device recreation re-attestation wiring missing: $requiredText"
            }
        }

        $dxvkAnalyzer = Get-Content (Join-Path $toolsRoot 'analyze_dxvk_session.py') -Raw
        foreach ($requiredText in @(
            'DXVK_DEVICE_CREATION_REATTESTATION_MISSING',
            'DXVK_DEVICE_CREATION_REATTESTATION_FAILED',
            'DeviceCreationReattestationPassed',
            'NativeTransportPrerequisitesObserved',
            'nativeTransportCandidate'
        )) {
            if ($dxvkAnalyzer -notmatch [regex]::Escape($requiredText)) {
                throw "DXVK session analyzer recreation gate missing: $requiredText"
            }
        }

        & $python.Source (Join-Path $toolsRoot 'test_analyze_dxvk_session.py')
        if ($LASTEXITCODE -ne 0) {
            throw "DXVK session analyzer regression test failed with exit code $LASTEXITCODE"
        }
    }

    default {
        throw "Unsupported RendererTarget in one-click contract: $($target.RendererTarget)"
    }
}

Write-Host ("One-click VR contract PASS: renderer={0} launchBackend={1} stage={2}" -f
    $target.RendererTarget,$target.LaunchBackend,$target.Stage)