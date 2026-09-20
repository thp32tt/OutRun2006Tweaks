Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$selector = Join-Path $root "Select-OutRunVRBackend.ps1"
$runner = Join-Path $root "Run-OutRunVRTest.ps1"

function Get-ActiveValues {
    $result = @{ backend='unknown'; profile='CORRECTNESS' }
    $active = Join-Path $root "ACTIVE_VR_BACKEND.txt"
    if (-not (Test-Path $active)) { return $result }
    Get-Content $active | ForEach-Object {
        if ($_ -match '^([^=]+)=(.*)$') {
            if ($matches[1] -eq 'backend') { $result.backend = $matches[2].Trim() }
            if ($matches[1] -eq 'profile' -and $matches[2].Trim()) { $result.profile = $matches[2].Trim() }
        }
    }
    return $result
}

function Get-SelectedProfile {
    if ($profileBox.SelectedItem) { return [string]$profileBox.SelectedItem }
    return 'CORRECTNESS'
}

function Refresh-Status {
    $current = Get-ActiveValues
    $backendText = switch ($current.backend) {
        "2d"        { "2D ORIGINAL" }
        "d3d9"      { "D3D9Ex REFERENCE" }
        "dxvk-safe" { "DXVK SAFE" }
        "dxvk"      { "DXVK MULTIVIEW" }
        "dx12"      { "DX12 STRICT" }
        default     { "확인되지 않음" }
    }
    $status.Text = "현재: $backendText / $($current.profile)"
}

function Invoke-Selector([string]$backend,[string]$profile) {
    if (-not (Test-Path $selector)) {
        throw "Select-OutRunVRBackend.ps1 파일이 없습니다."
    }
    $outFile = Join-Path $env:TEMP "outrun-vr-selector-out.txt"
    $errFile = Join-Path $env:TEMP "outrun-vr-selector-err.txt"
    Remove-Item $outFile,$errFile -Force -ErrorAction SilentlyContinue

    $args = @(
        "-NoProfile","-ExecutionPolicy","Bypass","-File",$selector,
        "-Backend",$backend,"-TestProfile",$profile
    )
    $p = Start-Process powershell -Wait -PassThru -WindowStyle Hidden -ArgumentList $args -RedirectStandardOutput $outFile -RedirectStandardError $errFile

    $output = ""
    if (Test-Path $outFile) { $output += (Get-Content $outFile -Raw) }
    if (Test-Path $errFile) { $output += (Get-Content $errFile -Raw) }
    if ($p.ExitCode -ne 0) {
        if ([string]::IsNullOrWhiteSpace($output)) { $output = "Backend/profile switch failed." }
        throw $output.Trim()
    }
}

function Select-Backend([string]$backend) {
    $profile = Get-SelectedProfile
    try {
        Invoke-Selector $backend $profile
        Refresh-Status
        $label = switch ($backend) {
            "2d"        { "2D ORIGINAL" }
            "d3d9"      { "D3D9Ex REFERENCE" }
            "dxvk-safe" { "DXVK SAFE" }
            "dxvk"      { "DXVK MULTIVIEW" }
            "dx12"      { "DX12 STRICT" }
        }
        [System.Windows.Forms.MessageBox]::Show(
            "$label / $profile 로 준비했습니다.",
            "전환 완료",
            [System.Windows.Forms.MessageBoxButtons]::OK,
            [System.Windows.Forms.MessageBoxIcon]::Information
        ) | Out-Null
    } catch {
        [System.Windows.Forms.MessageBox]::Show(
            $_.Exception.Message,
            "전환 실패",
            [System.Windows.Forms.MessageBoxButtons]::OK,
            [System.Windows.Forms.MessageBoxIcon]::Error
        ) | Out-Null
    }
}

function Start-VRTest {
    if (-not (Test-Path $runner)) {
        [System.Windows.Forms.MessageBox]::Show(
            "Run-OutRunVRTest.ps1 파일이 없습니다.",
            "OutRun VR Test Launcher",
            [System.Windows.Forms.MessageBoxButtons]::OK,
            [System.Windows.Forms.MessageBoxIcon]::Error
        ) | Out-Null
        return
    }

    $profile = Get-SelectedProfile
    $active = Get-ActiveValues
    if ($active.backend -eq 'unknown') {
        [System.Windows.Forms.MessageBox]::Show(
            "먼저 D3D9Ex REFERENCE를 선택하세요.",
            "백엔드 선택 필요",
            [System.Windows.Forms.MessageBoxButtons]::OK,
            [System.Windows.Forms.MessageBoxIcon]::Warning
        ) | Out-Null
        return
    }

    # The runner will re-seal stale logs and create a new profile-aware session
    # if the combobox differs from the currently active profile.
    $args = @(
        "-NoProfile","-ExecutionPolicy","Bypass","-File",$runner,
        "-TestProfile",$profile
    )
    Start-Process powershell -ArgumentList $args -WorkingDirectory $root
}

$form = New-Object System.Windows.Forms.Form
$form.Text = "OutRun 2006 VR Test Launcher"
$form.StartPosition = "CenterScreen"
$form.ClientSize = New-Object System.Drawing.Size(520,650)
$form.FormBorderStyle = "FixedDialog"
$form.MaximizeBox = $false

$title = New-Object System.Windows.Forms.Label
$title.Text = "OutRun 2006 VR Test Launcher"
$title.Font = New-Object System.Drawing.Font("Segoe UI",16,[System.Drawing.FontStyle]::Bold)
$title.AutoSize = $true
$title.Location = New-Object System.Drawing.Point(66,18)
$form.Controls.Add($title)

$hint = New-Object System.Windows.Forms.Label
$hint.Text = "권장: D3D9Ex REFERENCE + CORRECTNESS 1회. 비교가 필요할 때만 CONTROL/PERFORMANCE."
$hint.Font = New-Object System.Drawing.Font("Segoe UI",9)
$hint.AutoSize = $false
$hint.Size = New-Object System.Drawing.Size(440,40)
$hint.Location = New-Object System.Drawing.Point(40,55)
$form.Controls.Add($hint)

$profileLabel = New-Object System.Windows.Forms.Label
$profileLabel.Text = "Test Profile"
$profileLabel.Font = New-Object System.Drawing.Font("Segoe UI",10,[System.Drawing.FontStyle]::Bold)
$profileLabel.AutoSize = $true
$profileLabel.Location = New-Object System.Drawing.Point(42,101)
$form.Controls.Add($profileLabel)

$profileBox = New-Object System.Windows.Forms.ComboBox
$profileBox.DropDownStyle = [System.Windows.Forms.ComboBoxStyle]::DropDownList
$profileBox.Size = New-Object System.Drawing.Size(255,32)
$profileBox.Location = New-Object System.Drawing.Point(145,96)
[void]$profileBox.Items.Add("CORRECTNESS")
[void]$profileBox.Items.Add("CONTROL")
[void]$profileBox.Items.Add("PERFORMANCE")
$activeInitial = Get-ActiveValues
$idx = $profileBox.Items.IndexOf($activeInitial.profile)
if ($idx -lt 0) { $idx = 0 }
$profileBox.SelectedIndex = $idx
$form.Controls.Add($profileBox)

$profileHelp = New-Object System.Windows.Forms.Label
$profileHelp.Text = "CORRECTNESS=기본  |  CONTROL=보수적 비교  |  PERFORMANCE=성능 비교"
$profileHelp.Font = New-Object System.Drawing.Font("Segoe UI",8.5)
$profileHelp.AutoSize = $true
$profileHelp.Location = New-Object System.Drawing.Point(42,132)
$form.Controls.Add($profileHelp)

$status = New-Object System.Windows.Forms.Label
$status.Font = New-Object System.Drawing.Font("Segoe UI",10,[System.Drawing.FontStyle]::Bold)
$status.AutoSize = $true
$status.Location = New-Object System.Drawing.Point(42,160)
$form.Controls.Add($status)
Refresh-Status

$primary = New-Object System.Windows.Forms.Button
$primary.Text = "D3D9Ex REFERENCE  (권장)"
$primary.Size = New-Object System.Drawing.Size(430,58)
$primary.Location = New-Object System.Drawing.Point(44,195)
$primary.Font = New-Object System.Drawing.Font("Segoe UI",11,[System.Drawing.FontStyle]::Bold)
$primary.Tag = "d3d9"
$primary.Add_Click({ Select-Backend $this.Tag })
$form.Controls.Add($primary)

$control2d = New-Object System.Windows.Forms.Button
$control2d.Text = "2D ORIGINAL  (VR OFF)"
$control2d.Size = New-Object System.Drawing.Size(430,44)
$control2d.Location = New-Object System.Drawing.Point(44,265)
$control2d.Tag = "2d"
$control2d.Add_Click({ Select-Backend $this.Tag })
$form.Controls.Add($control2d)

$legacyLabel = New-Object System.Windows.Forms.Label
$legacyLabel.Text = "Legacy backend comparison — DX9Ex 기준 확립 전에는 일반 테스트에 사용하지 않음"
$legacyLabel.Font = New-Object System.Drawing.Font("Segoe UI",8.5)
$legacyLabel.AutoSize = $true
$legacyLabel.Location = New-Object System.Drawing.Point(44,322)
$form.Controls.Add($legacyLabel)

$legacyButtons = @(
    @{ Text="DXVK SAFE"; Backend="dxvk-safe"; X=44 },
    @{ Text="DXVK MULTIVIEW"; Backend="dxvk"; X=190 },
    @{ Text="DX12 STRICT"; Backend="dx12"; X=336 }
)
foreach ($b in $legacyButtons) {
    $btn = New-Object System.Windows.Forms.Button
    $btn.Text = $b.Text
    $btn.Size = New-Object System.Drawing.Size(138,42)
    $btn.Location = New-Object System.Drawing.Point($b.X,350)
    $btn.Tag = $b.Backend
    $btn.Add_Click({ Select-Backend $this.Tag })
    $form.Controls.Add($btn)
}

$runBtn = New-Object System.Windows.Forms.Button
$runBtn.Text = "선택한 Profile로 테스트 실행"
$runBtn.Size = New-Object System.Drawing.Size(430,66)
$runBtn.Location = New-Object System.Drawing.Point(44,420)
$runBtn.Font = New-Object System.Drawing.Font("Segoe UI",11,[System.Drawing.FontStyle]::Bold)
$runBtn.Add_Click({ Start-VRTest })
$form.Controls.Add($runBtn)

$logInfo = New-Object System.Windows.Forms.Label
$logInfo.Text = "게임 종료 후 로그는 Matrix / Variant / Profile / Session별로 자동 분리·ZIP 됩니다."
$logInfo.Font = New-Object System.Drawing.Font("Segoe UI",9)
$logInfo.AutoSize = $false
$logInfo.Size = New-Object System.Drawing.Size(430,42)
$logInfo.Location = New-Object System.Drawing.Point(44,505)
$form.Controls.Add($logInfo)

$captureInfo = New-Object System.Windows.Forms.Label
$captureInfo.Text = "VR 진단 캡처: 게임 중 Ctrl+F9. 약 10초 전 + 2초 후 텔레메트리를 저장하며 F11 Overlay/F12 recenter는 유지합니다."
$captureInfo.Font = New-Object System.Drawing.Font("Segoe UI",9)
$captureInfo.AutoSize = $false
$captureInfo.Size = New-Object System.Drawing.Size(430,42)
$captureInfo.Location = New-Object System.Drawing.Point(44,550)
$form.Controls.Add($captureInfo)

[void]$form.ShowDialog()
